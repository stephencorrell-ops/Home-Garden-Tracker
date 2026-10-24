import json
from datetime import date, timedelta
from pathlib import Path

import unittest

from . import _load  # noqa: F401  (makes the core importable without Home Assistant)
from custom_components.garden_tracker.core.api import GardenApp
from custom_components.garden_tracker.core import calc, microclimate as mc
from custom_components.garden_tracker.core.model import GardenError, GardenModel

TODAY = date(2026, 10, 24)
SPECIES = Path(mc.__file__).parent / "species.json"


def make(today=TODAY) -> GardenModel:
    m = GardenModel({}, lambda: today, lambda: None, lambda: None)
    m.presets = {k: v for k, v in json.loads(SPECIES.read_text("utf-8")).items() if not k.startswith("_")}
    m.load(None)
    return m


def winter(daily, year, low):
    """A winter of daily lows and highs: every day of Dec to Feb, with one cold night at `low`."""
    d = date(year, 12, 1)
    while d <= date(year + 1, 2, 28):
        daily[d.isoformat()] = [20.0, 38.0]
        d += timedelta(days=1)
    daily[date(year + 1, 1, 15).isoformat()] = [low, 30.0]


class Microclimate(unittest.TestCase):
    def test_zone_from_lowest_temperature(self):
        for low, zone in [(-7, "6a"), (-3, "6b"), (2, "7a"), (7, "7b"), (12, "8a")]:
            self.assertEqual(mc.zone_from_min(low), zone, low)

    def test_frost_years_find_last_spring_and_first_fall(self):
        daily = {"2025-03-27": [28, 50], "2025-04-10": [31, 60], "2025-05-02": [40, 70], "2025-10-30": [30, 55],
                 "2025-11-20": [20, 40], "2025-09-01": [50, 80]}
        y = mc.frost_years(daily, TODAY)[0]
        self.assertEqual((y["last_spring"], y["first_fall"], y["lowest"]), ("2025-04-10", "2025-10-30", 20.0))

    def test_local_zone_needs_complete_winters_and_averages_them(self):
        daily = {}
        winter(daily, 2024, 4.0)
        winter(daily, 2025, 8.0)
        z = mc.local_zone(daily, TODAY)
        self.assertEqual((z["count"], z["avg_min"], z["zone"]), (2, 6.0, "7b"))
        self.assertIsNone(mc.local_zone({}, TODAY)["zone"])
        self.assertIsNone(mc.local_zone({"2026-10-20": [30.0, 60.0]}, TODAY)["zone"])

    def test_expected_soil_is_the_recent_air_average(self):
        daily = {(TODAY - timedelta(days=i)).isoformat(): [40.0, 60.0] for i in range(10)}
        self.assertEqual(mc.expected_soil(daily, TODAY), 50.0)
        self.assertIsNone(mc.expected_soil({TODAY.isoformat(): [40, 60]}, TODAY))

    def test_solar_average_uses_the_time_measured(self):
        solar = {TODAY.isoformat(): [600, 1800, 3600]}  # 1800 Wh over one measured hour
        self.assertEqual(mc.solar_total(solar, TODAY, TODAY)["avg"], 1800)
        self.assertIsNone(mc.solar_total({}, TODAY, TODAY)["avg"])


class Model(unittest.TestCase):
    def test_rain_is_the_average_of_the_sensors(self):
        m = make()
        m.set_microclimate(rain_entities=["sensor.a", "sensor.b"])
        m.add_rain("sensor.a", 0.4)
        m.add_rain("sensor.b", 0.2)
        self.assertAlmostEqual(m.data["rain"][TODAY.isoformat()], 0.3)
        m.set_microclimate(rain_entities=["sensor.a"])
        self.assertAlmostEqual(m.data["rain"][TODAY.isoformat()], 0.4)

    def test_history_fills_in_without_overwriting_live_readings(self):
        m = make()
        m.record_temp_f(50)
        m.merge_daily({TODAY.isoformat(): (40.0, 45.0), "2026-10-01": (35.0, 55.0)})
        self.assertEqual(m.data["daily"][TODAY.isoformat()], [40.0, 50])
        self.assertEqual(m.data["daily"]["2026-10-01"], [35.0, 55.0])

    def test_frost_threshold_is_checked(self):
        with self.assertRaises(GardenError):
            make().set_microclimate(frost_f=50)

    def test_air_quality_keeps_the_average_and_the_highest(self):
        t = [1_792_850_000.0]
        m = make()
        m.now_fn = lambda: t[0]
        for v in (10, 30, 20):
            m.record_air("pm25", v)
            t[0] += 60
        a = m.snapshot()["micro"]["air"]["metrics"]["pm25"]
        self.assertEqual((a["current"], a["max"]["today"]), (20, 30))
        m.record_air("nope", 1)  # an unknown kind is ignored

    def test_snapshot_is_json_and_holds_the_garden(self):
        m = make()
        gid = m.add_garden("Big")
        snap = m.snapshot()
        json.dumps(snap)
        self.assertEqual([g["id"] for g in snap["gardens"]], [gid])

    def test_species_presets_load(self):
        self.assertTrue(make().presets)


class App(unittest.TestCase):
    """The pieces the web app uses: actions as JSON, saving, restoring and weather."""

    def app(self, stored=None):
        return GardenApp(SPECIES.read_text("utf-8"), stored, TODAY.isoformat())

    def test_actions_report_errors_instead_of_raising(self):
        a = self.app()
        self.assertEqual(json.loads(a.call("add_garden", json.dumps({"name": "Back yard"}))), {"ok": True})
        self.assertFalse(json.loads(a.call("add_garden", json.dumps({"name": " "})))["ok"])
        self.assertFalse(json.loads(a.call("no_such_action"))["ok"])

    def test_saved_data_restores_into_a_new_app(self):
        a = self.app()
        a.call("add_garden", json.dumps({"name": "Back yard"}))
        a.call("set_location", json.dumps({"lat": 47.3, "lon": -119.5, "name": "Ephrata"}))
        b = self.app(a.data())
        snap = json.loads(b.snapshot())
        self.assertEqual([g["name"] for g in snap["gardens"]], ["Back yard"])
        self.assertEqual(snap["micro"]["settings"]["location"]["name"], "Ephrata")

    def test_weather_fills_in_history_and_counts_as_rain(self):
        a = self.app()
        w = {"daily": {"2026-10-20": [30, 55]}, "rain": {"2026-10-20": 0.3}}
        self.assertTrue(json.loads(a.merge_weather(json.dumps(w)))["changed"])
        self.assertFalse(json.loads(a.merge_weather(json.dumps(w)))["changed"])  # the same days again change nothing
        snap = json.loads(a.snapshot())
        self.assertEqual(snap["micro"]["rain"]["month"], 0.3)
        self.assertEqual(snap["micro"]["temps"]["month"]["low"], 30)

    def test_bad_location_is_refused(self):
        self.assertFalse(json.loads(self.app().call("set_location", json.dumps({"lat": 99, "lon": 0})))["ok"])


if __name__ == "__main__":
    unittest.main()
