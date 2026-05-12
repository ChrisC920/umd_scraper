from __future__ import annotations

import argparse
import logging
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import date, datetime, timedelta, timezone

from .client import Client, SnapshotMissing
from .load import (
    get_client,
    log_run,
    stale_food_ids,
    upsert_foods_batch,
    upsert_nutrition_batch,
    upsert_offerings_batch,
)
from .parse_label import FoodNutrition, parse_label
from .parse_menu import parse_menu

HALLS = [16, 19, 51]

log = logging.getLogger("scraper")


def meals_for(d: date) -> list[str]:
    if d.weekday() in (5, 6):
        return ["Brunch", "Dinner"]
    return ["Breakfast", "Lunch", "Dinner"]


def meal_to_db(meal: str) -> str:
    return meal.lower()


def fmt_date(d: date) -> str:
    return f"{d.month}/{d.day}/{d.year}"


def _fetch_label(http: Client, rec_num: int, portion: int) -> FoodNutrition | None:
    try:
        html = http.label(rec_num, portion)
        return parse_label(html)
    except SnapshotMissing:
        # Wayback has no snapshot — mark missing so we don't keep retrying.
        log.info("snapshot missing rec=%s portion=%s", rec_num, portion)
        n = FoodNutrition()
        n.is_empty = True
        return n
    except Exception:
        log.exception("label fetch failed rec=%s portion=%s", rec_num, portion)
        return None


def run(
    days_ahead: int = 2,
    dry_run: bool = False,
    start_date: date | None = None,
    min_interval: float = 0.5,
    label_workers: int = 4,
    skip_labels: bool = False,
) -> int:
    http = Client(min_interval=min_interval)
    sb = None if dry_run else get_client()
    base_date = start_date or date.today()
    errors = 0

    for offset in range(days_ahead):
        served = base_date + timedelta(days=offset)
        for hall in HALLS:
            for meal in meals_for(served):
                started = datetime.now(timezone.utc)
                try:
                    html = http.longmenu(hall, fmt_date(served), meal)
                    items = parse_menu(html)
                except Exception as e:
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
                        log.info(
                            "  %s [%s] allergens=%s tags=%s",
                            it.name,
                            it.station,
                            it.allergens,
                            it.tags,
                        )
                    continue

                try:
                    # 1. Batch-upsert foods + tags, get id map
                    id_map = upsert_foods_batch(sb, items)

                    # 2. Find which need label refresh (skip if requested)
                    if skip_labels:
                        stale_items = []
                    else:
                        food_ids = list(id_map.values())
                        stale = stale_food_ids(sb, food_ids)
                        stale_items = [
                            it for it in items
                            if id_map.get((it.rec_num, it.portion)) in stale
                        ]
                    # Dedupe stale items by (rec_num, portion)
                    seen: set[tuple[int, int]] = set()
                    stale_items = [
                        it for it in stale_items
                        if (it.rec_num, it.portion) not in seen
                        and not seen.add((it.rec_num, it.portion))
                    ]

                    # 3. Parallel label fetches (HTTP-bound)
                    nutrition_by_id: dict[int, FoodNutrition] = {}
                    if stale_items:
                        log.info("  fetching %d labels (parallel=%d)", len(stale_items), label_workers)
                        with ThreadPoolExecutor(max_workers=label_workers) as ex:
                            futs = {
                                ex.submit(_fetch_label, http, it.rec_num, it.portion): it
                                for it in stale_items
                            }
                            for fut in as_completed(futs):
                                it = futs[fut]
                                nut = fut.result()
                                if nut is not None:
                                    fid = id_map[(it.rec_num, it.portion)]
                                    nutrition_by_id[fid] = nut

                    # 4. Bulk update nutrition
                    upsert_nutrition_batch(sb, nutrition_by_id)

                    # 5. Bulk insert offerings
                    offerings = [
                        (
                            id_map[(it.rec_num, it.portion)],
                            hall,
                            served,
                            meal_to_db(meal),
                            it.station,
                        )
                        for it in items
                        if (it.rec_num, it.portion) in id_map
                    ]
                    upsert_offerings_batch(sb, offerings)

                    log_run(
                        sb,
                        started_at=started,
                        hall_id=hall,
                        served_date=served,
                        meal=meal_to_db(meal),
                        status="ok",
                        items_found=len(items),
                    )
                except Exception as e:
                    log.exception("batch load failed hall=%s date=%s meal=%s", hall, served, meal)
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

    return 1 if errors else 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="umd-nutrition-scraper")
    p.add_argument("--days-ahead", type=int, default=2)
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--start-date", help="ISO date YYYY-MM-DD; default = today")
    p.add_argument("--min-interval", type=float, default=0.5, help="Seconds between requests")
    p.add_argument("--label-workers", type=int, default=4, help="Parallel label fetches")
    p.add_argument("--skip-labels", action="store_true", help="Skip label.aspx fetches (useful for Wayback)")
    p.add_argument("--log-level", default="INFO")
    args = p.parse_args(argv)
    logging.basicConfig(
        level=args.log_level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    sd = date.fromisoformat(args.start_date) if args.start_date else None
    return run(
        days_ahead=args.days_ahead,
        dry_run=args.dry_run,
        start_date=sd,
        min_interval=args.min_interval,
        label_workers=args.label_workers,
        skip_labels=args.skip_labels,
    )


if __name__ == "__main__":
    sys.exit(main())
