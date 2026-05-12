"""One-shot: re-normalize existing foods + menu_offerings rows in Supabase."""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from scraper.load import get_client  # noqa: E402
from scraper.normalize import (  # noqa: E402
    clean_food_name,
    clean_ingredients,
    clean_serving_size,
    clean_station,
    collapse_ws,
)

PAGE = 1000


def backfill_foods(sb) -> int:
    n = 0
    offset = 0
    while True:
        res = (
            sb.table("foods")
            .select("id,name,serving_size,servings_per,ingredients")
            .range(offset, offset + PAGE - 1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            break
        updates = []
        for r in rows:
            new = {
                "id": r["id"],
                "name": clean_food_name(r.get("name")),
                "serving_size": clean_serving_size(r.get("serving_size")),
                "servings_per": collapse_ws(r.get("servings_per")),
                "ingredients": clean_ingredients(r.get("ingredients")),
            }
            if any(new[k] != r.get(k) for k in ("name", "serving_size", "servings_per", "ingredients")):
                updates.append(new)
        for u in updates:
            fid = u.pop("id")
            sb.table("foods").update(u).eq("id", fid).execute()
            n += 1
        if len(rows) < PAGE:
            break
        offset += PAGE
    return n


def backfill_offerings(sb) -> int:
    n = 0
    offset = 0
    while True:
        res = (
            sb.table("menu_offerings")
            .select("id,station")
            .range(offset, offset + PAGE - 1)
            .execute()
        )
        rows = res.data or []
        if not rows:
            break
        for r in rows:
            new_station = clean_station(r.get("station"))
            if new_station != r.get("station"):
                sb.table("menu_offerings").update({"station": new_station}).eq("id", r["id"]).execute()
                n += 1
        if len(rows) < PAGE:
            break
        offset += PAGE
    return n


def main() -> int:
    sb = get_client()
    f = backfill_foods(sb)
    o = backfill_offerings(sb)
    print(f"foods updated: {f}")
    print(f"menu_offerings updated: {o}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
