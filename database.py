"""
Модуль для работы с базой данных автомобилей и щеток.
"""
import os
import logging
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any, Set, Union
from config import Config

logger = logging.getLogger(__name__)

class Database:
    """Класс для работы с базами данных автомобилей и щеток."""
    
    def __init__(self):
        """Инициализация баз данных."""
        self.cars_df = None
        self.wipers_df = None
        self.types_desc_df = None
        self.load_all()
    
    def load_all(self) -> bool:
        """
        Загружает все базы данных.
        
        Returns:
            bool: True, если все базы данных загружены успешно
        """
        try:
            self.load_cars_database()
            self.load_wipers_catalog()
            self.load_types_desc()
            return True
        except Exception as e:
            logger.error(f"Ошибка при загрузке баз данных: {str(e)}")
            return False
    
    def load_cars_database(self) -> None:
        """Загружает базу данных автомобилей."""
        try:
            df = pd.read_excel(Config.DATABASE_PATH, sheet_name=0, engine='openpyxl').fillna('нет')
            if not self.validate_database(df):
                raise ValueError("Ошибка валидации базы данных автомобилей")
            
            # Нормализация данных
            df['brand_lower'] = df['brand'].apply(self.normalize_text)
            df['model_lower'] = df['model'].apply(self.normalize_text)
            df['full_name'] = df['brand_lower'] + ' ' + df['model_lower']
            
            self.cars_df = df
            logger.info(f"База данных автомобилей загружена успешно: {len(df)} записей")
        except Exception as e:
            logger.error(f"Ошибка при загрузке базы данных автомобилей: {str(e)}")
            raise
    
    def load_wipers_catalog(self) -> None:
        """Загружает каталог щеток."""
        try:
            wipers = pd.read_excel(Config.WIPERS_PATH, sheet_name=0, engine='openpyxl').fillna('нет')
            wipers.columns = [col.strip() for col in wipers.columns]
            self.wipers_df = wipers
            logger.info(f"Каталог щеток загружен успешно: {len(wipers)} записей")
        except Exception as e:
            logger.error(f"Ошибка при загрузке каталога щеток: {str(e)}")
            raise
    
    def load_types_desc(self) -> None:
        """Загружает описания типов щеток."""
        try:
            df = pd.read_excel(Config.TYPES_DESC_PATH, sheet_name=0, engine='openpyxl').fillna('')
            df.columns = [col.strip() for col in df.columns]
            self.types_desc_df = df
            logger.info(f"Описания типов щеток загружены успешно: {len(df)} записей")
        except Exception as e:
            logger.error(f"Ошибка при загрузке описаний типов щеток: {str(e)}")
            raise
    
    @staticmethod
    def validate_database(df: pd.DataFrame) -> bool:
        """
        Проверяет наличие необходимых колонок в базе данных автомобилей.
        
        Args:
            df: DataFrame с данными автомобилей
            
        Returns:
            bool: True, если все необходимые колонки присутствуют
        """
        required_columns = ['brand', 'model', 'years', 'mount', 'driver', 'passanger']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            logger.error(f"В базе данных отсутствуют колонки: {missing_columns}")
            return False
        return True
    
    @staticmethod
    def normalize_text(s: Any) -> str:
        """
        Нормализует текст для поиска.
        
        Args:
            s: Текст для нормализации
            
        Returns:
            str: Нормализованный текст
        """
        import re
        from utils.text_utils import translit_ru_to_en
        
        s = str(s).strip().lower().replace('ё', 'е')
        if re.search(r'[а-я]', s):
            s = translit_ru_to_en(s)
        return s
    
    def get_car_info(self, row: pd.Series) -> str:
        """
        Форматирует информацию об автомобиле для отображения.
        
        Args:
            row: Строка DataFrame с данными автомобиля
            
        Returns:
            str: Отформатированная информация об автомобиле
        """
        from utils.formatting import format_wiper_info
        
        return (
            f"🚗 <b>{str(row.get('brand', '')).title()} {str(row.get('model', '')).upper()}</b> <i>({row.get('years', '')})</i>\n"
            f"🔗 <b>Крепление:</b> <i>{row.get('mount', '')}</i>\n"
            f"➡️ <b>Правая щётка:</b> <code>{format_wiper_info(row.get('driver', ''))}</code>\n"
            f"⬅️ <b>Левая щётка:</b> <code>{format_wiper_info(row.get('passanger', ''))}</code>\n"
            "——————\n"
        )
    
    def get_available_frames(self, mount: str, sizes: List[int]) -> pd.DataFrame:
        """
        Получает доступные типы корпусов щеток для заданного крепления и размеров.
        
        Args:
            mount: Тип крепления
            sizes: Список размеров щеток
            
        Returns:
            pd.DataFrame: DataFrame с доступными типами корпусов
        """
        if self.wipers_df is None:
            logger.error("База данных щеток не загружена")
            return pd.DataFrame()
        
        return self.wipers_df[
            (self.wipers_df[mount].str.lower() == "да") &
            (self.wipers_df['size'].isin(sizes))
        ][['gy_frame', 'gy_frame_pic']].drop_duplicates()
    
    def get_available_types(self, frame: str, mount: str, sizes: List[int]) -> pd.DataFrame:
        """
        Получает доступные виды щеток для заданного корпуса, крепления и размеров.
        
        Args:
            frame: Тип корпуса
            mount: Тип крепления
            sizes: Список размеров щеток
            
        Returns:
            pd.DataFrame: DataFrame с доступными видами щеток
        """
        if self.wipers_df is None:
            logger.error("База данных щеток не загружена")
            return pd.DataFrame()
        
        available_types = self.wipers_df[
            (self.wipers_df['gy_frame'] == frame) &
            (self.wipers_df[mount].str.lower() == "да") &
            (self.wipers_df['size'].isin(sizes))
        ][['gy_type', 'gy_type_pic']].drop_duplicates()
        
        # Сортировка: Premium-щетки в начале списка
        return available_types.sort_values(
            by="gy_type",
            key=lambda col: col.str.lower().str.contains("premium").map(lambda x: 0 if x else 1)
        )
    
    def get_wiper_kit_links(self, frame: str, gy_type: str, mount: str, driver_size: int, pass_size: int) -> Tuple[Optional[str], Optional[str]]:
        """
        Получает ссылки на комплект щеток.
        
        Args:
            frame: Тип корпуса
            gy_type: Вид щетки
            mount: Тип крепления
            driver_size: Размер правой щетки
            pass_size: Размер левой щетки
            
        Returns:
            Tuple[Optional[str], Optional[str]]: Ссылки на Ozon и Wildberries
        """
        if self.wipers_df is None:
            logger.error("База данных щеток не загружена")
            return None, None
        
        kits = self.wipers_df[
            (self.wipers_df['gy_type'].astype(str).str.strip() == str(gy_type).strip()) &
            (self.wipers_df['gy_frame'].astype(str).str.strip() == str(frame).strip())
        ].copy()
        kits = kits[kits[mount].astype(str).str.strip().str.lower() == "да"]
        kits = kits[kits['Комплект'].notnull() & (kits['Комплект'].astype(str).str.lower() != "нет")]
        
        sizes = set()
        if driver_size and pass_size:
            sizes.add(f"{driver_size}/{pass_size}")
            sizes.add(f"{pass_size}/{driver_size}")
        
        kits['Комплект_norm'] = kits['Комплект'].apply(lambda s: str(s).replace(" ", "").replace("мм", "").strip())
        kits = kits[kits['Комплект_norm'].isin(sizes)]
        
        ozon_kit_url, wb_kit_url = None, None
        if not kits.empty:
            k_row = kits.iloc[0]
            ozon_kit_url = k_row.get('Ozon', '')
            wb_kit_url = k_row.get('Wildberries', '')
        
        return ozon_kit_url, wb_kit_url
    
    def get_single_wiper_links(self, frame: str, gy_type: str, mount: str, size: int) -> Tuple[Optional[str], Optional[str]]:
        '''
        Получает ссылки на одну щетку определенного размера.
        '''
        if self.wipers_df is None:
            logger.error("База данных щеток не загружена")
            return None, None
        wipers = self.wipers_df[
            (self.wipers_df['gy_frame'] == frame) &
            (self.wipers_df['gy_type'] == gy_type) &
            (self.wipers_df['size'] == size)
        ]
        # Если нет точного совпадения по размеру, ищем ближайший размер (в пределах ±10 мм)
        if wipers.empty and isinstance(size, (int, float)):
            size_int = int(size)
            for delta in range(1, 11):
                wipers_plus = self.wipers_df[
                    (self.wipers_df['gy_frame'] == frame) &
                    (self.wipers_df['gy_type'] == gy_type) &
                    (self.wipers_df['size'] == size_int + delta)
                ]
                wipers_minus = self.wipers_df[
                    (self.wipers_df['gy_frame'] == frame) &
                    (self.wipers_df['gy_type'] == gy_type) &
                    (self.wipers_df['size'] == size_int - delta)
                ]
                if not wipers_plus.empty:
                    wipers = wipers_plus
                    break
                elif not wipers_minus.empty:
                    wipers = wipers_minus
                    break
        if wipers.empty:
            return None, None
        ozon_url = None
        wb_url = None
        # Приведение к любому варианту (ozon_url/Оzon) зависит от того, как называются столбцы!
        for _, wiper in wipers.iterrows():
            if pd.notna(wiper.get('ozon_url')) and not ozon_url:
                ozon_url = wiper['ozon_url']
            if pd.notna(wiper.get('Ozon')) and not ozon_url:
                ozon_url = wiper['Ozon']
            if pd.notna(wiper.get('wb_url')) and not wb_url:
                wb_url = wiper['wb_url']
            if pd.notna(wiper.get('Wildberries')) and not wb_url:
                wb_url = wiper['Wildberries']
            if ozon_url and wb_url:
                break
        return ozon_url, wb_url