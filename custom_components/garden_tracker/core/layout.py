"""Garden layout planner: rows, plant counts, density and support counts for a rectangular garden.

Pure Python, no Home Assistant. All the maths lives here so the Home Assistant card and the web app draw the
same numbers. Geometry is returned in inches, measured from the top-left corner of the garden: x runs across the
garden's width (the direction the rows are stacked), y runs along its length (the direction the rows run)."""
from __future__ import annotations

import math
from typing import Any

from . import rotation as rot
from . import sun

ROW_WIDTHS = (24, 30, 36, 48)  # inches across a planted row; corn wants a 48 in block
DEFAULT_PATH_IN = 24  # the access path left between rows
PAIR_GAP_IN = 12  # distance between the two plant lines of a double row
SUPPORTS = {"none": "No support", "tpost": "T-posts", "cage": "Cages", "corral": "Corral (posts and twine)"}
POST_KINDS = {"stake": "Stakes", "tpost": "T-posts"}
MAX_FT = 500
MAX_ROWS = 200

PATTERNS = {"single": "Single line", "double": "Double line", "grid": "Grid (offset)"}
HEX = 0.8660254  # an offset grid keeps every plant the same distance from its neighbours; lines sit this much closer

# crop key -> (spacing in inches, pattern, offset the two lines of a double, support, post spacing in feet).
# For a grid the spacing is the distance between neighbouring plants. Starter values, all editable per garden.
DEFAULTS: dict[str, tuple[float, str, bool, str, float]] = {
    "tomato": (24, "single", False, "tpost", 4), "pepper": (18, "single", False, "corral", 3),
    "jalapeno": (18, "single", False, "corral", 3), "habanero": (18, "single", False, "corral", 3),
    "cucumber": (12, "single", False, "tpost", 6), "pea": (2, "double", True, "tpost", 6),
    "bean": (4, "grid", True, "none", 6),  # a bush bean; for a climber use a single or double line with T-posts
    "garlic": (6, "grid", True, "none", 4), "onion": (4, "grid", True, "none", 4), "onion_red": (4, "grid", True, "none", 4),
    "onion_white": (4, "grid", True, "none", 4), "onion_sweet": (4, "grid", True, "none", 4),
    "carrot": (2, "grid", True, "none", 4), "potato": (12, "grid", True, "none", 4),
    "horseradish": (18, "grid", True, "none", 4), "watermelon": (36, "grid", True, "none", 4),
    "cantaloupe": (24, "grid", True, "none", 4), "pumpkin": (48, "grid", True, "none", 4),
    "cabbage": (18, "grid", True, "none", 4), "lettuce": (8, "grid", True, "none", 4),
    "cauliflower": (18, "grid", True, "none", 4),
    "broccoli": (18, "single", False, "none", 4), "kale": (14, "single", False, "none", 4), "spinach": (4, "grid", True, "none", 4),
    "radish": (2, "grid", True, "none", 4), "beet": (3, "grid", True, "none", 4), "zucchini": (36, "single", False, "none", 4),
    "eggplant": (24, "single", False, "cage", 3), "sunflower": (12, "single", False, "none", 4),
    "basil": (10, "grid", True, "none", 4), "cilantro": (4, "grid", True, "none", 4), "parsley": (8, "grid", True, "none", 4),
    "dill": (8, "grid", True, "none", 4), "chives": (6, "grid", True, "none", 4), "mint": (18, "single", False, "none", 4),
    "oregano": (12, "single", False, "none", 4), "thyme": (12, "single", False, "none", 4), "rosemary": (24, "single", False, "none", 4),
    "sage": (18, "single", False, "none", 4),
    "corn": (12, "grid", True, "none", 4), "hops": (36, "single", False, "tpost", 10),  # hops climb a string or pole 10 to 20 ft up
}
GENERIC = (12, "grid", True, "none", 4)
# Corn is pollinated by wind, so it needs a block at least 4 ft across (and 4 ft long) instead of a narrow row.
BLOCKS: dict[str, int] = {"corn": 48}


