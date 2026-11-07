from threading import Event
from time import monotonic, sleep

from valutatrade_hub.core.exceptions import ApiRequestError
from valutatrade_hub.logging_config import configure_logging
from valutatrade_hub.parser_service.api_clients import (
    CoinGeckoClient,
    ExchangeRateApiClient,
)
from valutatrade_hub.parser_service.config import ParserConfig
from valutatrade_hub.parser_service.storage import RatesStorage
from valutatrade_hub.parser_service.updater import RatesUpdater


class RatesScheduler:
    """Запускает обновление курсов по расписанию"""

    def __init__(
        self,
        updater: RatesUpdater,
        interval_seconds: int = 3600,
    ) -> None:
        """Сохраняет модуль обновления и интервал"""

        if type(interval_seconds) is not int:
            raise TypeError("Интервал должен быть целым числом")

        if interval_seconds <= 0:
            raise ValueError("Интервал должен быть больше нуля")

        self.updater = updater
        self.interval_seconds = interval_seconds
        self._stop_event = Event()

    def run(self) -> None:
        """Периодически обновляет курсы до остановки"""

        logger = configure_logging()

        print("Планировщик валютных курсов запущен")
        print(f"Интервал обновления: {self.interval_seconds} секунд")

        while not self._stop_event.is_set():
            try:
                result = self.updater.run_update()

            except ApiRequestError as error:
                logger.error("SCHEDULER update_failed error=%s", error)
                print(f"Ошибка обновления: {error}")

            else:
                print(f"Обновлено курсов: {result['updated']}")
                print(f"Время обновления (UTC): {result['last_refresh']}")

                for error in result["errors"]:
                    print(f"Ошибка источника: {error}")

            deadline = monotonic() + self.interval_seconds

            while not self._stop_event.is_set():
                remaining = deadline - monotonic()

                if remaining <= 0:
                    break

                sleep(min(remaining, 1.0))

        print("Планировщик остановлен")

    def stop(self) -> None:
        """Останавливает планировщик"""

        self._stop_event.set()


def main() -> None:
    """Создаёт компоненты и запускает планировщик"""

    config = ParserConfig()

    updater = RatesUpdater(
        CoinGeckoClient(config),
        ExchangeRateApiClient(config),
        RatesStorage(config),
    )

    scheduler = RatesScheduler(updater)

    try:
        scheduler.run()
    except KeyboardInterrupt:
        scheduler.stop()
        print("\nПланировщик остановлен пользователем")


if __name__ == "__main__":
    main()
