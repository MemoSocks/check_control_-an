# app/main/api_routes.py

from flask import Blueprint, jsonify, request, url_for
from sqlalchemy.orm import joinedload
from collections import defaultdict

from app import db
from flask_login import current_user
# --- ИЗМЕНЕНИЕ: Обновляем импорт, чтобы он соответствовал новой структуре моделей ---
from app.models import Part, RouteTemplate, RouteStage, Permission, StatusType

# Создаем новый блюпринт специально для API
api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/parts/<path:product_designation>')
def parts_for_product(product_designation):
    """
    API-эндпоинт для динамической загрузки списка деталей для конкретного изделия
    с поддержкой поиска и фильтрации.
    """
    # Начинаем строить запрос к БД
    query = Part.query.options(
        # Жадная загрузка связанных данных для минимизации запросов
        joinedload(Part.route_template).joinedload(RouteTemplate.stages).joinedload(RouteStage.stage),
        joinedload(Part.responsible),
        joinedload(Part.history) # Явно подгружаем историю для расчета прогресса
    ).filter(
        Part.product_designation == product_designation,
        ~Part.parent_associations.any()  # Выбираем только верхнеуровневые детали
    )

    # Применяем фильтр поиска, если он есть в параметрах запроса
    search_term = request.args.get('search')
    if search_term:
        search_filter = f"%{search_term}%"
        query = query.filter(
            db.or_(
                Part.part_id.ilike(search_filter),
                Part.name.ilike(search_filter),
                Part.material.ilike(search_filter)
            )
        )
    
    # Применяем фильтр по ответственному, если он есть
    responsible_id = request.args.get('responsible_id')
    if responsible_id and responsible_id.isdigit():
        query = query.filter(Part.responsible_id == int(responsible_id))

    # Выполняем запрос
    parts_from_query = query.order_by(Part.part_id.asc()).all()

    # Формируем список словарей для JSON-ответа
    parts_list = []
    for part in parts_from_query:
        route_stages_data = []
        if part.route_template:
            # Считаем прогресс по каждому этапу
            completed_quantities = defaultdict(int)
            for h in part.history:
                if h.status_type == StatusType.COMPLETED:
                    completed_quantities[h.status] += h.quantity

            ordered_stages = sorted(part.route_template.stages, key=lambda s: s.order)
            
            for rs in ordered_stages:
                stage_name = rs.stage.name
                qty_done = completed_quantities.get(stage_name, 0)
                status = 'pending'
                if qty_done >= part.quantity_total:
                    status = 'completed'
                elif qty_done > 0:
                    status = 'in_progress'
                
                route_stages_data.append({
                    'name': stage_name,
                    'status': status,
                    'qty_done': qty_done
                })
        
        parts_list.append({
            'part_id': part.part_id,
            'name': part.name,
            'material': part.material,
            'size': part.size,
            'current_status': part.current_status,
            'creation_date': part.date_added.strftime('%Y-%m-%d'),
            'quantity_completed': part.quantity_completed,
            'quantity_total': part.quantity_total,
            'history_url': url_for('main.history', part_id=part.part_id),
            'route_stages': route_stages_data,
            'delete_url': url_for('admin.part.delete_part', part_id=part.part_id),
            'edit_url': url_for('admin.part.edit_part', part_id=part.part_id),
            'qr_url': url_for('admin.part.generate_single_qr', part_id=part.part_id),
            'responsible_user': part.responsible.username if part.responsible else 'Не назначен'
        })

    # Определяем права текущего пользователя для передачи на фронтенд
    permissions = {
        'can_delete': current_user.can(Permission.DELETE_PARTS),
        'can_edit': current_user.can(Permission.EDIT_PARTS),
        'can_generate_qr': current_user.can(Permission.GENERATE_QR)
    } if current_user.is_authenticated else None

    return jsonify({'parts': parts_list, 'permissions': permissions})