"""Pure calculation helpers (no Home Assistant imports)."""
from __future__ import annotations

import math
from datetime import date, timedelta
from typing import Any


def d(iso: str | None) -> date | None:
    return date.fromisoformat(iso) if iso else None


def days_since(iso: str | None, today: date) -> int | None:
    return (today - date.fromisoformat(iso)).days if iso else None


def days_until(target: date | None, today: date) -> int | None:
    return (target - today).days if target else None


def latest(items: list[dict], key: str = "date") -> dict | None:
    return max(items, key=lambda i: i[key]) if items else None


def mean(xs: list[float]) -> float:
    return sum(xs) / len(xs)


# ---- sprays ----------------------------------------------------------------
def next_spray_date(v: dict) -> date | None:
    s = latest(v["sprays"])
    if s and s.get("reapply_days"):
        return date.fromisoformat(s["date"]) + timedelta(days=s["reapply_days"])
    return None


def safe_harvest_date(v: dict) -> date | None:
    dates = [date.fromisoformat(s["date"]) + timedelta(days=s["phi_days"])
             for s in v["sprays"] if s.get("phi_days") is not None]
    return max(dates) if dates else None


def spray_cutoff_date(v: dict) -> date | None:
    """Last day the most recently used product could go on and still allow the expected harvest."""
    s = latest(v["sprays"])
    harvest = d(v.get("expected_harvest"))
    if s and s.get("phi_days") is not None and harvest:
        return harvest - timedelta(days=s["phi_days"])
    return None


# ---- degree days -----------------------------------------------------------
def degree_days(daily: dict[str, list[float]], start: date, end: date,
                lower: float, upper: float) -> float:
    """Average method with horizontal cutoffs, degrees F."""
    total, day = 0.0, start
    while day <= end:
        v = daily.get(day.isoformat())
        if v:
            tmin = min(max(v[0], lower), upper)
            tmax = min(max(v[1], lower), upper)
            total += max(0.0, (tmin + tmax) / 2 - lower)
        day += timedelta(days=1)
    return total


def recent_dd_rate(daily: dict, today: date, n: int, lower: float, upper: float) -> float:
    """Average degree days per day over the last n complete days that have data."""
    total, days = 0.0, 0
    for i in range(1, n + 1):
        day = today - timedelta(days=i)
        if daily.get(day.isoformat()):
            total += degree_days(daily, day, day, lower, upper)
            days += 1
    return total / days if days else 0.0


def pest_status(v: dict, pest: dict, daily: dict, today: date) -> dict[str, Any] | None:
    biofix, logged = None, False
    stored = v.get("biofix", {}).get(pest["key"])
    if stored and date.fromisoformat(stored).year == today.year:
        biofix, logged = date.fromisoformat(stored), True
    elif pest.get("default_biofix"):
        m, dd = pest["default_biofix"].split("-")
        biofix = date(today.year, int(m), int(dd))
    if biofix is None or biofix > today:
        return None
    # Targets are counted from the default start (Jan 1). A logged trap catch restarts the count, so the part
    # of each target that stood for "waiting for first moths" comes off.
    cut = pest.get("no_biofix_dd", 0) if logged else 0
    total = degree_days(daily, biofix, today, pest["lower_f"], pest["upper_f"])
    ms = sorted(({**m, "dd": m["dd"] - cut} for m in pest.get("milestones", [])), key=lambda m: m["dd"])
    nxt = next((m for m in ms if m["dd"] > total and not m.get("gap")), None)
    reached = [m for m in ms if m["dd"] <= total]
    act = next((m for m in reversed(reached) if not m.get("gap")), None)  # the latest spray window that has opened
    in_gap = bool(reached and reached[-1].get("gap"))
    open_since = None
    if act:  # the day that window opened, so the card can say a spray is due
        run, day = 0.0, biofix
        while day <= today:
            run += degree_days(daily, day, day, pest["lower_f"], pest["upper_f"])
            if run >= act["dd"]:
                open_since = day.isoformat()
                break
            day += timedelta(days=1)
    return {
        "dd": round(total, 1), "biofix": biofix.isoformat(), "estimated_start": not logged and bool(pest.get("no_biofix_dd")),
        "next_dd": nxt["dd"] if nxt else None,
        "next_action": nxt["note"] if nxt else None,
        "dd_to_next": round(nxt["dd"] - total, 1) if nxt else None,
        "reached": reached, "open_since": open_since,
        "open_note": act["note"] if act else None, "open_dd": act["dd"] if act else None, "repeat_days": act.get("repeat_days") if act else None,
        "in_gap": in_gap, "gap_note": reached[-1]["note"] if in_gap else None,
    }


