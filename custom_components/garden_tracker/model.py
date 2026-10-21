"""Pure data model and business logic. No Home Assistant imports, so it can be unit tested."""
from __future__ import annotations

import re
import uuid
from datetime import date, timedelta
from typing import Any, Callable

from . import calc


DEFAULT_SETTINGS = {"frost_last": "04-25", "frost_first": "10-15"}  # Ephrata, WA averages
GROUP_MIN = 6  # plantings above this many plants are shown as one summary


class GardenError(ValueError):
    """Raised for invalid requests."""


REASONS = ["disease", "pests", "frost", "heat", "water", "animal_damage", "other"]
ARCHIVE_REASONS = ["season_over", "pulled_early", "died"]
STATUSES = ["alive", "dead", "pulled"]  # "harvested" is set only by single-harvest crops
DEFAULT_ADJUNCTS = [
    {"key": "sulfur", "name": "Sulfur", "per_year": 2},
    {"key": "humic_acid", "name": "Humic acid", "per_year": 2},
    {"key": "compost", "name": "Compost", "per_year": 1},
    {"key": "gypsum", "name": "Gypsum", "per_year": 1},
    {"key": "micros", "name": "Micros", "interval_days": 42},
]
METRICS = {
    "moisture": {"name": "Soil moisture", "unit": "%", "lo": 0, "hi": 100},
    "ec": {"name": "Soil EC", "unit": "mS/cm", "lo": 0, "hi": 30},
    "soil_temp": {"name": "Soil temperature", "unit": "°F", "lo": -40, "hi": 160},
}
COVER_CROPS = ["Winter rye", "Cereal rye", "Hairy vetch", "Winter wheat", "Austrian winter peas",
               "Crimson clover", "Snow peas"]
COVER_METHODS = ["mowed", "roll_crimped", "tarped", "tilled", "winterkill", "other"]
COVER_WAIT_DAYS = 21
# Rule-of-thumb minimum soil temperatures (°F) for sowing or transplanting.
PLANTING_TEMPS = [
    ("Peas, spinach, lettuce", 40), ("Carrots, beets, onions", 45), ("Potatoes", 45),
    ("Corn, beans", 60), ("Tomatoes", 60), ("Peppers, squash, cucumbers", 65), ("Melons", 70),
]
KINDS = {  # entry kind -> (parent type, list key)
    "harvest": ("v", "harvests"), "fertilizer": ("v", "fertilizations"), "spray": ("v", "sprays"),
    "review": ("v", "reviews"), "upotted": ("v", "upotted"),
    "adjunct": ("g", "adjuncts"), "ph": ("g", "ph_readings"),
    "moisture": ("g", "moisture"), "ec": ("g", "ec"), "soil_temp": ("g", "soil_temp"),
    "cover": ("g", "cover_crops"),
}
EDITABLE = {
    "harvest": ("lbs", "date", "notes"),
    "fertilizer": ("product", "n", "p", "k", "date", "notes"),
    "spray": ("product", "target", "phi_days", "reapply_days", "date"),
    "review": ("notes", "year"), "upotted": ("date",),
    "adjunct": ("type", "product", "amount", "date", "notes"), "ph": ("value", "date"),
    "moisture": ("value", "date"), "ec": ("value", "date"), "soil_temp": ("value", "date"),
    "cover": ("crop", "sown", "terminated", "method", "notes", "wait_days"),
}


def slug(text: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(text).lower()).strip("_") or "item"


def new_id() -> str:
    return uuid.uuid4().hex[:8]


def iso(v: Any) -> str | None:
    if v is None or v == "":
        return None
    if isinstance(v, date):
        return v.isoformat()
    try:
        return date.fromisoformat(str(v)).isoformat()
    except ValueError as err:
        raise GardenError(f"'{v}' is not a valid date") from err


