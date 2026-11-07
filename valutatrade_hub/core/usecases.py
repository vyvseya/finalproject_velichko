import math
from datetime import UTC, datetime, timedelta

from valutatrade_hub.core.currencies import get_currency
from valutatrade_hub.core.exceptions import ApiRequestError, InsufficientFundsError
from valutatrade_hub.core.models import EXCHANGE_RATES, Portfolio, User
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
    """Формирует информацию о стоимости валютного портфеля"""
    portfolio = load_portfolio(user)

    total = portfolio.get_total_value(base_currency)
    base_code = base_currency.strip().upper()

    wallets_info = []

    for code, wallet in portfolio.wallets.items():
        value = wallet.balance * EXCHANGE_RATES[code] / EXCHANGE_RATES[base_code]

        wallets_info.append(
            {
                "currency_code": code,
                "balance": wallet.balance,
                "value": value,
            }
        )

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

    cost_usd = amount * EXCHANGE_RATES[code]

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

    received_usd = amount * EXCHANGE_RATES[code]

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
    """Возвращает валютный курс с кэшированием по настройке TTL"""
    from_code = get_currency(from_currency).code
    to_code = get_currency(to_currency).code
    ttl_seconds = SettingsLoader().get("rates_ttl_seconds", 300)

    pair = f"{from_code}_{to_code}"
    rates = db.load("rates", {})
    now = datetime.now(UTC)

    cached = rates.get(pair)

    if isinstance(cached, dict):
        try:
            updated_at = datetime.fromisoformat(cached["updated_at"])
            rate = float(cached["rate"])

            if updated_at.tzinfo is None:
                updated_at = updated_at.replace(tzinfo=UTC)

            age = now - updated_at

            if (
                timedelta(0) <= age < timedelta(seconds=ttl_seconds)
                and math.isfinite(rate)
                and rate > 0
            ):
                return {
                    "from_currency": from_code,
                    "to_currency": to_code,
                    "rate": rate,
                    "inverse_rate": 1 / rate,
                    "updated_at": cached["updated_at"],
                    "source": cached.get("source", "stub"),
                    "cached": True,
                }

        except (KeyError, ValueError, TypeError):
            pass

    try:
        rate = EXCHANGE_RATES[from_code] / EXCHANGE_RATES[to_code]
    except (KeyError, ZeroDivisionError) as error:
        raise ApiRequestError(
            f"Не удалось обновить курс {from_code}/{to_code}: "
            "нет корректных данных в источнике котировок"
        ) from error

    updated_at = now.isoformat()

    rates[pair] = {
        "rate": rate,
        "updated_at": updated_at,
        "source": "stub",
    }
    rates["source"] = "stub"
    rates["last_refresh"] = updated_at

    db.save("rates", rates)

    return {
        "from_currency": from_code,
        "to_currency": to_code,
        "rate": rate,
        "inverse_rate": 1 / rate,
        "updated_at": updated_at,
        "source": "stub",
        "cached": False,
    }
