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
FREEZE_GUARD_F = 36.0  # below this the heater is never held off by a maximum run time
ENERGY_UNITS = {"kwh": 1.0, "wh": 0.001, "mwh": 1000.0}
POWER_UNITS = {"w": 0.001, "kw": 1.0}
CLIMATE_HYSTERESIS = 1.0  # degrees F past a set point before a heater or cooler turns off again


class GardenManager(GardenModel):
    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__({}, lambda: dt_util.now().date(), self._on_change, self._on_structure)
        self.hass = hass
        self._store: Store = Store(hass, STORAGE_VERSION, STORAGE_KEY)
        self._ph_unsub = None
        self._climate_unsub = None
        self._power_t: dict[str, object] = {}
        self._ready = False

    async def async_load(self) -> None:
        self.load(await self._store.async_load())
        path = Path(__file__).parent / "species.json"
        text = await self.hass.async_add_executor_job(path.read_text, "utf-8")
        self.presets = {k: v for k, v in json.loads(text).items() if not k.startswith("_")}
        self._ready = True
        self.refresh_ph_listeners()
        self._climate_unsub = async_track_time_interval(self.hass, self._tick, CLIMATE_INTERVAL)

    def _power_changed(self) -> None:
        if self._ready:
            self.sample_power()

    def _alarm_changed(self) -> None:
        if self._ready:
            self.check_alarms()

    @callback
    def check_alarms(self) -> None:
        """Compare each rack and greenhouse temperature with its alarm limits."""
        if not self._ready:
            return
        now, changed = dt_util.utcnow(), False
        for g in list(self.data["gardens"].values()):
            if g["sensor_alarm"]["enabled"]:
                status = {}
                for ent, metric in self.sensors_in_use(g).items():
                    st = self.hass.states.get(ent)
                    try:
                        ok = st is not None and st.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE) and float(st.state) == float(st.state)
                    except (TypeError, ValueError):
                        ok = False
                    status[ent] = (metric, ok)
                if self.update_sensor_alarm(g["id"], status, now):
                    changed = True
            if g.get("kind") == "garden" or not g["alarm"]["enabled"]:
                continue
            temp = self._air_temp_now(g)
            if temp is not None and self.update_alarm(g["id"], temp, now):
                changed = True
        if changed:
            self._touch()

    @callback
    def _tick(self, _now) -> None:
        self.check_alarms()
        self.run_climate()
        self.sample_power()

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
        now = dt_util.utcnow()
        for g in list(self.data["gardens"].values()):
            if g.get("kind") != "greenhouse" or (only and g["id"] != only):
                continue
            c = g["climate"]
            old = self.climate_state.get(g["id"], {})
            prev = old.get("state")
            temp = self._air_temp_now(g)
            new: dict = {}
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
                run = (now - old["since"]).total_seconds() / 60 if prev == "heating" and old.get("since") else 0
                mn, mx, rest = c.get("heat_min_run", 0), c.get("heat_max_run", 0), c.get("heat_rest", 10)
                if prev == "heating" and not heating and not cooling and mn and run < mn:
                    heating = True  # minimum run time: keep the heater on until it has run long enough
                resting_until = old.get("rest_until") if prev == "resting" else None
                cold = temp < FREEZE_GUARD_F  # near freezing, run times never stop the heater
                if heating and not cold:
                    if prev == "heating" and mx and run >= mx:
                        heating, resting_until = False, now + timedelta(minutes=rest)
                    elif prev != "heating" and resting_until and now < resting_until:
                        heating = False
                if heating:
                    state = "heating"
                    new["since"] = old["since"] if prev == "heating" and old.get("since") else now
                elif cooling:
                    state = "cooling"
                elif resting_until and now < resting_until and temp < c["heat_set"] + CLIMATE_HYSTERESIS:
                    state = "resting"
                    new["rest_until"] = resting_until
                else:
                    state = "idle"
            new["state"] = state
            if c["enabled"] or prev in ("heating", "cooling", "resting"):  # switching control off also switches devices off
                for e in c["heaters"]:
                    self._drive(e, state == "heating", "heater")
                for e in c["coolers"]:
                    self._drive(e, state == "cooling", "cooler")
            if state != prev:
                self.climate_state[g["id"]] = new
                self._touch()
            else:
                old.update({k: v for k, v in new.items() if k != "state"})

    # ---- power and energy ---------------------------------------------------------------
    @callback
    def sample_power(self) -> None:
        """Add up energy from the power or energy sensors chosen for each rack and greenhouse."""
        if not self._ready:
            return
        now = dt_util.utcnow()
        changed = False
        for g in self.data["gardens"].values():
            for group, ents in (g.get("power_sensors") or {}).items():
                for e in ents:
                    st = self.hass.states.get(e)
                    if st is None or st.state in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                        self._power_t.pop(e, None)
                        continue
                    try:
                        val = float(st.state)
                    except ValueError:
                        continue
                    unit = (st.attributes.get("unit_of_measurement") or "").strip().lower()
                    kwh = 0.0
                    if unit in ENERGY_UNITS:
                        total = val * ENERGY_UNITS[unit]
                        last = g["energy_last"].get(e)
                        if last != total:
                            g["energy_last"][e] = total
                            changed = True
                        if last is not None:
                            d = total - last
                            kwh = d if d >= 0 else total  # a drop means the meter was reset
                            if kwh > 500:
                                kwh = 0.0  # ignore a wild jump rather than record nonsense
                    elif unit in POWER_UNITS:
                        t0 = self._power_t.get(e)
                        self._power_t[e] = now
                        if t0 is not None:
                            secs = min((now - t0).total_seconds(), 300)
                            kwh = val * POWER_UNITS[unit] * secs / 3600
                    if kwh > 0:
                        self.record_energy(g, group, kwh)
                        changed = True
        if changed:
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
