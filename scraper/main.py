from __future__ import annotations

import argparse
import logging
import sys
from datetime import date, datetime, timedelta, timezone

from .client import Client
from .load import (
    get_client,
    log_run,
    needs_label_refresh,
    upsert_food_full,
    upsert_food_stub,
    upsert_offering,
)
from .parse_label import parse_label
from .parse_menu import parse_menu

HALLS = [16, 19, 51]

log = logging.getLogger("scraper")


def meals_for(d: date) -> list[str]:
    # Sat=5, Sun=6 → brunch + dinner (matches site JS).
    if d.weekday() in (5, 6):
        return ["Brunch", "Dinner"]
    return ["Breakfast", "Lunch", "Dinner"]


def meal_to_db(meal: str) -> str:
    return meal.lower()


def fmt_date(d: date) -> str:
    return f"{d.month}/{d.day}/{d.year}"


def run(days_ahead: int = 2, dry_run: bool = False) -> int:
    http = Client()
    sb = None if dry_run else get_client()
    today = date.today()
    errors = 0

    for offset in range(days_ahead):
        served = today + timedelta(days=offset)
        for hall in HALLS:
            for meal in meals_for(served):
                started = datetime.now(timezone.utc)
                try:
                    html = http.longmenu(hall, fmt_date(served), meal)
                    items = parse_menu(html)
                except Exception as e:  # network / parse failure
                    log.exception("fetch failed hall=%s date=%s meal=%s", hall, served, meal)
                    if sb:
                        log_run(
                            sb,
                            started_at=started,
                            hall_id=hall,
                            served_date=served,
                            meal=meal_to_db(meal),
                            status="error",
                            error_message=str(e)[:500],
                        )
                    errors += 1
                    continue

                if not items:
                    log.info("closed/empty hall=%s date=%s meal=%s", hall, served, meal)
                    if sb:
                        log_run(
                            sb,
                            started_at=started,
                            hall_id=hall,
                            served_date=served,
                            meal=meal_to_db(meal),
                            status="closed",
                        )
                    continue

                log.info("hall=%s date=%s meal=%s items=%d", hall, served, meal, len(items))
                if dry_run:
                    for it in items[:5]:
                        log.info("  %s [%s] allergens=%s tags=%s", it.name, it.station, it.allergens, it.tags)
                    continue

                for item in items:
                    try:
                        food_id = upsert_food_stub(sb, item)
                        if needs_label_refresh(sb, food_id):
                            try:
                                lh = http.label(item.rec_num, item.portion)
                                nut = parse_label(lh)
                            except Exception:
                                log.exception("label fetch failed rec=%s", item.rec_num)
                                nut = None
                            if nut is not None:
                                upsert_food_full(sb, food_id, nut)
                        upsert_offering(sb, food_id, hall, served, meal_to_db(meal), item.station)
                    except Exception:
                        log.exception("upsert failed item=%s", item.name)
                        errors += 1

                log_run(
                    sb,
                    started_at=started,
                    hall_id=hall,
                    served_date=served,
                    meal=meal_to_db(meal),
                    status="ok",
                    items_found=len(items),
                )

    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="umd-nutrition-scraper")
    p.add_argument("--days-ahead", type=int, default=2)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args(argv)
    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    return run(days_ahead=args.days_ahead, dry_run=args.dry_run)


if __name__ == "__main__":
    sys.exit(main())
