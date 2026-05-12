from __future__ import annotations

import os
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone

from supabase import Client, create_client

from .parse_label import FoodNutrition
from .parse_menu import MenuItem

LABEL_REFRESH_DAYS = 30


def get_client() -> Client:
    url = os.environ["SUPABASE_URL"]
    key = os.environ["SUPABASE_SERVICE_KEY"]
    return create_client(url, key)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_foods_batch(sb: Client, items: list[MenuItem]) -> dict[tuple[int, int], int]:
    """Upsert food stubs + tag rows in batches. Returns {(rec_num, portion): food_id}."""
    if not items:
        return {}

    # Dedupe by (rec_num, portion) — same food may appear in multiple stations
    by_key: dict[tuple[int, int], MenuItem] = {}
    for it in items:
        by_key[(it.rec_num, it.portion)] = it
    uniq = list(by_key.values())

    rows = [{"rec_num": it.rec_num, "portion": it.portion, "name": it.name} for it in uniq]
    sb.table("foods").upsert(rows, on_conflict="rec_num,portion").execute()

    # Fetch ids in one call (.in_ filters by single column, so use .or_ for composite)
    # Simpler: fetch all rec_nums, filter client-side by (rec_num, portion).
    rec_nums = list({it.rec_num for it in uniq})
    res = sb.table("foods").select("id,rec_num,portion").in_("rec_num", rec_nums).execute()
    id_map: dict[tuple[int, int], int] = {
        (r["rec_num"], r["portion"]): r["id"] for r in (res.data or [])
    }

    # Batch tag upserts
    allergen_rows = []
    tag_rows = []
    for it in uniq:
        food_id = id_map.get((it.rec_num, it.portion))
        if food_id is None:
            continue
        for a in it.allergens:
            allergen_rows.append({"food_id": food_id, "allergen": a})
        for t in it.tags:
            tag_rows.append({"food_id": food_id, "tag": t})
    if allergen_rows:
        sb.table("food_allergens").upsert(allergen_rows, on_conflict="food_id,allergen").execute()
    if tag_rows:
        sb.table("food_dietary_tags").upsert(tag_rows, on_conflict="food_id,tag").execute()

    return id_map


def stale_food_ids(sb: Client, food_ids: list[int]) -> set[int]:
    """Return ids whose label_scraped_at is null or older than LABEL_REFRESH_DAYS."""
    if not food_ids:
        return set()
    cutoff = (datetime.now(timezone.utc) - timedelta(days=LABEL_REFRESH_DAYS)).isoformat()
    res = (
        sb.table("foods")
        .select("id,label_scraped_at")
        .in_("id", food_ids)
        .execute()
    )
    stale: set[int] = set()
    for r in res.data or []:
        ts = r.get("label_scraped_at")
        if ts is None or ts < cutoff:
            stale.add(r["id"])
    return stale


def upsert_nutrition_batch(
    sb: Client,
    nutrition_by_id: dict[int, FoodNutrition],
) -> None:
    """Bulk-update nutrition cols + bulk-insert allergen rows from label data."""
    if not nutrition_by_id:
        return

    rows = []
    allergen_rows = []
    now = _now_iso()
    for food_id, nut in nutrition_by_id.items():
        cols = asdict(nut)
        allergens = cols.pop("allergens")
        is_empty = cols.pop("is_empty")
        cols.pop("name", None)
        update = {k: v for k, v in cols.items() if v is not None}
        update["id"] = food_id
        update["label_scraped_at"] = now
        update["label_missing"] = bool(is_empty)
        rows.append(update)
        for a in allergens:
            allergen_rows.append({"food_id": food_id, "allergen": a})

    # Upsert on PK to update existing rows in bulk.
    # Need rec_num+portion+name to satisfy NOT NULL — fetch them.
    ids = [r["id"] for r in rows]
    existing = sb.table("foods").select("id,rec_num,portion,name").in_("id", ids).execute()
    meta = {r["id"]: r for r in (existing.data or [])}
    for r in rows:
        m = meta.get(r["id"], {})
        r.setdefault("rec_num", m.get("rec_num"))
        r.setdefault("portion", m.get("portion"))
        r.setdefault("name", m.get("name"))
    sb.table("foods").upsert(rows, on_conflict="id").execute()

    if allergen_rows:
        sb.table("food_allergens").upsert(
            allergen_rows, on_conflict="food_id,allergen"
        ).execute()


def upsert_offerings_batch(
    sb: Client,
    items: list[tuple[int, int, date, str, str | None]],
) -> None:
    """items: list of (food_id, hall_id, served_date, meal, station)."""
    if not items:
        return
    rows = [
        {
            "food_id": f,
            "hall_id": h,
            "served_date": d.isoformat(),
            "meal": m,
            "station": s,
        }
        for (f, h, d, m, s) in items
    ]
    sb.table("menu_offerings").upsert(
        rows, on_conflict="food_id,hall_id,served_date,meal"
    ).execute()


def log_run(
    sb: Client,
    *,
    started_at: datetime,
    hall_id: int,
    served_date: date,
    meal: str,
    status: str,
    items_found: int = 0,
    error_message: str | None = None,
) -> None:
    sb.table("scrape_runs").insert(
        {
            "started_at": started_at.isoformat(),
            "finished_at": _now_iso(),
            "hall_id": hall_id,
            "served_date": served_date.isoformat(),
            "meal": meal,
            "status": status,
            "items_found": items_found,
            "error_message": error_message,
        }
    ).execute()
