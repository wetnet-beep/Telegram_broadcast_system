# -*- coding: utf-8 -*-
"""
СИСТЕМА ЗАЩИТЫ ОТ БАНА В TELEGRAM
Адаптивные задержки и лимиты
"""
import random
import time
import json
from datetime import datetime, timedelta
from typing import List, Tuple
import config

class AntiBanSystem:
    """Система для предотвращения блокировки аккаунта"""
    
    def __init__(self):
        self.message_history = []
        self.sent_messages_count = 0
        self.last_reset_time = datetime.now()
        self.delay_patterns = [
            [3.5, 4.5, 3.2],  # Паттерн 1
            [4.0, 3.0, 5.0],  # Паттерн 2
            [2.5, 3.5, 4.5],  # Паттерн 3
            [3.0, 4.0, 3.5],  # Паттерн 4
        ]
        self.current_pattern = 0
        self.position_in_pattern = 0
        
        # Лимиты Telegram
        self.hourly_limit = config.Config.MAX_MESSAGES_PER_HOUR
        self.daily_limit = 200
        self.min_delay = 2.0
        self.max_delay = 10.0
        
        # Загружаем историю
        self.load_history()
    
    def load_history(self):
        """Загрузить историю сообщений из файла"""
        try:
            with open(config.Config.MESSAGES_DB, 'r') as f:
                data = json.load(f)
                self.message_history = data.get('history', [])
                self.sent_messages_count = data.get('total', 0)
        except (FileNotFoundError, json.JSONDecodeError):
            self.message_history = []
            self.sent_messages_count = 0
    
    def save_history(self):
        """Сохранить историю сообщений"""
        data = {
            'history': self.message_history[-1000:],  # Храним последние 1000 записей
            'total': self.sent_messages_count,
            'last_update': datetime.now().isoformat()
        }
        try:
            with open(config.Config.MESSAGES_DB, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"⚠️ Ошибка сохранения истории: {e}")
    
    def record_message_sent(self, chat_id: int, message: str):
        """Записать отправленное сообщение"""
        record = {
            'timestamp': datetime.now().isoformat(),
            'chat_id': chat_id,
            'message_preview': message[:50],
            'hour': datetime.now().hour
        }
        
        self.message_history.append(record)
        self.sent_messages_count += 1
        
        # Сохраняем каждые 10 сообщений
        if self.sent_messages_count % 10 == 0:
            self.save_history()
    
    def get_messages_last_hour(self) -> int:
        """Получить количество сообщений за последний час"""
        now = datetime.now()
        one_hour_ago = now - timedelta(hours=1)
        
        count = 0
        for record in self.message_history:
            try:
                record_time = datetime.fromisoformat(record['timestamp'])
                if record_time > one_hour_ago:
                    count += 1
            except:
                continue
        
        return count
    
    def get_smart_delay(self) -> float:
        """
        Получить умную задержку для следующего сообщения
        
        Returns:
            Задержка в секундах
        """
        # Проверяем лимиты
        messages_last_hour = self.get_messages_last_hour()
        
        # Если приближаемся к лимиту - увеличиваем задержку
        if messages_last_hour > self.hourly_limit * 0.8:
            base_delay = random.uniform(8.0, 15.0)
        elif messages_last_hour > self.hourly_limit * 0.5:
            base_delay = random.uniform(5.0, 10.0)
        else:
            # Используем паттерн с небольшими вариациями
            pattern = self.delay_patterns[self.current_pattern]
            base_delay = pattern[self.position_in_pattern]
            
            # Добавляем случайность ±0.5 сек
            base_delay += random.uniform(-0.5, 0.5)
            
            # Обновляем позиции
            self.position_in_pattern += 1
            if self.position_in_pattern >= len(pattern):
                self.position_in_pattern = 0
                self.current_pattern = (self.current_pattern + 1) % len(self.delay_patterns)
        
        # Ограничиваем минимальную и максимальную задержку
        delay = max(self.min_delay, min(base_delay, self.max_delay))
        
        # Если ночь - можно уменьшить задержку
        hour = datetime.now().hour
        if 0 <= hour < 6:  # Ночное время
            delay *= 0.7
        
        return round(delay, 2)
    
    def check_limits(self) -> Tuple[bool, str]:
        """
        Проверить лимиты отправки
        
        Returns:
            (можно_отправлять, причина_если_нет)
        """
        now = datetime.now()
        
        # Проверяем часовой лимит
        messages_last_hour = self.get_messages_last_hour()
        if messages_last_hour >= self.hourly_limit:
            next_hour = (now + timedelta(hours=1)).replace(minute=0, second=0, microsecond=0)
            wait_time = (next_hour - now).seconds
            return False, f"⚠️ Достигнут часовой лимит. Ждите {wait_time // 60} мин."
        
        # Проверяем дневной лимит (если есть данные за 24 часа)
        if len(self.message_history) > 100:
            day_messages = 0
            for record in self.message_history[-200:]:  # Последние 200 записей
                try:
                    record_time = datetime.fromisoformat(record['timestamp'])
                    if record_time > now - timedelta(days=1):
                        day_messages += 1
                except:
                    continue
            
            if day_messages >= self.daily_limit:
                return False, "⚠️ Достигнут дневной лимит отправки"
        
        return True, "✅ Можно отправлять"
    
    def simulate_human_typing(self, message_length: int) -> float:
        """
        Рассчитать время имитации печати
        
        Args:
            message_length: Длина сообщения в символах
            
        Returns:
            Время задержки для имитации печати
        """
        # Средняя скорость печати: 200 символов в минуту
        typing_speed = 200 / 60  # Символов в секунду
        
        # Время на печать
        typing_time = message_length / typing_speed
        
        # Добавляем случайную паузу для "обдумывания"
        thinking_time = random.uniform(0.5, 2.0)
        
        return round(typing_time + thinking_time, 2)
    
    def get_recommended_batch_size(self) -> int:
        """
        Получить рекомендуемый размер пачки сообщений
        
        Returns:
            Количество сообщений в пачке
        """
        hour = datetime.now().hour
        
        # Днем отправляем меньше сообщений за раз
        if 8 <= hour <= 20:  # Дневное время
            return random.randint(3, 8)
        else:  # Вечер/ночь
            return random.randint(5, 12)
    
    def should_take_break(self, messages_sent: int) -> Tuple[bool, float]:
        """
        Определить, нужен ли перерыв
        
        Args:
            messages_sent: Количество отправленных сообщений подряд
            
        Returns:
            (нужен_ли_перерыв, длительность_перерыва)
        """
        # После каждой пачки - небольшой перерыв
        if messages_sent >= self.get_recommended_batch_size():
            break_time = random.uniform(30.0, 180.0)  # 30 сек - 3 мин
            return True, break_time
        
        # Редкий длинный перерыв
        if random.random() < 0.05:  # 5% шанс
            break_time = random.uniform(300.0, 600.0)  # 5-10 мин
            return True, break_time
        
        return False, 0.0

# Пример использования
if __name__ == "__main__":
    anti_ban = AntiBanSystem()
    
    print("🔍 Тестирование системы защиты от бана:")
    
    for i in range(15):
        can_send, reason = anti_ban.check_limits()
        
        if can_send:
            delay = anti_ban.get_smart_delay()
            print(f"{i+1}. Можно отправлять. Задержка: {delay} сек")
            
            # Записываем "отправленное" сообщение
            anti_ban.record_message_sent(chat_id=12345, message="Тестовое сообщение")
            
            # Проверяем нужен ли перерыв
            need_break, break_time = anti_ban.should_take_break(i+1)
            if need_break:
                print(f"   ⏸️ Нужен перерыв: {break_time} сек")
                break
        else:
            print(f"{i+1}. {reason}")
            break
    
    anti_ban.save_history()
    print(f"📊 Всего сообщений: {anti_ban.sent_messages_count}")
