# app/services/query_service.py

from sqlalchemy.orm import joinedload
from collections import namedtuple
from itertools import groupby

from app import db
# --- ИЗМЕНЕНИЕ: Обновляем импорт, чтобы он соответствовал новой структуре моделей ---
from app.models import (PartNote, StatusHistory, ResponsibleHistory, Stage,
                        RouteStage)


def get_combined_history(part):
    """
    Собирает, объединяет и сортирует по дате всю историю, связанную с деталью:
    смену статусов, смену ответственных и примечания.
    :param part: Экземпляр Part.
    :return: Отсортированный список всех исторических событий.
    """
    # Загружаем все связанные истории одним махом для производительности
    notes = PartNote.query.options(joinedload(PartNote.author), joinedload(PartNote.stage)).filter_by(part_id=part.part_id).all()
    status_changes = StatusHistory.query.filter_by(part_id=part.part_id).all()
    responsible_changes = ResponsibleHistory.query.options(joinedload(ResponsibleHistory.user)).filter_by(part_id=part.part_id).all()

    combined = []
    
    # Добавляем примечания
    for note in notes:
        combined.append({
            'type': 'note',
            'timestamp': note.timestamp,
            'user': note.author.username if note.author else 'Система',
            'details': note.text,
            'stage': note.stage.name if note.stage else None,
            'id': note.id
        })
        
    # Добавляем смену статусов
    for change in status_changes:
        combined.append({
            'type': 'status',
            'timestamp': change.timestamp,
            'user': change.operator_name,
            'details': f"Этап '{change.status}' выполнен. Количество: {change.quantity} шт.",
            'stage': change.status,
            'comment': change.comment,
            'status_type': change.status_type.name,
            'id': change.id
        })

    # Добавляем смену ответственных
    for change in responsible_changes:
        details_text = f"Назначен новый ответственный: {change.user.username}" if change.user else "Ответственный снят."
        combined.append({
            'type': 'responsible',
            'timestamp': change.timestamp,
            'user': 'Система', # Это системное событие
            'details': details_text,
            'stage': None
        })

    # Сортируем все события по дате в обратном порядке (самые новые вверху)
    return sorted(combined, key=lambda x: x['timestamp'], reverse=True)


def get_stages_query():
    """Возвращает запрос для получения всех этапов из справочника."""
    return Stage.query.order_by(Stage.name)


def get_route_stages_grouped(route_template_id):
    """
    Возвращает этапы для указанного маршрута, сгруппированные по порядку.
    """
    RouteStageInfo = namedtuple('RouteStageInfo', ['order', 'stage'])
    
    stages = db.session.query(
        RouteStage.order,
        Stage
    ).join(Stage, RouteStage.stage_id == Stage.id)\
     .filter(RouteStage.template_id == route_template_id)\
     .order_by(RouteStage.order)\
     .all()
    
    grouped_stages = []
    for order, group in groupby(stages, key=lambda x: x.order):
        stage_list = [item.Stage for item in group]
        grouped_stages.append(RouteStageInfo(order=order, stage=stage_list))
        
    return grouped_stages