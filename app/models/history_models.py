# app/models/history_models.py

import enum
from datetime import datetime, timezone
from app import db


class StatusType(enum.Enum):
    """Перечисление для типов записей в истории статусов."""
    COMPLETED = 'completed'
    REWORK = 'rework'
    SCRAPPED = 'scrapped'


class StatusHistory(db.Model):
    """Хранит историю прохождения деталью производственных этапов."""
    __tablename__ = 'StatusHistory'
    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.String, db.ForeignKey('Parts.part_id'), nullable=False, index=True)
    status = db.Column(db.String, nullable=False)
    operator_name = db.Column(db.String, nullable=False)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    quantity = db.Column(db.Integer, nullable=False, default=1, server_default='1')
    status_type = db.Column(db.Enum(StatusType), nullable=False, default=StatusType.COMPLETED)
    comment = db.Column(db.Text, nullable=True)
    
    # --- НАЧАЛО ИСПРАВЛЕНИЯ: Заменяем backref на back_populates ---
    part = db.relationship('Part', back_populates='history')
    # --- КОНЕЦ ИСПРАВЛЕНИЯ ---

    def __repr__(self):
        return f'<StatusHistory part={self.part_id} status={self.status}>'


class AuditLog(db.Model):
    """Хранит журнал всех значимых действий в системе."""
    __tablename__ = 'AuditLogs'
    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.String, nullable=True, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id', ondelete='SET NULL'), nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(50), nullable=False, default='general', server_default='general', index=True)
    
    # --- НАЧАЛО ИСПРАВЛЕНИЯ: Добавляем явную связь ---
    user = db.relationship('User', back_populates='audit_logs')
    # --- КОНЕЦ ИСПРАВЛЕНИЯ ---


class PartNote(db.Model):
    """Модель для хранения текстовых примечаний к деталям."""
    __tablename__ = 'PartNotes'
    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.String, db.ForeignKey('Parts.part_id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=False)
    stage_id = db.Column(db.Integer, db.ForeignKey('Stages.id'), nullable=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    text = db.Column(db.Text, nullable=False)

    # --- НАЧАЛО ИСПРАВЛЕНИЯ: Заменяем backref на back_populates ---
    part = db.relationship('Part', back_populates='notes')
    author = db.relationship('User', back_populates='notes', foreign_keys=[user_id])
    stage = db.relationship('Stage', back_populates='notes')
    # --- КОНЕЦ ИСПРАВЛЕНИЯ ---


class ResponsibleHistory(db.Model):
    """Хранит историю смены ответственных за деталь."""
    __tablename__ = 'ResponsibleHistory'
    id = db.Column(db.Integer, primary_key=True)
    part_id = db.Column(db.String, db.ForeignKey('Parts.part_id'), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=True, index=True)
    timestamp = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # --- НАЧАЛО ИСПРАВЛЕНИЯ: Заменяем backref на back_populates ---
    part = db.relationship('Part', back_populates='responsible_history')
    user = db.relationship('User', back_populates='responsible_history', foreign_keys=[user_id])
    # --- КОНЕЦ ИСПРАВЛЕНИЯ ---