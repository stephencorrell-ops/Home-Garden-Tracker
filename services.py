"""Services. The Lovelace card uses these too, so automations can do everything the card can."""
from __future__ import annotations

from typing import Any, Callable

import voluptuous as vol
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .const import DOMAIN
from .manager import GardenManager
from .model import ARCHIVE_REASONS, EDITABLE, KINDS, REASONS, GardenError

R, O = vol.Required, vol.Optional
NUM = vol.Coerce(float)
INT = vol.Coerce(int)
POS_INT = vol.All(vol.Coerce(int), vol.Range(min=1, max=1000))
DAYS = vol.All(vol.Coerce(int), vol.Range(min=0, max=3650))

Handler = Callable[[GardenManager, dict], Any]
SERVICES: dict[str, tuple[dict, Handler]] = {
    "add_garden": ({R("name"): cv.string, O("ph_entity"): cv.string, O("ph_min"): NUM, O("ph_max"): NUM},
                   lambda m, c: m.add_garden(c["name"], c.get("ph_entity"), c.get("ph_min", 6.0), c.get("ph_max", 6.8))),
    "update_garden": ({R("garden"): cv.string, O("name"): cv.string, O("ph_entity"): cv.string,
                       O("ph_min"): NUM, O("ph_max"): NUM},
                      lambda m, c: m.update_garden(c["garden"], c.get("name"), c.get("ph_entity"),
                                                   c.get("ph_min"), c.get("ph_max"))),
    "remove_garden": ({R("garden"): cv.string}, lambda m, c: m.remove_garden(c["garden"])),
    "add_adjunct_type": ({R("garden"): cv.string, R("name"): cv.string, O("per_year"): POS_INT,
                          O("interval_days"): POS_INT},
                         lambda m, c: m.add_adjunct_type(c["garden"], c["name"], c.get("per_year"), c.get("interval_days"))),
    "remove_adjunct_type": ({R("garden"): cv.string, R("adjunct"): cv.string},
                            lambda m, c: m.remove_adjunct_type(c["garden"], c["adjunct"])),
    "log_adjunct": ({R("garden"): cv.string, R("adjunct"): cv.string, O("date"): cv.date,
                     O("product"): cv.string, O("amount"): cv.string, O("notes"): cv.string},
                    lambda m, c: m.log_adjunct(c["garden"], c["adjunct"], c.get("date"), c.get("product"),
                                               c.get("amount"), c.get("notes"))),
    "log_ph": ({R("garden"): cv.string, R("value"): NUM, O("date"): cv.date},
               lambda m, c: m.log_ph(c["garden"], c["value"], c.get("date"))),
    "add_variety": ({R("garden"): cv.string, R("species"): cv.string, R("variety"): cv.string,
                     O("plants"): POS_INT, O("origin"): vol.In(["seed", "start"]),
                     O("planted_date"): cv.date, O("in_ground_date"): cv.date, O("days_to_harvest"): DAYS,
                     O("expected_harvest_date"): cv.date, O("expected_yield"): NUM, O("notes"): cv.string,
                     O("kind"): vol.In(["plant", "tree"])},
                    lambda m, c: m.add_variety(c["garden"], c["species"], c["variety"], c.get("plants", 1),
                                               c.get("origin", "seed"), c.get("planted_date"), c.get("in_ground_date"),
                                               c.get("days_to_harvest"), c.get("expected_harvest_date"),
                                               c.get("expected_yield"), c.get("notes", ""), c.get("kind"))),
    "update_variety": ({R("plant"): cv.string, O("name"): cv.string, O("garden"): cv.string,
                        O("planted_date"): cv.date, O("in_ground_date"): cv.date, O("days_to_harvest"): DAYS,
                        O("expected_harvest_date"): cv.date, O("expected_yield"): NUM, O("notes"): cv.string,
                        O("add_plants"): POS_INT},
                       lambda m, c: m.update_variety(c["plant"], c.get("name"), c.get("garden"), c.get("planted_date"),
                                                     c.get("in_ground_date"), c.get("days_to_harvest"),
                                                     c.get("expected_harvest_date"), c.get("expected_yield"),
                                                     c.get("notes"), c.get("add_plants"))),
    "set_harvest": ({R("plant"): cv.string, O("expected_date"): cv.date, O("expected_yield"): NUM},
                    lambda m, c: m.set_harvest(c["plant"], c.get("expected_date"), c.get("expected_yield"))),
    "log_stage": ({R("plant"): cv.string, R("stage"): vol.In(["planted", "upotted", "in_ground"]), O("date"): cv.date},
                  lambda m, c: m.log_stage(c["plant"], c["stage"], c.get("date"))),
    "log_fertilizer": ({R("plant"): cv.string, R("product"): cv.string, O("n"): NUM, O("p"): NUM, O("k"): NUM,
                        O("date"): cv.date, O("notes"): cv.string},
                       lambda m, c: m.log_fertilizer(c["plant"], c["product"], c.get("n"), c.get("p"), c.get("k"),
                                                     c.get("date"), c.get("notes"))),
    "log_spray": ({R("plant"): cv.string, R("product"): cv.string, O("date"): cv.date, O("target"): cv.string,
                   O("phi_days"): DAYS, O("reapply_days"): DAYS},
                  lambda m, c: m.log_spray(c["plant"], c["product"], c.get("date"), c.get("target"),
                                           c.get("phi_days"), c.get("reapply_days"))),
    "set_biofix": ({R("plant"): cv.string, R("pest"): cv.string, O("date"): cv.date},
                   lambda m, c: m.set_biofix(c["plant"], c["pest"], c.get("date"))),
    "add_review": ({R("plant"): cv.string, R("notes"): cv.string, O("year"): cv.positive_int},
                   lambda m, c: m.add_review(c["plant"], c["notes"], c.get("year"))),
    "log_harvest": ({R("plant"): cv.string, R("lbs"): NUM, O("date"): cv.date, O("notes"): cv.string},
                    lambda m, c: m.log_harvest(c["plant"], c["lbs"], c.get("date"), c.get("notes"))),
    "set_plant_status": ({R("plant"): cv.string, R("individual"): cv.string,
                          R("status"): vol.In(["alive", "dead", "pulled"]), O("reason"): vol.In(REASONS),
                          O("note"): cv.string, O("date"): cv.date},
                         lambda m, c: m.set_plant_status(c["plant"], c["individual"], c["status"], c.get("reason"),
                                                         c.get("note"), c.get("date"))),
    "archive_plant": ({R("plant"): cv.string, O("reason"): vol.In(ARCHIVE_REASONS), O("date"): cv.date,
                       O("notes"): cv.string, O("final_lbs"): NUM},
                      lambda m, c: m.archive_variety(c["plant"], c.get("reason", "season_over"), c.get("date"),
                                                     c.get("notes"), c.get("final_lbs"))),
    "plant_again": ({R("plant"): cv.string, O("planted_date"): cv.date, O("plants"): POS_INT, O("garden"): cv.string},
                    lambda m, c: m.plant_again(c["plant"], c.get("planted_date"), c.get("plants"), c.get("garden"))),
    "restore_plant": ({R("plant"): cv.string}, lambda m, c: m.restore_variety(c["plant"])),
    "remove_plant": ({R("plant"): cv.string}, lambda m, c: m.remove_variety(c["plant"])),
    "delete_entry": ({R("kind"): vol.In(list(KINDS)), R("parent"): cv.string, R("entry_id"): cv.string},
                     lambda m, c: m.delete_entry(c["kind"], c["parent"], c["entry_id"])),
    "undo_delete": ({}, lambda m, c: m.undo_delete()),
    "edit_entry": ({R("kind"): vol.In(list(KINDS)), R("parent"): cv.string, R("entry_id"): cv.string,
                    O("date"): cv.date, O("lbs"): NUM, O("notes"): cv.string, O("product"): cv.string,
                    O("n"): NUM, O("p"): NUM, O("k"): NUM, O("target"): cv.string, O("phi_days"): DAYS,
                    O("reapply_days"): DAYS, O("year"): cv.positive_int, O("type"): cv.string,
                    O("amount"): cv.string, O("value"): NUM},
                   lambda m, c: m.edit_entry(c["kind"], c["parent"], c["entry_id"],
                                             {k: v for k, v in c.items() if k in EDITABLE[c["kind"]]})),
    "add_species": ({R("key"): cv.string, R("name"): cv.string, O("kind"): vol.In(["tree", "plant"]),
                     O("pests"): list},
                    lambda m, c: m.add_species(c["key"], c["name"], c.get("kind", "tree"), c.get("pests", []))),
}


def async_register_services(hass: HomeAssistant) -> None:
    def make(handler: Handler):
        async def _call(call: ServiceCall) -> None:
            mgr = hass.data.get(DOMAIN)
            if mgr is None:
                raise ServiceValidationError("Garden Tracker is not set up")
            try:
                handler(mgr, dict(call.data))
            except GardenError as err:
                raise ServiceValidationError(str(err)) from err
        return _call

    for name, (schema, handler) in SERVICES.items():
        hass.services.async_register(DOMAIN, name, make(handler), vol.Schema(schema))
