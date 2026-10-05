"""Spend caps persisted to a JSON file. Raises CapExceeded past cap."""
import json
import os

CAPS = {
    "stt_credits": 49500,   # 150 min x 330
    "tts_chars": 60000,
    "mem_ops": 1077,        # ~$4.20 / $0.0039
    "tinker_calls": 500,
}
DEFAULT_PATH = os.path.join(os.path.dirname(__file__), "..", "spend.json")


class CapExceeded(Exception):
    pass


def _load(path: str = DEFAULT_PATH) -> dict:
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        return {k: 0 for k in CAPS}


def _save(used: dict, path: str = DEFAULT_PATH) -> None:
    with open(path, "w") as f:
        json.dump(used, f)


def check(key: str, amount: int, path: str = DEFAULT_PATH) -> dict:
    used = _load(path)
    if used.get(key, 0) + amount > CAPS[key]:
        raise CapExceeded(f"{key} cap {CAPS[key]} exceeded")
    return used


def spend(key: str, amount: int, path: str = DEFAULT_PATH) -> dict:
    used = _load(path)
    if used.get(key, 0) + amount > CAPS[key]:
        raise CapExceeded(f"{key} cap {CAPS[key]} exceeded")
    used[key] = used.get(key, 0) + amount
    _save(used, path)
    return used
