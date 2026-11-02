"""How much elemental sulfur it takes to bring soil pH down to a target, and how to put it on safely.

Amounts come from Ohio State Extension AGF-507, Table 1 (pounds of sulfur per acre, worked into the top 6 inches,
soil without free lime). Limits per pass and spacing follow Clemson Extension; the yearly ceiling follows the
Maine blueberry guide. Pure functions, no Home Assistant imports."""
from __future__ import annotations

import math
import re
from datetime import date, timedelta
from typing import Any

ACRE = 43560.0
# lb of sulfur per acre, by soil, target pH, then starting pH
TABLE: dict[str, dict[float, dict[float, float]]] = {
    "sand": {6.5: {7.0: 180, 7.5: 300, 8.0: 340, 8.5: 370}, 5.5: {7.0: 640, 7.5: 760, 8.0: 800, 8.5: 830}},
    "silt_loam": {6.5: {7.0: 360, 7.5: 600, 8.0: 670, 8.5: 730}, 5.5: {7.0: 1290, 7.5: 1530, 8.0: 1600, 8.5: 1660}},
    "clay": {6.5: {7.0: 720, 7.5: 1200, 8.0: 1340, 8.5: 1460}, 5.5: {7.0: 2580, 7.5: 3050, 8.0: 3190, 8.5: 3310}},
}
# the soils the garden offers -> (row for the low end, row for the high end, how it is matched)
SOIL_ROWS = {
    "sand": ("sand", "sand", None),
    "sandy_loam": ("sand", "silt_loam", "Sandy loam is not in the published table, so this runs from the sand figure to the silt loam figure."),
    "loam": ("silt_loam", "silt_loam", "Loam is not in the published table, so the silt loam figure is used, the closest one."),
    "silt_loam": ("silt_loam", "silt_loam", None),
    "clay_loam": ("silt_loam", "clay", "Clay loam is not in the published table, so this runs from the silt loam figure to the clay figure."),
    "clay": ("clay", "clay", None),
}
START_MIN, START_MAX, TARGET_MIN, TARGET_MAX = 7.0, 8.5, 5.5, 6.5

CAP_PER_100 = 0.5          # lb per 100 sq ft in one pass: the low end of Clemson's 5 to 10 lb per 1,000 sq ft
CEILING_PER_100 = 1000 / ACRE * 100  # lb per 100 sq ft in a year: Maine's 1,000 lb per acre, about 2.3
SPACING_DAYS = 91          # Clemson: no more often than every 2 to 3 months, so use the longer
SEASON = range(3, 9)       # March to August: Ohio State says fall and winter are not advisable


def _interp(x: float, pts: dict[float, float]) -> float:
    xs = sorted(pts)
    for a, b in zip(xs, xs[1:]):
        if a <= x <= b:
            return pts[a] + (pts[b] - pts[a]) * (x - a) / (b - a)
    return pts[xs[0]] if x < xs[0] else pts[xs[-1]]


def per_acre(row: str, start: float, target: float) -> float:
    t = TABLE[row]
    return _interp(target, {tg: _interp(start, t[tg]) for tg in t})


def target_for(lo: float, hi: float) -> tuple[float | None, str | None]:
    """The pH to aim for: the top of the target range, held to the table's 6.5 and below."""
    t = min(hi, TARGET_MAX)
    if t < TARGET_MIN:
        return None, f"The table stops at pH {TARGET_MIN:g}, and your target tops out at {hi:g}."
    if t < lo:
        return None, f"Your target range starts at {lo:g}, above the table's top of {TARGET_MAX:g}."
    return t, None


def estimate(soil: str, start: float, target: float, area_sqft: float | None) -> dict[str, Any]:
    """Pounds of sulfur for the bed. A low and a high, equal unless the soil sits between two rows of the table."""
    lo_row, hi_row, note = SOIL_ROWS.get(soil, SOIL_ROWS["clay_loam"])
    out: dict[str, Any] = {"ok": False, "note": note}
    if start <= target:
        out["why"] = "Your pH is already at or below the target."
        return out
    if not START_MIN <= start <= START_MAX:
        out["why"] = f"The table covers a starting pH of {START_MIN:g} to {START_MAX:g}. Yours is {start:g}."
        return out
    a, b = per_acre(lo_row, start, target), per_acre(hi_row, start, target)
    lo, hi = min(a, b), max(a, b)
    out.update(ok=True, per_acre=[round(lo), round(hi)], per_100=[round(lo / ACRE * 100, 2), round(hi / ACRE * 100, 2)], range=hi - lo > 1e-9)
    if area_sqft:
        out["lb"] = [round(lo * area_sqft / ACRE, 1), round(hi * area_sqft / ACRE, 1)]
    return out


def lbs_of(amount: Any) -> float | None:
    """Pounds in a logged amount like '2.3 lb'. A bare number has no unit, so it does not count."""
    m = re.match(r"\s*(\d+(?:\.\d+)?)\s*(?:lb|lbs|pound|pounds)\b", str(amount or ""), re.I)
    return float(m.group(1)) if m else None


def next_ok(last: date | None, today: date) -> date:
    return max(today, last + timedelta(days=SPACING_DAYS)) if last else today


def in_season(d: date) -> bool:
    return d.month in SEASON


def season_start(d: date) -> date:
    """The first day sulfur is suited on or after d: d itself in March to August, else the next March 1."""
    if in_season(d):
        return d
    return date(d.year + (1 if d.month > 8 else 0), 3, 1)


def plan(total: tuple[float, float], range_: bool, cap_lb: float, ceiling_lb: float, today: date,
         last: date | None, applied: list[tuple[date, float]]) -> list[dict[str, Any]]:
    """Passes no bigger than the cap, spaced and kept to spring and summer. With a range, only the first pass is planned."""
    lo = total[0]
    if lo <= 0 or cap_lb <= 0:
        return []
    n = 1 if range_ else max(1, math.ceil(lo / cap_lb - 1e-9))
    each = min(cap_lb, lo) if range_ else lo / n
    out, when = [], season_start(next_ok(last, today))
    done = list(applied)
    for i in range(n):
        for _ in range(4):  # push to next year when the yearly ceiling is used up
            year = [lb for d, lb in done if when - timedelta(days=365) < d <= when]
            if sum(year) + each <= ceiling_lb + 1e-9:
                break
            when = season_start(date(when.year + 1, 3, 1))
        out.append({"n": i + 1, "lb": round(each, 1), "date": when.isoformat()})
        done.append((when, each))
        when = season_start(when + timedelta(days=SPACING_DAYS))
    return out


def room_this_year(applied: list[tuple[date, float]], ceiling_lb: float, today: date) -> float:
    used = sum(lb for d, lb in applied if today - timedelta(days=365) < d <= today)
    return max(0.0, ceiling_lb - used)
