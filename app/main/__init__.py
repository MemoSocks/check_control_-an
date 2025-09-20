# app/main/__init__.py

from flask import Blueprint

# 1. Создаем главный "сборный" блюпринт для основного раздела приложения.
main_bp = Blueprint('main', __name__)

# 2. Импортируем наши новые, разделенные файлы с маршрутами.
# --- ИЗМЕНЕНИЕ: Импортируем `main_pages_bp` из `main_routes` ---
from . import main_routes, api_routes, action_routes

# 3. Регистрируем каждый дочерний блюпринт внутри нашего главного блюпринта.
# --- ИЗМЕНЕНИЕ: Регистрируем `main_pages_bp` ---
main_bp.register_blueprint(main_routes.main_pages_bp)
main_bp.register_blueprint(api_routes.api_bp)
main_bp.register_blueprint(action_routes.action_bp)