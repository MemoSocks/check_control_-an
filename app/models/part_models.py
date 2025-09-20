# app/models/part_models.py

from datetime import datetime, timezone
from app import db


class AssemblyComponent(db.Model):
    """
    Ассоциативная таблица для структуры "Изделие-Компонент" (M-N связь).
    Определяет, из каких дочерних деталей (child) и в каком количестве (quantity)
    состоит родительская сборка (parent).
    """
    __tablename__ = 'AssemblyComponents'
    parent_id = db.Column(db.String, db.ForeignKey('Parts.part_id'), primary_key=True)
    child_id = db.Column(db.String, db.ForeignKey('Parts.part_id'), primary_key=True)
    quantity = db.Column(db.Integer, nullable=False, default=1)

    # --- НАЧАЛО ИСПРАВЛЕНИЯ: Возвращаем back_populates со строковым именем класса ---
    child = db.relationship("Part", foreign_keys=[child_id], back_populates="parent_associations")
    parent = db.relationship("Part", foreign_keys=[parent_id], back_populates="child_associations")
    # --- КОНЕЦ ИСПРАВЛЕНИЯ ---


class Part(db.Model):
    """Основная модель, представляющая деталь, изделие или узел."""
    __tablename__ = 'Parts'
    
    # Основные идентификаторы
    part_id = db.Column(db.String, primary_key=True)
    product_designation = db.Column(db.String, nullable=False, index=True)
    
    # Описательные поля
    name = db.Column(db.String(150), nullable=False)
    material = db.Column(db.String(150), nullable=False)
    size = db.Column(db.String(100), nullable=True)
    drawing_filename = db.Column(db.String(255), nullable=True)
    
    # Даты и статус
    date_added = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    current_status = db.Column(db.String, default='На складе')
    last_update = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    
    # Количественные показатели
    quantity_total = db.Column(db.Integer, nullable=False, default=1, server_default='1')
    quantity_completed = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    quantity_scrapped = db.Column(db.Integer, nullable=False, default=0, server_default='0')
    
    # Внешние ключи
    route_template_id = db.Column(db.Integer, db.ForeignKey('RouteTemplates.id'), nullable=True)
    responsible_id = db.Column(db.Integer, db.ForeignKey('Users.id'), nullable=True)

    # --- НАЧАЛО ИСПРАВЛЕНИЯ: Возвращаем полноценные relationships ---
    # Прямые связи (One-to-Many)
    route_template = db.relationship('RouteTemplate', back_populates='parts')
    responsible = db.relationship('User', back_populates='responsible_parts', foreign_keys=[responsible_id])
    
    # Связи для иерархии (Many-to-Many к самой себе через AssemblyComponent)
    child_associations = db.relationship(
        'AssemblyComponent',
        foreign_keys=[AssemblyComponent.parent_id],
        back_populates='parent',
        cascade="all, delete-orphan",
        lazy='dynamic'
    )
    parent_associations = db.relationship(
        'AssemblyComponent',
        foreign_keys=[AssemblyComponent.child_id],
        back_populates='child',
        cascade="all, delete-orphan",
        lazy='dynamic'
    )
    
    # Обратные связи (Many-to-One), определены через back_populates в других моделях
    history = db.relationship("StatusHistory", back_populates="part", cascade="all, delete-orphan")
    notes = db.relationship("PartNote", back_populates="part", cascade="all, delete-orphan")
    responsible_history = db.relationship("ResponsibleHistory", back_populates="part", cascade="all, delete-orphan")
    # --- КОНЕЦ ИСПРАВЛЕНИЯ ---

    def __repr__(self):
        return f'<Part {self.part_id}>'