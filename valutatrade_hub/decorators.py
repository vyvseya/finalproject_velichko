from collections.abc import Callable
from functools import wraps
from typing import Any

from valutatrade_hub.logging_config import configure_logging


def log_action(
    action: str, *, verbose: bool = False
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Создаёт декоратор для логирования операций"""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        """Оборачивает функцию логированием"""

        @wraps(func)
        def wrapper(user: Any, currency_code: str, amount: float) -> Any:
            """Записывает результат выполнения операции"""
            logger = configure_logging()

            username = getattr(user, "username", str(user))
            code = (
                currency_code.upper()
                if isinstance(currency_code, str)
                else currency_code
            )

            context = (
                f"action={action.upper()} "
                f"user={username!r} "
                f"currency={code!r} "
                f"amount={amount!r}"
            )

            try:
                result = func(user, currency_code, amount)
            except Exception as error:
                logger.info(
                    "%s result=ERROR error_type=%s error_message=%r",
                    context,
                    type(error).__name__,
                    str(error),
                )
                raise

            rate_info = ""

            if isinstance(result, dict):
                value_usd = result.get("spent_usd", result.get("received_usd"))

                if value_usd is not None and result.get("amount"):
                    rate = value_usd / result["amount"]
                    rate_info = f" rate={rate:.8f} base='USD'"

            details = f" details={result!r}" if verbose else ""

            logger.info(
                "%s%s result=OK%s",
                context,
                rate_info,
                details,
            )

            return result

        return wrapper

    return decorator
