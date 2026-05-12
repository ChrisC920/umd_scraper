# UMD Nutrition Scraper

ETL pipeline that scrapes [nutrition.umd.edu](http://nutrition.umd.edu) menus + nutrition labels for all three UMD dining halls (South Campus, Yahentamitsi, 251 North) and loads into Supabase Postgres. Runs daily via GitHub Actions cron.

## Schema

- `dining_halls` — seeded (16, 19, 51)
- `foods` — one row per (rec_num, portion); full nutrition + ingredients
- `food_allergens` / `food_dietary_tags` — many-to-many filters
- `menu_offerings` — fact table: food × hall × date × meal × station
- `scrape_runs` — observability (closed/empty/error tracked)

Indexes support fast filtering on allergens, dietary tags, hall, date, meal, calorie/macro ranges, and trigram + full-text search on names.

## Edge cases handled

- Closed halls / empty meals → `scrape_runs.status = 'closed'`
- Weekend brunch days → `meals_for(date)` returns `['Brunch','Dinner']`
- Missing label pages → `foods.label_missing = true`, nutrition cols NULL
- HTTP failures → tenacity retries; persistent errors logged to `scrape_runs`
- Label refresh throttled to once per 30 days per food

## Run

```bash
pip install -r requirements-dev.txt
pytest -q

# dry run (no DB writes)
python -m scraper.main --dry-run

# real run
SUPABASE_URL=... SUPABASE_SERVICE_KEY=... python -m scraper.main
```

## Deploy

- Supabase migration in `supabase/migrations/`. Push with `supabase db push`.
- GH Actions workflow `.github/workflows/scrape.yml` runs daily at 09:00 UTC.
- Required secrets: `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`.
