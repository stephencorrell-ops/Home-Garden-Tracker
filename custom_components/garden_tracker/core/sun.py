"""The sun over a garden from April to September: which way the rows should run, and which tall crops shade shorter ones.

Pure Python, no Home Assistant. Compass bearings are degrees clockwise from north. A layout is drawn with plan x across
the rows and plan y along them; turning the plan by `rotation` degrees clockwise makes the rows run along a bearing of
`rotation` (0 is north-south, 90 is east-west), the x axis point along 90 + rotation and the y axis along 180 + rotation."""
from __future__ import annotations

import json
import math
from functools import lru_cache

# The 15th of April to September, as days of the year, and the solar hours that are sampled in each.
DAYS = ((105, "April"), (135, "May"), (166, "June"), (196, "July"), (227, "August"), (258, "September"))
HOURS = range(7, 18)
MIN_ALT = 10.0          # a sun lower than this gives little light, so it is left out
REF_DIFF_FT = 4.0       # how much taller the tall crops are than the short ones, used for the best angle when nothing is planted
MIN_TALLER_FT = 1.5     # a crop has to stand this much over another to shade it
WARN_PCT = 10           # report a crop that loses at least this share of its sun
DEFAULT_HEIGHT_FT = 2.0

# Mature height in feet. Starter values, editable for each crop in a garden.
HEIGHTS: dict[str, float] = {
    "corn": 7.0, "hops": 15.0, "sunflower": 8.0, "tomato": 5.0, "pole_bean": 6.0, "pea": 5.0, "cucumber": 5.0, "okra": 5.0, "pepper": 2.5,
    "jalapeno": 2.5, "habanero": 3.0, "eggplant": 3.0, "potato": 2.5, "horseradish": 3.0, "zucchini": 2.5, "squash": 2.5,
    "cauliflower": 2.0, "broccoli": 2.5, "kale": 2.0, "cabbage": 1.5, "bean": 1.5, "garlic": 1.5, "onion": 1.5, "onion_red": 1.5,
    "onion_white": 1.5, "onion_sweet": 1.5, "pumpkin": 1.5, "carrot": 1.0, "beet": 1.0, "watermelon": 1.0, "cantaloupe": 1.0,
    "lettuce": 0.7, "spinach": 0.5, "radish": 0.5, "basil": 2.0, "cilantro": 1.5, "parsley": 1.2, "dill": 3.5, "chives": 1.0, "mint": 1.5,
    "oregano": 1.5, "thyme": 0.7, "rosemary": 3.0, "sage": 2.0,
}


# Growth habits that change how tall a crop gets: (key, name, feet). A variety can pick one or give its own height.
HABITS: dict[str, list[tuple[str, str, float]]] = {
    "tomato": [("determinate", "Determinate (bush)", 3.5), ("indeterminate", "Indeterminate (vining)", 6.0)],
    "bean": [("bush", "Bush", 1.5), ("pole", "Pole or climbing", 7.0)],
    "pea": [("dwarf", "Dwarf", 2.0), ("climbing", "Climbing", 5.5)],
    "cucumber": [("bush", "Bush", 2.0), ("vining", "Vining on a trellis", 5.5)],
    "corn": [("short", "Short, about 4 ft", 4.0), ("standard", "Standard, about 7 ft", 7.0), ("tall", "Tall, 9 ft or more", 9.0)],
    "hops": [("dwarf", "Dwarf, about 10 ft", 10.0), ("standard", "Standard, about 15 ft", 15.0), ("tall", "Tall, about 20 ft", 20.0)],
}


def habits_for(key: str) -> list[dict]:
    return [{"key": k, "name": n, "height": h} for k, n, h in HABITS.get(key, [])]


def height_for(key: str) -> float:
    return HEIGHTS.get(key, DEFAULT_HEIGHT_FT)


def position(lat: float, doy: int, hour: float) -> tuple[float, float]:
    """Altitude and compass bearing of the sun, in degrees, at a solar hour (12 is noon) on a day of the year."""
    phi = math.radians(lat)
    dec = math.radians(23.44 * math.sin(math.radians(360 / 365 * (doy - 81))))
    h = math.radians(15 * (hour - 12))
    sin_alt = math.sin(phi) * math.sin(dec) + math.cos(phi) * math.cos(dec) * math.cos(h)
    alt = math.degrees(math.asin(max(-1.0, min(1.0, sin_alt))))
    east = -math.cos(dec) * math.sin(h)
    north = math.sin(dec) * math.cos(phi) - math.cos(dec) * math.sin(phi) * math.cos(h)
    return alt, math.degrees(math.atan2(east, north)) % 360


