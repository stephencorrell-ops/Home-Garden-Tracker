"""The Home Assistant side: devices, entities, the thermostat, alarms and services, in a real test instance."""
from datetime import timedelta

import pytest
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.util import dt as dt_util

from conftest import DOMAIN


def devices(hass, entry) -> dict:
    reg = dr.async_get(hass)
    return {next(iter(d.identifiers))[1]: d for d in dr.async_entries_for_config_entry(reg, entry.entry_id)}


def micro_entities(hass, entry) -> list[str]:
    return [e.entity_id for e in er.async_entries_for_config_entry(er.async_get(hass), entry.entry_id)
            if e.unique_id.startswith("micro_")]


def place(hass, name) -> dict:
    return next(g for g in hass.data[DOMAIN].snapshot()["gardens"] if g["name"] == name)


async def greenhouse(hass, call, name="GH", temp="70"):
    await call("add_garden", name=name, kind="greenhouse")
    hass.states.async_set("sensor.gh", temp, {"unit_of_measurement": "°F"})
    await call("set_garden_sensors", garden=name, metric="air_temp", entities=["sensor.gh"])


async def test_microclimate_sensors_are_there_after_setup(hass, entry, call):
    assert micro_entities(hass, entry), "the Microclimate device was removed at startup"
    assert hass.states.get("sensor.microclimate_local_hardiness_zone") is not None
    device_id = devices(hass, entry)["microclimate"].id
    await call("add_garden", name="Bed")
    await call("add_garden", name="Bed 2")
    assert devices(hass, entry)["microclimate"].id == device_id


async def test_reload_keeps_microclimate(hass, entry):
    hass.states.async_set("sensor.out2", "40", {"unit_of_measurement": "°F"})
    hass.config_entries.async_update_entry(entry, options={"temperature_entity": "sensor.out2"})
    await hass.async_block_till_done()
    assert hass.data[DOMAIN].outdoor_entity == "sensor.out2"
    assert micro_entities(hass, entry)
    assert await hass.config_entries.async_unload(entry.entry_id)
    await hass.async_block_till_done()
    assert DOMAIN not in hass.data


async def test_garden_and_plant_devices_follow_archive_and_restore(hass, entry, call):
    await call("add_garden", name="Bed")
    await call("add_variety", garden="Bed", species="tomato", variety="Sungold", plants=3)
    vid = hass.data[DOMAIN].snapshot()["varieties"][0]["id"]
    assert f"variety:{vid}" in devices(hass, entry)
    assert hass.states.get("sensor.sungold_plants_alive").state == "3"
    await call("archive_plant", plant=vid)
    assert f"variety:{vid}" not in devices(hass, entry)
    await call("restore_plant", plant=vid)
    assert f"variety:{vid}" in devices(hass, entry)
    gid = place(hass, "Bed")["id"]
    await call("archive_plant", plant=vid)  # a garden with plants in it can't be removed
    await call("remove_garden", garden="Bed")
    assert f"garden:{gid}" not in devices(hass, entry)
    await call("restore_garden", garden="Bed")
    assert f"garden:{gid}" in devices(hass, entry)


async def test_temperature_alarm_appears_when_turned_on_later(hass, entry, call):
    await greenhouse(hass, call)
    assert hass.states.get("binary_sensor.gh_sensor_offline_alarm") is not None
    assert hass.states.get("binary_sensor.gh_temperature_alarm") is None
    await call("set_temp_alarm", garden="GH", enabled=True, high=85, low=50)
    assert hass.states.get("binary_sensor.gh_temperature_alarm").state == "off"
    hass.states.async_set("sensor.gh", "45", {"unit_of_measurement": "°F"})
    hass.data[DOMAIN].check_alarms()
    await hass.async_block_till_done()
    assert hass.states.get("binary_sensor.gh_temperature_alarm").state == "on"
    await call("ack_temp_alarm", garden="GH")
    assert hass.states.get("binary_sensor.gh_temperature_alarm").state == "off"


