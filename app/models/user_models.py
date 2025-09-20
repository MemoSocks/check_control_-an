# app/models/user_models.py

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin, AnonymousUserMixin

from app import db


class Permission:
    """
    Класс-контейнер для констант прав доступа.
    """
    ADD_PARTS = 1
    EDIT_PARTS = 2
    DELETE_PARTS = 4
    GENERATE_QR = 8
    VIEW_AUDIT_LOG = 16
    MANAGE_STAGES = 32
    MANAGE_ROUTES = 64
    VIEW_REPORTS = 128
    MANAGE_USERS = 256
    SEND_TO_SCRAP = 512
    SEND_TO_REWORK = 1024
    ADMIN = 2048


class Role(db.Model):
    """Модель для ролей пользователей."""
    __tablename__ = 'Roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), unique=True)
    default = db.Column(db.Boolean, default=False, index=True)
    permissions = db.Column(db.Integer)
    
    # --- НАЧАЛО ИСПРАВЛЕНИЯ: Заменяем backref на back_populates ---
    users = db.relationship('User', back_populates='role', lazy='dynamic')
    # --- КОНЕЦ ИСПРАВЛЕНИЯ ---

    def __init__(self, **kwargs):
        super(Role, self).__init__(**kwargs)
        if self.permissions is None:
            self.permissions = 0

    def add_permission(self, perm):
        self.permissions |= perm

    def remove_permission(self, perm):
        self.permissions &= ~perm

    def reset_permissions(self):
        self.permissions = 0

    def has_permission(self, perm):
        return self.permissions & perm == perm

    @staticmethod
    def insert_roles():
        """
        Создает или обновляет предопределенные роли в базе данных.
        """
        roles_map = {
            'Operator': [Permission.GENERATE_QR],
            'Manager': [
                Permission.ADD_PARTS, Permission.EDIT_PARTS, Permission.DELETE_PARTS,
                Permission.GENERATE_QR, Permission.VIEW_AUDIT_LOG, Permission.VIEW_REPORTS,
                Permission.SEND_TO_SCRAP, Permission.SEND_TO_REWORK
            ],
            'Administrator': [
                Permission.ADD_PARTS, Permission.EDIT_PARTS, Permission.DELETE_PARTS,
                Permission.GENERATE_QR, Permission.VIEW_AUDIT_LOG, Permission.MANAGE_STAGES,
                Permission.MANAGE_ROUTES, Permission.VIEW_REPORTS, Permission.MANAGE_USERS,
                Permission.SEND_TO_SCRAP, Permission.SEND_TO_REWORK,
                Permission.ADMIN
            ]
        }
        default_role = 'Operator'
        with db.session.no_autoflush:
            for name, perms in roles_map.items():
                role = Role.query.filter_by(name=name).first()
                if role is None:
                    role = Role(name=name)
                    db.session.add(role)
                role.reset_permissions()
                for perm in perms:
                    role.add_permission(perm)
                role.default = (role.name == default_role)
        db.session.commit()

    def __repr__(self):
        return f'<Role {self.name}>'


class User(UserMixin, db.Model):
    """Модель для пользователей системы."""
    __tablename__ = 'Users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True, nullable=False)
    full_name = db.Column(db.String(128), nullable=True)
    password_hash = db.Column(db.String(256))
    role_id = db.Column(db.Integer, db.ForeignKey('Roles.id'))
    
    # --- НАЧАЛО ИСПРАВЛЕНИЯ: Добавляем обратные связи через back_populates ---
    role = db.relationship('Role', back_populates='users')
    audit_logs = db.relationship('AuditLog', back_populates='user')
    responsible_parts = db.relationship('Part', back_populates='responsible', foreign_keys='Part.responsible_id')
    notes = db.relationship('PartNote', back_populates='author', foreign_keys='PartNote.user_id')
    responsible_history = db.relationship('ResponsibleHistory', back_populates='user', foreign_keys='ResponsibleHistory.user_id')
    # --- КОНЕЦ ИСПРАВЛЕНИЯ ---

    def __init__(self, **kwargs):
        super(User, self).__init__(**kwargs)
        if self.role is None:
            self.role = Role.query.filter_by(default=True).first()

    def can(self, perm):
        return self.role is not None and self.role.has_permission(perm)

    def is_admin(self):
        return self.can(Permission.ADMIN)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<User {self.username}>'


class AnonymousUser(AnonymousUserMixin):
    """Класс для анонимных пользователей (не вошедших в систему)."""
    def can(self, permissions):
        return False

    def is_admin(self):
        return False