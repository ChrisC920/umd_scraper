from __future__ import annotations

import os
from dataclasses import asdict
from datetime import date, datetime, timezone

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


def upsert_food_stub(sb: Client, item: MenuItem) -> int:
    row = {"rec_num": item.rec_num, "portion": item.portion, "name": item.name}
    res = (
        sb.table("foods")
        .upsert(row, on_conflict="rec_num,portion", ignore_duplicates=False)
        .execute()
    )
    food_id = res.data[0]["id"] if res.data else None
    if food_id is None:
        sel = (
            sb.table("foods")
            .select("id")
            .eq("rec_num", item.rec_num)
            .eq("portion", item.portion)
            .single()
            .execute()
        )
        food_id = sel.data["id"]
    _replace_tags(sb, food_id, item.allergens, item.tags)
    return int(food_id)


def needs_label_refresh(sb: Client, food_id: int) -> bool:
    res = (
        sb.table("foods")
        .select("label_scraped_at,label_missing")
        .eq("id", food_id)
        .single()
        .execute()
    )
    data = res.data or {}
    scraped = data.get("label_scraped_at")
    if scraped is None:
        return True
    last = datetime.fromisoformat(scraped.replace("Z", "+00:00"))
    return (datetime.now(timezone.utc) - last).days >= LABEL_REFRESH_DAYS


def upsert_food_full(sb: Client, food_id: int, nut: FoodNutrition) -> None:
    cols = asdict(nut)
    allergens = cols.pop("allergens")
    is_empty = cols.pop("is_empty")
    cols.pop("name", None)  # keep menu name
    update = {k: v for k, v in cols.items() if v is not None}
    update["label_scraped_at"] = _now_iso()
    update["label_missing"] = bool(is_empty)
    sb.table("foods").update(update).eq("id", food_id).execute()
    if allergens:
        sb.table("food_allergens").upsert(
            [{"food_id": food_id, "allergen": a} for a in allergens],
            on_conflict="food_id,allergen",
        ).execute()


def _replace_tags(sb: Client, food_id: int, allergens: list[str], tags: list[str]) -> None:
    if allergens:
        sb.table("food_allergens").upsert(
            [{"food_id": food_id, "allergen": a} for a in allergens],
            on_conflict="food_id,allergen",
        ).execute()
    if tags:
        sb.table("food_dietary_tags").upsert(
            [{"food_id": food_id, "tag": t} for t in tags],
            on_conflict="food_id,tag",
        ).execute()


def upsert_offering(
    sb: Client,
    food_id: int,
    hall_id: int,
    served_date: date,
    meal: str,
    station: str | None,
) -> None:
    sb.table("menu_offerings").upsert(
        {
            "food_id": food_id,
            "hall_id": hall_id,
            "served_date": served_date.isoformat(),
            "meal": meal,
            "station": station,
        },
        on_conflict="food_id,hall_id,served_date,meal",
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
