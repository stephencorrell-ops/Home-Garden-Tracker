"""Reminders from your own notes, a look back at each year, and frost / heat alerts from a forecast.
Pure functions with no Home Assistant imports, so the web app and Home Assistant share them."""
from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from . import season as season_mod

NOTE_NEW_DAYS = 14          # a note you just wrote is not a reminder yet
LEAD_DAYS = 30              # remind this long before a planting window opens
TREE_WINDOW = ((2, 15), (4, 30))    # trees: the weeks before bloom
OTHER_WINDOW = ((3, 1), (6, 1))     # crops with no planting window of their own
HEAT_F = 95.0
LOOKAHEAD = 3               # days of forecast an alert looks at, today included
HEAT_BOLTS = {"lettuce", "spinach", "pea", "cilantro", "broccoli", "cauliflower", "radish", "cabbage"}
HEAT_BLOSSOMS = {"tomato", "pepper", "jalapeno", "habanero", "eggplant"}


def _iso(d: date) -> str:
    return d.isoformat()


def _fmt(d: date) -> str:
    return f"{d.strftime('%b')} {d.day}"


def _window(key: str, kind: str, today: date, last_md: str, first_md: str, crop_days: dict) -> tuple[date, date] | None:
    """The next planting window for this plant that has not closed yet."""
    for year in (today.year, today.year + 1):
        if kind == "tree":
            w = (date(year, *TREE_WINDOW[0]), date(year, *TREE_WINDOW[1]))
        else:
            e = crop_days.get(key)
            spec = (int(e["days"]), e["hardy"]) if e else season_mod.CROPS.get(key)
            w = season_mod.window(key, last_md, first_md, year, spec) if spec else (date(year, *OTHER_WINDOW[0]), date(year, *OTHER_WINDOW[1]))
        if w and w[1] >= w[0] and w[1] >= today:
            return w
    return None


def due_notes(varieties: list[dict], names: dict[str, str], garden_names: dict[str, str], today: date,
              last_md: str, first_md: str, crop_days: dict) -> list[dict]:
    """Notes you wrote for next year, shown when that plant's planting window is open or about to open.
    Past plants count too: their notes are kept for next year."""
    out = []
    for v in varieties:
        for r in v.get("reviews", []):
            snooze = r.get("snooze_until")
            if snooze and snooze > _iso(today):
                continue
            added = r.get("added")
            if added and (today - date.fromisoformat(added)).days < NOTE_NEW_DAYS:
                continue
            w = _window(v["species"], v.get("kind", ""), today, last_md, first_md, crop_days)
            if w is None:
                continue
            start, end = w
            opens = start <= today <= end
            soon = 0 < (start - today).days <= LEAD_DAYS
            if not (opens or soon) or r.get("done") == start.year:
                continue
            tree = v.get("kind") == "tree"
            if opens:
                label = f"Before bloom, until {_fmt(end)}" if tree else f"Planting window is open until {_fmt(end)}"
            else:
                label = f"Opens {_fmt(start)}"
            out.append({"id": r["id"], "v": v["id"], "name": v["name"], "species_name": names.get(v["species"]) or v.get("species_name") or v["species"],
                        "garden_name": garden_names.get(v.get("garden", ""), ""), "note": r["notes"], "year": r["year"],
                        "state": "open" if opens else "soon", "label": label, "cycle": start.year,
                        "from": _iso(start), "by": _iso(end), "archived": bool(v.get("archived"))})
    out.sort(key=lambda x: (x["state"] != "open", x["from"], x["name"].lower()))
    return out


# ---- frost and heat alerts ----------------------------------------------------------------

def _when(d: date, today: date, night: bool) -> str:
    n = (d - today).days
    if n == 0:
        return "tonight" if night else "today"
    if n == 1:
        return "tomorrow night" if night else "tomorrow"
    return d.strftime("%A")


def _runs(days: list[dict], hit) -> list[list[dict]]:
    runs: list[list[dict]] = []
    for d in days:
        if hit(d):
            if runs and (date.fromisoformat(d["date"]) - date.fromisoformat(runs[-1][-1]["date"])).days == 1:
                runs[-1].append(d)
            else:
                runs.append([d])
    return runs


def _list(names: list[str]) -> str:
    names = list(dict.fromkeys(names))
    if len(names) <= 1:
        return "".join(names)
    return ", ".join(names[:-1]) + " and " + names[-1]


