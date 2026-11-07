import math
from datetime import UTC, datetime, timedelta

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import ApiRequestError, InsufficientFundsError
from valutatrade_hub.core.models import Portfolio, User
from valutatrade_hub.decorators import log_action
from valutatrade_hub.infra.database import DatabaseManager
from valutatrade_hub.infra.settings import SettingsLoader

db = DatabaseManager()


def register_user(username: str, password: str) -> User:
    """Регистрирует нового пользователя и создаёт пустой портфель"""
    users = db.load("users", [])
    portfolios = db.load("portfolios", [])

    user = User(
        user_id=max((item["user_id"] for item in users), default=0) + 1,
        username=username,
        hashed_password="",
        salt="",
        registration_date=datetime.now(),
    )

    if any(item["username"] == user.username for item in users):
        raise ValueError(f"Имя пользователя '{user.username}' уже занято")

    user.change_password(password)

    users.append(
        {
            "user_id": user.user_id,
            "username": user.username,
            "hashed_password": user.hashed_password,
            "salt": user.salt,
            "registration_date": user.registration_date.isoformat(),
        }
    )

    portfolios.append(
        {
            "user_id": user.user_id,
            "wallets": {},
        }
    )

    db.save("users", users)
    db.save("portfolios", portfolios)

    return user


def login_user(username: str, password: str) -> User:
    """Проверяет учётные данные и возвращает пользователя"""
    users = db.load("users", [])

    user_data = next(
        (item for item in users if item["username"] == username),
        None,
    )

    if user_data is None:
        raise ValueError(f"Пользователь '{username}' не найден")

    user = User(
        user_id=user_data["user_id"],
        username=user_data["username"],
        hashed_password=user_data["hashed_password"],
        salt=user_data["salt"],
        registration_date=datetime.fromisoformat(user_data["registration_date"]),
    )

    if not user.verify_password(password):
        raise ValueError("Неверный пароль")

    return user


def load_portfolio(user: User) -> Portfolio:
    """Загружает портфель пользователя из JSON"""
    portfolios = db.load("portfolios", [])

    portfolio_data = next(
        (item for item in portfolios if item["user_id"] == user.user_id),
        None,
    )

    if portfolio_data is None:
        raise ValueError("Портфель пользователя не найден")

    portfolio = Portfolio(user)

    for currency_code, wallet_data in portfolio_data["wallets"].items():
        wallet = portfolio.add_currency(currency_code)
        wallet.balance = wallet_data["balance"]

    return portfolio


def get_portfolio_summary(user: User, base_currency: str = "USD") -> dict:
    """Формирует информацию о стоимости портфеля по актуальным курсам"""
    base_code = get_currency(base_currency).code
    portfolio = load_portfolio(user)

    wallets_info = []
    total = 0.0

    for code, wallet in portfolio.wallets.items():
        rate = get_exchange_rate(code, base_code)["rate"]
        value = wallet.balance * rate

        if not math.isfinite(value) or not math.isfinite(total + value):
            raise ValueError("Стоимость портфеля слишком велика")

        wallets_info.append(
            {
                "currency_code": code,
                "balance": wallet.balance,
                "value": value,
            }
        )

        total += value

    return {
        "username": user.username,
        "base_currency": base_code,
        "wallets": wallets_info,
        "total": total,
    }


def save_portfolio(portfolio: Portfolio) -> None:
    """Сохраняет кошельки пользователя в JSON"""
    portfolios = db.load("portfolios", [])

    for item in portfolios:
        if item["user_id"] == portfolio.user.user_id:
            item["wallets"] = {
                code: {"balance": wallet.balance}
                for code, wallet in portfolio.wallets.items()
            }

            db.save("portfolios", portfolios)
            return

    raise ValueError("Портфель пользователя не найден")


@log_action("BUY", verbose=True)
def buy_currency(user: User, currency_code: str, amount: float) -> dict:
    """Покупает валюту за USD и сохраняет изменения"""
    code = get_currency(currency_code).code

    if code == "USD":
        raise ValueError("Нельзя купить USD за USD")

    if type(amount) not in (int, float) or not math.isfinite(amount) or amount <= 0:
        raise ValueError("Сумма покупки должна быть положительным числом")

    cost_usd = amount * get_exchange_rate(code, "USD")["rate"]

    if not math.isfinite(cost_usd):
        raise ValueError("Сумма покупки слишком велика")

    portfolio = load_portfolio(user)
    usd_wallet = portfolio.get_wallet("USD")

    if usd_wallet is None:
        raise InsufficientFundsError(0.0, cost_usd, "USD")

    if usd_wallet.balance < cost_usd:
        raise InsufficientFundsError(usd_wallet.balance, cost_usd, "USD")

    target_wallet = portfolio.get_wallet(code)

    if target_wallet is None:
        target_wallet = portfolio.add_currency(code)

    usd_wallet.withdraw(cost_usd)
    target_wallet.deposit(amount)

    save_portfolio(portfolio)

    return {
        "currency": code,
        "amount": amount,
        "spent_usd": cost_usd,
        "balance": target_wallet.balance,
        "usd_balance": usd_wallet.balance,
    }


