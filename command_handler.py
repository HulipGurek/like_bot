"""
Модуль для обработки команд бота.
"""
import logging
import os
from typing import Dict, Any, Optional

from telegram import Update
from telegram.ext import ContextTypes

from config import Config
from utils.user_manager import UserManager
from utils.logging_utils import log_user_action

logger = logging.getLogger(__name__)

class CommandHandler:
    """Класс для обработки команд бота."""
    
    def __init__(self, user_manager: UserManager):
        """
        Инициализация обработчика команд.
        
        Args:
            user_manager: Менеджер пользователей
        """
        self.user_manager = user_manager
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обрабатывает команду /start.
        
        Args:
            update: Объект обновления Telegram
            context: Контекст обработчика
        """
        user = update.effective_user
        self.user_manager.register_user(user.id)
        log_user_action(user.id, user.username, "START")
        
        try:
            # Проверка наличия видео
            video_path = os.path.join(Config.WIPER_TYPES_IMG_DIR, "gy_video.mp4")
            if os.path.exists(video_path):
                with open(video_path, "rb") as video:
                    await update.message.reply_video(
                        video=video,
                        caption="👋 <b>Приветствую!</b>\nЯ помогу подобрать лучшие щетки Goodyear для вашего авто.\n\n"
                                "Просто напишите марку или модель автомобиля, например:\n"
                                "• BMW 5\n• KIA RIO\n• Audi Q7 2019\n\n"
                                "Команды:\n"
                                "/help - Справка по использованию\n"
                                ,
                        parse_mode='HTML'
                    )
            else:
                await update.message.reply_text(
                    f"👋 <b>Приветствую!</b>\n"
                    "Я помогу подобрать лучшие щетки Goodyear для вашего авто.\n\n"
                    "Просто напишите марку или модель автомобиля, например:\n"
                    "• BMW 5\n• KIA RIO\n• Audi Q7 2019\n\n"
                    "Команды:\n"
                    "/help - Справка по использованию\n"
                                        ,
                    parse_mode='HTML'
                )
        except Exception as e:
            logger.error(f"Не удалось отправить приветственное сообщение: {e}")
            await update.message.reply_text(
                "👋 <b>Приветствую!</b>\n"
                "Я помогу подобрать лучшие щетки Goodyear для вашего авто.\n\n"
                "Просто напишите марку или модель автомобиля, например:\n"
                "• BMW 5\n• KIA RIO\n• Nissan X trail",
                parse_mode='HTML'
            )
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обрабатывает команду /help.
        
        Args:
            update: Объект обновления Telegram
            context: Контекст обработчика
        """
        user = update.effective_user
        log_user_action(user.id, user.username, "HELP")
        
        await update.message.reply_text(
            "<b>Справка по использованию бота</b>\n\n"
            "Этот бот поможет вам подобрать щетки Goodyear для вашего автомобиля.\n\n"
            "<b>Как пользоваться:</b>\n"
            "1. Напишите марку или модель автомобиля (например, 'BMW 5', 'KIA RIO', 'Audi Q7 2019')\n"
            "2. Выберите точную модель из списка\n"
            "3. Выберите тип корпуса щетки\n"
            "4. Выберите вид щетки\n"
            "5. Выберите комплект или одну щетку\n"
            "6. Перейдите по ссылке для покупки\n\n"
            "<b>Доступные команды:</b>\n"
            "/start - Начать работу с ботом\n"
            "/help - Показать эту справку\n"
            "/brand - Поиск по марке автомобиля\n"
            "/feedback - Отправить отзыв о работе бота\n\n"
            "<b>Советы:</b>\n"
            "• Вы можете указать год выпуска автомобиля для более точного поиска\n"
            "• Добавляйте автомобили в избранное, чтобы быстро находить их в будущем\n"
            "• Используйте команду /brand для поиска всех моделей определенной марки\n"
            "• Если у вас возникли проблемы, используйте команду /feedback",
            parse_mode='HTML'
        )
    async def stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обрабатывает команду /stats.
        
        Args:
            update: Объект обновления Telegram
            context: Контекст обработчика
        """
        user = update.effective_user
        log_user_action(user.id, user.username, "STATS")
        
        stats = self.user_manager.get_stats()
        
        await update.message.reply_text(
            f"<b>Статистика использования бота</b>\n\n"
            f"👥 Всего обращений к боту: {stats['all_users_count']}\n"
            f"🧑‍💻 Уникальных пользователей: {stats['unique_users']}",
            parse_mode='HTML'
        )
    
    async def favorites(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обрабатывает команду /favorites.
        
        Args:
            update: Объект обновления Telegram
            context: Контекст обработчика
        """
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        user = update.effective_user
        log_user_action(user.id, user.username, "FAVORITES")
        
        favorites = self.user_manager.get_favorites(user.id)
        
        if not favorites:
            await update.message.reply_text(
                "У вас пока нет избранных автомобилей. Добавьте автомобили в избранное при поиске."
            )
            return
        
        # Формирование сообщения
        message = f"<b>Ваши избранные автомобили (1-{min(Config.PAGINATION_SIZE, len(favorites))} из {len(favorites)}):</b>\n\n"
        
        # Создание кнопок
        buttons = []
        
        for i, car in enumerate(favorites[:Config.PAGINATION_SIZE]):
            brand = car.get('brand', '')
            model = car.get('model', '')
            years = car.get('years', '')
            
            message += f"{i+1}. {brand.title()} {model.upper()} ({years})\n"
            
            # Создание кнопки для выбора автомобиля
            car_id = self.user_manager.store_callback_data(car)
            buttons.append([InlineKeyboardButton(
                f"{i+1}. {brand.title()} {model.upper()} ({years})",
                callback_data=f"model_{car_id}"
            )])
            
            # Создание кнопки для удаления из избранного
            remove_id = self.user_manager.store_callback_data({"index": i})
            buttons.append([InlineKeyboardButton(
                f"❌ Удалить {brand.title()} {model.upper()} из избранного",
                callback_data=f"remove_favorite_{remove_id}"
            )])
        
        # Добавление кнопок пагинации
        pagination_buttons = []
        
        if len(favorites) > Config.PAGINATION_SIZE:
            pagination_buttons.append(InlineKeyboardButton("➡️ Вперед", callback_data="page_1"))
        
        if pagination_buttons:
            buttons.append(pagination_buttons)
        
        # Добавление кнопки для нового поиска
        buttons.append([InlineKeyboardButton("🔄 Новый поиск", callback_data="new_search")])
        
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode='HTML'
        )
    
    async def feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обрабатывает команду /feedback.
        
        Args:
            update: Объект обновления Telegram
            context: Контекст обработчика
        """
        user = update.effective_user
        log_user_action(user.id, user.username, "FEEDBACK")
        
        # Сохраняем в контексте, что пользователь отправляет отзыв
        context.user_data['waiting_for_feedback'] = True
        
        await update.message.reply_text(
            "📝 <b>Отправка отзыва</b>\n\n"
            "Пожалуйста, напишите ваш отзыв о работе бота. Ваше мнение поможет нам улучшить сервис.\n\n"
            "Отправьте сообщение с вашим отзывом или /cancel для отмены.",
            parse_mode='HTML'
        )
    
    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обрабатывает команду /cancel.
        
        Args:
            update: Объект обновления Telegram
            context: Контекст обработчика
        """
        user = update.effective_user
        log_user_action(user.id, user.username, "CANCEL")
        
        # Сбрасываем все ожидания ввода
        if 'waiting_for_feedback' in context.user_data:
            del context.user_data['waiting_for_feedback']
            await update.message.reply_text("❌ Отправка отзыва отменена.")
        else:
            await update.message.reply_text(
                "Введите марку или модель автомобиля для поиска щеток."
            )
    async def brand(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        '''
        Обрабатывает команду /brand для поиска по марке автомобиля.
        '''
        user = update.effective_user
        log_user_action(user.id, user.username, "BRAND_SEARCH")
        if 'waiting_for_brand' in context.user_data:
            del context.user_data['waiting_for_brand']
        if context.args and len(context.args) > 0:
            brand_query = ' '.join(context.args)
            await self._handle_brand_search(update, context, brand_query)
        else:
            await update.message.reply_text(
                "🚗 <b>Поиск по марке автомобиля</b>\n\n"
                "Пожалуйста, введите марку автомобиля для поиска.\n"
                "Например: <code>BMW</code> или <code>Toyota</code>",
                parse_mode='HTML'
            )
            context.user_data['waiting_for_brand'] = True

    async def _handle_brand_search(self, update: Update, context: ContextTypes.DEFAULT_TYPE, brand_query: str) -> None:
        """
        Обрабатывает поиск по марке автомобиля.
        
        Args:
            update: Объект обновления Telegram
            context: Контекст обработчика
            brand_query: Запрос марки автомобиля
        """
        from handlers.message_handler import MessageHandler
        
        # Создаем временный объект MessageHandler для использования его методов
        message_handler = MessageHandler(self.database, self.user_manager, self.synonym_manager)
        
        # Выполняем поиск по марке
        await message_handler.handle_brand_search(update, context, brand_query)
    
    async def handle_feedback(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
        """
        Обрабатывает отправку отзыва.
        
        Args:
            update: Объект обновления Telegram
            context: Контекст обработчика
            
        Returns:
            bool: True, если сообщение было обработано как отзыв, False в противном случае
        """
        if 'waiting_for_feedback' not in context.user_data:
            return False
        
        user = update.effective_user
        feedback_text = update.message.text
        
        # Логирование отзыва
        log_user_action(user.id, user.username, "FEEDBACK_SENT", feedback_text)
        
        # Сбрасываем ожидание отзыва
        del context.user_data['waiting_for_feedback']
        
        # Сохранение отзыва в файл
        try:
            os.makedirs(os.path.join(Config.LOGS_DIR, 'feedback'), exist_ok=True)
            feedback_file = os.path.join(Config.LOGS_DIR, 'feedback', f'feedback_{user.id}.txt')
            
            with open(feedback_file, 'a', encoding='utf-8') as f:
                from utils.logging_utils import get_current_utc
                f.write(f"[{get_current_utc()}] {user.id} ({user.username}): {feedback_text}\n")
            
            await update.message.reply_text(
                "✅ Спасибо за ваш отзыв! Мы обязательно учтем его при улучшении бота."
            )
        except Exception as e:
            logger.error(f"Ошибка при сохранении отзыва: {e}")
            await update.message.reply_text(
                "⚠️ Произошла ошибка при сохранении отзыва. Пожалуйста, попробуйте позже."
            )
        
        return True