def samples(lat: float) -> list[tuple[float, float, float]]:
    """(altitude, bearing, weight) of the sun through April to September. The weight is how much of the light it brings."""
    out = []
    for doy, _ in DAYS:
        for hr in HOURS:
            alt, az = position(lat, doy, hr)
            if alt >= MIN_ALT:
                out.append((alt, az, math.sin(math.radians(alt))))
    return out


def _lost(heading: float, sun: list, height_ft: float, row_in: float, path_in: float) -> tuple[float, float, float]:
    """For rows running along `heading`: the share of the sun that a shorter row loses to a tall row beside it, when it sits
    on one side of the tall row and when it sits on the other, and the compass bearing of the side that gets the most shade."""
    gap, wide = path_in / 12, row_in / 12
    tot = a = b = 0.0
    for alt, az, w in sun:
        s = math.sin(math.radians(az + 180 - heading))
        f = max(0.0, min(1.0, (abs(s) * height_ft / math.tan(math.radians(alt)) - gap) / wide))
        if s > 0:
            a += w * f
        else:
            b += w * f
        tot += w
    if not tot:
        return 0.0, 0.0, heading
    return a / tot, b / tot, (heading + 90) % 360 if a >= b else (heading - 90) % 360


def best_heading(lat: float, height_ft: float, row_in: float, path_in: float, current: float) -> dict:
    """The row direction that costs the least sun, with tall crops on the side the shade falls away from.
    With the tall crops put at that edge only the other side's loss counts, so a heading is scored by the smaller of the two."""
    sun = samples(lat)
    res = {h: _lost(h, sun, height_ft, row_in, path_in) for h in range(0, 180, 5)}
    score = {h: min(r[0], r[1]) for h, r in res.items()}
    best = min(score, key=lambda h: (round(score[h], 2), min(h % 90, 90 - h % 90), h))  # near-ties go to a straight row
    c = _lost(current % 180, sun, height_ft, row_in, path_in)
    return {"best": best, "best_pct": round(100 * score[best]), "current_pct": round(100 * min(c[0], c[1])),
            "worst_pct": round(100 * max(score.values())), "tall_side": round(res[best][2]), "current_side": round(c[2]),
            "scores": {str(h): round(100 * v) for h, v in score.items()}}


def _hit(px: float, py: float, ux: float, uy: float, dmax: float, box: tuple[float, float, float, float]) -> bool:
    """Does the ray from (px, py) along (ux, uy) cross the box within dmax?"""
    xa, xb, ya, yb = box
    lo, hi = 0.0, dmax
    for p, u, a, b in ((px, ux, xa, xb), (py, uy, ya, yb)):
        if abs(u) < 1e-9:
            if not a <= p <= b:
                return False
        else:
            t1, t2 = (a - p) / u, (b - p) / u
            lo, hi = max(lo, min(t1, t2)), min(hi, max(t1, t2))
            if lo > hi:
                return False
    return hi > lo or hi == lo == 0


def shading(segments: list[dict], rotation: float, lat: float) -> list[dict]:
    return json.loads(_shading(json.dumps(segments), rotation, lat))


