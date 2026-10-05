# Garp

Turn your grandpa's voice memos into a family recipe book.

Record or upload a voice note. Garp transcribes it, pulls out the recipe in the speaker's own words, and prints it as a page in a 3D family cookbook. Anything that isn't a recipe gets rejected and never touches the book.

## Run it

```bash
PORT=8001 python3 -m extractor.server
```

Open `http://127.0.0.1:8001`. Click **Add a voice or live memo**, then Voice to upload a file or Live to record in the browser.

Set these for the full pipeline (missing key = local fallback):

```
ELEVENLABS_API_KEY=   # speech-to-text
BACKBOARD_API_KEY=    # recipe extraction (LLM_BACKEND=backboard)
TINKER_API_KEY=       # speech fine-tuning experiments (sft/)
```

## How it works

```
voice memo → POST /extract → transcribe → recipe JSON → book/_recipes/*.md → 3D page
```

- `extractor/memo_ingest.py` — file allowlist, 25 MB / 5 min caps
- `extractor/transcribe.py` — local faster-whisper first, ElevenLabs Scribe retry on the same file, credits only on cloud use
- `extractor/extract.py` — transcript to recipe JSON, strict schema, non-recipes rejected
- `extractor/to_nyum.py` — recipe JSON to book Markdown
- `extractor/bookview.py` — the 3D book, paged reading, in-book Voice/Live intake
- `extractor/server.py` — stdlib HTTP, no framework
- `sft/` — Tinker fine-tuning experiments (runs locally, not on Render)

## Deploy

`render.yaml` is a one-click Render blueprint. Add the API keys in the Render dashboard (never commit them) and attach a disk at `book/_recipes` so saved recipes survive redeploys.