def forecast_alerts(forecast: list[dict], today: date, plants: list[dict], frost_f: float, heat_f: float,
                    acked: list[str] | set[str]) -> list[dict]:
    """Frost and heat in the next few days, and which of your plants it matters to.
    `plants` is one entry per planting in the ground: {id, name, species, hardy, count}.
    `hardy` is tender, half, hardy, fall or None (unknown, treated as tender)."""
    end = today + timedelta(days=LOOKAHEAD - 1)
    days = sorted((d for d in forecast if today <= date.fromisoformat(d["date"]) <= end), key=lambda d: d["date"])
    acked = set(acked)
    alerts: list[dict] = []

    def hurt_by_frost(p: dict, low: float) -> bool:
        h = p.get("hardy") or "tender"
        return h == "tender" and low <= frost_f or h == "half" and low <= frost_f - 4

    for run in _runs(days, lambda d: d.get("lo") is not None and d["lo"] <= frost_f):
        low = min(d["lo"] for d in run)
        first = date.fromisoformat(run[0]["date"])
        hurt = [p for p in plants if hurt_by_frost(p, low)]
        if not hurt:
            continue
        safe = [p["name"] for p in plants if p not in hurt]
        aid = f"frost:{run[0]['date']}"
        text = "Cover or bring in: " + ", ".join(f"{p['name']} ({p['count']})" for p in hurt) + "."
        if safe:
            text += f" {_list(safe[:3])} {'is' if len(set(safe[:3])) == 1 else 'are'} fine."
        alerts.append({"id": aid, "kind": "frost", "date": run[0]["date"], "dates": [d["date"] for d in run], "value": round(low),
                       "title": f"Frost {_when(first, today, True)}: low of {round(low)}°F", "text": text,
                       "plants": [{"id": p["id"], "name": p["name"], "count": p["count"]} for p in hurt], "acked": aid in acked})

    for run in _runs(days, lambda d: d.get("hi") is not None and d["hi"] >= heat_f):
        high = max(d["hi"] for d in run)
        first, last = date.fromisoformat(run[0]["date"]), date.fromisoformat(run[-1]["date"])
        if not plants:
            continue
        span = first.strftime("%A") if first == last else f"{first.strftime('%A')} to {last.strftime('%A')}"
        bolts = [p["name"] for p in plants if p["species"] in HEAT_BOLTS]
        drops = [p["name"] for p in plants if p["species"] in HEAT_BLOSSOMS]
        text = "Water deeply the evening before."
        if bolts:
            text += f" {_list(bolts)} may bolt."
        if drops:
            text += f" {_list(drops)} may drop blossoms."
        aid = f"heat:{run[0]['date']}"
        alerts.append({"id": aid, "kind": "heat", "date": run[0]["date"], "dates": [d["date"] for d in run], "value": round(high),
                       "title": f"Heat {span}: highs of {round(high)}°F", "text": text, "plants": [], "acked": aid in acked})
    alerts.sort(key=lambda a: (a["date"], a["kind"]))
    return alerts


# ---- a look back at each year ---------------------------------------------------------------

def year_summaries(varieties: list[dict], names: dict[str, str], garden_names: dict[str, str], frost_years: list[dict],
                   today: date) -> dict[str, dict]:
    """What happened in each year you have records for, newest first. The current year counts as still in progress until
    November, so it is not compared with a finished year."""
    frost = {str(f["year"]): f for f in frost_years}
    years: dict[str, dict] = {}

    def y(k: str) -> dict:
        return years.setdefault(k, {"lbs": 0.0, "crops": {}, "gardens": {}, "picks": 0, "sprays": 0, "feeds": 0, "lost": 0, "notes": 0})

    for v in varieties:
        key = v["species"]
        nm = names.get(key) or v.get("species_name") or key
        gname = garden_names.get(v.get("garden", ""), "") or "Elsewhere"
        for h in v.get("harvests", []):
            e = y(h["date"][:4])
            e["lbs"] += h["lbs"]
            e["picks"] += 1
            c = e["crops"].setdefault(key, {"key": key, "name": nm, "lbs": 0.0})
            c["lbs"] += h["lbs"]
            e["gardens"][gname] = e["gardens"].get(gname, 0.0) + h["lbs"]
        for s in v.get("sprays", []):
            y(s["date"][:4])["sprays"] += 1
        for f in v.get("fertilizations", []):
            y(f["date"][:4])["feeds"] += 1
        for r in v.get("reviews", []):
            y(str(r["year"]))["notes"] += 1
        for p in v.get("plants", []):
            if p.get("status") in ("dead", "pulled") and p.get("status_date"):
                y(p["status_date"][:4])["lost"] += 1 if p["status"] == "dead" else 0
    out: dict[str, dict] = {}
    ordered = sorted(years, reverse=True)
    for k in ordered:
        e = years[k]
        if not (e["lbs"] or e["sprays"] or e["feeds"] or e["notes"] or e["lost"]):
            continue
        open_year = int(k) == today.year and (today.month, today.day) < (11, 1)
        prev = None if open_year else years.get(str(int(k) - 1))
        prev_lbs = round(prev["lbs"], 1) if prev and prev["lbs"] else None
        crops = []
        for c in sorted(e["crops"].values(), key=lambda c: -c["lbs"]):
            before = prev["crops"].get(c["key"], {}).get("lbs") if prev else None
            crops.append({"key": c["key"], "name": c["name"], "lbs": round(c["lbs"], 1),
                          "prev": round(before, 1) if before else None})
        # the biggest drop from last year, among crops that gave at least 5 lb then
        drop = None
        if prev:
            for pk, pc in prev["crops"].items():
                if pc["lbs"] < 5:
                    continue
                now = e["crops"].get(pk, {}).get("lbs", 0.0)
                pct = round((now - pc["lbs"]) / pc["lbs"] * 100)
                if pct <= -20 and (drop is None or pct < drop["pct"]):
                    drop = {"name": pc["name"], "pct": pct}
        best = max(e["gardens"].items(), key=lambda kv: kv[1]) if e["gardens"] else None
        f = frost.get(k)
        out[k] = {"year": int(k), "lbs": round(e["lbs"], 1), "prev_lbs": prev_lbs,
                  "change_pct": round((e["lbs"] - prev_lbs) / prev_lbs * 100) if prev_lbs else None,
                  "crops": crops, "picks": e["picks"], "sprays": e["sprays"], "feeds": e["feeds"], "lost": e["lost"], "notes": e["notes"],
                  "best_garden": {"name": best[0], "lbs": round(best[1], 1)} if best and len(e["gardens"]) > 1 else None,
                  "drop": drop, "in_progress": open_year, "last_spring_frost": f and f.get("last_spring"), "first_fall_frost": f and f.get("first_fall")}
    return out
