from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import parse_qs, urlparse

from bs4 import BeautifulSoup

from .extract import icon_filename_to_tags
from .normalize import clean_food_name, clean_station

REC_RE = re.compile(r"RecNumAndPort=(\d+)\*(\d+)")


@dataclass
class MenuItem:
    rec_num: int
    portion: int
    name: str
    station: str | None = None
    allergens: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)


def _parse_rec_href(href: str) -> tuple[int, int] | None:
    m = REC_RE.search(href)
    if m:
        return int(m.group(1)), int(m.group(2))
    qs = parse_qs(urlparse(href).query)
    rp = qs.get("RecNumAndPort", [None])[0]
    if rp and "*" in rp:
        a, b = rp.split("*", 1)
        return int(a), int(b)
    return None


def parse_menu(html: str) -> list[MenuItem]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[MenuItem] = []

    rows = soup.select("div.menu-item-row")
    if rows:
        # main-page format: stations as h5.card-title preceding rows
        current_station: str | None = None
        for el in soup.find_all(["h5", "div"]):
            if el.name == "h5" and "card-title" in (el.get("class") or []):
                current_station = el.get_text(strip=True)
            elif el.name == "div" and "menu-item-row" in (el.get("class") or []):
                item = _row_to_item(el, current_station)
                if item:
                    items.append(item)
        return items

    # longmenu.aspx format: table#long-menu-table with station header rows
    # (<td><p><strong>Station</strong></p></td>) interleaved with item rows.
    table = soup.select_one("table#long-menu-table")
    if table:
        current_station: str | None = None
        for tr in table.select("tbody > tr"):
            station_strong = tr.select_one("td > p > strong")
            link = tr.select_one("a[href*='label.aspx']")
            if station_strong and not link:
                raw_station = station_strong.get_text(strip=True)
                if raw_station:
                    current_station = clean_station(raw_station)
                continue
            if not link:
                continue
            rp = _parse_rec_href(link.get("href", ""))
            if not rp:
                continue
            name = clean_food_name(link.get_text(strip=True))
            if not name:
                continue
            allergens, tags = _collect_icons_in(tr)
            items.append(
                MenuItem(
                    rec_num=rp[0],
                    portion=rp[1],
                    name=name,
                    station=current_station,
                    allergens=allergens,
                    tags=tags,
                )
            )
        return items

    # generic fallback
    for a in soup.select("a[href*='label.aspx']"):
        rp = _parse_rec_href(a.get("href", ""))
        if not rp:
            continue
        name = clean_food_name(a.get_text(strip=True))
        if not name:
            continue
        station = clean_station(_nearest_station_heading(a))
        allergens, tags = _collect_icons_near(a)
        items.append(
            MenuItem(
                rec_num=rp[0],
                portion=rp[1],
                name=name,
                station=station,
                allergens=allergens,
                tags=tags,
            )
        )
    return items


def _collect_icons_in(node) -> tuple[list[str], list[str]]:
    allergens: list[str] = []
    tags: list[str] = []
    for img in node.select("img"):
        src = img.get("src") or ""
        a, t = icon_filename_to_tags(src.rsplit("/", 1)[-1])
        if a and a not in allergens:
            allergens.append(a)
        if t and t not in tags:
            tags.append(t)
    return allergens, tags


def _row_to_item(row, station: str | None) -> MenuItem | None:
    a = row.select_one("a.menu-item-name") or row.select_one("a[href*='label.aspx']")
    if not a:
        return None
    rp = _parse_rec_href(a.get("href", ""))
    if not rp:
        return None
    name = a.get_text(strip=True)
    allergens: list[str] = []
    tags: list[str] = []
    for img in row.select("img.nutri-icon, img"):
        src = img.get("src") or ""
        allergen, tag = icon_filename_to_tags(src.rsplit("/", 1)[-1])
        if allergen and allergen not in allergens:
            allergens.append(allergen)
        if tag and tag not in tags:
            tags.append(tag)
    return MenuItem(
        rec_num=rp[0],
        portion=rp[1],
        name=name,
        station=station,
        allergens=allergens,
        tags=tags,
    )


def _nearest_station_heading(node) -> str | None:
    for prev in node.find_all_previous(["h3", "h4", "h5"]):
        text = prev.get_text(strip=True)
        if text:
            return text
    return None


def _collect_icons_near(anchor) -> tuple[list[str], list[str]]:
    allergens: list[str] = []
    tags: list[str] = []
    parent = anchor.find_parent(["div", "tr", "li"]) or anchor.parent
    if not parent:
        return allergens, tags
    for img in parent.select("img"):
        src = img.get("src") or ""
        a, t = icon_filename_to_tags(src.rsplit("/", 1)[-1])
        if a and a not in allergens:
            allergens.append(a)
        if t and t not in tags:
            tags.append(t)
    return allergens, tags
