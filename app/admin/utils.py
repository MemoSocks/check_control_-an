# app/admin/utils.py

from functools import wraps
from flask import abort
from flask_login import current_user

# --- ИЗМЕНЕНИЕ: Обновляем импорт, чтобы он соответствовал новой структуре моделей ---
from app.models import Permission


def permission_required(permission):
    """
    Декоратор, который проверяет, обладает ли текущий пользователь
    необходимыми правами доступа для просмотра страницы.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.can(permission):
                # Если прав нет, возвращаем ошибку 403 (Forbidden)
                abort(403)
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def admin_required(f):
    """
    Более специфичный декоратор, который является частным случаем
    `permission_required` для проверки прав администратора.
    """
    return permission_required(Permission.ADMIN)(f)