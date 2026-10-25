"""Watering: which drip line to buy and how to lay it for each row, run times per garden, and fertigation amounts.

Each garden is one irrigation zone, so every line in it runs together and the garden's run time is the limit.
The run time is set by the thirstiest crop, given about one gallon an hour to each plant, and every other crop gets
the line that delivers what it needs in that same time with the least to spare.

The drip line is 1/2 inch (0.600 in inside, 0.700 in outside) pressure compensating polyethylene with the emitters
built in, as sold by Drip Depot. Flow rates, spacings and roll lengths below are the ones to check against what you
order (DRIP_FLOWS, DRIP_SPACINGS, ROLLS). The longest run a line can take depends on pressure, slope and the
emitters, and Drip Depot publishes it as a chart image, so it is the garden's "most water in one line" setting,
which you can change. Water needs per crop are rough starting figures for a hot dry summer and are editable.
Pure functions, no Home Assistant imports."""
from __future__ import annotations

import math
from typing import Any

DRIP_FLOWS = (0.5, 1.0)            # gallons per hour per emitter
DRIP_SPACINGS = (9, 12, 18, 24)    # inches between emitters
ROLLS = (100, 500)                 # feet in a roll
SHORT_OK = 0.85                    # a line that delivers at least this share of a crop's need in the run time is good enough
WASTE = 1.05                       # allow for cuts and fittings when ordering
GAL_PER_IN_SQFT = 0.6234           # one inch of water on one square foot
ANCHOR_PLANT_GPH = 1.0             # the run time is set by giving the thirstiest crop about this much per plant
DEFAULT_MAX_LINE_GPH = 200.0       # most water carried by one run of 1/2 inch line, a cautious figure

# soil -> (name, most gph per emitter, widest emitter spacing in inches, note)
SOILS: dict[str, tuple[str, float, int, str]] = {
    "sand": ("Sand", 1.0, 12, "Water drains straight down, so keep emitters close and water often in shorter runs."),
    "sandy_loam": ("Sandy loam", 1.0, 18, "Drains quickly; the water spreads about a foot sideways."),
    "loam": ("Loam", 1.0, 24, "Takes 1 gph emitters well."),
    "silt_loam": ("Silt loam", 1.0, 24, "Takes 1 gph emitters, but let the top dry between waterings."),
    "clay_loam": ("Clay loam", 1.0, 24, "Takes 1 gph emitters; water spreads sideways well."),
    "clay": ("Clay", 0.5, 24, "Soaks in slowly, so use 1/2 gph emitters (closer together if you need more water) to avoid puddling and runoff."),
}
DEFAULT_SOIL = "clay_loam"

# crop -> inches of water a week in midsummer, soil-dependent and editable per garden
WATER_IN_WEEK: dict[str, float] = {
    "tomato": 1.5, "pepper": 1.0, "jalapeno": 1.0, "habanero": 1.0, "cucumber": 1.5, "pea": 1.0, "bean": 1.0,
    "garlic": 1.0, "onion": 1.0, "onion_red": 1.0, "onion_white": 1.0, "onion_sweet": 1.0, "carrot": 1.0, "potato": 1.5,
    "horseradish": 1.0, "watermelon": 1.5, "cantaloupe": 1.5, "pumpkin": 1.5, "cabbage": 1.25, "lettuce": 1.0,
    "cauliflower": 1.25,
}
DEFAULT_WATER_IN_WEEK = 1.0
# crop -> nitrogen in parts per million for fertigation (editable). Fruiting crops take more than greens and roots.
PPM_N: dict[str, float] = {"tomato": 100.0, "pepper": 75.0, "cucumber": 100.0}
DEFAULT_PPM_N = 100.0
METHODS = {"drip": "Drip", "sprinkler": "Sprinklers"}


class IrrigationError(ValueError):
    pass


DEFAULT_PUMP = {"name": "Dosatron D14MZ2", "min_ratio": 50, "max_ratio": 500, "min_gpm": 0.05, "max_gpm": 14.0,
                "tank_gal": 4.0, "flush_min": 5.0}


def default_acid() -> dict:
    return {"ph": None, "ta_ppm": None, "target_ph": 5.5, "strength_pct": 35.0, "sg": None, "tested": None, "base": "kbic"}


def default_lime() -> dict:
    return {"target_ph": 6.5, "type": "calcitic", "depth_in": 6.0, "tilled": True, "ph": None, "lb_per_unit": None}


def default_fert() -> dict:
    """The Dosatron D14MZ2 and two starting mixes: a high nitrogen one for growth, then MasterBlend 4-18-38 with
    calcium nitrate and Epsom salt for fruiting. Everything here is a starting value and can be edited."""
    return {
        "every_days": 14, "active": "growth",
        "pumps": {"pump1": dict(DEFAULT_PUMP)}, "tank_pump": {},
        "mixes": {
            "growth": {"name": "Growth (high nitrogen)", "ppm_n": None, "components": [
                {"name": "High nitrogen 20-10-20", "n": 20.0, "p": 10.0, "k": 20.0, "ca": 0.0, "mg": 0.0, "parts": 1.0, "tank": "A"}]},
            "fruiting": {"name": "Fruiting (MasterBlend tomato)", "ppm_n": None, "components": [
                {"name": "MasterBlend 4-18-38", "n": 4.0, "p": 18.0, "k": 38.0, "ca": 0.0, "mg": 0.0, "parts": 2.0, "tank": "B"},
                {"name": "Calcium nitrate 15.5-0-0", "n": 15.5, "p": 0.0, "k": 0.0, "ca": 19.0, "mg": 0.0, "parts": 2.0, "tank": "A"},
                {"name": "Epsom salt", "n": 0.0, "p": 0.0, "k": 0.0, "ca": 0.0, "mg": 9.8, "parts": 1.0, "tank": "B"}]},
        },
    }


def blank() -> dict:
    return {"method": "drip", "soil": DEFAULT_SOIL, "per_week": 3, "run_min": None, "sprinkler_in_hr": 0.75,
            "sprinkler_gpm": None, "max_line_gph": DEFAULT_MAX_LINE_GPH, "crops": {},
            "fert": default_fert(), "acid": default_acid(), "lime": default_lime()}