class LayoutError(ValueError):
    pass


def block_text(name: str, need: int, row_in: int) -> str:
    return (f"{name} is pollinated by wind, so it needs a block at least {need // 12} ft across, not a narrow row. "
            f"Your rows are {row_in} in wide. Set the row width to {need} in for a block, or grow {name.lower()} where the rows are {need} in.")


def defaults_for(key: str) -> dict:
    sp, pattern, stagger, sup, post = DEFAULTS.get(key, GENERIC)
    return {"spacing_in": sp, "pattern": pattern, "stagger": stagger, "support": sup, "post_ft": post,
            "post_kind": "stake", "twine_levels": 2, "yield_lb": None, "height_ft": sun.height_for(key),
            "min_row_in": BLOCKS.get(key)}


def blank(year: int) -> dict:
    return {"width_ft": 20.0, "length_ft": 20.0, "row_in": 30, "path_in": DEFAULT_PATH_IN, "rotation": 0, "year": year,
            "rows": [], "crops": {}, "draft": None}


def _num(v: Any, name: str, lo: float, hi: float) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise LayoutError(f"{name} must be a number") from None
    if not lo <= x <= hi:
        raise LayoutError(f"{name} must be between {lo:g} and {hi:g}")
    return x


def path_in(layout: dict) -> float:
    p = layout.get("path_in")
    return DEFAULT_PATH_IN if p is None else float(p)


