"""A thermostat for each greenhouse: holds the air between a heat and a cool set point."""
from __future__ import annotations

from homeassistant.components.climate import (
    ClimateEntity, ClimateEntityFeature, HVACAction, HVACMode)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, SIGNAL_STRUCTURE, SIGNAL_UPDATE
from .manager import GardenManager
from .model import GardenError

_ACTION = {"heating": HVACAction.HEATING, "cooling": HVACAction.COOLING, "idle": HVACAction.IDLE,
           "no_sensor": HVACAction.IDLE, "off": HVACAction.OFF}


class GreenhouseThermostat(ClimateEntity):
    _attr_has_entity_name = True
    _attr_name = None
    _attr_should_poll = False
    _attr_icon = "mdi:greenhouse"
    _attr_temperature_unit = UnitOfTemperature.FAHRENHEIT
    _attr_hvac_modes = [HVACMode.HEAT_COOL, HVACMode.OFF]
    _attr_supported_features = (ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
                                | ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF)
    _attr_min_temp, _attr_max_temp, _attr_target_temperature_step = 30, 110, 1

    def __init__(self, mgr: GardenManager, known: set, gid: str, g: dict) -> None:
        self._mgr, self._known, self._gid = mgr, known, gid
        self._attr_unique_id = f"{gid}_thermostat"
        if g["kind"] == "rack":
            self._attr_icon = "mdi:table-furniture"
        self._attr_device_info = DeviceInfo(identifiers={(DOMAIN, f"garden:{gid}")}, name=g["name"],
                                            model=g["kind_name"], manufacturer="Garden Tracker")
        known.add(self._attr_unique_id)

    def _c(self) -> dict | None:
        g = self._mgr.index()["g"].get(self._gid)
        return g["climate"] if g else None

    async def async_added_to_hass(self) -> None:
        @callback
        def _upd() -> None:
            self.async_write_ha_state()
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_UPDATE, _upd))

    async def async_will_remove_from_hass(self) -> None:
        self._known.discard(self._attr_unique_id)

    @property
    def available(self) -> bool:
        return self._c() is not None

    @property
    def hvac_mode(self):
        c = self._c()
        return HVACMode.HEAT_COOL if c and c["enabled"] else HVACMode.OFF

    @property
    def hvac_action(self):
        c = self._c()
        return _ACTION.get(c["state"], HVACAction.OFF) if c else None

    @property
    def current_temperature(self):
        c = self._c()
        return c["temp"] if c else None

    @property
    def target_temperature_low(self):
        c = self._c()
        return c["heat_set"] if c else None

    @property
    def target_temperature_high(self):
        c = self._c()
        return c["cool_set"] if c else None

    @property
    def extra_state_attributes(self):
        c = self._c()
        if not c:
            return None
        out = {"heaters": c["heaters"], "fans": c["coolers"], "status": c["state"], "fan_running": c["fan_on"]}
        if c["lights"]:
            out.update(lights=c["lights"], lights_on=c["lights_on"])
        return out

    def _apply(self, **kw) -> None:
        try:
            self._mgr.set_climate(self._gid, **kw)
        except GardenError as err:
            raise HomeAssistantError(str(err)) from err

    async def async_set_temperature(self, **kwargs) -> None:
        low, high = kwargs.get("target_temp_low"), kwargs.get("target_temp_high")
        if low is None and high is None and kwargs.get(ATTR_TEMPERATURE) is not None:
            return
        self._apply(heat_set=low, cool_set=high)

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        self._apply(enabled=hvac_mode != HVACMode.OFF)


def _build(mgr: GardenManager, known: set) -> list:
    return [GreenhouseThermostat(mgr, known, g["id"], g) for g in mgr.snapshot()["gardens"]
            if g["kind"] in ("greenhouse", "rack") and f"{g['id']}_thermostat" not in known]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    mgr: GardenManager = hass.data[DOMAIN]
    known: set[str] = set()
    async_add_entities(_build(mgr, known))

    @callback
    def _structure() -> None:
        async_add_entities(_build(mgr, known))

    entry.async_on_unload(async_dispatcher_connect(hass, SIGNAL_STRUCTURE, _structure))