class GardenModel:
    def __init__(self, presets: dict, today_fn: Callable[[], date],
                 notify: Callable[[], None] | None = None,
                 structure: Callable[[], None] | None = None) -> None:
        self.data: dict[str, Any] = {"gardens": {}, "varieties": {}, "species": {}, "daily": {},
                                    "settings": dict(DEFAULT_SETTINGS)}
        self.presets = presets
        self._today_fn = today_fn
        self._notify = notify or (lambda: None)
        self._structure = structure or (lambda: None)
        self._rev = 0
        self._cache: tuple | None = None
        self._trash: dict | None = None

    # ---- plumbing -------------------------------------------------------
    def load(self, stored: dict | None) -> None:
        if stored:
            for k in self.data:
                if k in stored:
                    self.data[k] = stored[k]
        self.data["settings"] = {**DEFAULT_SETTINGS, **(self.data.get("settings") or {})}
        for g in self.data["gardens"].values():
            self._ensure_garden(g)

    @staticmethod
    def _ensure_garden(g: dict) -> None:
        for k in METRICS:
            g.setdefault(k, [])
        g.setdefault("sensors", {})
        g.setdefault("cover_crops", [])
        g.setdefault("frost", {})

    def today(self) -> date:
        return self._today_fn()

    def _touch(self, structure: bool = False) -> None:
        self._rev += 1
        if structure:
            self._structure()
        self._notify()

    def record_temp_f(self, temp_f: float) -> None:
        key = self.today().isoformat()
        cur = self.data["daily"].get(key)
        new = [temp_f, temp_f] if cur is None else [min(cur[0], temp_f), max(cur[1], temp_f)]
        if new != cur:
            self.data["daily"][key] = new
            self._touch()

    # ---- lookups ----------------------------------------------------------
    def find_garden(self, ref: str) -> dict:
        gs = self.data["gardens"]
        if ref in gs:
            return gs[ref]
        for g in gs.values():
            if g["name"].lower() == str(ref).lower():
                return g
        raise GardenError(f"No garden found matching '{ref}'")

    def find_variety(self, ref: str, archived_ok: bool = False) -> dict:
        vs = self.data["varieties"]
        v = vs.get(ref)
        if v is None:
            cands = [x for x in vs.values() if x["name"].lower() == str(ref).lower()]
            active = [x for x in cands if not x.get("archived")]
            v = (active or (cands if archived_ok else []) or [None])[0]
        if v is None:
            raise GardenError(f"No plant found matching '{ref}'")
        if v.get("archived") and not archived_ok:
            raise GardenError(f"'{v['name']}' is archived")
        return v

    @staticmethod
    def _entry(items: list[dict], entry_id: str) -> tuple[int, dict]:
        for i, e in enumerate(items):
            if e["id"] == entry_id:
                return i, e
        raise GardenError("That log entry no longer exists")

    def get_species(self, key: str) -> dict | None:
        return self.data["species"].get(key) or self.presets.get(key)

    def _unique(self, base: str, existing: dict) -> str:
        pid, n = base, 2
        while pid in existing:
            pid, n = f"{base}_{n}", n + 1
        return pid

    # ---- species ----------------------------------------------------------
    def add_species(self, key: str, name: str, kind: str, pests: list[dict]) -> None:
        self.data["species"][slug(key)] = {"name": name, "kind": kind, "pests": pests}
        self._touch(True)

    # ---- gardens ----------------------------------------------------------
    def add_garden(self, name: str, ph_entity: str | None = None,
                   ph_min: float = 6.0, ph_max: float = 6.8) -> str:
        gid = self._unique(slug(name), self.data["gardens"])
        self.data["gardens"][gid] = {
            "id": gid, "name": name, "ph_entity": ph_entity or None, "ph_target": [ph_min, ph_max],
            "adjunct_types": {a["key"]: dict(a) for a in DEFAULT_ADJUNCTS},
            "adjuncts": [], "ph_readings": []}
        self._ensure_garden(self.data["gardens"][gid])
        self._touch(True)
        return gid

    def update_garden(self, ref: str, name: str | None = None, ph_entity: str | None = None,
                      ph_min: float | None = None, ph_max: float | None = None) -> None:
        g = self.find_garden(ref)
        if name:
            g["name"] = name
        if ph_entity is not None:
            g["ph_entity"] = ph_entity.strip() or None
        lo, hi = g["ph_target"]
        g["ph_target"] = [ph_min if ph_min is not None else lo, ph_max if ph_max is not None else hi]
        self._touch(True)

    def remove_garden(self, ref: str) -> None:
        g = self.find_garden(ref)
        if any(v["garden"] == g["id"] and not v.get("archived") for v in self.data["varieties"].values()):
            raise GardenError("Archive or remove this garden's plants first")
        for v in self.data["varieties"].values():
            if v["garden"] == g["id"]:
                v["garden_name"] = g["name"]
        del self.data["gardens"][g["id"]]
        self._touch(True)

    def add_adjunct_type(self, garden: str, name: str, per_year: int | None = None,
                         interval_days: int | None = None) -> None:
        g = self.find_garden(garden)
        key = self._unique(slug(name), g["adjunct_types"])
        t: dict[str, Any] = {"key": key, "name": name}
        if interval_days:
            t["interval_days"] = interval_days
        else:
            t["per_year"] = per_year or 1
        g["adjunct_types"][key] = t
        self._touch(True)

    def remove_adjunct_type(self, garden: str, adjunct: str) -> None:
        g = self.find_garden(garden)
        key = self._adjunct_key(g, adjunct)
        del g["adjunct_types"][key]
        self._touch(True)

    @staticmethod
    def _adjunct_key(g: dict, ref: str) -> str:
        if ref in g["adjunct_types"]:
            return ref
        for k, t in g["adjunct_types"].items():
            if t["name"].lower() == str(ref).lower():
                return k
        raise GardenError(f"'{ref}' is not an adjunct in {g['name']}")

    def log_adjunct(self, garden: str, adjunct: str, when: Any = None, product: str | None = None,
                    amount: str | None = None, notes: str | None = None) -> None:
        g = self.find_garden(garden)
        try:
            key = self._adjunct_key(g, adjunct)
        except GardenError:
            name = str(adjunct).strip()
            if not name:
                raise
            key = self._unique(slug(name), g["adjunct_types"])
            g["adjunct_types"][key] = {"key": key, "name": name, "as_needed": True}
            self._touch(True)
        g["adjuncts"].append({"id": new_id(), "type": key,
                              "date": iso(when) or self.today().isoformat(),
                              "product": product, "amount": amount, "notes": notes})
        self._touch()

    def log_ph(self, garden: str, value: float, when: Any = None) -> None:
        g = self.find_garden(garden)
        if not 0 < value < 14:
            raise GardenError("pH must be between 0 and 14")
        g["ph_readings"].append({"id": new_id(), "date": iso(when) or self.today().isoformat(),
                                 "value": round(value, 2), "source": "manual"})
        self._touch()

    def record_sensor_ph(self, gid: str, value: float) -> None:
        g = self.data["gardens"].get(gid)
        if not g or not 0 < value < 14:
            return
        today = self.today().isoformat()
        for r in g["ph_readings"]:
            if r["date"] == today and r["source"] == "sensor":
                if r["value"] == round(value, 2):
                    return
                r["value"] = round(value, 2)
                break
        else:
            g["ph_readings"].append({"id": new_id(), "date": today, "value": round(value, 2), "source": "sensor"})
        self._touch()

    # ---- frost dates ------------------------------------------------------------
    @staticmethod
    def _md(v: Any) -> str | None:
        if v is None or v == "":
            return None
        if isinstance(v, date):
            return v.strftime("%m-%d")
        text = str(v).strip()
        if len(text) == 10:
            text = text[5:]
        try:
            date(2000, int(text[:2]), int(text[3:5]))
            if len(text) != 5 or text[2] != "-":
                raise ValueError
        except ValueError as err:
            raise GardenError(f"'{v}' is not a valid date (use MM-DD)") from err
        return text

    def set_frost_dates(self, garden: str | None = None, last: Any = None, first: Any = None,
                        all_gardens: bool = False) -> None:
        """Set expected last spring / first fall frost (month and day). Applies to one garden, or to all."""
        last_md, first_md = self._md(last), self._md(first)
        if not last_md and not first_md:
            raise GardenError("Enter the last spring frost, the first fall frost, or both")
        if garden and not all_gardens:
            g = self.find_garden(garden)
            if last_md:
                g["frost"]["last"] = last_md
            if first_md:
                g["frost"]["first"] = first_md
        else:
            if last_md:
                self.data["settings"]["frost_last"] = last_md
            if first_md:
                self.data["settings"]["frost_first"] = first_md
            for g in self.data["gardens"].values():
                g["frost"] = {}
        self._touch(True)

    def reset_frost_dates(self, garden: str) -> None:
        self.find_garden(garden)["frost"] = {}
        self._touch(True)

    def _frost_view(self, g: dict, today: date) -> dict:
        st = self.data["settings"]
        last = g["frost"].get("last") or st["frost_last"]
        first = g["frost"].get("first") or st["frost_first"]
        return {"last": last, "first": first, "custom": bool(g["frost"]),
                "last_date": calc.md_date(last, today.year).isoformat(),
                "first_date": calc.md_date(first, today.year).isoformat(),
                "next": calc.frost_status(last, first, today)}

    # ---- winter cover crops -----------------------------------------------------
    def add_cover_crop(self, garden: str, crop: str, sown: Any = None, notes: str | None = None,
                       wait_days: int | None = None) -> str:
        g = self.find_garden(garden)
        crop = (crop or "").strip()
        if not crop:
            raise GardenError("Enter the cover crop")
        cid = new_id()
        g["cover_crops"].append({"id": cid, "crop": crop, "sown": iso(sown) or self.today().isoformat(),
                                 "terminated": None, "method": None, "notes": notes or "",
                                 "wait_days": int(wait_days) if wait_days is not None else COVER_WAIT_DAYS})
        self._touch()
        return cid

    def terminate_cover_crop(self, garden: str, cover: str, when: Any = None, method: str | None = None,
                             notes: str | None = None) -> None:
        g = self.find_garden(garden)
        _, e = self._entry(g["cover_crops"], cover)
        if method is not None and method not in COVER_METHODS:
            raise GardenError("Method must be one of: " + ", ".join(COVER_METHODS))
        stamp = iso(when) or self.today().isoformat()
        if stamp < e["sown"]:
            raise GardenError("Termination can't be before it was sown")
        e["terminated"], e["method"] = stamp, method
        if notes:
            e["notes"] = (e["notes"] + " " + notes).strip()
        self._touch()

    def reopen_cover_crop(self, garden: str, cover: str) -> None:
        g = self.find_garden(garden)
        _, e = self._entry(g["cover_crops"], cover)
        e["terminated"], e["method"] = None, None
        self._touch()

    # ---- soil moisture, EC and temperature --------------------------------------
    def _metric(self, metric: str) -> dict:
        if metric not in METRICS:
            raise GardenError("Metric must be one of: " + ", ".join(METRICS))
        return METRICS[metric]

    def set_sensors(self, garden: str, metric: str, entities: list[str]) -> None:
        g = self.find_garden(garden)
        self._metric(metric)
        clean: list[str] = []
        for e in entities:
            e = str(e).strip()
            if e and e not in clean:
                clean.append(e)
        g["sensors"][metric] = clean
        self._touch(True)

    def log_metric(self, garden: str, metric: str, value: float, when: Any = None) -> None:
        g = self.find_garden(garden)
        spec = self._metric(metric)
        if not spec["lo"] <= value <= spec["hi"]:
            raise GardenError(f"{spec['name']} must be between {spec['lo']} and {spec['hi']} {spec['unit']}")
        g[metric].append({"id": new_id(), "date": iso(when) or self.today().isoformat(),
                          "value": round(value, 2), "source": "manual"})
        self._touch()

    def record_sensor_metric(self, gid: str, metric: str, value: float) -> None:
        """Fold one averaged sensor reading into today's entry (mean, last, min, max)."""
        g = self.data["gardens"].get(gid)
        spec = METRICS.get(metric)
        if not g or not spec or not spec["lo"] <= value <= spec["hi"]:
            return
        today = self.today().isoformat()
        value = round(value, 2)
        for r in g[metric]:
            if r["date"] == today and r["source"] == "sensor":
                if r.get("last") == value:
                    return
                r["n"] = r.get("n", 1) + 1
                r["sum"] = round(r.get("sum", r["value"]) + value, 3)
                r["min"], r["max"] = min(r.get("min", value), value), max(r.get("max", value), value)
                r["last"], r["value"] = value, round(r["sum"] / r["n"], 2)
                break
        else:
            g[metric].append({"id": new_id(), "date": today, "value": value, "last": value, "min": value,
                              "max": value, "n": 1, "sum": value, "source": "sensor"})
        self._touch()

    # ---- varieties and plants -----------------------------------------------
    def add_variety(self, garden: str, species: str, variety: str, plants: int = 1,
                    origin: str = "seed", planted: Any = None, in_ground: Any = None,
                    days_to_harvest: int | None = None, expected_harvest: Any = None,
                    expected_yield: float | None = None, notes: str = "",
                    kind: str | None = None, single_harvest: bool | None = None,
                    multi_year: bool | None = None) -> str:
        g = self.find_garden(garden)
        skey = slug(species)
        sp = self.get_species(skey)
        planted_d = iso(planted) or self.today().isoformat()
        harvest = iso(expected_harvest)
        rule = sp.get("harvest_rule") if sp else None
        use_rule = bool(rule and not days_to_harvest and not harvest)
        if not days_to_harvest and not use_rule and sp and sp.get("default_days"):
            days_to_harvest = int(sp["default_days"])
        auto = False
        if use_rule:
            harvest = calc.rule_harvest_date(rule, date.fromisoformat(planted_d), self._first_frost(g)).isoformat()
            auto = True
        elif not harvest and days_to_harvest:
            harvest = (date.fromisoformat(planted_d) + timedelta(days=days_to_harvest)).isoformat()
            auto = True
        vid = self._unique(slug(variety or species), self.data["varieties"])
        count = max(1, int(plants))
        vkind = sp["kind"] if sp else (kind or "plant")
        self.data["varieties"][vid] = {
            "id": vid, "name": variety or species, "species": skey,
            "species_name": sp["name"] if sp else species, "kind": vkind, "garden": g["id"],
            "origin": origin, "planted": planted_d, "in_ground": iso(in_ground), "upotted": [],
            "days_to_harvest": days_to_harvest, "expected_harvest": harvest, "expected_auto": auto,
            "expected_yield": expected_yield, "notes": notes or "", "expected_rule": use_rule,
            "multi_year": ((bool(sp.get("multi_year")) if sp else False) or bool(multi_year)) if vkind != "tree" else False,
            "single_harvest": (bool(sp.get("single_harvest")) if sp else False) or bool(single_harvest) if vkind != "tree" else False,
            "plants": [{"id": new_id(), "label": f"Plant {i + 1}" if count > 1 or vkind != "tree" else variety or species,
                        "status": "alive", "reason": "", "note": "", "status_date": None}
                       for i in range(count)],
            "harvests": [], "fertilizations": [], "sprays": [], "biofix": {}, "reviews": [],
            "archived": None}
        self._touch(True)
        return vid

    def update_variety(self, ref: str, name: str | None = None, garden: str | None = None,
                       planted: Any = None, in_ground: Any = None, days_to_harvest: int | None = None,
                       expected_harvest: Any = None, expected_yield: float | None = None,
                       notes: str | None = None, add_plants: int | None = None,
                       single_harvest: bool | None = None, multi_year: bool | None = None) -> None:
        v = self.find_variety(ref)
        if multi_year is not None and v["kind"] != "tree":
            v["multi_year"] = bool(multi_year)
        if single_harvest is not None and v["kind"] != "tree":
            v["single_harvest"] = bool(single_harvest)
        if name:
            v["name"] = name
        if garden:
            v["garden"] = self.find_garden(garden)["id"]
        if iso(planted):
            v["planted"] = iso(planted)
        if iso(in_ground):
            v["in_ground"] = iso(in_ground)
        if days_to_harvest:
            v["days_to_harvest"] = days_to_harvest
            v["expected_rule"] = False
        if iso(expected_harvest):
            v["expected_harvest"], v["expected_auto"] = iso(expected_harvest), False
        else:
            redo = (v.get("expected_auto") and (days_to_harvest or iso(planted))) or \
                   (days_to_harvest and not v.get("expected_harvest"))
            if redo and v.get("days_to_harvest"):
                v["expected_harvest"] = (date.fromisoformat(v["planted"]) +
                                         timedelta(days=v["days_to_harvest"])).isoformat()
                v["expected_auto"] = True
        if expected_yield is not None:
            v["expected_yield"] = expected_yield
        if notes is not None:
            v["notes"] = notes
        for _ in range(int(add_plants or 0)):
            v["plants"].append({"id": new_id(), "label": f"Plant {len(v['plants']) + 1}", "status": "alive",
                                "reason": "", "note": "", "status_date": None})
        self._touch(True)

    def set_harvest(self, ref: str, expected: Any = None, expected_yield: float | None = None) -> None:
        v = self.find_variety(ref)
        if iso(expected):
            v["expected_harvest"], v["expected_auto"] = iso(expected), False
        if expected_yield is not None:
            v["expected_yield"] = expected_yield
        self._touch()

    def log_stage(self, ref: str, stage: str, when: Any = None) -> None:
        v = self.find_variety(ref)
        day = iso(when) or self.today().isoformat()
        if stage == "upotted":
            v["upotted"].append({"id": new_id(), "date": day})
        elif stage in ("planted", "in_ground"):
            v[stage] = day
        else:
            raise GardenError("Stage must be planted, upotted, or in_ground")
        self._touch()

    def log_fertilizer(self, ref: str, product: str, n: float | None = None, p: float | None = None,
                       k: float | None = None, when: Any = None, notes: str | None = None) -> None:
        v = self.find_variety(ref)
        v["fertilizations"].append({"id": new_id(), "date": iso(when) or self.today().isoformat(),
                                    "product": product, "n": n, "p": p, "k": k, "notes": notes})
        self._touch()

    def log_spray(self, ref: str, product: str, when: Any = None, target: str | None = None,
                  phi_days: int | None = None, reapply_days: int | None = None) -> None:
        v = self.find_variety(ref)
        v["sprays"].append({"id": new_id(), "date": iso(when) or self.today().isoformat(),
                            "product": product, "target": target,
                            "phi_days": phi_days, "reapply_days": reapply_days})
        self._touch()

    def set_biofix(self, ref: str, pest: str, when: Any = None) -> None:
        self.find_variety(ref)["biofix"][pest] = iso(when) or self.today().isoformat()
        self._touch()

    def add_review(self, ref: str, notes: str, year: int | None = None) -> None:
        self.find_variety(ref)["reviews"].append(
            {"id": new_id(), "year": year or self.today().year, "notes": notes})
        self._touch()

    def set_plant_status(self, ref: str, plant: str, status: str, reason: str | None = None,
                         note: str | None = None, when: Any = None) -> None:
        v = self.find_variety(ref)
        p = next((x for x in v["plants"] if x["id"] == plant or x["label"].lower() == str(plant).lower()), None)
        if p is None:
            raise GardenError(f"No plant '{plant}' in {v['name']}")
        if status not in STATUSES:
            raise GardenError("Status must be alive, dead, or pulled")
        if status == "alive":
            p.update(status="alive", reason="", note="", status_date=None)
        else:
            if reason not in REASONS:
                raise GardenError("Pick a reason: " + ", ".join(REASONS))
            p.update(status=status, reason=reason, note=note or "",
                     status_date=iso(when) or self.today().isoformat())
        self._touch()

    def mark_plants_lost(self, ref: str, count: int, status: str = "dead", reason: str | None = None,
                         note: str | None = None, when: Any = None) -> None:
        """Mark `count` living plants dead/pulled in one go (for big plantings)."""
        v = self.find_variety(ref)
        if status not in ("dead", "pulled"):
            raise GardenError("Status must be dead or pulled")
        if reason not in REASONS:
            raise GardenError("Pick a reason: " + ", ".join(REASONS))
        alive = [p for p in v["plants"] if p["status"] == "alive"]
        count = int(count)
        if count < 1:
            raise GardenError("Enter how many plants")
        if count > len(alive):
            raise GardenError(f"Only {len(alive)} living plants in {v['name']}")
        stamp = iso(when) or self.today().isoformat()
        for p in alive[-count:]:
            p.update(status=status, reason=reason, note=note or "", status_date=stamp)
        self._touch()

    def restore_plants(self, ref: str, count: int, status: str | None = None,
                       reason: str | None = None, when: Any = None) -> None:
        """Bring `count` lost plants back to alive (most recently lost first)."""
        v = self.find_variety(ref)
        lost = [p for p in v["plants"] if p["status"] in ("dead", "pulled")
                and (not status or p["status"] == status) and (not reason or p["reason"] == reason)
                and (not when or p["status_date"] == iso(when))]
        count = int(count)
        if count < 1 or count > len(lost):
            raise GardenError(f"{len(lost)} lost plants match")
        lost.sort(key=lambda p: p["status_date"] or "")
        for p in lost[-count:]:
            p.update(status="alive", reason="", note="", status_date=None)
        self._touch()

    def _single(self, v: dict) -> bool:
        """True for crops that are pulled when harvested (carrots, onions, garlic, potatoes)."""
        if v["kind"] == "tree":
            return False
        flag = v.get("single_harvest")
        if flag is None:
            sp = self.get_species(v["species"]) or {}
            flag = bool(sp.get("single_harvest"))
        return bool(flag)

    def _first_frost(self, g: dict | None) -> str:
        return ((g or {}).get("frost") or {}).get("first") or self.data["settings"]["frost_first"]

    def _refresh_rule(self, v: dict) -> None:
        """Keep a frost-based expected harvest date (horseradish) in step with the garden's frost date."""
        sp = self.get_species(v["species"]) or {}
        rule = sp.get("harvest_rule")
        if not rule:
            return
        if v.get("expected_rule") is None and v.get("expected_auto") and v.get("days_to_harvest") == 730:
            v["expected_rule"], v["days_to_harvest"] = True, None  # was the 0.6.0 blanket 730 days
        if v.get("expected_rule") and v.get("expected_auto"):
            g = self.data["gardens"].get(v["garden"])
            v["expected_harvest"] = calc.rule_harvest_date(
                rule, date.fromisoformat(v["planted"]), self._first_frost(g)).isoformat()

    def _multi(self, v: dict) -> bool:
        """True for slow crops (horseradish) whose countdown reads in years, months and days."""
        if v["kind"] == "tree":
            return False
        flag = v.get("multi_year")
        if flag is None:
            flag = bool((self.get_species(v["species"]) or {}).get("multi_year"))
        return bool(flag)

    def log_harvest(self, ref: str, lbs: float, when: Any = None, notes: str | None = None,
                    plants: int | None = None) -> None:
        v = self.find_variety(ref)
        if lbs <= 0:
            raise GardenError("Enter the pounds picked")
        alive = [p for p in v["plants"] if p["status"] == "alive"]
        if not alive:
            raise GardenError("No living plants to receive this harvest")
        day = iso(when) or self.today().isoformat()
        entry = {"id": new_id(), "date": day, "lbs": round(lbs, 3), "notes": notes}
        if self._single(v):
            n = int(plants) if plants else len(alive)
            if n < 1 or n > len(alive):
                raise GardenError(f"Pick between 1 and {len(alive)} plants")
            chosen = alive[:n]
            entry["shares"] = calc.split_even(lbs, [p["id"] for p in chosen])
            entry["ended"] = [p["id"] for p in chosen]
            for p in chosen:
                p.update(status="harvested", reason="", note="", status_date=day)
            if n == len(alive):
                v["archived"] = self._archive_stamp(v, "season_over", day, "Harvested")
                entry["auto_archived"] = True
        else:
            entry["shares"] = calc.split_even(lbs, [p["id"] for p in alive])
        v["harvests"].append(entry)
        self._touch(entry.get("auto_archived", False))

    def _archive_stamp(self, v: dict, reason: str, day: str, notes: str) -> dict:
        g = self.data["gardens"].get(v["garden"])
        return {"date": day, "reason": reason, "notes": notes or "", "year": int(day[:4]),
                "garden_name": g["name"] if g else v.get("garden_name", "")}

    # ---- editing and removing log entries -------------------------------------
    def _parent(self, kind: str, parent: str) -> dict:
        if kind not in KINDS:
            raise GardenError(f"Unknown log type '{kind}'")
        return self.find_garden(parent) if KINDS[kind][0] == "g" else self.find_variety(parent, True)

    def delete_entry(self, kind: str, parent: str, entry_id: str) -> None:
        owner = self._parent(kind, parent)
        items = owner[KINDS[kind][1]]
        idx, entry = self._entry(items, entry_id)
        items.pop(idx)
        self._trash = {"kind": kind, "owner": owner, "idx": idx, "entry": entry, "archived": None, "dates": {}}
        structure = False
        if kind == "harvest" and entry.get("ended"):
            for p in owner["plants"]:
                if p["id"] in entry["ended"] and p["status"] == "harvested":
                    self._trash["dates"][p["id"]] = p["status_date"]
                    p.update(status="alive", reason="", note="", status_date=None)
            if entry.get("auto_archived") and owner.get("archived"):
                self._trash["archived"] = owner["archived"]
                owner["archived"] = None
                structure = True
        self._touch(structure)

    def undo_delete(self) -> None:
        t = self._trash
        if not t:
            raise GardenError("Nothing to undo")
        t["owner"][KINDS[t["kind"]][1]].insert(t["idx"], t["entry"])
        if t["kind"] == "harvest" and t["entry"].get("ended"):
            for p in t["owner"]["plants"]:
                if p["id"] in t["dates"]:
                    p.update(status="harvested", reason="", note="", status_date=t["dates"][p["id"]])
            if t["archived"]:
                t["owner"]["archived"] = t["archived"]
        self._trash = None
        self._touch(True)

    def edit_entry(self, kind: str, parent: str, entry_id: str, fields: dict) -> None:
        owner = self._parent(kind, parent)
        _, e = self._entry(owner[KINDS[kind][1]], entry_id)
        backup = dict(e)
        for key, val in fields.items():
            if key not in EDITABLE[kind] or val is None:
                continue
            if key == "date":
                e["date"] = iso(val)
            elif key == "lbs":
                if val <= 0:
                    raise GardenError("Pounds must be above zero")
                ids = list(e["shares"])
                e["lbs"], e["shares"] = round(val, 3), calc.split_even(val, ids)
            elif kind == "cover" and key in ("sown", "terminated"):
                e[key] = iso(val)
            elif kind == "cover" and key == "wait_days":
                e[key] = int(val)
            elif key == "value" and kind in METRICS:
                spec = METRICS[kind]
                if not spec["lo"] <= val <= spec["hi"]:
                    raise GardenError(f"{spec['name']} must be between {spec['lo']} and {spec['hi']} {spec['unit']}")
                e["value"], e["source"] = round(val, 2), "manual"
                e.pop("min", None), e.pop("max", None), e.pop("last", None)
            elif key == "value":
                if not 0 < val < 14:
                    raise GardenError("pH must be between 0 and 14")
                e["value"], e["source"] = round(val, 2), "manual"
            elif key == "type":
                e["type"] = self._adjunct_key(owner, val)
            else:
                e[key] = val
        if kind == "cover" and e.get("terminated") and e["terminated"] < e["sown"]:
            e.clear()
            e.update(backup)
            raise GardenError("Termination can't be before it was sown")
        self._touch()

    # ---- archive / next year ----------------------------------------------------
    def archive_variety(self, ref: str, reason: str = "season_over", when: Any = None,
                        notes: str | None = None, final_lbs: float | None = None) -> None:
        v = self.find_variety(ref)
        if reason not in ARCHIVE_REASONS:
            raise GardenError("Reason must be season_over, pulled_early, or died")
        day = iso(when) or self.today().isoformat()
        if final_lbs and final_lbs > 0:
            self.log_harvest(v["id"], final_lbs, day)
        v["archived"] = self._archive_stamp(v, reason, day, notes or "")
        self._touch(True)

    def end_season(self, garden: str, when: Any = None, notes: str | None = None,
                   cover: str | None = None, wait_days: int | None = None) -> int:
        """Archive every active non-tree planting in a garden; optionally sow a cover crop."""
        g = self.find_garden(garden)
        targets = [v["id"] for v in self.data["varieties"].values()
                   if v["garden"] == g["id"] and not v.get("archived") and v["kind"] != "tree"]
        if not targets and not cover:
            raise GardenError(f"No active plants in {g['name']} to end")
        for vid in targets:
            self.archive_variety(vid, "season_over", when, notes)
        if cover:
            self.add_cover_crop(g["id"], cover, when, None, wait_days)
        self._touch(True)
        return len(targets)

    def restore_variety(self, ref: str) -> None:
        v = self.find_variety(ref, True)
        v["archived"] = None
        self._touch(True)

    def plant_again(self, ref: str, planted: Any = None, plants: int | None = None,
                    garden: str | None = None) -> str:
        old = self.find_variety(ref, True)
        gref = garden or old["garden"]
        if gref not in self.data["gardens"]:
            raise GardenError("Pick a garden for the new plants")
        ypp = None
        seasons = calc.seasons_for(
            {**old, "id": "_new"}, self.data["varieties"], self.data["daily"], self.today())
        if seasons:
            ypp = round(calc.mean([s["yield_per_plant"] for s in seasons]), 1)
        return self.add_variety(gref, old["species"], old["name"], plants or len(old["plants"]),
                                old["origin"], planted, None, old.get("days_to_harvest"), None,
                                ypp or old.get("expected_yield"), "", old["kind"], self._single(old),
                                self._multi(old))

    def remove_variety(self, ref: str) -> None:
        v = self.find_variety(ref, True)
        del self.data["varieties"][v["id"]]
        self._touch(True)

    # ---- snapshot for the card and sensors --------------------------------------
    def snapshot(self) -> dict:
        key = (self._rev, self.today())
        if self._cache and self._cache[0] == key:
            return self._cache[1]
        snap = self._build()
        self._cache = (key, snap)
        return snap

    def index(self) -> dict:
        s = self.snapshot()
        return {"g": {g["id"]: g for g in s["gardens"]}, "v": {v["id"]: v for v in s["varieties"]}}

    def _build(self) -> dict:
        today, daily = self.today(), self.data["daily"]
        species = {}
        for k, sp in {**self.presets, **self.data["species"]}.items():
            species[k] = {"key": k, "name": sp["name"], "kind": sp["kind"],
                          "pests": [{"key": p["key"], "name": p["name"]} for p in sp.get("pests", [])],
                          "feeding_plan": sp.get("feeding_plan", []),
                          "single_harvest": bool(sp.get("single_harvest")),
                          "multi_year": bool(sp.get("multi_year")), "default_days": sp.get("default_days"), "harvest_rule": sp.get("harvest_rule")}
        gardens = [self._garden_view(g, today) for g in self.data["gardens"].values()]
        varieties = [self._variety_view(v, today, daily) for v in self.data["varieties"].values()]
        varieties.sort(key=lambda x: (x["archived"] is not None, x["garden"], x["kind"], x["name"].lower()))
        return {"today": today.isoformat(), "species": species, "gardens": gardens,
                "varieties": varieties, "can_undo": self._trash is not None,
                "reasons": REASONS}

    def _garden_view(self, g: dict, today: date) -> dict:
        hist = sorted(g["ph_readings"], key=lambda r: (r["date"], r["id"]))
        cur, first = (hist[-1] if hist else None), (hist[0] if hist else None)
        lo, hi = g["ph_target"]
        level = None
        if cur:
            level = "ok" if lo <= cur["value"] <= hi else ("low" if cur["value"] < lo else "high")
        names = {k: t["name"] for k, t in g["adjunct_types"].items()}
        log = sorted(g["adjuncts"], key=lambda e: (e["date"], e["id"]), reverse=True)
        metrics = {k: self._metric_view(g, k) for k in METRICS}
        return {
            "id": g["id"], "name": g["name"], "metrics": metrics,
            "planting": self._planting_view(metrics["soil_temp"]),
            "cover": self._cover_view(g, today),
            "frost": self._frost_view(g, today),
            "ph": {"entity": g.get("ph_entity"), "current": cur and cur["value"], "date": cur and cur["date"],
                   "source": cur and cur["source"], "target": [lo, hi], "level": level,
                   "first": first and {"date": first["date"], "value": first["value"]}, "history": hist},
            "adjuncts": [calc.adjunct_status(t, g["adjuncts"], today) for t in g["adjunct_types"].values()],
            "adjunct_log": [{**e, "type_name": names.get(e["type"], e["type"])} for e in log],
        }

    @staticmethod
    def _metric_view(g: dict, key: str) -> dict:
        spec = METRICS[key]
        hist = sorted(g.get(key, []), key=lambda r: (r["date"], r["id"]))
        cur = hist[-1] if hist else None
        keep = ("id", "date", "value", "min", "max", "source")
        return {"key": key, "name": spec["name"], "unit": spec["unit"],
                "entities": list(g.get("sensors", {}).get(key, [])),
                "current": cur and (cur.get("last", cur["value"]) if cur["source"] == "sensor" else cur["value"]),
                "date": cur and cur["date"], "source": cur and cur["source"],
                "min": cur and cur.get("min"), "max": cur and cur.get("max"),
                "history": [{k: r[k] for k in keep if k in r} for r in hist[-180:]]}

    @staticmethod
    def _cover_view(g: dict, today: date) -> dict:
        items = []
        for e in g.get("cover_crops", []):
            sown = date.fromisoformat(e["sown"])
            end = date.fromisoformat(e["terminated"]) if e.get("terminated") else None
            wait = e.get("wait_days", COVER_WAIT_DAYS)
            ready = end + timedelta(days=wait) if end else None
            left = (ready - today).days if ready else None
            state = "growing" if not end else ("waiting" if left > 0 else "done")
            items.append({**e, "wait_days": wait, "days_in_ground": ((end or today) - sown).days,
                          "state": state, "ready_date": ready and ready.isoformat(),
                          "days_left": left if left is None else max(0, left),
                          "days_since_term": (today - end).days if end else None})
        items.sort(key=lambda x: (x["state"] == "done", x["sown"]), reverse=False)
        done = [i for i in items if i["state"] == "done"]
        live = [i for i in items if i["state"] != "done"]
        live.sort(key=lambda x: x["sown"], reverse=True)
        done.sort(key=lambda x: x["sown"], reverse=True)
        growing = [i for i in live if i["state"] == "growing"]
        waiting = [i for i in live if i["state"] == "waiting"]
        blocked = None
        if growing:
            blocked = {"reason": "growing", "days_left": None, "date": None}
        elif waiting:
            w = max(waiting, key=lambda x: x["days_left"])
            blocked = {"reason": "waiting", "days_left": w["days_left"], "date": w["ready_date"]}
        return {"items": live + done, "blocked": blocked, "presets": COVER_CROPS, "methods": COVER_METHODS}

    @staticmethod
    def _planting_view(temp: dict) -> dict | None:
        """Is the soil warm enough? Uses the average of the last 3 daily lows (or readings)."""
        hist = temp["history"][-3:]
        if not hist:
            return None
        basis = round(sum(r.get("min", r["value"]) for r in hist) / len(hist), 1)
        return {"basis": basis, "days": len(hist),
                "crops": [{"name": n, "min_f": t, "ready": basis >= t} for n, t in PLANTING_TEMPS]}

    def _variety_view(self, v: dict, today: date, daily: dict) -> dict:
        self._refresh_rule(v)
        sp = self.get_species(v["species"]) or {}
        kind = v["kind"]
        totals = calc.plant_totals(v)
        allp = [{"id": p["id"], "label": p["label"], "status": p["status"], "reason": p["reason"],
                 "note": p["note"], "status_date": p["status_date"],
                 "total": round(totals.get(p["id"], 0.0), 2)} for p in v["plants"]]
        alive = [p for p in allp if p["status"] == "alive"]
        grouped = len(allp) > GROUP_MIN
        lost: list[dict] = []
        if grouped:
            groups: dict[tuple, dict] = {}
            for p in allp:
                if p["status"] in ("alive", "harvested"):
                    continue
                k = (p["status"], p["reason"], p["status_date"], p["note"])
                gp = groups.setdefault(k, {"status": k[0], "reason": k[1], "date": k[2], "note": k[3],
                                           "count": 0, "lbs": 0.0})
                gp["count"] += 1
                gp["lbs"] = round(gp["lbs"] + p["total"], 2)
            lost = sorted(groups.values(), key=lambda x: x["date"] or "", reverse=True)
            plants = []
        else:
            plants = allp
        labels = {p["id"]: p["label"] for p in v["plants"]}

        def to_text(shares: dict) -> str:
            n = len(shares)
            if grouped:
                return "all plants" if n == len(allp) else f"{n} plants"
            return ", ".join(labels.get(pid, "removed plant") for pid in shares)

        harvests = []
        for h in sorted(v["harvests"], key=lambda h: (h["date"], h["id"]), reverse=True):
            hh = {k: val for k, val in h.items() if k != "shares"}
            hh["to"] = [] if grouped else [labels.get(pid, "removed plant") for pid in h["shares"]]
            hh["to_text"] = to_text(h["shares"])
            hh["n"] = len(h["shares"])
            hh["ended"] = len(h.get("ended", []))
            hh["each"] = round(h["lbs"] / max(1, len(h["shares"])), 2)
            harvests.append(hh)
        per_avg = round(sum(p["total"] for p in allp) / max(1, len(allp)), 2)
        last_f, last_s = calc.latest(v["fertilizations"]), calc.latest(v["sprays"])
        last_up = calc.latest(v["upotted"])
        planted_d = date.fromisoformat(v["planted"])
        days = {"planted": (today - planted_d).days, "upotted": calc.days_since(last_up and last_up["date"], today),
                "in_ground": calc.days_since(v.get("in_ground"), today),
                "fertilized": calc.days_since(last_f and last_f["date"], today)}
        dh = calc.days_until(calc.d(v.get("expected_harvest")), today)
        nxt, safe, cut = calc.next_spray_date(v), calc.safe_harvest_date(v), calc.spray_cutoff_date(v)
        spray = {"days_since": calc.days_since(last_s and last_s["date"], today),
                 "next_in": calc.days_until(nxt, today), "next_date": nxt and nxt.isoformat(),
                 "safe_in": None if safe is None else max(0, (safe - today).days),
                 "safe_date": safe and safe.isoformat(),
                 "cutoff_in": calc.days_until(cut, today), "cutoff_date": cut and cut.isoformat()}
        pests = []
        for pest in sp.get("pests", []):
            st = calc.pest_status(v, pest, daily, today)
            rate = calc.recent_dd_rate(daily, today, 7, pest["lower_f"], pest["upper_f"])
            est = None
            if st and st["dd_to_next"] and rate > 0.5:
                est = int(-(-st["dd_to_next"] // rate))
            pests.append({"key": pest["key"], "name": pest["name"], "status": st, "est_days": est,
                          "needs_biofix": st is None and not pest.get("default_biofix")})
        feeding = None
        plan = sp.get("feeding_plan")
        if plan and kind != "tree":
            ref_day = date.fromisoformat(v["in_ground"]) if v.get("in_ground") else planted_d
            age = (today - ref_day).days
            cur = max((i for i, ph in enumerate(plan) if ph["from_day"] <= age), default=0)
            feeding = {"phases": plan, "current": cur}
        seasons = calc.seasons_for(v, self.data["varieties"], daily, today)
        proj = None if v.get("archived") else calc.project(v, seasons, daily, today, len(alive) or len(allp))
        status = self._status(kind, dh, spray, pests, proj)
        g = self.data["gardens"].get(v["garden"])
        return {
            "id": v["id"], "name": v["name"], "species": v["species"], "species_name": v["species_name"],
            "kind": kind, "garden": v["garden"],
            "garden_name": g["name"] if g else (v.get("archived") or {}).get("garden_name", v.get("garden_name", "")),
            "origin": v["origin"], "planted": v["planted"], "in_ground": v.get("in_ground"),
            "upotted": sorted(v["upotted"], key=lambda u: u["date"], reverse=True),
            "days_to_harvest": v.get("days_to_harvest"), "expected_harvest": v.get("expected_harvest"),
            "expected_yield": v.get("expected_yield"), "notes": v["notes"],
            "age_years": round((today - planted_d).days / 365.25, 1), "days": days, "days_to_expected": dh, "multi_year": self._multi(v),
            "countdown": self._countdown(v, today, False), "countdown_short": self._countdown(v, today, True),
            "plants": plants, "grouped": grouped, "lost": lost, "per_plant_avg": per_avg,
            "alive": len(alive), "count": len(allp), "single_harvest": self._single(v),
            "harvested": sum(1 for p in allp if p["status"] == "harvested"),
            "total_lbs": round(sum(totals.values()), 2), "harvests": harvests,
            "fertilizations": sorted(v["fertilizations"], key=lambda e: (e["date"], e["id"]), reverse=True),
            "last_fert": last_f, "feeding": feeding,
            "sprays": sorted(v["sprays"], key=lambda e: (e["date"], e["id"]), reverse=True),
            "spray": spray, "pests": pests,
            "reviews": sorted(v["reviews"], key=lambda e: (e["year"], e["id"]), reverse=True),
            "projection": proj, "seasons": seasons, "status": status, "archived": v.get("archived"),
        }

    def _countdown(self, v: dict, today: date, short: bool) -> str | None:
        exp = calc.d(v.get("expected_harvest"))
        if not exp or not self._multi(v) or exp <= today:
            return None
        return calc.ymd_text(today, exp, short)

    @staticmethod
    def _status(kind: str, dh: int | None, spray: dict, pests: list, proj: dict | None) -> dict:
        if kind == "tree":
            if spray["safe_in"] and dh is not None and dh <= 21:
                return {"level": "hold", "text": f"Hold: safe to pick in {spray['safe_in']} days"}
            near = [(p["status"]["dd_to_next"], p) for p in pests
                    if p["status"] and p["status"]["dd_to_next"] is not None and p["status"]["dd_to_next"] <= 40]
            if near:
                dd, p = min(near, key=lambda x: x[0])
                est = p["est_days"]
                return {"level": "spray", "text": f"Spray window in about {est} days" if est else "Spray window near"}
            if spray["next_in"] is not None and spray["next_in"] <= 3:
                n = spray["next_in"]
                return {"level": "spray", "text": "Reapply spray due" if n <= 0 else f"Reapply spray in {n} days"}
            return {"level": "ok", "text": "On track"}
        if dh is not None and dh <= 0:
            return {"level": "info", "text": "Harvest time"}
        return {"level": "ok", "text": "On track"}
