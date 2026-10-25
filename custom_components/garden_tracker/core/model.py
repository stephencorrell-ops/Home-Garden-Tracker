"""Pure data model and business logic. No Home Assistant imports, so it can be unit tested."""
from __future__ import annotations

import copy
import re
import time
import uuid
from datetime import date, datetime, timedelta
from typing import Any, Callable

from . import calc
from . import irrigation as irr
from . import layout as lay
from . import rotation as rot
from . import microclimate as mc
from . import season as season_mod
from . import sun as sun_mod


DEFAULT_SETTINGS = {"frost_last": "04-25", "frost_first": "10-15",  # Ephrata, WA averages
                    "usda_zone": "7a (6b on the 2012 map)", "frost_f": mc.FROST_F,
                    "location": None, "temp_entities": [], "rain_entities": [], "humidity_entities": [], "solar_entities": [],
                    "air_entities": {"pm1": [], "pm25": [], "pm10": [], "nox": [], "voc": []}}
SENSOR_ALARM_AFTER = timedelta(hours=1)  # how long an in-use sensor may report nothing before it alarms
ALARM_BACK_F = 1.0  # the air must come back this far inside a limit before an alarm counts as over
UNSET: Any = object()
SAMPLE_SLOT_S = 900                 # temperature readings are kept every 15 minutes...
SAMPLE_KEEP_S = 8 * 86400           # ...for eight days, to draw the last 24 hours and the week
SAMPLED = ("soil_temp", "air_temp", "out_temp")
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
    "out_temp": {"name": "Outside temperature", "unit": "°F", "lo": -60, "hi": 150},
    "par": {"name": "Light (PAR)", "unit": "µmol/m²/s", "lo": 0, "hi": 4000},
}
# Places plants live. A garden has soil; the seedling rack and greenhouse are indoor, so they track
# air temperature (and light on the rack), watering and 10x20 trays instead of soil and fertilizer.
LOCATION_KINDS = {"garden": "Garden", "rack": "Seedling rack", "greenhouse": "Greenhouse"}
METRIC_SETS = {"garden": ("moisture", "ec", "soil_temp", "out_temp"), "rack": ("air_temp", "par"),
               "greenhouse": ("air_temp", "out_temp")}
DEFAULT_CONTAINERS = ["6-cell tray", "4-cell tray", "3.3 in pot", "5 in pot"]
# How many fit in one 10x20 tray (Bootstrap Farmer sizes): 12 six-cell inserts, 8 four-cell inserts, and the pot inserts.
CONTAINER_PER_TRAY = {"6-cell tray": 72, "4-cell tray": 32, "3.3 in pot": 18, "5 in pot": 8}
POWER_GROUPS = {"greenhouse": {"heat": "Heating", "cool": "Fans"}, "rack": {"power": "Lights and power"}}
DEFAULT_CLIMATE = {"enabled": False, "heat_set": 60.0, "cool_set": 80.0, "heaters": [], "coolers": [],
                   "heat_min_run": 0, "heat_max_run": 0, "heat_rest": 10,
                   # fans switch on above cool_set and off at cool_off (None = one degree below cool_set)
                   "cool_off": None, "fan_min_run": 0,
                   # heaters switch on below heat_set and off at heat_off (None = one degree above heat_set)
                   "heat_off": None,
                   # grow lights (seedling rack): on for light_hours a day, starting at light_on
                   "lights": [], "light_sched": False, "light_on": "06:00", "light_hours": 16.0,
                   # fans also run on a schedule: fan_minutes at the start of every fan_every hours
                   "fan_sched": False, "fan_minutes": 5, "fan_every": 6.0, "fan_lights_only": False}
RACK_CLIMATE = {**DEFAULT_CLIMATE, "heat_set": 70.0, "cool_set": 82.0, "fan_lights_only": True}
CLIMATE_KINDS = ("greenhouse", "rack")
TIME_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


