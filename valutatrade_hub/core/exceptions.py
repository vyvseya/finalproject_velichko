class InsufficientFundsError(ValueError):
    """Ошибка при недостаточном балансе кошелька"""

    def __init__(self, available: float, required: float, code: str):
        self.available = available
        self.required = required
        self.code = code

        super().__init__(
            f"Недостаточно средств: доступно {available:g} {code}, "
            f"требуется {required:g} {code}"
        )


class CurrencyNotFoundError(ValueError):
    """Ошибка при обращении к неизвестной валюте"""

    def __init__(self, code: str):
        self.code = code
        super().__init__(f"Неизвестная валюта '{code}'")


class ApiRequestError(RuntimeError):
    """Ошибка при обращении к внешнему API"""

    def __init__(self, reason: str):
        self.reason = reason
        super().__init__(f"Ошибка при обращении к внешнему API: {reason}")
