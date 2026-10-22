"""Sensors: one device per garden and per active plant variety."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass, SensorEntity, SensorEntityDescription, SensorStateClass)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfMass, UnitOfTemperature, UnitOfTime
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_STRUCTURE, SIGNAL_UPDATE
from .manager import GardenManager


@dataclass(frozen=True, kw_only=True)
class Desc(SensorEntityDescription):
    value_fn: Callable[[dict], Any]
    attr_fn: Callable[[dict], dict] | None = None


def _days(**kw) -> dict:
    return dict(device_class=SensorDeviceClass.DURATION, native_unit_of_measurement=UnitOfTime.DAYS, **kw)


COMMON = [
    Desc(key="total_lbs", name="Harvest total", device_class=SensorDeviceClass.WEIGHT,
         native_unit_of_measurement=UnitOfMass.POUNDS, state_class=SensorStateClass.TOTAL,
         value_fn=lambda v: v["total_lbs"],
         attr_fn=lambda v: {"per_plant": {p["label"]: p["total"] for p in v["plants"]} if not v["grouped"]
                            else {"average": v["per_plant_avg"]}, "alive": v["alive"]}),
    Desc(key="plants_alive", name="Plants alive", icon="mdi:sprout", value_fn=lambda v: v["alive"],
         attr_fn=lambda v: {"plants": v["plants"], "total": v["count"], "lost": v["lost"]}),
    Desc(key="to_harvest", name="Days to expected harvest", **_days(),
         value_fn=lambda v: v["days_to_expected"],
         attr_fn=lambda v: {"expected_harvest": v["expected_harvest"], "projection": v["projection"],
                            "countdown": v["countdown"]}),
]
ANNUAL = [
    Desc(key="since_planted", name="Days since planted", **_days(), value_fn=lambda v: v["days"]["planted"]),
    Desc(key="since_in_ground", name="Days since in ground", **_days(), value_fn=lambda v: v["days"]["in_ground"]),
    Desc(key="since_fertilized", name="Days since fertilized", **_days(),
         value_fn=lambda v: v["days"]["fertilized"],
         attr_fn=lambda v: {"last": v["last_fert"], "feeding": v["feeding"]}),
]
TREE = [
    Desc(key="age", name="Age", icon="mdi:tree", native_unit_of_measurement="yr",
         value_fn=lambda v: v["age_years"]),
    Desc(key="since_spray", name="Days since last spray", **_days(), value_fn=lambda v: v["spray"]["days_since"],
         attr_fn=lambda v: {"history": v["sprays"][:10]}),
    Desc(key="to_next_spray", name="Days until next spray", **_days(), value_fn=lambda v: v["spray"]["next_in"],
         attr_fn=lambda v: {"next_spray": v["spray"]["next_date"]}),
    Desc(key="to_safe_harvest", name="Days until safe to harvest", **_days(), value_fn=lambda v: v["spray"]["safe_in"],
         attr_fn=lambda v: {"safe_harvest_date": v["spray"]["safe_date"]}),
    Desc(key="to_spray_cutoff", name="Days until spray cutoff", **_days(), value_fn=lambda v: v["spray"]["cutoff_in"],
         attr_fn=lambda v: {"cutoff_date": v["spray"]["cutoff_date"]}),
]


class _Base(SensorEntity):
    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, mgr: GardenManager, known: set, uid: str, ident: str, name: str, model: str) -> None:
        self._mgr, self._known, self._ident = mgr, known, ident
        self._attr_unique_id = uid
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, ident)}, name=name, model=model,
                                            manufacturer="Garden Tracker")
        known.add(uid)

    async def async_added_to_hass(self) -> None:
        @callback
        def _upd() -> None:
            self.async_write_ha_state()
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_UPDATE, _upd))

    async def async_will_remove_from_hass(self) -> None:
        self._known.discard(self._attr_unique_id)


class VarietySensor(_Base):
    def __init__(self, mgr, known, vid: str, v: dict, desc: Desc) -> None:
        super().__init__(mgr, known, f"{vid}_{desc.key}", f"variety:{vid}", v["name"], v["species_name"])
        self.entity_description, self._vid = desc, vid

    def _view(self) -> dict | None:
        return self._mgr.index()["v"].get(self._vid)

    @property
    def available(self) -> bool:
        return self._view() is not None

    @property
    def native_value(self):
        v = self._view()
        return self.entity_description.value_fn(v) if v else None

    @property
    def extra_state_attributes(self):
        v, fn = self._view(), self.entity_description.attr_fn
        return fn(v) if v and fn else None


class PestSensor(VarietySensor):
    _attr_native_unit_of_measurement = "DD"
    _attr_icon = "mdi:bug"

    def __init__(self, mgr, known, vid: str, v: dict, pest: dict) -> None:
        d = Desc(key=f"dd_{pest['key']}", name=f"{pest['name']} degree days", value_fn=lambda _v: None)
        super().__init__(mgr, known, vid, v, d)
        self._pest = pest["key"]

    def _p(self):
        v = self._view()
        return next((p for p in v["pests"] if p["key"] == self._pest), None) if v else None

    @property
    def native_value(self):
        p = self._p()
        return p["status"]["dd"] if p and p["status"] else None

    @property
    def extra_state_attributes(self):
        p = self._p()
        if not p:
            return None
        return p["status"] or {"note": "Biofix not set; call garden_tracker.set_biofix"}


class GardenPhSensor(_Base):
    _attr_device_class = SensorDeviceClass.PH
    _attr_name = "Soil pH"
    _attr_suggested_display_precision = 2

    def __init__(self, mgr, known, gid: str, g: dict) -> None:
        super().__init__(mgr, known, f"{gid}_ph", f"garden:{gid}", g["name"], "Garden")
        self._gid = gid

    def _view(self):
        return self._mgr.index()["g"].get(self._gid)

    @property
    def available(self) -> bool:
        return self._view() is not None

    @property
    def native_value(self):
        g = self._view()
        return g["ph"]["current"] if g else None

    @property
    def extra_state_attributes(self):
        g = self._view()
        return {"target": g["ph"]["target"], "level": g["ph"]["level"], "date": g["ph"]["date"]} if g else None


class GardenMetricSensor(_Base):
    """Soil moisture, EC or temperature for a garden (averaged across its sensors)."""

    _UNITS = {"moisture": PERCENTAGE, "ec": "mS/cm", "soil_temp": UnitOfTemperature.FAHRENHEIT,
              "air_temp": UnitOfTemperature.FAHRENHEIT, "par": "µmol/m²/s"}
    _CLASS = {"moisture": SensorDeviceClass.MOISTURE, "ec": None, "soil_temp": SensorDeviceClass.TEMPERATURE,
              "air_temp": SensorDeviceClass.TEMPERATURE, "par": None}
    _ICON = {"moisture": "mdi:water-percent", "ec": "mdi:flash", "soil_temp": "mdi:thermometer",
             "air_temp": "mdi:thermometer", "par": "mdi:white-balance-sunny"}

    def __init__(self, mgr, known, gid: str, g: dict, metric: str) -> None:
        super().__init__(mgr, known, f"{gid}_{metric}", f"garden:{gid}", g["name"], g["kind_name"])
        self._gid, self._metric = gid, metric
        self._attr_name = g["metrics"][metric]["name"]
        self._attr_native_unit_of_measurement = self._UNITS[metric]
        self._attr_device_class = self._CLASS[metric]
        self._attr_icon = self._ICON[metric]
        self._attr_state_class = SensorStateClass.MEASUREMENT

    def _m(self):
        g = self._mgr.index()["g"].get(self._gid)
        return g["metrics"][self._metric] if g else None

    @property
    def available(self) -> bool:
        return self._m() is not None

    @property
    def native_value(self):
        m = self._m()
        return m["current"] if m else None

    @property
    def extra_state_attributes(self):
        m = self._m()
        if not m:
            return None
        return {"today_min": m["min"], "today_max": m["max"], "date": m["date"],
                "source": m["source"], "sensors": m["entities"]}


class CoverWaitSensor(_Base):
    """Days until the garden can be planted after a cover crop is terminated."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.DAYS
    _attr_name = "Days until planting after cover crop"
    _attr_icon = "mdi:grass"

    def __init__(self, mgr, known, gid: str, g: dict) -> None:
        super().__init__(mgr, known, f"{gid}_cover_wait", f"garden:{gid}", g["name"], "Garden")
        self._gid = gid

    def _c(self):
        g = self._mgr.index()["g"].get(self._gid)
        return g["cover"] if g else None

    @property
    def available(self) -> bool:
        return self._c() is not None

    @property
    def native_value(self):
        c = self._c()
        if not c or not c["blocked"]:
            return 0
        return c["blocked"]["days_left"]

    @property
    def extra_state_attributes(self):
        c = self._c()
        if not c:
            return None
        b = c["blocked"]
        return {"status": "ready" if not b else b["reason"], "ready_date": b and b["date"],
                "cover_crops": [{"crop": i["crop"], "state": i["state"], "days_in_ground": i["days_in_ground"]}
                                for i in c["items"] if i["state"] != "done"]}


