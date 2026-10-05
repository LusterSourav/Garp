"""Read-aloud: recipe text -> mp3 via ElevenLabs TTS. Lazy, key-gated."""
import os
import urllib.request

TTS_URL = "https://api.elevenlabs.io/v1/text-to-speech/"


def speak(text: str, voice_id: str, out_path: str,
          model: str = "eleven_flash_v2_5") -> str:
    """Write mp3, return path. Raises RuntimeError without key (no network)."""
    import json

    key = os.getenv("ELEVENLABS_API_KEY")
    if not key:
        raise RuntimeError("set ELEVENLABS_API_KEY for read-aloud")
    payload = json.dumps({"text": text, "model_id": model}).encode()
    req = urllib.request.Request(
        TTS_URL + voice_id, data=payload,
        headers={"xi-api-key": key, "Content-Type": "application/json",
                 "Accept": "audio/mpeg"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        audio = r.read()
    with open(out_path, "wb") as f:
        f.write(audio)
    return out_path


def recipe_text(recipe: dict) -> str:
    lines = [recipe["title"] + "."]
    lines += [f"Step {i}: {s}" for i, s in enumerate(recipe["steps"], 1)]
    if recipe.get("tips"):
        lines.append("Tips: " + " ".join(recipe["tips"]))
    return " ".join(lines)
