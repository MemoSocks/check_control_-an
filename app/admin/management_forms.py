# app/admin/management_forms.py

from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import (StringField, BooleanField, SubmitField, SelectMultipleField,
                     IntegerField, ValidationError)
from wtforms.validators import DataRequired, NumberRange

# --- ИЗМЕНЕНИЕ: Обновляем импорт, чтобы он соответствовал новой структуре моделей ---
from app.models import RouteTemplate, Stage


class FileUploadForm(FlaskForm):
    """Форма для загрузки файла (Excel/CSV) для массового импорта."""
    file = FileField(
        'Excel/CSV-файл',
        validators=[FileRequired(), FileAllowed(['xlsx', 'xls', 'csv'])]
    )
    submit = SubmitField('Загрузить и импортировать')


class GenerateFromCloudForm(FlaskForm):
    """Форма для генерации Word-отчета из данных облачного Excel-файла."""
    excel_path = StringField(
        'Путь к Excel-файлу в OneDrive',
        validators=[DataRequired()]
    )
    row_number = IntegerField(
        'Номер строки для обработки',
        validators=[DataRequired(), NumberRange(min=2)]
    )
    word_template = FileField(
        'Файл шаблона Word (.docx)',
        validators=[FileRequired(), FileAllowed(['docx'])]
    )
    submit = SubmitField('Сгенерировать документ')


class StageDictionaryForm(FlaskForm):
    """Форма для создания/редактирования этапа в справочнике."""
    name = StringField('Название этапа', validators=[DataRequired()])
    can_scrap = BooleanField('Можно отправить в брак с этого этапа')
    can_rework = BooleanField('Можно отправить на доработку с этого этапа')
    submit = SubmitField('Сохранить')


class RouteTemplateForm(FlaskForm):
    """Форма для создания/редактирования шаблона технологического маршрута."""
    name = StringField('Название шаблона маршрута', validators=[DataRequired()])
    is_default = BooleanField('Использовать по умолчанию для новых деталей (при импорте)')
    stages = SelectMultipleField(
        'Этапы',
        coerce=int,
        validators=[DataRequired(message="В маршруте должен быть как минимум один этап.")]
    )
    submit = SubmitField('Сохранить маршрут')

    def __init__(self, *args, **kwargs):
        """
        Конструктор формы.
        `obj` используется для передачи редактируемого объекта для валидации.
        Динамически заполняет поле `stages` актуальными данными из БД.
        """
        self.obj = kwargs.get('obj')
        super(RouteTemplateForm, self).__init__(*args, **kwargs)
        self.stages.choices = [(s.id, s.name) for s in Stage.query.order_by('name').all()]

    def validate_name(self, name):
        """Проверяет уникальность названия шаблона маршрута."""
        query = RouteTemplate.query.filter(RouteTemplate.name == name.data)
        # Если мы редактируем объект, его нужно исключить из проверки
        if self.obj and self.obj.id:
            query = query.filter(RouteTemplate.id != self.obj.id)
        if query.first():
            raise ValidationError('Шаблон с таким названием уже существует.')