@log_action("SELL")
def sell_currency(user: User, currency_code: str, amount: float) -> dict:
    """Продаёт валюту за USD и сохраняет изменения"""
    code = get_currency(currency_code).code

    if code == "USD":
        raise ValueError("Нельзя продать USD за USD")

    if type(amount) not in (int, float) or not math.isfinite(amount) or amount <= 0:
        raise ValueError("Сумма продажи должна быть положительным числом")

    received_usd = amount * get_exchange_rate(code, "USD")["rate"]

    if not math.isfinite(received_usd):
        raise ValueError("Сумма продажи слишком велика")

    portfolio = load_portfolio(user)
    target_wallet = portfolio.get_wallet(code)

    if target_wallet is None:
        raise InsufficientFundsError(0.0, amount, code)

    if target_wallet.balance < amount:
        raise InsufficientFundsError(target_wallet.balance, amount, code)

    usd_wallet = portfolio.get_wallet("USD")

    if usd_wallet is None:
        usd_wallet = portfolio.add_currency("USD")

    if not math.isfinite(usd_wallet.balance + received_usd):
        raise ValueError("Баланс USD превысит допустимое значение")

    target_wallet.withdraw(amount)
    usd_wallet.deposit(received_usd)

    save_portfolio(portfolio)

    return {
        "currency": code,
        "amount": amount,
        "received_usd": received_usd,
        "balance": target_wallet.balance,
        "usd_balance": usd_wallet.balance,
    }


def get_exchange_rate(from_currency: str, to_currency: str) -> dict:
    """Возвращает актуальный курс из локального кэша"""
    from_code = get_currency(from_currency).code
    to_code = get_currency(to_currency).code
    now = datetime.now(UTC)

    if from_code == to_code:
        return {
            "from_currency": from_code,
            "to_currency": to_code,
            "rate": 1.0,
            "inverse_rate": 1.0,
            "updated_at": now.isoformat(),
            "source": "identity",
            "cached": True,
        }

    cache = db.load("rates", {"pairs": {}, "last_refresh": None})

    if not isinstance(cache, dict) or not isinstance(cache.get("pairs"), dict):
        raise ApiRequestError("Несовместимый формат rates.json. Выполните update-rates")

    pairs = cache["pairs"]
    ttl_seconds = SettingsLoader().get("rates_ttl_seconds", 300)

    def usd_price(code: str) -> tuple[float, datetime, str]:
        """Возвращает стоимость валюты в USD из кэша"""
        if code == "USD":
            return 1.0, now, "USD"

        entry = pairs.get(f"{code}_USD")

        if not isinstance(entry, dict):
            raise ApiRequestError(f"Курс {code}/USD не найден. Выполните update-rates")

        try:
            price = entry["rate"]
            updated_at = datetime.fromisoformat(entry["updated_at"])
        except (KeyError, ValueError, TypeError) as error:
            raise ApiRequestError(f"Некорректная запись курса {code}/USD") from error

        if (
            type(price) not in (int, float)
            or not math.isfinite(price)
            or price <= 0
            or updated_at.tzinfo is None
        ):
            raise ApiRequestError(f"Некорректный курс {code}/USD")

        age = now - updated_at

        if not timedelta(0) <= age < timedelta(seconds=ttl_seconds):
            raise ApiRequestError(f"Курс {code}/USD устарел. Выполните update-rates")

        return float(price), updated_at, entry.get("source", "unknown")

    from_usd, from_time, from_source = usd_price(from_code)
    to_usd, to_time, to_source = usd_price(to_code)

    rate = from_usd / to_usd

    if rate <= 0 or not math.isfinite(rate) or not math.isfinite(1 / rate):
        raise ApiRequestError("Не удалось рассчитать корректный курс")

    sources = [source for source in (from_source, to_source) if source != "USD"]

    return {
        "from_currency": from_code,
        "to_currency": to_code,
        "rate": rate,
        "inverse_rate": 1 / rate,
        "updated_at": min(from_time, to_time).isoformat(),
        "source": ", ".join(dict.fromkeys(sources)),
        "cached": True,
    }