# ---- harvest ---------------------------------------------------------------
def plant_totals(v: dict) -> dict[str, float]:
    t = {p["id"]: 0.0 for p in v["plants"]}
    for h in v["harvests"]:
        for pid, val in h["shares"].items():
            t[pid] = t.get(pid, 0.0) + val
    return t


def split_even(lbs: float, plant_ids: list[str]) -> dict[str, float]:
    share = round(lbs / len(plant_ids), 4)
    return {pid: share for pid in plant_ids}


def _full_year_data(daily: dict, year: int) -> bool:
    keys = [k for k in daily if k.startswith(f"{year}-")]
    return bool(keys) and min(keys) <= f"{year}-02-01"


def bloom_dates(v: dict) -> dict[int, date]:
    """Full bloom for each year: the earliest date logged."""
    out: dict[int, date] = {}
    for b in v.get("blooms", []):
        day = date.fromisoformat(b["date"])
        if day.year not in out or day < out[day.year]:
            out[day.year] = day
    return out


def _season(year: int, first: date, lbs: float, plants: int, daily: dict,
            planted: date | None, tree: bool, bloom: date | None = None) -> dict:
    s = {"year": year, "first_harvest": first.isoformat(), "doy": first.timetuple().tm_yday,
         "total": round(lbs, 2), "yield_per_plant": round(lbs / max(1, plants), 2),
         "days_to_first": (first - planted).days if planted else None, "dd_first": None, "dd_bloom": None}
    if tree and _full_year_data(daily, year):
        s["dd_first"] = round(degree_days(daily, date(year, 1, 1), first, 50, 86), 1)
    if tree and bloom and bloom < first and bloom.isoformat() in daily:
        s["dd_bloom"] = round(degree_days(daily, bloom, first, 50, 86), 1)
    return s


def seasons_for(v: dict, varieties: dict, daily: dict, today: date, perennial: bool | None = None) -> list[dict]:
    """Past seasons for this variety. Trees and bushes use their own earlier years; annuals use earlier records of the same variety."""
    out: list[dict] = []
    if perennial is None:
        perennial = v["kind"] == "tree"
    if perennial:
        by_year: dict[int, list] = {}
        for h in v["harvests"]:
            by_year.setdefault(int(h["date"][:4]), []).append(h)
        for y, hs in sorted(by_year.items()):
            if y >= today.year:
                continue
            first = date.fromisoformat(min(h["date"] for h in hs))
            out.append(_season(y, first, sum(h["lbs"] for h in hs), len(v["plants"]), daily, None, True, bloom_dates(v).get(y)))
    else:
        key = (v["species"], v["name"].strip().lower())
        for o in varieties.values():
            if o["id"] == v["id"] or (o["species"], o["name"].strip().lower()) != key or not o["harvests"]:
                continue
            planted = date.fromisoformat(o["planted"])
            if not o.get("archived") and planted.year >= today.year:
                continue
            first = date.fromisoformat(min(h["date"] for h in o["harvests"]))
            out.append(_season(planted.year, first, sum(h["lbs"] for h in o["harvests"]),
                               len(o["plants"]), daily, planted, False))
        out.sort(key=lambda s: (s["year"], s["first_harvest"]))
    return out


def first_harvests(v: dict, today: date) -> list[dict]:
    """The date of the first pick in each earlier year, newest first. Empty once this year's first pick is logged."""
    firsts: dict[int, str] = {}
    for h in v.get("harvests", []):
        y = int(h["date"][:4])
        if y == today.year:
            return []
        if y < today.year and (y not in firsts or h["date"] < firsts[y]):
            firsts[y] = h["date"]
    return [{"year": y, "date": firsts[y]} for y in sorted(firsts, reverse=True)]


def dd_basis(v: dict, seasons: list[dict], today: date) -> tuple[str, date, str]:
    """Where the degree days start: this year's full bloom when it is logged and an earlier year has one too, else Jan 1."""
    bloom = bloom_dates(v).get(today.year)
    if bloom and bloom <= today and any(s.get("dd_bloom") for s in seasons):
        return "bloom", bloom, "dd_bloom"
    return "jan1", date(today.year, 1, 1), "dd_first"


def harvest_dd(v: dict, seasons: list[dict], daily: dict, today: date) -> dict | None:
    """Experimental. Degree days (50 F) to the first pick of each earlier year, counted from full bloom when logged
    (else Jan 1), and where this year stands against them."""
    basis, start, key = dd_basis(v, seasons, today)
    years = [{"year": s["year"], "dd": round(s[key])} for s in seasons if s.get(key)]
    if not years or (basis == "jan1" and not _full_year_data(daily, today.year)):
        return None
    usual = round(mean([y["dd"] for y in years]))
    mine = [h["date"] for h in v.get("harvests", []) if h["date"].startswith(str(today.year))]
    this_pick = round(degree_days(daily, start, date.fromisoformat(min(mine)), 50, 86)) if mine else None
    now = round(degree_days(daily, start, today - timedelta(days=1), 50, 86))
    return {"basis": basis, "from": start.isoformat(), "years": sorted(years, key=lambda y: -y["year"]), "usual": usual, "now": now,
            "to_go": None if this_pick is not None else max(0, usual - now), "this_pick": this_pick}