class FrostSensor(_Base):
    """Days to the next expected frost: last spring frost first, then first fall frost."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.DAYS
    _attr_name = "Days until expected frost"
    _attr_icon = "mdi:snowflake-alert"

    def __init__(self, mgr, known, gid: str, g: dict) -> None:
        super().__init__(mgr, known, f"{gid}_frost", f"garden:{gid}", g["name"], "Garden")
        self._gid = gid

    def _f(self):
        g = self._mgr.index()["g"].get(self._gid)
        return g["frost"] if g else None

    @property
    def available(self) -> bool:
        return self._f() is not None

    @property
    def native_value(self):
        f = self._f()
        return f["next"]["days"] if f and f["next"] else None

    @property
    def extra_state_attributes(self):
        f = self._f()
        if not f:
            return None
        n = f["next"]
        return {"event": n["event"] if n else None, "date": n["date"] if n else None,
                "last_spring_frost": f["last"], "first_fall_frost": f["first"]}


class FertilitySensor(_Base):
    """Feed / hold / recheck / ok, from soil EC read together with moisture."""

    _attr_name = "Soil fertility"
    _attr_icon = "mdi:flower"
    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = ["ok", "feed", "hold", "recheck"]

    def __init__(self, mgr, known, gid: str, g: dict) -> None:
        super().__init__(mgr, known, f"{gid}_fertility", f"garden:{gid}", g["name"], "Garden")
        self._gid = gid

    def _f(self):
        g = self._mgr.index()["g"].get(self._gid)
        return g["fertility"] if g else None

    @property
    def available(self) -> bool:
        f = self._f()
        return f is not None and f["action"] is not None

    @property
    def native_value(self):
        f = self._f()
        return f["action"] if f else None

    @property
    def extra_state_attributes(self):
        f = self._f()
        if not f:
            return None
        return {"advice": f["advice"], "ec": f["ec"], "ec_level": f["level"], "moisture": f["moisture"],
                "moisture_state": f["moisture_state"], "ec_target": f["ec_target"],
                "moisture_band": f["moisture_band"], "probe_depth_in": f["depth"],
                "ec_change_14d": f["ec_change"], "last_fed": f["last_fed"]}


class WateringSensor(_Base):
    """Days since the seedling rack or greenhouse was last watered."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.DAYS
    _attr_name = "Days since watered"
    _attr_icon = "mdi:watering-can"

    def __init__(self, mgr, known, gid: str, g: dict) -> None:
        super().__init__(mgr, known, f"{gid}_watered", f"garden:{gid}", g["name"], g["kind_name"])
        self._gid = gid

    def _w(self):
        g = self._mgr.index()["g"].get(self._gid)
        return g["water"] if g else None

    @property
    def available(self) -> bool:
        return self._w() is not None

    @property
    def native_value(self):
        w = self._w()
        return w["days_since"] if w else None

    @property
    def extra_state_attributes(self):
        w = self._w()
        return {"last_watered": w["last"], "water_every_days": w["every"], "status": w["level"]} if w else None


