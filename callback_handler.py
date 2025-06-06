"""
Модуль для обработки callback-запросов.
"""
import os
import logging
from typing import List, Dict, Any, Optional, Tuple, Union

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto
)
from telegram.ext import ContextTypes

from config import Config
from utils.database import Database
from utils.user_manager import UserManager
from utils.logging_utils import log_user_action
from handlers.message_handler import MessageHandler
from utils.synonyms import SynonymManager
from utils.text_utils import translit_ru_to_en

logger = logging.getLogger(__name__)

class CallbackHandler:
    """Класс для обработки callback-запросов."""
    
    def __init__(self, database: Database, user_manager: UserManager, synonym_manager: SynonymManager):
        self.db = database
        self.user_manager = user_manager
        self.synonym_manager = synonym_manager

    def translit_ru_to_en(text):
        # Простейший пример, замени на свою функцию если есть в utils.text_utils
        table = str.maketrans(
            "абвгдеёжзийклмнопрстуфхцчшщьыъэюя",
            "abvgdeejzijklmnoprstufhccss_y_eua"
        )
        return text.lower().translate(table)

    async def handle_callback_query(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        query = update.callback_query
        user = query.from_user
        try:
            await query.answer()
            if not hasattr(query, 'data') or not query.data:
                return
            data = query.data
            log_user_action(user.id, user.username, "BUTTON_CLICK", data)
            # --- ПОСТРАНИЧНЫЙ ВЫВОД МОДЕЛЕЙ ---
            if data.startswith("models_page_"):
                parts = data.split("_")
                page = int(parts[2])
                brand_query_raw = "_".join(parts[3:])  # Может быть кириллица

                # --- НОРМАЛИЗАЦИЯ БРЕНДА ---
                synonyms = self.synonym_manager.get_synonyms()
                brand_query_norm = brand_query_raw.strip().lower()
                canonical_brand = None

                # 1. Прямое совпадение
                all_brands = [b.lower() for b in self.db.cars_df['brand'].unique()]
                if brand_query_norm in all_brands:
                    canonical_brand = brand_query_norm
                else:
                    # 2. Поиск по синонимам
                    for canon, syns in synonyms.items():
                        all_syns = [canon] + (syns if isinstance(syns, list) else [syns])
                        all_syns_norm = [s.lower() for s in all_syns]
                        if brand_query_norm in all_syns_norm:
                            canonical_brand = canon.lower()
                            break
                # 3. Если не нашли — пробуем транслит
                if not canonical_brand and any('а' <= x <= 'я' for x in brand_query_norm):
                    brand_query_translit = translit_ru_to_en(brand_query_norm)
                    if brand_query_translit in all_brands:
                        canonical_brand = brand_query_translit
                # 4. Если всё равно не нашли — ищем частичное совпадение
                if not canonical_brand:
                    for brand in self.db.cars_df['brand'].unique():
                        if brand_query_norm in brand.lower():
                            canonical_brand = brand.lower()
                            break
                # 5. Если вообще ничего — fallback
                if not canonical_brand:
                    canonical_brand = brand_query_norm

                handler = MessageHandler(self.db, self.user_manager, self.synonym_manager)
                matches = self.db.cars_df[self.db.cars_df['brand'].str.lower() == canonical_brand]
                if matches.empty:
                    matches = self.db.cars_df[self.db.cars_df['brand'].str.lower().str.contains(canonical_brand)]
                matches = matches.sort_values(by=["model"], ascending=True, kind="stable")
                await handler.show_models_with_pagination(update, context, matches, canonical_brand, page, edit=True)
                return
            # --- Патч brand_search_fixes: расширенная обработка single_ ---
            if data.startswith("model_"):
                await self._handle_model_selection(query, context)
            elif data.startswith("frame_"):
                await self._handle_frame_selection(query, context)
            elif data.startswith("type_"):
                await self._handle_type_selection(query, context)
            elif data.startswith("kit_"):
                await self._handle_kit_selection(query, context)
            elif data.startswith("single_left_") or data.startswith("single_right_"):
                await self._handle_single_wiper_side_selection(query, context)
            elif data.startswith("single_"):
                await self._handle_single_wiper_selection(query, context)
            elif data == "new_search":
                await self._handle_new_search(query, context)
            elif data.startswith("back_to_frames_"):
                await self._handle_back_to_frames(query, context)
            elif data.startswith("back_to_types_"):
                await self._handle_back_to_types(query, context)
            elif data.startswith("add_favorite_"):
                await self._handle_add_favorite(query, context)
            elif data.startswith("view_favorites"):
                await self._handle_view_favorites(query, context)
            elif data.startswith("remove_favorite_"):
                await self._handle_remove_favorite(query, context)
            elif data.startswith("page_"):
                await self._handle_pagination(query, context)
        except Exception as e:
            logger.error(f"Ошибка при обработке кнопки: {str(e)}")
            log_user_action(user.id, user.username, "BUTTON_ERROR", getattr(query, "data", ""), str(e))
            try:
                await query.edit_message_text(
                    text="😔 Произошла ошибка при получении информации. Попробуйте ещё раз✨"
                )
            except Exception:
                pass

    async def _handle_single_wiper_selection(self, query: Update.callback_query, context: ContextTypes.DEFAULT_TYPE) -> None:
        '''
        Обрабатывает выбор одной щетки.
        '''
        type_id = query.data.replace("single_", "")
        store = self.user_manager.get_callback_data(type_id)
        if not store:
            await query.message.edit_text(
                text="⚠️ Не удалось найти информацию о выбранной щетке. Пожалуйста, начните поиск заново. /start"
            )
            return
        buttons = []
        driver_size = store.get('driver_size')
        pass_size = store.get('pass_size')
        if driver_size:
            buttons.append([InlineKeyboardButton(f"➡️ Правая ({driver_size} мм)", callback_data=f"single_left_{type_id}")])
        if pass_size:
            buttons.append([InlineKeyboardButton(f"⬅️ Левая ({pass_size} мм)", callback_data=f"single_right_{type_id}")])
        buttons.append([InlineKeyboardButton("🔙 Назад", callback_data=f"type_{type_id}")])
        buttons.append([InlineKeyboardButton("🔄 Новый поиск", callback_data="new_search")])
        car_rows = self.db.cars_df[
            (self.db.cars_df['brand'] == store.get('brand', '')) &
            (self.db.cars_df['model'] == store.get('model', '')) &
            (self.db.cars_df['years'] == store.get('years', ''))
        ]
        car_info = ""
        if not car_rows.empty:
            car_info = self.db.get_car_info(car_rows.iloc[0])
        frame = store.get('gy_frame', '')
        gy_type = store.get('gy_type', '')
        type_desc = ""
        if self.db.types_desc_df is not None:
            type_rows = self.db.types_desc_df[self.db.types_desc_df['gy_type'] == gy_type]
            if not type_rows.empty:
                desc = type_rows.iloc[0].get('description', '')
                if desc:
                    type_desc = f"\n\n<i>{desc}</i>"
        message = (
            f"{car_info}\n"
            f"<b>Выбран тип:</b> <i>{frame} {gy_type}</i>{type_desc}\n\n"
            f"<b>Выберите сторону для покупки одной щётки:</b>"
        )
        await query.message.edit_text(
            message,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode='HTML'
        )

    async def _handle_single_wiper_side_selection(self, query: Update.callback_query, context: ContextTypes.DEFAULT_TYPE) -> None:
        '''
        Обрабатывает выбор конкретной стороны для одной щетки.
        '''
        data = query.data
        is_left = data.startswith("single_left_")
        type_id = data.replace("single_left_", "").replace("single_right_", "")
        store = self.user_manager.get_callback_data(type_id)
        if not store:
            await query.message.edit_text(
                text="⚠️ Не удалось найти информацию о выбранной щетке. Пожалуйста, начните поиск заново. /start"
            )
            return
        frame = store.get('gy_frame', '')
        gy_type = store.get('gy_type', '')
        mount = store.get('mount', '')
        size = store.get('driver_size') if is_left else store.get('pass_size')
        side_name = "Правая" if is_left else "Левая"
        if not size:
            await query.message.edit_text(
                text=f"⚠️ Не удалось найти размер для {side_name.lower()} стороны. Пожалуйста, выберите другую сторону."
            )
            return
        ozon_url, wb_url = self.db.get_single_wiper_links(frame, gy_type, mount, size)
        car_rows = self.db.cars_df[
            (self.db.cars_df['brand'] == store.get('brand', '')) &
            (self.db.cars_df['model'] == store.get('model', '')) &
            (self.db.cars_df['years'] == store.get('years', ''))
        ]
        car_info = ""
        if not car_rows.empty:
            car_info = self.db.get_car_info(car_rows.iloc[0])
        type_desc = ""
        if self.db.types_desc_df is not None:
            type_rows = self.db.types_desc_df[self.db.types_desc_df['gy_type'] == gy_type]
            if not type_rows.empty:
                desc = type_rows.iloc[0].get('description', '')
                if desc:
                    type_desc = f"\n\n<i>{desc}</i>"
        message = (
            f"{car_info}\n"
            f"<b>Выбран тип:</b> <i>{frame} {gy_type}</i>{type_desc}\n\n"
            f"<b>{side_name} щётка ({size} мм)</b>\n\n"
            f"<b>Выберите магазин для покупки:</b>"
        )
        buttons = []
        if ozon_url and isinstance(ozon_url, str) and ozon_url.startswith("http"):
            buttons.append([InlineKeyboardButton("🌐 Купить на Ozon", url=ozon_url)])
        if wb_url and isinstance(wb_url, str) and wb_url.startswith("http"):
            buttons.append([InlineKeyboardButton("🟣 Купить на Wildberries", url=wb_url)])
        buttons.append([InlineKeyboardButton("🔙 Назад", callback_data=f"single_{type_id}")])
        buttons.append([InlineKeyboardButton("🔄 Новый поиск", callback_data="new_search")])
        await query.message.edit_text(
            message,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode='HTML'
        )



    
    async def _handle_model_selection(self, query: Update.callback_query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обрабатывает выбор модели автомобиля.
        
        Args:
            query: Объект callback-запроса
            context: Контекст обработчика
        """
        model_id = query.data.replace("model_", "")
        store = self.user_manager.get_callback_data(model_id)
        
        if not store:
            await query.message.edit_text(
                text="⚠️ Нет подходящих щёток.\n /start"
            )
            return
        
        car_rows = self.db.cars_df[
            (self.db.cars_df['brand'] == store.get('brand', '')) &
            (self.db.cars_df['model'] == store.get('model', '')) &
            (self.db.cars_df['years'] == store.get('years', ''))
        ]
        
        if car_rows.empty:
            await query.message.edit_text(
                text="⚠️ Нет подходящих щёток.\n /start"
            )
            return
        
        car = car_rows.iloc[0]
        car_info = self.db.get_car_info(car)
        
        mount = car['mount']
        driver_size = int(car['driver']) if str(car['driver']).isdigit() else None
        pass_size = int(car['passanger']) if str(car['passanger']).isdigit() else None
        
        # Получение доступных типов корпусов
        available_frames = self.db.get_available_frames(mount, [driver_size, pass_size])
        
        if available_frames.empty:
            await query.message.edit_text(
                car_info + "\n⚠️ К сожалению, для этого автомобиля нет подходящих щёток в нашем каталоге.",
                parse_mode='HTML'
            )
            return
        
        # Создание кнопок для выбора типа корпуса
        buttons = []
        for _, rowf in available_frames.iterrows():
            frame = rowf['gy_frame']
            frame_id = self.user_manager.store_callback_data({
                "brand": car['brand'],
                "model": car['model'],
                "years": car['years'],
                "mount": mount,
                "driver_size": driver_size,
                "pass_size": pass_size,
                "gy_frame": frame
            })
            btn = InlineKeyboardButton(str(frame), callback_data=f"frame_{frame_id}")
            buttons.append([btn])
        
      
        
        
        # Добавление кнопки для нового поиска
        buttons.append([InlineKeyboardButton("🔄 Новый поиск", callback_data="new_search")])
        
        await query.message.edit_text(
            car_info + "\n<b>Выберите тип:</b>",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode='HTML'
        )
    
    async def _handle_frame_selection(self, query: Update.callback_query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обрабатывает выбор типа корпуса щетки.
        
        Args:
            query: Объект callback-запроса
            context: Контекст обработчика
        """
        frame_id = query.data.replace("frame_", "")
        store = self.user_manager.get_callback_data(frame_id)
        
        if not store:
            await query.message.edit_text(
                text="⚠️ Не удалось найти информацию о выбранном корпусе. Пожалуйста, начните поиск заново. /start"
            )
            return
        
        mount = store['mount']
        driver_size = store['driver_size']
        pass_size = store['pass_size']
        frame = store['gy_frame']
        
        # Получение доступных видов щеток
        available_types = self.db.get_available_types(frame, mount, [driver_size, pass_size])
        
        if available_types.empty:
            await query.message.edit_text(
                text="⚠️ Не удалось найти подходящие виды щеток для выбранного корпуса. Пожалуйста, выберите другой корпус."
            )
            return
        
        # Если найден только один вид щетки, сразу переходим к нему
        if len(available_types) == 1:
            gy_type = available_types.iloc[0]['gy_type']
            type_id = self.user_manager.store_callback_data({
                **store, "gy_type": gy_type
            })
            await self._handle_type_selection_internal(query, store, gy_type, type_id, context)
            return
        
        # Создание кнопок для выбора вида щетки
        buttons = []
        for _, rowt in available_types.iterrows():
            gy_type = rowt['gy_type']
            type_id = self.user_manager.store_callback_data({**store, "gy_type": gy_type})
            buttons.append([InlineKeyboardButton(str(gy_type), callback_data=f"type_{type_id}")])

        # Кнопки "Назад" и "Новый поиск"
        back_to_frames_id = self.user_manager.store_callback_data({**store})
        buttons.append([InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_frames_{back_to_frames_id}")])
        buttons.append([InlineKeyboardButton("🔄 Новый поиск", callback_data="new_search")])

        # Получение информации об автомобиле
        car_rows = self.db.cars_df[
            (self.db.cars_df['brand'] == store.get('brand', '')) &
            (self.db.cars_df['model'] == store.get('model', '')) &
            (self.db.cars_df['years'] == store.get('years', ''))
        ]

        if car_rows.empty:
            await query.message.edit_text(
                text="⚠️ Не удалось найти информацию о выбранной модели. Пожалуйста, начните поиск заново. /start"
            )
            return

        car_info = self.db.get_car_info(car_rows.iloc[0])
        frame = store['gy_frame']

        # Формируем message только теперь!
        message = car_info + f"\n<b>Выберите вид щётки:</b>"

        # Отправляем картинку корпуса (если нужна)
        img_dir = Config.WIPER_TYPES_IMG_DIR
        img_filename = f"{frame}.png"
        img_path = os.path.join(img_dir, img_filename)
        if os.path.exists(img_path):
            with open(img_path, "rb") as photo:
                await query.message.reply_photo(photo=photo)

        # Теперь точно отправляем текст с кнопками
        await query.message.edit_text(
            message,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode='HTML'
        )
    
    async def _handle_type_selection(self, query: Update.callback_query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обрабатывает выбор вида щетки.
        
        Args:
            query: Объект callback-запроса
            context: Контекст обработчика
        """
        type_id = query.data.replace("type_", "")
        store = self.user_manager.get_callback_data(type_id)
        
        if not store:
            await query.message.edit_text(
                text="⚠️ Не удалось найти информацию о выбранном виде щетки. Пожалуйста, начните поиск заново. /start"
            )
            return
        
        gy_type = store['gy_type']
        await self._handle_type_selection_internal(query, store, gy_type, type_id, context)
    
    async def _handle_type_selection_internal(self, query: Update.callback_query, store: Dict[str, Any], 
                                             gy_type: str, type_id: str, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Внутренний метод для обработки выбора вида щетки.
        
        Args:
            query: Объект callback-запроса
            store: Данные из хранилища callback
            gy_type: Вид щетки
            type_id: Идентификатор типа
            context: Контекст обработчика
        """
        frame = store['gy_frame']
        mount = store['mount']
        driver_size = store['driver_size']
        pass_size = store['pass_size']
        
        
        # Получение ссылок на комплект щеток
        ozon_kit_url, wb_kit_url = self.db.get_wiper_kit_links(frame, gy_type, mount, driver_size, pass_size)
        
        # Создание кнопок
        buttons = []
        
        # Кнопка для комплекта щеток
        if ozon_kit_url or wb_kit_url:
            buttons.append([InlineKeyboardButton("🛒 Купить комплект щёток", callback_data=f"kit_{type_id}")])
        
        # Кнопка для одиночных щеток
        buttons.append([InlineKeyboardButton("🛒 Купить одну щётку", callback_data=f"single_{type_id}")])
        
        # Кнопка "Назад"
        back_to_frames_id = self.user_manager.store_callback_data({
            "brand": store.get('brand', ''),
            "model": store.get('model', ''),
            "years": store.get('years', ''),
            "mount": mount,
            "driver_size": driver_size,
            "pass_size": pass_size,
            "gy_frame": frame
        })
        buttons.append([InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_frames_{back_to_frames_id}")])
        buttons.append([InlineKeyboardButton("🔄 Новый поиск", callback_data="new_search")])

        # Получение информации об автомобиле
        car_rows = self.db.cars_df[
            (self.db.cars_df['brand'] == store.get('brand', '')) &
            (self.db.cars_df['model'] == store.get('model', '')) &
            (self.db.cars_df['years'] == store.get('years', ''))
        ]
        
        if car_rows.empty:
            await query.message.edit_text(
                text="⚠️ Не удалось найти информацию о выбранной модели. Пожалуйста, начните поиск заново. /start"
            )
            return
        
        car_info = self.db.get_car_info(car_rows.iloc[0])
        
        # Получение описания типа щетки
        type_desc = ""
        if self.db.types_desc_df is not None:
            type_rows = self.db.types_desc_df[self.db.types_desc_df['gy_type'] == gy_type]
            if not type_rows.empty:
                desc = type_rows.iloc[0].get('description', '')
                if desc:
                    type_desc = f"\n\n<i>{desc}</i>"
        
        # Формирование сообщения
        message = (
            f"{car_info}\n"
            f"<b>Выбран тип:</b> <i>{frame} {gy_type}</i>{type_desc}\n\n"
            f"<b>Что вы хотите сделать?</b>"
        )

        # ... всё что было ДО message ...
        message = (
            f"{car_info}\n"
            f"<b>Выбран тип:</b> <i>{frame} {gy_type}</i>{type_desc}\n\n"
            f"<b>Что вы хотите сделать?</b>"
        )

        
        img_dir = Config.WIPER_TYPES_IMG_DIR
        img_filename = f"{gy_type}.png"
        img_path = os.path.join(img_dir, img_filename)

        if os.path.exists(img_path):
            # 1. Отправляем фото (без caption)
            await context.bot.send_photo(
                chat_id=query.message.chat_id,
                photo=open(img_path, "rb")
            )

        # 2. Сразу после этого отправляем текст с кнопками (reply_markup)
        await context.bot.send_message(
            chat_id=query.message.chat_id,
            text=message,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode='HTML'
        )
    
    async def _handle_kit_selection(self, query: Update.callback_query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обрабатывает выбор комплекта щеток.
        
        Args:
            query: Объект callback-запроса
            context: Контекст обработчика
        """
        type_id = query.data.replace("kit_", "")
        store = self.user_manager.get_callback_data(type_id)
        
        if not store:
            await query.message.edit_text(
                text="⚠️ Не удалось найти информацию о выбранном комплекте. Пожалуйста, начните поиск заново. /start"
            )
            return
        
        frame = store['gy_frame']
        gy_type = store['gy_type']
        mount = store['mount']
        driver_size = store['driver_size']
        pass_size = store['pass_size']
        
        # Получение ссылок на комплект щеток
        ozon_kit_url, wb_kit_url = self.db.get_wiper_kit_links(frame, gy_type, mount, driver_size, pass_size)
        
        # Получение информации об автомобиле
        car_rows = self.db.cars_df[
            (self.db.cars_df['brand'] == store.get('brand', '')) &
            (self.db.cars_df['model'] == store.get('model', '')) &
            (self.db.cars_df['years'] == store.get('years', ''))
        ]
        
        car_info = ""
        if not car_rows.empty:
            car_info = self.db.get_car_info(car_rows.iloc[0])
        
        # Получение описания типа щетки
        type_desc = ""
        if self.db.types_desc_df is not None:
            type_rows = self.db.types_desc_df[self.db.types_desc_df['gy_type'] == gy_type]
            if not type_rows.empty:
                desc = type_rows.iloc[0].get('description', '')
                if desc:
                    type_desc = f"\n\n<i>{desc}</i>"
        
        # Формирование сообщения
        message = (
            f"{car_info}\n"
            f"<b>Выбран тип:</b> <i>{frame} {gy_type}</i>{type_desc}\n\n"
            f"<b>Выберите магазин для покупки комплекта щёток:</b>"
        )
        
        # Создание кнопок
        buttons = []
        
        if ozon_kit_url and isinstance(ozon_kit_url, str) and ozon_kit_url.startswith("http" ):
            buttons.append([InlineKeyboardButton("🌐 Комплект на Ozon", url=ozon_kit_url)])
        
        if wb_kit_url and isinstance(wb_kit_url, str) and wb_kit_url.startswith("http" ):
            buttons.append([InlineKeyboardButton("🟣 Комплект на Wildberries", url=wb_kit_url)])
        
        buttons.append([InlineKeyboardButton("🔙 Назад", callback_data=f"type_{type_id}")])
        buttons.append([InlineKeyboardButton("🔄 Новый поиск", callback_data="new_search")])

        await query.message.edit_text(
            message,
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode='HTML'
        )

    


    
    async def _handle_new_search(self, query: Update.callback_query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обрабатывает запрос на новый поиск.
        
        Args:
            query: Объект callback-запроса
            context: Контекст обработчика
        """
        await query.message.edit_text(
            text="Введите марку автомобиля:"
        )
    
    async def _handle_back_to_frames(self, query: Update.callback_query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обрабатывает возврат к выбору типа корпуса.
        
        Args:
            query: Объект callback-запроса
            context: Контекст обработчика
        """
        back_id = query.data.replace("back_to_frames_", "")
        store = self.user_manager.get_callback_data(back_id)
        
        if not store:
            await query.message.edit_text(
                text="⚠️ Не удалось вернуться к выбору корпуса. Пожалуйста, начните поиск заново. /start"
            )
            return
        
        # Получение информации об автомобиле
        car_rows = self.db.cars_df[
            (self.db.cars_df['brand'] == store.get('brand', '')) &
            (self.db.cars_df['model'] == store.get('model', '')) &
            (self.db.cars_df['years'] == store.get('years', ''))
        ]
        
        if car_rows.empty:
            await query.message.edit_text(
                text="⚠️ Не удалось найти информацию о выбранной модели. Пожалуйста, начните поиск заново. /start"
            )
            return
        
        car = car_rows.iloc[0]
        mount = car['mount']
        driver_size = int(car['driver']) if str(car['driver']).isdigit() else None
        pass_size = int(car['passanger']) if str(car['passanger']).isdigit() else None
        car_info = self.db.get_car_info(car)
        
        # Получение доступных типов корпусов
        available_frames = self.db.get_available_frames(mount, [driver_size, pass_size])
        
        if available_frames.empty:
            await query.message.edit_text(
                car_info + "\n⚠️ К сожалению, для этого автомобиля нет подходящих щёток в нашем каталоге.",
                parse_mode='HTML'
            )
            return
        
        # Создание кнопок для выбора типа корпуса
        buttons = []
        for _, rowf in available_frames.iterrows():
            frame = rowf['gy_frame']
            frame_id = self.user_manager.store_callback_data({
                **store,
                "mount": mount,
                "driver_size": driver_size,
                "pass_size": pass_size,
                "gy_frame": frame
            })
            btn = InlineKeyboardButton(str(frame), callback_data=f"frame_{frame_id}")
            buttons.append([btn])
        
        # Добавление кнопки для нового поиска
        buttons.append([InlineKeyboardButton("🔄 Новый поиск", callback_data="new_search")])
        
        await query.message.edit_text(
            car_info + "\n<b>Выберите тип:</b>",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode='HTML'
        )
    
    async def _handle_back_to_types(self, query: Update.callback_query, context: ContextTypes.DEFAULT_TYPE) -> None:
        """
        Обрабатывает возврат к выбору вида щетки.
        
        Args:
            query: Объект callback-запроса
            context: Контекст обработчика
        """
        back_id = query.data.replace("back_to_types_", "")
        store = self.user_manager.get_callback_data(back_id)
        
        if not store:
            await query.message.edit_text(
                text="⚠️ Не удалось вернуться к выбору вида щетки. Пожалуйста, начните поиск заново. /start"
            )
            return
        
        frame = store['gy_frame']
        mount = store['mount']
        driver_size = store['driver_size']
        pass_size = store['pass_size']
        
        # Получение доступных видов щеток
        available_types = self.db.get_available_types(frame, mount, [driver_size, pass_size])
        
        if available_types.empty:
            await query.message.edit_text(
                text="⚠️ Не удалось найти подходящие виды щеток для выбранного корпуса. Пожалуйста, выберите другой корпус."
            )
            return
        
        # Создание кнопок для выбора вида щетки
        buttons = []
        for _, rowt in available_types.iterrows():
            gy_type = rowt['gy_type']
            type_id = self.user_manager.store_callback_data({
                **store, "gy_type": gy_type
            })
            buttons.append([InlineKeyboardButton(str(gy_type), callback_data=f"type_{type_id}")])
        
        # Добавление кнопки "Назад"
        back_to_frames_id = self.user_manager.store_callback_data({**store})
        buttons.append([InlineKeyboardButton("🔙 Назад", callback_data=f"back_to_frames_{back_to_frames_id}")])
        buttons.append([InlineKeyboardButton("🔄 Новый поиск", callback_data="new_search")])

        # Получение информации об автомобиле
        car_rows = self.db.cars_df[
            (self.db.cars_df['brand'] == store.get('brand', '')) &
            (self.db.cars_df['model'] == store.get('model', '')) &
            (self.db.cars_df['years'] == store.get('years', ''))
        ]
        
        if car_rows.empty:
            await query.message.edit_text(
                text="⚠️ Не удалось найти информацию о выбранной модели. Пожалуйста, начните поиск заново. /start"
            )
            return
        
        car_info = self.db.get_car_info(car_rows.iloc[0])
        
        await query.message.edit_text(
            car_info + f"\n<b>Выберите вид щётки:</b>",
            reply_markup=InlineKeyboardMarkup(buttons),
            parse_mode='HTML'
        )
    
