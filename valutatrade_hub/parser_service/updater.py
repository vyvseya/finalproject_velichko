from datetime import UTC, datetime

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.logging_config import configure_logging
from valutatrade_hub.parser_service.api_clients import BaseApiClient
from valutatrade_hub.parser_service.storage import RatesStorage


class RatesUpdater:
    """Управляет обновлением валютных курсов"""

    def __init__(
        self,
        coingecko_client: BaseApiClient,
        exchangerate_client: BaseApiClient,
        storage: RatesStorage,
    ) -> None:
        """Сохраняет API-клиентов и хранилище"""
        self.clients = {
            "coingecko": (coingecko_client, "CoinGecko"),
            "exchangerate": (exchangerate_client, "ExchangeRate-API"),
        }
        self.storage = storage

    def run_update(self, source: str | None = None) -> dict:
        """Получает курсы и сохраняет успешные обновления"""
        if source is not None and source not in self.clients:
            raise ValueError(f"Неизвестный источник курсов '{source}'")

        logger = configure_logging()
        selected = [source] if source is not None else list(self.clients)

        logger.info("PARSER start sources=%s", ",".join(selected))

        fetched = []
        errors = []

        for name in selected:
            client, label = self.clients[name]

            try:
                rates = client.fetch_rates()
            except ApiRequestError as error:
                errors.append(str(error))
                logger.error(
                    "PARSER source=%s result=ERROR error=%s",
                    label,
                    error,
                )
                continue

            fetched.append((label, rates))

            logger.info(
                "PARSER source=%s result=OK rates=%d",
                label,
                len(rates),
            )

        if not fetched:
            raise ApiRequestError("Не удалось получить курсы ни из одного источника")

        timestamp = (
            datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
        )

        updated_count = 0

        for label, rates in fetched:
            count = self.storage.save_rates(
                rates,
                source=label,
                timestamp=timestamp,
            )
            updated_count += count

            logger.info(
                "PARSER saved source=%s updated=%d",
                label,
                count,
            )

        last_refresh = self.storage.load_current().get("last_refresh")

        logger.info(
            "PARSER finished updated=%d errors=%d",
            updated_count,
            len(errors),
        )

        return {
            "updated": updated_count,
            "last_refresh": last_refresh,
            "errors": errors,
        }
