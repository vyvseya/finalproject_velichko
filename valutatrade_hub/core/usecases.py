from datetime import datetime

from valutatrade_hub.core import utils
from valutatrade_hub.core.models import User


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
