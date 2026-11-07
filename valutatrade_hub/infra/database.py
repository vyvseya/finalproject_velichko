from __future__ import annotations

from typing import Self

from valutatrade_hub.core import utils
from valutatrade_hub.infra.settings import SettingsLoader


class DatabaseManager:
    """Управляет доступом к JSON-хранилищу"""

    _instance: DatabaseManager | None = None

    def __new__(cls) -> Self:
        """Возвращает единственный экземпляр класса"""
        # Используем __new__ для простой реализации Singleton
        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    def __init__(self) -> None:
        """Инициализирует менеджер только один раз"""
        if getattr(self, "_initialized", False):
            return

        self._settings = SettingsLoader()
        self._initialized = True

    def _get_filename(self, storage: str) -> str:
        """Находит имя JSON-файла в настройках"""
        filenames = {
            "users": "users_file",
            "portfolios": "portfolios_file",
            "rates": "rates_file",
        }

        if storage not in filenames:
            raise ValueError(f"Неизвестное хранилище '{storage}'")

        return self._settings.get(filenames[storage])

    def load(self, storage: str, default: list | dict) -> list | dict:
        """Загружает данные из JSON-хранилища"""
        filename = self._get_filename(storage)
        return utils.load_json(filename, default)

    def save(self, storage: str, data: list | dict) -> None:
        """Сохраняет данные в JSON-хранилище"""
        filename = self._get_filename(storage)
        utils.save_json(filename, data)