def add_year(d: date, years: int = 1) -> date:
    try:
        return d.replace(year=d.year + years)
    except ValueError:  # Feb 29
        return d.replace(year=d.year + years, day=28)


def roll_expected(exp: date | None, today: date, harvests: list[dict]) -> date | None:
    """A tree or bush is picked every year: once this year's harvest has come and gone, expect next year's.

    The date rolls on when it is more than 45 days past, or when a pick was logged around it and the picking has
    been over for two weeks."""
    if exp is None:
        return None
    picks = sorted(h["date"] for h in harvests)
    while exp < today:
        near = [x for x in picks if x[:4] == str(exp.year) and x >= (exp - timedelta(days=45)).isoformat()]
        over = bool(near) and today > date.fromisoformat(near[-1]) + timedelta(days=14)
        if today > exp + timedelta(days=45) or over:
            exp = add_year(exp)
        else:
            break
    return exp


MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
PARTS = ("early", "mid", "late")


def _eom(y: int, m: int) -> int:
    return (date(y + (m == 12), m % 12 + 1, 1) - timedelta(days=1)).day


def window_clean(w: Any) -> dict | None:
    """A usual harvest window like late July to early August: {fm, fp, tm, tp}, or None when it is not set."""
    if not w:
        return None
    try:
        out = {"fm": int(w["fm"]), "fp": str(w["fp"]).lower(), "tm": int(w["tm"]), "tp": str(w["tp"]).lower()}
    except (KeyError, TypeError, ValueError):
        raise ValueError("Pick the month and early, mid or late for both ends of the harvest")
    if not (1 <= out["fm"] <= 12 and 1 <= out["tm"] <= 12) or out["fp"] not in PARTS or out["tp"] not in PARTS:
        raise ValueError("Pick the month and early, mid or late for both ends of the harvest")
    return out


def window_text(w: dict) -> str:
    a, b = f'{w["fp"].capitalize()} {MONTHS[w["fm"] - 1]}', f'{w["tp"]} {MONTHS[w["tm"] - 1]}'
    if (w["fm"], w["fp"]) == (w["tm"], w["tp"]):
        return a
    if w["fm"] == w["tm"]:
        return f'{w["fp"].capitalize()} to {w["tp"]} {MONTHS[w["fm"] - 1]}'
    return f"{a} to {b}"


def window_dates(w: dict, year: int) -> tuple[date, date]:
    """Start and end of the window for the harvest that begins in `year` (it may run into the next year)."""
    start = date(year, w["fm"], {"early": 1, "mid": 11, "late": 21}[w["fp"]])
    end_year = year + (1 if (w["tm"], PARTS.index(w["tp"])) < (w["fm"], PARTS.index(w["fp"])) else 0)
    end = date(end_year, w["tm"], {"early": 10, "mid": 20, "late": _eom(end_year, w["tm"])}[w["tp"]])
    return start, end


def window_status(w: dict | None, today: date) -> dict | None:
    """Where the usual harvest window stands: in season now, or the next time it opens. No year needed."""
    if not w:
        return None
    for yr in (today.year - 1, today.year):
        start, end = window_dates(w, yr)
        if start <= today <= end:
            return {"text": window_text(w), "state": "now", "start": start.isoformat(), "end": end.isoformat(), "days": 0}
    start, end = window_dates(w, today.year)
    if start < today:
        start, end = window_dates(w, today.year + 1)
    return {"text": window_text(w), "state": "ahead", "start": start.isoformat(), "end": end.isoformat(), "days": (start - today).days}


