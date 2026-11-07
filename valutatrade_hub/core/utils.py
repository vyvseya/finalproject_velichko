import json
import os
import tempfile
from pathlib import Path

from valutatrade_hub.infra.settings import SettingsLoader

DATA_DIR = Path(__file__).resolve().parents[2] / SettingsLoader().get(
    "data_dir", "data"
)


def load_json(filename: str | Path, default: list | dict) -> list | dict:
    """Загружает JSON-файл или возвращает значение по умолчанию"""
    filepath = DATA_DIR / filename

    if not filepath.exists():
        return default.copy()

    with filepath.open("r", encoding="utf-8") as file:
        return json.load(file)


def save_json(filename: str | Path, data: list | dict) -> None:
    """Безопасно сохраняет данные в JSON-файл"""
    filepath = DATA_DIR / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)

    temp_path = None

    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            dir=filepath.parent,
            prefix=f".{filepath.name}.",
            suffix=".tmp",
            delete=False,
        ) as temp_file:
            temp_path = Path(temp_file.name)

            json.dump(data, temp_file, ensure_ascii=False, indent=4)
            temp_file.flush()
            os.fsync(temp_file.fileno())

        os.replace(temp_path, filepath)

    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
