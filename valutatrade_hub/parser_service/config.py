import os
from dataclasses import dataclass, field
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader


def _data_directory() -> Path:
    """Возвращает путь к папке данных из настроек"""
    data_dir = Path(SettingsLoader().get("data_dir", "data"))

    if not data_dir.is_absolute():
        data_dir = Path(__file__).resolve().parents[2] / data_dir

    return data_dir


@dataclass(frozen=True)
class ParserConfig:
    """Хранит настройки сервиса получения валютных курсов"""

    EXCHANGERATE_API_KEY: str | None = field(
        default_factory=lambda: os.getenv("EXCHANGERATE_API_KEY")
    )
    COINGECKO_API_KEY: str | None = field(
        default_factory=lambda: os.getenv("COINGECKO_API_KEY")
    )

    COINGECKO_URL: str = "https://api.coingecko.com/api/v3/simple/price"
    EXCHANGERATE_API_URL: str = "https://v6.exchangerate-api.com/v6"

    BASE_CURRENCY: str = field(
        default_factory=lambda: SettingsLoader().get("default_base_currency", "USD")
    )

    FIAT_CURRENCIES: tuple[str, ...] = ("EUR", "GBP", "RUB")
    CRYPTO_CURRENCIES: tuple[str, ...] = ("BTC", "ETH", "SOL")

    CRYPTO_ID_MAP: dict[str, str] = field(
        default_factory=lambda: {
            "BTC": "bitcoin",
            "ETH": "ethereum",
            "SOL": "solana",
        }
    )

    REQUEST_TIMEOUT: int = 10

    RATES_FILE_PATH: Path = field(
        default_factory=lambda: (
            _data_directory() / SettingsLoader().get("rates_file", "rates.json")
        )
    )
    HISTORY_FILE_PATH: Path = field(
        default_factory=lambda: _data_directory() / "exchange_rates.json"
    )
