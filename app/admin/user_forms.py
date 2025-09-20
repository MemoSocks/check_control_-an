# app/admin/user_forms.py

from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField, SubmitField,
                     SelectMultipleField)
from wtforms.validators import DataRequired, Optional, Length
from wtforms_sqlalchemy.fields import QuerySelectField

# --- ИЗМЕНЕНИЕ: Обновляем импорт, чтобы он соответствовал новой структуре моделей ---
from app.models import Role, Permission


def get_roles():
    """Фабрика для QuerySelectField, возвращает все роли."""
    return Role.query.order_by(Role.name).all()


class LoginForm(FlaskForm):
    """Форма для входа пользователя в систему."""
    username = StringField('Логин', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')


class UserBaseForm(FlaskForm):
    """Базовая форма с общими полями для создания и редактирования пользователя."""
    username = StringField(
        'Имя пользователя (логин)',
        validators=[DataRequired(), Length(min=3, max=64)]
    )
    full_name = StringField(
        'ФИО',
        validators=[DataRequired(), Length(max=128)]
    )
    role = QuerySelectField(
        'Роль',
        query_factory=get_roles,
        get_label='name',
        allow_blank=False
    )


class AddUserForm(UserBaseForm):
    """Форма для создания нового пользователя."""
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Создать пользователя')


class EditUserForm(UserBaseForm):
    """Форма для редактирования существующего пользователя."""
    password = PasswordField(
        'Новый пароль (оставьте пустым, чтобы не менять)',
        validators=[Optional(), Length(min=6)]
    )
    submit = SubmitField('Сохранить изменения')


class RoleForm(FlaskForm):
    """Форма для создания/редактирования роли."""
    name = StringField('Название роли', validators=[DataRequired()])
    permissions = SelectMultipleField('Права доступа', coerce=int)
    submit = SubmitField('Сохранить роль')

    def __init__(self, *args, **kwargs):
        """
        Конструктор динамически заполняет поле `permissions`
        всеми возможными правами из модели Permission.
        """
        super(RoleForm, self).__init__(*args, **kwargs)
        self.permissions.choices = [
            (Permission.ADD_PARTS, 'Добавление изделий/деталей'),
            (Permission.EDIT_PARTS, 'Корректировка изделий/деталей'),
            (Permission.DELETE_PARTS, 'Удаление изделий/деталей'),
            (Permission.GENERATE_QR, 'Генерация QR-кодов'),
            (Permission.VIEW_AUDIT_LOG, 'Просмотр журнала аудита'),
            (Permission.MANAGE_STAGES, 'Управление справочником этапов'),
            (Permission.MANAGE_ROUTES, 'Управление маршрутами'),
            (Permission.VIEW_REPORTS, 'Просмотр отчетов'),
            (Permission.MANAGE_USERS, 'Управление пользователями'),
            (Permission.SEND_TO_SCRAP, 'Отправка в брак'),
            (Permission.SEND_TO_REWORK, 'Отправка на доработку'),
            (Permission.ADMIN, 'Полный администратор')
        ]