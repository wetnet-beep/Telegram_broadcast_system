# -*- coding: utf-8 -*-
"""
ПЛАНИРОВЩИК РАССЫЛКИ СООБЩЕНИЙ
Управление очередью, приоритетами, временем отправки
"""
import asyncio
import json
import random
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from queue import Queue, PriorityQueue
import threading
import time

from anti_ban_system import AntiBanSystem
from chat_manager import ChatManager
import config

class MessageScheduler:
    """Планировщик для управления рассылкой сообщений"""
    
    def __init__(self, telegram_client, chat_manager: ChatManager = None):
        """
        Инициализация планировщика
        
        Args:
            telegram_client: Клиент Telegram для отправки
            chat_manager: Менеджер чатов (опционально)
        """
        self.client = telegram_client
        self.chat_manager = chat_manager or ChatManager()
        self.anti_ban = AntiBanSystem()
        
        # Очередь сообщений
        self.message_queue = Queue()
        self.priority_queue = PriorityQueue()
        
        # Статус работы
        self.is_running = False
        self.is_paused = False
        self.current_thread = None
        
        # Статистика
        self.stats = {
            'total_sent': 0,
            'total_failed': 0,
            'start_time': None,
            'last_sent': None
        }
        
        # Шаблоны сообщений
        self.message_templates = [
            "Привет! {name}, у нас для тебя важная информация!",
            "Внимание, {name}! Специальное предложение только для тебя!",
            "{name}, не пропусти новости нашей группы!",
            "Дорогой {name}, у нас для тебя есть кое-что интересное!",
            "Приветствуем, {name}! Загляни к нам, будет интересно!"
        ]
    
    def add_message_to_queue(self, chat_id: int, message: str, 
                            priority: int = 5, send_time: datetime = None):
        """
        Добавить сообщение в очередь
        
        Args:
            chat_id: ID чата
            message: Текст сообщения
            priority: Приоритет (1-высший, 10-низший)
            send_time: Время отправки (None для немедленной)
        """
        queue_item = {
            'chat_id': chat_id,
            'message': message,
            'priority': priority,
            'send_time': send_time or datetime.now(),
            'added_time': datetime.now(),
            'attempts': 0
        }
        
        if send_time:
            # Для отложенных - в приоритетную очередь
            self.priority_queue.put((priority, queue_item))
        else:
            # Для немедленных - в обычную очередь
            self.message_queue.put(queue_item)
        
        print(f"📥 Сообщение добавлено в очередь для чата {chat_id}")
    
    def add_broadcast_to_queue(self, chat_ids: List[int], message: str, 
                              priority: int = 5, delay_between: float = None):
        """
        Добавить рассылку в очередь
        
        Args:
            chat_ids: Список ID чатов
            message: Текст сообщения
            priority: Приоритет
            delay_between: Задержка между сообщениями
        """
        for i, chat_id in enumerate(chat_ids):
            if delay_between and i > 0:
                send_time = datetime.now() + timedelta(seconds=delay_between * i)
            else:
                send_time = None
            
            self.add_message_to_queue(chat_id, message, priority, send_time)
        
        print(f"📨 Рассылка добавлена: {len(chat_ids)} сообщений")
    
    def start(self, max_messages: int = None, auto_stop: bool = True):
        """
        Запустить планировщик
        
        Args:
            max_messages: Максимальное количество сообщений (None = бесконечно)
            auto_stop: Автоматически остановиться после завершения
        """
        if self.is_running:
            print("⚠️ Планировщик уже запущен")
            return
        
        print("🚀 Запуск планировщика рассылки...")
        self.is_running = True
        self.is_paused = False
        self.stats['start_time'] = datetime.now()
        
        # Запускаем в отдельном потоке
        self.current_thread = threading.Thread(
            target=self._process_queue,
            args=(max_messages, auto_stop),
            daemon=True
        )
        self.current_thread.start()
    
    def stop(self):
        """Остановить планировщик"""
        self.is_running = False
        if self.current_thread:
            self.current_thread.join(timeout=5)
        print("🛑 Планировщик остановлен")
    
    def pause(self):
        """Приостановить рассылку"""
        self.is_paused = True
        print("⏸️ Рассылка приостановлена")
    
    def resume(self):
        """Возобновить рассылку"""
        self.is_paused = False
        print("▶️ Рассылка возобновлена")
    
    def _process_queue(self, max_messages: int = None, auto_stop: bool = True):
        """
        Обработка очереди сообщений (внутренний метод)
        
        Args:
            max_messages: Максимальное количество сообщений
            auto_stop: Автоматически остановиться
        """
        messages_sent = 0
        
        while self.is_running:
            # Проверяем паузу
            if self.is_paused:
                time.sleep(1)
                continue
            
            # Проверяем лимит сообщений
            if max_messages and messages_sent >= max_messages:
                if auto_stop:
                    self.stop()
                break
            
            # Получаем следующее сообщение
            message_item = self._get_next_message()
            if not message_item:
                # Если очередь пуста и автостоп
                if auto_stop and self.message_queue.empty() and self.priority_queue.empty():
                    print("📭 Очередь пуста, остановка...")
                    self.stop()
                    break
                
                time.sleep(1)
                continue
            
            # Проверяем время отправки
            now = datetime.now()
            if message_item['send_time'] and message_item['send_time'] > now:
                # Сообщение еще не готово к отправке
                self.priority_queue.put((message_item['priority'], message_item))
                time.sleep(1)
                continue
            
            # Отправляем сообщение
            success = self._send_message(message_item)
            
            if success:
                messages_sent += 1
                self.stats['total_sent'] += 1
                self.stats['last_sent'] = datetime.now()
                
                # Обновляем статистику чата
                if self.chat_manager:
                    self.chat_manager.update_chat_stats(message_item['chat_id'], True)
            else:
                self.stats['total_failed'] += 1
                
                # Повторная попытка (максимум 3 раза)
                if message_item['attempts'] < 3:
                    message_item['attempts'] += 1
                    # Задержка перед повторной попыткой
                    retry_delay = 60 * message_item['attempts']  # 60, 120, 180 сек
                    message_item['send_time'] = now + timedelta(seconds=retry_delay)
                    self.priority_queue.put((message_item['priority'] + 5, message_item))
                    print(f"🔄 Повторная попытка через {retry_delay} сек")
                else:
                    print(f"❌ Сообщение не отправлено после 3 попыток")
            
            # Выводим статистику каждые 10 сообщений
            if messages_sent % 10 == 0:
                self._print_stats()
    
    def _get_next_message(self) -> Optional[Dict]:
        """
        Получить следующее сообщение из очереди
        
        Returns:
            Элемент очереди или None
        """
        # Сначала проверяем приоритетную очередь
        if not self.priority_queue.empty():
            _, item = self.priority_queue.get()
            return item
        
        # Затем обычную очередь
        if not self.message_queue.empty():
            return self.message_queue.get()
        
        return None
    
    def _send_message(self, message_item: Dict) -> bool:
        """
        Отправить сообщение (внутренний метод)
        
        Args:
            message_item: Элемент очереди
            
        Returns:
            True если успешно
        """
        chat_id = message_item['chat_id']
        message = message_item['message']
        
        try:
            # Проверяем лимиты анти-бана
            can_send, reason = self.anti_ban.check_limits()
            if not can_send:
                print(f"⏸️ {reason}")
                # Откладываем на 5 минут
                message_item['send_time'] = datetime.now() + timedelta(minutes=5)
                self.priority_queue.put((1, message_item))  # Высокий приоритет
                return False
            
            # Получаем умную задержку
            delay = self.anti_ban.get_smart_delay()
            
            print(f"📤 Отправка в чат {chat_id} через {delay} сек...")
            
            # Используем синхронную отправку
            success = self.client.send_message(
                chat_id=chat_id,
                message=message,
                delay_before=delay,
                delay_after=0
            )
            
            if success:
                # Записываем в историю
                self.anti_ban.record_message_sent(chat_id, message)
                return True
            else:
                return False
                
        except Exception as e:
            print(f"❌ Ошибка отправки: {e}")
            return False
    
    def _print_stats(self):
        """Вывести статистику"""
        if self.stats['start_time']:
            runtime = datetime.now() - self.stats['start_time']
            hours, remainder = divmod(runtime.seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            
            print("\n" + "="*50)
            print("📊 СТАТИСТИКА РАССЫЛКИ:")
            print(f"   Всего отправлено: {self.stats['total_sent']}")
            print(f"   Не удалось отправить: {self.stats['total_failed']}")
            print(f"   Время работы: {hours:02d}:{minutes:02d}:{seconds:02d}")
            
            if self.stats['last_sent']:
                last_sent_ago = (datetime.now() - self.stats['last_sent']).seconds
                print(f"   Последняя отправка: {last_sent_ago} сек назад")
            
            # Статистика анти-бана
            msgs_last_hour = self.anti_ban.get_messages_last_hour()
            print(f"   Сообщений за час: {msgs_last_hour}")
            
            print("="*50 + "\n")
    
    def generate_personalized_message(self, chat_id: int) -> str:
        """
        Сгенерировать персонализированное сообщение
        
        Args:
            chat_id: ID чата
            
        Returns:
            Персонализированное сообщение
        """
        # Получаем информацию о чате
        chat_info = self.chat_manager.chats.get(chat_id, {})
        chat_name = chat_info.get('title', 'друг')
        
        # Выбираем случайный шаблон
        template = random.choice(self.message_templates)
        
        # Заменяем плейсхолдеры
        message = template.format(name=chat_name)
        
        # Добавляем случайный эмодзи
        emojis = ['😊', '🎉', '🚀', '⭐', '💫', '🔥', '👋', '📢']
        message += " " + random.choice(emojis)
        
        return message
    
    def create_broadcast_campaign(self, chat_ids: List[int], 
                                 message: str = None,
                                 messages_count: int = 1,
                                 delay_between: float = None) -> str:
        """
        Создать кампанию рассылки
        
        Args:
            chat_ids: Список чатов
            message: Сообщение (None для персонализированных)
            messages_count: Количество сообщений на чат
            delay_between: Задержка между сообщениями
            
        Returns:
            ID кампании
        """
        import uuid
        campaign_id = str(uuid.uuid4())[:8]
        
        print(f"🎯 Создание кампании {campaign_id} для {len(chat_ids)} чатов...")
        
        for chat_id in chat_ids:
            for i in range(messages_count):
                if message:
                    msg_to_send = message
                else:
                    msg_to_send = self.generate_personalized_message(chat_id)
                
                # Разная задержка для разных сообщений
                if delay_between:
                    msg_delay = delay_between * (i + 1)
                else:
                    msg_delay = None
                
                self.add_message_to_queue(
                    chat_id=chat_id,
                    message=msg_to_send,
                    priority=3,
                    send_time=datetime.now() + timedelta(seconds=msg_delay) if msg_delay else None
                )
        
        print(f"✅ Кампания {campaign_id} создана: {len(chat_ids) * messages_count} сообщений")
        return campaign_id
    
    def get_queue_status(self) -> Dict:
        """Получить статус очередей"""
        return {
            'immediate_queue': self.message_queue.qsize(),
            'scheduled_queue': self.priority_queue.qsize(),
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'stats': self.stats.copy()
        }

# Пример использования
if __name__ == "__main__":
    print("🔧 Тестирование планировщика...")
    
    # Создаем мок-клиент для тестов
    class MockClient:
        def send_message(self, chat_id, message, delay_before=0, delay_after=0):
            print(f"[MOCK] Отправка в {chat_id}: {message[:30]}...")
            time.sleep(0.1)  # Имитация отправки
            return True
    
    # Создаем планировщик
    scheduler = MessageScheduler(MockClient())
    
    # Добавляем тестовые сообщения
    test_chats = [1001, 1002, 1003, 1004, 1005]
    
    print("📨 Добавление тестовой рассылки...")
    scheduler.add_broadcast_to_queue(
        chat_ids=test_chats,
        message="Тестовое сообщение от планировщика",
        delay_between=2.0
    )
    
    # Запускаем на 3 сообщения
    print("🚀 Запуск планировщика (макс. 3 сообщения)...")
    scheduler.start(max_messages=3, auto_stop=True)
    
    # Ждем завершения
    time.sleep(10)
    
    if scheduler.is_running:
        scheduler.stop()
    
    print("✅ Тест завершен")