def _num(v: Any, name: str, lo: float, hi: float) -> float:
    try:
        x = float(v)
    except (TypeError, ValueError):
        raise IrrigationError(f"{name} must be a number") from None
    if not lo <= x <= hi or x != x:
        raise IrrigationError(f"{name} must be between {lo:g} and {hi:g}")
    return x


def validate_settings(method: Any = None, soil: Any = None, per_week: Any = None, run_min: Any = "keep", sprinkler_in_hr: Any = None,
                      sprinkler_gpm: Any = "keep", max_line_gph: Any = None) -> dict:
    out: dict[str, Any] = {}
    if method is not None:
        if method not in METHODS:
            raise IrrigationError("Method must be drip or sprinklers")
        out["method"] = method
    if soil is not None:
        if soil not in SOILS:
            raise IrrigationError("Pick a soil from the list")
        out["soil"] = soil
    if per_week is not None:
        out["per_week"] = int(_num(per_week, "Waterings per week", 1, 14))
    if run_min != "keep":  # empty means work it out
        out["run_min"] = None if run_min in (None, "", 0) else _num(run_min, "Run time", 1, 1440)
    if sprinkler_in_hr is not None:
        out["sprinkler_in_hr"] = _num(sprinkler_in_hr, "Sprinkler rate", 0.05, 10)
    if sprinkler_gpm != "keep":
        out["sprinkler_gpm"] = None if sprinkler_gpm in (None, "", 0) else _num(sprinkler_gpm, "Sprinkler flow", 0.1, 500)
    if max_line_gph is not None:
        out["max_line_gph"] = _num(max_line_gph, "Most water in one line", 10, 2000)
    return out


def validate_crop(water_in_week: Any = None, lines: Any = None, flow_gph: Any = "keep", emit_in: Any = "keep", ppm_n: Any = None) -> dict:
    out: dict[str, Any] = {}
    if water_in_week is not None:
        out["water_in_week"] = _num(water_in_week, "Water per week", 0.1, 6)
    if lines is not None:
        out["lines"] = int(_num(lines, "Drip lines per row", 1, 4))
    if flow_gph != "keep":  # empty goes back to the suggestion
        if flow_gph in (None, "", 0):
            out["flow_gph"] = None
        else:
            f = _num(flow_gph, "Emitter flow", 0.1, 10)
            if f not in DRIP_FLOWS:
                raise IrrigationError("Emitter flow must be " + " or ".join(f"{x:g}" for x in DRIP_FLOWS) + " gph")
            out["flow_gph"] = f
    if emit_in != "keep":
        if emit_in in (None, "", 0):
            out["emit_in"] = None
        else:
            e = int(_num(emit_in, "Emitter spacing", 1, 100))
            if e not in DRIP_SPACINGS:
                raise IrrigationError("Emitter spacing must be " + ", ".join(str(x) for x in DRIP_SPACINGS) + " inches")
            out["emit_in"] = e
    if ppm_n is not None:
        out["ppm_n"] = _num(ppm_n, "Nitrogen ppm", 1, 1000)
    return out


def validate_fert(every_days: Any = None, active: Any = None) -> dict:
    out: dict[str, Any] = {}
    if every_days is not None:
        out["every_days"] = int(_num(every_days, "Days between feedings", 1, 90))
    if active is not None:
        out["active"] = str(active)
    return out


def validate_injector(name: Any = None, min_ratio: Any = None, max_ratio: Any = None, min_gpm: Any = None, max_gpm: Any = None,
                      tank_gal: Any = None, flush_min: Any = None) -> dict:
    out: dict[str, Any] = {}
    if name is not None:
        out["name"] = str(name).strip()[:60] or "Injector"
    if min_ratio is not None:
        out["min_ratio"] = _num(min_ratio, "Strongest dilution (1:N)", 1, 5000)
    if max_ratio is not None:
        out["max_ratio"] = _num(max_ratio, "Weakest dilution (1:N)", 1, 5000)
    if min_gpm is not None:
        out["min_gpm"] = _num(min_gpm, "Lowest flow", 0, 1000)
    if max_gpm is not None:
        out["max_gpm"] = _num(max_gpm, "Highest flow", 0.01, 1000)
    if tank_gal is not None:
        out["tank_gal"] = _num(tank_gal, "Most solution to mix", 0.1, 1000)
    if flush_min is not None:
        out["flush_min"] = _num(flush_min, "Flush time", 0, 120)
    return out


def validate_mix(name: Any = None, ppm_n: Any = "keep") -> dict:
    out: dict[str, Any] = {}
    if name is not None:
        n = str(name).strip()[:60]
        if not n:
            raise IrrigationError("A mix needs a name")
        out["name"] = n
    if ppm_n != "keep":  # empty means work it out from the plants
        out["ppm_n"] = None if ppm_n in (None, "", 0) else _num(ppm_n, "Nitrogen ppm", 1, 1000)
    return out


def validate_component(name: Any = None, n: Any = None, p: Any = None, k: Any = None, ca: Any = None, mg: Any = None,
                       parts: Any = None, tank: Any = None) -> dict:
    out: dict[str, Any] = {}
    if name is not None:
        nm = str(name).strip()[:60]
        if not nm:
            raise IrrigationError("A fertilizer needs a name")
        out["name"] = nm
    for key, v, label in (("n", n, "Nitrogen"), ("p", p, "Phosphate"), ("k", k, "Potash"), ("ca", ca, "Calcium"), ("mg", mg, "Magnesium")):
        if v is not None:
            out[key] = _num(v, label + " percent", 0, 100)
    if parts is not None:
        out["parts"] = _num(parts, "Parts by weight", 0.01, 1000)
    if tank is not None:
        t = str(tank).strip().upper()[:1]
        if not t.isalpha():
            raise IrrigationError("The tank is a letter, like A or B")
        out["tank"] = t
    return out


