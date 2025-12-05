#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ГЛАВНЫЙ ФАЙЛ ТЕЛЕГРАМ СИСТЕМЫ РАССЫЛКИ - ЧАСТЬ 1/2
Интеграция всех модулей + интерфейс пользователя
"""
import os
import sys
import json
import time
from datetime import datetime
from colorama import init, Fore, Style

# Инициализация цветного вывода
init(autoreset=True)

# Добавляем текущую директорию в путь
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем наши модули
from github_downloader import GitHubDownloader
from telegram_client import TelegramSyncClient
from chat_manager import ChatManager
from message_scheduler import MessageScheduler
from anti_ban_system import AntiBanSystem
import config

class TelegramBroadcastSystem:
    """Главный класс системы рассылки"""
    
    def __init__(self):
        """Инициализация системы"""
        print(Fore.CYAN + Style.BRIGHT + """
╔══════════════════════════════════════════════════╗
║      TELEGRAM BROADCAST SYSTEM v2.0              ║
║      Автономная система рассылки сообщений       ║
╚══════════════════════════════════════════════════╝
        """)
        
        self.downloader = GitHubDownloader()
        self.client = None
        self.chat_manager = None
        self.scheduler = None
        self.anti_ban = None
        
        # Флаги состояния
        self.is_authenticated = False
        self.is_github_ready = False
        
        # Загружаем конфигурацию
        self.load_config()
    
    def load_config(self):
        """Загрузить конфигурацию"""
        print(Fore.YELLOW + "📋 Загрузка конфигурации...")
        
        # Проверяем наличие конфигурационного файла
        if not os.path.exists('.env'):
            print(Fore.RED + "❌ Файл .env не найден!")
            print(Fore.YELLOW + "Создайте файл .env со следующими параметрами:")
            print("""
