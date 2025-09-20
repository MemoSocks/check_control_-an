# app/main/main_routes.py

from flask import Blueprint, render_template, flash, redirect, url_for
from sqlalchemy import func
from sqlalchemy.orm import joinedload
from collections import defaultdict

from app import db
from app.models import Part, StatusHistory, Stage, RouteStage, User, StatusType
from app.admin.action_forms import ConfirmStageQuantityForm, ReworkScrapForm
from app.admin.part_forms import AddChildPartForm
from app.admin.action_forms import AddNoteForm
from app.services import query_service

# --- ИЗМЕНЕНИЕ: Переименовываем блюпринт, чтобы избежать конфликта ---
main_pages_bp = Blueprint('main_pages', __name__)


@main_pages_bp.route('/')
def dashboard():
    """
    Отображает главную страницу (панель мониторинга).
    Выполняет агрегированный запрос для отображения общего прогресса по каждому изделию.
    """
    # Запрос для получения общего прогресса по каждому изделию (только для верхнеуровневых деталей)
    product_progress_query = db.session.query(
        Part.product_designation,
        func.count(Part.part_id).label('total_parts'),
        func.sum(Part.quantity_total).label('total_quantity'),
        func.sum(Part.quantity_completed).label('completed_quantity')
    ).filter(~Part.parent_associations.any()).group_by(Part.product_designation).all()

    # Формируем список продуктов для передачи в шаблон
    products = [{
        'product_designation': row.product_designation,
        'total_parts': row.total_parts,
        'total_possible_stages': row.total_quantity or 0,
        'total_completed_stages': row.completed_quantity or 0
    } for row in product_progress_query]

    # Получаем список пользователей для фильтра "Ответственный"
    responsible_users = User.query.order_by(User.username).all()

    return render_template('dashboard.html', products=products, responsible_users=responsible_users)


@main_pages_bp.route('/history/<path:part_id>')
def history(part_id):
    """
    Отображает страницу с полной историей и составом для конкретной детали.
    """
    part = db.get_or_404(Part, part_id)
    combined_history = query_service.get_combined_history(part)
    
    # Инициализируем формы для добавления примечаний и дочерних узлов
    note_form = AddNoteForm()
    child_form = AddChildPartForm()

    # Заполняем выпадающий список этапов в форме примечаний
    if part.route_template:
        note_form.stage.query = db.session.query(Stage).join(RouteStage).filter(
            RouteStage.template_id == part.route_template_id
        ).order_by(Stage.name)
    else:
        # Если маршрута нет, делаем список пустым
        note_form.stage.query = db.session.query(Stage).filter_by(id=-1)

    return render_template(
        'history.html',
        part=part,
        combined_history=combined_history,
        note_form=note_form,
        child_form=child_form
    )


@main_pages_bp.route('/scan/<path:part_id>')
def select_stage(part_id):
    """
    Отображает страницу сканирования, предлагая следующий доступный этап
    для выполнения.
    """
    part = db.get_or_404(Part, part_id)
    if not part.route_template:
        flash('Ошибка: Этой детали не присвоен технологический маршрут.', 'error')
        return redirect(url_for('main.dashboard'))

    # Рассчитываем количество уже выполненных изделий на каждом этапе
    completed_quantities = defaultdict(int)
    for h in part.history:
        if h.status_type == StatusType.COMPLETED:
            completed_quantities[h.status] += h.quantity
        
    # Находим следующий невыполненный этап в маршруте
    ordered_stages = sorted(part.route_template.stages, key=lambda s: s.order)
    next_stage_obj = None
    for rs in ordered_stages:
        if completed_quantities.get(rs.stage.name, 0) < part.quantity_total:
            next_stage_obj = rs.stage
            break

    # Инициализируем формы
    form = ConfirmStageQuantityForm()
    rework_scrap_form = ReworkScrapForm()

    # Предзаполняем поле "количество" оставшимся количеством на этом этапе
    if next_stage_obj and form.quantity.data is None:
        completed_on_this_stage = completed_quantities.get(next_stage_obj.name, 0)
        remaining = part.quantity_total - completed_on_this_stage
        form.quantity.data = remaining if remaining > 0 else 1
        rework_scrap_form.quantity.data = remaining if remaining > 0 else 1

    return render_template(
        'select_stage.html',
        part=part,
        next_stage=next_stage_obj,
        form=form,
        rework_scrap_form=rework_scrap_form
    )