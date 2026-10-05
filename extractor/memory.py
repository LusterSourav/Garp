"""Backboard persistent memory: one thread per recipe. Stdlib only.
No key -> RuntimeError (caller degrades to local-only, burns nothing)."""
import json
import os
import urllib.request

BASE = os.getenv("BACKBOARD_BASE_URL", "https://app.backboard.io/api")


def _post(path: str, payload: dict) -> dict:
    key = os.getenv("BACKBOARD_API_KEY")
    if not key:
        raise RuntimeError("set BACKBOARD_API_KEY for shared memory")
    req = urllib.request.Request(
        BASE + path, data=json.dumps(payload).encode(),
        headers={"X-API-Key": key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def remember(recipe: dict) -> str:
    """Store recipe facts; return thread_id for later ask()."""
    text = (f"Remember this family recipe '{recipe['title']}': "
            f"ingredients: {'; '.join(recipe['ingredients'])}. "
            f"steps: {' '.join(recipe['steps'])}. "
            f"tips: {' '.join(recipe.get('tips', []))}. "
            f"Unresolved, do not guess: {' '.join(recipe.get('unclear', []))}.")
    return _post("/threads/messages", {"content": text})["thread_id"]


def ask(question: str, thread_id: str | None = None) -> dict:
    """Ask across stored recipe memory. Pass thread_id to continue."""
    payload = {"content": question}
    if thread_id:
        payload["thread_id"] = thread_id
    return _post("/threads/messages", payload)
