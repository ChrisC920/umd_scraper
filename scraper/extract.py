from __future__ import annotations

ICON_TO_ALLERGEN = {
    "shellfish": "shellfish",  # must come before "fish"
    "dairy": "dairy",
    "egg": "eggs",
    "fish": "fish",
    "gluten": "gluten",
    "nuts": "nuts",
    "sesame": "sesame",
    "soy": "soy",
}

ICON_TO_TAG = {
    "vegan": "vegan",
    "vegetarian": "vegetarian",
    "halalfriendly": "halal",
    "local": "local",
    "smartchoice": "smart_choice",
}

ALLERGEN_TEXT_MAP = {
    "milk": "dairy",
    "dairy": "dairy",
    "eggs": "eggs",
    "egg": "eggs",
    "fish": "fish",
    "wheat": "gluten",
    "gluten": "gluten",
    "tree nuts": "nuts",
    "peanuts": "nuts",
    "nuts": "nuts",
    "sesame": "sesame",
    "crustacean shellfish": "shellfish",
    "shellfish": "shellfish",
    "soybeans": "soy",
    "soy": "soy",
}


def icon_filename_to_tags(filename: str) -> tuple[str | None, str | None]:
    """Return (allergen, tag) for a single icon filename. Either may be None."""
    lower = filename.lower()
    allergen = next((v for k, v in ICON_TO_ALLERGEN.items() if k in lower), None)
    tag = next((v for k, v in ICON_TO_TAG.items() if k in lower), None)
    return allergen, tag


def parse_allergens_text(text: str) -> list[str]:
    """Parse 'Milk, Eggs, Wheat, Soybeans' → ['dairy','eggs','gluten','soy']."""
    if not text:
        return []
    out: list[str] = []
    for raw in text.split(","):
        key = raw.strip().lower()
        mapped = ALLERGEN_TEXT_MAP.get(key)
        if mapped and mapped not in out:
            out.append(mapped)
    return out
