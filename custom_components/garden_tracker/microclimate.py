"""Local climate worked out from your own sensors: recorded frost dates, temperature extremes, rainfall,
expected against actual soil temperature, and a hardiness zone. Pure functions, no Home Assistant imports."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

FROST_F = 32.0
MIN_WINTER_DAYS = 60  # recorded days between December and February for a winter to count toward the zone
SOIL_AIR_DAYS = 10    # soil is expected to follow the average of this many days of air temperature


def zone_from_min(t_f: float) -> str:
    """USDA hardiness zone for an average yearly lowest temperature: 7a is 0 to 5, 7b is 5 to 10, 6b is -5 to 0."""
    n = int((t_f // 10) + 7)
    sub = "a" if (t_f % 10) < 5 else "b"
    return f"{n}{sub}"


def _d(s: str) -> date:
    return date.fromisoformat(s)


def frost_years(daily: dict, today: date, threshold: float = FROST_F) -> list[dict]:
    """Recorded last spring frost and first fall frost for every year with data, newest first."""
    years: dict[int, dict] = {}
    for k, (lo, _hi) in daily.items():
        d = _d(k)
        y = years.setdefault(d.year, {"year": d.year, "last_spring": None, "first_fall": None, "lowest": lo,
                                      "lowest_date": k, "since": k, "days": 0})
        y["days"] += 1
        if k < y["since"]:
            y["since"] = k
        if lo < y["lowest"]:
            y["lowest"], y["lowest_date"] = lo, k
        if lo <= threshold:
            if d.month <= 6 and (y["last_spring"] is None or k > y["last_spring"]):
                y["last_spring"] = k
            if d.month >= 8 and (y["first_fall"] is None or k < y["first_fall"]):
                y["first_fall"] = k
    out = []
    for y in sorted(years.values(), key=lambda r: r["year"], reverse=True):
        y["spring_final"] = today >= date(y["year"], 7, 1)
        y["spring_partial"] = _d(y["since"]) > date(y["year"], 1, 20)  # data started after the winter
        y["lowest"] = round(y["lowest"], 1)
        out.append(y)
    return out


def local_zone(daily: dict, today: date) -> dict:
    """Hardiness zone from the lowest temperature of each completed winter (July to June), averaged."""
    lows: dict[int, dict] = {}
    for k, (lo, _hi) in daily.items():
        d = _d(k)
        s = d.year if d.month >= 7 else d.year - 1
        w = lows.setdefault(s, {"season": s, "lowest": lo, "date": k, "winter_days": 0})
        if lo < w["lowest"]:
            w["lowest"], w["date"] = lo, k
        if d.month in (12, 1, 2):
            w["winter_days"] += 1
    done = []
    for s, w in sorted(lows.items()):
        w["complete"] = today >= date(s + 1, 4, 1) and w["winter_days"] >= MIN_WINTER_DAYS
        w["label"] = f"{s}-{str(s + 1)[2:]}"
        w["lowest"] = round(w["lowest"], 1)
        w["zone"] = zone_from_min(w["lowest"])
        if w["complete"]:
            done.append(w)
    recent = done[-10:]
    cur = lows.get(today.year if today.month >= 7 else today.year - 1)
    out: dict[str, Any] = {"winters": [w for w in sorted(lows.values(), key=lambda r: r["season"], reverse=True)][:10],
                           "count": len(recent), "zone": None, "avg_min": None,
                           "so_far": cur and {"label": cur["label"], "lowest": cur["lowest"], "date": cur["date"]}}
    if recent:
        avg = sum(w["lowest"] for w in recent) / len(recent)
        out["avg_min"] = round(avg, 1)
        out["zone"] = zone_from_min(avg)
    return out


def temp_range(daily: dict, start: date, end: date) -> dict:
    """Lowest and highest recorded between two dates, inclusive."""
    lo = hi = None
    lod = hid = None
    d = start
    while d <= end:
        r = daily.get(d.isoformat())
        if r:
            if lo is None or r[0] < lo:
                lo, lod = r[0], d.isoformat()
            if hi is None or r[1] > hi:
                hi, hid = r[1], d.isoformat()
        d += timedelta(days=1)
    return {"low": lo and round(lo, 1), "high": hi and round(hi, 1), "low_date": lod, "high_date": hid}


def rain_total(rain: dict, start: date, end: date) -> float:
    return round(sum(v for k, v in rain.items() if start.isoformat() <= k <= end.isoformat()), 2)


def periods(today: date) -> dict[str, tuple[date, date]]:
    return {"day": (today, today), "week": (today - timedelta(days=6), today),
            "month": (today.replace(day=1), today), "year": (date(today.year, 1, 1), today)}


def expected_soil(daily: dict, today: date) -> float | None:
    """Soil a few inches down follows recent air temperature, so expect the average of the last days' daily means."""
    vals = []
    for i in range(SOIL_AIR_DAYS):
        r = daily.get((today - timedelta(days=i)).isoformat())
        if r:
            vals.append((r[0] + r[1]) / 2)
    return round(sum(vals) / len(vals), 1) if len(vals) >= 3 else None


def soil_last_year(history: list[dict], today: date, window: int = 3) -> float | None:
    """Average soil reading within a few days of this date a year ago."""
    try:
        ref = today.replace(year=today.year - 1)
    except ValueError:
        ref = today.replace(year=today.year - 1, day=28)
    vals = [r["value"] for r in history if abs((_d(r["date"]) - ref).days) <= window]
    return round(sum(vals) / len(vals), 1) if vals else None
