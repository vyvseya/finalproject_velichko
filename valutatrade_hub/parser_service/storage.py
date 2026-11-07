import math
import re
from datetime import UTC, datetime, timedelta

from valutatrade_hub.core import utils
from valutatrade_hub.parser_service.config import ParserConfig


class RatesStorage:
    """Управляет текущими курсами и историей измерений"""

    def __init__(self, config: ParserConfig | None = None) -> None:
        """Сохраняет настройки файлового хранилища"""
        self.config = config if config is not None else ParserConfig()

    def load_current(self) -> dict:
        """Загружает последние курсы валют"""
        return utils.load_json(
            self.config.RATES_FILE_PATH,
            {"pairs": {}, "last_refresh": None},
        )

    def load_history(self) -> list:
        """Загружает историю измерений курсов"""
        return utils.load_json(self.config.HISTORY_FILE_PATH, [])

    def save_rates(
        self,
        rates: dict[str, float],
        source: str,
        timestamp: str | None = None,
    ) -> int:
        """Сохраняет измерения и обновляет последние курсы"""
        if not isinstance(rates, dict):
            raise TypeError("Курсы должны быть словарём")

        if not isinstance(source, str) or not source.strip():
            raise ValueError("Укажите источник курсов")

        if timestamp is None:
            timestamp = (
                datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")
            )

        try:
            measured_at = datetime.fromisoformat(timestamp)
        except (AttributeError, ValueError) as error:
            raise ValueError("Некорректная дата измерения") from error

        if not timestamp.endswith("Z") or measured_at.utcoffset() != timedelta(0):
            raise ValueError("Дата должна быть в формате ISO UTC")

        for pair, rate in rates.items():
            if not isinstance(pair, str) or not re.fullmatch(
                r"[A-Z]{2,5}_[A-Z]{2,5}", pair
            ):
                raise ValueError(f"Некорректная валютная пара: {pair}")

            if type(rate) not in (int, float) or not math.isfinite(rate) or rate <= 0:
                raise ValueError(f"Некорректный курс для {pair}")

        current = self.load_current()
        history = self.load_history()

        if not isinstance(current, dict) or not isinstance(current.get("pairs"), dict):
            raise TypeError("Несовместимый формат rates.json")

        if not isinstance(history, list):
            raise TypeError("Некорректный формат exchange_rates.json")

        known_ids = {record["id"] for record in history}
        initial_history_size = len(history)
        updated_count = 0

        for pair, rate in rates.items():
            from_code, to_code = pair.split("_")
            record_id = f"{pair}_{timestamp}"

            if record_id not in known_ids:
                history.append(
                    {
                        "id": record_id,
                        "from_currency": from_code,
                        "to_currency": to_code,
                        "rate": float(rate),
                        "timestamp": timestamp,
                        "source": source,
                        "meta": {},
                    }
                )
                known_ids.add(record_id)

            previous = current["pairs"].get(pair)

            if previous is not None:
                previous_time = datetime.fromisoformat(previous["updated_at"])

                if measured_at <= previous_time:
                    continue

            current["pairs"][pair] = {
                "rate": float(rate),
                "updated_at": timestamp,
                "source": source,
            }
            updated_count += 1

        if len(history) > initial_history_size:
            utils.save_json(self.config.HISTORY_FILE_PATH, history)

        if updated_count:
            last_refresh = current.get("last_refresh")

            if last_refresh is None or measured_at > datetime.fromisoformat(
                last_refresh
            ):
                current["last_refresh"] = timestamp

            utils.save_json(self.config.RATES_FILE_PATH, current)

        return updated_count
