"""
Главный модуль Telegram-бота для подбора щеток Goodyear.
"""
import os
import logging
import asyncio
from typing import Dict, Any, Optional, List

from telegram.ext import (
    Application, CallbackQueryHandler, CommandHandler,
    ContextTypes, MessageHandler as TelegramMessageHandler, filters
)

from config import Config
from utils.database import Database
from utils.user_manager import UserManager
from utils.synonyms import SynonymManager
from utils.logging_utils import setup_logging
from handlers.message_handler import MessageHandler
from handlers.callback_handler import CallbackHandler
from handlers.command_handler import CommandHandler as BotCommandHandler

# Настройка логирования
setup_logging()
logger = logging.getLogger(__name__)

class WipersBot:
    """Основной класс Telegram-бота для подбора щеток."""
    
    def __init__(self):
        """Инициализация бота."""
        # Проверка конфигурации
        if not Config.validate():
            logger.error("Ошибка валидации конфигурации. Бот не может быть запущен.")
            return
        
        # Инициализация компонентов
        self.db = Database()
        self.user_manager = UserManager()
        self.synonym_manager = SynonymManager("synonyms.csv", reload_interval=5)
        
        # Инициализация обработчиков
        self.message_handler = MessageHandler(self.db, self.user_manager, self.synonym_manager)
        self.callback_handler = CallbackHandler(self.db, self.user_manager)
        self.command_handler = BotCommandHandler(self.user_manager)
        
        # Инициализация приложения
        self.application = Application.builder().token(Config.TELEGRAM_TOKEN).build()
        
        # Регистрация обработчиков
        self._register_handlers()
        
        logger.info("Бот инициализирован успешно")
    
    def _register_handlers(self) -> None:
        """Регистрирует обработчики команд и сообщений."""
        # Обработчики команд
        self.application.add_handler(CommandHandler("start", self.command_handler.start))
        self.application.add_handler(CommandHandler("help", self.command_handler.help))
        self.application.add_handler(CommandHandler("stats", self.command_handler.stats))
        
        self.application.add_handler(CommandHandler("feedback", self.command_handler.feedback))
        self.application.add_handler(CommandHandler("cancel", self.command_handler.cancel))
        self.application.add_handler(CommandHandler("brand", self.command_handler.brand))  # Новая команда
        
        # Обработчик callback-запросов
        self.application.add_handler(CallbackQueryHandler(self.callback_handler.handle_callback_query))
        
        # Обработчик текстовых сообщений
        self.application.add_handler(TelegramMessageHandler(
            filters.TEXT & ~filters.COMMAND, 
            self._handle_message
        ))
        
        logger.info("Обработчики зарегистрированы")
    
    async def _handle_message(self, update, context) -> None:
        """
        Обрабатывает текстовые сообщения.
        
        Args:
            update: Объект обновления Telegram
            context: Контекст обработчика
        """
        # Проверяем, не ожидается ли отзыв
        if await self.command_handler.handle_feedback(update, context):
            return
        
        # Обрабатываем сообщение как поисковый запрос
        await self.message_handler.handle_message(update, context)
    
    def run(self) -> None:
        """Запускает бота."""
        try:
            logger.info("Запуск бота...")
            self.application.run_polling()
        except Exception as e:
            logger.error(f"Ошибка при запуске бота: {e}")
    
    def stop(self) -> None:
        """Останавливает бота."""
        try:
            logger.info("Остановка бота...")
            self.application.stop()
            self.synonym_manager.stop()
        except Exception as e:
            logger.error(f"Ошибка при остановке бота: {e}")

if __name__ == "__main__":
    bot = WipersBot()
    bot.run()