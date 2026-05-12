from scraper.client import is_maintenance


MAINTENANCE_HTML = """
<html><body>
  <h1>We'll be back!</h1>
  <p>Sorry for the inconvenience. We're performing some maintenance.
  We anticipate restoring the nutrition site by Fall 2026.</p>
</body></html>
"""

LIVE_HTML = """
<html><body>
  <select id="location-select-menu" name="locationNum">
    <option value="16">South Campus</option>
  </select>
  <a id="longmenu-link" href="longmenu.aspx">Plan Your Meal</a>
</body></html>
"""


def test_detect_maintenance():
    assert is_maintenance(MAINTENANCE_HTML) is True


def test_detect_live():
    assert is_maintenance(LIVE_HTML) is False


def test_live_markers_override_maintenance_text():
    # If both appear (e.g. wayback page that contains old maintenance text), prefer live.
    mixed = MAINTENANCE_HTML + LIVE_HTML
    assert is_maintenance(mixed) is False
