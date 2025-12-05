# -*- coding: utf-8 -*-
"""
МЕНЕДЖЕР ЧАТОВ ДЛЯ РАССЫЛКИ
Управление списками чатов, группами, избранными
"""
import json
import os
from typing import List, Dict, Set
from datetime import datetime
import config

class ChatManager:
    """Управление чатами для рассылки"""
    
    def __init__(self):
        self.chats_db_file = config.Config.CHATS_DB
        self.chats = self.load_chats()
        self.categories = {
            'favorites': set(),  # Избранные чаты
            'groups': set(),     # Группы
            'channels': set(),   # Каналы
            'users': set(),      # Личные чаты
            'blacklist': set()   # Заблокированные чаты
        }
        self.load_categories()
    
    def load_chats(self) -> Dict[int, Dict]:
        """Загрузить чаты из базы данных"""
        try:
            if os.path.exists(self.chats_db_file):
                with open(self.chats_db_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Конвертируем ключи обратно в int (JSON сохраняет как строку)
                    return {int(k): v for k, v in data.items()}
        except (json.JSONDecodeError, FileNotFoundError) as e:
            print(f"⚠️ Ошибка загрузки чатов: {e}")
        
        return {}
    
    def save_chats(self):
        """Сохранить чаты в базу данных"""
        try:
            with open(self.chats_db_file, 'w', encoding='utf-8') as f:
                json.dump(self.chats, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Ошибка сохранения чатов: {e}")
    
    def load_categories(self):
        """Загрузить категории чатов"""
        try:
            if os.path.exists('chat_categories.json'):
                with open('chat_categories.json', 'r') as f:
                    data = json.load(f)
                    for category, chat_list in data.items():
                        self.categories[category] = set(chat_list)
        except (FileNotFoundError, json.JSONDecodeError):
            pass
    
    def save_categories(self):
        """Сохранить категории чатов"""
        try:
            data = {k: list(v) for k, v in self.categories.items()}
            with open('chat_categories.json', 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"❌ Ошибка сохранения категорий: {e}")
    
    def add_chat(self, chat_id: int, title: str, username: str = "", 
                chat_type: str = "unknown", members_count: int = 0):
        """
        Добавить новый чат
        
        Args:
            chat_id: ID чата
            title: Название чата
            username: Юзернейм (если есть)
            chat_type: Тип чата (group, channel, private)
            members_count: Количество участников
        """
        chat_info = {
            'id': chat_id,
            'title': title,
            'username': username,
            'type': chat_type,
            'members_count': members_count,
            'added_date': datetime.now().isoformat(),
            'last_message_sent': None,
            'message_count': 0,
            'is_active': True
        }
        
        self.chats[chat_id] = chat_info
        
        # Автоматически определяем категорию
        if chat_type == 'Channel':
            self.categories['channels'].add(chat_id)
        elif chat_type == 'Chat' or chat_type == 'ChatForbidden' or members_count > 2:
            self.categories['groups'].add(chat_id)
        else:
            self.categories['users'].add(chat_id)
        
        self.save_chats()
        self.save_categories()
        print(f"✅ Чат добавлен: {title} (ID: {chat_id})")
    
    def remove_chat(self, chat_id: int):
        """Удалить чат из всех списков"""
        if chat_id in self.chats:
            del self.chats[chat_id]
            
            # Удаляем из всех категорий
            for category in self.categories.values():
                category.discard(chat_id)
            
            self.save_chats()
            self.save_categories()
            print(f"🗑️ Чат удален: ID {chat_id}")
    
    def add_to_favorites(self, chat_id: int):
        """Добавить чат в избранное"""
        if chat_id in self.chats:
            self.categories['favorites'].add(chat_id)
            self.save_categories()
            print(f"⭐ Чат добавлен в избранное: {self.chats[chat_id]['title']}")
    
    def remove_from_favorites(self, chat_id: int):
        """Удалить чат из избранного"""
        self.categories['favorites'].discard(chat_id)
        self.save_categories()
    
    def add_to_blacklist(self, chat_id: int, reason: str = ""):
        """Добавить чат в черный список"""
        if chat_id in self.chats:
            self.categories['blacklist'].add(chat_id)
            self.chats[chat_id]['is_active'] = False
            self.chats[chat_id]['blacklist_reason'] = reason
            self.save_categories()
            self.save_chats()
            print(f"🚫 Чат добавлен в черный список: {self.chats[chat_id]['title']}")
    
    def is_chat_allowed(self, chat_id: int) -> bool:
        """
        Проверить, можно ли отправлять в этот чат
        
        Args:
            chat_id: ID чата
            
        Returns:
            True если можно отправлять
        """
        # Проверяем черный список
        if chat_id in self.categories['blacklist']:
            return False
        
        # Проверяем активность чата
        if chat_id in self.chats and not self.chats[chat_id].get('is_active', True):
            return False
        
        return True
    
    def get_chats_by_category(self, category: str) -> List[int]:
        """
        Получить чаты определенной категории
        
        Args:
            category: Категория (favorites, groups, channels, users)
            
        Returns:
            Список ID чатов
        """
        if category in self.categories:
            return list(self.categories[category])
        return []
    
    def get_all_active_chats(self) -> List[int]:
        """Получить все активные чаты"""
        active_chats = []
        for chat_id, chat_info in self.chats.items():
            if chat_info.get('is_active', True) and self.is_chat_allowed(chat_id):
                active_chats.append(chat_id)
        return active_chats
    
    def get_chats_for_broadcast(self, limit: int = 50, 
                               category: str = None) -> List[int]:
        """
        Получить чаты для рассылки с учетом приоритетов
        
        Args:
            limit: Максимальное количество чатов
            category: Специфическая категория (опционально)
            
        Returns:
            Список ID чатов для рассылки
        """
        # Определяем, из каких категорий брать чаты
        if category and category in self.categories:
            source_categories = [category]
        else:
            # Приоритет: избранное → группы → каналы → пользователи
            source_categories = ['favorites', 'groups', 'channels', 'users']
        
        result = []
        for cat in source_categories:
            if len(result) >= limit:
                break
            
            chats_in_category = self.get_chats_by_category(cat)
            # Фильтруем активные чаты
            active_chats = [cid for cid in chats_in_category if self.is_chat_allowed(cid)]
            
            # Добавляем до лимита
            remaining = limit - len(result)
            result.extend(active_chats[:remaining])
        
        return result
    
    def update_chat_stats(self, chat_id: int, message_sent: bool = True):
        """Обновить статистику чата"""
        if chat_id in self.chats:
            if message_sent:
                self.chats[chat_id]['last_message_sent'] = datetime.now().isoformat()
                self.chats[chat_id]['message_count'] = self.chats[chat_id].get('message_count', 0) + 1
            self.save_chats()
    
    def search_chats(self, query: str) -> List[Dict]:
        """
        Поиск чатов по названию или юзернейму
        
        Args:
            query: Строка для поиска
            
        Returns:
            Список найденных чатов
        """
        results = []
        query_lower = query.lower()
        
        for chat_id, chat_info in self.chats.items():
            title = chat_info.get('title', '').lower()
            username = chat_info.get('username', '').lower()
            
            if query_lower in title or query_lower in username:
                results.append(chat_info)
        
        return results
    
    def import_chats_from_list(self, chat_list: List[Dict]):
        """Импортировать чаты из списка"""
        for chat in chat_list:
            self.add_chat(
                chat_id=chat.get('id'),
                title=chat.get('title', 'Unknown'),
                username=chat.get('username', ''),
                chat_type=chat.get('type', 'unknown'),
                members_count=chat.get('participants_count', 0)
            )
    
    def export_chats(self, category: str = None) -> List[Dict]:
        """
        Экспортировать чаты
        
        Args:
            category: Категория для экспорта (опционально)
            
        Returns:
            Список чатов
        """
        if category:
            chat_ids = self.get_chats_by_category(category)
            return [self.chats.get(cid, {}) for cid in chat_ids if cid in self.chats]
        else:
            return list(self.chats.values())

# Пример использования
if __name__ == "__main__":
    manager = ChatManager()
    
    # Пример добавления чатов
    test_chats = [
        {'id': 123456, 'title': 'Test Group', 'type': 'Chat', 'participants_count': 10},
        {'id': 789012, 'title': 'News Channel', 'type': 'Channel', 'participants_count': 1000},
        {'id': 345678, 'title': 'John Doe', 'type': 'User', 'participants_count': 1}
    ]
    
    print("📥 Импорт тестовых чатов...")
    manager.import_chats_from_list(test_chats)
    
    # Добавляем один в избранное
    manager.add_to_favorites(123456)
    
    # Получаем чаты для рассылки
    broadcast_chats = manager.get_chats_for_broadcast(limit=10)
    print(f"📨 Чаты для рассылки: {len(broadcast_chats)}")
    
    # Поиск чатов
    search_results = manager.search_chats("test")
    print(f"🔍 Найдено чатов: {len(search_results)}")
    
    # Сохраняем
    manager.save_chats()
