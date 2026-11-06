"""Problem sensors: frost and heat from the forecast, and each rack or greenhouse with an alarm switched on."""
from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_STRUCTURE, SIGNAL_UPDATE
from .manager import GardenManager


class TemperatureAlarm(BinarySensorEntity):
    """On from the moment the air goes past a limit until the alarm is acknowledged."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_name = "Temperature alarm"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM

    _uid = "temp_alarm"

    def __init__(self, mgr: GardenManager, known: set, gid: str, g: dict) -> None:
        self._mgr, self._known, self._gid = mgr, known, gid
        self._attr_unique_id = f"{gid}_{self._uid}"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"garden:{gid}")}, name=g["name"],
                                            model=g["kind_name"], manufacturer="Garden Tracker")
        known.add(self._attr_unique_id)

    def _a(self) -> dict | None:
        g = self._mgr.index()["g"].get(self._gid)
        return g["alarm"] if g else None

    async def async_added_to_hass(self) -> None:
        @callback
        def _upd() -> None:
            self.async_write_ha_state()
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_UPDATE, _upd))

    async def async_will_remove_from_hass(self) -> None:
        self._known.discard(self._attr_unique_id)

    @property
    def available(self) -> bool:
        return self._a() is not None

    @property
    def is_on(self) -> bool:
        a = self._a()
        return bool(a and a["enabled"] and a["alerts"])

    @property
    def extra_state_attributes(self):
        a = self._a()
        if not a:
            return None
        return {"high_limit": a["high"], "low_limit": a["low"],
                "alarms": [{"kind": x["kind"], "since": x["start"], "ended": x["end"], "peak": x["peak"]}
                           for x in a["alerts"]]}


class SensorAlarm(TemperatureAlarm):
    """On while a sensor that is in use has reported nothing for over an hour and nobody has acknowledged it."""

    _attr_name = "Sensor offline alarm"
    _uid = "sensor_alarm"

    def _a(self) -> dict | None:
        g = self._mgr.index()["g"].get(self._gid)
        return g["sensor_alarm"] if g else None

    @property
    def is_on(self) -> bool:
        a = self._a()
        return bool(a and a["enabled"] and a["alerts"])

    @property
    def extra_state_attributes(self):
        a = self._a()
        return None if not a else {"sensors": [{"entity_id": x["entity"], "measures": x["metric"], "since": x["since"],
                                                "back": x["end"]} for x in a["alerts"]]}


class FrostHeatAlert(BinarySensorEntity):
    """On while the forecast brings frost or heat that matters to your plants and you have not dismissed it."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    _attr_name = "Frost and heat alert"
    _attr_device_class = BinarySensorDeviceClass.PROBLEM
    _attr_unique_id = "frost_heat_alert"

    def __init__(self, mgr: GardenManager) -> None:
        self._mgr = mgr
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, "weather_alerts")}, name="Garden weather",
                                            manufacturer="Garden Tracker")

    async def async_added_to_hass(self) -> None:
        @callback
        def _upd() -> None:
            self.async_write_ha_state()
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_UPDATE, _upd))

    def _open(self) -> list[dict]:
        return [a for a in self._mgr.snapshot()["alerts"] if not a["acked"]]

    @property
    def is_on(self) -> bool:
        return bool(self._open())

    @property
    def extra_state_attributes(self):
        snap = self._mgr.snapshot()
        return {"alerts": [{"id": a["id"], "kind": a["kind"], "title": a["title"], "text": a["text"], "dates": a["dates"],
                            "plants": [p["name"] for p in a["plants"]]} for a in self._open()],
                "forecast_source": snap["forecast"]["source"] or None}


def _build(mgr: GardenManager, known: set) -> list:
    out: list = []
    if "frost_heat_alert" not in known:
        known.add("frost_heat_alert")
        out.append(FrostHeatAlert(mgr))
    for g in mgr.snapshot()["gardens"]:
        if g["alarm"] and g["alarm"]["enabled"] and f"{g['id']}_temp_alarm" not in known:
            out.append(TemperatureAlarm(mgr, known, g["id"], g))
        if g["sensor_alarm"]["enabled"] and g["sensor_alarm"]["in_use"] and f"{g['id']}_sensor_alarm" not in known:
            out.append(SensorAlarm(mgr, known, g["id"], g))
    return out


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    mgr: GardenManager = hass.data[DOMAIN]
    known: set[str] = set()
    async_add_entities(_build(mgr, known))

    @callback
    def _structure() -> None:
        async_add_entities(_build(mgr, known))

    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_STRUCTURE, _structure))
