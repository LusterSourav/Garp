"""Offline self-check: no network, no keys. Fails if logic breaks."""
import html
import os
import re
import tempfile

from extractor import bookview, caps, extract, iconboil, memo_ingest, server
from extractor import transcribe


def demo():
    # ingest guards
    try:
        memo_ingest.check_upload("x.exe", 10)
        raise SystemExit("ext allowlist broken")
    except ValueError:
        pass
    try:
        memo_ingest.check_upload("a.m4a", 99 * 1024 * 1024)
        raise SystemExit("size cap broken")
    except ValueError:
        pass
    assert len(memo_ingest.memo_id(b"abc")) == 16

    # prompt + schema
    msgs = extract.build_messages("add a handful of dal", "English")
    assert "NEVER invent" in msgs[0]["content"]
    assert "English" in msgs[1]["content"]
    good = {"title": "t", "ingredients": ["a handful of dal"],
            "steps": ["s"], "tips": [], "unclear": ["how big is handful?"]}
    assert extract.validate(good) == good
    try:
        extract.validate({"title": "t"})
        raise SystemExit("schema validation broken")
    except ValueError:
        pass
    try:
        extract.validate({"title": "", "ingredients": [], "steps": [],
                          "tips": [], "unclear": ["not a recipe"]})
        raise SystemExit("non-recipe gate broken")
    except extract.NonRecipeError:
        pass

    # caps
    with tempfile.NamedTemporaryFile(delete=True) as f:
        path = f.name + ".json"
        caps.spend("mem_ops", 7, path)
        try:
            caps.spend("mem_ops", 10 ** 9, path)
            raise SystemExit("cap enforcement broken")
        except caps.CapExceeded:
            pass
        try:
            caps.check("mem_ops", 10 ** 9, path)
            raise SystemExit("cap precheck broken")
        except caps.CapExceeded:
            pass

    # local-first STT: clear audio stays local, uncertain audio retries once
    class _Seg:
        def __init__(self, text, logprob, no_speech, compression):
            self.text = text
            self.avg_logprob = logprob
            self.no_speech_prob = no_speech
            self.compression_ratio = compression

    class _Info:
        language = "en"
        language_probability = 0.97

    def _fw(segments):
        class _Model:
            def __init__(self, *args, **kwargs):
                pass

            def transcribe(self, heard_path, language=None):
                assert heard_path == "/tmp/memo.m4a"
                return segments, _Info()

        return type("FakeFasterWhisper", (), {"WhisperModel": _Model})

    clear = [_Seg("Add a handful of dal and cook the onions slowly", -0.2,
                  0.05, 0.7)]
    noisy = [_Seg("music music music music music", -1.4, 0.92, 3.1)]
    text, usable = transcribe.assess_local_segments(clear, _Info())
    assert usable["usable"] and usable["words"] >= 5
    _, uncertain = transcribe.assess_local_segments(noisy, _Info())
    assert not uncertain["usable"]
    key = os.environ.pop("ELEVENLABS_API_KEY", None)
    try:
        text, backend, detail = transcribe.transcribe_with_fallback(
            "/tmp/memo.m4a", "", local_module=_fw(clear))
        assert (text, backend) == (
            "Add a handful of dal and cook the onions slowly", "faster-whisper")
        assert detail["usable"]
        try:
            transcribe.transcribe_with_fallback("/tmp/memo.m4a", "",
                                                local_module=_fw(noisy))
            raise SystemExit("uncertain local audio should not pass")
        except transcribe.UnclearAudioError:
            pass
        try:
            transcribe.transcribe_with_fallback("/tmp/memo.m4a", "",
                                                local_module=None)
            raise SystemExit("missing STT backend should fail")
        except transcribe.NoBackendError:
            pass
    finally:
        if key is not None:
            os.environ["ELEVENLABS_API_KEY"] = key
    old_key = os.environ.get("ELEVENLABS_API_KEY")
    os.environ["ELEVENLABS_API_KEY"] = "test-key"
    try:
        heard = []

        def _scribe(path, language):
            heard.append(path)
            return "cloud transcript"

        budget = []
        text, backend, detail = transcribe.transcribe_with_fallback(
            "/tmp/memo.m4a", "", local_module=_fw(noisy),
            scribe_impl=_scribe,
            scribe_budget_check=lambda: budget.append(1))
        assert (text, backend) == ("cloud transcript", "scribe")
        assert heard == ["/tmp/memo.m4a"] and budget == [1]
        assert "low local confidence" in detail["fallback"]
        budget.clear()
        text, backend, _ = transcribe.transcribe_with_fallback(
            "/tmp/memo.m4a", "", local_module=_fw(clear),
            scribe_impl=_scribe,
            scribe_budget_check=lambda: budget.append(1))
        assert backend == "faster-whisper" and budget == []
    finally:
        if old_key is None:
            os.environ.pop("ELEVENLABS_API_KEY", None)
        else:
            os.environ["ELEVENLABS_API_KEY"] = old_key
    with tempfile.NamedTemporaryFile(delete=False) as f:
        temp_path = f.name
    server._remove_temp_file(temp_path)
    server._remove_temp_file(temp_path)
    assert not os.path.exists(temp_path)

    # icons: every referenced svg exists, normalizes to M/L-only paths
    root = os.path.dirname(os.path.abspath(__file__))
    src = ""
    for rel in ("extractor/bookview.py", "assets/search.js", "assets/style.css"):
        with open(os.path.join(root, rel)) as f:
            src += f.read()
    refs = set(re.findall(r"tabler-icon-([a-z0-9-]+)\.svg", src))
    refs |= set(re.findall(r"bic\(\"([a-z0-9-]+)\"", src))
    refs |= set(re.findall(r"_icon\(['\"]([a-z0-9-]+)['\"]", src))
    refs |= {icon for _, icon, _ in bookview.FLAGS}
    disk = {fn[len("tabler-icon-"):-len(".svg")] for fn in
            os.listdir(os.path.join(root, "assets", "tabler-icons"))
            if fn.endswith(".svg")}
    assert refs, "no icon refs found"
    assert refs <= disk, f"missing svg files: {refs - disk}"
    assert disk <= refs, f"dead svg files: {disk - refs}"
    got = iconboil.all_icons()
    assert refs <= set(got), f"iconboil gaps: {refs - set(got)}"
    for name in refs:
        d = got[name]
        assert d["paths"], f"{name}: no paths"
        assert d["color"], f"{name}: no color"
        for p in d["paths"]:
            assert re.fullmatch(r"[ML0-9.\- ]+", p), f"{name}: bad path {p[:40]}"
    # boil spans carry path data + <img> fallback; memo badge exists
    h = bookview._icons({"favorite": True, "memo": True, "spicy": True})
    assert "microphone" in h and "data-paths" in h and "<img" in h
    assert "star" in h and "pepper" in h
    for rel in ("assets/boil.js", "assets/rough.js"):
        assert os.path.isfile(os.path.join(root, rel)), f"missing {rel}"

    # plain print text everywhere: escaping holds, no stroke-draw SVG remains
    esc = bookview._book(title="Ab <c>")
    assert "&lt;c&gt;" in esc and 'svg class="hand' not in esc
    assert 'class="draw"' not in esc
    # footer gone, plain tagline on the homepage
    idx = bookview.index([], {"english": "English", "spanish": "Spanish"})
    assert "Enjoy!" not in idx and "<footer" not in idx
    assert "Turn your grandpa" in idx and 'svg class="hand' not in idx
    assert 'class="draw"' not in idx
    assert 'id="upload"' not in idx and 'name="language" value="auto"' in idx
    assert 'id="voice_btn"' in idx and 'id="live_btn"' in idx
    assert 'Add a voice or live memo' in idx and 'option value=' not in idx
    assert 'Accept\':\'application/json\'' in idx and 'Auto-stopped' in idx
    assert extract.is_recipe_transcript("Add a handful of dal and onions")
    assert not extract.is_recipe_transcript("I am going to the bank tomorrow")
    recs = bookview.list_recipes(os.path.join(root, "book", "_recipes"))
    assert recs, "need a recipe fixture"
    rp = bookview.recipe_page(recs[0])
    assert "Enjoy!" not in rp and "<footer" not in rp
    assert 'svg class="hand' not in rp and 'class="draw"' not in rp
    # recipe detail lives in the book: no steps section, no header h1,
    # full ingredients + steps inside #top-text
    assert "<section>" not in rp and "<h1>" not in rp
    top = rp.split('id="top-text"')[1]
    m0 = recs[0]["meta"]
    for _s in recs[0]["steps"]:
        for _q, _n in _s["ings"]:
            assert html.escape(_n) in top or _n in top
        if _s["text"]:
            assert html.escape(_s["text"]) in top
    assert m0.get("title", "") in rp
    assert '<ul class="meta">' in rp
    # recipe pages: proper typography, no trailing dash, paged reading
    assert " \u2014 </p>" not in rp
    assert 'id="recipe_pages"' in rp and 'id="pturn_left"' in rp
    assert 'id="pturn_right"' in rp and 'page_prev' not in rp
    assert 'page_next' not in rp and 'recipe_pager' not in rp
    assert "class=\"step\"" in rp and "class=\"ing\"" in rp
    assert "turned" in rp and "recipe_pages" in rp
    cp = bookview.category_page(recs[0]["meta"].get("category", "x"), recs)
    assert "Enjoy!" not in cp and "<footer" not in cp
    assert "<h1>Family</h1>" in cp and 'svg class="hand' not in cp
    # category = centered 3D book only: no list section can overlap it
    assert "<section" not in cp
    # recipe meta row: tagged, absent elsewhere; black-ink scoped rules exist
    assert '<ul class="meta">' not in cp and '<ul class="meta">' not in idx
    with open(os.path.join(root, "assets", "style.css")) as f:
        css = f.read()
    assert "main.recipe header ul.meta li" in css and "#16161d" in css
    assert "ul.meta .boil canvas" in css
    # header must not clip the absolute search overlay (flow-root, not overflow)
    assert "display: flow-root" in css
    assert "overflow: auto;  /* clearfix */" not in css
    # result/category rows: icons inline before titles, compact cards+titles
    assert ".search .results h3 .icons" in css and "float: none" in css
    assert "section h3 svg.hand" in css and "height: 1.6em" in css
    assert "padding: 0.22rem 0.8rem" in css
    # print typography: vendored barlow/lora only; no playfair/crimson/hand links
    assert "barlow/webfont.css" in idx and "lora/webfont.css" in idx
    assert "playfair/webfont.css" not in idx and "crimson/webfont.css" not in idx
    assert "hand/webfont.css" not in idx
    # header tagline present as plain text (only the print fallback uses #fff)
    assert 'class="tag"' in idx and "Turn your grandpa" in idx
    # resting book centers on the closed box (union only sets scale)
    assert "closed.l-bs.left)+closed.w/2" in rp.replace(" ", "")
    # homepage: animation fully removed; 3D book deck with default content
    assert "rb-hero" not in idx and "rainbros" not in idx
    assert 'class="draw"' not in idx and 'id="book3d"' in idx
    assert "Add a voice or live memo" in idx and 'id="voice_intake"' in idx
    assert not os.path.exists(os.path.join(root, "assets", "rainbros.css"))
    assert not hasattr(bookview, "_rainbros") and not hasattr(bookview, "RAINBROS_JS")
    # book on every page, generated from page content
    assert 'id="book3d"' in rp and 'id="top-text"' in rp
    # book layout spread removed completely: 3D book only, no nav-to-spread
    assert "location.href='/spread'" not in rp and "spread-text" not in rp
    assert "ob-spread" not in rp and "ob-page" not in rp and "ob-pager" not in rp
    assert "spread-open" not in rp and "Open book layout" not in rp
    assert not hasattr(bookview, "spread_page")
    assert not hasattr(bookview, "_spread")
    assert hasattr(bookview, "PAGER_JS")  # recipe page-turn paginator
    assert not hasattr(bookview, "_family") and not hasattr(bookview, "OB_LINK")
    assert not os.path.exists(os.path.join(root, "assets", "ob-spread.css"))
    assert not os.path.exists(os.path.join(root, "assets", "fonts", "playfair"))
    assert not os.path.exists(os.path.join(root, "assets", "fonts", "crimson"))
    with open(os.path.join(root, "extractor", "server.py")) as f:
        srv_routes = f.read()
    assert "/spread" not in srv_routes and "spread_page" not in srv_routes
    title = recs[0]["meta"].get("title", "")
    assert f"<h3>{html.escape(title)}</h3>" in rp  # plain book-face title
    assert 'id="book3d"' in cp and 'id="top-text"' in cp
    with open(os.path.join(root, "assets", "search.js")) as f:
        search_src = f.read()
    assert "function text(" in search_src and "svg.hand" not in search_src
    assert "function bic(" in search_src
    # no unversioned changing assets: search tag carries ?v=
    assert "search.js?v=" in idx
    # animated tab favicon: versioned, guarded, cheap
    assert "tab-anim.js?v=" in idx
    assert "favicon.svg?v=" in idx  # icon itself cache-busted (immutable assets)
    # version stamp: served HTML always names the running code (stale-server check)
    assert f'<meta name="garp-v" content="{bookview.V}">' in idx
    with open(os.path.join(root, "extractor", "server.py")) as f:
        srv = f.read()
    assert "garp v{bookview.V}" in srv  # boot banner names version + port
    with open(os.path.join(root, "assets", "tab-anim.js")) as f:
        tab = f.read()
    assert "prefers-reduced-motion" in tab and "document.hidden" in tab
    assert "toDataURL" in tab and "image/png" in tab
    assert "replaceChild" in tab and "tabdebug=1" in tab
    # boil engine: guarded, restores fallback, reports status
    with open(os.path.join(root, "assets", "boil.js")) as f:
        boil = f.read()
    assert "__boil" in boil and "replaceChild(span.__boilImg" in boil
    assert "clientWidth" in boil and "rough.canvas unavailable" in boil
    # responsive: overlay results, height-driven titles, no page overflow
    with open(os.path.join(root, "assets", "style.css")) as f:
        css_all = f.read()
    assert ".home .search .results" in css_all
    assert "position: absolute" in css_all and "overscroll-behavior: contain" in css_all
    assert "section h3 svg.hand" in css_all
    assert "overflow-x: hidden" in css_all
    assert "innerHeight" in rp  # book fit caps to viewport height (recipe pages)
    print("component-1 smoke OK")


if __name__ == "__main__":
    demo()