def row_count(layout: dict) -> int:
    """How many planted rows fit across the width, with an access path between each pair."""
    w, r, p = layout["width_ft"] * 12, layout["row_in"], path_in(layout)
    return max(0, min(MAX_ROWS, int((w + p + 1e-6) // (r + p))))


def row_x0(layout: dict, i: int) -> float:
    """Distance in inches from the left edge to the start of planted row i (the rows are centred across the width)."""
    n, r, p = row_count(layout), layout["row_in"], path_in(layout)
    pad = (layout["width_ft"] * 12 - (n * r + max(0, n - 1) * p)) / 2
    return pad + i * (r + p)


def settings_for(layout: dict, key: str) -> dict:
    return {**defaults_for(key), **(layout.get("crops", {}).get(key) or {})}


def validate_crop(spacing_in: Any = None, support: Any = None, post_ft: Any = None, post_kind: Any = None,
                  twine_levels: Any = None, pattern: Any = None, stagger: Any = None, yield_lb: Any = None, height_ft: Any = None) -> dict:
    out: dict = {}
    if spacing_in is not None:
        out["spacing_in"] = _num(spacing_in, "Spacing", 1, 240)
    if support is not None:
        if support not in SUPPORTS:
            raise LayoutError("Support must be none, tpost, cage or corral")
        out["support"] = support
    if post_ft is not None:
        out["post_ft"] = _num(post_ft, "Post spacing", 1, 50)
    if post_kind is not None:
        if post_kind not in POST_KINDS:
            raise LayoutError("Corral posts must be stakes or T-posts")
        out["post_kind"] = post_kind
    if twine_levels is not None:
        out["twine_levels"] = int(_num(twine_levels, "Twine lines", 1, 6))
    if pattern is not None:
        if pattern not in PATTERNS:
            raise LayoutError("Pattern must be single, double or grid")
        out["pattern"] = pattern
    if stagger is not None:
        out["stagger"] = bool(stagger)
    if yield_lb is not None:
        out["yield_lb"] = _num(yield_lb, "Weight per plant", 0.01, 1000)
    if height_ft is not None:
        out["height_ft"] = _num(height_ft, "Height", 0.1, 30)
    return out


def validate_size(layout: dict, width_ft: Any = None, length_ft: Any = None, row_in: Any = None, rotation: Any = None,
                  path: Any = None) -> None:
    if width_ft is not None:
        layout["width_ft"] = _num(width_ft, "Width", 1, MAX_FT)
    if length_ft is not None:
        layout["length_ft"] = _num(length_ft, "Length", 1, MAX_FT)
    if row_in is not None:
        if int(row_in) not in ROW_WIDTHS:
            raise LayoutError("Rows must be 24, 30, 36 or 48 inches wide")
        layout["row_in"] = int(row_in)
    if rotation is not None:
        r = round(_num(rotation, "Angle", -720, 720) % 360, 1)  # any angle: the rows run this many degrees off north
        layout["rotation"] = int(r) if r == int(r) else r
    if path is not None:
        layout["path_in"] = _num(path, "Path width", 0, 120)
    if (layout["width_ft"] * 12 + path_in(layout)) // (layout["row_in"] + path_in(layout)) > MAX_ROWS:
        raise LayoutError(f"That is more than {MAX_ROWS} rows. Use a smaller width")


def row_segments(layout: dict, i: int, names: dict[str, str] | None = None) -> list[dict]:
    """What is planted in row i, as [{"crop", "ft", "start_ft"}] in order along the row.

    A row is stored as a crop key (the whole row), or a list of sections. Sections without a start follow the one
    before. Overlaps and anything past the end are cut off."""
    rows = layout.get("rows") or []
    raw = rows[i] if i < len(rows) else None
    if isinstance(raw, str):
        raw = [{"crop": raw, "ft": layout["length_ft"], "start_ft": 0}]
    out, cursor, end = [], 0.0, layout["length_ft"]
    placed = []
    for sg in raw or []:
        start = sg.get("start_ft")
        start = cursor if start is None else float(start)
        placed.append((start, sg))
        cursor = start + float(sg.get("ft") or 0)
    floor = 0.0
    for start, sg in sorted(placed, key=lambda t: t[0]):
        if names is not None and sg.get("crop") not in names:
            continue
        start = max(start, floor, 0.0)
        ft = min(float(sg.get("ft") or 0), end - start)
        if ft <= 1e-6:
            continue
        out.append({"crop": sg["crop"], "ft": round(ft, 3), "start_ft": round(start, 3), "variety": sg.get("variety") or ""})
        floor = start + ft
    return out


def _lines(layout: dict, s: dict) -> tuple[list[float], bool]:
    """Offsets of the plant lines from the middle of the row, and whether every other line is shifted half a step."""
    row_in, pattern = layout["row_in"], s["pattern"]
    if pattern == "grid":  # offset rows of plants, every plant the same distance from its neighbours
        pitch = s["spacing_in"] * HEX
        n = max(1, round(row_in / pitch))
        return [(k - (n - 1) / 2) * pitch for k in range(n)], n > 1
    if pattern == "double":
        return [-PAIR_GAP_IN / 2, PAIR_GAP_IN / 2], bool(s["stagger"])
    return [0.0], False


def _per_line(s: dict, seg_in: float, stagger: bool) -> int:
    sp = s["spacing_in"]
    return max(0, int((seg_in - (sp / 2 if stagger else 0) + 1e-6) // sp))


def _segment(layout: dict, cx: float, start_in: float, seg_in: float, key: str, name: str) -> dict:
    s = settings_for(layout, key)
    offs, stagger = _lines(layout, s)
    xs = [cx + o for o in offs]
    sp = s["spacing_in"]
    extra = sp / 2 if stagger else 0  # offset lines are shifted half a step, so they need half a step more room
    per = _per_line(s, seg_in, stagger)
    first = start_in + (seg_in - per * sp - extra) / 2
    ys = [round(first + (j + 0.5) * sp, 2) for j in range(per)] if per <= 2000 else []
    seg = {"crop": key, "name": name, "start_in": round(start_in, 2), "len_in": round(seg_in, 2), "lines": xs, "ys": ys,
           "ys2": [round(y + extra, 2) for y in ys] if stagger else [], "per_line": per, "plants": per * len(xs),
           "posts": 0, "stakes": 0, "twine_ft": 0, "cages": 0, "grid": s["pattern"] == "grid",
           "block_w_in": (xs[-1] - xs[0]) + 12}
    seg_ft = seg_in / 12
    stations = int(seg_ft // s["post_ft"]) + 1
    if s["support"] == "tpost":
        seg["posts"] = stations
    elif s["support"] == "cage":
        seg["cages"] = seg["plants"]
    elif s["support"] == "corral":
        # a post on each side at every station, with twine run along both sides and closed across the ends
        seg["posts" if s["post_kind"] == "tpost" else "stakes"] = stations * 2
        seg["twine_ft"] = round(s["twine_levels"] * (2 * seg_ft + 2 * seg["block_w_in"] / 12), 1)
    return seg


# ---- rotation ---------------------------------------------------------------------------------------------
def trait_key(crop: str, variety: str) -> str:
    return f"{crop}|{(variety or '').strip().lower()}"


def resistances(traits: dict | None, crop: str, variety: str | None) -> frozenset:
    """The diseases a named variety is resistant to, as entered from its seed packet."""
    if not variety or not traits:
        return frozenset()
    return frozenset((traits.get(trait_key(crop, variety)) or {}).get("resist") or [])


def _conflicts(layout: dict, x0: float, y0: float, y1: float, crop: str, history: dict[int, dict], year: int,
               names: dict[str, str], resist: frozenset = frozenset()) -> list[dict]:
    """Earlier seasons that grew a crop which should not be followed by `crop` on the same ground."""
    x1, found = x0 + layout["row_in"], {}
    for hy, hl in sorted(history.items(), reverse=True):
        if hy >= year:
            continue
        for hi in range(row_count(hl)):
            hx0 = row_x0(hl, hi)
            if min(x1, hx0 + hl["row_in"]) - max(x0, hx0) < 0.5 * min(layout["row_in"], hl["row_in"]):
                continue  # a different row
            for sg in row_segments(hl, hi):
                a, b = sg["start_ft"] * 12, (sg["start_ft"] + sg["ft"]) * 12
                over = min(y1, b) - max(y0, a)
                if over < 6:
                    continue
                bad = rot.check(crop, sg["crop"], year - hy, resist)
                if bad and (hy, sg["crop"]) not in found:
                    found[(hy, sg["crop"])] = {**bad, "year": hy, "years_ago": year - hy, "other": sg["crop"],
                                               "other_name": names.get(sg["crop"], sg["crop"]),
                                               "overlap_ft": round(over / 12, 1), "back_in": hy + bad["rest"]}
    return sorted(found.values(), key=lambda c: ({"same": 0, "family": 1}.get(c["level"], 2), -c["year"]))


def _join(items: list[str]) -> str:
    return ", ".join(items[:-1]) + " and " + items[-1] if len(items) > 1 else items[0]


def _alert_text(name: str, row: int, c: dict, variety: str = "") -> str:
    who = f"{name} ({variety})" if variety else name
    where = f"row {row + 1}"
    if c["level"] == "resistant":
        return (f"{c['other_name']} grew in {where} in {c['year']}. {who} is within the usual rest time, but it is resistant to "
                f"{_join(c['resisted'])}, so those are not a worry. Rotate anyway when you can.")
    t = f"{name} was already in {where} in {c['year']}." if c["level"] == "same" else \
        f"{c['other_name']} grew in {where} in {c['year']}, and {name} shares diseases with it."
    t += f" Still a risk: {_join(c['risks'])}. Keep it off this spot until {c['back_in']}."
    if c["resisted"]:
        t += f" {variety or 'The variety'} resists {_join(c['resisted'])}, which shortens the wait."
    return t


# ---- planning a crop from a target ----------------------------------------------------------------------
def draft_result(layout: dict, names: dict[str, str], history: dict[int, dict], year: int, traits: dict | None = None) -> dict | None:
    """The row length a crop needs for a target: harvest weight, number of plants, or feet of row."""
    d = layout.get("draft")
    if not d or d.get("crop") not in names:
        return None
    key, mode, value = d["crop"], d.get("mode") or "weight", d.get("value")
    s = settings_for(layout, key)
    offs, stagger = _lines(layout, s)
    fit = lambda seg_in: _per_line(s, seg_in, stagger) * len(offs)  # noqa: E731
    variety = (d.get("variety") or "").strip()
    resist = resistances(traits, key, variety)
    res: dict = {"crop": key, "name": names[key], "variety": variety, "resist": sorted(resist),
                 "height_ft": ((traits or {}).get(trait_key(key, variety)) or {}).get("height_ft") or s["height_ft"], "mode": mode, "value": value, "spacing_in": s["spacing_in"], "pattern": s["pattern"],
                 "yield_lb": s["yield_lb"], "lines": len(offs), "ready": False, "need": None, "flags": []}
    if not value or value <= 0:
        res["need"] = "value"
    elif mode == "length":
        res.update(length_ft=value, plants=fit(value * 12), ready=True)
    else:
        if mode == "weight":
            if not s["yield_lb"]:
                res["need"] = "yield"
                return res
            needed = math.ceil(value / s["yield_lb"] - 1e-9)
        else:
            needed = math.ceil(value - 1e-9)
        ft = 0.5
        while ft <= MAX_FT and fit(ft * 12) < needed:
            ft += 0.5
        if ft > MAX_FT:
            res["need"] = "size"
            return res
        res.update(plants_needed=needed, length_ft=ft, plants=fit(ft * 12), ready=True)
    if res["ready"]:
        res["rows"] = round(res["length_ft"] / layout["length_ft"], 2)
        res["est_lb"] = round(res["plants"] * s["yield_lb"], 1) if s["yield_lb"] else None
        res["per_ft"] = round(res["plants"] / res["length_ft"], 2)
    for i in range(row_count(layout)):  # would this crop clash with last seasons' crops in each row?
        c = _conflicts(layout, row_x0(layout, i), 0, layout["length_ft"] * 12, key, history, year, names, resist)
        res["flags"].append({"level": c[0]["level"], "text": f"{c[0]['other_name']} in {c[0]['year']}"} if c else None)
    return res


def plan(layout: dict | None, names: dict[str, str], history: dict[int, dict] | None = None, year: int | None = None,
         traits: dict | None = None, lat: float | None = None) -> dict:
    """Work out every row and the totals. `names` maps crop key to display name (only plants, not trees)."""
    history = history or {}
    available = [{"key": k, "name": n, **defaults_for(k), **((layout or {}).get("crops", {}).get(k) or {}),
                  "diseases": rot.diseases_for(k), "habits": sun.habits_for(k)} for k, n in sorted(names.items(), key=lambda kv: kv[1].lower())]
    if not layout:
        return {"configured": False, "available": available, "row_widths": list(ROW_WIDTHS), "supports": SUPPORTS,
                "patterns": PATTERNS}
    year = int(layout.get("year") or year or 0)
    l_in = layout["length_ft"] * 12
    n, row_in = row_count(layout), layout["row_in"]
    rows, crops, alerts = [], {}, []
    bed_ft2 = 0.0
    for i in range(n):
        x0 = row_x0(layout, i)
        cx = x0 + row_in / 2
        segs = []
        for sg in row_segments(layout, i, names):
            seg = _segment(layout, cx, sg["start_ft"] * 12, sg["ft"] * 12, sg["crop"], names[sg["crop"]])
            segs.append(seg)
            c = crops.setdefault(sg["crop"], {"key": sg["crop"], "name": names[sg["crop"]], **settings_for(layout, sg["crop"]),
                                              "rows": 0, "_rows": set(), "feet": 0.0, "plants": 0, "posts": 0, "stakes": 0,
                                              "twine_ft": 0, "cages": 0})
            c["_rows"].add(i)
            c["feet"] += sg["ft"]
            for k in ("plants", "posts", "stakes", "cages"):
                c[k] += seg[k]
            c["twine_ft"] = round(c["twine_ft"] + seg["twine_ft"], 1)
            bed_ft2 += sg["ft"] * row_in / 12
            seg["variety"] = sg.get("variety") or ""
            vt = (traits or {}).get(trait_key(sg["crop"], seg["variety"])) if seg["variety"] else None
            seg["height_ft"] = (vt or {}).get("height_ft") or c["height_ft"]  # a variety can be taller or shorter than its crop usually is
            resist = resistances(traits, sg["crop"], seg["variety"])
            for bad in _conflicts(layout, x0, seg["start_in"], seg["start_in"] + seg["len_in"], sg["crop"], history, year, names, resist):
                alerts.append({"row": i, "crop": sg["crop"], "name": names[sg["crop"]], "variety": seg["variety"], **bad,
                               "text": _alert_text(names[sg["crop"]], i, bad, seg["variety"])})
        whole = len(segs) == 1 and segs[0]["start_in"] <= 1e-6 and segs[0]["len_in"] >= l_in - 1e-6
        rows.append({"i": i, "x": cx, "x0": x0, "crop": segs[0]["crop"] if whole else None,
                     "used_ft": round(sum(sg["len_in"] for sg in segs) / 12, 2), "segments": segs,
                     **{k: sum(sg[k] for sg in segs) for k in ("plants", "posts", "stakes", "twine_ft", "cages")}})
    for c in crops.values():
        c["rows"] = len(c.pop("_rows"))
        c["feet"] = round(c["feet"], 2)
    area = layout["width_ft"] * layout["length_ft"]
    plants = sum(c["plants"] for c in crops.values())
    warnings = []
    for c in crops.values():
        need = BLOCKS.get(c["key"])
        if need and row_in < need:
            warnings.append({"crop": c["key"], "name": c["name"], "text": block_text(c["name"], need, row_in)})
        for r in rows:
            for sg in r["segments"]:
                if need and sg["crop"] == c["key"] and sg["len_in"] < need - 1e-6:
                    warnings.append({"crop": c["key"], "name": c["name"], "text": f"{c['name']} in row {r['i'] + 1} is only {sg['len_in'] / 12:.1f} ft long. It needs a block at least {need // 12} ft by {need // 12} ft to pollinate."})
    alerts.sort(key=lambda a: ({"same": 0, "family": 1}.get(a["level"], 2), a["row"]))
    return {
        "configured": True, "year": year, "width_ft": layout["width_ft"], "length_ft": layout["length_ft"], "row_in": row_in,
        "path_in": path_in(layout), "rotation": layout.get("rotation") or 0,
        "sun": sun.analyse(rows, row_in, path_in(layout), float(layout.get("rotation") or 0), lat, {k: c["height_ft"] for k, c in crops.items()}),
        "pair_gap_in": PAIR_GAP_IN, "rows": rows, "crops": list(crops.values()), "available": available, "warnings": warnings,
        "row_widths": list(ROW_WIDTHS), "supports": SUPPORTS, "patterns": PATTERNS, "alerts": alerts,
        "draft": draft_result(layout, names, history, year, traits), "rotation_sources": rot.SOURCES,
        "totals": {"rows": n, "planted_rows": sum(1 for r in rows if r["segments"]), "plants": plants, "area_sqft": round(area, 1),
                   "density": round(plants / area, 2) if area else 0,
                   "bed_density": round(plants / bed_ft2, 2) if bed_ft2 else 0,
                   "posts": sum(c["posts"] for c in crops.values()), "stakes": sum(c["stakes"] for c in crops.values()),
                   "twine_ft": round(sum(c["twine_ft"] for c in crops.values()), 1),
                   "post_kinds": POST_KINDS, "cages": sum(c["cages"] for c in crops.values())},
    }
