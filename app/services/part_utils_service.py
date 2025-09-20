# app/services/part_utils_service.py

import os
from datetime import datetime, timezone
from werkzeug.utils import secure_filename
from PIL import Image
from flask import render_template_string, url_for, current_app
from flask_wtf.csrf import generate_csrf

from app import db, socketio
from app.models import Permission
from app.utils import to_safe_key, generate_qr_code_as_base64


def _send_websocket_notification(event_type: str, message: str, data: dict = None):
    """
    Централизованная функция для отправки WebSocket-уведомлений.
    :param event_type: Тип события (например, 'part_created').
    :param message: Текст уведомления.
    :param data: Словарь с дополнительными данными.
    """
    try:
        payload = {'event': event_type, 'message': message}
        if data:
            payload.update(data)
        socketio.emit('notification', payload)
    except RuntimeError:
        print(f"WebSocket emit skipped (not in a Socket.IO server context): {message}")


def save_part_drawing(file_storage, config):
    """
    Сохраняет файл чертежа, оптимизируя изображение, и возвращает уникальное имя файла.
    :param file_storage: Объект FileStorage из Flask.
    :param config: Конфигурация приложения.
    :return: Уникальное имя сохраненного файла.
    """
    filename = secure_filename(file_storage.filename)
    unique_filename = f"{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}_{filename}"
    file_path = os.path.join(config['DRAWING_UPLOAD_FOLDER'], unique_filename)
    try:
        img = Image.open(file_storage)
        img.save(file_path, optimize=True, quality=85)
    except Exception:
        file_storage.seek(0)
        file_storage.save(file_path)
    return unique_filename


def _render_part_row_html(part, user):
    """
    Вспомогательная функция для рендеринга HTML-кода одной строки
    таблицы деталей для отправки через WebSocket.
    :param part: Экземпляр Part.
    :param user: Текущий пользователь (для проверки прав).
    :return: Строка с HTML-кодом.
    """
    permissions = {
        'can_edit': user.can(Permission.EDIT_PARTS),
        'can_delete': user.can(Permission.DELETE_PARTS),
        'can_generate_qr': user.can(Permission.GENERATE_QR)
    }
    
    # --- НАЧАЛО ИСПРАВЛЕНИЯ: Обновляем url_for ---
    row_template = """
        <tr class="hover:bg-gray-100 highlight-new" id="part-row-{{ part.part_id | urlencode }}">
            <td class="px-6 py-4"><input type="checkbox" value="{{ part.part_id }}" class="part-checkbox rounded border-gray-300"></td>
            <td class="px-6 py-4"><a href="{{ url_for('main.main_pages.history', part_id=part.part_id) }}" class="text-blue-600 hover:underline font-medium">{{ part.part_id }}</a></td>
            <td class="px-6 py-4 text-sm text-gray-900 name-cell">{{ part.name }}</td>
            <td class="px-6 py-4 text-sm text-gray-500 size-cell">{{ part.size or '' }}</td>
            <td class="px-6 py-4 text-sm text-gray-500 material-cell">{{ part.material }}</td>
            <td class="px-6 py-4 text-xs route-cell">
                <span class="text-gray-400 italic">Маршрут не назначен</span>
            </td>
            <td class="px-6 py-4 progress-cell">
                <div class="w-full bg-gray-200 rounded-full h-2.5"><div class="bg-blue-600 h-2.5 rounded-full" style="width: 0%"></div></div>
                <small>0 из {{ part.quantity_total }}</small>
            </td>
            <td class="px-6 py-4 text-sm text-gray-500 responsible-cell">Не назначен</td>
        </tr>
    """
    # --- КОНЕЦ ИСПРАВЛЕНИЯ ---
    return render_template_string(
        row_template,
        part=part,
        permissions=permissions,
        csrf_token=generate_csrf()
    )


def get_parts_for_printing(part_ids):
    """
    Получает детали по списку ID и генерирует для каждой QR-код в формате Base64.
    :param part_ids: Список ID деталей.
    :return: Список словарей, каждый из которых содержит объект Part и его QR-код.
    """
    from app.models import Part
    
    parts = db.session.query(Part).filter(Part.part_id.in_(part_ids)).all()
    
    with current_app.app_context():
        parts_for_print = [
            {
                'part': part,
                'qr_image': generate_qr_code_as_base64(part.part_id)
            }
            for part in parts
        ]
        
    return parts_for_print