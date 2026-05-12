"""Text normalizers for ingestion. Applied at parse time so DB receives uniform data."""
from __future__ import annotations

import re

_WS_RE = re.compile(r"\s+")
_SERVING_UNIT_MAP = {
    "ea": "ea",
    "each": "ea",
    "oz": "oz",
    "ounce": "oz",
    "ounces": "oz",
    "g": "g",
    "gram": "g",
    "grams": "g",
    "ml": "ml",
    "fl": "fl oz",
    "cup": "cup",
    "cups": "cup",
    "tbsp": "tbsp",
    "tsp": "tsp",
    "slice": "slice",
    "slices": "slice",
    "piece": "piece",
    "pieces": "piece",
}
_SERVING_RE = re.compile(r"^\s*([\d./]+)\s*(.*?)\s*$")

# Words that should stay lowercase in a Title-Cased name (small connectors).
_LOWERCASE_WORDS = {
    "a", "an", "and", "as", "at", "but", "by", "for", "in", "of", "on",
    "or", "the", "to", "up", "via", "vs", "w/", "w/o",
}
# Tokens kept verbatim (mostly abbreviations).
_KEEP_AS_IS = {"BBQ", "GF", "DF", "PB", "PB&J", "BLT"}


def collapse_ws(s: str | None) -> str | None:
    if s is None:
        return None
    s = _WS_RE.sub(" ", s).strip()
    return s or None


def title_case_name(s: str | None) -> str | None:
    """Title-case a name while preserving abbreviations and lowercasing connectors."""
    s = collapse_ws(s)
    if s is None:
        return None
    parts = s.split(" ")
    out: list[str] = []
    for i, raw in enumerate(parts):
        token = raw
        upper = token.upper().rstrip(".,;:")
        if upper in _KEEP_AS_IS:
            out.append(upper if not token.endswith((".", ",")) else upper + token[-1])
            continue
        lower = token.lower()
        # Connectors stay lowercase, except as the first/last word.
        if lower in _LOWERCASE_WORDS and 0 < i < len(parts) - 1:
            out.append(lower)
            continue
        out.append(_smart_title(token))
    return " ".join(out)


def _smart_title(tok: str) -> str:
    """Title-case a token while preserving punctuation and intra-word case for hyphens."""
    if not tok:
        return tok
    # Handle hyphens/slashes by recursing on parts.
    for sep in ("-", "/"):
        if sep in tok:
            return sep.join(_smart_title(p) for p in tok.split(sep))
    # Leading punctuation (e.g. "(roasted") — keep, capitalize letter after.
    m = re.match(r"^([^\w]*)(.*?)([^\w]*)$", tok)
    if not m:
        return tok.capitalize()
    pre, core, post = m.groups()
    if not core:
        return tok
    return pre + core[0].upper() + core[1:].lower() + post


def clean_station(s: str | None) -> str | None:
    return title_case_name(s)


def clean_food_name(s: str | None) -> str | None:
    return title_case_name(s)


def clean_serving_size(s: str | None) -> str | None:
    """e.g. '1 EACH' -> '1 ea', '6 oz' -> '6 oz', '1ea' -> '1 ea'."""
    if s is None:
        return None
    raw = collapse_ws(s)
    if not raw:
        return None
    # Inject a space between number and letters: "1ea" -> "1 ea"
    spaced = re.sub(r"(\d)([a-zA-Z])", r"\1 \2", raw)
    m = _SERVING_RE.match(spaced)
    if not m:
        return raw.lower()
    qty, unit = m.group(1), m.group(2).lower().strip()
    unit_norm = _SERVING_UNIT_MAP.get(unit, unit)
    return f"{qty} {unit_norm}".strip() if unit_norm else qty


def clean_ingredients(s: str | None) -> str | None:
    """Collapse whitespace; normalize 'Contains:' capitalization; strip junk."""
    if s is None:
        return None
    out = _WS_RE.sub(" ", s).strip()
    if not out:
        return None
    # Normalize "contains:" / "CONTAINS:" -> "Contains:"
    out = re.sub(r"\b[Cc][Oo][Nn][Tt][Aa][Ii][Nn][Ss]\s*:", "Contains:", out)
    # Trim space before punctuation
    out = re.sub(r"\s+([,.;:)])", r"\1", out)
    out = re.sub(r"\(\s+", "(", out)
    return out
