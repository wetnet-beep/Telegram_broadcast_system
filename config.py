# -*- coding: utf-8 -*-
"""
КОНФИГУРАЦИОННЫЙ ФАЙЛ СИСТЕМЫ
"""
import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Telegram API данные (получаются от пользователя)
    API_ID = os.getenv('API_ID', '')          # Получить на my.telegram.org
    API_HASH = os.getenv('API_HASH', '')      # Получить на my.telegram.org
    PHONE_NUMBER = os.getenv('PHONE_NUMBER', '')
    
    # Настройки GitHub
    GITHUB_TOKEN = os.getenv('GITHUB_TOKEN', '')
    GITHUB_REPO = os.getenv('GITHUB_REPO', '')  # Формат: username/repo
    
    # Настройки рассылки
    DEFAULT_DELAY = [3.5, 4.5, 3.2]  # Задержки в секундах (циклично)
    MESSAGE_TEMPLATE = "Привет! Это тестовая рассылка от пользователя."
    
    # Настройки защиты от бана
    MAX_MESSAGES_PER_HOUR = 30
    RANDOM_DELAY_RANGE = (2, 10)  # Случайная задержка в секундах
    HUMANIZE_TYPING = True         # Имитация печати пользователя
    
    # Файлы для хранения данных
    SESSION_FILE = "user_session.session"
    CHATS_DB = "chats_database.json"
    MESSAGES_DB = "messages_history.json"
    
    # Логирование
    LOG_LEVEL = "INFO"
    LOG_FILE = "broadcast.log"
