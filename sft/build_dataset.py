"""Pairs dir -> SFT conversations JSONL. Offline, stdlib only.

Pairs dir layout: N transcript.txt + recipe.json sharing a basename:
  sambar.transcript.txt + sambar.recipe.json
recipe.json keys: title, ingredients, steps, tips, unclear.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from extractor.extract import SYSTEM  # single source of system prompt


def build(pairs_dir: str) -> list:
    convs = []
    for name in sorted(os.listdir(pairs_dir)):
        if not name.endswith(".transcript.txt"):
            continue
        base = name[: -len(".transcript.txt")]
        rpath = os.path.join(pairs_dir, base + ".recipe.json")
        if not os.path.exists(rpath):
            print(f"skip {base}: no recipe.json", file=sys.stderr)
            continue
        with open(os.path.join(pairs_dir, name)) as f:
            transcript = f.read().strip()
        with open(rpath) as f:
            recipe = json.load(f)
        for k in ("title", "ingredients", "steps", "tips", "unclear"):
            if k not in recipe:
                raise ValueError(f"{base}: recipe.json missing {k}")
        convs.append([
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": transcript},
            {"role": "assistant",
             "content": json.dumps(recipe, ensure_ascii=False)},
        ])
    return convs


def main() -> None:
    pairs, out = sys.argv[1], sys.argv[2]
    convs = build(pairs)
    with open(out, "w") as f:
        for c in convs:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    print(f"{len(convs)} pairs -> {out}")


if __name__ == "__main__":
    main()
