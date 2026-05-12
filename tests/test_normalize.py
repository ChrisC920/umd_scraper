from scraper.normalize import (
    clean_food_name,
    clean_ingredients,
    clean_serving_size,
    clean_station,
    collapse_ws,
)


def test_collapse_ws():
    assert collapse_ws("  hello   world  ") == "hello world"
    assert collapse_ws("") is None
    assert collapse_ws(None) is None


def test_food_name_title_case():
    assert clean_food_name("french toast") == "French Toast"
    assert clean_food_name("FRENCH TOAST") == "French Toast"
    assert clean_food_name("Cajun Roasted Breakfast Potatoes w/ Peppers & Onions") == \
        "Cajun Roasted Breakfast Potatoes w/ Peppers & Onions"
    # Connectors stay lowercase mid-string, capitalized at start.
    assert clean_food_name("MAC AND CHEESE") == "Mac and Cheese"
    assert clean_food_name("THE BIG ONE") == "The Big One"


def test_food_name_keeps_abbrev():
    assert clean_food_name("BBQ chicken") == "BBQ Chicken"


def test_serving_size():
    assert clean_serving_size("1 ea") == "1 ea"
    assert clean_serving_size("1 EACH") == "1 ea"
    assert clean_serving_size("1 each") == "1 ea"
    assert clean_serving_size("6 oz") == "6 oz"
    assert clean_serving_size("1 OUNCE") == "1 oz"
    assert clean_serving_size("1ea") == "1 ea"
    assert clean_serving_size("  4  oz  ") == "4 oz"
    assert clean_serving_size(None) is None


def test_station():
    assert clean_station("Broiler Works") == "Broiler Works"
    assert clean_station("MONGOLIAN GRILL") == "Mongolian Grill"


def test_ingredients_collapse():
    raw = "Liquid Eggs  2/20 lb (Whole Egg, Citric Acid. contains: Eggs.)"
    out = clean_ingredients(raw)
    assert "  " not in out
    assert "Contains:" in out
    assert "contains:" not in out
    assert "( " not in out


def test_ingredients_punctuation_spacing():
    out = clean_ingredients("Foo (a , b , c .)")
    assert out == "Foo (a, b, c.)"
