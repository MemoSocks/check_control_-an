# app/services/part_creation_service.py

from flask import current_app
from sqlalchemy.exc import IntegrityError

from app import db
from app.models import Part, AuditLog, AssemblyComponent
from .part_utils_service import (
    _send_websocket_notification, 
    save_part_drawing, 
    _render_part_row_html
)


def create_single_part(form, user, config):
    """
    Создает одну деталь на основе данных из формы.
    :param form: Экземпляр формы PartForm.
    :param user: Текущий пользователь.
    :param config: Конфигурация приложения.
    """
    drawing_filename = save_part_drawing(form.drawing.data, config) if form.drawing.data else None
    
    # --- НАЧАЛО ИСПРАВЛЕНИЯ: Получаем ID из объекта RouteTemplate ---
    # QuerySelectField возвращает полный объект, а нам нужен только его ID для записи в БД.
    route_template_id = form.route_template.data.id if form.route_template.data else None
    # --- КОНЕЦ ИСПРАВЛЕНИЯ ---

    new_part = Part(
        part_id=form.part_id.data,
        product_designation=form.product.data,
        name=form.name.data,
        material=form.material.data,
        size=form.size.data,
        route_template_id=route_template_id, # Используем ID
        drawing_filename=drawing_filename,
        quantity_total=form.quantity_total.data
    )
    
    db.session.add(new_part)
    log_entry = AuditLog(
        part_id=new_part.part_id,
        user_id=user.id,
        action="Создание",
        details="Деталь создана вручную.",
        category='part'
    )
    db.session.add(log_entry)
    
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise
    
    with current_app.app_context():
        part_html = _render_part_row_html(new_part, user)
    
    _send_websocket_notification(
        'part_created',
        f"Пользователь {user.username} создал деталь: {new_part.part_id}",
        data={
            'part_id': new_part.part_id,
            'product_designation': new_part.product_designation,
            'html': part_html
        }
    )


def create_child_part(form, parent_part_id, user):
    """
    Создает дочернюю деталь (узел/компонент) и связывает ее с родителем.
    :param form: Экземпляр формы AddChildPartForm.
    :param parent_part_id: ID родительской детали.
    :param user: Текущий пользователь.
    """
    parent_part = db.get_or_404(Part, parent_part_id)

    new_part = Part(
        part_id=form.part_id.data,
        product_designation=parent_part.product_designation,
        name=form.name.data,
        material=form.material.data,
        quantity_total=1,
        route_template_id=parent_part.route_template_id
    )
    db.session.add(new_part)

    component_link = AssemblyComponent(
        parent_id=parent_part_id,
        child_id=form.part_id.data,
        quantity=form.quantity_total.data
    )
    db.session.add(component_link)

    log_entry = AuditLog(
        part_id=parent_part_id,
        user_id=user.id,
        action="Обновление состава",
        details=f"В состав '{parent_part.name}' добавлен узел '{new_part.name}' ({form.quantity_total.data} шт.).",
        category='part'
    )
    db.session.add(log_entry)

    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise

    _send_websocket_notification(
        'part_updated',
        f"В состав изделия {parent_part.part_id} добавлен новый узел.",
        data={'part_id': parent_part.part_id}
    )