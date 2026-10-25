"""What the app can do: every action the card asks for, as plain functions on the garden model.

The Home Assistant integration checks each call against a schema (services.py) before running these, and the
web app runs them directly. Keeping them here means a fix lands in both."""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, Callable

from .model import EDITABLE, UNSET, GardenError, GardenModel  # noqa: F401  (the handlers below use these)

Handler = Callable[[GardenModel, dict], Any]
HANDLERS: dict[str, Handler] = {
    "set_location": lambda m, c: m.set_location(c.get("lat"), c.get("lon"), c.get("name")),
    "add_garden": lambda m, c: m.add_garden(c["name"], c.get("ph_entity"), c.get("ph_min", 6.0), c.get("ph_max", 6.8),
        c.get("kind", "garden")),
    "update_garden": lambda m, c: m.update_garden(c["garden"], c.get("name"), c.get("ph_entity"),
        c.get("ph_min"), c.get("ph_max"), c.get("ec_min"), c.get("ec_max"),
        c.get("moisture_min"), c.get("moisture_max"),
        c.get("probe_depth")),
    "remove_garden": lambda m, c: m.remove_garden(c["garden"]),
    "add_adjunct_type": lambda m, c: m.add_adjunct_type(c["garden"], c["name"], c.get("per_year"), c.get("interval_days")),
    "remove_adjunct_type": lambda m, c: m.remove_adjunct_type(c["garden"], c["adjunct"]),
    "log_adjunct": lambda m, c: m.log_adjunct(c["garden"], c["adjunct"], c.get("date"), c.get("product"),
        c.get("amount"), c.get("notes")),
    "log_ph": lambda m, c: m.log_ph(c["garden"], c["value"], c.get("date")),
    "add_variety": lambda m, c: m.add_variety(c["garden"], c["species"], c["variety"], c.get("plants", 1),
        c.get("origin", "seed"), c.get("planted_date"), c.get("in_ground_date"),
        c.get("days_to_harvest"), c.get("expected_harvest_date"),
        c.get("expected_yield"), c.get("notes", ""), c.get("kind"),
        c.get("single_harvest"), c.get("multi_year"), c.get("container")),
    "update_variety": lambda m, c: m.update_variety(c["plant"], c.get("name"), c.get("garden"), c.get("planted_date"),
        c.get("in_ground_date"), c.get("days_to_harvest"),
        c.get("expected_harvest_date"), c.get("expected_yield"),
        c.get("notes"), c.get("add_plants"), c.get("single_harvest"), c.get("multi_year"),
        c.get("container")),
    "set_harvest": lambda m, c: m.set_harvest(c["plant"], c.get("expected_date"), c.get("expected_yield")),
    "log_stage": lambda m, c: m.log_stage(c["plant"], c["stage"], c.get("date")),
    "log_fertilizer": lambda m, c: m.log_fertilizer(c["plant"], c["product"], c.get("n"), c.get("p"), c.get("k"),
        c.get("date"), c.get("notes")),
    "log_spray": lambda m, c: m.log_spray(c["plant"], c["product"], c.get("date"), c.get("target"),
        c.get("phi_days"), c.get("reapply_days")),
    "set_biofix": lambda m, c: m.set_biofix(c["plant"], c["pest"], c.get("date")),
    "add_review": lambda m, c: m.add_review(c["plant"], c["notes"], c.get("year")),
    "log_harvest": lambda m, c: m.log_harvest(c["plant"], c["lbs"], c.get("date"), c.get("notes"), c.get("plants")),
    "set_plant_status": lambda m, c: m.set_plant_status(c["plant"], c["individual"], c["status"], c.get("reason"),
        c.get("note"), c.get("date")),
    "mark_plants_lost": lambda m, c: m.mark_plants_lost(c["plant"], c["count"], c["status"], c["reason"],
        c.get("note"), c.get("date")),
    "restore_plants": lambda m, c: m.restore_plants(c["plant"], c["count"], c.get("status"), c.get("reason"),
        c.get("date")),
    "set_garden_sensors": lambda m, c: m.set_sensors(c["garden"], c["metric"], c["entities"]),
    "set_soil_sensors_paused": lambda m, c: m.set_sensors_paused(c["garden"], c["paused"], c.get("group", "all")),
    "log_garden_reading": lambda m, c: m.log_metric(c["garden"], c["metric"], c["value"], c.get("date")),
    "set_layout": lambda m, c: m.set_layout(c["garden"], c.get("width_ft"), c.get("length_ft"), c.get("row_in"), c.get("rotation"), c.get("path_in")),
    "assign_layout_rows": lambda m, c: m.assign_layout_rows(c["garden"], c.get("crop"), c.get("rows"), c.get("variety")),
    "add_layout_segment": lambda m, c: m.add_layout_segment(c["garden"], c["row"], c["crop"], c["length_ft"], c.get("start_ft"), c.get("variety")),
    "remove_layout_segment": lambda m, c: m.remove_layout_segment(c["garden"], c["row"], c.get("index")),
    "set_layout_crop": lambda m, c: m.set_layout_crop(c["garden"], c["crop"], c.get("spacing_in"), c.get("support"), c.get("post_ft"), c.get("post_kind"), c.get("twine_levels"), c.get("pattern"), c.get("stagger"), c.get("yield_lb")),
    "set_layout_draft": lambda m, c: m.set_layout_draft(c["garden"], c.get("crop"), c.get("mode"), c.get("value"), c.get("yield_lb"), c.get("spacing_in"), c.get("variety")),
    "place_layout_draft": lambda m, c: m.place_layout_draft(c["garden"], c["row"], c.get("start_ft")),
    "start_layout_season": lambda m, c: m.start_layout_season(c["garden"], c.get("year")),
    "set_variety_traits": lambda m, c: m.set_variety_traits(c["crop"], c["variety"], c.get("resist")),
    "remove_variety_traits": lambda m, c: m.remove_variety_traits(c["crop"], c["variety"]),
    "set_irrigation": lambda m, c: m.set_irrigation(c["garden"], c.get("method"), c.get("soil"), c.get("per_week"), c.get("run_min", "keep"), c.get("max_line_gph")),
    "set_sprinkler": lambda m, c: m.set_sprinkler(c["garden"], c.get("mode"), c.get("pr_mode"), c.get("gpm"), c.get("radius_ft"), c.get("arc"), c.get("pr_in_hr", "keep"), c.get("heads", "keep"), c.get("per_week", "keep")),
    "set_irrigation_crop": lambda m, c: m.set_irrigation_crop(c["garden"], c["crop"], c.get("water_in_week"), c.get("lines"), c.get("flow_gph", "keep"), c.get("emit_in", "keep"), c.get("ppm_n")),
    "reset_irrigation_crop": lambda m, c: m.reset_irrigation_crop(c["garden"], c["crop"]),
    "set_acid": lambda m, c: m.set_acid(c["garden"], c.get("ph"), c.get("ta_ppm"), c.get("target_ph"), c.get("strength_pct"), c.get("sg", "keep"), c.get("base")),
    "set_lime": lambda m, c: m.set_lime(c["garden"], c.get("target_ph"), c.get("type"), c.get("depth_in"), c.get("tilled"), c.get("ph", "keep"), c.get("lb_per_unit", "keep")),
    "set_fertigation": lambda m, c: m.set_fertigation(c["garden"], c.get("every_days"), c.get("active")),
    "set_pump": lambda m, c: m.set_pump(c["garden"], c.get("pump"), c.get("name"), c.get("min_ratio"), c.get("max_ratio"), c.get("min_gpm"), c.get("max_gpm"), c.get("tank_gal"), c.get("flush_min")),
    "remove_pump": lambda m, c: m.remove_pump(c["garden"], c["pump"]),
    "set_tank_pump": lambda m, c: m.set_tank_pump(c["garden"], c["tank"], c["pump"]),
    "log_acid": lambda m, c: m.log_acid(c["garden"], c.get("date"), c.get("ml"), c.get("water_gal"), c.get("ph_before"), c.get("ph_after"), c.get("notes"), c.get("g"), c.get("product")),
    "set_fert_mix": lambda m, c: m.set_fert_mix(c["garden"], c.get("mix"), c.get("name"), c.get("ppm_n", "keep")),
    "remove_fert_mix": lambda m, c: m.remove_fert_mix(c["garden"], c["mix"]),
    "set_fert_component": lambda m, c: m.set_fert_component(c["garden"], c["mix"], c.get("index"), c.get("name"), c.get("n"), c.get("p"), c.get("k"), c.get("ca"), c.get("mg"), c.get("parts"), c.get("tank")),
    "remove_fert_component": lambda m, c: m.remove_fert_component(c["garden"], c["mix"], c["index"]),
    "remove_layout": lambda m, c: m.remove_layout(c["garden"]),
    "set_trays": lambda m, c: m.set_trays(c["garden"], c["trays"]),
    "log_watering": lambda m, c: m.log_watering(c["garden"], c.get("date"), c.get("notes")),
    "set_water_interval": lambda m, c: m.set_water_interval(c["garden"], c.get("days")),
    "set_greenhouse_climate": lambda m, c: m.set_climate(c["garden"], c.get("enabled"), c.get("heat_set"),
        c.get("cool_set"), c.get("heaters"), c.get("coolers"),
        c.get("heat_min_run"), c.get("heat_max_run"),
        c.get("heat_rest"), c.get("lights"), c.get("light_sched"),
        c.get("light_on"), c.get("light_hours"), c.get("fan_sched"),
        c.get("fan_minutes"), c.get("fan_every"),
        c.get("fan_lights_only"), c.get("cool_off", UNSET),
        c.get("fan_min_run"), c.get("heat_off", UNSET)),
    "set_temp_alarm": lambda m, c: m.set_temp_alarm(c["garden"], c.get("enabled"), c.get("high", UNSET),
        c.get("low", UNSET)),
    "ack_temp_alarm": lambda m, c: m.ack_temp_alarm(c["garden"], c.get("kind")),
    "set_sensor_alarm": lambda m, c: m.set_sensor_alarm(c["garden"], c["enabled"]),
    "ack_sensor_alarm": lambda m, c: m.ack_sensor_alarm(c["garden"], c.get("entity")),
    "set_microclimate": lambda m, c: m.set_microclimate(c.get("usda_zone", UNSET), c.get("frost_f"),
        c.get("temp_entities", UNSET), c.get("rain_entities", UNSET),
        c.get("humidity_entities", UNSET), c.get("solar_entities", UNSET),
        c.get("air_entities", UNSET)),
    "set_power_rate": lambda m, c: m.set_power_rate(c["cents"]),
    "set_power_sensors": lambda m, c: m.set_power_sensors(c["garden"], c["group"], c["entities"]),
    "up_pot": lambda m, c: m.up_pot(c["plant"], c["container"], c.get("date")),
    "move_plants": lambda m, c: m.move_plants(c["plant"], c["to"], c.get("count"), c.get("date")),
    "add_cover_crop": lambda m, c: m.add_cover_crop(c["garden"], c["crop"], c.get("sown_date"), c.get("notes"),
        c.get("wait_days"), c.get("amount_lbs")),
    "terminate_cover_crop": lambda m, c: m.terminate_cover_crop(c["garden"], c["cover"], c.get("date"),
        c.get("method"), c.get("notes")),
    "reopen_cover_crop": lambda m, c: m.reopen_cover_crop(c["garden"], c["cover"]),
    "end_season": lambda m, c: m.end_season(c["garden"], c.get("date"), c.get("notes"), c.get("cover_crop"),
        c.get("wait_days")),
    "set_frost_dates": lambda m, c: m.set_frost_dates(c.get("garden"), c.get("last_frost"), c.get("first_frost"),
        c.get("all_gardens", False)),
    "reset_frost_dates": lambda m, c: m.reset_frost_dates(c["garden"]),
    "archive_plant": lambda m, c: m.archive_variety(c["plant"], c.get("reason", "season_over"), c.get("date"),
        c.get("notes"), c.get("final_lbs")),
    "plant_again": lambda m, c: m.plant_again(c["plant"], c.get("planted_date"), c.get("plants"), c.get("garden")),
    "restore_plant": lambda m, c: m.restore_variety(c["plant"]),
    "remove_plant": lambda m, c: m.remove_variety(c["plant"]),
    "delete_entry": lambda m, c: m.delete_entry(c["kind"], c["parent"], c["entry_id"]),
    "undo_delete": lambda m, c: m.undo_delete(),
    "edit_entry": lambda m, c: m.edit_entry(c["kind"], c["parent"], c["entry_id"],
        {k: v for k, v in c.items() if k in EDITABLE[c["kind"]]}),
    "add_species": lambda m, c: m.add_species(c["key"], c["name"], c.get("kind", "tree"), c.get("pests", [])),
}