class TraysSensor(_Base):
    """How many 10x20 trays are in use."""

    _attr_name = "10x20 trays in use"
    _attr_icon = "mdi:tray-full"
    _attr_native_unit_of_measurement = "trays"

    def __init__(self, mgr, known, gid: str, g: dict) -> None:
        super().__init__(mgr, known, f"{gid}_trays", f"garden:{gid}", g["name"], g["kind_name"])
        self._gid = gid

    @property
    def available(self) -> bool:
        return self._gid in self._mgr.index()["g"]

    @property
    def native_value(self):
        g = self._mgr.index()["g"].get(self._gid)
        return g["trays"] if g else None


class PlaceEnergySensor(_Base):
    """Energy used today or this month by the heaters, coolers or lights chosen for a place."""

    _attr_device_class = SensorDeviceClass.ENERGY
    _attr_native_unit_of_measurement = "kWh"
    _attr_icon = "mdi:flash"

    def __init__(self, mgr, known, gid: str, g: dict, period: str) -> None:
        super().__init__(mgr, known, f"{gid}_energy_{period}", f"garden:{gid}", g["name"], g["kind_name"])
        self._gid, self._period = gid, period
        self._attr_name = "Energy today" if period == "today" else "Energy this month"

    def _p(self):
        g = self._mgr.index()["g"].get(self._gid)
        return g["power"] if g else None

    @property
    def available(self) -> bool:
        return self._p() is not None

    @property
    def native_value(self):
        p = self._p()
        return p[self._period] if p else None

    @property
    def extra_state_attributes(self):
        p = self._p()
        return {r["name"].lower(): r[self._period] for r in p["groups"]} if p else None


