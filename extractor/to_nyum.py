"""Recipe JSON -> nyum Markdown. Verbatim quantities, unclear stays draft-only."""
import re


def _slug(title: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    if not slug or slug == "index":
        slug = "recipe"
    return slug  # ponytail: nyum breaks on spaces and index.md


def to_nyum(recipe: dict, author: str = "Grandpa", category: str = "Family",
            size: str = "", time: str = "") -> tuple[str, str]:
    """Return (filename, markdown). unclear[] never reaches print output."""
    front = [f"title: {recipe['title']}", f"author: {author}",
             f"category: {category}", "memo: ✓"]
    if recipe.get("tips"):
        front.append(f"description: {recipe['tips'][0]}")
    if size:
        front.append(f"size: {size}")
    if time:
        front.append(f"time: {time}")
    lines = ["---", *front, "---", ""]
    for i, step in enumerate(recipe["steps"]):
        ings = recipe["ingredients"] if i == 0 else []  # keep-all-first, steps flow
        for ing in ings:
            lines.append(f"* `{ing}`")
            lines.append("")
        lines += [f"> {step}", "", "---", ""]
    if recipe.get("tips"):
        lines.append("> Tips: " + " ".join(recipe["tips"]))
        lines.append("")
    return _slug(recipe["title"]) + ".md", "\n".join(lines).rstrip() + "\n"