def project(v: dict, seasons: list[dict], daily: dict, today: date, alive: int, perennial: bool | None = None) -> dict | None:
    if not seasons:
        return None
    if perennial is None:
        perennial = v["kind"] == "tree"
    ypp = mean([s["yield_per_plant"] for s in seasons])
    method, proj = "", None
    if not perennial:
        days = [s["days_to_first"] for s in seasons if s["days_to_first"] is not None]
        if days:
            proj = date.fromisoformat(v["planted"]) + timedelta(days=round(mean(days)))
            method = "days from planting"
    else:
        basis, start, key = dd_basis(v, seasons, today)
        dds = [s[key] for s in seasons if s.get(key)]
        if dds and (basis == "bloom" or _full_year_data(daily, today.year)):
            target = mean(dds)
            now = degree_days(daily, start, today - timedelta(days=1), 50, 86)
            rate = recent_dd_rate(daily, today, 14, 50, 86)
            if now >= target:
                proj, method = today, "degree days" + (" from bloom" if basis == "bloom" else "")
            elif rate > 0.5:
                proj, method = today + timedelta(days=math.ceil((target - now) / rate)), "degree days" + (" from bloom" if basis == "bloom" else "")
    if proj is None:
        doy = round(mean([s["doy"] for s in seasons]))
        proj, method = date(today.year, 1, 1) + timedelta(days=doy - 1), "calendar date"
    if perennial:
        # the season is over once the usual date is well past: look ahead to next year's
        usual = date(today.year, 1, 1) + timedelta(days=round(mean([s["doy"] for s in seasons])) - 1)
        if today > usual + timedelta(days=45):
            proj, method = date(today.year + 1, 1, 1) + timedelta(days=round(mean([s["doy"] for s in seasons])) - 1), "calendar date"
    vs_last = proj.timetuple().tm_yday - seasons[-1]["doy"]
    return {"date": proj.isoformat(), "days_until": (proj - today).days,
            "basis_seasons": len(seasons), "method": method, "vs_last_days": vs_last,
            "yield_per_plant": round(ypp, 1), "yield_total": round(ypp * max(1, alive), 1)}


# ---- adjuncts and pH -------------------------------------------------------
def adjunct_status(atype: dict, entries: list[dict], today: date) -> dict:
    mine = [e for e in entries if e["type"] == atype["key"]]
    last = latest(mine)
    count = len([e for e in mine if e["date"][:4] == str(today.year)])
    out = {"key": atype["key"], "name": atype["name"], "per_year": atype.get("per_year"), "as_needed": bool(atype.get("as_needed")),
           "interval_days": atype.get("interval_days"), "count": count, "last": last,
           "days_since": days_since(last["date"], today) if last else None, "due_in": None}
    if atype.get("as_needed"):
        out.update(level="ok" if count else "none", label=f"{count} this year" if count else "As needed")
    elif atype.get("interval_days"):
        if not last:
            out.update(level="none", label="Not applied yet")
        else:
            due = atype["interval_days"] - out["days_since"]
            out["due_in"] = due
            if due > 14:
                out.update(level="ok", label=f"Next in {due} d")
            elif due > 0:
                out.update(level="warn", label=f"Due in {due} d")
            elif due == 0:
                out.update(level="warn", label="Due today")
            else:
                out.update(level="warn", label=f"Overdue {-due} d")
    else:
        n = atype.get("per_year") or 1
        out["label"] = f"{count} of {n}"
        out["level"] = "ok" if count >= n else ("warn" if count > 0 else "none")
    return out


# ---- long countdowns and frost ---------------------------------------------------
def _add_months(d: date, n: int) -> date:
    y, mo = divmod(d.month - 1 + n, 12)
    y += d.year
    mo += 1
    day = d.day
    while True:
        try:
            return date(y, mo, day)
        except ValueError:
            day -= 1


def ymd_parts(frm: date, to: date) -> tuple[int, int, int]:
    """Whole calendar years, months and days from `frm` up to `to` (to >= frm)."""
    months = (to.year - frm.year) * 12 + (to.month - frm.month)
    if _add_months(frm, months) > to:
        months -= 1
    rest = (to - _add_months(frm, months)).days
    return months // 12, months % 12, rest


def ymd_text(frm: date, to: date, short: bool = False) -> str | None:
    if to < frm:
        return None
    y, mo, d = ymd_parts(frm, to)
    if short:
        bits = [f"{y} y" if y else "", f"{mo} mo" if mo else "", f"{d} d" if d or not (y or mo) else ""]
    else:
        bits = [f"{y} year{'s' if y != 1 else ''}" if y else "", f"{mo} month{'s' if mo != 1 else ''}" if mo else "",
                f"{d} day{'s' if d != 1 else ''}" if d or not (y or mo) else ""]
    return " ".join(b for b in bits if b)


def md_date(md: str, year: int) -> date:
    m, d = (int(x) for x in md.split("-"))
    try:
        return date(year, m, d)
    except ValueError:
        return date(year, m, 28)


def frost_status(last_md: str, first_md: str, today: date) -> dict | None:
    """One countdown at a time: last spring frost until it has passed, then first fall frost."""
    last, first = md_date(last_md, today.year), md_date(first_md, today.year)
    if today <= last:
        return {"event": "last", "date": last.isoformat(), "days": (last - today).days}
    if today < first:
        return {"event": "first", "date": first.isoformat(), "days": (first - today).days}
    return None


def rule_harvest_date(rule: dict, planted: date, first_frost_md: str) -> date:
    """Harvest set by the first fall frost: N days after it, in the `year_offset`-th year after planting."""
    frost = md_date(first_frost_md, planted.year + int(rule.get("year_offset", 1)))
    return frost + timedelta(days=int(rule.get("after_first_frost_days", 21)))