class AdjunctSensor(_Base):
    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.DAYS

    def __init__(self, mgr, known, gid: str, g: dict, atype: dict) -> None:
        super().__init__(mgr, known, f"{gid}_adj_{atype['key']}", f"garden:{gid}", g["name"], "Garden")
        self._gid, self._key = gid, atype["key"]
        self._attr_name = f"Days since {atype['name'].lower()}"

    def _a(self):
        g = self._mgr.index()["g"].get(self._gid)
        return next((a for a in g["adjuncts"] if a["key"] == self._key), None) if g else None

    @property
    def available(self) -> bool:
        return self._a() is not None

    @property
    def native_value(self):
        a = self._a()
        return a["days_since"] if a else None

    @property
    def extra_state_attributes(self):
        a = self._a()
        return {"last": a["last"], "applications_this_year": a["count"], "status": a["label"]} if a else None


def _build(mgr: GardenManager, known: set) -> list:
    ents: list = []
    snap = mgr.snapshot()
    for g in snap["gardens"]:
        if g["kind"] != "garden":
            for uid, cls in (("watered", WateringSensor), ("trays", TraysSensor)):
                if f"{g['id']}_{uid}" not in known:
                    ents.append(cls(mgr, known, g["id"], g))
            for metric in g["metrics"]:
                if f"{g['id']}_{metric}" not in known:
                    ents.append(GardenMetricSensor(mgr, known, g["id"], g, metric))
            if g["power"]:
                for period in ("today", "month"):
                    if f"{g['id']}_energy_{period}" not in known:
                        ents.append(PlaceEnergySensor(mgr, known, g["id"], g, period))
            continue
        if f"{g['id']}_ph" not in known:
            ents.append(GardenPhSensor(mgr, known, g["id"], g))
        if f"{g['id']}_frost" not in known:
            ents.append(FrostSensor(mgr, known, g["id"], g))
        if f"{g['id']}_fertility" not in known:
            ents.append(FertilitySensor(mgr, known, g["id"], g))
        if f"{g['id']}_cover_wait" not in known:
            ents.append(CoverWaitSensor(mgr, known, g["id"], g))
        for metric in g["metrics"]:
            if f"{g['id']}_{metric}" not in known:
                ents.append(GardenMetricSensor(mgr, known, g["id"], g, metric))
        for a in g["adjuncts"]:
            if f"{g['id']}_adj_{a['key']}" not in known:
                ents.append(AdjunctSensor(mgr, known, g["id"], g, a))
    for v in snap["varieties"]:
        if v["archived"]:
            continue
        for d in COMMON + (TREE if v["kind"] == "tree" else ANNUAL):
            if f"{v['id']}_{d.key}" not in known:
                ents.append(VarietySensor(mgr, known, v["id"], v, d))
        sp = mgr.get_species(v["species"]) or {}
        for pest in sp.get("pests", []):
            if f"{v['id']}_dd_{pest['key']}" not in known:
                ents.append(PestSensor(mgr, known, v["id"], v, pest))
    return ents


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    mgr: GardenManager = hass.data[DOMAIN]
    known: set[str] = set()
    async_add_entities(_build(mgr, known))

    @callback
    def _structure() -> None:
        async_add_entities(_build(mgr, known))

    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_STRUCTURE, _structure))
