"""Pure data model and business logic. No Home Assistant imports, so it can be unit tested."""
from __future__ import annotations

import copy
import re
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Callable

from . import calc


DEFAULT_SETTINGS = {"frost_last": "04-25", "frost_first": "10-15"}  # Ephrata, WA averages
ALARM_BACK_F = 1.0  # the air must come back this far inside a limit before an alarm counts as over
UNSET: Any = object()
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
    "air_temp": {"name": "Temperature", "unit": "°F", "lo": -40, "hi": 160},
    "par": {"name": "Light (PAR)", "unit": "µmol/m²/s", "lo": 0, "hi": 4000},
}
# Places plants live. A garden has soil; the seedling rack and greenhouse are indoor, so they track
# air temperature (and light on the rack), watering and 10x20 trays instead of soil and fertilizer.
LOCATION_KINDS = {"garden": "Garden", "rack": "Seedling rack", "greenhouse": "Greenhouse"}
METRIC_SETS = {"garden": ("moisture", "ec", "soil_temp"), "rack": ("air_temp", "par"), "greenhouse": ("air_temp",)}
DEFAULT_CONTAINERS = ["6-cell tray", "4-cell tray", "3.3 in pot", "5 in pot"]
# How many fit in one 10x20 tray (Bootstrap Farmer sizes): 12 six-cell inserts, 8 four-cell inserts, and the pot inserts.
CONTAINER_PER_TRAY = {"6-cell tray": 72, "4-cell tray": 32, "3.3 in pot": 18, "5 in pot": 8}
POWER_GROUPS = {"greenhouse": {"heat": "Heating", "cool": "Cooling"}, "rack": {"power": "Lights and power"}}
DEFAULT_CLIMATE = {"enabled": False, "heat_set": 60.0, "cool_set": 80.0, "heaters": [], "coolers": [],
                   "heat_min_run": 0, "heat_max_run": 0, "heat_rest": 10}
CLIMATE_MIN_GAP = 3.0  # degrees F between the heat and cool set points

COVER_CROPS = ["Winter rye", "Cereal rye", "Hairy vetch", "Winter wheat", "Austrian winter peas",
               "Crimson clover", "Snow peas"]
