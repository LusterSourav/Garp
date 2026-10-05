"""Minimal Render-ready HTTP: GET / (upload page), POST /extract
(multipart memo file), GET /health (spend counters). Stdlib only.
Approved recipes autosave as nyum Markdown into BOOK_DIR."""
import json
import os
import tempfile
from email.parser import BytesParser
from email.policy import HTTP
from http.server import BaseHTTPRequestHandler, HTTPServer

from . import bookview, caps, extract, iconboil, memo_ingest, memory
from . import to_nyum, transcribe

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BOOK_DIR = os.getenv("BOOK_DIR", os.path.join(ROOT, "book", "_recipes"))
ASSETS_DIR = os.path.join(ROOT, "assets")

MIME = {".css": "text/css", ".js": "text/javascript", ".svg": "image/svg+xml",
        ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
        ".woff": "font/woff", ".woff2": "font/woff2",
        ".wav": "audio/wav", ".txt": "text/plain"}

LANGS = {"english": "English", "spanish": "Spanish", "hindi": "Hindi",
         "french": "French", "arabic": "Arabic", "mandarin": "Mandarin",
         "portuguese": "Portuguese", "russian": "Russian",
         "indonesian": "Indonesian", "german": "German"}
STT_LANGS = {"english": "en", "spanish": "es", "hindi": "hi",
             "french": "fr", "arabic": "ar", "mandarin": "zh",
             "portuguese": "pt", "russian": "ru", "indonesian": "id",
             "german": "de"}


def _remove_temp_file(path: str) -> None:
    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


