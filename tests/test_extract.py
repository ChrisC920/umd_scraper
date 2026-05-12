from scraper.extract import icon_filename_to_tags, parse_allergens_text


def test_icon_to_allergen():
    assert icon_filename_to_tags("icons_2016_dairy.gif") == ("dairy", None)
    assert icon_filename_to_tags("icons_2016_egg.gif") == ("eggs", None)
    assert icon_filename_to_tags("icons_2016_Shellfish.png") == ("shellfish", None)


def test_icon_to_tag():
    assert icon_filename_to_tags("icons_2016_vegan.gif") == (None, "vegan")
    assert icon_filename_to_tags("icons_2022_HalalFriendly.gif") == (None, "halal")
    assert icon_filename_to_tags("icons_2016_local.gif") == (None, "local")


def test_allergen_text():
    assert sorted(parse_allergens_text("Milk, Eggs, Wheat, Soybeans")) == ["dairy", "eggs", "gluten", "soy"]
    assert parse_allergens_text("") == []