def validate_acid(ph: Any = None, ta_ppm: Any = None, target_ph: Any = None, strength_pct: Any = None, sg: Any = "keep",
                  base: Any = None) -> dict:
    out: dict[str, Any] = {}
    if base is not None:
        if base not in BASES:
            raise IrrigationError("Pick a base from the list")
        out["base"] = base
    if ph is not None:
        out["ph"] = _num(ph, "Water pH", 3, 12)
    if ta_ppm is not None:
        out["ta_ppm"] = _num(ta_ppm, "Total alkalinity (ppm as calcium carbonate)", 0, 2000)
    if target_ph is not None:
        out["target_ph"] = _num(target_ph, "Target pH", 3, 9)
    if strength_pct is not None:
        out["strength_pct"] = _num(strength_pct, "Acid strength", 1, 100)
    if sg != "keep":  # empty means work it out from the strength
        out["sg"] = None if sg in (None, "", 0) else _num(sg, "Specific gravity", 0.9, 2.0)
    return out


def fert_of(f: dict | None) -> dict:
    """The fertigation settings with anything missing filled in from the defaults."""
    d = default_fert()
    if not f or "mixes" not in f:
        return d
    pumps = {k: {**DEFAULT_PUMP, **p} for k, p in (f.get("pumps") or {}).items()}
    if not pumps:  # an older save with a single injector
        pumps = {"pump1": {**DEFAULT_PUMP, **(f.get("injector") or {})}}
    first = next(iter(pumps))
    out = {"every_days": f.get("every_days") or d["every_days"], "active": f.get("active") or d["active"], "pumps": pumps,
           "tank_pump": {t: k for t, k in (f.get("tank_pump") or {}).items() if k in pumps}, "mixes": {}}
    out["first_pump"] = first
    for k, m in f["mixes"].items():
        out["mixes"][k] = {"name": m.get("name") or k, "ppm_n": m.get("ppm_n"), "components": [dict(c) for c in m.get("components") or []]}
    return out


def pump_for(f: dict, tank: str) -> tuple[str, dict]:
    """Which pump a stock tank ("A", "B" and so on, or "acid") is run through."""
    k = f["tank_pump"].get(tank) or f.get("first_pump") or next(iter(f["pumps"]))
    return k, f["pumps"][k]


def settings_for(s: dict | None) -> dict:
    base = blank()
    if s:
        base.update({k: v for k, v in s.items() if k not in ("fert", "crops", "acid")})
        base["acid"] = {**default_acid(), **(s.get("acid") or {})}
        base["lime"] = {**default_lime(), **(s.get("lime") or {})}
        base["fert"] = fert_of(s.get("fert"))
        base["crops"] = {k: dict(v) for k, v in (s.get("crops") or {}).items()}
    return base


def rolls_for(feet: float) -> list[dict]:
    """The rolls that cover `feet` (with an allowance for cuts), fewest and least spare line."""
    need = math.ceil(feet * WASTE)
    big, small = max(ROLLS), min(ROLLS)
    n_big = need // big
    rest = need - n_big * big
    n_small = math.ceil(rest / small) if rest > 0 else 0
    if n_small * small >= big:  # a whole big roll is no more than the small ones
        n_big, n_small = n_big + 1, 0
    return [{"len": ln, "count": n} for ln, n in ((big, n_big), (small, n_small)) if n]


def label(flow: float, emit_in: float) -> str:
    return f"{flow:g} gph at {emit_in:g} in"


def _options(soil: tuple, plant_in: float, lines: int, flows: tuple, spaces: tuple) -> list[dict]:
    """Every line that suits the soil and puts at least one emitter beside each plant."""
    top = max(float(min(spaces)), min(float(plant_in), float(soil[2])))
    out = []
    for f in flows:
        if f > soil[1] + 1e-9:
            continue
        for e in spaces:
            if e > top + 1e-9:
                continue
            out.append({"flow": f, "emit_in": e, "rate": lines * f * 12 / e,  # gallons an hour for each foot of row
                        "divides": abs(plant_in / e - round(plant_in / e)) < 1e-6 and round(plant_in / e) >= 1})
    return out


def _lines_for(cfg: dict, pattern: str, row_in: int) -> int:
    if cfg.get("lines"):
        return int(cfg["lines"])
    return 2 if pattern == "grid" and row_in >= 30 else 1


def plan(layout: dict, settings: dict | None, names: dict[str, str] | None = None, soil_ph: float | None = None) -> dict:
    """Watering for a laid-out garden. `layout` is the result of layout.plan."""
    st = settings_for(settings)
    soil = SOILS.get(st["soil"], SOILS[DEFAULT_SOIL])
    base = {"configured": bool(layout and layout.get("configured")), "method": st["method"], "methods": METHODS,
            "soil": st["soil"], "soils": [{"key": k, "name": v[0], "max_gph": v[1], "note": v[3]} for k, v in SOILS.items()],
            "soil_note": soil[3], "per_week": st["per_week"], "flows": list(DRIP_FLOWS), "spacings": list(DRIP_SPACINGS),
            "rolls": list(ROLLS), "max_line_gph": st["max_line_gph"], "sprinkler_in_hr": st["sprinkler_in_hr"],
            "sprinkler_gpm": st["sprinkler_gpm"], "fert_settings": fert_of(st["fert"]),
            "lime": lime(st["lime"], st["soil"], soil_ph, (layout.get("width_ft", 0) * layout.get("length_ft", 0)) if layout and layout.get("configured") else None)}
    if not base["configured"]:
        return base
    row_in = layout["row_in"]
    crops_in = {c["key"]: c for c in layout["crops"]}
    info: dict[str, dict] = {}
    for key, c in crops_in.items():
        cfg = st["crops"].get(key) or {}
        info[key] = {"key": key, "name": c["name"], "pattern": c["pattern"], "spacing_in": c["spacing_in"],
                     "water_in_week": cfg.get("water_in_week") or WATER_IN_WEEK.get(key, DEFAULT_WATER_IN_WEEK),
                     "lines": _lines_for(cfg, c["pattern"], row_in), "ppm_n": cfg.get("ppm_n") or PPM_N.get(key, DEFAULT_PPM_N),
                     "pin_flow": cfg.get("flow_gph"), "pin_emit": cfg.get("emit_in"), "ft": c["feet"], "plants": c["plants"],
                     "custom_water": bool(cfg.get("water_in_week")), "custom_lines": bool(cfg.get("lines"))}
    for i in info.values():
        i["need_ft"] = i["water_in_week"] * row_in / 12 * GAL_PER_IN_SQFT  # gallons a week for each foot of row
        i["need_gal"] = round(i["need_ft"] * i["ft"], 1)
    area = layout["width_ft"] * layout["length_ft"]
    if st["method"] == "sprinkler":
        return _sprinkler(base, st, layout, list(info.values()), area)
    return _drip(base, st, layout, info, soil, row_in)


