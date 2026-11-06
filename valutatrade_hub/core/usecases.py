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