API_ID=ваш_api_id
API_HASH=ваш_api_hash
PHONE_NUMBER=+79991234567
GITHUB_TOKEN=ваш_github_token (опционально)
GITHUB_REPO=user/repo (опционально)
            """)
            
            # Предлагаем создать файл
            self.create_env_file()
        else:
            print(Fore.GREEN + "✅ Конфигурация загружена")
    
    def create_env_file(self):
        """Создать файл .env"""
        print(Fore.CYAN + "\n🛠️  Создание файла конфигурации...")
        
        api_id = input("Введите API ID (получить на my.telegram.org): ").strip()
        api_hash = input("Введите API Hash: ").strip()
        phone = input("Введите номер телефона (с кодом страны): ").strip()
        
        github_token = input("Введите GitHub Token (опционально, Enter чтобы пропустить): ").strip()
        github_repo = input("Введите GitHub репозиторий user/repo (опционально): ").strip()
        
        with open('.env', 'w') as f:
            f.write(f"API_ID={api_id}\n")
            f.write(f"API_HASH={api_hash}\n")
            f.write(f"PHONE_NUMBER={phone}\n")
            if github_token:
                f.write(f"GITHUB_TOKEN={github_token}\n")
            if github_repo:
                f.write(f"GITHUB_REPO={github_repo}\n")
        
        print(Fore.GREEN + "✅ Файл .env создан")
        
        # Перезагружаем конфигурацию
        from importlib import reload
        reload(config)
    
    def authenticate_telegram(self):
        """Аутентификация в Telegram"""
        print(Fore.CYAN + "\n🔐 Аутентификация в Telegram...")
        
        try:
            # Создаем клиент
            self.client = TelegramSyncClient()
            
            # Подключаемся
            if self.client.connect():
                self.is_authenticated = True
                
                # Инициализируем менеджер чатов
                self.chat_manager = ChatManager()
                
                # Получаем чаты пользователя
                print(Fore.YELLOW + "📋 Получение списка чатов...")
                chats = self.client.get_all_chats(limit=100)
                
                if chats:
                    self.chat_manager.import_chats_from_list(chats)
                    print(Fore.GREEN + f"✅ Получено {len(chats)} чатов")
                else:
                    print(Fore.RED + "⚠️ Чаты не найдены или произошла ошибка")
                
                # Создаем планировщик
                self.scheduler = MessageScheduler(self.client, self.chat_manager)
                self.anti_ban = AntiBanSystem()
                
                return True
            else:
                print(Fore.RED + "❌ Ошибка аутентификации")
                return False
                
        except Exception as e:
            print(Fore.RED + f"❌ Ошибка: {e}")
            return False
    
    def download_from_github(self):
        """Скачать код с GitHub"""
        print(Fore.CYAN + "\n📥 Загрузка кода с GitHub...")
        
        # Варианты загрузки
        print("\nВыберите способ загрузки:")
        print("1. Ввести ссылку на GitHub репозиторий")
        print("2. Ввести user/repo")
        print("3. Вставить код напрямую")
        print("4. Использовать репозиторий из конфигурации")
        
        choice = input("\nВаш выбор (1-4): ").strip()
        
        if choice == "1":
            url = input("Введите полную ссылку на репозиторий: ").strip()
            result = self.downloader.download_from_code_input(url)
            
        elif choice == "2":
            repo = input("Введите user/repo: ").strip()
            result = self.downloader.download_repo(repo)
            
        elif choice == "3":
            print("\nВведите код (Ctrl+D для завершения):")
            lines = []
            try:
                while True:
                    line = input()
                    lines.append(line)
            except EOFError:
                pass
            
            code = "\n".join(lines)
            if code:
                result = self.downloader.download_from_code_input(code)
            else:
                print(Fore.RED + "❌ Код не введен")
                result = False
                
        elif choice == "4":
            if config.Config.GITHUB_REPO:
                result = self.downloader.download_repo(config.Config.GITHUB_REPO)
            else:
                print(Fore.RED + "❌ Репозиторий не указан в конфигурации")
                result = False
        else:
            print(Fore.RED + "❌ Неверный выбор")
            return False
        
        if result:
            self.is_github_ready = True
            print(Fore.GREEN + "✅ Код успешно загружен")
            return True
        else:
            print(Fore.RED + "❌ Ошибка загрузки")
            return False
    
    def show_main_menu(self):
        """Показать главное меню"""
        while True:
            print(Fore.CYAN + Style.BRIGHT + "\n" + "═" * 50)
            print("ГЛАВНОЕ МЕНЮ")
            print("═" * 50)
            
            # Показываем статус
            status_auth = "✅" if self.is_authenticated else "❌"
            status_github = "✅" if self.is_github_ready else "❌"
            
            print(f"Telegram: {status_auth} | GitHub: {status_github}")
            print("\nДоступные команды:")
            
            if not self.is_authenticated:
                print("1. 🔐 Аутентификация в Telegram")
            
            if not self.is_github_ready:
                print("2. 📥 Загрузить код с GitHub")
            
            print("3. 📋 Управление чатами")
            print("4. 📨 Настройка рассылки")
            print("5. 🚀 Запуск рассылки")
            print("6. 📊 Статистика")
            print("7. ⚙️  Настройки системы")
            print("8. 💾 Сохранить данные")
            print("9. 🚪 Выход")
            
            print("═" * 50)
            
            choice = input(Fore.YELLOW + "\nВыберите действие (1-9): ").strip()
            
            if choice == "1" and not self.is_authenticated:
                self.authenticate_telegram()
                
            elif choice == "2" and not self.is_github_ready:
                self.download_from_github()
                
            elif choice == "3" and self.is_authenticated:
                self.manage_chats_menu()
                
            elif choice == "4" and self.is_authenticated:
                self.setup_broadcast_menu()
                
            elif choice == "5" and self.is_authenticated:
                self.start_broadcast_menu()
                
            elif choice == "6" and self.is_authenticated:
                self.show_statistics()
                
            elif choice == "7":
                self.system_settings_menu()
                
            elif choice == "8":
                self.save_all_data()
                
            elif choice == "9":
                print(Fore.GREEN + "\n👋 До свидания!")
                if self.client:
                    self.client.disconnect()
                break
            else:
                print(Fore.RED + "❌ Неверный выбор или действие недоступно")
    
    def manage_chats_menu(self):
        """Меню управления чатами"""
        if not self.chat_manager:
            print(Fore.RED + "❌ Менеджер чатов не инициализирован")
            return
        
        while True:
            print(Fore.CYAN + "\n" + "═" * 50)
            print("УПРАВЛЕНИЕ ЧАТАМИ")
            print("═" * 50)
            
            total_chats = len(self.chat_manager.chats)
            active_chats = len(self.chat_manager.get_all_active_chats())
            favorites = len(self.chat_manager.get_chats_by_category('favorites'))
            
            print(f"Всего чатов: {total_chats}")
            print(f"Активных: {active_chats}")
            print(f"Избранных: {favorites}")
            
            print("\n1. 👁️  Просмотреть все чаты")
            print("2. ⭐ Управление избранными")
            print("3. 🔍 Поиск чатов")
            print("4. 🚫 Черный список")
            print("5. 📥 Импорт чатов из Telegram")
            print("6. 📤 Экспорт чатов")
            print("7. 🗑️  Удалить чат")
            print("8. ↩️  Назад")
            
            choice = input(Fore.YELLOW + "\nВыберите действие (1-8): ").strip()
            
            if choice == "1":
                self.view_all_chats()
            elif choice == "2":
                self.manage_favorites()
            elif choice == "3":
                self.search_chats()
            elif choice == "4":
                self.manage_blacklist()
            elif choice == "5":
                self.import_chats_from_telegram()
            elif choice == "6":
                self.export_chats()
            elif choice == "7":
                self.delete_chat()
            elif choice == "8":
                break
            else:
                print(Fore.RED + "❌ Неверный выбор")
    
    def view_all_chats(self):
        """Просмотреть все чаты"""
        chats = self.chat_manager.export_chats()
        
        if not chats:
            print(Fore.YELLOW + "📭 Чаты не найдены")
            return
        
        print(Fore.CYAN + f"\n📋 Найдено {len(chats)} чатов:\n")
        
        for i, chat in enumerate(chats[:50], 1):  # Показываем первые 50
            status = "⭐" if chat['id'] in self.chat_manager.categories['favorites'] else "  "
            status += "🚫" if chat['id'] in self.chat_manager.categories['blacklist'] else "  "
            
            print(f"{i:3d}. {status} {chat.get('title', 'Без названия')}")
            print(f"     ID: {chat['id']} | Тип: {chat.get('type', 'unknown')}")
            print(f"     Участников: {chat.get('members_count', 0)}")
            print()
        
        if len(chats) > 50:
            print(Fore.YELLOW + f"... и еще {len(chats) - 50} чатов")
    
    def setup_broadcast_menu(self):
        """Меню настройки рассылки"""
        if not self.scheduler:
            print(Fore.RED + "❌ Планировщик не инициализирован")
            return
        
        while True:
            print(Fore.CYAN + "\n" + "═" * 50)
            print("НАСТРОЙКА РАССЫЛКИ")
            print("═" * 50)
            
            queue_status = self.scheduler.get_queue_status()
            queue_size = queue_status['immediate_queue'] + queue_status['scheduled_queue']
            
            print(f"Сообщений в очереди: {queue_size}")
            print(f"Статус: {'▶️ Запущена' if queue_status['is_running'] else '⏸️ Остановлена'}")
            
            print("\n1. 📝 Создать новую рассылку")
            print("2. ⏱️  Настроить задержки")
            print("3. 📋 Выбрать чаты для рассылки")
            print("4. ✏️  Редактировать шаблоны сообщений")
            print("5. 👁️  Просмотреть очередь")
            print("6. 🗑️  Очистить очередь")
            print("7. ↩️  Назад")
            
            choice = input(Fore.YELLOW + "\nВыберите действие (1-7): ").strip()
            
            if choice == "1":
                self.create_broadcast()
            elif choice == "2":
                self.configure_delays()
            elif choice == "3":
                self.select_chats_for_broadcast()
            elif choice == "4":
                self.edit_message_templates()
            elif choice == "5":
                self.view_queue()
            elif choice == "6":
                self.clear_queue()
            elif choice == "7":
                break
            else:
                print(Fore.RED + "❌ Неверный выбор")
    
    def create_broadcast(self):
        """Создать новую рассылку"""
        if not self.chat_manager:
            print(Fore.RED + "❌ Менеджер чатов не инициализирован")
            return
        
        print(Fore.CYAN + "\n🎯 СОЗДАНИЕ НОВОЙ РАССЫЛКИ")
        
        # Выбор чатов
        print("\nВыберите чаты для рассылки:")
        print("1. Все активные чаты")
        print("2. Только избранные")
        print("3. Только группы")
        print("4. Только каналы")
        print("5. Выбрать вручную")
        
        choice = input(Fore.YELLOW + "\nВаш выбор (1-5): ").strip()
        
        if choice == "1":
            chat_ids = self.chat_manager.get_all_active_chats()
            category = "все активные"
        elif choice == "2":
            chat_ids = self.chat_manager.get_chats_by_category('favorites')
            category = "избранные"
        elif choice == "3":
            chat_ids = self.chat_manager.get_chats_by_category('groups')
            category = "группы"
        elif choice == "4":
            chat_ids = self.chat_manager.get_chats_by_category('channels')
            category = "каналы"
        elif choice == "5":
            # Показываем список для выбора
            self.view_all_chats()
            selected = input(Fore.YELLOW + "\nВведите ID чатов через запятую: ").strip()
            chat_ids = [int(cid.strip()) for cid in selected.split(',') if cid.strip().isdigit()]
            category = "ручной выбор"
        else:
            print(Fore.RED + "❌ Неверный выбор")
            return
        
        if not chat_ids:
            print(Fore.RED + "❌ Не найдено чатов для рассылки")
            return
        
        print(Fore.GREEN + f"✅ Выбрано {len(chat_ids)} чатов ({category})")
        
        # Настройка сообщения
        print("\nНастройка сообщения:")
        print("1. Использовать стандартный шаблон")
        print("2. Использовать персонализированные сообщения")
        print("3. Ввести свое сообщение")
        
        msg_choice = input(Fore.YELLOW + "\nВаш выбор (1-3): ").strip()
        
        if msg_choice == "1":
            message = config.Config.MESSAGE_TEMPLATE
        elif msg_choice == "2":
            message = None  # Будет генерироваться автоматически
            print(Fore.YELLOW + "ℹ️  Будут использованы персонализированные сообщения")
        elif msg_choice == "3":
            print(Fore.YELLOW + "Введите сообщение (Ctrl+D для завершения):")
            lines = []
            try:
                while True:
                    line = input()
                    lines.append(line)
            except EOFError:
                pass
            message = "\n".join(lines)
        else:
            print(Fore.RED + "❌ Неверный выбор")
            return
        
        # Настройка количества сообщений
        try:
            count = int(input(Fore.YELLOW + "\nСколько сообщений отправить в каждый чат? (1-10): ").strip())
            count = max(1, min(10, count))
        except:
            count = 1
            print(Fore.YELLOW + "ℹ️  Установлено значение по умолчанию: 1")
        
        # Настройка задержки
        print("\nНастройка задержки между сообщениями:")
        print("1. Автоматическая (рекомендуется)")
        print("2. Фиксированная")
        print("3. Случайная в диапазоне")
        
        delay_choice = input(Fore.YELLOW + "\nВаш выбор (1-3): ").strip()
        
        if delay_choice == "1":
            delay = None  # Автоматическая задержка
            print(Fore.GREEN + "✅ Используется автоматическая система задержек")
        elif delay_choice == "2":
            try:
                delay = float(input(Fore.YELLOW + "Задержка в секундах: ").strip())
                delay = max(1.0, min(30.0, delay))
            except:
                delay = 3.0
                print(Fore.YELLOW + f"ℹ️  Установлено значение по умолчанию: {delay} сек")
        elif delay_choice == "3":
            try:
                min_d = float(input(Fore.YELLOW + "Минимальная задержка (сек): ").strip())
                max_d = float(input(Fore.YELLOW + "Максимальная задержка (сек): ").strip())
                min_d = max(1.0, min(30.0, min_d))
                max_d = max(min_d, min(60.0, max_d))
                delay = f"{min_d}-{max_d}"
            except:
                delay = "3-10"
                print(Fore.YELLOW + f"ℹ️  Установлено значение по умолчанию: {delay} сек")
        else:
            delay = None
            print(Fore.YELLOW + "ℹ️  Используется автоматическая система задержек")
                  # Создание кампании
        campaign_id = self.scheduler.create_broadcast_campaign(
            chat_ids=chat_ids,
            message=message,
            messages_count=count,
            delay_between=delay if isinstance(delay, (int, float)) else None
        )
        
        print(Fore.GREEN + f"\n✅ Кампания создана! ID: {campaign_id}")
        print(Fore.YELLOW + f"📨 Всего будет отправлено: {len(chat_ids) * count} сообщений")
    
    def start_broadcast_menu(self):
        """Меню запуска рассылки"""
        if not self.scheduler:
            print(Fore.RED + "❌ Планировщик не инициализирован")
            return
        
        queue_status = self.scheduler.get_queue_status()
        queue_size = queue_status['immediate_queue'] + queue_status['scheduled_queue']
        
        if queue_size == 0:
            print(Fore.YELLOW + "📭 Очередь рассылки пуста")
            print(Fore.YELLOW + "Сначала создайте рассылку в меню настройки")
            return
        
        print(Fore.CYAN + f"\n📊 Статус очереди: {queue_size} сообщений")
        
        if self.scheduler.is_running:
            print(Fore.YELLOW + "\nРассылка уже запущена")
            print("1. ⏸️  Приостановить")
            print("2. 🛑 Остановить")
            print("3. 📊 Статистика")
            print("4. ↩️  Назад")
            
            choice = input(Fore.YELLOW + "\nВаш выбор (1-4): ").strip()
            
            if choice == "1":
                self.scheduler.pause()
                print(Fore.GREEN + "✅ Рассылка приостановлена")
            elif choice == "2":
                self.scheduler.stop()
                print(Fore.GREEN + "✅ Рассылка остановлена")
            elif choice == "3":
                self.show_broadcast_statistics()
            elif choice == "4":
                return
            else:
                print(Fore.RED + "❌ Неверный выбор")
        else:
            print(Fore.GREEN + "\nРассылка готова к запуску")
            print("1. 🚀 Запустить рассылку")
            print("2. ⚙️  Настроить лимиты")
            print("3. ↩️  Назад")
            
            choice = input(Fore.YELLOW + "\nВаш выбор (1-3): ").strip()
            
            if choice == "1":
                # Запрашиваем лимит сообщений
                limit_input = input(Fore.YELLOW + "Лимит сообщений (Enter для безлимита): ").strip()
                if limit_input and limit_input.isdigit():
                    limit = int(limit_input)
                else:
                    limit = None
                
                print(Fore.CYAN + "\n🚀 Запуск рассылки...")
                self.scheduler.start(max_messages=limit)
                
                # Показываем прогресс
                self.monitor_broadcast()
                
            elif choice == "2":
                self.configure_limits()
            elif choice == "3":
                return
            else:
                print(Fore.RED + "❌ Неверный выбор")
    
    def monitor_broadcast(self):
        """Мониторинг процесса рассылки"""
        import time
        
        print(Fore.CYAN + "\n📡 МОНИТОРИНГ РАССЫЛКИ")
        print("Нажмите Ctrl+C для остановки мониторинга\n")
        
        try:
            while self.scheduler.is_running:
                stats = self.scheduler.get_queue_status()
                
                print(f"\r📨 Отправлено: {stats['stats']['total_sent']} | "
                      f"Ошибок: {stats['stats']['total_failed']} | "
                      f"В очереди: {stats['immediate_queue'] + stats['scheduled_queue']}", 
                      end='', flush=True)
                
                time.sleep(2)
                
        except KeyboardInterrupt:
            print(Fore.YELLOW + "\n\n⏸️  Мониторинг остановлен")
    
    def show_statistics(self):
        """Показать общую статистику"""
        print(Fore.CYAN + "\n" + "═" * 50)
        print("СТАТИСТИКА СИСТЕМЫ")
        print("═" * 50)
        
        # Статистика чатов
        if self.chat_manager:
            total_chats = len(self.chat_manager.chats)
            active_chats = len(self.chat_manager.get_all_active_chats())
            favorites = len(self.chat_manager.get_chats_by_category('favorites'))
            blacklisted = len(self.chat_manager.get_chats_by_category('blacklist'))
            
            print(f"\n📋 ЧАТЫ:")
            print(f"   Всего: {total_chats}")
            print(f"   Активных: {active_chats}")
            print(f"   Избранных: {favorites}")
            print(f"   В черном списке: {blacklisted}")
        
        # Статистика рассылки
        if self.scheduler:
            stats = self.scheduler.get_queue_status()
            queue_size = stats['immediate_queue'] + stats['scheduled_queue']
            
            print(f"\n📨 РАССЫЛКА:")
            print(f"   Сообщений в очереди: {queue_size}")
            print(f"   Всего отправлено: {stats['stats']['total_sent']}")
            print(f"   Ошибок отправки: {stats['stats']['total_failed']}")
            print(f"   Статус: {'▶️ Запущена' if stats['is_running'] else '⏸️ Остановлена'}")
        
        # Статистика анти-бана
        if self.anti_ban:
            msgs_last_hour = self.anti_ban.get_messages_last_hour()
            
            print(f"\n🛡️  ЗАЩИТА ОТ БАНА:")
            print(f"   Сообщений за час: {msgs_last_hour}")
            print(f"   Лимит в час: {config.Config.MAX_MESSAGES_PER_HOUR}")
            
            if msgs_last_hour > config.Config.MAX_MESSAGES_PER_HOUR * 0.8:
                print(Fore.RED + "   ⚠️  Приближаетесь к лимиту!")
            elif msgs_last_hour > config.Config.MAX_MESSAGES_PER_HOUR * 0.5:
                print(Fore.YELLOW + "   ⚠️  Лимит на половине")
            else:
                print(Fore.GREEN + "   ✅ В пределах лимита")
        
        print(Fore.CYAN + "═" * 50)
        input(Fore.YELLOW + "\nНажмите Enter для продолжения...")
    
    def save_all_data(self):
        """Сохранить все данные системы"""
        print(Fore.CYAN + "\n💾 Сохранение данных...")
        
        try:
            # Сохраняем чаты
            if self.chat_manager:
                self.chat_manager.save_chats()
                self.chat_manager.save_categories()
            
            # Сохраняем историю сообщений
            if self.anti_ban:
                self.anti_ban.save_history()
            
            # Сохраняем сессию Telegram
            if self.client and self.client.async_client:
                import asyncio
                asyncio.run(self.client.async_client.save_session_string())
            
            print(Fore.GREEN + "✅ Все данные сохранены")
            
        except Exception as e:
            print(Fore.RED + f"❌ Ошибка сохранения: {e}")
    
    # Дополнительные методы меню (упрощенные для примера)
    def manage_favorites(self):
        """Управление избранными чатами"""
        print(Fore.YELLOW + "\n⚠️  Функция в разработке")
        input("Нажмите Enter для продолжения...")
    
    def search_chats(self):
        """Поиск чатов"""
        query = input(Fore.YELLOW + "Введите поисковый запрос: ").strip()
        if self.chat_manager and query:
            results = self.chat_manager.search_chats(query)
            print(Fore.GREEN + f"✅ Найдено {len(results)} чатов")
    
    def manage_blacklist(self):
        """Управление черным списком"""
        print(Fore.YELLOW + "\n⚠️  Функция в разработке")
    
    def import_chats_from_telegram(self):
        """Импорт чатов из Telegram"""
        if self.client and self.chat_manager:
            print(Fore.YELLOW + "\n📥 Импорт чатов из Telegram...")
            chats = self.client.get_all_chats(limit=200)
            if chats:
                self.chat_manager.import_chats_from_list(chats)
                print(Fore.GREEN + f"✅ Импортировано {len(chats)} чатов")
    
    def export_chats(self):
        """Экспорт чатов"""
        print(Fore.YELLOW + "\n⚠️  Функция в разработке")
    
    def delete_chat(self):
        """Удалить чат"""
        chat_id = input(Fore.YELLOW + "Введите ID чата для удаления: ").strip()
        if chat_id.isdigit() and self.chat_manager:
            self.chat_manager.remove_chat(int(chat_id))
    
    def configure_delays(self):
        """Настроить задержки"""
        print(Fore.YELLOW + "\n⚠️  Функция в разработке")
    
    def select_chats_for_broadcast(self):
        """Выбрать чаты для рассылки"""
        print(Fore.YELLOW + "\n⚠️  Функция в разработке")
    
    def edit_message_templates(self):
        """Редактировать шаблоны сообщений"""
        print(Fore.YELLOW + "\n⚠️  Функция в разработке")
    
    def view_queue(self):
        """Просмотреть очередь"""
        if self.scheduler:
            stats = self.scheduler.get_queue_status()
            print(Fore.CYAN + f"\n📊 Очередь: {stats['immediate_queue']} немедленных, "
                  f"{stats['scheduled_queue']} отложенных")
    
    def clear_queue(self):
        """Очистить очередь"""
        confirm = input(Fore.RED + "Вы уверены? (y/N): ").strip().lower()
        if confirm == 'y' and self.scheduler:
            # Создаем новые пустые очереди
            self.scheduler.message_queue = Queue()
            self.scheduler.priority_queue = PriorityQueue()
            print(Fore.GREEN + "✅ Очередь очищена")
    
    def configure_limits(self):
        """Настроить лимиты"""
        print(Fore.YELLOW + "\n⚠️  Функция в разработке")
    
    def show_broadcast_statistics(self):
        """Показать статистику рассылки"""
        if self.scheduler:
            self.scheduler._print_stats()
    
    def system_settings_menu(self):
        """Меню настроек системы"""
        print(Fore.YELLOW + "\n⚠️  Функция в разработке")

def main():
    """Главная функция"""
    try:
        # Создаем и запускаем систему
        system = TelegramBroadcastSystem()
        
        # Запускаем главное меню
        system.show_main_menu()
        
    except KeyboardInterrupt:
        print(Fore.YELLOW + "\n\n👋 Программа прервана пользователем")
    except Exception as e:
        print(Fore.RED + f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
