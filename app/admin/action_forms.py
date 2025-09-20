# app/admin/action_forms.py

from flask_wtf import FlaskForm
from wtforms import (StringField, IntegerField, TextAreaField,
                     HiddenField, SubmitField)
from wtforms.validators import DataRequired, Optional, Length, NumberRange
from wtforms_sqlalchemy.fields import QuerySelectField

# --- ИЗМЕНЕНИЕ: Обновляем импорт, чтобы он соответствовал новой структуре моделей ---
from app.models import RouteTemplate, Stage, User


# --- Фабрики для полей QuerySelectField ---

def get_route_templates():
    """Возвращает все шаблоны маршрутов для выпадающего списка."""
    return RouteTemplate.query.order_by(RouteTemplate.name).all()

def get_stages():
    """Возвращает все этапы из справочника для выпадающего списка."""
    return Stage.query.order_by(Stage.name).all()

def get_all_users():
    """Возвращает всех пользователей для выпадающего списка."""
    return User.query.order_by(User.username).all()


# --- Формы для выполнения действий ---

class ConfirmStageQuantityForm(FlaskForm):
    """Форма для подтверждения выполнения этапа на странице сканирования."""
    quantity = IntegerField(
        'Количество',
        validators=[DataRequired(), NumberRange(min=1)]
    )
    operator_name = StringField(
        'Ваше ФИО',
        validators=[Optional(), Length(min=3)]
    )
    action = HiddenField('Действие', default='completed')
    submit = SubmitField('Подтвердить')


class ReworkScrapForm(FlaskForm):
    """Форма для отправки в брак или на доработку."""
    quantity = IntegerField(
        'Количество',
        validators=[DataRequired(), NumberRange(min=1)]
    )
    comment = TextAreaField(
        'Причина (обязательно)',
        validators=[DataRequired(), Length(min=5)]
    )
    action = HiddenField('Действие')
    submit = SubmitField('Отправить')


class AddNoteForm(FlaskForm):
    """Форма для добавления примечания к детали."""
    stage = QuerySelectField(
        'Привязать к этапу (необязательно)',
        query_factory=get_stages,
        get_label='name',
        allow_blank=True,
        blank_text='-- Общее примечание --'
    )
    text = TextAreaField('Текст примечания', validators=[DataRequired()])
    submit = SubmitField('Добавить примечание')


class ChangeRouteForm(FlaskForm):
    """Форма для смены технологического маршрута детали."""
    new_route = QuerySelectField(
        'Новый технологический маршрут',
        query_factory=get_route_templates,
        get_label='name',
        allow_blank=False
    )
    submit = SubmitField('Сохранить новый маршрут')


class ChangeResponsibleForm(FlaskForm):
    """Форма для смены ответственного за деталь."""
    responsible = QuerySelectField(
        'Назначить ответственного',
        query_factory=get_all_users,
        get_label='username',
        allow_blank=True,
        blank_text='-- Не назначен --'
    )
    submit = SubmitField('Сохранить')


class ConfirmForm(FlaskForm):
    """
    Пустая форма, используемая для простых POST-запросов,
    которые требуют только CSRF-защиты (например, удаление, генерация QR).
    """
    pass