@lru_cache(maxsize=16)
def _shading(raw: str, rotation: float, lat: float) -> str:
    """Crops that a taller crop shades. Each segment is {crop, name, row, height, box: (x0, x1, y0, y1)} in inches in the plan."""
    segments = json.loads(raw)
    sun = samples(lat)
    xb, yb = 90 + rotation, 180 + rotation
    out: dict[str, dict] = {}
    for s in segments:
        x0, x1, y0, y1 = s["box"]
        taller = []
        for t in segments:
            if t["height"] - s["height"] < MIN_TALLER_FT:
                continue
            reach = (t["height"] - s["height"]) * 12 / math.tan(math.radians(MIN_ALT))  # the longest shadow it can throw
            tx0, tx1, ty0, ty1 = t["box"]
            if max(tx0 - x1, x0 - tx1, 0) ** 2 + max(ty0 - y1, y0 - ty1, 0) ** 2 <= reach ** 2:
                taller.append(t)
        if not taller:
            continue
        ny = max(2, min(8, int((y1 - y0) / 36) + 1))
        pts = [(x0 + (x1 - x0) * fx, y0 + (y1 - y0) * (j + 0.5) / ny) for fx in (0.25, 0.75) for j in range(ny)]
        tot = lost = am = pm = 0.0
        by: dict[str, float] = {}
        for alt, az, w in sun:
            ux, uy = math.cos(math.radians(az - xb)), math.cos(math.radians(az - yb))
            tan = math.tan(math.radians(alt))
            for px, py in pts:
                tot += w
                for t in taller:
                    dmax = (t["height"] - s["height"]) * 12 / tan
                    if _hit(px, py, ux, uy, dmax, t["box"]):
                        lost += w
                        by[t["name"]] = by.get(t["name"], 0.0) + w
                        if az < 180:
                            am += w
                        else:
                            pm += w
                        break
        if not tot:
            continue
        e = out.setdefault(s["name"], {"crop": s["crop"], "name": s["name"], "height": s["height"], "tot": 0.0, "lost": 0.0, "am": 0.0, "pm": 0.0,
                                       "by": {}, "rows": set()})
        e["tot"] += tot * (y1 - y0)
        e["lost"] += lost * (y1 - y0)
        e["am"] += am * (y1 - y0)
        e["pm"] += pm * (y1 - y0)
        e["rows"].add(s["row"])
        for k, v in by.items():
            e["by"][k] = e["by"].get(k, 0.0) + v * (y1 - y0)
    res = []
    for e in out.values():
        pct = round(100 * e["lost"] / e["tot"]) if e["tot"] else 0
        if pct < WARN_PCT:
            continue
        when = "morning" if e["am"] > 1.5 * e["pm"] else "afternoon" if e["pm"] > 1.5 * e["am"] else "morning and afternoon"
        res.append({"crop": e["crop"], "name": e["name"], "height": e["height"], "pct": pct, "when": when,
                    "by": [k for k, _ in sorted(e["by"].items(), key=lambda kv: -kv[1])][:3], "rows": sorted(r + 1 for r in e["rows"])})
    return json.dumps(sorted(res, key=lambda r: -r["pct"]))


def compass(bearing: float) -> str:
    return ["north", "northeast", "east", "southeast", "south", "southwest", "west", "northwest"][int(((bearing % 360) + 22.5) // 45) % 8]


def analyse(layout_rows: list[dict], row_in: float, path_in: float, rotation: float, lat: float | None,
            heights: dict[str, float]) -> dict:
    """Everything the layout page shows about the sun. `layout_rows` are the planned rows (each with `segments`)."""
    used = lat if lat is not None else 40.0
    segs = []
    for r in layout_rows:
        for sg in r["segments"]:
            lines = sg["lines"] or [r["x"]]
            segs.append({"crop": sg["crop"], "name": sg["name"] + (f" ({sg['variety']})" if sg.get("variety") else ""), "row": r["i"],
                         "height": sg.get("height_ft") or heights.get(sg["crop"], height_for(sg["crop"])),
                         "box": (min(lines) - 8, max(lines) + 8, sg["start_in"], sg["start_in"] + sg["len_in"])})
    tall = max(segs, key=lambda s: s["height"]) if segs else None
    short = min(segs, key=lambda s: s["height"]) if segs else None
    diff = (tall["height"] - short["height"]) if segs else REF_DIFF_FT
    even = bool(segs) and diff < MIN_TALLER_FT  # nothing stands over anything else
    ang = best_heading(used, max(diff, MIN_TALLER_FT), row_in, path_in, rotation)
    if even:
        ang["best"], ang["best_pct"], ang["current_pct"] = 0, 0, 0
    heading = round(rotation % 180, 1)
    sh = shading(segs, rotation, used) if segs else []
    return {"lat": round(used, 2), "lat_assumed": lat is None, "months": "April to September", "heading": heading, "x_side": compass(270 + rotation), "start_end": compass(rotation),
            "runs": f"{compass(rotation)} to {compass(rotation + 180)}",
            "tallest": tall and {"name": tall["name"], "height": tall["height"]}, "shortest": short and {"name": short["name"], "height": short["height"]},
            "diff_ft": round(diff, 1), "even": even, "planted": bool(segs),
            "best": ang["best"], "best_pct": ang["best_pct"], "current_pct": ang["current_pct"], "worst_pct": ang["worst_pct"],
            "tall_side": compass(ang["tall_side"]), "current_side": compass(ang["current_side"]), "shading": sh}