def _pick_options(i: dict, soil: tuple) -> list[dict]:
    opts = _options(soil, i["spacing_in"], i["lines"], DRIP_FLOWS, DRIP_SPACINGS)
    if i["pin_flow"] or i["pin_emit"]:
        pinned = [o for o in opts if (not i["pin_flow"] or o["flow"] == i["pin_flow"]) and (not i["pin_emit"] or o["emit_in"] == i["pin_emit"])]
        if not pinned:  # chosen by hand: the soil or plant spacing may argue against it, but the grower decides
            pinned = [{"flow": i["pin_flow"] or min(DRIP_FLOWS), "emit_in": i["pin_emit"] or max(DRIP_SPACINGS),
                       "rate": i["lines"] * (i["pin_flow"] or min(DRIP_FLOWS)) * 12 / (i["pin_emit"] or max(DRIP_SPACINGS)), "divides": True}]
        return pinned
    return opts


def _drip(base: dict, st: dict, layout: dict, info: dict, soil: tuple, row_in: int) -> dict:
    for i in info.values():
        i["opts"] = _pick_options(i, soil)
        for o in i["opts"]:
            o["hours"] = i["need_ft"] / o["rate"]
            ft_each = i["ft"] / i["plants"] if i["plants"] else i["spacing_in"] / 12  # feet of row for each plant
            o["plant_gph"] = o["rate"] * ft_each

    def baseline(i: dict) -> dict:  # about 1 gph for each plant, on an emitter that sits by every plant, spread widest
        pool = [o for o in i["opts"] if o["divides"]] or i["opts"]
        return min(pool, key=lambda o: (round(abs(o["plant_gph"] - ANCHOR_PLANT_GPH), 3), -o["emit_in"], -o["flow"]))

    auto = max(baseline(i)["hours"] for i in info.values()) if info else 0.0
    hours = st["run_min"] * st["per_week"] / 60 if st["run_min"] else auto
    for i in info.values():
        if i["pin_flow"] or i["pin_emit"]:
            best = baseline(i) if len(i["opts"]) > 1 else i["opts"][0]
        else:
            ok = [o for o in i["opts"] if o["hours"] <= hours / SHORT_OK + 1e-6]
            pool = [o for o in ok if o["divides"]] or ok
            if pool:  # least to spare: the slowest line that still gets the job done in time
                best = min(pool, key=lambda o: (-round(o["hours"], 2), -o["flow"], -o["emit_in"]))
            else:
                best = min(i["opts"], key=lambda o: (o["hours"], -o["flow"], -o["emit_in"]))
        i["best"] = best
        order = sorted(i["opts"], key=lambda o: (not o["divides"], abs(o["hours"] - hours)))
        i["alts"] = [{"label": label(o["flow"], o["emit_in"]), "minutes": round(o["hours"] * 60 / st["per_week"])}
                     for o in order if o is not best][:3]
    per = st["per_week"]
    run_min = round(hours * 60 / per, 1)
    crops, rows_out, order_ft, order_n = [], [], {}, {}
    total_gph = 0.0
    line_flag = []
    seg_by_crop: dict[str, dict] = {k: {"emitters": 0, "gph": 0.0} for k in info}
    for r in layout["rows"]:
        items, per_line, lines_n = [], 0.0, 1
        for sg in r["segments"]:
            i = info[sg["crop"]]
            b = i["best"]
            ft = sg["len_in"] / 12
            n_em = int(sg["len_in"] / b["emit_in"] + 1e-6)
            gph_line = n_em * b["flow"]
            lines_n = max(lines_n, i["lines"])
            per_line += gph_line
            items.append({"crop": sg["crop"], "name": sg["name"], "ft": round(ft, 1), "lines": i["lines"], "label": label(b["flow"], b["emit_in"]),
                          "gph": round(gph_line * i["lines"], 1)})
            key = (b["flow"], b["emit_in"])
            order_ft[key] = order_ft.get(key, 0.0) + ft * i["lines"]
            order_n[key] = order_n.get(key, 0) + n_em * i["lines"]
            seg_by_crop[sg["crop"]]["emitters"] += n_em * i["lines"]
            seg_by_crop[sg["crop"]]["gph"] += gph_line * i["lines"]
            total_gph += gph_line * i["lines"]
        if items:
            over = per_line > st["max_line_gph"] + 1e-6
            if over:
                line_flag.append(r["i"])
            rows_out.append({"i": r["i"], "items": items, "lines": lines_n, "line_gph": round(per_line, 1),
                             "gph": round(sum(it["gph"] for it in items), 1), "over": over})
    for i in info.values():
        b, s = i["best"], seg_by_crop[i["key"]]
        gal_watering = s["gph"] * run_min / 60
        gal_week = s["gph"] * hours
        crops.append({"key": i["key"], "name": i["name"], "pattern": i["pattern"], "spacing_in": i["spacing_in"], "ft": i["ft"],
                      "plants": i["plants"], "water_in_week": i["water_in_week"], "lines": i["lines"], "ppm_n": i["ppm_n"],
                      "custom_water": i["custom_water"], "custom_lines": i["custom_lines"],
                      "pinned": bool(i["pin_flow"] or i["pin_emit"]), "flow_gph": b["flow"], "emit_in": b["emit_in"],
                      "label": label(b["flow"], b["emit_in"]), "emitters": s["emitters"], "gph": round(s["gph"], 1),
                      "plant_gph": round(s["gph"] / i["plants"], 2) if i["plants"] else 0,
                      "gal_plant_watering": round(gal_watering / i["plants"], 2) if i["plants"] else 0,
                      "gal_week": round(gal_week, 1), "need_gal_week": i["need_gal"],
                      "pct": round(100 * gal_week / i["need_gal"]) if i["need_gal"] else None,
                      "short": gal_week < i["need_gal"] * 0.9, "over": gal_week > i["need_gal"] * 1.3, "alternatives": i["alts"]})
    crops.sort(key=lambda c: c["name"].lower())
    order = []
    for (f, e), ft in sorted(order_ft.items(), key=lambda kv: (-kv[0][0], kv[0][1])):
        order.append({"flow": f, "emit_in": e, "label": label(f, e), "feet": round(ft, 1), "order_ft": math.ceil(ft * WASTE),
                      "emitters": order_n[(f, e)], "rolls": rolls_for(ft)})
    gal_week = sum(c["gal_week"] for c in crops)
    ft = fert(st["fert"], crops, total_gph * run_min / 60, "drip", layout["width_ft"] * layout["length_ft"], run_min, total_gph / 60)
    return {**base, "run_min": run_min, "run_min_set": st["run_min"], "auto_run_min": round(auto * 60 / per, 1), "hours_week": round(hours, 2),
            "crops": crops, "rows": rows_out, "order": order, "waste": WASTE,
            "totals": {"gph": round(total_gph, 1), "gpm": round(total_gph / 60, 2), "gal_watering": round(total_gph * run_min / 60, 1),
                       "gal_week": round(gal_week, 1), "emitters": sum(o["emitters"] for o in order),
                       "feet": round(sum(o["feet"] for o in order), 1), "lines_over": line_flag},
            "fert": ft, "acid": _acid_for(st, total_gph * run_min / 60, run_min, ft)}


