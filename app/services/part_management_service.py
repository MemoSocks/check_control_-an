# app/services/part_management_service.py

import os
from flask import current_app

# --- ИЗМЕНЕНИЕ: Исправляем пути импорта ---
from app import db
from app.models import AuditLog, ResponsibleHistory, Part
from .part_utils_service import (
    _send_websocket_notification,
    save_part_drawing,
    to_safe_key
)


def update_part_from_form(part, form, user, config):
    """
    Обновляет данные детали на основе данных из формы редактирования.
    :param part: Экземпляр Part для обновления.
    :param form: Экземпляр формы EditPartForm.
    :param user: Текущий пользователь.
    :param config: Конфигурация приложения.
    """
    changes = []
    if part.product_designation != form.product_designation.data:
        changes.append(f"Изделие: '{part.product_designation}' -> '{form.product_designation.data}'")
        part.product_designation = form.product_designation.data
    if part.name != form.name.data:
        changes.append(f"Наименование: '{part.name}' -> '{form.name.data}'")
        part.name = form.name.data
    if part.material != form.material.data:
        changes.append(f"Материал: '{part.material}' -> '{form.material.data}'")
        part.material = form.material.data
    if part.size != form.size.data:
        changes.append(f"Размер: '{part.size}' -> '{form.size.data}'")
        part.size = form.size.data
        
    if form.drawing.data:
        if part.drawing_filename:
            old_file_path = os.path.join(config['DRAWING_UPLOAD_FOLDER'], part.drawing_filename)
            if os.path.exists(old_file_path):
                os.remove(old_file_path)
        part.drawing_filename = save_part_drawing(form.drawing.data, config)
        changes.append("Обновлен чертеж.")
        
    if changes:
        log_details = "; ".join(changes)
        db.session.add(AuditLog(part_id=part.part_id, user_id=user.id, action="Редактирование", details=log_details, category='part'))
        db.session.commit()
        
        _send_websocket_notification(
            'part_updated',
            f"Пользователь {user.username} обновил данные детали {part.part_id}",
            data={
                'part_id': part.part_id,
                'name': part.name,
                'material': part.material,
                'size': part.size
            }
        )


def delete_single_part(part, user, config):
    """
    Удаляет одну деталь и связанные с ней данные.
    :param part: Экземпляр Part для удаления.
    :param user: Текущий пользователь.
    :param config: Конфигурация приложения.
    """
    part_id = part.part_id
    product_designation = part.product_designation
    
    if part.drawing_filename:
        file_path = os.path.join(config['DRAWING_UPLOAD_FOLDER'], part.drawing_filename)
        if os.path.exists(file_path):
            os.remove(file_path)
            
    db.session.add(AuditLog(part_id=part_id, user_id=user.id, action="Удаление", details=f"Деталь '{part_id}' и вся ее история были удалены.", category='part'))
    db.session.delete(part)
    db.session.commit()
    
    _send_websocket_notification(
        'part_deleted',
        f"Пользователь {user.username} удалил деталь: {part_id}",
        data={
            'part_id': part_id,
            'product_designation': product_designation,
            'safe_key': to_safe_key(product_designation)
        }
    )


def delete_multiple_parts(part_ids, user, config):
    """
    Массово удаляет детали по списку их ID.
    :param part_ids: Список ID деталей для удаления.
    :param user: Текущий пользователь.
    :param config: Конфигурация приложения.
    :return: Количество удаленных деталей.
    """
    parts_to_delete = db.session.query(Part).filter(Part.part_id.in_(part_ids)).all()
    deleted_count = 0
    deleted_data = []

    for part in parts_to_delete:
        if part.drawing_filename:
            file_path = os.path.join(config['DRAWING_UPLOAD_FOLDER'], part.drawing_filename)
            if os.path.exists(file_path):
                os.remove(file_path)
        
        deleted_data.append({'part_id': part.part_id, 'product_designation': part.product_designation})
        db.session.add(AuditLog(part_id=part.part_id, user_id=user.id, action="Массовое удаление", details=f"Деталь '{part.part_id}' удалена.", category='part'))
        db.session.delete(part)
        deleted_count += 1
        
    db.session.commit()
    
    if deleted_count > 0:
        _send_websocket_notification(
            'bulk_delete',
            f"Пользователь {user.username} удалил {deleted_count} деталей.",
            data={'deleted_parts': deleted_data}
        )
        
    return deleted_count


def change_part_route(part, new_route, user):
    """
    Изменяет технологический маршрут для детали.
    :param part: Экземпляр Part.
    :param new_route: Экземпляр RouteTemplate.
    :param user: Текущий пользователь.
    :return: True, если изменения были, иначе False.
    """
    if part.route_template_id != new_route.id:
        old_route_name = part.route_template.name if part.route_template else "Не назначен"
        part.route_template_id = new_route.id
        db.session.add(AuditLog(part_id=part.part_id, user_id=user.id, action="Редактирование", details=f"Маршрут изменен с '{old_route_name}' на '{new_route.name}'.", category='part'))
        db.session.commit()
        _send_websocket_notification('part_updated', f"Для детали {part.part_id} изменен маршрут.", {'part_id': part.part_id})
        return True
    return False


def change_responsible_user(part, new_user, current_user):
    """
    Изменяет ответственного пользователя для детали.
    :param part: Экземпляр Part.
    :param new_user: Экземпляр User (может быть None).
    :param current_user: Текущий аутентифицированный пользователь.
    :return: True, если изменения были, иначе False.
    """
    old_responsible_id = part.responsible_id
    new_responsible_id = new_user.id if new_user else None
    
    if old_responsible_id != new_responsible_id:
        old_user_name = part.responsible.username if part.responsible else "Не назначен"
        new_user_name = new_user.username if new_user else "Не назначен"
        part.responsible_id = new_responsible_id
        
        db.session.add(ResponsibleHistory(part_id=part.part_id, user_id=new_responsible_id))
        db.session.add(AuditLog(part_id=part.part_id, user_id=current_user.id, action="Смена ответственного", details=f"Ответственный изменен с '{old_user_name}' на '{new_user_name}'.", category='management'))
        db.session.commit()
        
        _send_websocket_notification(
            'part_updated',
            f"Для детали {part.part_id} сменен ответственный.",
            data={'part_id': part.part_id, 'responsible_user': new_user_name}
        )
        return True
    return False