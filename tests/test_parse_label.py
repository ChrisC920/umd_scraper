from pathlib import Path

from scraper.parse_label import parse_label

FIXTURE = Path(__file__).parent.parent / "french_toast_sample.html"


def test_french_toast_label():
    html = FIXTURE.read_text(encoding="utf-8", errors="ignore")
    nut = parse_label(html)
    assert nut.name == "French Toast"
    assert nut.calories == 251.0
    assert nut.total_fat_g == 10.5
    assert nut.sat_fat_g == 4.1
    assert nut.trans_fat_g == 0.0
    assert nut.cholesterol_mg == 248.6
    assert nut.sodium_mg == 307.7
    assert nut.total_carbs_g == 26.0
    assert nut.fiber_g == 2.0
    assert nut.sugars_g == 6.8
    assert nut.added_sugars_g == 0.0
    assert nut.protein_g == 10.9
    assert nut.iron_mg == 2.2
    assert nut.calcium_mg == 130.1
    assert nut.serving_size == "1 ea"
    assert nut.ingredients and "Liquid Eggs" in nut.ingredients
    assert sorted(nut.allergens) == ["dairy", "eggs", "gluten", "soy"]
    assert not nut.is_empty


def test_empty_label_handled():
    nut = parse_label("<html><body><h2>Mystery Food</h2></body></html>")
    assert nut.is_empty
    assert nut.name == "Mystery Food"
    assert nut.calories is None