def _sprinkler(base: dict, st: dict, layout: dict, crops_in: list[dict], area: float) -> dict:
    need_in = max((i["water_in_week"] for i in crops_in), default=0.0)
    rate = st["sprinkler_in_hr"]
    hours = need_in / rate if rate else 0.0
    per = st["per_week"]
    run_min = round(hours * 60 / per, 1)
    gal_week = need_in * area * GAL_PER_IN_SQFT
    gpm = st["sprinkler_gpm"] or (round(gal_week / (hours * 60), 1) if hours else 0.0)
    crops = [{"key": i["key"], "name": i["name"], "water_in_week": i["water_in_week"], "ppm_n": i["ppm_n"], "plants": i["plants"],
              "custom_water": i["custom_water"], "pct": round(100 * need_in / i["water_in_week"]) if i["water_in_week"] else None}
             for i in sorted(crops_in, key=lambda i: i["name"].lower())]
    gal_watering = round(gal_week / per, 1)
    ft = fert(st["fert"], crops, gal_watering, "sprinkler", area, run_min, gpm)
    return {**base, "run_min": run_min, "run_min_set": None, "hours_week": round(hours, 2), "need_in_week": need_in, "crops": crops,
            "rows": [], "order": [], "totals": {"gph": round(gpm * 60, 1), "gpm": gpm, "gal_watering": gal_watering, "gal_week": round(gal_week, 1),
                                                "gpm_given": bool(st["sprinkler_gpm"]), "area_sqft": round(area, 1)},
            "fert": ft, "acid": _acid_for(st, gal_watering, run_min, ft)}


PK1, PK2, KW = 6.35, 10.33, 1e-14  # carbonic acid at 25 C
# sulfuric acid strength (% by weight) -> specific gravity, for working out how many equivalents are in a millilitre
SULFURIC_SG = ((0, 1.0), (10, 1.069), (20, 1.139), (30, 1.219), (35, 1.260), (40, 1.303), (50, 1.395), (60, 1.498), (70, 1.610),
               (80, 1.727), (90, 1.814), (93, 1.835), (98, 1.84), (100, 1.84))
H2SO4_G_MOL = 98.079


def sulfuric_sg(pct: float) -> float:
    pts = SULFURIC_SG
    for (a, sa), (b, sb) in zip(pts, pts[1:]):
        if a <= pct <= b:
            return sa + (sb - sa) * (pct - a) / (b - a)
    return pts[-1][1]


def _alpha(ph: float) -> tuple[float, float, float]:
    h = 10 ** -ph
    k1, k2 = 10 ** -PK1, 10 ** -PK2
    d = h * h + k1 * h + k1 * k2
    return h, k1 * h / d, k1 * k2 / d


# base -> (name, grams in one equivalent of alkalinity at full strength, purity, a bicarbonate adds carbon as well)
BASES: dict[str, tuple[str, float, float, bool]] = {
    "kbic": ("Potassium bicarbonate", 100.115, 1.0, True),
    "nabic": ("Sodium bicarbonate (baking soda)", 84.007, 1.0, True),
    "koh": ("Potassium hydroxide (caustic potash, 85% flakes)", 56.106, 0.85, False),
}


def base_eq_per_litre(ph: float, ta_ppm: float, target_ph: float, bicarbonate: bool) -> float | None:
    """Alkalinity (equivalents per litre) to add to raise the water to the target pH. A bicarbonate also adds carbon, so
    it cannot take the water past about pH 8.3, where the carbon is all bicarbonate; None when the target is out of reach."""
    a0 = ta_ppm / 50000.0
    h, a1, a2 = _alpha(ph)
    ct = (a0 + h - KW / h) / (a1 + 2 * a2)
    h2, b1, b2 = _alpha(target_ph)
    f = b1 + 2 * b2
    if bicarbonate:
        if f >= 1 - 1e-9:
            return None
        return max(0.0, (ct * f + KW / h2 - h2 - a0) / (1 - f))
    return max(0.0, ct * f + KW / h2 - h2 - a0)


def acid_eq_per_litre(ph: float, ta_ppm: float, target_ph: float) -> float:
    """Strong acid (equivalents per litre) that takes water of this pH and alkalinity down to the target pH.

    Alkalinity is carried by bicarbonate and carbonate. The total carbon is fixed by the test (it is worked out from
    the pH and alkalinity), and acid then uses up alkalinity until the pH has fallen to the target. Adding acid fast to
    a closed vessel; CO2 that bubbles out afterwards would let the pH drift up a little, so check with a meter."""
    a0 = ta_ppm / 50000.0  # mg a litre as calcium carbonate to equivalents a litre
    h, a1, a2 = _alpha(ph)
    ct = (a0 + h - KW / h) / (a1 + 2 * a2)
    h2, b1, b2 = _alpha(target_ph)
    a_target = ct * (b1 + 2 * b2) - h2 + KW / h2
    return max(0.0, a0 - a_target)


