from pathlib import Path

from scraper.parse_menu import parse_menu

FIXTURE = Path(__file__).parent.parent / "nutrition_site.html"


def test_parses_some_items():
    html = FIXTURE.read_text(encoding="utf-8", errors="ignore")
    items = parse_menu(html)
    assert len(items) > 0, "expected at least one menu item"


def test_french_toast_present():
    html = FIXTURE.read_text(encoding="utf-8", errors="ignore")
    items = parse_menu(html)
    ft = [i for i in items if i.rec_num == 119370]
    assert ft, "French Toast (119370*1) should appear in fixture"
    assert ft[0].name.lower().startswith("french toast")


def test_items_have_stations():
    html = FIXTURE.read_text(encoding="utf-8", errors="ignore")
    items = parse_menu(html)
    with_station = [i for i in items if i.station]
    assert len(with_station) > 0, "at least some items should have a station"


def test_allergen_icons_extracted():
    html = FIXTURE.read_text(encoding="utf-8", errors="ignore")
    items = parse_menu(html)
    any_allergens = any(i.allergens for i in items)
    assert any_allergens, "at least one item should have allergen icons"
