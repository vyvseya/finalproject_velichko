from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any, Self


class SettingsLoader:
    """Загружает и хранит настройки приложения"""

    _instance: SettingsLoader | None = None

    def __new__(cls) -> Self:
        """Возвращает единственный экземпляр класса"""
        # __new__ проще метакласса для небольшого CLI-проекта
        if cls._instance is None:
            cls._instance = super().__new__(cls)

        return cls._instance

    def __init__(self) -> None:
        """Инициализирует настройки только один раз"""
        if getattr(self, "_initialized", False):
            return

        self._config_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
        self._settings: dict[str, Any] = {}

        self.reload()
        self._initialized = True

    def reload(self) -> None:
        """Перезагружает настройки из pyproject.toml"""
        defaults = {
            "data_dir": "data",
            "users_file": "users.json",
            "portfolios_file": "portfolios.json",
            "rates_file": "rates.json",
            "rates_ttl_seconds": 300,
            "default_base_currency": "USD",
            "log_file": "logs/actions.log",
            "log_format": "text",
            "log_level": "INFO",
        }

        if not self._config_path.exists():
            self._settings = defaults
            return

        with self._config_path.open("rb") as file:
            config = tomllib.load(file)

        custom_settings = config.get("tool", {}).get("valutatrade", {})
        self._settings = {**defaults, **custom_settings}

    def get(self, key: str, default: Any = None) -> Any:
        """Возвращает значение настройки по ключу"""
        return self._settings.get(key, default)
