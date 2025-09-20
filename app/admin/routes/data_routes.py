# app/admin/routes/data_routes.py

from flask import (Blueprint, render_template, flash, redirect, url_for,
                   current_app)
from flask_login import current_user

from app import db
# --- ИЗМЕНЕНИЕ: Обновляем импорт, чтобы он соответствовал новой структуре моделей ---
from app.models import Part, Permission, RouteTemplate
from app.admin.management_forms import FileUploadForm
from app.admin.part_forms import PartForm
from app.services import part_import_export_service as pies
from app.admin.utils import permission_required

data_bp = Blueprint('data', __name__)


@data_bp.route('/')
@permission_required(Permission.ADD_PARTS)
def data_management():
    """Отображает главную страницу раздела импорта/экспорта."""
    upload_form = FileUploadForm()
    part_form = PartForm()
    # Динамически заполняем выпадающий список маршрутов в форме
    part_form.route_template.choices = [
        (rt.id, rt.name) for rt in RouteTemplate.query.order_by(RouteTemplate.name).all()
    ]
    
    return render_template(
        'data_management.html',
        upload_form=upload_form,
        part_form=part_form,
        title="Работа с данными"
    )


@data_bp.route('/upload_excel', methods=['POST'])
@permission_required(Permission.ADD_PARTS)
def upload_excel():
    """Обрабатывает загрузку и импорт деталей из Excel-файла."""
    form = FileUploadForm()
    if form.validate_on_submit():
        try:
            # Вызываем сервис для импорта
            added, skipped = pies.import_parts_from_excel(
                form.file.data, current_user
            )
            flash(f"Импорт завершен. Добавлено: {added}, пропущено дубликатов: {skipped}.", 'success')
        except ValueError as e:
            flash(f"Ошибка валидации: {e}", 'error')
        except Exception as e:
            flash(f"Произошла ошибка при обработке файла: {e}", 'error')
            current_app.logger.error(f"Excel import error: {e}", exc_info=True)
    else:
        # Обрабатываем ошибки валидации самой формы
        for field, errors in form.errors.items():
            for error in errors:
                flash(f"Ошибка в поле '{getattr(form, field).label.text}': {error}", 'error')

    return redirect(url_for('admin.data.data_management'))


@data_bp.route('/export_parts')
@permission_required(Permission.ADD_PARTS)
def export_parts():
    """
    Формирует и отдает CSV-файл со списком всех деталей в базе данных.
    """
    # Вызываем сервис для экспорта
    csv_stream = pies.export_all_parts_to_csv()

    if not csv_stream:
        flash("В базе данных нет деталей для экспорта.", "warning")
        return redirect(url_for('admin.data.data_management'))

    # Формируем HTTP-ответ с файлом
    from flask import Response
    from datetime import datetime
    
    return Response(
        csv_stream.getvalue(),
        mimetype="text/csv",
        headers={
            "Content-disposition": f"attachment; filename=full_parts_export_{datetime.now().strftime('%Y-%m-%d')}.csv"
        }
    )