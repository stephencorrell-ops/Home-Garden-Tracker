"""Services. The Lovelace card uses these too, so automations can do everything the card can."""
from __future__ import annotations

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .core.api import HANDLERS
from .core.model import (ARCHIVE_REASONS, COVER_METHODS, KINDS, LOCATION_KINDS, METRICS, REASONS,
                         GardenError)
from .manager import GardenManager

R, O = vol.Required, vol.Optional
NUM = vol.Coerce(float)
INT = vol.Coerce(int)
POS_INT = vol.All(vol.Coerce(int), vol.Range(min=1, max=1000))
DAYS = vol.All(vol.Coerce(int), vol.Range(min=0, max=3650))

SERVICES: dict[str, dict] = {
    "add_garden": {R("name"): cv.string, O("ph_entity"): cv.string, O("ph_min"): NUM, O("ph_max"): NUM,
        O("kind"): vol.In(list(LOCATION_KINDS))},
    "update_garden": {R("garden"): cv.string, O("name"): cv.string, O("ph_entity"): cv.string,
        O("ph_min"): NUM, O("ph_max"): NUM,
        O("ec_min"): NUM, O("ec_max"): NUM, O("moisture_min"): NUM, O("moisture_max"): NUM,
        O("probe_depth"): NUM},
    "remove_garden": {R("garden"): cv.string},
    "add_adjunct_type": {R("garden"): cv.string, R("name"): cv.string, O("per_year"): POS_INT,
        O("interval_days"): POS_INT},
    "remove_adjunct_type": {R("garden"): cv.string, R("adjunct"): cv.string},
    "log_adjunct": {R("garden"): cv.string, R("adjunct"): cv.string, O("date"): cv.date,
        O("product"): cv.string, O("amount"): cv.string, O("notes"): cv.string},
    "log_ph": {R("garden"): cv.string, R("value"): NUM, O("date"): cv.date},
    "add_variety": {R("garden"): cv.string, R("species"): cv.string, R("variety"): cv.string,
        O("plants"): POS_INT, O("origin"): vol.In(["seed", "start"]),
        O("planted_date"): cv.date, O("in_ground_date"): cv.date, O("days_to_harvest"): DAYS,
        O("expected_harvest_date"): cv.date, O("expected_yield"): NUM, O("notes"): cv.string,
        O("kind"): vol.In(["plant", "tree"]), O("single_harvest"): cv.boolean, O("multi_year"): cv.boolean,
        O("container"): cv.string},
    "update_variety": {R("plant"): cv.string, O("name"): cv.string, O("garden"): cv.string,
        O("planted_date"): cv.date, O("in_ground_date"): cv.date, O("days_to_harvest"): DAYS,
        O("expected_harvest_date"): cv.date, O("expected_yield"): NUM, O("notes"): cv.string,
        O("add_plants"): POS_INT, O("single_harvest"): cv.boolean, O("multi_year"): cv.boolean,
        O("container"): cv.string},
    "set_harvest": {R("plant"): cv.string, O("expected_date"): cv.date, O("expected_yield"): NUM},
    "log_stage": {R("plant"): cv.string, R("stage"): vol.In(["planted", "upotted", "in_ground"]), O("date"): cv.date},
    "log_fertilizer": {R("plant"): cv.string, R("product"): cv.string, O("n"): NUM, O("p"): NUM, O("k"): NUM,
        O("date"): cv.date, O("notes"): cv.string},
    "log_spray": {R("plant"): cv.string, R("product"): cv.string, O("date"): cv.date, O("target"): cv.string,
        O("phi_days"): DAYS, O("reapply_days"): DAYS},
    "set_biofix": {R("plant"): cv.string, R("pest"): cv.string, O("date"): cv.date},
    "add_review": {R("plant"): cv.string, R("notes"): cv.string, O("year"): cv.positive_int},
    "log_harvest": {R("plant"): cv.string, R("lbs"): NUM, O("date"): cv.date, O("notes"): cv.string,
        O("plants"): POS_INT},
    "set_plant_status": {R("plant"): cv.string, R("individual"): cv.string,
        R("status"): vol.In(["alive", "dead", "pulled"]), O("reason"): vol.In(REASONS),
        O("note"): cv.string, O("date"): cv.date},
    "mark_plants_lost": {R("plant"): cv.string, R("count"): POS_INT, R("status"): vol.In(["dead", "pulled"]),
        R("reason"): vol.In(REASONS), O("note"): cv.string, O("date"): cv.date},
    "restore_plants": {R("plant"): cv.string, R("count"): POS_INT, O("status"): vol.In(["dead", "pulled"]),
        O("reason"): vol.In(REASONS), O("date"): cv.date},
    "set_garden_sensors": {R("garden"): cv.string, R("metric"): vol.In(list(METRICS)),
        R("entities"): vol.All(cv.ensure_list, [cv.string])},
    "set_soil_sensors_paused": {R("garden"): cv.string, R("paused"): cv.boolean,
        O("group"): vol.In(["moisture_ec", "soil_temp", "air_temp", "out_temp", "par", "all"])},
    "log_garden_reading": {R("garden"): cv.string, R("metric"): vol.In(list(METRICS)),
        R("value"): NUM, O("date"): cv.date},
    "set_layout": {R("garden"): cv.string, O("width_ft"): NUM, O("length_ft"): NUM, O("row_in"): vol.All(vol.Coerce(int), vol.In([24, 30, 36])),
        O("double"): cv.boolean, O("stagger"): cv.boolean},
    "assign_layout_rows": {R("garden"): cv.string, O("crop"): vol.Any(None, cv.string), O("rows"): vol.All(cv.ensure_list, [vol.All(vol.Coerce(int), vol.Range(min=0, max=199))])},
    "set_layout_crop": {R("garden"): cv.string, R("crop"): cv.string, O("spacing_in"): NUM, O("support"): vol.In(["none", "tpost", "cage", "corral"]), O("post_ft"): NUM,
        O("post_kind"): vol.In(["stake", "tpost"]), O("twine_levels"): vol.All(vol.Coerce(int), vol.Range(min=1, max=6)),
        O("across_in"): NUM, O("stagger"): cv.boolean},
    "remove_layout": {R("garden"): cv.string},
    "set_trays": {R("garden"): cv.string, R("trays"): vol.All(vol.Coerce(int), vol.Range(min=0, max=500))},
    "log_watering": {R("garden"): cv.string, O("date"): cv.date, O("notes"): cv.string},
    "set_water_interval": {R("garden"): cv.string, O("days"): vol.All(vol.Coerce(int), vol.Range(min=0, max=60))},
    "set_greenhouse_climate": {R("garden"): cv.string, O("enabled"): cv.boolean, O("heat_set"): NUM,
        O("cool_set"): NUM, O("heaters"): vol.All(cv.ensure_list, [cv.string]),
        O("coolers"): vol.All(cv.ensure_list, [cv.string]),
        O("heat_min_run"): vol.All(vol.Coerce(int), vol.Range(min=0, max=720)),
        O("heat_max_run"): vol.All(vol.Coerce(int), vol.Range(min=0, max=720)),
        O("heat_rest"): vol.All(vol.Coerce(int), vol.Range(min=0, max=720)),
        O("lights"): vol.All(cv.ensure_list, [cv.string]), O("light_sched"): cv.boolean,
        O("light_on"): cv.string, O("light_hours"): vol.All(NUM, vol.Range(min=1, max=24)),
        O("fan_sched"): cv.boolean, O("fan_minutes"): vol.All(vol.Coerce(int), vol.Range(min=1, max=1440)),
        O("fan_every"): vol.All(NUM, vol.Range(min=0.5, max=168)), O("fan_lights_only"): cv.boolean,
        O("cool_off"): vol.Any(None, NUM), O("fan_min_run"): vol.All(vol.Coerce(int), vol.Range(min=0, max=720)),
        O("heat_off"): vol.Any(None, NUM)},
    "set_temp_alarm": {R("garden"): cv.string, O("enabled"): cv.boolean,
        O("high"): vol.Any(None, NUM), O("low"): vol.Any(None, NUM)},
    "ack_temp_alarm": {R("garden"): cv.string, O("kind"): vol.In(["high", "low"])},
    "set_sensor_alarm": {R("garden"): cv.string, R("enabled"): cv.boolean},
    "ack_sensor_alarm": {R("garden"): cv.string, O("entity"): cv.string},
    "set_microclimate": {O("usda_zone"): vol.Any(None, cv.string), O("frost_f"): vol.All(NUM, vol.Range(min=20, max=40)),
        O("temp_entities"): vol.Any(None, cv.ensure_list), O("rain_entities"): vol.Any(None, cv.ensure_list),
        O("humidity_entities"): vol.Any(None, cv.ensure_list),
        O("solar_entities"): vol.Any(None, cv.ensure_list),
        O("air_entities"): vol.Any(None, {O(k): cv.ensure_list for k in ("pm1", "pm25", "pm10", "nox", "voc")})},
    "set_power_rate": {R("cents"): vol.All(NUM, vol.Range(min=0, max=1000))},
    "set_power_sensors": {R("garden"): cv.string, R("group"): vol.In(["heat", "cool", "power"]),
        R("entities"): vol.All(cv.ensure_list, [cv.string])},
    "up_pot": {R("plant"): cv.string, R("container"): cv.string, O("date"): cv.date},
    "move_plants": {R("plant"): cv.string, R("to"): cv.string, O("count"): POS_INT, O("date"): cv.date},
    "add_cover_crop": {R("garden"): cv.string, R("crop"): cv.string, O("sown_date"): cv.date,
        O("notes"): cv.string, O("wait_days"): vol.All(vol.Coerce(int), vol.Range(min=0, max=120)),
        O("amount_lbs"): NUM},
    "terminate_cover_crop": {R("garden"): cv.string, R("cover"): cv.string, O("date"): cv.date,
        O("method"): vol.In(COVER_METHODS), O("notes"): cv.string},
    "reopen_cover_crop": {R("garden"): cv.string, R("cover"): cv.string},
    "end_season": {R("garden"): cv.string, O("date"): cv.date, O("notes"): cv.string, O("cover_crop"): cv.string,
        O("wait_days"): vol.All(vol.Coerce(int), vol.Range(min=0, max=120))},
    "set_frost_dates": {O("garden"): cv.string, O("last_frost"): cv.string, O("first_frost"): cv.string,
        O("all_gardens"): cv.boolean},
    "reset_frost_dates": {R("garden"): cv.string},
    "archive_plant": {R("plant"): cv.string, O("reason"): vol.In(ARCHIVE_REASONS), O("date"): cv.date,
        O("notes"): cv.string, O("final_lbs"): NUM},
    "plant_again": {R("plant"): cv.string, O("planted_date"): cv.date, O("plants"): POS_INT, O("garden"): cv.string},
    "restore_plant": {R("plant"): cv.string},
    "remove_plant": {R("plant"): cv.string},
    "delete_entry": {R("kind"): vol.In(list(KINDS)), R("parent"): cv.string, R("entry_id"): cv.string},
    "undo_delete": {},
    "edit_entry": {R("kind"): vol.In(list(KINDS)), R("parent"): cv.string, R("entry_id"): cv.string,
        O("date"): cv.date, O("lbs"): NUM, O("notes"): cv.string, O("product"): cv.string,
        O("n"): NUM, O("p"): NUM, O("k"): NUM, O("target"): cv.string, O("phi_days"): DAYS,
        O("reapply_days"): DAYS, O("year"): cv.positive_int, O("type"): cv.string,
        O("amount"): cv.string, O("value"): NUM, O("sown"): cv.date, O("terminated"): cv.date,
        O("method"): vol.In(COVER_METHODS), O("crop"): cv.string, O("amount_lbs"): NUM,
        O("wait_days"): vol.All(vol.Coerce(int), vol.Range(min=0, max=120))},
    "add_species": {R("key"): cv.string, R("name"): cv.string, O("kind"): vol.In(["tree", "plant"]),
        O("pests"): list},
}


def async_register_services(hass: HomeAssistant) -> None:
    def make(handler):
        async def _call(call: ServiceCall) -> None:
            mgr = hass.data.get(DOMAIN)
            if mgr is None:
                raise ServiceValidationError("Garden Tracker is not set up")
            try:
                handler(mgr, dict(call.data))
            except GardenError as err:
                raise ServiceValidationError(str(err)) from err
        return _call

    for name, schema in SERVICES.items():
        hass.services.async_register(DOMAIN, name, make(HANDLERS[name]), vol.Schema(schema))
