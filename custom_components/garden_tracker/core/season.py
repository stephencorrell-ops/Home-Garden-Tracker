"""Which crops have time to grow before the first frost, and how many short crops fit one after another.

Pure Python. Frost dates are month-day strings ("04-25"), as the garden keeps them. The numbers are starter values taken
from common seed-packet and extension rules of thumb (days from planting or transplanting to harvest, and how much frost a
crop takes); they are a guide for planning and not a promise."""
from __future__ import annotations

from datetime import date, timedelta

# How a crop copes with frost decides when it can go out and how late it can still finish.
#   tender: killed by frost, so it goes out after the last frost and has to finish before the first
#   half:   takes a light frost, so it can go out two weeks early and finishes about at the first frost
#   hardy:  takes a hard frost, goes out four weeks early and keeps growing a bit past the first frost
START = {"tender": 7, "half": -14, "hardy": -28}   # days from the last spring frost to the first planting
END = {"tender": 0, "half": 0, "hardy": 10}        # days from the first fall frost to the last day the crop can still finish
FALL_PLANT = (-14, 35)                             # garlic: plant from 2 weeks before to 5 weeks after the first fall frost
TIGHT_DAYS = 14                                    # less spare time than this is called tight
SHORT_CROP_DAYS = 90                               # crops this quick can be run one after another in the same bed

# crop key -> (days to harvest, hardiness). "fall" crops are planted in autumn and harvested the next summer.
CROPS: dict[str, tuple[int, str]] = {
    "radish": (25, "hardy"), "spinach": (40, "hardy"), "lettuce": (45, "hardy"), "pea": (60, "hardy"), "beet": (55, "hardy"),
    "carrot": (70, "hardy"), "kale": (55, "hardy"), "broccoli": (65, "hardy"), "cabbage": (75, "hardy"), "cauliflower": (70, "half"),
    "onion": (110, "hardy"), "onion_red": (110, "hardy"), "onion_white": (100, "hardy"), "onion_sweet": (110, "hardy"),
    "potato": (90, "half"), "bean": (55, "tender"), "zucchini": (50, "tender"), "cucumber": (55, "tender"),
    "tomato": (75, "tender"), "pepper": (75, "tender"), "jalapeno": (75, "tender"), "habanero": (90, "tender"),
    "corn": (80, "tender"), "cantaloupe": (80, "tender"), "watermelon": (85, "tender"), "pumpkin": (100, "tender"),
    "garlic": (240, "fall"),
    "eggplant": (80, "tender"), "sunflower": (85, "tender"), "basil": (60, "tender"), "cilantro": (45, "half"), "dill": (60, "half"),
    "parsley": (75, "hardy"),
}  # perennials (hops, mint, chives, oregano, thyme, rosemary, sage) have no season to fit; give one a time yourself if you want it listed
HARDY_NAMES = {"tender": "Tender: killed by frost", "half": "Half-hardy: takes a light frost", "hardy": "Hardy: takes a hard frost",
               "fall": "Planted in fall, harvested next year"}


def _md(md: str, year: int) -> date:
    m, d = (int(x) for x in md.split("-"))
    try:
        return date(year, m, d)
    except ValueError:
        return date(year, m, 28)


def window(key: str, last_md: str, first_md: str, year: int, spec: tuple[int, str] | None = None) -> tuple[date, date] | None:
    """The first and last day this crop can be planted in `year`, or None if there is no time for the crop."""
    spec = spec or CROPS.get(key)
    if not spec:
        return None
    days, hardy = spec
    first = _md(first_md, year)
    if hardy == "fall":
        return first + timedelta(days=FALL_PLANT[0]), first + timedelta(days=FALL_PLANT[1])
    start = _md(last_md, year) + timedelta(days=START[hardy])
    end = first + timedelta(days=END[hardy]) - timedelta(days=days)
    return start, end


def analyse(names: dict[str, str], last_md: str, first_md: str, today: date, planted: set[str] | None = None,
            edits: dict[str, dict] | None = None) -> dict:
    last_d, first_d = _md(last_md, today.year), _md(first_md, today.year)
    rows = []
    edits, untimed = edits or {}, []
    for key, name in names.items():
        e = edits.get(key)
        spec = (int(e["days"]), e["hardy"]) if e else CROPS.get(key)
        if not spec:
            untimed.append({"key": key, "name": name})
            continue
        days, hardy = spec
        w = window(key, last_md, first_md, today.year, spec)
        closed = w[1] < today  # this year's window has closed, so the dates shown are next year's
        if closed:
            w = window(key, last_md, first_md, today.year + 1, spec)
        start, end = w
        if hardy == "fall":
            season_days = (end - start).days
            spare = season_days
        else:
            season_days = (_md(first_md, start.year) + timedelta(days=END[hardy]) - (_md(last_md, start.year) + timedelta(days=START[hardy]))).days
            spare = season_days - days
        opens, left, waits = start <= today <= end, (end - today).days, (start - today).days
        if hardy != "fall" and spare < 0:
            status, text = "short", f"Needs {days} days and the season gives {season_days}"
        elif opens:
            status = "tight" if left < TIGHT_DAYS else "plant"
            text = f"Plant now, last day {end.strftime('%b')} {end.day}" if hardy != "fall" else f"Plant now through {end.strftime('%b')} {end.day}"
        elif closed:
            status, text = "late", f"Too late this year, opens {start.strftime('%b')} {start.day}"
        else:
            status, text = "wait", f"Opens {start.strftime('%b')} {start.day}"
        rows.append({"key": key, "name": name, "days": days, "hardy": hardy, "from": start.isoformat(), "by": end.isoformat(),
                     "status": status, "text": text, "open": opens, "left": left if opens else None, "wait": waits if waits > 0 else None,
                     "spare": spare, "season_days": season_days, "fall": hardy == "fall", "edited": bool(e), "usual_days": CROPS[key][0] if key in CROPS else None,
                     "usual_hardy": CROPS[key][1] if key in CROPS else None,
                     "rounds": (season_days // days if days <= SHORT_CROP_DAYS and hardy != "fall" and season_days >= days else 1),
                     "planted": bool(planted and key in planted)})
    order = {"plant": 0, "tight": 1, "wait": 2, "late": 3, "short": 4}
    rows.sort(key=lambda r: (order[r["status"]], r["days"], r["name"]))
    to_frost = (first_d - today).days
    return {"last_frost": last_d.isoformat(), "first_frost": first_d.isoformat(), "days_to_frost": to_frost,
            "season_days": (first_d - last_d).days, "crops": rows, "untimed": sorted(untimed, key=lambda x: x["name"]), "hardiness": HARDY_NAMES,
            "now": sum(1 for r in rows if r["status"] in ("plant", "tight"))}
