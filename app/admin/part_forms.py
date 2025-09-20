# app/admin/part_forms.py

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, IntegerField, SubmitField
from wtforms.validators import DataRequired, Optional, Length, NumberRange
from wtforms_sqlalchemy.fields import QuerySelectField

from app.models import RouteTemplate


def get_route_templates():
    """Фабрика для QuerySelectField, возвращает все шаблоны маршрутов."""
    return RouteTemplate.query.order_by(RouteTemplate.name).all()


class PartForm(FlaskForm):
    """Форма для добавления новой основной детали (партии)."""
    product = StringField(
        'Изделие (напр. "Наборка №3")', 
        validators=[DataRequired(), Length(max=100)]
    )
    part_id = StringField(
        'Обозначение (Артикул)', 
        validators=[DataRequired(), Length(max=100)]
    )
    name = StringField(
        'Наименование', 
        validators=[DataRequired(), Length(max=150)]
    )
    material = StringField(
        'Материал (из колонки "Прим.")', 
        validators=[DataRequired(), Length(max=150)]
    )
    size = StringField(
        'Размер (необязательно)', 
        validators=[Optional(), Length(max=100)]
    )
    quantity_total = IntegerField(
        'Общее количество в партии', 
        default=1, 
        validators=[DataRequired(), NumberRange(min=1)]
    )
    route_template = QuerySelectField(
        'Технологический маршрут', 
        query_factory=get_route_templates,
        get_label='name',
        allow_blank=False,
        validators=[DataRequired()]
    )
    drawing = FileField(
        'Чертеж (изображение, необязательно)', 
        validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'gif'])]
    )
    submit = SubmitField('Добавить деталь')


class EditPartForm(FlaskForm):
    """Форма для редактирования основной информации о детали."""
    product_designation = StringField(
        'Изделие', 
        validators=[DataRequired(), Length(max=100)]
    )
    name = StringField(
        'Наименование', 
        validators=[DataRequired(), Length(max=150)]
    )
    # --- НАЧАЛО ИСПРАВЛЕНИЯ: Добавляем поля для редактирования ---
    material = StringField(
        'Материал', 
        validators=[DataRequired(), Length(max=150)]
    )
    size = StringField(
        'Размер', 
        validators=[Optional(), Length(max=100)]
    )
    # --- КОНЕЦ ИСПРАВЛЕНИЯ ---
    drawing = FileField(
        'Заменить чертеж (необязательно)', 
        validators=[Optional(), FileAllowed(['jpg', 'jpeg', 'png', 'gif'])]
    )
    submit = SubmitField('Сохранить изменения')


class AddChildPartForm(FlaskForm):
    """Форма для добавления дочернего узла/компонента в состав изделия."""
    part_id = StringField(
        'Обозначение узла/компонента', 
        validators=[DataRequired(), Length(max=100)]
    )
    name = StringField(
        'Наименование узла/компонента', 
        validators=[DataRequired(), Length(max=150)]
    )
    material = StringField(
        'Материал', 
        validators=[DataRequired(), Length(max=150)]
    )
    quantity_total = IntegerField(
        'Количество в составе родителя', 
        default=1, 
        validators=[DataRequired(), NumberRange(min=1)]
    )
    submit = SubmitField('Добавить узел')