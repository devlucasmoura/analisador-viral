import json
from pathlib import Path


APP_FOLDER = Path.home() / ".analisador-viral"
CONFIG_FILE = APP_FOLDER / "config.json"


def _ensure_folder():
    APP_FOLDER.mkdir(parents=True, exist_ok=True)


def load_api_key() -> str | None:
    if not CONFIG_FILE.exists():
        return None
    try:
        data = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        return data.get("api_key")
    except (json.JSONDecodeError, OSError):
        return None


def save_api_key(api_key: str) -> None:
    _ensure_folder()
    data = {"api_key": api_key.strip()}
    CONFIG_FILE.write_text(json.dumps(data), encoding="utf-8")


def clear_api_key() -> None:
    if CONFIG_FILE.exists():
        CONFIG_FILE.unlink()
