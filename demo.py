"""Offline end-to-end (no keys, no network): transcript -> validated
recipe JSON -> nyum book file -> TTS text. Proves the full loop runs."""
import os
import tempfile

from extractor import caps, extract, speak, to_nyum

TRANSCRIPT = ("Soak tamarind lemon-sized. Add a handful of dal, a little hing, "
              "not that much. Don't rush the onions, they'll punish you.")

# what the LLM returns for TRANSCRIPT (format enforced by response_format)
LLM_JSON = {"title": "Demo Sambar",
            "ingredients": ["tamarind lemon-sized", "a handful of dal",
                            "a little hing"],
            "steps": ["Soak tamarind.", "Add dal and hing."],
            "tips": ["Don't rush the onions, they'll punish you."],
            "unclear": ["How big is Thatha's handful?"]}


def demo():
    recipe = extract.validate(LLM_JSON)  # same gate server uses
    fn, md = to_nyum.to_nyum(recipe, author="Thatha", size="4 servings")
    book = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "book", "_recipes")
    os.makedirs(book, exist_ok=True)
    with open(os.path.join(book, fn), "w") as f:
        f.write(md)
    text = speak.recipe_text(recipe)
    assert "Demo Sambar" in text and "Step 1" in text
    try:
        speak.speak(text, "voice-id", "/tmp/x.mp3")
        raise SystemExit("speak should require ELEVENLABS_API_KEY")
    except RuntimeError:
        pass
    with tempfile.NamedTemporaryFile(delete=True) as f:
        assert caps.spend("mem_ops", 1, f.name + ".json")["mem_ops"] == 1
    print(f"demo OK -> book/_recipes/{fn} ({len(md)} chars, "
          f"{len(text)} TTS chars)")


if __name__ == "__main__":
    demo()