def flush_for(inj: dict, run_min: float) -> float:
    return inj["flush_min"] if run_min > 3 * inj["flush_min"] else 0.0


def _dilution(inj: dict, water: float) -> tuple[int, int]:
    """The ratio to set and the number of batches, so each batch fits the stock tank and the pump's range."""
    ratio = max(inj["min_ratio"], math.ceil(water / inj["tank_gal"] - 1e-9))
    batches = 1
    if ratio > inj["max_ratio"]:
        ratio = inj["max_ratio"]
        batches = math.ceil(water / ratio / inj["tank_gal"] - 1e-9)
    return int(ratio), batches


def _raise(out: dict, a: dict, inj: dict, water: float) -> dict:
    """Base for the stock tank when the water's pH is below the target."""
    name, g_eq, purity, bicarb = BASES[out["base"]]
    eq = base_eq_per_litre(a["ph"], a["ta_ppm"], a["target_ph"], bicarb)
    if eq is None:
        out["warnings"].append(f"{name} cannot take water above about pH 8.3. Pick a lower target, or use potassium hydroxide.")
        out.update({"meq_l": 0, "g_per_gal": 0, "water_gal": round(water, 1), "table": []})
        return out
    g_gal = eq * g_eq / purity * 3.78541
    out.update({"meq_l": round(eq * 1000, 2), "g_per_gal": round(g_gal, 2), "kg_per_1000": round(g_gal, 2), "base_name": name,
                "water_gal": round(water, 1),
                "table": [{"ph": t, "g_per_gal": round((base_eq_per_litre(a["ph"], a["ta_ppm"], t, bicarb) or 0) * g_eq / purity * 3.78541, 2)}
                          for t in (6.0, 6.5, 7.0, 7.5) if t > a["ph"] and (not bicarb or t < 8.3)]})
    if water > 0:
        ratio, batches = _dilution(inj, water)
        stock = water / ratio / batches
        grams = g_gal * water / batches
        out["tank"] = {"ratio": ratio, "percent": round(100 / ratio, 3), "dial": f"1:{ratio} ({100 / ratio:.2f}%)", "stock_gal": round(stock, 2),
                       "batches": batches, "g": round(grams), "oz": round(grams / 28.3495, 1), "g_per_gal_stock": round(grams / stock) if stock else None}
        if out["tank"]["g_per_gal_stock"] and out["tank"]["g_per_gal_stock"] > 400:
            out["warnings"].append("That is a strong stock solution; bicarbonate dissolves to about 330 g a gallon, so use a weaker dilution or a bigger tank.")
    if not bicarb:
        out["warnings"].append("Potassium hydroxide is caustic: wear eye protection and gloves, add it to water slowly, and use it only if your pump's seals and tubing are rated for it.")
    return out


def acid(a: dict | None, inj: dict, water: float, pump: str = "pump1") -> dict:
    """Acid for the stock tank. `water` is the gallons that pass through the injector in one watering."""
    a = {**default_acid(), **(a or {})}
    out: dict[str, Any] = {"ph": a["ph"], "ta_ppm": a["ta_ppm"], "target_ph": a["target_ph"], "strength_pct": a["strength_pct"],
                           "sg_set": a["sg"], "ready": False, "warnings": []}
    sg = a["sg"] or round(sulfuric_sg(a["strength_pct"]), 3)
    meq_ml = sg * a["strength_pct"] / 100 * 1000 / H2SO4_G_MOL * 2  # two hydrogens in each molecule
    out.update({"sg": sg, "meq_per_ml": round(meq_ml, 2), "pump": pump, "pump_name": inj["name"],
                "bases": [{"key": k, "name": v[0]} for k, v in BASES.items()], "base": a["base"] if a["base"] in BASES else "kbic"})
    if a["ph"] is None or a["ta_ppm"] is None:
        return out
    out["ready"] = True
    out["mode"] = "raise" if a["ph"] < a["target_ph"] else "lower"
    if a["ph"] == a["target_ph"]:
        out["warnings"].append("The water is already at the target pH.")
    if out["mode"] == "raise":
        return _raise(out, a, inj, water)
    eq = acid_eq_per_litre(a["ph"], a["ta_ppm"], a["target_ph"])
    ml_gal = eq * 1000 * 3.78541 / meq_ml
    out.update({"meq_l": round(eq * 1000, 2), "ml_per_gal": round(ml_gal, 2), "ml_per_1000": round(ml_gal * 1000), "water_gal": round(water, 1),
                "table": [{"ph": t, "ml_per_gal": round(acid_eq_per_litre(a["ph"], a["ta_ppm"], t) * 1000 * 3.78541 / meq_ml, 2)}
                          for t in (6.5, 6.0, 5.5, 5.0) if t < a["ph"]]})
    if water > 0:
        ratio, batches = _dilution(inj, water)
        stock = water / ratio
        ml = ml_gal * water / batches
        out["tank"] = {"ratio": int(ratio), "percent": round(100 / ratio, 3), "dial": f"1:{int(ratio)} ({100 / ratio:.2f}%)",
                       "stock_gal": round(stock / batches, 2), "batches": batches, "ml": round(ml), "oz": round(ml / 29.5735, 1),
                       "ml_per_gal_stock": round(ml / (stock / batches)) if stock else None}
    if a["ta_ppm"] and a["ph"] < 6.0 and a["ta_ppm"] > 60:
        out["warnings"].append("A pH this low with this much alkalinity is unusual. Re-test the water before treating it.")
    return out


# soil -> pounds of pure limestone to raise 1,000 sq ft of soil one pH unit, worked 6 inches deep. These are rough
# figures that grow with clay and organic matter; a lab's buffer pH result is better, and can be entered instead.
LIME_PER_UNIT = {"sand": 25.0, "sandy_loam": 40.0, "loam": 60.0, "silt_loam": 75.0, "clay_loam": 90.0, "clay": 110.0}
LIMES = {"calcitic": ("Ground limestone (calcitic)", 1.00), "dolomitic": ("Dolomitic limestone", 1.05),
         "hydrated": ("Hydrated lime", 1.35), "ash": ("Wood ash", 0.67)}
