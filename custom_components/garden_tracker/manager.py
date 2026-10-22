"""Home Assistant wrapper around the pure garden model."""
from __future__ import annotations

import json
import logging
from datetime import timedelta
from pathlib import Path

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfTemperature
from homeassistant.exceptions import HomeAssistantError
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.event import async_track_state_change_event, async_track_time_interval
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util
from homeassistant.util.unit_conversion import TemperatureConverter

from .const import SIGNAL_STRUCTURE, SIGNAL_UPDATE, STORAGE_KEY, STORAGE_VERSION
from .model import METRICS, GardenModel


_LOGGER = logging.getLogger(__name__)
CLIMATE_INTERVAL = timedelta(minutes=1)
CLIMATE_HYSTERESIS = 1.0  # degrees F past a set point before a heater or cooler turns off again


class GardenManager(GardenModel):
    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__({}, lambda: dt_util.now().date(), self._on_change, self._on_structure)
        self.hass = hass
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._ph_unsub = None
        self._climate_unsub = None
        self._ready = False

    async def async_load(self) -> None:
        self.load(await self._store.async_load())
        path = Path(__file__).parent / "species.json"
        text = await self.hass.async_add_executor_job(path.read_text, "utf-8")
        self.presets = {k: v for k, v in json.loads(text).items() if not k.startswith("_")}
        self._ready = True
        self.refresh_ph_listeners()
        self._climate_unsub = async_track_time_interval(self.hass, lambda _now: self.run_climate(), CLIMATE_INTERVAL)

    async def async_shutdown(self) -> None:
        if self._climate_unsub:
            self._climate_unsub()
            self._climate_unsub = None
        if self._ph_unsub:
            self._ph_unsub()
            self._ph_unsub = None
        await self._store.async_save(self.data)

    # ---- model callbacks ------------------------------------------------------
    def _on_change(self) -> None:
        if not self._ready:
            return
        self._store.async_delay_save(lambda: self.data, 5)
        async_dispatcher_send(self.hass, SIGNAL_UPDATE)

    def _on_structure(self) -> None:
        if not self._ready:
            return
        self.refresh_ph_listeners()
        async_dispatcher_send(self.hass, SIGNAL_STRUCTURE)

    # ---- soil sensors (pH, moisture, EC, temperature) ---------------------------
    def refresh_ph_listeners(self) -> None:
        if self._ph_unsub:
            self._ph_unsub()
            self._ph_unsub = None
        by_entity: dict[str, set[tuple[str, str]]] = {}
        for g in self.data["gardens"].values():
            if g.get("ph_entity"):
                by_entity.setdefault(g["ph_entity"], set()).add((g["id"], "ph"))
            for metric, ents in g.get("sensors", {}).items():
                for ent in ents:
                    by_entity.setdefault(ent, set()).add((g["id"], metric))
        if not by_entity:
            self.run_climate()
            return

        @callback
        def _changed(event) -> None:
            for gid, metric in by_entity.get(event.data["entity_id"], ()):
                self._ingest(gid, metric)
                if metric == "air_temp":
                    self.run_climate(gid)

        self._ph_unsub = async_track_state_change_event(self.hass, list(by_entity), _changed)
        for pairs in by_entity.values():
            for gid, metric in pairs:
                self._ingest(gid, metric)
        self.run_climate()

    def _convert(self, metric: str, state) -> float | None:
        if state is None or state.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
            return None
        try:
            val = float(state.state)
        except ValueError:
            return None
        unit = (state.attributes.get("unit_of_measurement") or "").replace("μ", "µ").lower()
        if metric in ("soil_temp", "air_temp"):
            try:
                return TemperatureConverter.convert(
                    val, state.attributes.get("unit_of_measurement") or self.hass.config.units.temperature_unit,
                    UnitOfTemperature.FAHRENHEIT)
            except HomeAssistantError:
                return None
        if metric == "ec":
            if unit in ("µs/cm", "us/cm"):
                return val / 1000
            if unit == "s/m":
                return val * 10
            if unit == "ms/m":
                return val / 100
            if unit in ("", "none") and val > 30:
                return val / 1000  # unitless readings that large are almost always µS/cm
        return val

    # ---- greenhouse thermostat ------------------------------------------------------
    def _air_temp_now(self, g: dict) -> float | None:
        if g.get("sensors_paused", {}).get("air_temp"):
            return None
        vals = [v for v in (self._convert("air_temp", self.hass.states.get(e))
                            for e in g.get("sensors", {}).get("air_temp", [])) if v is not None]
        return sum(vals) / len(vals) if vals else None

    def _drive(self, entity_id: str, on: bool, role: str) -> None:
        domain = entity_id.split(".")[0]
        st = self.hass.states.get(entity_id)
        if st is None or st.state == STATE_UNAVAILABLE:
            return
        if domain == "climate":
            mode = ("heat" if role == "heater" else "cool") if on else "off"
            if st.state == mode:
                return
            call = ("climate", "set_hvac_mode", {"entity_id": entity_id, "hvac_mode": mode})
        else:
            if st.state == ("on" if on else "off"):
                return
            call = ("homeassistant", "turn_on" if on else "turn_off", {"entity_id": entity_id})

        async def _go() -> None:
            try:
                await self.hass.services.async_call(*call, blocking=False)
            except HomeAssistantError as err:
                _LOGGER.warning("Garden Tracker: could not switch %s: %s", entity_id, err)
        self.hass.async_create_task(_go())

    @callback
    def run_climate(self, only: str | None = None) -> None:
        """Hold each greenhouse between its heat and cool set points by switching the chosen devices."""
        if not self._ready:
            return
        for g in list(self.data["gardens"].values()):
            if g.get("kind") != "greenhouse" or (only and g["id"] != only):
                continue
            c = g["climate"]
            prev = self.climate_state.get(g["id"], {}).get("state")
            temp = self._air_temp_now(g)
            if not c["enabled"]:
                state = "off"
            elif temp is None:
                state = "no_sensor"  # fail safe: never leave a heater running without a temperature
            else:
                heating, cooling = prev == "heating", prev == "cooling"
                if temp < c["heat_set"]:
                    heating, cooling = True, False
                elif heating and temp >= c["heat_set"] + CLIMATE_HYSTERESIS:
                    heating = False
                if temp > c["cool_set"]:
                    cooling, heating = True, False
                elif cooling and temp <= c["cool_set"] - CLIMATE_HYSTERESIS:
                    cooling = False
                state = "heating" if heating else "cooling" if cooling else "idle"
            if c["enabled"] or prev in ("heating", "cooling"):  # switching control off also switches devices off
                for e in c["heaters"]:
                    self._drive(e, state == "heating", "heater")
                for e in c["coolers"]:
                    self._drive(e, state == "cooling", "cooler")
            if state != prev:
                self.climate_state[g["id"]] = {"state": state}
                self._touch()

    def _ingest(self, gid: str, metric: str) -> None:
        g = self.data["gardens"].get(gid)
        if not g:
            return
        if metric == "ph":
            state = self.hass.states.get(g.get("ph_entity") or "")
            if state is not None and state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                try:
                    self.record_sensor_ph(gid, float(state.state))
                except ValueError:
                    pass
            return
        vals = [v for v in (self._convert(metric, self.hass.states.get(e))
                            for e in g.get("sensors", {}).get(metric, [])) if v is not None]
        if vals:
            avg = sum(vals) / len(vals)
            spec = METRICS.get(metric)
            if spec and not spec["lo"] <= avg <= spec["hi"]:
                _LOGGER.warning("Garden Tracker: %s reading %s from %s is outside %s to %s %s and was ignored; "
                                "check the sensor's unit", metric, round(avg, 2), g.get("sensors", {}).get(metric),
                                spec["lo"], spec["hi"], spec["unit"])
            self.record_sensor_metric(gid, metric, avg)
        else:
            _LOGGER.debug("Garden Tracker: no usable %s values for garden %s (sensors unavailable or non-numeric)",
                          metric, gid)
