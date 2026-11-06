import math
from datetime import datetime

from valutatrade_hub.core import utils
from valutatrade_hub.core.models import EXCHANGE_RATES, Portfolio, User


def register_user(username: str, password: str) -> User:
    """Регистрирует нового пользователя и создаёт пустой портфель"""
    users = utils.load_json("users.json", [])
    portfolios = utils.load_json("portfolios.json", [])

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

    utils.save_json("users.json", users)
    utils.save_json("portfolios.json", portfolios)

    return user


def login_user(username: str, password: str) -> User:
    """Проверяет учётные данные и возвращает пользователя"""
    users = utils.load_json("users.json", [])

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
    portfolios = utils.load_json("portfolios.json", [])

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
    portfolios = utils.load_json("portfolios.json", [])

    for item in portfolios:
        if item["user_id"] == portfolio.user.user_id:
            item["wallets"] = {
                code: {"balance": wallet.balance}
                for code, wallet in portfolio.wallets.items()
            }

            utils.save_json("portfolios.json", portfolios)
            return

    raise ValueError("Портфель пользователя не найден")


def buy_currency(user: User, currency_code: str, amount: float) -> dict:
    """Покупает валюту за USD и сохраняет изменения"""
    if not isinstance(currency_code, str) or not currency_code.strip():
        raise ValueError("Укажите код валюты")

    code = currency_code.strip().upper()

    if code not in EXCHANGE_RATES:
        raise ValueError(f"Неизвестная валюта '{code}'")

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
        raise ValueError("Для покупки необходим USD-кошелёк")

    if usd_wallet.balance < cost_usd:
        raise ValueError("Недостаточно средств в USD-кошельке")

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


def sell_currency(user: User, currency_code: str, amount: float) -> dict:
    """Продаёт валюту за USD и сохраняет изменения"""
    if not isinstance(currency_code, str) or not currency_code.strip():
        raise ValueError("Укажите код валюты")

    code = currency_code.strip().upper()

    if code not in EXCHANGE_RATES:
        raise ValueError(f"Неизвестная валюта '{code}'")

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
        raise ValueError(f"Кошелёк '{code}' не найден")

    if target_wallet.balance < amount:
        raise ValueError(f"Недостаточно {code} для продажи")

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