class GardenApp:
    """The whole app on its own, for places without Home Assistant: the model, its actions, saving and loading.

    Everything crosses in and out as JSON text so a web page can talk to it."""

    WEATHER_SOURCE = "weather-service"

    def __init__(self, species_text: str, stored_json: str | None = None, today_iso: str | None = None) -> None:
        self.today_iso = today_iso or date.today().isoformat()
        self.model = GardenModel({}, lambda: date.fromisoformat(self.today_iso))
        self.model.presets = {k: v for k, v in json.loads(species_text).items() if not k.startswith("_")}
        self.model.load(json.loads(stored_json) if stored_json else None)
        st = self.model.data["settings"]
        if self.WEATHER_SOURCE not in st["rain_entities"]:  # rain from the weather service counts like a rain sensor
            st["rain_entities"] = [*st["rain_entities"], self.WEATHER_SOURCE]

    def set_today(self, today_iso: str) -> None:
        self.today_iso = today_iso
        self.model._touch()

    def call(self, service: str, data_json: str = "{}") -> str:
        try:
            handler = HANDLERS.get(service)
            if handler is None:
                raise GardenError(f"Unknown action '{service}'")
            handler(self.model, json.loads(data_json or "{}"))
            return json.dumps({"ok": True})
        except GardenError as err:
            return json.dumps({"ok": False, "error": str(err)})

    def snapshot(self) -> str:
        return json.dumps(self.model.snapshot(), default=str)

    def data(self) -> str:
        """Everything that is saved, as one piece of JSON text. The same text restores it."""
        return json.dumps(self.model.data, default=str)

    def merge_weather(self, weather_json: str) -> str:
        """Add days of weather: {"daily": {date: [low F, high F]}, "rain": {date: inches}}."""
        w = json.loads(weather_json)
        daily = {k: (float(v[0]), float(v[1])) for k, v in (w.get("daily") or {}).items()
                 if v and v[0] is not None and v[1] is not None}
        rain = {k: float(v) for k, v in (w.get("rain") or {}).items() if v}
        changed = bool(daily and self.model.merge_daily(daily))
        changed = bool(rain and self.model.merge_rain(self.WEATHER_SOURCE, rain)) or changed
        return json.dumps({"changed": changed, "days": len(daily)})
