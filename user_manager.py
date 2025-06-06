"""
Модуль для управления пользовательскими данными.
"""
import logging
import random
import string
from typing import Dict, List, Set, Any, Optional

logger = logging.getLogger(__name__)

def random_id(length: int = 6) -> str:
    """
    Генерирует случайный идентификатор.
    
    Args:
        length: Длина идентификатора
        
    Returns:
        str: Случайный идентификатор
    """
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))

class UserManager:
    """Класс для управления пользовательскими данными."""
    
    def __init__(self):
        """Инициализация менеджера пользователей."""
        self.unique_users: Set[int] = set()
        self.all_users_count: int = 0
        self.callback_storage: Dict[str, Dict[str, Any]] = {}
        self.favorites: Dict[int, List[Dict[str, Any]]] = {}
    
    def get_models_for_brand(self, brand: str) -> list:
        """
        Возвращает список моделей для указанной марки.
        """
        # Пример через pandas (или подстрой под свою базу)
        # self.cars_df — DataFrame с колонкой 'brand' и 'model'
        return sorted(self.cars_df[self.cars_df['brand'].str.lower() == brand.lower()]['model'].unique())
    
    def register_user(self, user_id: int) -> None:
        """
        Регистрирует пользователя.
        
        Args:
            user_id: ID пользователя
        """
        self.unique_users.add(user_id)
        self.all_users_count += 1
    
    def store_callback_data(self, data: Dict[str, Any]) -> str:
        """
        Сохраняет данные для callback и возвращает идентификатор.
        
        Args:
            data: Данные для сохранения
            
        Returns:
            str: Идентификатор сохраненных данных
        """
        callback_id = random_id()
        self.callback_storage[callback_id] = data
        return callback_id
    
    def get_callback_data(self, callback_id: str) -> Optional[Dict[str, Any]]:
        """
        Получает данные по идентификатору callback.
        
        Args:
            callback_id: Идентификатор callback
            
        Returns:
            Optional[Dict[str, Any]]: Данные callback или None, если не найдены
        """
        return self.callback_storage.get(callback_id)
    

    
    def get_stats(self) -> Dict[str, int]:
        """
        Получает статистику пользователей.
        
        Returns:
            Dict[str, int]: Статистика пользователей
        """
        return {
            'unique_users': len(self.unique_users),
            'all_users_count': self.all_users_count
        }
