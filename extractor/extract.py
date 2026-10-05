"""Transcript -> recipe JSON. Two stdlib backends (env LLM_BACKEND):
- openai (default): any OpenAI-compatible /chat/completions (Ollama, Tinker).
- backboard: hosted via Backboard threads API, cheapest model
  (claude-haiku-4-5, $1/1M in) — zero installs, ~$0.005/recipe.
Temperature 0.2, JSON only."""
import json
import os
import re
import urllib.request

BB_BASE = os.getenv("BACKBOARD_BASE_URL", "https://app.backboard.io/api")
BB_MODEL = os.getenv("BACKBOARD_MODEL", "claude-haiku-4-5-20251001")

SYSTEM = """You turn a transcript of an elderly cook talking into a recipe.
Return ONLY JSON with these keys:
title (string), ingredients (list of strings), steps (list of strings),
tips (list of strings), unclear (list of strings).
Rules:
- Use the speaker's own words for quantities ("a handful", "a little").
- NEVER invent a quantity, ingredient or step that was not said.
- If something is vague or missing, put a short question in `unclear`.
- Keep his personal asides in `tips`.
- If the transcript is NOT about a food recipe, return empty title/lists and
  put "not a recipe" in `unclear`."""

REQUIRED_KEYS = ("title", "ingredients", "steps", "tips", "unclear")


class NonRecipeError(ValueError):
    pass


def build_messages(transcript: str, out_language: str = "the same language as the transcript") -> list:
    if out_language.strip().lower() in ("", "auto"):
        out_language = "the same language as the transcript"
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user",
         "content": f"Write the recipe in {out_language}.\n\nTranscript:\n{transcript}"},
    ]


def extract(transcript: str, out_language: str = "the same language as the transcript") -> dict:
    if out_language.strip().lower() in ("", "auto"):
        out_language = "the same language as the transcript"
    if os.getenv("LLM_BACKEND", "openai").lower() == "backboard":
        return validate(_json_loads(_extract_backboard(transcript,
                                                       out_language)))
    base = os.getenv("LLM_BASE_URL", "http://localhost:11434/v1").rstrip("/")
    model = os.getenv("LLM_MODEL", "qwen2.5:7b")
    key = os.getenv("LLM_API_KEY", "ollama")
    payload = json.dumps({
        "model": model,
        "messages": build_messages(transcript, out_language),
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }).encode()
    req = urllib.request.Request(
        f"{base}/chat/completions", data=payload,
        headers={"Content-Type": "application/json",
                 "Authorization": f"Bearer {key}"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        content = json.load(r)["choices"][0]["message"]["content"]
    return validate(_json_loads(content))


def _extract_backboard(transcript: str, out_language: str) -> str:
    key = os.getenv("BACKBOARD_API_KEY")
    if not key:
        raise RuntimeError("set BACKBOARD_API_KEY for backboard backend")
    user = (f"{SYSTEM}\n\nWrite the recipe in {out_language}. "
            f"Reply with ONLY the JSON object, no fences.\n\nTranscript:\n{transcript}")
    payload = json.dumps({"content": user, "llm_provider": "anthropic",
                          "model_name": BB_MODEL, "stream": False}).encode()
    req = urllib.request.Request(
        BB_BASE + "/threads/messages", data=payload,
        headers={"X-API-Key": key, "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r).get("content", "")


def _json_loads(text: str) -> dict:
    text = text.strip()
    if text.startswith("```"):  # ponytail: models love fences despite orders
        text = text.split("\n", 1)[1] if "\n" in text else text[3:]
        text = text.rsplit("```", 1)[0]
    return json.loads(text.strip())


def validate(recipe: dict) -> dict:
    missing = [k for k in REQUIRED_KEYS if k not in recipe]
    if missing:
        raise ValueError(f"recipe missing keys: {missing}")
    if not isinstance(recipe["ingredients"], list) or not isinstance(
            recipe["steps"], list):
        raise ValueError("ingredients/steps must be lists")
    if not str(recipe.get("title", "")).strip() or not recipe["ingredients"]\
            or not recipe["steps"]:
        raise NonRecipeError("not a usable recipe: empty title/ingredients/steps")
    if any("not a recipe" in str(u).lower()
           for u in recipe.get("unclear", [])):
        raise NonRecipeError("not a recipe")
    return recipe


COOK_SIGNALS = (
    "add boil fry cook bake grill mix stir salt pepper onion garlic oil water "
    "rice dal flour sugar milk egg tomato potato chicken meat fish bread dough "
    "sauce soup curry recipe marinate soak steam roast chop slice simmer serve "
    "ingredient añadir hervir cocinar freír hornear aceite sal ajo cebolla arroz "
    "harina azúcar leche huevo tomate papa pollo carne pescado pan sopa curry "
    "receta nấu add recipe garam masala turmeric paneer atta daal "
    "दाल चावल नमक प्याज तेल पानी उबाल भून मिला पका हल्दी नुस्खा "
    "طبخ وصفة زيت ملح بصل ثوم دجاج لحم سمك أرز ماء بيض خبز شوربة "
    "食谱 炒 煮 炸 烤 盐 油 葱 蒜 鸡肉 牛肉 鱼 米饭 面 汤 水 鸡蛋 面粉 "
    "ajouter cuire huile sel oignon ail riz farine sucre lait œuf tomate "
    "poulet viande poisson soupe recette cozinhar adicionar sal óle óleo cebola "
    "alho arroz farinha açúcar leite ovo tomate frango carne peixe pão sopa "
    "kochen rezept öl salz zwiebel knoblauch hähnchen fleisch fisch reis mehl "
    "zucker milch ei tomaten kartoffeln suppe braten backen готовить добавить "
    "соль лук чеснок масло рис мука сахар молоко яйцо помидор картофель курица "
    "мясо рыба суп рецепт masak tambah garam bawang minyak nasi tepung gula "
    "susu telur tomat ayam daging ikan sup resep"
).split()


def is_recipe_transcript(text: str) -> bool:
    low = text.lower()
    return any(w in low for w in COOK_SIGNALS)
