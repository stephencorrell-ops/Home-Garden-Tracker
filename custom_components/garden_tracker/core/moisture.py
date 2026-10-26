"""Estimate soil moisture from the last watering, the weather, the soil type and mulch. Used by the web app,
which has no soil probe. A simple bucket: the top few inches hold some water, the sun and wind draw it down
each day, and watering or rain fill it back up. A real reading always wins over this."""
from __future__ import annotations

from datetime import date, timedelta

from . import irrigation as irr

ROOT_IN = 8            # inches of soil the bucket stands for
KC = 0.65              # share of reference evaporation that a bed of crops and bare soil loses
MULCH_ET = 0.7         # mulch cuts what the bare soil loses, so the whole bed dries more slowly
MULCH_RAIN_LOST = 0.05 # inches of a rain caught on the mulch
WINDOW = 21            # days looked back
ALLOWED = 0.5          # water the plants may use before the bed wants watering
# soil: (field capacity %, wilting point %, inches of water held per foot of soil that plants can use)
SOIL_WATER = {
    "sand": (15, 5, 0.8), "sandy_loam": (22, 9, 1.3), "loam": (30, 13, 1.8),
    "silt_loam": (33, 13, 2.0), "clay_loam": (36, 18, 1.8), "clay": (42, 25, 1.6),
}


def estimate(soil: str, mulch: bool, daily: dict, rain: dict, waterings: list[str], today: date, lat: float | None,
             today_temps: tuple | None = None) -> dict | None:
    """Returns {"rows": [{date, value}], "avail": 0 to 1, ...} or None when there is no weather to go on."""
    fc, wp, awc = SOIL_WATER.get(soil, SOIL_WATER[irr.DEFAULT_SOIL])
    taw = awc * ROOT_IN / 12
    lat_used = irr.DEFAULT_LAT if lat is None else lat
    t0 = today.isoformat()
    past = [w for w in waterings if w <= t0]
    last = max(past) if past else None
    floor = today - timedelta(days=WINDOW)
    start = date.fromisoformat(last) if last and date.fromisoformat(last) >= floor else floor
    watered = bool(last) and start == date.fromisoformat(last)
    depl = 0.0 if watered else taw * 0.5
    days_w = {w for w in past}
    rows, ets, d = [], [], start
    have = False
    while d <= today:
        k = d.isoformat()
        t = daily.get(k) or (list(today_temps) if k == t0 and today_temps else None)
        if t and t[0] is not None and t[1] is not None:
            et, have = irr.et0_day(t[0], t[1], lat_used, d), True
        else:
            et = irr.REF_ET_DAY
        et *= KC * (MULCH_ET if mulch else 1.0)
        if k == t0:
            et *= 0.5  # the day is half over
        r = float(rain.get(k) or 0)
        if r >= irr.RAIN_MIN_DAY:
            depl -= max(0.0, r * irr.RAIN_USEFUL - (MULCH_RAIN_LOST if mulch else 0.0))
        if k in days_w:
            depl = 0.0
        depl = max(0.0, min(taw, depl + et))
        ets.append(et)
        rows.append({"date": k, "value": round(wp + (1 - depl / taw) * (fc - wp), 1), "avail": round(1 - depl / taw, 2)})
        d += timedelta(days=1)
    if not have:
        return None
    avail = 1 - depl / taw
    recent = ets[-7:]
    per_day = max(0.01, sum(recent) / len(recent))
    left = max(0.0, (ALLOWED * taw - depl) / per_day) if depl < ALLOWED * taw else 0.0
    return {"rows": rows, "avail": round(avail, 2), "value": rows[-1]["value"], "fc": fc, "wp": wp,
            "since_water": (today - date.fromisoformat(last)).days if last else None, "watered": watered,
            "days_left": round(left), "level": "dry" if avail < 0.4 else ("wet" if avail >= 0.95 else "ok"),
            "taw_in": round(taw, 2), "depth_in": ROOT_IN}
