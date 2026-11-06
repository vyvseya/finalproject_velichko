import hashlib
import math
import secrets
from datetime import datetime

EXCHANGE_RATES = {
    "USD": 1.0,
    "EUR": 1.0786,
    "BTC": 59337.21,
    "RUB": 0.01016,
    "ETH": 3720.0,
}


class User:
    """Представляет пользователя валютной платформы"""

    def __init__(
        self,
        user_id: int,
        username: str,
        hashed_password: str,
        salt: str,
        registration_date: datetime,
    ):
        """Создает пользователя и сохраняет его данные"""
        if type(user_id) is not int or user_id <= 0:
            raise ValueError("ID пользователя должен быть положительным числом")

        if not isinstance(registration_date, datetime):
            raise TypeError("Дата регистрации должна быть datetime")

        if not isinstance(hashed_password, str) or not isinstance(salt, str):
            raise TypeError("Хеш пароля и соль должны быть строками")

        self._user_id = user_id
        self._username = ""
        self.username = username
        self._hashed_password = hashed_password
        self._salt = salt
        self._registration_date = registration_date

    @property
    def user_id(self) -> int:
        """Возвращает идентификатор пользователя"""
        return self._user_id

    @property
    def username(self) -> str:
        """Возвращает имя пользователя"""
        return self._username

    @username.setter
    def username(self, value: str):
        """Изменяет имя пользователя после проверкиу"""
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Имя пользователя не может быть пустым")

        self._username = value.strip()

    @property
    def hashed_password(self) -> str:
        """Возвращает хеш пароля."""
        return self._hashed_password

    @property
    def salt(self) -> str:
        """Возвращает соль пользователя."""
        return self._salt

    @property
    def registration_date(self) -> datetime:
        """Возвращает дату регистрации."""
        return self._registration_date

    def get_user_info(self) -> dict:
        """Возвращает информацию о пользователе без пароля."""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "registration_date": self.registration_date.isoformat(),
        }

    def change_password(self, new_password: str) -> None:
        """Изменяет пароль, создавая новую соль и хеш."""
        if not isinstance(new_password, str) or len(new_password) < 4:
            raise ValueError("Пароль должен быть не короче 4 символов")

        self._salt = secrets.token_hex(16)
        self._hashed_password = hashlib.sha256(
            (new_password + self._salt).encode("utf-8")
        ).hexdigest()

    def verify_password(self, password: str) -> bool:
        """Проверяет правильность введённого пароля."""
        if not isinstance(password, str):
            return False

        password_hash = hashlib.sha256(
            (password + self._salt).encode("utf-8")
        ).hexdigest()

        return secrets.compare_digest(password_hash, self._hashed_password)


class Wallet:
    """Представляет кошелёк для одной валюты"""

    def __init__(self, currency_code: str, balance: float = 0.0):
        """Создаёт кошелёк с указанной валютой и балансом"""
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым")

        self.currency_code = currency_code.strip().upper()
        self._balance = 0.0
        self.balance = balance

    @property
    def balance(self) -> float:
        """Возвращает текущий баланс кошелька"""
        return self._balance

    @balance.setter
    def balance(self, value: float) -> None:
        """Устанавливает баланс после проверки"""
        if type(value) not in (int, float) or not math.isfinite(value):
            raise TypeError("Баланс должен быть конечным числом")

        if value < 0:
            raise ValueError("Баланс не может быть отрицательным")

        self._balance = float(value)

    def deposit(self, amount: float) -> None:
        """Пополняет баланс кошелька"""
        if type(amount) not in (int, float) or not math.isfinite(amount):
            raise TypeError("Сумма должна быть конечным числом")

        if amount <= 0:
            raise ValueError("Сумма пополнения должна быть положительной")

        self.balance += amount

    def withdraw(self, amount: float) -> None:
        """Снимает средства с баланса кошелька"""
        if type(amount) not in (int, float) or not math.isfinite(amount):
            raise TypeError("Сумма должна быть конечным числом")

        if amount <= 0:
            raise ValueError("Сумма снятия должна быть положительной")

        if amount > self.balance:
            raise ValueError("Недостаточно средств на балансе")

        self.balance -= amount

    def get_balance_info(self) -> str:
        """Возвращает информацию о текущем балансе"""
        return f"Баланс: {self.balance} {self.currency_code}"


class Portfolio:
    """Управляет валютными кошельками пользователя"""

    def __init__(self, user: User):
        """Создаёт пустой портфель пользователя"""
        if not isinstance(user, User):
            raise TypeError("Пользователь должен быть объектом User")

        self._user = user
        self._user_id = user.user_id
        self._wallets: dict[str, Wallet] = {}

    @property
    def user(self) -> User:
        """Возвращает владельца портфеля"""
        return self._user

    @property
    def wallets(self) -> dict[str, Wallet]:
        """Возвращает копию словаря кошельков"""
        return self._wallets.copy()

    def add_currency(self, currency_code: str) -> Wallet:
        """Добавляет новый валютный кошелёк в портфель"""
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым")

        code = currency_code.strip().upper()

        if code in self._wallets:
            raise ValueError(f"Кошелёк {code} уже существует")

        wallet = Wallet(code)
        self._wallets[code] = wallet

        return wallet

    def get_wallet(self, currency_code: str) -> Wallet | None:
        """Возвращает кошелёк по коду валюты"""
        if not isinstance(currency_code, str) or not currency_code.strip():
            raise ValueError("Код валюты не может быть пустым")

        code = currency_code.strip().upper()
        return self._wallets.get(code)

    def get_total_value(self, base_currency: str = "USD") -> float:
        """Рассчитывает общую стоимость портфеля в выбранной валюте"""
        exchange_rates = EXCHANGE_RATES

        if not isinstance(base_currency, str) or not base_currency.strip():
            raise ValueError("Код базовой валюты не может быть пустым")

        base_code = base_currency.strip().upper()

        if base_code not in exchange_rates:
            raise ValueError(f"Неизвестная базовая валюта '{base_code}'")

        total_usd = 0.0

        for code, wallet in self._wallets.items():
            if code not in exchange_rates:
                raise ValueError(f"Курс валюты '{code}' неизвестен")

            total_usd += wallet.balance * exchange_rates[code]

        return total_usd / exchange_rates[base_code]
