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


def blank() -> dict:
    return {"method": "drip", "soil": DEFAULT_SOIL, "per_week": 3, "run_min": None, "sprinkler_in_hr": 0.75,
            "sprinkler_gpm": None, "max_line_gph": DEFAULT_MAX_LINE_GPH, "crops": {},
            "fert": {"product": "", "n_pct": 20.0, "p_pct": 20.0, "k_pct": 20.0, "ppm_n": 100.0, "ratio": 100, "per_week": 1}}


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


def validate_fert(product: Any = None, n_pct: Any = None, p_pct: Any = None, k_pct: Any = None, ppm_n: Any = None,
                  ratio: Any = None, per_week: Any = None) -> dict:
    out: dict[str, Any] = {}
    if product is not None:
        out["product"] = str(product).strip()[:80]
    for k, v in (("n_pct", n_pct), ("p_pct", p_pct), ("k_pct", k_pct)):
        if v is not None:
            out[k] = _num(v, k[0].upper() + " percent", 0, 100)
    if ppm_n is not None:
        out["ppm_n"] = _num(ppm_n, "Nitrogen ppm", 1, 1000)
    if ratio is not None:
        out["ratio"] = int(_num(ratio, "Injector ratio", 1, 2000))
    if per_week is not None:
        out["per_week"] = int(_num(per_week, "Feedings per week", 1, 14))
    return out


def settings_for(s: dict | None) -> dict:
    base = blank()
    if s:
        base.update({k: v for k, v in s.items() if k not in ("fert", "crops")})
        base["fert"].update(s.get("fert") or {})
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


def plan(layout: dict, settings: dict | None, names: dict[str, str] | None = None) -> dict:
    """Watering for a laid-out garden. `layout` is the result of layout.plan."""
    st = settings_for(settings)
    soil = SOILS.get(st["soil"], SOILS[DEFAULT_SOIL])
    base = {"configured": bool(layout and layout.get("configured")), "method": st["method"], "methods": METHODS,
            "soil": st["soil"], "soils": [{"key": k, "name": v[0], "max_gph": v[1], "note": v[3]} for k, v in SOILS.items()],
            "soil_note": soil[3], "per_week": st["per_week"], "flows": list(DRIP_FLOWS), "spacings": list(DRIP_SPACINGS),
            "rolls": list(ROLLS), "max_line_gph": st["max_line_gph"], "sprinkler_in_hr": st["sprinkler_in_hr"],
            "sprinkler_gpm": st["sprinkler_gpm"], "fert_settings": st["fert"]}
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
    return {**base, "run_min": run_min, "run_min_set": st["run_min"], "auto_run_min": round(auto * 60 / per, 1), "hours_week": round(hours, 2),
            "crops": crops, "rows": rows_out, "order": order, "waste": WASTE,
            "totals": {"gph": round(total_gph, 1), "gpm": round(total_gph / 60, 2), "gal_watering": round(total_gph * run_min / 60, 1),
                       "gal_week": round(gal_week, 1), "emitters": sum(o["emitters"] for o in order),
                       "feet": round(sum(o["feet"] for o in order), 1), "lines_over": line_flag},
            "fert": fert(st["fert"], crops, total_gph * run_min / 60, "drip", layout["width_ft"] * layout["length_ft"])}


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
    return {**base, "run_min": run_min, "run_min_set": None, "hours_week": round(hours, 2), "need_in_week": need_in, "crops": crops,
            "rows": [], "order": [], "totals": {"gph": round(gpm * 60, 1), "gpm": gpm, "gal_watering": gal_watering, "gal_week": round(gal_week, 1),
                                                "gpm_given": bool(st["sprinkler_gpm"]), "area_sqft": round(area, 1)},
            "fert": fert(st["fert"], crops, gal_watering, "sprinkler", area)}


def fert(f: dict, crops: list[dict], gal: float, method: str, area: float) -> dict:
    """What to inject for one watering at the nitrogen strength chosen. `gal` is the garden's water for one watering."""
    n = f["n_pct"] / 100
    ppm = f["ppm_n"]
    out = {"ppm_n": ppm, "n_pct": f["n_pct"], "p_pct": f["p_pct"], "k_pct": f["k_pct"], "product": f["product"], "ratio": f["ratio"],
           "per_week": f["per_week"], "gal": round(gal, 1), "ready": n > 0 and gal > 0}
    if not out["ready"]:
        return out
    mg_n = gal * 3.78541 * ppm  # parts per million is milligrams in a litre
    g_fert = mg_n / 1000 / n
    stock_gal = gal / f["ratio"]
    out.update({"n_g": round(mg_n / 1000, 1), "fert_g": round(g_fert, 1), "fert_oz": round(g_fert / 28.3495, 2),
                "stock_gal": round(stock_gal, 2), "stock_g_per_gal": round(g_fert / stock_gal, 1) if stock_gal else None,
                "stock_ppm": round(ppm * f["ratio"]), "lb_n_1000": round(mg_n / 1000 / 453.592 * 1000 / area, 2) if area else None,
                "lb_n_week": round(mg_n / 1000 / 453.592 * f["per_week"], 2)})
    out["plants"] = []
    if method == "drip":
        for c in crops:
            if not c["plants"]:
                continue
            water = c["gal_plant_watering"]
            mg = water * 3.78541 * ppm
            out["plants"].append({"key": c["key"], "name": c["name"], "gal": water, "n_mg": round(mg), "fert_g": round(mg / 1000 / n, 2),
                                  "your_ppm": c["ppm_n"], "high": ppm > c["ppm_n"] * 1.25, "low": ppm < c["ppm_n"] * 0.75})
    return out
