# wsgi.py

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
from pythonjsonlogger import jsonlogger

from app import create_app
from config import config_by_name

# Загружаем переменные окружения из файла .env
load_dotenv()

# Определяем конфигурацию (development, production) на основе переменной окружения
config_name = os.environ.get('FLASK_ENV', 'development')
try:
    config_class = config_by_name[config_name]
except KeyError:
    sys.exit(f"Ошибка: Неверное имя конфигурации '{config_name}'. Допустимые значения: development, production, testing.")

# Создаем экземпляры приложения и SocketIO с помощью фабрики
app, socketio = create_app(config_class)

# --- Настройка логирования ---
if not app.debug:
    log_dir = os.path.join(app.instance_path, 'logs')
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    log_file_path = os.path.join(log_dir, 'app.log')

    file_handler = RotatingFileHandler(
        log_file_path, maxBytes=10485760, backupCount=5, encoding='utf-8'
    )
    
    log_format = '%(asctime)s %(name)s %(levelname)s %(pathname)s %(lineno)d %(message)s'
    formatter = jsonlogger.JsonFormatter(log_format)
    file_handler.setFormatter(formatter)
    
    app.logger.addHandler(file_handler)
    
    log_level = os.environ.get('LOG_LEVEL', 'INFO').upper()
    app.logger.setLevel(log_level)
    
    app.logger.info('Product Tracker application startup')

# --- НАЧАЛО ИСПРАВЛЕНИЯ ---
# Этот блок необходим для правильного запуска в режиме разработки с поддержкой eventlet.
# Стандартная команда `flask run` несовместима с eventlet.
# Теперь мы будем запускать приложение напрямую командой `python wsgi.py`.
if __name__ == '__main__':
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5000))
    print(f"--> Starting SocketIO server with eventlet on http://{host}:{port}")
    socketio.run(app, host=host, port=port)
# --- КОНЕЦ ИСПРАВЛЕНИЯ ---