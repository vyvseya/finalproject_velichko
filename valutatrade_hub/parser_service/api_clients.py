import math
from abc import ABC, abstractmethod

import requests

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.parser_service.config import ParserConfig


class BaseApiClient(ABC):
    """Абстрактный клиент внешнего API"""

    @abstractmethod
    def fetch_rates(self) -> dict[str, float]:
        """Получает курсы валют из внешнего источника"""
        raise NotImplementedError


class CoinGeckoClient(BaseApiClient):
    """Получает курсы криптовалют через CoinGecko"""

    def __init__(self, config: ParserConfig | None = None) -> None:
        """Сохраняет настройки API-клиента"""
        self.config = config if config is not None else ParserConfig()

    def fetch_rates(self) -> dict[str, float]:
        """Запрашивает и проверяет курсы криптовалют"""
        base = self.config.BASE_CURRENCY.upper()

        try:
            coin_ids = [
                self.config.CRYPTO_ID_MAP[code]
                for code in self.config.CRYPTO_CURRENCIES
            ]
        except KeyError as error:
            raise ApiRequestError(f"CoinGecko: не найден ID валюты {error}") from error

        params = {
            "ids": ",".join(coin_ids),
            "vs_currencies": base.lower(),
        }

        headers = {}

        if self.config.COINGECKO_API_KEY:
            headers["x-cg-demo-api-key"] = self.config.COINGECKO_API_KEY

        try:
            response = requests.get(
                self.config.COINGECKO_URL,
                params=params,
                headers=headers,
                timeout=self.config.REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()

        except (requests.exceptions.RequestException, ValueError) as error:
            raise ApiRequestError(f"CoinGecko: {error}") from error

        if not isinstance(data, dict):
            raise ApiRequestError("CoinGecko: некорректный формат ответа")

        rates = {}

        for code in self.config.CRYPTO_CURRENCIES:
            coin_id = self.config.CRYPTO_ID_MAP[code]
            coin_data = data.get(coin_id)

            if not isinstance(coin_data, dict):
                raise ApiRequestError(f"CoinGecko: отсутствуют данные для {code}")

            price = coin_data.get(base.lower())

            if (
                type(price) not in (int, float)
                or not math.isfinite(price)
                or price <= 0
            ):
                raise ApiRequestError(f"CoinGecko: некорректный курс {code}/{base}")

            rates[f"{code}_{base}"] = float(price)

        return rates


class ExchangeRateApiClient(BaseApiClient):
    """Получает курсы фиатных валют через ExchangeRate-API"""

    def __init__(self, config: ParserConfig | None = None) -> None:
        """Сохраняет настройки API-клиента"""
        self.config = config if config is not None else ParserConfig()

    def fetch_rates(self) -> dict[str, float]:
        """Запрашивает и проверяет курсы фиатных валют"""
        api_key = self.config.EXCHANGERATE_API_KEY

        if not api_key:
            raise ApiRequestError("ExchangeRate-API: не задан EXCHANGERATE_API_KEY")

        base = self.config.BASE_CURRENCY.upper()
        url = f"{self.config.EXCHANGERATE_API_URL.rstrip('/')}/{api_key}/latest/{base}"

        try:
            response = requests.get(
                url,
                timeout=self.config.REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()

        except (requests.exceptions.RequestException, ValueError) as error:
            raise ApiRequestError(
                f"ExchangeRate-API: ошибка запроса ({type(error).__name__})"
            ) from error

        if not isinstance(data, dict):
            raise ApiRequestError("ExchangeRate-API: некорректный формат ответа")

        if data.get("result") != "success":
            reason = data.get("error-type", "неизвестная ошибка")
            raise ApiRequestError(f"ExchangeRate-API: {reason}")

        if data.get("base_code") != base:
            raise ApiRequestError("ExchangeRate-API: неверная базовая валюта")

        conversion_rates = data.get("conversion_rates")

        if not isinstance(conversion_rates, dict):
            raise ApiRequestError("ExchangeRate-API: отсутствует список курсов")

        rates = {}

        for code in self.config.FIAT_CURRENCIES:
            value = conversion_rates.get(code)

            if (
                type(value) not in (int, float)
                or not math.isfinite(value)
                or value <= 0
            ):
                raise ApiRequestError(
                    f"ExchangeRate-API: некорректный курс {base}/{code}"
                )

            rates[f"{code}_{base}"] = 1 / value

        return rates