async def test_thermostat_heats_then_rests_as_idle(hass, entry, call):
    await greenhouse(hass, call, temp="40")
    hass.states.async_set("switch.heat", "off")
    await call("set_greenhouse_climate", garden="GH", enabled=True, heat_set=50, cool_set=80, heaters=["switch.heat"],
               heat_max_run=1, heat_rest=10)
    mgr, gid = hass.data[DOMAIN], place(hass, "GH")["id"]
    st = hass.states.get("climate.gh")
    assert (st.state, st.attributes["hvac_action"]) == ("heat_cool", "heating")
    mgr.climate_state[gid]["since"] = dt_util.utcnow() - timedelta(minutes=5)  # past the maximum run time
    mgr.run_climate()
    await hass.async_block_till_done()
    st = hass.states.get("climate.gh")
    assert st.attributes["status"] == "resting"
    assert st.attributes["hvac_action"] == "idle"
    await hass.services.async_call("climate", "set_hvac_mode", {"entity_id": "climate.gh", "hvac_mode": "off"},
                                   blocking=True)
    await hass.async_block_till_done()
    assert hass.states.get("climate.gh").attributes["hvac_action"] == "off"


async def test_rain_and_energy_are_counted(hass, entry, call):
    hass.states.async_set("sensor.rain", "0.1", {"unit_of_measurement": "in"})
    await call("set_microclimate", rain_entities=["sensor.rain"])
    hass.states.async_set("sensor.rain", "0.3", {"unit_of_measurement": "in"})
    await hass.async_block_till_done()
    rain = hass.states.get("sensor.microclimate_rain_today")  # the test instance shows rain in mm
    assert (float(rain.state), rain.attributes["unit_of_measurement"]) == (pytest.approx(5.08), "mm")

    await call("add_garden", name="Rack", kind="rack")
    hass.states.async_set("sensor.kwh", "10", {"unit_of_measurement": "kWh"})
    await call("set_power_sensors", garden="Rack", group="power", entities=["sensor.kwh"])
    await call("set_power_rate", cents=20)
    hass.states.async_set("sensor.kwh", "10.5", {"unit_of_measurement": "kWh"})
    hass.data[DOMAIN].sample_power()
    await hass.async_block_till_done()
    assert float(hass.states.get("sensor.rack_energy_today").state) == pytest.approx(0.5)
    assert float(hass.states.get("sensor.rack_energy_cost_today").state) == pytest.approx(0.1)


async def test_services_run_and_bad_input_is_refused(hass, entry, call):
    await call("add_garden", name="Bed")
    await call("add_adjunct_type", garden="Bed", name="Sulfur")
    await call("log_adjunct", garden="Bed", adjunct="Sulfur")
    await call("log_ph", garden="Bed", value=6.2)
    await call("add_variety", garden="Bed", species="tomato", variety="Sungold", plants=2)
    await call("add_variety", garden="Bed", species="garlic", variety="Music", plants=50)
    await call("add_variety", species="apple", variety="Gala", kind="tree")
    vid = {v["name"]: v["id"] for v in hass.data[DOMAIN].snapshot()["varieties"]}
    await call("log_harvest", plant=vid["Sungold"], lbs=2.5)
    await call("log_fertilizer", plant=vid["Sungold"], product="Fish", n=2, p=4, k=1)
    await call("log_spray", plant=vid["Gala"], product="Captan", phi_days=7, reapply_days=10)
    await call("log_harvest", plant=vid["Music"], lbs=10)  # garlic is pulled when harvested
    await call("plant_again", plant=vid["Music"])
    await call("end_season", garden="Bed", cover_crop="Winter rye")
    assert hass.states.get("sensor.bed_soil_ph").state == "6.2"
    assert hass.states.get("sensor.bed_days_since_sulfur").state == "0"

    harvest = dict(hass.data[DOMAIN].find_variety(vid["Sungold"], True)["harvests"][0])
    with pytest.raises(ServiceValidationError):
        await call("edit_entry", kind="harvest", parent=vid["Sungold"], entry_id=harvest["id"], date="2026-01-01", lbs=-1)
    assert hass.data[DOMAIN].find_variety(vid["Sungold"], True)["harvests"][0] == harvest
    with pytest.raises(ServiceValidationError):
        await call("set_greenhouse_climate", garden="Bed", enabled=True)
