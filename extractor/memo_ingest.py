"""Upload intake: allowlist + size cap + stable id. No third-party deps."""
import hashlib
import os

ALLOWED_EXTS = {".m4a", ".mp3", ".opus", ".ogg", ".wav", ".webm"}
MAX_BYTES = 25 * 1024 * 1024  # ~5 min of m4a/opus voice memo
MAX_MINUTES = 5


def check_upload(filename: str, n_bytes: int) -> None:
    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_EXTS:
        raise ValueError(f"bad extension {ext!r}, allowed: {sorted(ALLOWED_EXTS)}")
    if n_bytes > MAX_BYTES:
        raise ValueError(f"{n_bytes} bytes over {MAX_BYTES} cap (~5 min memo)")


def memo_id(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()[:16]


def check_duration_seconds(path: str) -> None:
    """Best-effort duration cap via ffprobe; skip silently if absent."""
    import json
    import shutil
    import subprocess

    if shutil.which("ffprobe") is None:
        return
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_entries", "format=duration", path],
            capture_output=True, text=True, timeout=30,
        )
        dur = float(json.loads(out.stdout)["format"]["duration"])
    except Exception:
        return  # ponytail: unparseable duration never blocks intake
    if dur > MAX_MINUTES * 60:
        raise ValueError(f"{dur:.0f}s over {MAX_MINUTES} min cap")

