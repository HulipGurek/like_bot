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
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

MODELS_PER_PAGE = 100  # Можно вынести в Config

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
                        caption="👋 <b>Привет!</b>\n\nЯ помогу подобрать подходящие щётки стеклоочистителя для вашего автомобиля.\n\n"
                                "Напишите марку и следуйте моим инструкциям, например:\n"
                                "• Lada • KIA • Renault •\n\n"                                

                                "/help - Справка по использованию\n"
                                ,
                        parse_mode='HTML'
                    )
            else:
                await update.message.reply_text(
                    f"👋 <b>Привет!</b>\n\nЯ помогу подобрать подходящие щётки стеклоочистителя для вашего автомобиля.\n\n"
                                "Напишите марку и следуйте инструкциям, например:\n"
                                "• Lada • KIA • Renault •\n\n"                                

                                "/help - Справка по использованию\n"
                                        ,
                    parse_mode='HTML'
                )
        except Exception as e:
            logger.error(f"Не удалось отправить приветственное сообщение: {e}")
            await update.message.reply_text(
                "👋 <b>Привет!</b>\n\nЯ помогу подобрать подходящие щётки стеклоочистителя для вашего автомобиля.\n\n"
                                "Напишите марку и следуйте моим инструкциям, например:\n"
                                "• Lada • KIA • Renault •\n\n"                                

                                "/help - Справка по использованию\n",
                parse_mode='HTML'
            )
            
    async def show_models_with_pagination(self, update, context, brand: str, page: int = 0):
        models = self.user_manager.get_models_for_brand(brand)
        # 1. Приводим к строке и убираем пробелы
        models = [str(m).strip() for m in models]
        # 2. Сортируем по всей строке
        models = sorted(models, key=lambda m: m.upper())

        # Для отладки, выведи в консоль — увидишь, если есть лишние пробелы или не строки
        print("MODELS:", models)

        total = len(models)
        start = page * MODELS_PER_PAGE
        end = start + MODELS_PER_PAGE
        current_models = models[start:end]

        if not current_models:
            await update.message.reply_text(f"Не найдено моделей для марки {brand.title()}.")
            return

        buttons = []
        for model in current_models:
            model_id = self.user_manager.store_callback_data({"brand": brand, "model": model})
            buttons.append([InlineKeyboardButton(model, callback_data=f"model_{model_id}")])

        nav_buttons = []
        if page > 0:
            nav_buttons.append(InlineKeyboardButton("⬅️ Назад", callback_data=f"models_page_{page-1}_{brand}"))
        if end < total:
            nav_buttons.append(InlineKeyboardButton("➡️ Далее", callback_data=f"models_page_{page+1}_{brand}"))
        if nav_buttons:
            buttons.append(nav_buttons)
        buttons.append([InlineKeyboardButton("🔄 Новый поиск", callback_data="new_search")])

        await update.message.reply_text(
            f"<b>Выберите модель для {brand.title()}:</b>\nПоказано {start+1}-{min(end, total)} из {total}",
            reply_markup=InlineKeyboardMarkup(buttons),
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
            "Этот бот поможет подобрать щётки Goodyear для вашего автомобиля.\n\n"
            "<b>Как пользоваться:</b>\n"
            "1. Напишите марку\n"
            "2. Выберите точную модель из списка\n"
            "3. Выберите тип и вид щётки\n"
            "4. Выберите маркетплейс для покупки\n\n"

            "<b>Доступные команды:</b>\n"
            "/start - Начать работу с ботом\n"
            "/help - Показать эту справку\n"
            "/brand - Поиск по марке автомобиля\n"
            "/feedback - Отправить отзыв о работе бота\n\n"
            "<b>Советы:</b>\n"
            "• Вы можете указать год выпуска автомобиля для более точного поиска\n"
            
            "• Используйте команду /brand для поиска всех моделей определенной марки\n"
            "• Оставить отзыв можно использовав команду /feedback",
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
            "Отправьте сообщение с вашим отзывом или нажмите ➡︎ /cancel для отмены.",
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
        await self.show_models_with_pagination(update, context, brand_query, page=0)
    
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
                "✅ Спасибо за ваш отзыв! Мы обязательно учтем его при улучшении бота. /start"
            )
        except Exception as e:
            logger.error(f"Ошибка при сохранении отзыва: {e}")
            await update.message.reply_text(
                "⚠️ Произошла ошибка при сохранении отзыва. Пожалуйста, попробуйте позже. /start"
            )
        
        return True