LIME_MAX_LB_1000 = {True: 100.0, False: 70.0}  # most to put on at once: worked in (10 lb per 100 sq ft) or left on top (5 to 7)
LIME_NOTES = ("UConn Extension: no more than 5 to 7 lb of limestone per 100 sq ft on the surface, or 10 lb worked in to 6 inches, at one time; "
              "it takes about 3 to 9 months to work. Cornell Cooperative Extension: rates come from a soil test.")


def validate_lime(target_ph: Any = None, lime_type: Any = None, depth_in: Any = None, tilled: Any = None, ph: Any = "keep",
                  lb_per_unit: Any = "keep") -> dict:
    out: dict[str, Any] = {}
    if target_ph is not None:
        out["target_ph"] = _num(target_ph, "Target pH", 4, 8)
    if lime_type is not None:
        if lime_type not in LIMES:
            raise IrrigationError("Pick a lime from the list")
        out["type"] = lime_type
    if depth_in is not None:
        out["depth_in"] = _num(depth_in, "Depth", 1, 24)
    if tilled is not None:
        out["tilled"] = bool(tilled)
    if ph != "keep":  # empty means use the garden's latest logged pH
        out["ph"] = None if ph in (None, "", 0) else _num(ph, "Soil pH", 3, 9)
    if lb_per_unit != "keep":
        out["lb_per_unit"] = None if lb_per_unit in (None, "", 0) else _num(lb_per_unit, "Lime per pH unit", 1, 1000)
    return out


def lime(l: dict | None, soil: str, logged_ph: float | None, area: float | None) -> dict:
    """Lime to raise the soil's pH, spread dry, for `area` square feet (1,000 when the garden has no layout)."""
    l = {**default_lime(), **(l or {})}
    cur = l["ph"] if l["ph"] is not None else logged_ph
    area_given = bool(area)
    area = area or 1000.0
    lname, cce = LIMES.get(l["type"], LIMES["calcitic"])
    per = l["lb_per_unit"] or LIME_PER_UNIT.get(soil, 60.0)
    out: dict[str, Any] = {"ph": cur, "ph_from": "you" if l["ph"] is not None else ("log" if logged_ph is not None else None),
                           "target_ph": l["target_ph"], "type": l["type"], "types": [{"key": k, "name": v[0]} for k, v in LIMES.items()],
                           "type_name": lname, "depth_in": l["depth_in"], "tilled": l["tilled"], "lb_per_unit": per,
                           "lb_per_unit_set": l["lb_per_unit"], "soil": soil, "area_sqft": round(area, 0), "area_given": area_given,
                           "ready": False, "warnings": [], "notes": LIME_NOTES}
    if cur is None:
        return out
    out["ready"] = True
    if cur >= l["target_ph"]:
        out["warnings"].append("The soil is already at or above the target pH, so it needs no lime.")
        out.update({"lb_1000": 0, "lb_total": 0, "applications": 0})
        return out
    lb_1000 = per * (l["target_ph"] - cur) * (l["depth_in"] / 6.0) / cce
    cap = LIME_MAX_LB_1000[bool(l["tilled"])]
    n = max(1, math.ceil(lb_1000 / cap - 1e-9))
    out.update({"lb_1000": round(lb_1000, 1), "lb_100": round(lb_1000 / 10, 1), "lb_total": round(lb_1000 * area / 1000, 1),
                "applications": n, "per_application_1000": round(lb_1000 / n, 1),
                "per_application_total": round(lb_1000 * area / 1000 / n, 1), "cap_1000": cap})
    if n > 1:
        out["warnings"].append(f"That is more than {cap:g} lb per 1,000 sq ft, the most to apply at once, so split it into {n} applications and re-test the soil between them. It takes 3 to 9 months to work.")
    if per == LIME_PER_UNIT.get(soil) and not l["lb_per_unit"]:
        out["warnings"].append("This is an estimate from the soil type. A lab's lime recommendation is better; enter its pounds per 1,000 sq ft for one pH unit to use it.")
    return out


def _acid_for(st: dict, gal: float, run_min: float, ft: dict) -> dict:
    """Acid goes through its own pump; it can only run with the feeding when that pump is not one the feeding uses."""
    f = fert_of(st["fert"])
    pk, inj = pump_for(f, "acid")
    water = gal * (run_min - flush_for(inj, run_min)) / run_min if run_min else gal
    out = acid(st["acid"], inj, water, pk)
    out["with_feed"] = bool(ft.get("feed_pumps")) and pk not in ft["feed_pumps"]
    if ft.get("feed_pumps"):
        out["note"] = ("Runs with the feeding, on its own pump." if out["with_feed"]
                       else f"Runs on its own watering, because {inj['name']} also runs the fertilizer.")
    return out