COVER_METHODS = ["mowed", "roll_crimped", "tarped", "tilled", "winterkill", "other"]
COVER_WAIT_DAYS = 21
# Soil EC and moisture guidance. The probe only reads the top few inches, and EC reads high in dry soil
# and low in wet soil, so a reading is only trusted when moisture is inside the band.
DEFAULT_EC_TARGET = [0.8, 1.8]
DEFAULT_MOISTURE_BAND = [25, 60]
DEFAULT_PROBE_DEPTH = 4
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
    "cover": ("g", "cover_crops"), "water": ("g", "watering"),
    "air_temp": ("g", "air_temp"), "par": ("g", "par"),
}
EDITABLE = {
    "harvest": ("lbs", "date", "notes"),
    "fertilizer": ("product", "n", "p", "k", "date", "notes"),
    "spray": ("product", "target", "phi_days", "reapply_days", "date"),
    "review": ("notes", "year"), "upotted": ("date",),
    "adjunct": ("type", "product", "amount", "date", "notes"), "ph": ("value", "date"),
    "moisture": ("value", "date"), "ec": ("value", "date"), "soil_temp": ("value", "date"),
    "air_temp": ("value", "date"), "par": ("value", "date"), "water": ("date", "notes"),
    "cover": ("crop", "sown", "terminated", "method", "notes", "wait_days", "amount_lbs"),
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
        self.climate_state: dict[str, dict] = {}  # runtime only: what the thermostat is doing now
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
        g.setdefault("kind", "garden")
        g.setdefault("trays", 0)
        g.setdefault("watering", [])
        g.setdefault("water_every", None)
        g.setdefault("power_sensors", {})
        g.setdefault("energy", {})
        g.setdefault("energy_last", {})
        if g["kind"] != "garden":
            a = g.get("alarm") or {}
            g["alarm"] = {"enabled": bool(a.get("enabled")), "high": a.get("high"), "low": a.get("low"),
                          "events": dict(a.get("events") or {})}
        if g["kind"] == "greenhouse":
            g["climate"] = {**DEFAULT_CLIMATE, **(g.get("climate") or {})}
        g.setdefault("ec_target", list(DEFAULT_EC_TARGET))
        g.setdefault("moisture_band", list(DEFAULT_MOISTURE_BAND))
        g.setdefault("probe_depth", DEFAULT_PROBE_DEPTH)
        if not isinstance(g.get("sensors_paused"), dict):  # older versions stored one switch for everything
            g["sensors_paused"] = {k: True for k in METRICS} if g.get("sensors_paused") else {}

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
                   ph_min: float = 6.0, ph_max: float = 6.8, kind: str = "garden") -> str:
        if kind not in LOCATION_KINDS:
            raise GardenError("Type must be garden, rack or greenhouse")
        gid = self._unique(slug(name), self.data["gardens"])
        self.data["gardens"][gid] = {
            "id": gid, "name": name, "kind": kind, "ph_entity": ph_entity or None, "ph_target": [ph_min, ph_max],
            "adjunct_types": {a["key"]: dict(a) for a in DEFAULT_ADJUNCTS} if kind == "garden" else {},
            "adjuncts": [], "ph_readings": []}
        self._ensure_garden(self.data["gardens"][gid])
        self._touch(True)
        return gid

    def update_garden(self, ref: str, name: str | None = None, ph_entity: str | None = None,
                      ph_min: float | None = None, ph_max: float | None = None,
                      ec_min: float | None = None, ec_max: float | None = None,
                      moisture_min: float | None = None, moisture_max: float | None = None,
                      probe_depth: float | None = None) -> None:
        g = self.find_garden(ref)
        self._ensure_garden(g)
        elo, ehi = g["ec_target"]
        elo, ehi = (ec_min if ec_min is not None else elo), (ec_max if ec_max is not None else ehi)
        mlo, mhi = g["moisture_band"]
        mlo, mhi = (moisture_min if moisture_min is not None else mlo), (moisture_max if moisture_max is not None else mhi)
        if elo >= ehi or mlo >= mhi:
            raise GardenError("The low end of a range must be below the high end")
        g["ec_target"], g["moisture_band"] = [elo, ehi], [mlo, mhi]
        if probe_depth is not None:
            if probe_depth <= 0:
                raise GardenError("Probe depth must be above zero")
            g["probe_depth"] = probe_depth
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
                       wait_days: int | None = None, amount_lbs: float | None = None) -> str:
        g = self.find_garden(garden)
        crop = (crop or "").strip()
        if not crop:
            raise GardenError("Enter the cover crop")
        if amount_lbs is not None and amount_lbs <= 0:
            raise GardenError("Seed amount must be above zero")
        cid = new_id()
        g["cover_crops"].append({"id": cid, "crop": crop, "sown": iso(sown) or self.today().isoformat(),
                                 "terminated": None, "method": None, "notes": notes or "",
                                 "amount_lbs": round(amount_lbs, 2) if amount_lbs else None,
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

    # ---- seedling rack and greenhouse -------------------------------------------
    def _location(self, ref: str) -> dict:
        g = self.find_garden(ref)
        self._ensure_garden(g)
        if g["kind"] == "garden":
            raise GardenError(f"{g['name']} is a garden. This only works for a seedling rack or greenhouse")
        return g

    def set_trays(self, garden: str, trays: int) -> None:
        g = self._location(garden)
        if trays < 0 or trays > 500:
            raise GardenError("Trays must be between 0 and 500")
        g["trays"] = int(trays)
        self._touch()

    def log_watering(self, garden: str, when: Any = None, notes: str | None = None) -> None:
        g = self._location(garden)
        g["watering"].append({"id": new_id(), "date": iso(when) or self.today().isoformat(), "notes": notes or ""})
        self._touch()

    def set_water_interval(self, garden: str, days: int | None) -> None:
        g = self._location(garden)
        if days is not None and not 1 <= int(days) <= 60:
            raise GardenError("Water every must be between 1 and 60 days")
        g["water_every"] = int(days) if days else None
        self._touch()

    def set_climate(self, garden: str, enabled: bool | None = None, heat_set: float | None = None,
                    cool_set: float | None = None, heaters: list[str] | None = None,
                    coolers: list[str] | None = None, heat_min_run: int | None = None,
                    heat_max_run: int | None = None, heat_rest: int | None = None) -> None:
        g = self._location(garden)
        if g["kind"] != "greenhouse":
            raise GardenError("Heating and cooling control is for a greenhouse")
        c = g["climate"]
        heat = c["heat_set"] if heat_set is None else float(heat_set)
        cool = c["cool_set"] if cool_set is None else float(cool_set)
        if not 30 <= heat <= 110 or not 30 <= cool <= 130:
            raise GardenError("Set points must be between 30 and 130 °F")
        if cool - heat < CLIMATE_MIN_GAP:
            raise GardenError(f"The cool set point must be at least {CLIMATE_MIN_GAP:g} degrees above the heat set point")

        def clean(items):
            out: list[str] = []
            for e in items or []:
                e = str(e).strip()
                if e and e not in out:
                    out.append(e)
            return out
        if heaters is not None:
            c["heaters"] = clean(heaters)
        if coolers is not None:
            c["coolers"] = clean(coolers)
        if set(c["heaters"]) & set(c["coolers"]):
            raise GardenError("A device can't be both the heater and the cooler")
        mn = c.get("heat_min_run", 0) if heat_min_run is None else int(heat_min_run)
        mx = c.get("heat_max_run", 0) if heat_max_run is None else int(heat_max_run)
        rest = c.get("heat_rest", 10) if heat_rest is None else int(heat_rest)
        if not (0 <= mn <= 720 and 0 <= mx <= 720 and 0 <= rest <= 720):
            raise GardenError("Run times must be between 0 and 720 minutes")
        if mn and mx and mn > mx:
            raise GardenError("The minimum heater run time can't be longer than the maximum")
        c["heat_min_run"], c["heat_max_run"], c["heat_rest"] = mn, mx, rest
        c["heat_set"], c["cool_set"] = heat, cool
        if enabled is not None:
            c["enabled"] = bool(enabled)
        self._touch(True)

    def set_temp_alarm(self, garden: str, enabled: bool | None = None, high: Any = UNSET, low: Any = UNSET) -> None:
        """Warn when a rack or greenhouse gets hotter or colder than a limit. Turning it off clears any alarm."""
        g = self._location(garden)
        if g["kind"] == "garden":
            raise GardenError("Temperature alarms are for a seedling rack or greenhouse")
        a = g["alarm"]

        def limit(v):
            if v is None or v == "":
                return None
            v = float(v)
            if not -20 <= v <= 150:
                raise GardenError("Alarm limits must be between -20 and 150 °F")
            return v
        hi = a["high"] if high is UNSET else limit(high)
        lo = a["low"] if low is UNSET else limit(low)
        if hi is not None and lo is not None and hi - lo < 2:
            raise GardenError("The high limit must be at least 2 degrees above the low limit")
        on = a["enabled"] if enabled is None else bool(enabled)
        if on and hi is None and lo is None:
            raise GardenError("Set a high or low limit first")
        a["high"], a["low"], a["enabled"] = hi, lo, on
        if not on:
            a["events"] = {}
        else:  # a limit that was removed has nothing left to watch
            for kind, v in (("high", hi), ("low", lo)):
                if v is None:
                    a["events"].pop(kind, None)
        self._touch(True)
        self._alarm_changed()

    def ack_temp_alarm(self, garden: str, kind: str | None = None) -> None:
        """Acknowledge a temperature alarm. One that is still going stays quiet until the air has been back in range."""
        g = self._location(garden)
        if g["kind"] == "garden":
            raise GardenError("Temperature alarms are for a seedling rack or greenhouse")
        ev = g["alarm"]["events"]
        for k in ([kind] if kind else ["high", "low"]):
            e = ev.get(k)
            if not e:
                continue
            if e.get("end"):
                del ev[k]
            else:
                e["acked"] = True
        self._touch(True)

    def update_alarm(self, garden_id: str, temp: float, now: Any) -> bool:
        """Feed in the latest air temperature. Returns True when an alarm started, changed or ended."""
        g = self.data["gardens"].get(garden_id)
        if not g or g.get("kind") == "garden" or not g["alarm"]["enabled"]:
            return False
        a, changed = g["alarm"], False
        stamp = now.isoformat()
        for kind, lim in (("high", a["high"]), ("low", a["low"])):
            if lim is None:
                continue
            sign = 1 if kind == "high" else -1
            out, back = sign * (temp - lim) > 0, sign * (temp - lim) <= -ALARM_BACK_F
            e = a["events"].get(kind)
            if out:
                if e is None or e.get("end"):
                    new = {"start": stamp, "end": None, "peak": round(temp, 1), "acked": False}
                    if e:  # the last time out of range was never acknowledged, so keep a count of it
                        new["prior_n"] = e.get("prior_n", 0) + 1
                        new["prior_s"] = e.get("prior_s", 0) + int((datetime.fromisoformat(e["end"])
                                                                   - datetime.fromisoformat(e["start"])).total_seconds())
                    a["events"][kind] = new
                    changed = True
                elif sign * (temp - e["peak"]) > 0:
                    e["peak"], changed = round(temp, 1), True
            elif back and e and not e.get("end"):
                if e.get("acked"):
                    del a["events"][kind]  # it was acknowledged, so there is nothing left to show
                else:
                    e["end"] = stamp
                changed = True
        return changed

    def _alarm_changed(self) -> None:
        """Hook for the manager: check the temperature against the limits now."""

    def _alarm_view(self, g: dict) -> dict:
        a = g["alarm"]
        alerts, quiet = [], []
        for kind in ("high", "low"):
            e = a["events"].get(kind)
            if not e:
                continue
            if e.get("acked"):
                quiet.append(kind)
            else:
                alerts.append({"kind": kind, "start": e["start"], "end": e.get("end"), "peak": e["peak"],
                               "ongoing": not e.get("end"), "prior_n": e.get("prior_n", 0),
                               "prior_s": e.get("prior_s", 0)})
        alerts.sort(key=lambda x: (not x["ongoing"], x["start"]))
        return {"enabled": a["enabled"], "high": a["high"], "low": a["low"], "alerts": alerts, "acknowledged": quiet}

    def set_power_sensors(self, garden: str, group: str, entities: list[str]) -> None:
        g = self._location(garden)
        groups = POWER_GROUPS.get(g["kind"], {})
        if group not in groups:
            raise GardenError("Group must be " + ", ".join(groups))
        clean: list[str] = []
        for e in entities or []:
            e = str(e).strip()
            if e and e not in clean:
                clean.append(e)
        if clean:
            g["power_sensors"][group] = clean
        else:
            g["power_sensors"].pop(group, None)
        for e in list(g["energy_last"]):
            if not any(e in v for v in g["power_sensors"].values()):
                del g["energy_last"][e]
        self._touch(True)
        self._power_changed()

    def set_power_rate(self, cents: float | None) -> None:
        """Price of electricity in cents per kWh, used to put a dollar figure on power use. 0 clears it."""
        if cents is not None and not 0 <= cents <= 1000:
            raise GardenError("Rate must be between 0 and 1000 cents per kWh")
        self.data["settings"]["rate_cents"] = round(float(cents), 4) if cents else None
        self._touch(True)

    def _power_changed(self) -> None:
        """Hook for the manager: sample the power sensors now."""

    def record_energy(self, g: dict, group: str, kwh: float) -> None:
        """Add energy used (kWh) to today's total for a place. Keeps about a year and a half of days."""
        if kwh <= 0:
            return
        day = self.today().isoformat()
        bucket = g["energy"].setdefault(group, {})
        bucket[day] = round(bucket.get(day, 0.0) + kwh, 4)
        if len(bucket) > 550:
            for old in sorted(bucket)[:-550]:
                del bucket[old]

    def _power_view(self, g: dict, today: date) -> dict | None:
        groups = POWER_GROUPS.get(g.get("kind"), {})
        sensors = g.get("power_sensors", {})
        if not any(sensors.get(k) for k in groups):
            return None
        day, month = today.isoformat(), today.isoformat()[:7]
        rows, total_days = [], {}
        for key, name in groups.items():
            if not sensors.get(key):
                continue
            b = g.get("energy", {}).get(key, {})
            rows.append({"key": key, "name": name, "entities": list(sensors[key]),
                         "today": round(b.get(day, 0.0), 2),
                         "month": round(sum(v for d, v in b.items() if d.startswith(month)), 2)})
            for d, v in b.items():
                total_days[d] = total_days.get(d, 0.0) + v
        days = [{"date": (today - timedelta(days=i)).isoformat(),
                 "kwh": round(total_days.get((today - timedelta(days=i)).isoformat(), 0.0), 2)} for i in range(29, -1, -1)]
        months: dict[str, float] = {}
        for d, v in total_days.items():
            months[d[:7]] = months.get(d[:7], 0.0) + v
        rate = self.data["settings"].get("rate_cents")

        def cost(kwh: float) -> float | None:
            return None if not rate else round(kwh * rate / 100, 2)
        for r in rows:
            r["today_cost"], r["month_cost"] = cost(r["today"]), cost(r["month"])
        total_today, total_month = sum(r["today"] for r in rows), sum(r["month"] for r in rows)
        for d in days:
            d["cost"] = cost(d["kwh"])
        return {"unit": "kWh", "groups": rows, "today": round(total_today, 2), "month": round(total_month, 2),
                "rate": rate, "today_cost": cost(total_today), "month_cost": cost(total_month), "days": days,
                "months": [{"month": m, "kwh": round(v, 1), "cost": cost(v)} for m, v in sorted(months.items())[-12:]]}

    def _trays_calc(self, g: dict) -> dict:
        """How many 10x20 trays the plants here would fill, from each pot or tray size."""
        counts: dict[str, int] = {}
        unknown = 0
        for v in self.data["varieties"].values():
            if v["garden"] != g["id"] or v.get("archived") or v["kind"] == "tree":
                continue
            alive = sum(1 for p in v["plants"] if p["status"] == "alive")
            c = v.get("container")
            if c in CONTAINER_PER_TRAY:
                counts[c] = counts.get(c, 0) + alive
            else:
                unknown += alive
        rows = [{"container": c, "plants": n, "per_tray": CONTAINER_PER_TRAY[c], "trays": -(-n // CONTAINER_PER_TRAY[c])}
                for c, n in counts.items() if n]
        return {"total": sum(r["trays"] for r in rows), "rows": rows, "unknown": unknown}

    def up_pot(self, ref: str, container: str, when: Any = None) -> None:
        v = self.find_variety(ref)
        container = (container or "").strip()
        if not container:
            raise GardenError("Pick the new pot or tray")
        v["upotted"].append({"id": new_id(), "date": iso(when) or self.today().isoformat(),
                             "container": container, "from": v.get("container")})
        v["container"] = container
        self._touch()

    def move_plants(self, ref: str, to: str, count: int | None = None, when: Any = None) -> str:
        """Move a planting, or some of its living plants, to another garden, rack or greenhouse.

        Moving only some plants splits them into a new planting with the same history."""
        v = self.find_variety(ref)
        dest = self.find_garden(to)
        if dest["id"] == v["garden"]:
            raise GardenError("Those plants are already there")
        src = self.data["gardens"].get(v["garden"]) or {}
        day = iso(when) or self.today().isoformat()
        alive = [p for p in v["plants"] if p["status"] == "alive"]
        if not alive:
            raise GardenError("No living plants to move")
        n = len(alive) if count is None else int(count)
        if n < 1:
            raise GardenError("Move at least one plant")
        if n > len(alive):
            raise GardenError(f"Only {len(alive)} living plants to move")
        move = {"id": new_id(), "date": day, "from": src.get("name", v["garden"]), "to": dest["name"], "count": n}
        target = v
        if n < len(alive):
            moving = alive[-n:]
            ids = {p["id"] for p in moving}
            nid = self._unique(slug(v["name"]), self.data["varieties"])
            clone = copy.deepcopy(v)
            clone.update(id=nid, plants=moving, harvests=[], fertilizations=[], sprays=[], reviews=[],
                         upotted=copy.deepcopy(v["upotted"]), moves=copy.deepcopy(v.get("moves", [])))
            v["plants"] = [p for p in v["plants"] if p["id"] not in ids]
            self.data["varieties"][nid] = clone
            target = clone
        target["garden"] = dest["id"]
        target.setdefault("moves", []).append(move)
        if dest.get("kind", "garden") == "garden" and not target.get("in_ground"):
            target["in_ground"] = day
        self._touch(True)
        return target["id"]

    PAUSE_GROUPS = {"moisture_ec": ("moisture", "ec"), "soil_temp": ("soil_temp",),
                    "air_temp": ("air_temp",), "par": ("par",), "all": tuple(METRICS)}

    def set_sensors_paused(self, garden: str, paused: bool, group: str = "all") -> None:
        """Ignore sensor readings while the probes are out of the ground.

        Groups: moisture_ec (the moisture and EC probe), soil_temp, or all."""
        g = self.find_garden(garden)
        self._ensure_garden(g)
        if group not in self.PAUSE_GROUPS:
            raise GardenError("Group must be moisture_ec, soil_temp, air_temp, par or all")
        for k in self.PAUSE_GROUPS[group]:
            g["sensors_paused"][k] = bool(paused)
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
        if not g or not spec or g.get("sensors_paused", {}).get(metric) or not spec["lo"] <= value <= spec["hi"]:
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
                    multi_year: bool | None = None, container: str | None = None) -> str:
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
            "container": (container or "").strip() or None, "moves": [],
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
                       single_harvest: bool | None = None, multi_year: bool | None = None,
                       container: str | None = None) -> None:
        v = self.find_variety(ref)
        if container is not None:
            v["container"] = container.strip() or None
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
            elif kind == "cover" and key == "amount_lbs":
                if val < 0:
                    raise GardenError("Seed amount can't be negative")
                e[key] = round(val, 2) if val else None
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
                "containers": list(DEFAULT_CONTAINERS), "container_per_tray": dict(CONTAINER_PER_TRAY),
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
        kind = g.get("kind", "garden")
        metrics = {k: self._metric_view(g, k) for k in METRIC_SETS[kind]}
        soil = kind == "garden"
        return {
            "id": g["id"], "name": g["name"], "kind": kind, "kind_name": LOCATION_KINDS[kind], "metrics": metrics,
            "planting": self._planting_view(metrics["soil_temp"]) if soil else None,
            "cover": self._cover_view(g, today),
            "frost": self._frost_view(g, today),
            "paused": {k: bool(g.get("sensors_paused", {}).get(k)) for k in METRICS},
            "fertility": self._fertility_view(g, metrics, today) if soil else None,
            "trays": g.get("trays", 0), "water": self._water_view(g, today),
            "trays_calc": self._trays_calc(g) if kind != "garden" else None,
            "power": self._power_view(g, today) if kind != "garden" else None,
            "power_groups": POWER_GROUPS.get(kind, {}), "power_sensors": {k: list(v) for k, v in g.get("power_sensors", {}).items()},
            "climate": self._climate_view(g, metrics) if kind == "greenhouse" else None,
            "alarm": self._alarm_view(g) if kind != "garden" else None,
            "ph": {"entity": g.get("ph_entity"), "current": cur and cur["value"], "date": cur and cur["date"],
                   "source": cur and cur["source"], "target": [lo, hi], "level": level,
                   "first": first and {"date": first["date"], "value": first["value"]}, "history": hist},
            "adjuncts": [calc.adjunct_status(t, g["adjuncts"], today) for t in g["adjunct_types"].values()],
            "adjunct_log": [{**e, "type_name": names.get(e["type"], e["type"])} for e in log],
        }

    @staticmethod
    def _water_view(g: dict, today: date) -> dict:
        log = sorted(g.get("watering", []), key=lambda e: (e["date"], e["id"]), reverse=True)
        last = log[0]["date"] if log else None
        since = calc.days_since(last, today)
        every = g.get("water_every")
        level = None
        if every:
            level = "none" if since is None else ("due" if since >= every else ("soon" if since >= every - 1 else "ok"))
        return {"last": last, "days_since": since, "every": every, "level": level, "log": log[:60]}

    def _climate_view(self, g: dict, metrics: dict) -> dict:
        c = g.get("climate") or dict(DEFAULT_CLIMATE)
        st = self.climate_state.get(g["id"], {})
        return {**c, "temp": metrics["air_temp"]["current"], "state": st.get("state", "off" if not c["enabled"] else "idle"),
                "gap": CLIMATE_MIN_GAP}

    def _fertility_view(self, g: dict, metrics: dict, today: date) -> dict:
        """Judge soil EC (fertility) together with moisture, for the top few inches the probe can see."""
        elo, ehi = g.get("ec_target", DEFAULT_EC_TARGET)
        mlo, mhi = g.get("moisture_band", DEFAULT_MOISTURE_BAND)
        ec, mo = metrics["ec"], metrics["moisture"]
        out = {"ec_target": [elo, ehi], "moisture_band": [mlo, mhi], "depth": g.get("probe_depth", DEFAULT_PROBE_DEPTH),
               "ec": ec["current"], "moisture": mo["current"], "level": None, "moisture_state": None,
               "advice": None, "action": None, "ec_change": None, "last_fed": None}
        fed = [f["date"] for v in self.data["varieties"].values() if v["garden"] == g["id"]
               and not v.get("archived") for f in v.get("fertilizations", [])]
        out["last_fed"] = max(fed) if fed else None
        out["probes_out"] = bool(g.get("sensors_paused", {}).get("ec") or g.get("sensors_paused", {}).get("moisture"))
        out["paused"] = out["probes_out"] or any(not c.get("terminated") for c in g.get("cover_crops", []))
        if ec["current"] is None:
            return out
        e = ec["current"]
        out["level"] = "low" if e < elo else ("high" if e > ehi else "ok")
        if mo["current"] is not None:
            m = mo["current"]
            out["moisture_state"] = "dry" if m < mlo else ("wet" if m > mhi else "ok")
        ms = out["moisture_state"]
        depth = out["depth"]
        depth = int(depth) if float(depth).is_integer() else depth
        week = [r for r in ec["history"] if (today - date.fromisoformat(r["date"])).days <= 14]
        if len(week) >= 2:
            out["ec_change"] = round(e - week[0]["value"], 2)
        lvl = out["level"]
        if out["paused"]:
            return out  # a cover crop is growing, so there is no feeding or watering advice
        if lvl == "ok":
            out["action"], out["advice"] = "ok", f"Fertility is in range in the top {depth} in. No feeding needed."
        elif lvl == "low":
            if ms == "wet":
                out["action"] = "recheck"
                out["advice"] = "EC reads low, but the soil is wet and that lowers the reading. Check again once it drains."
            else:
                out["action"] = "feed"
                out["advice"] = f"Fertility is low in the top {depth} in. Consider feeding."
        else:
            if ms == "dry":
                out["action"] = "recheck"
                out["advice"] = "EC reads high, but the soil is dry and that raises the reading. Water, then check again."
            else:
                out["action"] = "hold"
                out["advice"] = f"Salts are high in the top {depth} in. Skip fertilizer and water deeply to flush them."
        if ms is None and out["action"] in ("feed", "hold"):
            out["advice"] += " Add a moisture reading to confirm."
        return out

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
        # Seed mix: share of the pounds sown when more than one crop with an amount is in the ground together.
        parts = [i for i in live if i.get("amount_lbs")]
        total = sum(i["amount_lbs"] for i in parts)
        mix = None
        if len(parts) >= 2:
            mix = {"total_lbs": round(total, 2),
                   "parts": [{"id": i["id"], "crop": i["crop"], "lbs": i["amount_lbs"],
                              "pct": round(100 * i["amount_lbs"] / total)} for i in parts]}
            for p in mix["parts"]:
                next(i for i in items if i["id"] == p["id"])["mix_pct"] = p["pct"]
        return {"items": live + done, "blocked": blocked, "presets": COVER_CROPS, "methods": COVER_METHODS,
                "mix": mix}

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
            "container": v.get("container"), "moves": sorted(v.get("moves", []), key=lambda m: (m["date"], m["id"]), reverse=True),
            "location_kind": (g or {}).get("kind", "garden"),
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
