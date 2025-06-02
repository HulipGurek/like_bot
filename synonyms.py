"""
Модуль для управления синонимами.
"""
import os
import threading
import time
import logging
import pandas as pd
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class SynonymManager:
    """Класс для управления синонимами."""
    
    def __init__(self, filepath: str = "synonyms.csv", reload_interval: int = 10):
        """
        Инициализация менеджера синонимов.
        
        Args:
            filepath: Путь к файлу с синонимами
            reload_interval: Интервал перезагрузки синонимов в секундах
        """
        self.filepath = filepath
        self.reload_interval = reload_interval
        self._synonyms: Dict[str, str] = {}
        self._last_mtime: Optional[float] = None
        self._lock = threading.Lock()
        self._stop = False
        self.reload_synonyms()
        threading.Thread(target=self._watch, daemon=True).start()

    def reload_synonyms(self) -> None:
        """Перезагружает синонимы из файла."""
        try:
            if os.path.exists(self.filepath):
                mtime = os.path.getmtime(self.filepath)
                if self._last_mtime == mtime:
                    return
                df = pd.read_csv(self.filepath)
                synonyms = {}
                for _, row in df.iterrows():
                    base = str(row['base']).strip().lower()
                    syns = [s.strip() for s in str(row['synonyms']).strip().lower().split(',') if s.strip()]
                    for syn in syns:
                        synonyms[syn] = base
                    synonyms[base] = base
                with self._lock:
                    self._synonyms = synonyms
                    self._last_mtime = mtime
                logger.info(f"[SynonymManager] Синонимы перезагружены, {len(synonyms)} записей")
        except Exception as e:
            logger.error(f"[SynonymManager] Ошибка при перезагрузке синонимов: {e}")

    def get_synonyms(self) -> Dict[str, str]:
        """
        Получает словарь синонимов.
        
        Returns:
            Dict[str, str]: Словарь синонимов
        """
        with self._lock:
            return dict(self._synonyms)

    def _watch(self) -> None:
        """Фоновый поток для отслеживания изменений в файле синонимов."""
        while not self._stop:
            self.reload_synonyms()
            time.sleep(self.reload_interval)

    def stop(self) -> None:
        """Останавливает фоновый поток."""
        self._stop = True

def apply_synonyms(parts: list, synonyms: Dict[str, str]) -> list:
    # Сначала ищем по всей строке (соединённые слова)
    joined = " ".join(parts).lower()
    if joined in synonyms:
        return [synonyms[joined]]
    # Потом — по каждому слову отдельно
    return [synonyms.get(word, word) for word in parts]
