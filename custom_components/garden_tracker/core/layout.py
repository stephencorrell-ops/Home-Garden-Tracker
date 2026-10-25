"""Garden layout planner: rows, plant counts, density and support counts for a rectangular garden.

Pure Python, no Home Assistant. All the maths lives here so the Home Assistant card and the web app draw the
same numbers. Geometry is returned in inches, measured from the top-left corner of the garden: x runs across the
garden's width (the direction the rows are stacked), y runs along its length (the direction the rows run)."""
from __future__ import annotations

from typing import Any

ROW_WIDTHS = (24, 30, 36)  # inches between row centres
PAIR_GAP_IN = 12  # distance between the two plant lines of a double row
SUPPORTS = {"none": "No support", "tpost": "T-posts", "cage": "Cages"}
MAX_FT = 500
MAX_ROWS = 200

# crop key -> (in-row spacing in inches, support, T-post spacing in feet). Starter values, all editable per garden.
DEFAULTS: dict[str, tuple[float, str, float]] = {
    "tomato": (24, "tpost", 4), "pepper": (18, "cage", 4), "jalapeno": (18, "cage", 4), "habanero": (18, "cage", 4),
    "cucumber": (12, "tpost", 6), "bean": (4, "tpost", 6), "pea": (2, "tpost", 6),
    "garlic": (6, "none", 4), "onion": (4, "none", 4), "onion_red": (4, "none", 4), "onion_white": (4, "none", 4),
    "onion_sweet": (4, "none", 4), "carrot": (2, "none", 4), "potato": (12, "none", 4), "horseradish": (18, "none", 4),
    "watermelon": (36, "none", 4), "cantaloupe": (24, "none", 4), "pumpkin": (48, "none", 4),
    "cabbage": (18, "none", 4), "lettuce": (8, "none", 4), "cauliflower": (18, "none", 4),
}
GENERIC = (12, "none", 4)


class LayoutError(ValueError):
    pass


def defaults_for(key: str) -> dict:
    sp, sup, post = DEFAULTS.get(key, GENERIC)
    return {"spacing_in": sp, "support": sup, "post_ft": post}


def blank() -> dict:
    return {"width_ft": 20.0, "length_ft": 20.0, "row_in": 30, "double": False, "rows": [], "crops": {}}


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


def validate_crop(spacing_in: Any = None, support: Any = None, post_ft: Any = None) -> dict:
    out: dict = {}
    if spacing_in is not None:
        out["spacing_in"] = _num(spacing_in, "Spacing", 1, 240)
    if support is not None:
        if support not in SUPPORTS:
            raise LayoutError("Support must be none, tpost or cage")
        out["support"] = support
    if post_ft is not None:
        out["post_ft"] = _num(post_ft, "Post spacing", 1, 50)
    return out


def validate_size(layout: dict, width_ft: Any = None, length_ft: Any = None, row_in: Any = None, double: Any = None) -> None:
    if width_ft is not None:
        layout["width_ft"] = _num(width_ft, "Width", 1, MAX_FT)
    if length_ft is not None:
        layout["length_ft"] = _num(length_ft, "Length", 1, MAX_FT)
    if row_in is not None:
        if int(row_in) not in ROW_WIDTHS:
            raise LayoutError("Rows must be 24, 30 or 36 inches apart")
        layout["row_in"] = int(row_in)
    if double is not None:
        layout["double"] = bool(double)
    if layout["width_ft"] * 12 // layout["row_in"] > MAX_ROWS:
        raise LayoutError(f"That is more than {MAX_ROWS} rows. Use a smaller width")


def plan(layout: dict | None, names: dict[str, str]) -> dict:
    """Work out every row and the totals. `names` maps crop key to display name (only plants, not trees)."""
    available = [{"key": k, "name": n, **defaults_for(k), **((layout or {}).get("crops", {}).get(k) or {})}
                 for k, n in sorted(names.items(), key=lambda kv: kv[1].lower())]
    if not layout:
        return {"configured": False, "available": available, "row_widths": list(ROW_WIDTHS), "supports": SUPPORTS}
    w_in, l_in = layout["width_ft"] * 12, layout["length_ft"] * 12
    n, row_in, double = row_count(layout), layout["row_in"], layout["double"]
    pad = (w_in - n * row_in) / 2
    stored = list(layout.get("rows") or [])
    rows, crops = [], {}
    for i in range(n):
        key = stored[i] if i < len(stored) and stored[i] in names else None
        cx = pad + (i + 0.5) * row_in
        xs = [cx - PAIR_GAP_IN / 2, cx + PAIR_GAP_IN / 2] if double else [cx]
        r: dict = {"i": i, "x": cx, "lines": xs, "crop": key, "plants": 0, "ys": [], "posts": 0, "cages": 0}
        if key:
            s = settings_for(layout, key)
            per = int((l_in + 1e-6) // s["spacing_in"])
            r["ys"] = [round((l_in - per * s["spacing_in"]) / 2 + (j + 0.5) * s["spacing_in"], 2) for j in range(per)] if per <= 2000 else []
            r["plants"] = per * len(xs)
            r["per_line"] = per
            if s["support"] == "tpost":
                r["posts"] = int(layout["length_ft"] // s["post_ft"]) + 1
            elif s["support"] == "cage":
                r["cages"] = r["plants"]
            c = crops.setdefault(key, {"key": key, "name": names[key], **s, "rows": 0, "plants": 0, "posts": 0, "cages": 0})
            c["rows"] += 1
            c["plants"] += r["plants"]
            c["posts"] += r["posts"]
            c["cages"] += r["cages"]
        rows.append(r)
    area = layout["width_ft"] * layout["length_ft"]
    plants = sum(c["plants"] for c in crops.values())
    planted_rows = sum(c["rows"] for c in crops.values())
    row_area = planted_rows * row_in / 12 * layout["length_ft"]
    return {
        "configured": True, "width_ft": layout["width_ft"], "length_ft": layout["length_ft"], "row_in": row_in, "double": double,
        "pair_gap_in": PAIR_GAP_IN, "pad_in": pad, "rows": rows, "crops": list(crops.values()), "available": available,
        "row_widths": list(ROW_WIDTHS), "supports": SUPPORTS,
        "totals": {"rows": n, "planted_rows": planted_rows, "plants": plants, "area_sqft": round(area, 1),
                   "density": round(plants / area, 2) if area else 0,
                   "bed_density": round(plants / row_area, 2) if row_area else 0,
                   "posts": sum(c["posts"] for c in crops.values()), "cages": sum(c["cages"] for c in crops.values())},
    }
