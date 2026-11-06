import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def load_json(filename: str, default: list | dict) -> list | dict:
    """Загружает JSON-файл или возвращает значение по умолчанию"""
    filepath = DATA_DIR / filename

    if not filepath.exists():
        return default.copy()

    with filepath.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(filename: str, data: list | dict) -> None:
    """Сохраняет данные в JSON-файл"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    filepath = DATA_DIR / filename

    with filepath.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=4)
