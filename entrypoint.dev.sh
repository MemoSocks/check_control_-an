#!/bin/sh

# Немедленно завершать работу, если какая-либо команда завершается с ошибкой
set -e

# Запускаем сборку и отслеживание CSS в фоновом режиме
# Знак '&' в конце отправляет команду в фон
echo "--> Starting PostCSS watcher in the background..."
npm run css:watch &

# --- НАЧАЛО ИСПРАВЛЕНИЯ ---
# Заменяем `npm run start:flask`, который использует `flask run`,
# на прямой запуск wsgi.py. Это необходимо для корректной работы
# WebSocket (Flask-SocketIO) с eventlet в режиме разработки.
echo "--> Starting Flask-SocketIO development server with eventlet..."
python wsgi.py
# --- КОНЕЦ ИСПРАВЛЕНИЯ ---```