"""Garden layout planner: rows, plant counts, density and support counts for a rectangular garden.

Pure Python, no Home Assistant. All the maths lives here so the Home Assistant card and the web app draw the
same numbers. Geometry is returned in inches, measured from the top-left corner of the garden: x runs across the
garden's width (the direction the rows are stacked), y runs along its length (the direction the rows run)."""
from __future__ import annotations

from typing import Any

ROW_WIDTHS = (24, 30, 36)  # inches between row centres
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
}
GENERIC = (12, "grid", True, "none", 4)


class LayoutError(ValueError):
    pass


def defaults_for(key: str) -> dict:
    sp, pattern, stagger, sup, post = DEFAULTS.get(key, GENERIC)
    return {"spacing_in": sp, "pattern": pattern, "stagger": stagger, "support": sup, "post_ft": post,
            "post_kind": "stake", "twine_levels": 2}


def blank() -> dict:
    return {"width_ft": 20.0, "length_ft": 20.0, "row_in": 30, "rotation": 0, "rows": [], "crops": {}}


def _num(v: Any, name: str, lo: float, hi: float) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise LayoutError(f"{name} must be a number") from None
    if not lo <= x <= hi:
        raise LayoutError(f"{name} must be between {lo:g} and {hi:g}")
    return x


def row_count(layout: dict) -> int:
    return min(MAX_ROWS, int((layout["width_ft"] * 12 + 1e-6) // layout["row_in"]))


def settings_for(layout: dict, key: str) -> dict:
    return {**defaults_for(key), **(layout.get("crops", {}).get(key) or {})}


def validate_crop(spacing_in: Any = None, support: Any = None, post_ft: Any = None, post_kind: Any = None,
                  twine_levels: Any = None, pattern: Any = None, stagger: Any = None) -> dict:
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
    return out


def validate_size(layout: dict, width_ft: Any = None, length_ft: Any = None, row_in: Any = None, rotation: Any = None) -> None:
    if width_ft is not None:
        layout["width_ft"] = _num(width_ft, "Width", 1, MAX_FT)
    if length_ft is not None:
        layout["length_ft"] = _num(length_ft, "Length", 1, MAX_FT)
    if row_in is not None:
        if int(row_in) not in ROW_WIDTHS:
            raise LayoutError("Rows must be 24, 30 or 36 inches wide")
        layout["row_in"] = int(row_in)
    if rotation is not None:
        if int(rotation) % 90:
            raise LayoutError("Turn the garden in steps of 90 degrees")
        layout["rotation"] = int(rotation) % 360
    if layout["width_ft"] * 12 // layout["row_in"] > MAX_ROWS:
        raise LayoutError(f"That is more than {MAX_ROWS} rows. Use a smaller width")


def row_segments(layout: dict, i: int, names: dict[str, str] | None = None) -> list[dict]:
    """What is planted in row i, as [{"crop", "ft"}] in order from the start of the row.

    A row is stored as a crop key (the whole row), or a list of segments. Anything past the end is cut off."""
    rows = layout.get("rows") or []
    raw = rows[i] if i < len(rows) else None
    if isinstance(raw, str):
        raw = [{"crop": raw, "ft": layout["length_ft"]}]
    out, used = [], 0.0
    for sg in raw or []:
        if names is not None and sg.get("crop") not in names:
            continue
        ft = min(float(sg.get("ft") or 0), layout["length_ft"] - used)
        if ft <= 1e-6:
            continue
        out.append({"crop": sg["crop"], "ft": round(ft, 3)})
        used += ft
    return out


def _segment(layout: dict, i: int, cx: float, start_in: float, seg_in: float, key: str, name: str) -> dict:
    row_in = layout["row_in"]
    s = settings_for(layout, key)
    pattern = s["pattern"]
    if pattern == "grid":  # offset rows of plants, every plant the same distance from its neighbours
        pitch = s["spacing_in"] * HEX
        n_lines = max(1, round(row_in / pitch))
        xs = [cx + (k - (n_lines - 1) / 2) * pitch for k in range(n_lines)]
        stagger = n_lines > 1
    elif pattern == "double":
        xs = [cx - PAIR_GAP_IN / 2, cx + PAIR_GAP_IN / 2]
        stagger = bool(s["stagger"])
    else:
        xs, stagger = [cx], False
    grid = pattern == "grid"
    sp = s["spacing_in"]
    extra = sp / 2 if stagger else 0  # offset lines are shifted half a step, so they need half a step more room
    per = max(0, int((seg_in - extra + 1e-6) // sp))
    first = start_in + (seg_in - per * sp - extra) / 2
    ys = [round(first + (j + 0.5) * sp, 2) for j in range(per)] if per <= 2000 else []
    seg = {"crop": key, "name": name, "start_in": round(start_in, 2), "len_in": round(seg_in, 2), "lines": xs, "ys": ys,
           "ys2": [round(y + extra, 2) for y in ys] if stagger else [], "per_line": per, "plants": per * len(xs),
           "posts": 0, "stakes": 0, "twine_ft": 0, "cages": 0, "grid": grid, "block_w_in": (xs[-1] - xs[0]) + 12}
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


def plan(layout: dict | None, names: dict[str, str]) -> dict:
    """Work out every row and the totals. `names` maps crop key to display name (only plants, not trees)."""
    available = [{"key": k, "name": n, **defaults_for(k), **((layout or {}).get("crops", {}).get(k) or {})}
                 for k, n in sorted(names.items(), key=lambda kv: kv[1].lower())]
    if not layout:
        return {"configured": False, "available": available, "row_widths": list(ROW_WIDTHS), "supports": SUPPORTS, "patterns": PATTERNS}
    w_in, l_in = layout["width_ft"] * 12, layout["length_ft"] * 12
    n, row_in = row_count(layout), layout["row_in"]
    pad = (w_in - n * row_in) / 2
    rows, crops = [], {}
    bed_ft2 = 0.0
    for i in range(n):
        cx = pad + (i + 0.5) * row_in
        segs, start = [], 0.0
        for sg in row_segments(layout, i, names):
            seg = _segment(layout, i, cx, start, sg["ft"] * 12, sg["crop"], names[sg["crop"]])
            segs.append(seg)
            start += sg["ft"] * 12
            c = crops.setdefault(sg["crop"], {"key": sg["crop"], "name": names[sg["crop"]], **settings_for(layout, sg["crop"]),
                                              "rows": 0, "_rows": set(), "feet": 0.0, "plants": 0, "posts": 0, "stakes": 0,
                                              "twine_ft": 0, "cages": 0})
            c["_rows"].add(i)
            c["feet"] += sg["ft"]
            for k in ("plants", "posts", "stakes", "cages"):
                c[k] += seg[k]
            c["twine_ft"] = round(c["twine_ft"] + seg["twine_ft"], 1)
            bed_ft2 += sg["ft"] * row_in / 12
        whole = len(segs) == 1 and segs[0]["len_in"] >= l_in - 1e-6
        rows.append({"i": i, "x": cx, "crop": segs[0]["crop"] if whole else None, "used_ft": round(start / 12, 2),
                     "segments": segs, **{k: sum(sg[k] for sg in segs) for k in ("plants", "posts", "stakes", "twine_ft", "cages")}})
    for c in crops.values():
        c["rows"] = len(c.pop("_rows"))
        c["feet"] = round(c["feet"], 2)
    area = layout["width_ft"] * layout["length_ft"]
    plants = sum(c["plants"] for c in crops.values())
    return {
        "configured": True, "width_ft": layout["width_ft"], "length_ft": layout["length_ft"], "row_in": row_in, "rotation": int(layout.get("rotation") or 0),
        "pair_gap_in": PAIR_GAP_IN, "pad_in": pad, "rows": rows, "crops": list(crops.values()), "available": available,
        "row_widths": list(ROW_WIDTHS), "supports": SUPPORTS, "patterns": PATTERNS,
        "totals": {"rows": n, "planted_rows": sum(1 for r in rows if r["segments"]), "plants": plants, "area_sqft": round(area, 1),
                   "density": round(plants / area, 2) if area else 0,
                   "bed_density": round(plants / bed_ft2, 2) if bed_ft2 else 0,
                   "posts": sum(c["posts"] for c in crops.values()), "stakes": sum(c["stakes"] for c in crops.values()),
                   "twine_ft": round(sum(c["twine_ft"] for c in crops.values()), 1),
                   "post_kinds": POST_KINDS, "cages": sum(c["cages"] for c in crops.values())},
    }
