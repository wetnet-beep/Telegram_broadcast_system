# -*- coding: utf-8 -*-
"""
МОДУЛЬ ДЛЯ РАБОТЫ С TELEGRAM API
Использует Telethon для асинхронной работы
"""
import asyncio
import json
import os
from datetime import datetime
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty, InputPeerChannel, InputPeerChat
import config

class TelegramUserClient:
    """Класс для работы с Telegram аккаунтом пользователя"""
    
    def __init__(self, api_id: str = None, api_hash: str = None, phone: str = None):
        """
        Инициализация клиента Telegram
        
        Args:
            api_id: API ID из my.telegram.org
            api_hash: API Hash из my.telegram.org
            phone: Номер телефона с кодом страны
        """
        self.api_id = api_id or config.Config.API_ID
        self.api_hash = api_hash or config.Config.API_HASH
        self.phone = phone or config.Config.PHONE_NUMBER
        self.client = None
        self.is_connected = False
        self.session_file = config.Config.SESSION_FILE
        
    async def connect(self) -> bool:
        """
        Подключение к Telegram
        
        Returns:
            True если успешно
        """
        try:
            print("🔗 Подключение к Telegram...")
            
            # Создаем клиента
            self.client = TelegramClient(
                session=self.session_file,
                api_id=int(self.api_id),
                api_hash=self.api_hash,
                device_model="Telegram Broadcast System",
                system_version="1.0",
                app_version="2.0"
            )
            
            # Подключаемся
            await self.client.start(phone=self.phone)
            
            # Проверяем подключение
            me = await self.client.get_me()
            print(f"✅ Подключено как: {me.first_name} (@{me.username})")
            
            self.is_connected = True
            return True
            
        except Exception as e:
            print(f"❌ Ошибка подключения: {e}")
            return False
    
    async def disconnect(self):
        """Отключение от Telegram"""
        if self.client and self.is_connected:
            await self.client.disconnect()
            self.is_connected = False
            print("🔌 Отключено от Telegram")
    
    async def get_all_chats(self, limit: int = 200) -> list:
        """
        Получить список всех чатов
        
        Args:
            limit: Максимальное количество чатов
            
        Returns:
            Список словарей с информацией о чатах
        """
        if not self.is_connected:
            print("⚠️ Сначала подключитесь к Telegram")
            return []
        
        try:
            print("📋 Получение списка чатов...")
            
            # Получаем диалоги
            dialogs = await self.client(GetDialogsRequest(
                offset_date=None,
                offset_id=0,
                offset_peer=InputPeerEmpty(),
                limit=limit,
                hash=0
            ))
            
            chats = []
            for dialog in dialogs.chats:
                chat_info = {
                    'id': dialog.id,
                    'title': getattr(dialog, 'title', ''),
                    'username': getattr(dialog, 'username', ''),
                    'type': type(dialog).__name__,
                    'participants_count': getattr(dialog, 'participants_count', 0)
                }
                chats.append(chat_info)
            
            print(f"✅ Найдено {len(chats)} чатов")
            return chats
            
        except Exception as e:
            print(f"❌ Ошибка при получении чатов: {e}")
            return []
    
    async def send_message(self, chat_id: int, message: str, 
                          delay_before: float = 0, delay_after: float = 0) -> bool:
        """
        Отправить сообщение в чат
        
        Args:
            chat_id: ID чата
            message: Текст сообщения
            delay_before: Задержка перед отправкой (сек)
            delay_after: Задержка после отправки (сек)
            
        Returns:
            True если успешно
        """
        if not self.is_connected:
            print("⚠️ Сначала подключитесь к Telegram")
            return False
        
        try:
            # Задержка перед отправкой
            if delay_before > 0:
                print(f"⏳ Задержка {delay_before} сек...")
                await asyncio.sleep(delay_before)
            
            # Получаем entity чата
            entity = await self.client.get_entity(chat_id)
            
            # Отправляем сообщение
            await self.client.send_message(entity=entity, message=message)
            
            print(f"✅ Сообщение отправлено в чат {chat_id}")
            
            # Задержка после отправки
            if delay_after > 0:
                await asyncio.sleep(delay_after)
            
            return True
            
        except Exception as e:
            print(f"❌ Ошибка отправки сообщения: {e}")
            return False
    
    async def get_chat_members(self, chat_id: int, limit: int = 100) -> list:
        """
        Получить список участников чата
        
        Args:
            chat_id: ID чата
            limit: Максимальное количество участников
            
        Returns:
            Список участников
        """
        if not self.is_connected:
            return []
        
        try:
            entity = await self.client.get_entity(chat_id)
            participants = await self.client.get_participants(entity, limit=limit)
            
            members = []
            for participant in participants:
                member_info = {
                    'id': participant.id,
                    'first_name': getattr(participant, 'first_name', ''),
                    'last_name': getattr(participant, 'last_name', ''),
                    'username': getattr(participant, 'username', '')
                }
                members.append(member_info)
            
            return members
            
        except Exception as e:
            print(f"❌ Ошибка получения участников: {e}")
            return []
    
    async def save_session_string(self) -> str:
        """
        Сохранить сессию как строку для повторного использования
        
        Returns:
            Строка сессии
        """
        if not self.is_connected:
            return ""
        
        session_string = self.client.session.save()
        
        # Сохраняем в файл
        with open("session_string.txt", "w") as f:
            f.write(session_string)
        
        print("✅ Сессия сохранена в session_string.txt")
        return session_string

# Синхронные обертки для удобства
class TelegramSyncClient:
    """Синхронная обертка для Telegram клиента"""
    
    def __init__(self):
        self.async_client = TelegramUserClient()
        self.loop = asyncio.new_event_loop()
    
    def connect(self) -> bool:
        """Синхронное подключение"""
        return self.loop.run_until_complete(self.async_client.connect())
    
    def disconnect(self):
        """Синхронное отключение"""
        self.loop.run_until_complete(self.async_client.disconnect())
        self.loop.close()
    
    def get_all_chats(self, limit: int = 200) -> list:
        """Синхронное получение чатов"""
        return self.loop.run_until_complete(self.async_client.get_all_chats(limit))
    
    def send_message(self, chat_id: int, message: str, 
                    delay_before: float = 0, delay_after: float = 0) -> bool:
        """Синхронная отправка сообщения"""
        return self.loop.run_until_complete(
            self.async_client.send_message(chat_id, message, delay_before, delay_after)
        )

# Пример использования
if __name__ == "__main__":
    # Получаем данные от пользователя
    api_id = input("Введите API ID: ").strip()
    api_hash = input("Введите API Hash: ").strip()
    phone = input("Введите номер телефона: ").strip()
    
    # Создаем и подключаем клиент
    client = TelegramSyncClient()
    client.async_client.api_id = api_id
    client.async_client.api_hash = api_hash
    client.async_client.phone = phone
    
    if client.connect():
        # Получаем чаты
        chats = client.get_all_chats(limit=50)
        for chat in chats[:5]:  # Показываем первые 5
            print(f"{chat['title']} (ID: {chat['id']})")
        
        client.disconnect()
