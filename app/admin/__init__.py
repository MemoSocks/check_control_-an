# app/admin/__init__.py

from flask import Blueprint

# 1. Создаем главный "сборный" блюпринт для всей админки.
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# 2. Импортируем дочерние блюпринты.
from .routes import management_routes, part_routes, report_routes, user_routes
# --- НОВЫЙ ИМПОРТ ---
from .routes import data_routes

# 3. Регистрируем каждый дочерний блюпринт внутри нашего главного "сборного" блюпринта.
admin_bp.register_blueprint(management_routes.management_bp)
admin_bp.register_blueprint(part_routes.part_bp, url_prefix='/part')
admin_bp.register_blueprint(report_routes.report_bp, url_prefix='/report')
admin_bp.register_blueprint(user_routes.user_bp, url_prefix='/user')
# --- НОВАЯ РЕГИСТРАЦИЯ ---
admin_bp.register_blueprint(data_routes.data_bp, url_prefix='/data')