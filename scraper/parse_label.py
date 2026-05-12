from __future__ import annotations

import re
from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from .extract import parse_allergens_text
from .normalize import clean_food_name, clean_ingredients, clean_serving_size

NUM_RE = re.compile(r"([-+]?\d*\.?\d+)")


@dataclass
class FoodNutrition:
    name: str | None = None
    serving_size: str | None = None
    servings_per: str | None = None
    calories: float | None = None
    total_fat_g: float | None = None
    sat_fat_g: float | None = None
    trans_fat_g: float | None = None
    cholesterol_mg: float | None = None
    sodium_mg: float | None = None
    total_carbs_g: float | None = None
    fiber_g: float | None = None
    sugars_g: float | None = None
    added_sugars_g: float | None = None
    protein_g: float | None = None
    iron_mg: float | None = None
    calcium_mg: float | None = None
    potassium_mg: float | None = None
    vitamin_a_mcg: float | None = None
    vitamin_c_mg: float | None = None
    ingredients: str | None = None
    allergens: list[str] = field(default_factory=list)
    is_empty: bool = False


# Substring → field name. First match wins; order matters (longest/most-specific first).
FIELD_PATTERNS: list[tuple[str, str]] = [
    ("saturated fat", "sat_fat_g"),
    ("trans fat", "trans_fat_g"),
    ("trans fatty acid", "trans_fat_g"),
    ("total fat", "total_fat_g"),
    ("cholesterol", "cholesterol_mg"),
    ("sodium", "sodium_mg"),
    ("dietary fiber", "fiber_g"),
    ("added sugars", "added_sugars_g"),
    ("total sugars", "sugars_g"),
    ("total carbohydrate", "total_carbs_g"),
    ("carbohydrates", "total_carbs_g"),
    ("protein", "protein_g"),
    ("iron", "iron_mg"),
    ("calcium", "calcium_mg"),
    ("potassium", "potassium_mg"),
    ("vitamin a", "vitamin_a_mcg"),
    ("vitamin c", "vitamin_c_mg"),
]


def _to_float(text: str) -> float | None:
    m = NUM_RE.search(text.replace(",", ""))
    return float(m.group(1)) if m else None


def parse_label(html: str) -> FoodNutrition:
    soup = BeautifulSoup(html, "html.parser")
    out = FoodNutrition()

    h2 = soup.find("h2")
    if h2:
        out.name = clean_food_name(h2.get_text(strip=True))

    facts = soup.select_one("table.facts_table")
    if not facts:
        out.is_empty = True
        # still try ingredients/allergens just in case
        _extract_ingredients_allergens(soup, out)
        return out

    serv_size_divs = facts.select("div.nutfactsservsize")
    if len(serv_size_divs) >= 2:
        out.serving_size = clean_serving_size(serv_size_divs[1].get_text(strip=True))

    serv_per = facts.select_one("div.nutfactsservpercont")
    if serv_per:
        from .normalize import collapse_ws
        out.servings_per = collapse_ws(serv_per.get_text(strip=True))

    # Calories per serving — the <p> after the "Calories per serving" header.
    for p in facts.find_all("p"):
        text = p.get_text(strip=True)
        if text and text != "Calories per serving":
            val = _to_float(text)
            if val is not None and out.calories is None:
                out.calories = val
                break

    for span in facts.select("span.nutfactstopnutrient"):
        text = span.get_text(" ", strip=True).lower()
        for needle, field in FIELD_PATTERNS:
            if needle in text:
                if getattr(out, field) is None:
                    val = _to_float(text)
                    if val is not None:
                        setattr(out, field, val)
                break
        if "calories" in text and "per serving" not in text and out.calories is None:
            val = _to_float(text)
            if val is not None:
                out.calories = val

    _extract_ingredients_allergens(soup, out)

    if out.calories is None and out.total_fat_g is None and out.protein_g is None:
        out.is_empty = True
    return out


def _extract_ingredients_allergens(soup: BeautifulSoup, out: FoodNutrition) -> None:
    ing_val = soup.select_one("span.labelingredientsvalue")
    if ing_val:
        out.ingredients = clean_ingredients(ing_val.get_text(" ", strip=True))
    all_val = soup.select_one("span.labelallergensvalue")
    if all_val:
        out.allergens = parse_allergens_text(all_val.get_text(" ", strip=True))
