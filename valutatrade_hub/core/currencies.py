import math
from abc import ABC, abstractmethod

from valutatrade_hub.core.exceptions import CurrencyNotFoundError


class Currency(ABC):
    """Абстрактный базовый класс валюты"""

    def __init__(self, name: str, code: str):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("Название валюты не может быть пустым")

        if (
            not isinstance(code, str)
            or not 2 <= len(code) <= 5
            or not code.isalpha()
            or not code.isupper()
        ):
            raise ValueError("Код валюты должен содержать 2–5 заглавных букв")

        self.name = name.strip()
        self.code = code

    @abstractmethod
    def get_display_info(self) -> str:
        """Возвращает информацию о валюте"""
        raise NotImplementedError


class FiatCurrency(Currency):
    """Представляет обычную государственную валюту"""

    def __init__(self, name: str, code: str, issuing_country: str):
        super().__init__(name, code)

        if not isinstance(issuing_country, str) or not issuing_country.strip():
            raise ValueError("Страна эмиссии не может быть пустой")

        self.issuing_country = issuing_country.strip()

    def get_display_info(self) -> str:
        """Возвращает информацию о фиатной валюте"""
        return f"[FIAT] {self.code} — {self.name} (Issuing: {self.issuing_country})"


class CryptoCurrency(Currency):
    """Представляет криптовалюту"""

    def __init__(
        self,
        name: str,
        code: str,
        algorithm: str,
        market_cap: float,
    ):
        super().__init__(name, code)

        if not isinstance(algorithm, str) or not algorithm.strip():
            raise ValueError("Алгоритм не может быть пустым")

        if (
            type(market_cap) not in (int, float)
            or not math.isfinite(market_cap)
            or market_cap < 0
        ):
            raise ValueError("Капитализация должна быть неотрицательным числом")

        self.algorithm = algorithm.strip()
        self.market_cap = float(market_cap)

    def get_display_info(self) -> str:
        """Возвращает информацию о криптовалюте"""
        market_cap_text = f"{self.market_cap:.2e}".replace("e+", "e")

        return (
            f"[CRYPTO] {self.code} — {self.name} "
            f"(Algo: {self.algorithm}, MCAP: {market_cap_text})"
        )


CURRENCY_REGISTRY: dict[str, Currency] = {
    "USD": FiatCurrency("US Dollar", "USD", "United States"),
    "EUR": FiatCurrency("Euro", "EUR", "Eurozone"),
    "GBP": FiatCurrency("British Pound", "GBP", "United Kingdom"),
    "RUB": FiatCurrency("Russian Ruble", "RUB", "Russia"),
    "BTC": CryptoCurrency("Bitcoin", "BTC", "SHA-256", 1.12e12),
    "ETH": CryptoCurrency("Ethereum", "ETH", "Proof of Stake", 4.0e11),
    "SOL": CryptoCurrency(
        "Solana",
        "SOL",
        "Proof of History + Proof of Stake",
        0.0,
    ),
}


def get_currency(code: str) -> Currency:
    """Возвращает валюту из реестра по её коду"""
    if not isinstance(code, str):
        raise TypeError("Код валюты должен быть строкой")

    normalized_code = code.strip().upper()

    currency = CURRENCY_REGISTRY.get(normalized_code)

    if currency is None:
        raise CurrencyNotFoundError(normalized_code)

    return currency