def fert(f: dict | None, crops: list[dict], gal: float, method: str, area: float, run_min: float, gpm: float) -> dict:
    """What to put in the stock tank, where to set the injector and how long to run it for one feeding.

    `gal` is the water the whole garden gets in one watering, `run_min` how long the zone runs and `gpm` its flow. The
    injector is on for the run less the flush at the end, which pushes the last of the feed out of the lines. The
    nitrogen strength is the mix's own setting or, if that is empty, the average of what the crops in the garden like,
    weighted by the water each one gets. Each fertilizer's share is its parts by weight, and fertilizers that cannot
    sit together in a concentrate (calcium nitrate with sulfates and phosphates) go in separate tanks."""
    f = fert_of(f)
    mixes = f["mixes"]
    active = f["active"] if f["active"] in mixes else next(iter(mixes), None)
    out: dict[str, Any] = {"mixes": [{"key": k, "name": m["name"], "active": k == active} for k, m in mixes.items()],
                           "active": active, "every_days": f["every_days"], "pumps": [{"key": k, **p} for k, p in f["pumps"].items()],
                           "tank_pump": f["tank_pump"], "first_pump": f["first_pump"], "ready": False,
                           "tank_names": sorted({c["tank"] for m in mixes.values() for c in m["components"]}) + ["acid"], "gal_watering": round(gal, 1),
                           "run_min": run_min, "gpm": round(gpm, 2), "warnings": [], "components": [], "tanks": [], "plants": [],
                           "mix": None}
    if not active:
        return out
    mix = mixes[active]
    out["mix"] = {"key": active, "name": mix["name"], "ppm_n": mix["ppm_n"], "components": mix["components"]}
    letters = sorted({c["tank"] for c in mix["components"]})
    used = [pump_for(f, t)[1] for t in letters] or [f["pumps"][f["first_pump"]]]
    flush = max(flush_for(p, run_min) for p in used)  # the longest flush of the pumps the feeding uses
    frac = (run_min - flush) / run_min if run_min else 1.0
    water = gal * frac
    inject_min = round(run_min - flush, 1)
    out.update({"flush_min": flush, "inject_min": inject_min, "water_gal": round(water, 1)})
    weights = [(c.get("gal_week") or c.get("plants") or 1, c["ppm_n"]) for c in crops if c.get("plants")]
    avg = sum(w * p for w, p in weights) / sum(w for w, _ in weights) if weights else 100.0
    ppm = mix["ppm_n"] or round(avg)
    out["ppm_n"], out["ppm_from"] = ppm, "mix" if mix["ppm_n"] else "plants"
    comps = mix["components"]
    psum = sum(c["parts"] for c in comps)
    n_frac = sum(c["parts"] * c["n"] / 100 for c in comps) / psum if psum else 0.0
    if not comps or n_frac <= 0 or water <= 0:
        out["warnings"].append("This mix needs a fertilizer with nitrogen in it." if comps else "Add a fertilizer to this mix.")
        return out
    litres = water * 3.78541
    n_g = litres * ppm / 1000
    blend_g = n_g / n_frac
    out["ready"] = True
    out["n_pct"] = round(100 * n_frac, 2)
    out["blend_g"] = round(blend_g)
    for c in comps:
        g = blend_g * c["parts"] / psum
        out["components"].append({**c, "g": round(g, 1), "oz": round(g / 28.3495, 2), "lb": round(g / 453.592, 2)})

    def ppm_of(key: str, share: float = 1.0) -> int:
        return round(sum(c["g"] * c[key] / 100 for c in out["components"]) * 1000 / litres * share)

    out["analysis"] = {"N": round(ppm), "P2O5": ppm_of("p"), "K2O": ppm_of("k"), "Ca": ppm_of("ca"), "Mg": ppm_of("mg")}
    runs: dict[str, list[str]] = {}
    for t in sorted({c["tank"] for c in out["components"]}):
        mine = [c for c in out["components"] if c["tank"] == t]
        grams = sum(c["g"] for c in mine)
        pk, inj = pump_for(f, t)
        runs.setdefault(pk, []).append(t)
        ratio = max(inj["min_ratio"], math.ceil(water / inj["tank_gal"] - 1e-9))
        batches = 1
        if ratio > inj["max_ratio"]:
            ratio = inj["max_ratio"]
            batches = math.ceil(water / ratio / inj["tank_gal"] - 1e-9)
        stock = water / ratio
        per_batch = stock / batches
        tk = {"tank": t, "pump": pk, "pump_name": inj["name"],
              "components": [{"name": c["name"], "g": round(c["g"] / batches, 1), "oz": round(c["g"] / batches / 28.3495, 2),
                              "lb": round(c["g"] / batches / 453.592, 3)} for c in mine],
              "grams": round(grams / batches, 1), "ratio": int(ratio), "percent": round(100 / ratio, 3), "stock_gal": round(per_batch, 2),
              "batches": batches, "g_per_gal": round(grams / batches / per_batch) if per_batch else None,
              "dial": f"1:{int(ratio)} ({100 / ratio:.2f}%)"}
        if tk["g_per_gal"] and tk["g_per_gal"] > 570:  # about 150 g a litre, more than most fertilizers dissolve
            out["warnings"].append(f"Tank {t} is very strong ({tk['g_per_gal']} g a gallon) and may not dissolve all the way. Use a bigger tank or a weaker dilution.")
        out["tanks"].append(tk)
        if gpm and not inj["min_gpm"] <= gpm <= inj["max_gpm"]:
            out["warnings"].append(f"The garden runs at {gpm:g} GPM, outside the {inj['name']}'s {inj['min_gpm']:g} to {inj['max_gpm']:g} GPM range.")
    n_runs = max((len(v) for v in runs.values()), default=1)
    out["feed_runs"] = [{"n": i + 1, "tanks": [v[i] for v in runs.values() if i < len(v)]} for i in range(n_runs)]
    out["feed_pumps"] = list(runs)
    if n_runs > 1:
        shared = [f["pumps"][k]["name"] for k, v in runs.items() if len(v) > 1]
        out["warnings"].append("Tanks " + " and ".join(t["tank"] for t in out["tanks"]) + " cannot be mixed strong (calcium nitrate turns cloudy and drops out with sulfates and phosphates), and " + " and ".join(shared) + " can only run one at a time. Run them on " + str(n_runs) + " waterings in a row, at the same run time, so the plants get every fertilizer in the feeding. A second pump would let them run together.")
    elif len(out["tanks"]) > 1:
        out["warnings"].append("Tanks " + " and ".join(t["tank"] for t in out["tanks"]) + " run together on separate pumps, so they never meet strong.")
    lb_n = n_g / 453.592
    out.update({"n_g": round(n_g, 1), "lb_n_1000": round(lb_n * 1000 / area, 3) if area else None,
                "lb_n_week": round(lb_n * 7 / f["every_days"], 3)})
    if method == "drip":
        for c in crops:
            if not c.get("plants"):
                continue
            w = c["gal_plant_watering"] * frac
            mg = w * 3.78541 * ppm
            out["plants"].append({"key": c["key"], "name": c["name"], "gal": round(w, 2), "n_mg": round(mg), "your_ppm": c["ppm_n"],
                                  "blend_g": round(mg / 1000 / n_frac, 2), "high": ppm > c["ppm_n"] * 1.25, "low": ppm < c["ppm_n"] * 0.75})
    return out