class Handler(BaseHTTPRequestHandler):
    def _json(self, code: int, obj: dict) -> None:
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _html(self, code: int, html_body: str) -> None:
        body = html_body.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):  # exact-nyum book UI + assets + health
        path = self.path.split("?")[0]
        if path == "/health":
            self._json(200, {"ok": True, "v": bookview.V,
                             "spend": caps._load(), "caps": caps.CAPS})
        elif path == "/":
            self._html(200, bookview.index(
                bookview.list_recipes(BOOK_DIR), LANGS))
        elif path == "/search.json":
            self._json(200, bookview.search_index(
                bookview.list_recipes(BOOK_DIR)))
        elif path == "/icons.json":
            self._json(200, iconboil.all_icons())
        elif path.startswith("/assets/"):
            rel = os.path.normpath(
                path[len("/assets/"):])
            if rel.startswith("..") or os.path.isabs(rel):
                return self.send_error(404)
            path = os.path.join(ASSETS_DIR, rel)
            if not os.path.isfile(path):
                return self.send_error(404)
            with open(path, "rb") as f:
                body = f.read()
            self.send_response(200)
            self.send_header("Content-Type", MIME.get(
                os.path.splitext(path)[1].lower(),
                "application/octet-stream"))
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "public, max-age=31536000")
            self.end_headers()
            self.wfile.write(body)
        elif self.path.startswith("/category/"):
            slug = self.path[len("/category/"):].split("?")[0].split("/")[0]
            recs = [r for r in bookview.list_recipes(BOOK_DIR)
                    if "".join(c if c.isalnum() else "-"
                               for c in r["meta"].get("category", "").lower()) == slug]
            if not recs:
                return self.send_error(404)
            cat = recs[0]["meta"].get("category", "")
            self._html(200, bookview.category_page(cat, recs))
        elif self.path.startswith("/recipe/"):
            slug = self.path[len("/recipe/"):].split("?")[0].split("/")[0]
            if not slug.replace("-", "").replace("_", "").isalnum():
                return self.send_error(404)
            path = os.path.join(BOOK_DIR, slug + ".md")
            if not os.path.isfile(path):
                return self.send_error(404)
            try:
                self._html(200, bookview.recipe_page(
                    bookview.parse_recipe(path)))
            except Exception:
                self.send_error(500, "bad recipe file")
        else:
            self.send_error(404)

    def do_POST(self):  # multipart memo upload (no cgi on 3.13+)
        if self.path != "/extract":
            return self.send_error(404)
        try:
            length = int(self.headers.get("Content-Length", 0))
        except ValueError:
            return self._json(400, {"error": "bad Content-Length"})
        if length > memo_ingest.MAX_BYTES + 65536:
            return self._json(413, {"error": "upload too large"})
        raw = self.rfile.read(length)
        head = (f"Content-Type: {self.headers.get('Content-Type', '')}\r\n"
                "MIME-Version: 1.0\r\n\r\n").encode()
        try:
            msg = BytesParser(policy=HTTP).parsebytes(head + raw)
            parts = {p.get_param("name", header="content-disposition"): p
                     for p in msg.iter_parts()}
        except Exception:
            return self._json(400, {"error": "bad multipart body"})
        if "memo" not in parts:
            return self._json(400, {"error": "missing memo file"})
        item = parts["memo"]
        lang_part = parts.get("language")
        lang = (lang_part.get_content().strip() if lang_part is not None
                else "auto")
        if lang not in LANGS and lang != "auto":
            return self._json(400, {"error": f"bad language, pick auto or {sorted(LANGS)}"})
        data = item.get_payload(decode=True) or b""
        filename = item.get_filename() or "memo.m4a"
        try:
            memo_ingest.check_upload(filename, len(data))
        except ValueError as e:
            return self._json(413, {"error": str(e)})
        mid = memo_ingest.memo_id(data)
        with tempfile.NamedTemporaryFile(
                suffix=os.path.splitext(filename)[1] or ".m4a",
                delete=False) as f:
            f.write(data)
            path = f.name
        try:
            memo_ingest.check_duration_seconds(path)
            minutes = max(1, len(data) // (320 * 1024) + 1)  # ~320KB/min m4a
            text, backend, _ = transcribe.transcribe_with_fallback(
                path, language=("" if lang == "auto" else STT_LANGS[lang]),
                scribe_budget_check=lambda: caps.check(
                    "stt_credits", minutes * 330))
            if not text.strip():
                return self._json(400, {"error": "no speech detected"})
            if not extract.is_recipe_transcript(text):
                return self._json(422, {"error": "not related to a recipe"})
            if backend == "scribe":
                caps.spend("stt_credits", minutes * 330)
            else:
                caps.spend("tinker_calls", 0)  # local path burns nothing
            recipe = extract.extract(text, "" if lang == "auto" else LANGS[lang])
            caps.spend("tinker_calls", 1)
            thread_id, saved = None, None
            sm = parts.get("save_memory")
            if sm is not None and sm.get_content().strip().lower() in (
                    "1", "true"):
                try:  # shared memory never fails the request
                    thread_id = memory.remember(recipe)
                    caps.spend("mem_ops", 1)
                except Exception:
                    thread_id = None
            try:  # ponytail: book autosave never fails the request
                os.makedirs(BOOK_DIR, exist_ok=True)
                fn, md = to_nyum.to_nyum(recipe)
                saved = os.path.join(BOOK_DIR, fn)
                with open(saved, "w") as f:
                    f.write(md)
            except Exception:
                saved = None
        except transcribe.UnclearAudioError as e:
            return self._json(400, {"error": str(e)})
        except extract.NonRecipeError as e:
            return self._json(422, {"error": str(e)})
        except caps.CapExceeded as e:
            return self._json(402, {"error": str(e)})
        except Exception as e:
            return self._json(500, {"error": str(e)})
        finally:
            _remove_temp_file(path)
        if (saved and "text/html" in
                self.headers.get("Accept", "")):
            slug = os.path.splitext(os.path.basename(saved))[0]
            self.send_response(303)
            self.send_header("Location", f"/recipe/{slug}")
            self.end_headers()
            return
        slug = os.path.splitext(os.path.basename(
            saved))[0] if saved else None
        self._json(200, {"memo_id": mid, "backend": backend,
                         "thread_id": thread_id, "saved": saved,
                         "slug": slug, **recipe})


def main(port: int = 8000) -> None:
    print(f"garp v{bookview.V} on :{port} (book: {BOOK_DIR})", flush=True)
    HTTPServer(("0.0.0.0", port), Handler).serve_forever()


if __name__ == "__main__":
    main(int(os.getenv("PORT", "8000")))
