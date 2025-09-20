# app/models/route_models.py

from app import db


class Stage(db.Model):
    """Модель для справочника производственных этапов."""
    __tablename__ = 'Stages'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    
    can_scrap = db.Column(db.Boolean, nullable=False, default=True, server_default='true')
    can_rework = db.Column(db.Boolean, nullable=False, default=True, server_default='true')

    # --- НАЧАЛО ИСПРАВЛЕНИЯ: Добавляем обратную связь ---
    # Связь, на которую ссылается PartNote.stage
    notes = db.relationship('PartNote', back_populates='stage')
    # --- КОНЕЦ ИСПРАВЛЕНИЯ ---

    def __repr__(self):
        return f'<Stage {self.name}>'


class RouteTemplate(db.Model):
    """
    Модель для шаблона технологического маршрута, который является
    упорядоченным набором этапов (Stage).
    """
    __tablename__ = 'RouteTemplates'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    is_default = db.Column(db.Boolean, default=False, index=True)
    
    stages = db.relationship('RouteStage', back_populates='template', cascade="all, delete-orphan")

    # --- НАЧАЛО ИСПРАВЛЕНИЯ: Добавляем обратную связь ---
    # Связь, на которую ссылается Part.route_template
    parts = db.relationship('Part', back_populates='route_template')
    # --- КОНЕЦ ИСПРАВЛЕНИЯ ---

    def __repr__(self):
        return f'<RouteTemplate {self.name}>'


class RouteStage(db.Model):
    """
    Ассоциативная таблица, связывающая маршруты (RouteTemplate) и этапы (Stage),
    а также определяющая порядок этапов в маршруте.
    """
    __tablename__ = 'RouteStages'
    id = db.Column(db.Integer, primary_key=True)
    template_id = db.Column(db.Integer, db.ForeignKey('RouteTemplates.id'), nullable=False)
    stage_id = db.Column(db.Integer, db.ForeignKey('Stages.id'), nullable=False)
    order = db.Column(db.Integer, nullable=False)
    
    template = db.relationship('RouteTemplate', back_populates='stages')
    
    # --- НАЧАЛО ИСПРАВЛЕНИЯ: Используем back_populates для единообразия ---
    stage = db.relationship('Stage')
    # --- КОНЕЦ ИСПРАВЛЕНИЯ ---
    
    def __repr__(self):
        return f'<RouteStage template={self.template_id} stage={self.stage_id} order={self.order}>'