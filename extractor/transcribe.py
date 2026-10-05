"""Transcription with spend-aware backend order. Lazy imports only."""
import json
import os
import re
import urllib.request

ELEVENLABS_STT_URL = "https://api.elevenlabs.io/v1/speech-to-text"
CREDITS_PER_MIN = 330
LOCAL_MODEL = os.getenv("LOCAL_STT_MODEL", "small")
LOCAL_MIN_WORDS = 5
LOCAL_MIN_AVG_LOGPROB = -0.75
LOCAL_MAX_NO_SPEECH = 0.60
LOCAL_MAX_COMPRESSION = 2.4
LOCAL_MIN_LANGUAGE_PROBABILITY = 0.45
LOOP_NGRAMS = (5, 7, 10)
LOOP_MAX_REPEATS = 3


class TranscriptionError(RuntimeError):
    pass


class NoBackendError(TranscriptionError):
    pass


class UnclearAudioError(ValueError):
    pass


def _words(text: str) -> list:
    return re.findall(r"[^\W\d_]+(?:['’][^\W\d_]+)?", text.lower())


def _has_loop(words: list) -> bool:
    for n in LOOP_NGRAMS:
        if len(words) < n * 2:
            continue
        counts = {}
        for i in range(len(words) - n + 1):
            gram = tuple(words[i:i + n])
            counts[gram] = counts.get(gram, 0) + 1
            if counts[gram] > LOOP_MAX_REPEATS:
                return True
    return False


def assess_local_segments(segments, info=None) -> tuple[str, dict]:
    """Score faster-whisper output without spending cloud credits."""
    words = []
    logprob_total = 0.0
    no_speech_total = 0.0
    compression = 0.0
    texts = []
    for segment in segments or []:
        text = str(getattr(segment, "text", "") or "").strip()
        tokens = _words(text)
        if not tokens:
            continue
        n = len(tokens)
        words.extend(tokens)
        texts.append(text)
        logprob_total += float(getattr(segment, "avg_logprob", 0.0)) * n
        no_speech_total += float(getattr(segment, "no_speech_prob", 0.0)) * n
        compression = max(compression,
                          float(getattr(segment, "compression_ratio", 0.0)))
    joined = " ".join(texts)
    assessment = {
        "words": len(words),
        "avg_logprob": logprob_total / len(words) if words else 0.0,
        "no_speech": no_speech_total / len(words) if words else 1.0,
        "compression": compression,
        "language": getattr(info, "language", ""),
        "language_probability": getattr(info, "language_probability", None),
        "loop": _has_loop(words),
        "usable": False,
        "reason": "",
    }
    if assessment["words"] < LOCAL_MIN_WORDS:
        assessment["reason"] = "too little usable speech"
    elif assessment["avg_logprob"] < LOCAL_MIN_AVG_LOGPROB:
        assessment["reason"] = "low local confidence"
    elif assessment["no_speech"] > LOCAL_MAX_NO_SPEECH:
        assessment["reason"] = "likely no speech"
    elif assessment["compression"] >= LOCAL_MAX_COMPRESSION:
        assessment["reason"] = "repetitive local output"
    elif assessment["loop"]:
        assessment["reason"] = "repeated local output"
    elif (assessment["language_probability"] is not None and
          assessment["language_probability"] < LOCAL_MIN_LANGUAGE_PROBABILITY):
        assessment["reason"] = "uncertain local language"
    else:
        assessment["usable"] = True
    return joined, assessment


def local_transcribe(path: str, faster_whisper, language: str = "") -> tuple[str, dict]:
    """Run the installed local model and score its transcript."""
    model = faster_whisper.WhisperModel(LOCAL_MODEL, device="cpu",
                                        compute_type="int8")
    segments, info = model.transcribe(path, language=language or None)
    return assess_local_segments(segments, info)


_UNSET = object()


def transcribe_with_fallback(path: str, language: str = "",
                             local_module=_UNSET,
                             scribe_impl=None,
                             scribe_budget_check=None) -> tuple[str, str, dict]:
    """Try local STT first, then retry the same file with Scribe.

    Cloud credits are used only when local output is unusable and a
    caller-approved budget check passes immediately before Scribe.
    """
    if local_module is _UNSET:
        try:
            import faster_whisper as local_module  # type: ignore
        except ImportError:
            local_module = None
    local_error = None
    if local_module is not None:
        try:
            text, assessment = local_transcribe(path, local_module, language)
            if assessment["usable"]:
                return text, "faster-whisper", assessment
            local_error = assessment["reason"] or "uncertain local transcript"
        except Exception as exc:
            local_error = str(exc) or type(exc).__name__
    else:
        local_error = "faster-whisper not installed"
    if not os.getenv("ELEVENLABS_API_KEY"):
        if local_module is None:
            raise NoBackendError(
                "no backend: set ELEVENLABS_API_KEY or pip install faster-whisper"
            )
        raise UnclearAudioError(
            "local transcription was uncertain "
            f"({local_error}); set ELEVENLABS_API_KEY for automatic cloud retry"
        )
    if scribe_budget_check is not None:
        scribe_budget_check()
    scribe = scribe_impl or _scribe
    text = scribe(path, language)
    return text, "scribe", {"fallback": local_error}


def transcribe(path: str, language: str = "") -> tuple[str, str]:
    """Return (text, backend). Raises RuntimeError if nothing configured."""
    text, backend, _ = transcribe_with_fallback(path, language)
    return text, backend


def _scribe(path: str, language: str) -> str:
    import mimetypes

    boundary = "----memo-boundary"
    with open(path, "rb") as f:
        audio = f.read()
    ctype = mimetypes.guess_type(path)[0] or "audio/mp4"
    body = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; "
        f"filename=\"memo\"\r\nContent-Type: {ctype}\r\n\r\n"
    ).encode() + audio + (
        f"\r\n--{boundary}\r\nContent-Disposition: form-data; "
        f"name=\"model_id\"\r\n\r\nscribe_v2\r\n"
        + (f"--{boundary}\r\nContent-Disposition: form-data; "
           f"name=\"language_code\"\r\n\r\n{language}\r\n" if language else "")
        + f"--{boundary}--\r\n"
    ).encode()
    req = urllib.request.Request(
        ELEVENLABS_STT_URL, data=body,
        headers={"xi-api-key": os.environ["ELEVENLABS_API_KEY"],
                 "Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r).get("text", "")