def _minutes(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def lights_on_at(c: dict, minute: int) -> bool:
    """Whether the grow lights should be on at this minute of the day (0 to 1439)."""
    return (minute - _minutes(c["light_on"])) % 1440 < c["light_hours"] * 60


def fan_on_at(c: dict, minute: int) -> bool:
    """Whether the scheduled fan run is on now: fan_minutes at the start of each fan_every hours, counted
    from the lights-on time when there is a light schedule, otherwise from midnight."""
    if c["fan_lights_only"] and c["light_sched"] and not lights_on_at(c, minute):
        return False
    anchor = _minutes(c["light_on"]) if c["light_sched"] else 0
    return ((minute - anchor) % 1440) % (c["fan_every"] * 60) < c["fan_minutes"]
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
# Rule-of-thumb minimum soil temperatures (°F) for sowing or transplanting, and how long each takes to grow.
PLANTING_TEMPS = [  # (crops, minimum soil °F, days from planting to harvest)
    ("Peas, spinach, lettuce", 40, 50), ("Carrots, beets, onions", 45, 75), ("Potatoes", 45, 90),
    ("Corn, beans", 60, 70), ("Tomatoes", 60, 75), ("Peppers, squash, cucumbers", 65, 70), ("Melons", 70, 85),
]
KINDS = {  # entry kind -> (parent type, list key)
    "harvest": ("v", "harvests"), "fertilizer": ("v", "fertilizations"), "spray": ("v", "sprays"),
    "review": ("v", "reviews"), "upotted": ("v", "upotted"),
    "adjunct": ("g", "adjuncts"), "ph": ("g", "ph_readings"),
    "moisture": ("g", "moisture"), "ec": ("g", "ec"), "soil_temp": ("g", "soil_temp"),
    "cover": ("g", "cover_crops"), "water": ("g", "watering"), "acid": ("g", "acid_log"),
    "air_temp": ("g", "air_temp"), "par": ("g", "par"), "out_temp": ("g", "out_temp"),
}
EDITABLE = {
    "harvest": ("lbs", "date", "notes"),
    "fertilizer": ("product", "n", "p", "k", "date", "notes"),
    "spray": ("product", "target", "phi_days", "reapply_days", "date"),
    "review": ("notes", "year"), "upotted": ("date",),
    "adjunct": ("type", "product", "amount", "date", "notes"), "ph": ("value", "date"),
    "moisture": ("value", "date"), "ec": ("value", "date"), "soil_temp": ("value", "date"),
    "air_temp": ("value", "date"), "par": ("value", "date"), "out_temp": ("value", "date"), "water": ("date", "notes"),
    "acid": ("date", "ml", "g", "water_gal", "ph_before", "ph_after", "notes", "product"),
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
        self.data: dict[str, Any] = {"gardens": {}, "varieties": {}, "species": {}, "daily": {}, "rain": {}, "rain_src": {}, "humid": {}, "solar": {}, "air": {"q": {}, "h": {}, "d": {}},
                                    "settings": dict(DEFAULT_SETTINGS), "variety_traits": {}, "crop_days": {}}
        self.presets = presets
        self._air_now: dict[str, tuple[float, float]] = {}
        self._air_touched = 0.0
        self.now_fn: Callable[[], float] = time.time  # seconds since the epoch; the manager sets a Home Assistant clock
        self.home_lat: float | None = None  # Home Assistant's own latitude, used when no location was set
        self.outdoor_entity: str | None = None  # the main outdoor temperature sensor, used when a place has none of its own
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
        self.data["settings"] = {**copy.deepcopy(DEFAULT_SETTINGS), **(self.data.get("settings") or {})}
        for tier in ("q", "h", "d"):
            self.data["air"].setdefault(tier, {})
        self.data["settings"].setdefault("air_entities", {})
        for m in mc.AIR:
            self.data["settings"]["air_entities"].setdefault(m, [])
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
        g.setdefault("layout", None)
        g.setdefault("layout_history", {})
        g.setdefault("irrigation", None)
        g.setdefault("acid_log", [])
        g.setdefault("watering", [])
        g.setdefault("water_every", None)
        g.setdefault("power_sensors", {})
        g.setdefault("energy", {})
        g.setdefault("energy_last", {})
        g.setdefault("samples", {})
        sa = g.get("sensor_alarm") or {}
        g["sensor_alarm"] = {"enabled": sa.get("enabled", True), "down": dict(sa.get("down") or {})}
        if g["kind"] != "garden":
            a = g.get("alarm") or {}
            g["alarm"] = {"enabled": bool(a.get("enabled")), "high": a.get("high"), "low": a.get("low"),
                          "events": dict(a.get("events") or {})}
        if g["kind"] in CLIMATE_KINDS:
            g["climate"] = {**(RACK_CLIMATE if g["kind"] == "rack" else DEFAULT_CLIMATE), **(g.get("climate") or {})}
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

    def merge_daily(self, rows: dict[str, tuple[float, float]]) -> bool:
        """Fill in daily lows and highs from Home Assistant's long-term statistics. Live readings are kept."""
        changed = False
        for k, (lo, hi) in rows.items():
            cur = self.data["daily"].get(k)
            new = [round(lo, 1), round(hi, 1)] if cur is None else [min(cur[0], round(lo, 1)), max(cur[1], round(hi, 1))]
            if new != cur:
                self.data["daily"][k] = new
                changed = True
        if changed:
            self._touch()
        return changed

    # ---- rain: every sensor keeps its own daily amounts, and a day's rain is their average -----------
    def _rain_day(self, k: str) -> None:
        vals = [self.data["rain_src"][e][k] for e in self.data["settings"]["rain_entities"]
                if k in self.data["rain_src"].get(e, {})]
        if vals and sum(vals) > 0:
            self.data["rain"][k] = round(sum(vals) / len(vals), 3)
        else:
            self.data["rain"].pop(k, None)

    def rebuild_rain(self) -> None:
        days = {k for src in self.data["rain_src"].values() for k in src} | set(self.data["rain"])
        for k in days:
            self._rain_day(k)

    def merge_rain(self, entity: str, rows: dict[str, float]) -> bool:
        src = self.data["rain_src"].setdefault(entity, {})
        changed = False
        for k, v in rows.items():
            if v > 0 and v > src.get(k, 0):
                src[k] = round(v, 3)
                self._rain_day(k)
                changed = True
        if changed:
            self._touch()
        return changed

    def add_rain(self, entity: str, inches: float) -> None:
        """Add rain that just fell (inches) to today's total for one sensor."""
        if inches <= 0:
            return
        key = self.today().isoformat()
        src = self.data["rain_src"].setdefault(entity, {})
        src[key] = round(src.get(key, 0) + inches, 3)
        self._rain_day(key)
        self._touch()

    def record_humidity(self, pct: float) -> None:
        key = self.today().isoformat()
        cur = self.data["humid"].get(key)
        new = [pct, pct] if cur is None else [min(cur[0], pct), max(cur[1], pct)]
        if new != cur:
            self.data["humid"][key] = new
            self._touch()

    def merge_humid(self, rows: dict[str, tuple[float, float]]) -> bool:
        changed = False
        for k, (lo, hi) in rows.items():
            cur = self.data["humid"].get(k)
            new = [round(lo, 1), round(hi, 1)] if cur is None else [min(cur[0], round(lo, 1)), max(cur[1], round(hi, 1))]
            if new != cur:
                self.data["humid"][k] = new
                changed = True
        if changed:
            self._touch()
        return changed

    def record_solar(self, w_m2: float, wh: float = 0.0, secs: float = 0.0) -> None:
        """Today's brightest reading, the energy (Wh/m2) that fell since the last one, and the time it covers."""
        key = self.today().isoformat()
        cur = list(self.data["solar"].get(key) or [0.0, 0.0, 0.0])
        cur += [0.0] * (3 - len(cur))
        new = [max(cur[0], round(w_m2, 1)), round(cur[1] + max(wh, 0.0), 2), round(cur[2] + max(secs, 0.0))]
        if new != cur:
            self.data["solar"][key] = new
            self._touch()

    def merge_solar(self, rows: dict[str, tuple[float, float]]) -> bool:
        changed = False
        for k, (peak, wh) in rows.items():
            if k >= self.today().isoformat():  # today is measured live, a part-day statistic would skew it
                continue
            cur = self.data["solar"].get(k)
            new = [round(peak, 1), round(wh, 1), 86400] if cur is None else [
                max(cur[0], round(peak, 1)), max(cur[1], round(wh, 1)), max(cur[2] if len(cur) > 2 else 86400, 86400)]
            if cur is not None and cur[1] >= round(wh, 1):  # what was measured live is kept as it is
                new = cur
            if new != cur:
                self.data["solar"][k] = new
                changed = True
        if changed:
            self._touch()
        return changed

    # ---- air quality: 15 minute averages for a day, hourly for a week, daily (with the day's highest) for a month ----
    def record_air(self, metric: str, value: float) -> None:
        if metric not in mc.AIR:
            return
        now = self.now_fn()
        self._air_now[metric] = (now, value)
        air = self.data["air"]
        for tier, key in (("q", str(int(now // 900 * 900))), ("h", str(int(now // 3600 * 3600))), ("d", self.today().isoformat())):
            slot = air[tier].setdefault(f"{metric}|{key}", [0.0, 0, value])
            slot[0] += value
            slot[1] += 1
            slot[2] = max(slot[2], value)
        if now - self._air_touched >= 60:  # readings can arrive every second; update everything once a minute
            self._air_touched = now
            self._prune_air(now)
            self._touch()

    def _prune_air(self, now: float) -> None:
        air = self.data["air"]
        for tier, keep in (("q", 2 * 86400), ("h", 9 * 86400)):
            for k in [k for k in air[tier] if float(k.split("|")[1]) < now - keep]:
                del air[tier][k]
        cut = (self.today() - timedelta(days=400)).isoformat()
        for k in [k for k in air["d"] if k.split("|")[1] < cut]:
            del air["d"][k]

    def merge_air(self, metric: str, rows: dict[int, tuple[float, float]]) -> bool:
        """Fill in hours (and the days they make up) from long-term statistics: {hour start: (mean, highest)}."""
        air, changed, days = self.data["air"], False, {}
        for ts, (mean, hi) in rows.items():
            key = f"{metric}|{int(ts)}"
            if key not in air["h"]:
                air["h"][key] = [round(mean, 2), 1, round(hi, 2)]
                changed = True
            day = self._local_day(ts)
            days.setdefault(day, []).append((mean, hi))
        for day, hrs in days.items():
            key = f"{metric}|{day}"
            if key not in air["d"] and day != self.today().isoformat():
                air["d"][key] = [round(sum(m for m, _ in hrs), 2), len(hrs), round(max(h for _, h in hrs), 2)]
                changed = True
        if changed:
            self._touch()
        return changed

    def _local_day(self, ts: float) -> str:
        return datetime.fromtimestamp(ts).date().isoformat()

    def _air_view(self, today: date) -> dict:
        st, air, now = self.data["settings"], self.data["air"], self.now_fn()
        out: dict[str, Any] = {"sensors": st["air_entities"], "metrics": {}}
        for m, (name, unit) in mc.AIR.items():
            def rows(tier, lo):
                return sorted((k.split("|")[1], v) for k, v in air[tier].items() if k.startswith(m + "|") and k.split("|")[1] >= lo)
            day = [[int(k), round(v[0] / v[1], 1)] for k, v in rows("q", str(int(now - 86400))) if float(k) >= now - 86400]
            week = [[int(k), round(v[0] / v[1], 1), round(v[2], 1)] for k, v in rows("h", "0") if float(k) >= now - 7 * 86400]
            month = [[k, round(v[0] / v[1], 1), round(v[2], 1)] for k, v in rows("d", (today - timedelta(days=29)).isoformat())]
            cur = self._air_now.get(m)
            out["metrics"][m] = {
                "name": name, "unit": unit, "current": round(cur[1], 1) if cur and now - cur[0] <= 3600 else None,
                "day": day, "week": week, "month": month,
                "max": {"today": next((r[2] for r in month if r[0] == today.isoformat()), None),
                        "week": max((r[2] for r in week), default=None),
                        "month": max((r[2] for r in month), default=None)}}
        return out

    def set_location(self, lat: float | None, lon: float | None, name: str | None = None) -> None:
        """Where the garden is, for apps that get local weather from a service instead of your own sensors."""
        if lat is None or lon is None:
            self.data["settings"]["location"] = None
        else:
            if not (-90 <= lat <= 90 and -180 <= lon <= 180):
                raise GardenError("That is not a place on the map")
            self.data["settings"]["location"] = {"lat": round(float(lat), 4), "lon": round(float(lon), 4),
                                                 "name": (name or "").strip()[:60] or None}
        self._touch()

    def set_microclimate(self, usda_zone: Any = UNSET, frost_f: float | None = None, temp_entities: Any = UNSET,
                         rain_entities: Any = UNSET, humidity_entities: Any = UNSET, solar_entities: Any = UNSET,
                         air_entities: Any = UNSET) -> None:
        st = self.data["settings"]
        if usda_zone is not UNSET:
            st["usda_zone"] = (str(usda_zone).strip()[:40] or None) if usda_zone is not None else None
        if frost_f is not None:
            if not 20 <= float(frost_f) <= 40:
                raise GardenError("Frost is between 20 and 40 °F")
            st["frost_f"] = float(frost_f)
        for key, val in (("temp_entities", temp_entities), ("rain_entities", rain_entities),
                         ("humidity_entities", humidity_entities), ("solar_entities", solar_entities)):
            if val is not UNSET:
                ids = [val] if isinstance(val, str) else list(val or [])
                st[key] = list(dict.fromkeys(i.strip() for i in ids if i and i.strip()))
        if air_entities is not UNSET:
            for m in mc.AIR:
                ids = (air_entities or {}).get(m, [])
                ids = [ids] if isinstance(ids, str) else list(ids or [])
                st["air_entities"][m] = list(dict.fromkeys(i.strip() for i in ids if i and i.strip()))
        self.rebuild_rain()
        self._touch(True)
        self._micro_changed()

    def _micro_changed(self) -> None:
        """Hook for the manager: watch the rain sensor that was chosen and pull its history."""

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
        name = (name or "").strip()
        if not name:
            raise GardenError("Give it a name")
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

    def _recorded_frost(self, g: dict, today: date) -> dict:
        """First and last frost this year as your sensors recorded them: the garden's own outside sensors if it
        has some, otherwise the main outdoor sensor."""
        thr = self.data["settings"].get("frost_f", mc.FROST_F)
        rows, own = self.data["daily"], bool(g.get("sensors", {}).get("out_temp"))
        if own:
            rows = {r["date"]: [r.get("min", r["value"]), r.get("max", r["value"])] for r in g.get("out_temp", [])
                    if r["source"] == "sensor"} or rows
        yrs = {y["year"]: y for y in mc.frost_years(rows, today, thr)}
        cur = yrs.get(today.year)
        prev = yrs.get(today.year - 1)
        return {"year": today.year, "threshold": thr, "source": "garden" if own and rows is not self.data["daily"] else "main",
                "last_spring": cur and cur["last_spring"], "spring_final": bool(cur and cur["spring_final"]),
                "spring_partial": bool(cur and cur["spring_partial"]),
                "first_fall": cur and cur["first_fall"],
                "last_year": prev and {"last_spring": prev["last_spring"], "first_fall": prev["first_fall"]}}

    def _micro_view(self, today: date) -> dict:
        st, daily, rain = self.data["settings"], self.data["daily"], self.data["rain"]
        thr = st.get("frost_f", mc.FROST_F)
        per = mc.periods(today)
        gardens = [g for g in self.data["gardens"].values() if g.get("kind", "garden") == "garden"]
        actual, last_year = [], []
        for g in gardens:
            hist = sorted(g.get("soil_temp", []), key=lambda r: (r["date"], r["id"]))
            if hist and not g.get("sensors_paused", {}).get("soil_temp"):
                cur = hist[-1]
                if (today - date.fromisoformat(cur["date"])).days <= 2:
                    actual.append(cur.get("last", cur["value"]))
            ly = mc.soil_last_year(hist, today)
            if ly is not None:
                last_year.append(ly)
        avg = lambda xs: round(sum(xs) / len(xs), 1) if xs else None
        exp = mc.expected_soil(daily, today)
        act = avg(actual)
        zone = mc.local_zone(daily, today)
        return {
            "zone": {**zone, "usda": st.get("usda_zone")},
            "frost": {"threshold": thr, "years": mc.frost_years(daily, today, thr)[:6],
                      "expected_last": st["frost_last"], "expected_first": st["frost_first"],
                      "first_data": min(daily) if daily else None},
            "temps": {k: mc.temp_range(daily, a, b) for k, (a, b) in per.items()},
            "rain": {"sensors": st["rain_entities"], "days_recorded": len(rain),
                     **{k: mc.rain_total(rain, a, b) for k, (a, b) in per.items()}},
            "soil": {"actual": act, "expected": exp, "last_year": avg(last_year),
                     "diff": None if act is None or exp is None else round(act - exp, 1)},
            "humidity": {"sensors": st["humidity_entities"],
                         **{k: mc.temp_range(self.data["humid"], a, b) for k, (a, b) in per.items()}},
            "air": self._air_view(today),
            "solar": {"sensors": st["solar_entities"], **{k: mc.solar_total(self.data["solar"], a, b) for k, (a, b) in per.items()}},
            "settings": {"usda_zone": st.get("usda_zone"), "frost_f": thr, "location": st.get("location"), "outdoor_entity": self.outdoor_entity,
                         "temp_entities": st["temp_entities"], "rain_entities": st["rain_entities"],
                         "humidity_entities": st["humidity_entities"], "solar_entities": st["solar_entities"],
                         "air_entities": st["air_entities"]},
        }

    def _frost_view(self, g: dict, today: date) -> dict:
        st = self.data["settings"]
        last = g["frost"].get("last") or st["frost_last"]
        first = g["frost"].get("first") or st["frost_first"]
        return {"last": last, "first": first, "custom": bool(g["frost"]), "recorded": self._recorded_frost(g, today),
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

    def _metric_for(self, g: dict, metric: str) -> dict:
        spec = self._metric(metric)
        if metric not in METRIC_SETS[g.get("kind", "garden")]:
            raise GardenError(f"{g['name']} doesn't track {spec['name'].lower()}")
        return spec

    def set_sensors(self, garden: str, metric: str, entities: list[str]) -> None:
        g = self.find_garden(garden)
        self._metric_for(g, metric)
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

    # ---- layout planner -------------------------------------------------------------------------------
    def _plant_names(self) -> dict[str, str]:
        return {k: sp["name"] for k, sp in {**self.presets, **self.data["species"]}.items() if sp.get("kind") != "tree"}

    def _layout_garden(self, ref: str) -> dict:
        g = self.find_garden(ref)
        self._ensure_garden(g)
        if g["kind"] != "garden":
            raise GardenError("Layouts are for gardens, not racks or greenhouses")
        return g

    def _layout_of(self, ref: str) -> tuple[dict, dict]:
        g = self._layout_garden(ref)
        if not g["layout"]:
            raise GardenError("Set the garden size first")
        return g, g["layout"]

    def _layout_year(self, g: dict) -> int:
        old = [int(y) for y in g["layout_history"]]
        return max([self.today().year] + [y + 1 for y in old])

    def _row_check(self, L: dict, row: int) -> int:
        row = int(row)
        if not 0 <= row < lay.row_count(L):
            raise GardenError(f"There is no row {row + 1}")
        return row

    def set_layout(self, garden: str, width_ft: Any = None, length_ft: Any = None, row_in: Any = None, rotation: Any = None,
                   path_in: Any = None) -> None:
        g = self._layout_garden(garden)
        new = copy.deepcopy(g["layout"]) if g["layout"] else lay.blank(self._layout_year(g))
        try:
            lay.validate_size(new, width_ft, length_ft, row_in, rotation, path_in)
        except lay.LayoutError as e:
            raise GardenError(str(e)) from None
        g["layout"] = new
        self._touch()

    def assign_layout_rows(self, garden: str, crop: str | None, rows: list[int] | None = None, variety: str | None = None) -> None:
        g, L = self._layout_of(garden)
        names = self._plant_names()
        if crop and crop not in names:
            raise GardenError(f"Unknown crop '{crop}'")
        n = lay.row_count(L)
        cur = (list(L.get("rows") or []) + [None] * n)[:n]
        variety = (variety or "").strip()
        for i in (range(n) if rows is None else rows):
            cur[self._row_check(L, i)] = ([{"crop": crop, "ft": L["length_ft"], "start_ft": 0, "variety": variety}] if crop and variety
                                          else crop or None)
        L["rows"] = cur
        self._touch()

    def _put_section(self, L: dict, row: int, crop: str, ft: float, start_ft: float | None, variety: str = "") -> None:
        segs = lay.row_segments(L, row)
        start = max([s["start_ft"] + s["ft"] for s in segs] + [0.0]) if start_ft is None else start_ft
        end = start + ft
        if start < 0 or end > L["length_ft"] + 1e-6:
            left = L["length_ft"] - start
            raise GardenError(f"Row {row + 1} has only {max(left, 0):g} ft from there. Clear some of it first" if left > 0.4
                              else f"Row {row + 1} is full from there. Clear some of it first")
        for sg in segs:
            if start < sg["start_ft"] + sg["ft"] - 1e-6 and end > sg["start_ft"] + 1e-6:
                raise GardenError(f"Row {row + 1} already has {self._plant_names().get(sg['crop'], sg['crop'])} there. Clear it first")
        n = lay.row_count(L)
        cur = (list(L.get("rows") or []) + [None] * n)[:n]
        cur[row] = sorted(segs + [{"crop": crop, "ft": ft, "start_ft": round(start, 3), "variety": variety}],
                           key=lambda x: x["start_ft"])
        L["rows"] = cur

    def add_layout_segment(self, garden: str, row: int, crop: str, length_ft: Any, start_ft: Any = None, variety: str | None = None) -> None:
        """Plant `length_ft` of a row with `crop`, from `start_ft` or after whatever is already planted in that row."""
        g, L = self._layout_of(garden)
        if crop not in self._plant_names():
            raise GardenError(f"Unknown crop '{crop}'")
        row = self._row_check(L, row)
        try:
            ft = lay._num(length_ft, "Length", 0.5, lay.MAX_FT)
            start = None if start_ft is None else lay._num(start_ft, "Start", 0, lay.MAX_FT)
        except lay.LayoutError as e:
            raise GardenError(str(e)) from None
        self._put_section(L, row, crop, ft, start, (variety or "").strip())
        self._touch()

    def remove_layout_segment(self, garden: str, row: int, index: int | None = None) -> None:
        """Take one planted section out of a row (the last one when no index is given)."""
        g, L = self._layout_of(garden)
        row = self._row_check(L, row)
        segs = lay.row_segments(L, row)
        if not segs:
            return
        del segs[len(segs) - 1 if index is None else int(index)]
        n = lay.row_count(L)
        cur = (list(L.get("rows") or []) + [None] * n)[:n]
        cur[row] = segs or None
        L["rows"] = cur
        self._touch()

    def set_layout_crop(self, garden: str, crop: str, spacing_in: Any = None, support: Any = None, post_ft: Any = None,
                        post_kind: Any = None, twine_levels: Any = None, pattern: Any = None, stagger: Any = None,
                        yield_lb: Any = None, height_ft: Any = None) -> None:
        g, L = self._layout_of(garden)
        if crop not in self._plant_names():
            raise GardenError(f"Unknown crop '{crop}'")
        try:
            vals = lay.validate_crop(spacing_in, support, post_ft, post_kind, twine_levels, pattern, stagger, yield_lb, height_ft)
        except lay.LayoutError as e:
            raise GardenError(str(e)) from None
        L.setdefault("crops", {}).setdefault(crop, {}).update(vals)
        self._touch()

    # ---- watering: drip or sprinklers, run time, fertigation ----------------------------------------------
    def _irrigation_of(self, garden: str) -> tuple[dict, dict]:
        g = self._layout_garden(garden)
        if not g.get("irrigation"):
            g["irrigation"] = irr.blank()
        return g, g["irrigation"]

    def set_irrigation(self, garden: str, method: Any = None, soil: Any = None, per_week: Any = None, run_min: Any = "keep",
                       max_line_gph: Any = None, weather: Any = None) -> None:
        g, I = self._irrigation_of(garden)
        try:
            I.update(irr.validate_settings(method, soil, per_week, run_min, max_line_gph, weather))
        except irr.IrrigationError as e:
            raise GardenError(str(e)) from None
        self._touch()

    def set_sprinkler(self, garden: str, mode: Any = None, pr_mode: Any = None, gpm: Any = None, radius_ft: Any = None, arc: Any = None,
                      pr_in_hr: Any = "keep", heads: Any = "keep", per_week: Any = "keep") -> None:
        g, I = self._irrigation_of(garden)
        try:
            vals = irr.validate_sprinkler(mode, pr_mode, gpm, radius_ft, arc, pr_in_hr, heads, per_week)
        except irr.IrrigationError as e:
            raise GardenError(str(e)) from None
        I["sprinkler"] = {**irr.default_sprinkler(), **(I.get("sprinkler") or {}), **vals}
        self._touch()

    def set_irrigation_crop(self, garden: str, crop: str, water_in_week: Any = None, lines: Any = None, flow_gph: Any = "keep",
                            emit_in: Any = "keep", ppm_n: Any = None) -> None:
        g, I = self._irrigation_of(garden)
        if crop not in self._plant_names():
            raise GardenError(f"Unknown crop '{crop}'")
        try:
            vals = irr.validate_crop(water_in_week, lines, flow_gph, emit_in, ppm_n)
        except irr.IrrigationError as e:
            raise GardenError(str(e)) from None
        I.setdefault("crops", {}).setdefault(crop, {}).update(vals)
        self._touch()

    def reset_irrigation_crop(self, garden: str, crop: str) -> None:
        g, I = self._irrigation_of(garden)
        I.setdefault("crops", {}).pop(crop, None)
        self._touch()

    def _fert_of(self, garden: str) -> dict:
        g, I = self._irrigation_of(garden)
        I["fert"] = irr.fert_of(I.get("fert"))
        return I["fert"]

    def set_acid(self, garden: str, ph: Any = None, ta_ppm: Any = None, target_ph: Any = None, strength_pct: Any = None,
                 sg: Any = "keep", base: Any = None) -> None:
        g, I = self._irrigation_of(garden)
        try:
            vals = irr.validate_acid(ph, ta_ppm, target_ph, strength_pct, sg, base)
        except irr.IrrigationError as e:
            raise GardenError(str(e)) from None
        a = {**irr.default_acid(), **(I.get("acid") or {}), **vals}
        if ph is not None or ta_ppm is not None:
            a["tested"] = self.today().isoformat()
        I["acid"] = a
        self._touch()

    def set_fertigation(self, garden: str, every_days: Any = None, active: Any = None) -> None:
        F = self._fert_of(garden)
        try:
            vals = irr.validate_fert(every_days, active)
        except irr.IrrigationError as e:
            raise GardenError(str(e)) from None
        if "active" in vals and vals["active"] not in F["mixes"]:
            raise GardenError("Pick one of the mixes")
        F.update(vals)
        self._touch()

    def set_lime(self, garden: str, target_ph: Any = None, lime_type: Any = None, depth_in: Any = None, tilled: Any = None,
                 ph: Any = "keep", lb_per_unit: Any = "keep") -> None:
        g, I = self._irrigation_of(garden)
        try:
            vals = irr.validate_lime(target_ph, lime_type, depth_in, tilled, ph, lb_per_unit)
        except irr.IrrigationError as e:
            raise GardenError(str(e)) from None
        I["lime"] = {**irr.default_lime(), **(I.get("lime") or {}), **vals}
        self._touch()

    def set_pump(self, garden: str, pump: str | None = None, name: Any = None, min_ratio: Any = None, max_ratio: Any = None,
                 min_gpm: Any = None, max_gpm: Any = None, tank_gal: Any = None, flush_min: Any = None) -> str:
        """Change a pump, or add one when `pump` is empty. Returns its key."""
        F = self._fert_of(garden)
        try:
            vals = irr.validate_injector(name, min_ratio, max_ratio, min_gpm, max_gpm, tank_gal, flush_min)
            if pump:
                if pump not in F["pumps"]:
                    raise irr.IrrigationError("Unknown pump")
                new = {**F["pumps"][pump], **vals}
            else:
                if not vals.get("name"):
                    raise irr.IrrigationError("A pump needs a name")
                new = {**irr.DEFAULT_PUMP, **vals}
            if new["min_ratio"] > new["max_ratio"]:
                raise irr.IrrigationError("The strongest dilution (1:50) must be a smaller number than the weakest (1:500)")
            if new["min_gpm"] > new["max_gpm"]:
                raise irr.IrrigationError("The lowest flow must be less than the highest")
        except irr.IrrigationError as e:
            raise GardenError(str(e)) from None
        if not pump:
            base = slug(new["name"])
            pump, n = base, 2
            while pump in F["pumps"]:
                pump, n = f"{base}_{n}", n + 1
        F["pumps"][pump] = new
        self._touch()
        return pump

    def remove_pump(self, garden: str, pump: str) -> None:
        F = self._fert_of(garden)
        if pump not in F["pumps"]:
            raise GardenError("Unknown pump")
        if len(F["pumps"]) == 1:
            raise GardenError("Keep at least one pump")
        del F["pumps"][pump]
        F["tank_pump"] = {t: k for t, k in F["tank_pump"].items() if k != pump}  # those tanks go back to the first pump
        self._touch()

    def set_tank_pump(self, garden: str, tank: str, pump: str) -> None:
        """Which pump a stock tank (a letter, or acid) runs through."""
        F = self._fert_of(garden)
        t = str(tank).strip()
        t = "acid" if t.lower() == "acid" else t.upper()[:1]
        if not t.isalpha():
            raise GardenError("A tank is a letter, or acid")
        if pump not in F["pumps"]:
            raise GardenError("Unknown pump")
        F["tank_pump"][t] = pump
        self._touch()

    def log_acid(self, garden: str, when: Any = None, ml: Any = None, water_gal: Any = None, ph_before: Any = None,
                 ph_after: Any = None, notes: str | None = None, g: Any = None, product: str | None = None) -> None:
        """Log an acid application (mL) or, when the water was raised, a base (grams)."""
        gd = self._layout_garden(garden)
        if ml in (None, "") and g in (None, ""):
            raise GardenError("Enter the amount of acid in mL, or of base in grams")
        try:
            vals = {"ml": irr._num(ml, "Acid (mL)", 0, 100000) if ml not in (None, "") else None,
                    "g": irr._num(g, "Base (g)", 0, 1000000) if g not in (None, "") else None,
                    "water_gal": irr._num(water_gal, "Water (gallons)", 0, 1000000) if water_gal not in (None, "") else None,
                    "ph_before": irr._num(ph_before, "pH before", 0, 14) if ph_before not in (None, "") else None,
                    "ph_after": irr._num(ph_after, "pH after", 0, 14) if ph_after not in (None, "") else None}
        except irr.IrrigationError as e:
            raise GardenError(str(e)) from None
        gd.setdefault("acid_log", []).append({"id": new_id(), "date": iso(when) or self.today().isoformat(), "notes": notes or "",
                                              "product": (product or "").strip()[:60], **vals})
        self._touch()

    def set_fert_mix(self, garden: str, mix: str | None = None, name: Any = None, ppm_n: Any = "keep") -> str:
        """Change a mix, or start a new one when `mix` is empty. Returns its key."""
        F = self._fert_of(garden)
        try:
            vals = irr.validate_mix(name, ppm_n)
        except irr.IrrigationError as e:
            raise GardenError(str(e)) from None
        if mix:
            if mix not in F["mixes"]:
                raise GardenError("Unknown mix")
            F["mixes"][mix].update(vals)
        else:
            if not vals.get("name"):
                raise GardenError("A mix needs a name")
            base = re.sub(r"[^a-z0-9]+", "_", vals["name"].lower()).strip("_") or "mix"
            mix, n = base, 2
            while mix in F["mixes"]:
                mix, n = f"{base}_{n}", n + 1
            F["mixes"][mix] = {"name": vals["name"], "ppm_n": vals.get("ppm_n"), "components": []}
        self._touch()
        return mix

    def remove_fert_mix(self, garden: str, mix: str) -> None:
        F = self._fert_of(garden)
        if mix not in F["mixes"]:
            raise GardenError("Unknown mix")
        if len(F["mixes"]) == 1:
            raise GardenError("Keep at least one mix")
        del F["mixes"][mix]
        if F["active"] == mix:
            F["active"] = next(iter(F["mixes"]))
        self._touch()

    def set_fert_component(self, garden: str, mix: str, index: Any = None, name: Any = None, n: Any = None, p: Any = None,
                           k: Any = None, ca: Any = None, mg: Any = None, parts: Any = None, tank: Any = None) -> None:
        """Change fertilizer number `index` in a mix, or add one when index is empty."""
        F = self._fert_of(garden)
        if mix not in F["mixes"]:
            raise GardenError("Unknown mix")
        comps = F["mixes"][mix]["components"]
        try:
            vals = irr.validate_component(name, n, p, k, ca, mg, parts, tank)
        except irr.IrrigationError as e:
            raise GardenError(str(e)) from None
        if index is None or index == "":
            if not vals.get("name"):
                raise GardenError("A fertilizer needs a name")
            comps.append({"name": "", "n": 0.0, "p": 0.0, "k": 0.0, "ca": 0.0, "mg": 0.0, "parts": 1.0, "tank": "A", **vals})
        else:
            if not 0 <= int(index) < len(comps):
                raise GardenError("No such fertilizer")
            comps[int(index)].update(vals)
        self._touch()

    def remove_fert_component(self, garden: str, mix: str, index: Any) -> None:
        F = self._fert_of(garden)
        if mix not in F["mixes"] or not 0 <= int(index) < len(F["mixes"][mix]["components"]):
            raise GardenError("No such fertilizer")
        del F["mixes"][mix]["components"][int(index)]
        self._touch()

    def set_layout_draft(self, garden: str, crop: str | None = None, mode: str | None = None, value: Any = None,
                         yield_lb: Any = None, spacing_in: Any = None, variety: str | None = None) -> None:
        """What to plant: a crop and a target (harvest weight, number of plants, or feet of row). The planner works out the rest."""
        g, L = self._layout_of(garden)
        d = dict(L.get("draft") or {})
        if crop is not None:
            if crop not in self._plant_names():
                raise GardenError(f"Unknown crop '{crop}'")
            if d.get("crop") != crop:
                d.pop("variety", None)  # a variety belongs to its crop
            d["crop"] = crop
        if not d.get("crop"):
            raise GardenError("Pick a crop first")
        if variety is not None:
            d["variety"] = variety.strip()
        if mode is not None:
            if mode not in ("weight", "plants", "length"):
                raise GardenError("Plan by weight, plants or row length")
            d["mode"] = mode
        if value is not None:
            try:
                d["value"] = lay._num(value, "Amount", 0, 100000)
            except lay.LayoutError as e:
                raise GardenError(str(e)) from None
        if yield_lb is not None or spacing_in is not None:
            try:
                vals = lay.validate_crop(spacing_in=spacing_in, yield_lb=yield_lb)
            except lay.LayoutError as e:
                raise GardenError(str(e)) from None
            L.setdefault("crops", {}).setdefault(d["crop"], {}).update(vals)
        L["draft"] = d
        self._touch()

    def place_layout_draft(self, garden: str, row: int, start_ft: Any = None) -> None:
        """Put the planned crop into the garden from `start_ft` in `row`, carrying on into the next rows if it is longer."""
        g, L = self._layout_of(garden)
        res = lay.draft_result(L, self._plant_names(), self._history(g), int(L.get("year") or self.today().year), self.data["variety_traits"])
        if not res or not res["ready"]:
            raise GardenError("Say how much to plant first")
        try:
            start = 0.0 if start_ft is None else lay._num(start_ft, "Start", 0, lay.MAX_FT)
        except lay.LayoutError as e:
            raise GardenError(str(e)) from None
        row, left, n = self._row_check(L, row), res["length_ft"], lay.row_count(L)
        trial = copy.deepcopy(L)
        while left > 1e-6:
            if row >= n:
                raise GardenError(f"{res['length_ft']:g} ft does not fit from there. Pick an earlier row or a smaller amount")
            ft = min(left, trial["length_ft"] - start)
            self._put_section(trial, row, res["crop"], ft, start, res["variety"])
            left -= ft
            row, start = row + 1, 0.0
        trial["draft"] = L.get("draft")
        g["layout"] = trial
        self._touch()

    def set_variety_traits(self, crop: str, variety: str, resist: Any = UNSET, height_ft: Any = UNSET, habit: Any = UNSET) -> None:
        """Remember what a named variety resists (the letters on the seed packet) and how tall it grows, so rotation alerts
        and the shade check can allow for it. Anything left out keeps its earlier value."""
        if crop not in self._plant_names():
            raise GardenError(f"Unknown crop '{crop}'")
        name = (variety or "").strip()
        if not name:
            raise GardenError("Give the variety a name")
        cur = self.data["variety_traits"].get(lay.trait_key(crop, name)) or {}
        new = {"crop": crop, "name": name, "resist": cur.get("resist") or []}
        if resist is not UNSET:
            valid = {d["key"] for d in rot.diseases_for(crop)}
            bad = [r for r in resist or [] if r not in valid]
            if bad:
                raise GardenError(f"{bad[0]} is not a disease listed for {self._plant_names()[crop]}")
            new["resist"] = sorted(set(resist or []))
        for k in ("height_ft", "habit"):
            if cur.get(k) is not None:
                new[k] = cur[k]
        if habit is not UNSET:
            known = {h["key"]: h for h in sun_mod.habits_for(crop)}
            if habit in (None, ""):
                new.pop("habit", None)
            elif habit not in known:
                raise GardenError(f"{habit} is not a growth habit for {self._plant_names()[crop]}")
            else:
                new["habit"] = habit
                if height_ft is UNSET:  # picking a habit gives its usual height unless a height comes with it
                    new["height_ft"] = known[habit]["height"]
        if height_ft is not UNSET:
            if height_ft in (None, ""):
                new.pop("height_ft", None)
            else:
                try:
                    h = float(height_ft)
                except (TypeError, ValueError):
                    raise GardenError("Height must be a number") from None
                if not 0.1 <= h <= 30:
                    raise GardenError("Height must be between 0.1 and 30 feet")
                new["height_ft"] = h
        self.data["variety_traits"][lay.trait_key(crop, name)] = new
        self._touch()

    def set_crop_days(self, crop: str, days: Any, hardy: Any = None) -> None:
        """Days from planting to harvest for a crop, and how it takes frost, as the seed packet says. Used by the frost planner."""
        if crop not in self._plant_names():
            raise GardenError(f"Unknown crop '{crop}'")
        try:
            n = int(float(days))
        except (TypeError, ValueError):
            raise GardenError("Days to harvest must be a number") from None
        if not 5 <= n <= 400:
            raise GardenError("Days to harvest must be between 5 and 400")
        cur = self.data["crop_days"].get(crop) or {}
        usual = season_mod.CROPS.get(crop)
        h = hardy or cur.get("hardy") or (usual[1] if usual else "tender")
        if h not in season_mod.HARDY_NAMES:
            raise GardenError("Frost hardiness must be tender, half, hardy or fall")
        self.data["crop_days"][crop] = {"days": n, "hardy": h}
        self._touch()

    def reset_crop_days(self, crop: str) -> None:
        self.data["crop_days"].pop(crop, None)
        self._touch()

    def remove_variety_traits(self, crop: str, variety: str) -> None:
        self.data["variety_traits"].pop(lay.trait_key(crop, variety), None)
        self._touch()

    def _history(self, g: dict) -> dict[int, dict]:
        return {int(y): h for y, h in g["layout_history"].items()}

    def start_layout_season(self, garden: str, year: Any = None) -> None:
        """Keep this season's layout and begin the next one with the same garden, empty rows and the same crop settings."""
        g, L = self._layout_of(garden)
        this = int(L.get("year") or self.today().year)
        new = this + 1 if year is None else int(year)
        if new <= this or str(new) in g["layout_history"]:
            raise GardenError(f"{new} is not after the current season ({this})")
        old = copy.deepcopy(L)
        old["year"], old["draft"] = this, None
        g["layout_history"][str(this)] = old
        fresh = copy.deepcopy(L)
        fresh.update(year=new, rows=[], draft=None)
        g["layout"] = fresh
        self._touch()

    def remove_layout(self, garden: str) -> None:
        g = self._layout_garden(garden)
        g["layout"] = None
        self._touch()

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
                    heat_max_run: int | None = None, heat_rest: int | None = None,
                    lights: list[str] | None = None, light_sched: bool | None = None, light_on: str | None = None,
                    light_hours: float | None = None, fan_sched: bool | None = None, fan_minutes: int | None = None,
                    fan_every: float | None = None, fan_lights_only: bool | None = None,
                    cool_off: Any = UNSET, fan_min_run: int | None = None, heat_off: Any = UNSET) -> None:
        g = self._location(garden)
        if g["kind"] not in CLIMATE_KINDS:
            raise GardenError("Heating, fan and light control is for a seedling rack or greenhouse")
        c = g["climate"]
        heat = c["heat_set"] if heat_set is None else float(heat_set)
        cool = c["cool_set"] if cool_set is None else float(cool_set)
        if not 30 <= heat <= 110 or not 30 <= cool <= 130:
            raise GardenError("Set points must be between 30 and 130 °F")
        if cool - heat < CLIMATE_MIN_GAP:
            raise GardenError(f"The cool set point must be at least {CLIMATE_MIN_GAP:g} degrees above the heat set point")
        off = c.get("cool_off") if cool_off is UNSET else (None if cool_off in (None, "") else float(cool_off))
        if off is not None and not heat < off < cool:
            raise GardenError("The fans-off temperature must be between the heat set point and the fans-on temperature")
        hoff = c.get("heat_off") if heat_off is UNSET else (None if heat_off in (None, "") else float(heat_off))
        if hoff is not None and not heat < hoff < cool:
            raise GardenError("The heat-off temperature must be between the heat set point and the fans-on temperature")
        if fan_min_run is not None and not 0 <= int(fan_min_run) <= 720:
            raise GardenError("Fan minimum run must be between 0 and 720 minutes")

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
        if lights is not None:
            if clean(lights) and g["kind"] != "rack":
                raise GardenError("Grow lights are for the seedling rack")
            c["lights"] = clean(lights)
        mine = [c["heaters"], c["coolers"], c["lights"]]
        if any(set(a) & set(b) for i, a in enumerate(mine) for b in mine[i + 1:]):
            raise GardenError("A device can only be one of heater, fan or light")
        if light_sched and g["kind"] != "rack":
            raise GardenError("Grow lights are for the seedling rack")
        if light_on is not None:
            if not TIME_RE.match(str(light_on)):
                raise GardenError("Lights on time must look like 06:00")
            c["light_on"] = str(light_on)
        if light_hours is not None:
            if not 1 <= float(light_hours) <= 24:
                raise GardenError("Lights on for between 1 and 24 hours a day")
            c["light_hours"] = float(light_hours)
        if fan_every is not None:
            if not 0.5 <= float(fan_every) <= 168:
                raise GardenError("Fan cycle must be between 0.5 and 168 hours")
            c["fan_every"] = float(fan_every)
        if fan_minutes is not None:
            if not 1 <= int(fan_minutes) <= 1440:
                raise GardenError("Fan run must be between 1 and 1440 minutes")
            c["fan_minutes"] = int(fan_minutes)
        if c["fan_minutes"] > c["fan_every"] * 60:
            raise GardenError("The fan run can't be longer than the time between runs")
        if light_sched is not None:
            c["light_sched"] = bool(light_sched)
        if fan_sched is not None:
            c["fan_sched"] = bool(fan_sched)
        if fan_lights_only is not None:
            c["fan_lights_only"] = bool(fan_lights_only)
        mn = c.get("heat_min_run", 0) if heat_min_run is None else int(heat_min_run)
        mx = c.get("heat_max_run", 0) if heat_max_run is None else int(heat_max_run)
        rest = c.get("heat_rest", 10) if heat_rest is None else int(heat_rest)
        if not (0 <= mn <= 720 and 0 <= mx <= 720 and 0 <= rest <= 720):
            raise GardenError("Run times must be between 0 and 720 minutes")
        if mn and mx and mn > mx:
            raise GardenError("The minimum heater run time can't be longer than the maximum")
        c["heat_min_run"], c["heat_max_run"], c["heat_rest"] = mn, mx, rest
        c["heat_set"], c["cool_set"], c["cool_off"], c["heat_off"] = heat, cool, off, hoff
        if fan_min_run is not None:
            c["fan_min_run"] = int(fan_min_run)
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

    @staticmethod
    def sensors_in_use(g: dict) -> dict[str, str]:
        """Every sensor a place is relying on, as entity id to what it measures. Probes marked out are left off."""
        out: dict[str, str] = {}
        paused = g.get("sensors_paused", {})
        for metric, ents in g.get("sensors", {}).items():
            if not paused.get(metric):
                for e in ents:
                    out.setdefault(e, metric)
        if g.get("ph_entity"):
            out.setdefault(g["ph_entity"], "ph")
        for ents in g.get("power_sensors", {}).values():
            for e in ents:
                out.setdefault(e, "power")
        return out

    def set_sensor_alarm(self, garden: str, enabled: bool) -> None:
        """Warn when a sensor in use reports nothing for an hour. Turning it off clears any warning."""
        g = self.find_garden(garden)
        g["sensor_alarm"]["enabled"] = bool(enabled)
        if not enabled:
            g["sensor_alarm"]["down"] = {}
        self._touch(True)
        self._alarm_changed()

    def ack_sensor_alarm(self, garden: str, entity: str | None = None) -> None:
        g = self.find_garden(garden)
        down = g["sensor_alarm"]["down"]
        for ent in ([entity] if entity else list(down)):
            e = down.get(ent)
            if not e or not e.get("raised"):
                continue
            if e.get("end"):
                del down[ent]
            else:
                e["acked"] = True
        self._touch(True)

    def update_sensor_alarm(self, garden_id: str, status: dict[str, tuple[str, bool]], now: Any) -> bool:
        """Feed in whether each sensor in use has a value. Returns True when a warning started, changed or ended."""
        g = self.data["gardens"].get(garden_id)
        if not g or not g["sensor_alarm"]["enabled"]:
            return False
        down, changed, stamp = g["sensor_alarm"]["down"], False, now.isoformat()
        for ent in list(down):
            if ent not in status:  # no longer in use, so nothing to watch
                changed = changed or bool(down[ent].get("raised"))
                del down[ent]
        for ent, (metric, ok) in status.items():
            e = down.get(ent)
            if ok:
                if not e:
                    continue
                if not e.get("raised") or e.get("acked"):
                    changed = changed or bool(e.get("raised"))
                    del down[ent]  # a short gap, or a warning you already acknowledged
                elif not e.get("end"):
                    e["end"], changed = stamp, True
            elif e is None or e.get("end"):
                new = {"since": stamp, "metric": metric, "raised": False, "end": None, "acked": False}
                if e:  # it dropped out again before the last warning was acknowledged
                    new.update(raised=True, prior_n=e.get("prior_n", 0) + 1,
                               prior_s=e.get("prior_s", 0) + int((datetime.fromisoformat(e["end"])
                                                                  - datetime.fromisoformat(e["since"])).total_seconds()))
                    changed = True
                down[ent] = new
            elif not e.get("raised") and now - datetime.fromisoformat(e["since"]) >= SENSOR_ALARM_AFTER:
                e["raised"], changed = True, True
        return changed

    def _sensor_alarm_view(self, g: dict) -> dict:
        sa = g["sensor_alarm"]
        alerts = [{"entity": ent, "metric": e["metric"], "since": e["since"], "end": e.get("end"),
                   "ongoing": not e.get("end"), "prior_n": e.get("prior_n", 0), "prior_s": e.get("prior_s", 0)}
                  for ent, e in sa["down"].items() if e.get("raised") and not e.get("acked")]
        alerts.sort(key=lambda x: (not x["ongoing"], x["since"]))
        return {"enabled": sa["enabled"], "in_use": len(self.sensors_in_use(g)), "alerts": alerts,
                "acknowledged": [ent for ent, e in sa["down"].items() if e.get("raised") and e.get("acked")]}

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
                    "air_temp": ("air_temp",), "par": ("par",), "out_temp": ("out_temp",), "all": tuple(METRICS)}

    def set_sensors_paused(self, garden: str, paused: bool, group: str = "all") -> None:
        """Ignore sensor readings while the probes are out of the ground.

        Groups: moisture_ec (the moisture and EC probe), soil_temp, or all."""
        g = self.find_garden(garden)
        self._ensure_garden(g)
        if group not in self.PAUSE_GROUPS:
            raise GardenError("Group must be moisture_ec, soil_temp, air_temp, out_temp, par or all")
        for k in self.PAUSE_GROUPS[group]:
            g["sensors_paused"][k] = bool(paused)
        self._touch(True)

    def log_metric(self, garden: str, metric: str, value: float, when: Any = None) -> None:
        g = self.find_garden(garden)
        spec = self._metric_for(g, metric)
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
        if metric in SAMPLED:
            self._sample(g, metric, value)
        self._touch()

    def _sample(self, g: dict, metric: str, value: float) -> None:
        """Keep one reading per 15 minutes (the latest in the slot) for the last 24 hour and week charts."""
        now = int(self.now_fn())
        rows = g["samples"].setdefault(metric, [])
        if rows and rows[-1][0] // SAMPLE_SLOT_S == now // SAMPLE_SLOT_S:
            rows[-1] = [now, value]
        else:
            rows.append([now, value])
        cut = now - SAMPLE_KEEP_S
        while rows and rows[0][0] < cut:
            rows.pop(0)

    def _samples_view(self, g: dict, metric: str) -> list[list[float]]:
        """The last 24 hours of readings, 15 minutes apart, as [seconds since the epoch, value]."""
        cut = int(self.now_fn()) - 86400
        return [r for r in g["samples"].get(metric, []) if r[0] >= cut]

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
        return {"today": today.isoformat(), "micro": self._micro_view(today), "species": species, "gardens": gardens,
                "varieties": varieties, "variety_traits": list(self.data["variety_traits"].values()), "can_undo": self._trash is not None,
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
        for k in metrics:
            if k in SAMPLED:
                metrics[k]["day"] = self._samples_view(g, k)
        if "out_temp" in metrics:  # with no sensor of its own it follows the main outdoor sensor
            metrics["out_temp"]["fallback"] = bool(not metrics["out_temp"]["entities"] and self.outdoor_entity)
        soil = kind == "garden"
        return {
            "id": g["id"], "name": g["name"], "kind": kind, "kind_name": LOCATION_KINDS[kind], "metrics": metrics,
            "planting": self._planting_view(metrics["soil_temp"], g, today) if soil else None,
            "cover": self._cover_view(g, today),
            "frost": self._frost_view(g, today),
            "paused": {k: bool(g.get("sensors_paused", {}).get(k)) for k in METRICS},
            "fertility": self._fertility_view(g, metrics, today) if soil else None,
            "layout": lay.plan(g.get("layout"), self._plant_names(), self._history(g), today.year, self.data["variety_traits"], self._lat(), *self._soil_ph(g)) if soil else None,
            "irrigation": self._irrigation_view(g, today) if soil else None,
            "season": self._season_view(g, today) if soil and kind == "garden" else None,
            "layout_history": ({y: lay.plan(h, self._plant_names(), None, int(y)) for y, h in g["layout_history"].items()} if soil else {}),
            "trays": g.get("trays", 0), "water": self._water_view(g, today),
            "trays_calc": self._trays_calc(g) if kind != "garden" else None,
            "power": self._power_view(g, today) if kind != "garden" else None,
            "power_groups": POWER_GROUPS.get(kind, {}), "power_sensors": {k: list(v) for k, v in g.get("power_sensors", {}).items()},
            "climate": self._climate_view(g, metrics) if kind in CLIMATE_KINDS else None,
            "alarm": self._alarm_view(g) if kind != "garden" else None,
            "sensor_alarm": self._sensor_alarm_view(g),
            "ph": {"entity": g.get("ph_entity"), "current": cur and cur["value"], "date": cur and cur["date"],
                   "source": cur and cur["source"], "target": [lo, hi], "level": level,
                   "first": first and {"date": first["date"], "value": first["value"]}, "history": hist},
            "adjuncts": [calc.adjunct_status(t, g["adjuncts"], today) for t in g["adjunct_types"].values()],
            "adjunct_log": [{**e, "type_name": names.get(e["type"], e["type"])} for e in log],
        }

    def _season_view(self, g: dict, today: date) -> dict:
        st = self.data["settings"]
        last = (g.get("frost") or {}).get("last") or st["frost_last"]
        first = (g.get("frost") or {}).get("first") or st["frost_first"]
        planted = {c["key"] for c in (lay.plan(g.get("layout"), self._plant_names(), None, today.year).get("crops") or [])} if g.get("layout") else set()
        return season_mod.analyse(self._plant_names(), last, first, today, planted, self.data.get("crop_days"))

    def _soil_ph(self, g: dict) -> tuple:
        """The pH to judge acid-loving crops by: the latest reading (sensor or logged), else the soil test typed into the lime tool."""
        hist = sorted(g["ph_readings"], key=lambda r: (r["date"], r["id"]))
        if hist:
            return hist[-1]["value"], ("tested" if hist[-1].get("source") != "sensor" else "sensor")
        est = ((g.get("irrigation") or {}).get("lime") or {}).get("ph")
        return (est, "estimated") if est else (None, "")

    def _lat(self) -> float | None:
        """Where the garden is, north to south: the place you set, otherwise Home Assistant's own latitude."""
        loc = self.data["settings"].get("location")
        return loc["lat"] if loc else self.home_lat

    def _irrigation_view(self, g: dict, today: date) -> dict:
        hist = sorted(g["ph_readings"], key=lambda r: (r["date"], r["id"]))
        cur = hist[-1]["value"] if hist else None
        wx = irr.weather_need(self.data["daily"], self.data["rain"], today, self._lat())
        w = irr.plan(lay.plan(g.get("layout"), self._plant_names(), None, today.year), g.get("irrigation"), None, cur, wx)
        log = sorted(g.get("acid_log", []), key=lambda e: (e["date"], e["id"]), reverse=True)
        year = [e for e in log if e["date"][:4] == str(today.year)]
        w["acid_log"] = {"entries": log[:60], "last": log[0]["date"] if log else None, "days_since": calc.days_since(log[0]["date"], today) if log else None,
                         "count_year": len(year), "ml_year": round(sum(e.get("ml") or 0 for e in year)), "g_year": round(sum(e.get("g") or 0 for e in year)), "year": today.year}
        return w

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
                "gap": CLIMATE_MIN_GAP, "heat_off_at": c.get("heat_off") if c.get("heat_off") is not None else c["heat_set"] + 1.0,
                "cool_off_at": c.get("cool_off") if c.get("cool_off") is not None else c["cool_set"] - 1.0, "fan_on": bool(st.get("fan")), "lights_on": bool(st.get("light"))}

    def _feeding_off(self, g: dict, today: date) -> bool:
        """True from the garden's first fall frost until after its last spring frost, when feeding advice is off."""
        fr = self._frost_view(g, today)
        return today >= date.fromisoformat(fr["first_date"]) or today <= date.fromisoformat(fr["last_date"])

    def _fertility_view(self, g: dict, metrics: dict, today: date) -> dict:
        """Judge soil EC (fertility) together with moisture, for the top few inches the probe can see."""
        elo, ehi = g.get("ec_target", DEFAULT_EC_TARGET)
        mlo, mhi = g.get("moisture_band", DEFAULT_MOISTURE_BAND)
        ec, mo = metrics["ec"], metrics["moisture"]
        out = {"ec_target": [elo, ehi], "moisture_band": [mlo, mhi], "depth": g.get("probe_depth", DEFAULT_PROBE_DEPTH),
               "ec": ec["current"], "moisture": mo["current"], "level": None, "moisture_state": None,
               "advice": None, "action": None, "ec_change": None, "last_fed": None, "off_season": False}
        fed = [f["date"] for v in self.data["varieties"].values() if v["garden"] == g["id"]
               and not v.get("archived") for f in v.get("fertilizations", [])]
        out["last_fed"] = max(fed) if fed else None
        out["probes_out"] = bool(g.get("sensors_paused", {}).get("ec") or g.get("sensors_paused", {}).get("moisture"))
        out["paused"] = out["probes_out"] or any(not c.get("terminated") for c in g.get("cover_crops", []))
        # No feeding advice from the first fall frost until after the last spring frost.
        fr = self._frost_view(g, today)
        out["off_season"] = self._feeding_off(g, today)
        out["season"] = {"from": fr["first"], "until": fr["last"]}
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
        if out["paused"] or out["off_season"]:
            return out  # a cover crop is growing or it is the off season, so there is no feeding or watering advice
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

    def _planting_view(self, temp: dict, g: dict, today: date) -> dict | None:
        """Is the soil warm enough? Uses the average of the last 3 daily lows (or readings). A crop is left
        out once there are fewer days before this year's first frost than it needs to grow, which hides the
        whole guide through the fall and winter, until it counts toward the next frost on January 1."""
        hist = temp["history"][-3:]
        if not hist:
            return None
        basis = round(sum(r.get("min", r["value"]) for r in hist) / len(hist), 1)
        left = (calc.md_date(self._first_frost(g), today.year) - today).days
        crops = [{"name": n, "min_f": t, "ready": basis >= t} for n, t, need in PLANTING_TEMPS if left >= need]
        if not crops:
            return None
        return {"basis": basis, "days": len(hist), "frost_in": left, "crops": crops}

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
        feeding, g = None, self.data["gardens"].get(v["garden"])
        feeding_off = bool(g and g.get("kind", "garden") == "garden" and self._feeding_off(g, today))
        plan = sp.get("feeding_plan")
        if plan and kind != "tree" and not feeding_off:
            ref_day = date.fromisoformat(v["in_ground"]) if v.get("in_ground") else planted_d
            age = (today - ref_day).days
            cur = max((i for i, ph in enumerate(plan) if ph["from_day"] <= age), default=0)
            feeding = {"phases": plan, "current": cur}
        seasons = calc.seasons_for(v, self.data["varieties"], daily, today)
        proj = None if v.get("archived") else calc.project(v, seasons, daily, today, len(alive) or len(allp))
        status = self._status(kind, dh, spray, pests, proj)
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
            "last_fert": last_f, "feeding": feeding, "feeding_off": feeding_off,
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
