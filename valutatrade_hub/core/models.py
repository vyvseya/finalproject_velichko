import hashlib
import secrets
from datetime import datetime


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
