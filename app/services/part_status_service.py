# app/services/part_status_service.py

from collections import defaultdict
from flask import render_template_string

# --- ИЗМЕНЕНИЕ: Исправляем пути импорта ---
from app import db
from app.models import StatusHistory, StatusType, AuditLog
from .part_utils_service import _send_websocket_notification


def _recalculate_part_progress(part):
    """
    Вспомогательная функция для пересчета общего прогресса выполнения детали.
    Находит минимальное количество выполненных изделий по всем этапам маршрута.
    """
    if not part.route_template:
        part.quantity_completed = 0
        return

    all_history = StatusHistory.query.filter_by(
        part_id=part.part_id, status_type=StatusType.COMPLETED
    ).all()
    
    completed_quantities = defaultdict(int)
    for h in all_history:
        completed_quantities[h.status] += h.quantity
        
    stage_names = [rs.stage.name for rs in sorted(part.route_template.stages, key=lambda s: s.order)]
    
    if not stage_names:
        part.quantity_completed = 0
        return

    min_completed = part.quantity_total
    for stage_name in stage_names:
        qty = completed_quantities.get(stage_name, 0)
        if qty < min_completed:
            min_completed = qty
            
    part.quantity_completed = min_completed


def complete_stage(part, stage, quantity, operator_name):
    """
    Обрабатывает успешное завершение этапа для указанного количества деталей.
    :param part: Экземпляр Part.
    :param stage: Экземпляр Stage.
    :param quantity: Количество выполненных изделий.
    :param operator_name: Имя оператора.
    """
    db.session.add(StatusHistory(
        part_id=part.part_id,
        status=stage.name,
        operator_name=operator_name,
        quantity=quantity,
        status_type=StatusType.COMPLETED
    ))
    
    part.current_status = stage.name
    _recalculate_part_progress(part)
    
    db.session.commit()


def scrap_part(part, stage, quantity, user, comment):
    """
    Обрабатывает отправку деталей в брак.
    :param part: Экземпляр Part.
    :param stage: Экземпляр Stage, на котором обнаружен брак.
    :param quantity: Количество бракованных изделий.
    :param user: Пользователь, отправивший в брак.
    :param comment: Причина брака.
    """
    # Сбрасываем историю, так как партия больше не в работе
    StatusHistory.query.filter_by(part_id=part.part_id).delete()
    
    part.quantity_scrapped = (part.quantity_scrapped or 0) + quantity
    part.quantity_completed = 0
    part.current_status = "В браке"
    
    db.session.add(StatusHistory(
        part_id=part.part_id,
        status=stage.name,
        operator_name=user.full_name or user.username,
        quantity=quantity,
        status_type=StatusType.SCRAPPED,
        comment=comment
    ))
    
    db.session.add(AuditLog(
        part_id=part.part_id,
        user_id=user.id,
        action="Отправка в брак",
        details=f"Этап: {stage.name}. Причина: {comment}",
        category='part'
    ))
    
    db.session.commit()
    _send_websocket_notification('part_updated', f"Деталь {part.part_id} отправлена в брак.", {'part_id': part.part_id})


def rework_part(part, current_stage, quantity, user, comment):
    """
    Обрабатывает отправку деталей на доработку на предыдущий этап.
    :param part: Экземпляр Part.
    :param current_stage: Текущий этап, с которого отправляют на доработку.
    :param quantity: Количество изделий на доработку.
    :param user: Пользователь, отправивший на доработку.
    :param comment: Причина доработки.
    """
    if not part.route_template:
        raise ValueError("У детали нет маршрута для доработки.")

    ordered_stages = sorted(part.route_template.stages, key=lambda s: s.order)
    current_stage_index = next((i for i, rs in enumerate(ordered_stages) if rs.stage_id == current_stage.id), -1)
            
    if current_stage_index <= 0:
        raise ValueError("Невозможно отправить на доработку с первого или несуществующего этапа.")

    # Определяем этап, на который нужно вернуться
    rework_to_stage = ordered_stages[current_stage_index - 1].stage
    # Определяем этапы, историю которых нужно "откатить"
    stages_to_revert_names = [rs.stage.name for rs in ordered_stages[current_stage_index-1:]]
    
    # Удаляем историю для откатываемых этапов
    StatusHistory.query.filter(
        StatusHistory.part_id == part.part_id,
        StatusHistory.status.in_(stages_to_revert_names)
    ).delete()

    part.current_status = f"Доработка ({rework_to_stage.name})"
    
    # Добавляем запись о самой доработке
    db.session.add(StatusHistory(
        part_id=part.part_id,
        status=current_stage.name,
        operator_name=user.full_name or user.username,
        quantity=quantity,
        status_type=StatusType.REWORK,
        comment=comment
    ))
    
    db.session.add(AuditLog(
        part_id=part.part_id,
        user_id=user.id,
        action="Отправка на доработку",
        details=f"Возврат на этап '{rework_to_stage.name}'. Причина: {comment}",
        category='part'
    ))
    
    _recalculate_part_progress(part)
    db.session.commit()
    
    _send_websocket_notification('part_updated', f"Деталь {part.part_id} отправлена на доработку.", {'part_id': part.part_id})


def cancel_stage_by_history_id(history_id, user):
    """
    Отменяет одну запись в истории статусов и пересчитывает прогресс.
    :param history_id: ID записи в StatusHistory для удаления.
    :param user: Пользователь, выполняющий отмену.
    :return: Кортеж (объект Part, имя отмененного этапа).
    """
    history_entry = db.get_or_404(StatusHistory, history_id)
    part = history_entry.part
    stage_name = history_entry.status
    
    db.session.add(AuditLog(
        part_id=part.part_id,
        user_id=user.id,
        action="Отмена этапа",
        details=f"Отменен этап: '{stage_name}' ({history_entry.quantity} шт.).",
        category='part'
    ))
    
    db.session.delete(history_entry)
    db.session.flush() # Применяем удаление, чтобы пересчет был корректным
    
    _recalculate_part_progress(part)
    
    # Обновляем текущий статус детали на основе последней записи в истории
    new_last_history = StatusHistory.query.filter_by(
        part_id=part.part_id
    ).order_by(StatusHistory.timestamp.desc()).first()
    
    part.current_status = new_last_history.status if new_last_history else 'На складе'
    
    db.session.commit()

    # Рендерим новый HTML для прогресс-бара для отправки по WebSocket
    progress_html = render_template_string(
        """
        <div class="w-full bg-gray-200 rounded-full h-2.5">
            <div class="bg-blue-600 h-2.5 rounded-full" style="width: {{ (part.quantity_completed / part.quantity_total * 100)|int }}%"></div>
        </div>
        <small>{{ part.quantity_completed }} из {{ part.quantity_total }}</small>
        """,
        part=part
    )
    
    _send_websocket_notification(
        'stage_completed',
        f"Для детали {part.part_id} отменен этап '{stage_name}'.",
        data={'part_id': part.part_id, 'progress_html': progress_html}
    )
    
    return part, stage_name