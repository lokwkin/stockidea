from datetime import date
import json
from typing import Any
from stockpick.config import CACHE_DIR


def save_to_cache(key: str, data: Any) -> None:
    CACHE_DIR.mkdir(exist_ok=True)
    cache_path = CACHE_DIR / f"{key}.json"

    with open(cache_path, "w") as f:
        json.dump({
            "cache_date": date.today().isoformat(),  # TTL is 1 day
            "data": data,
        }, f)


def load_from_cache(key: str) -> Any | None:
    CACHE_DIR.mkdir(exist_ok=True)
    cache_path = CACHE_DIR / f"{key}.json"

    if not cache_path.exists():
        return None

    with open(cache_path, "r") as f:
        cached = json.load(f)

    if cached.get("cache_date") != date.today().isoformat():
        return None

    return cached.get("data")
