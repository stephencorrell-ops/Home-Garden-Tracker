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


class Layout(unittest.TestCase):
    def garden(self):
        m = make()
        gid = m.add_garden("Back yard")
        return m, gid

    def view(self, m, gid):
        return next(g for g in m.snapshot()["gardens"] if g["id"] == gid)["layout"]

    def seg(self, m, gid, row=0, k=0):
        return self.view(m, gid)["rows"][row]["segments"][k]

    def test_single_line_tomatoes_with_t_posts(self):
        m, gid = self.garden()
        self.assertFalse(self.view(m, gid)["configured"])
        m.set_layout(gid, 20, 40, 30, None, 0)  # no paths
        m.assign_layout_rows(gid, "tomato")
        v = self.view(m, gid)
        self.assertEqual(v["totals"]["rows"], 8)  # 240 in across at 30 in a row
        self.assertEqual(len(self.seg(m, gid)["lines"]), 1)
        self.assertEqual(v["rows"][0]["plants"], 20)  # 480 in long at 24 in
        self.assertEqual(v["totals"]["plants"], 160)
        self.assertEqual(v["totals"]["posts"], 8 * 11)  # a post every 4 ft plus the end one: 40 / 4 + 1
        self.assertEqual(v["totals"]["density"], 0.2)

    def test_double_line_doubles_the_plants_and_can_be_staggered(self):
        m, gid = self.garden()
        m.set_layout(gid, 6, 10, 36)
        m.assign_layout_rows(gid, "tomato")
        one = self.view(m, gid)["totals"]["plants"]
        m.set_layout_crop(gid, "tomato", None, None, None, None, None, "double", False)
        sg = self.seg(m, gid)
        self.assertEqual(len(sg["lines"]), 2)
        self.assertEqual(sg["ys2"], [])
        self.assertEqual(self.view(m, gid)["totals"]["plants"], one * 2)
        m.set_layout_crop(gid, "tomato", None, None, None, None, None, None, True)
        sg = self.seg(m, gid)
        self.assertEqual(round(sg["ys2"][0] - sg["ys"][0], 2), 12)  # half of 24 in
        self.assertLessEqual(sg["ys2"][-1], 120)

    def test_an_offset_grid_keeps_every_plant_the_spacing_from_its_neighbours(self):
        m, gid = self.garden()
        m.set_layout(gid, 5, 5, 30)  # one 30 in row, 5 ft long
        m.add_layout_segment(gid, 0, "garlic", 5)
        m.set_layout_crop(gid, "garlic", 7, None, None, None, None, "grid")
        sg = self.seg(m, gid)
        self.assertEqual(len(sg["lines"]), 5)  # lines sit 7 x 0.866 = 6.06 in apart
        self.assertAlmostEqual(sg["lines"][1] - sg["lines"][0], 6.062, places=2)
        self.assertEqual(sg["per_line"], 8)
        self.assertEqual(sg["plants"], 40)
        self.assertEqual(round(sg["ys2"][0] - sg["ys"][0], 2), 3.5)  # every other line is half a step along
        a, b = (sg["lines"][0], sg["ys"][0]), (sg["lines"][1], sg["ys2"][0])
        self.assertAlmostEqual(((a[0] - b[0]) ** 2 + (a[1] - b[1]) ** 2) ** 0.5, 7, places=1)

    def test_pepper_corral_counts_posts_and_twine(self):
        m, gid = self.garden()
        m.set_layout(gid, 6, 12, 36)
        m.assign_layout_rows(gid, "pepper")
        r = self.view(m, gid)["rows"][0]
        self.assertEqual(r["stakes"], 2 * (12 // 3 + 1))  # both sides, every 3 ft plus the end
        self.assertEqual(r["twine_ft"], 2 * (2 * 12 + 2 * 1))  # 2 lines of twine, two sides and two ends
        m.set_layout_crop(gid, "pepper", None, None, 4, "tpost", 3)
        r = self.view(m, gid)["rows"][0]
        self.assertEqual((r["posts"], r["stakes"]), (2 * (12 // 4 + 1), 0))
        self.assertEqual(r["twine_ft"], 3 * 26)

    def test_cages_follow_plants(self):
        m, gid = self.garden()
        m.set_layout(gid, 6, 10, 36, None, 0)
        m.assign_layout_rows(gid, "pepper")
        m.set_layout_crop(gid, "pepper", None, "cage", None, None, None, "double")
        v = self.view(m, gid)
        self.assertEqual(v["totals"]["plants"], 2 * 2 * 6)  # 2 rows, 2 lines, 120 in / 18 in = 6
        self.assertEqual(v["totals"]["cages"], v["totals"]["plants"])

    def test_one_row_can_hold_several_crops_in_sections(self):
        m, gid = self.garden()
        m.set_layout(gid, 5, 25, 30, None, 0)  # two rows, 25 ft long
        m.add_layout_segment(gid, 0, "onion", 5)
        m.add_layout_segment(gid, 0, "carrot", 10)
        m.add_layout_segment(gid, 0, "bean", 10)
        v = self.view(m, gid)
        segs = v["rows"][0]["segments"]
        self.assertEqual([x["crop"] for x in segs], ["onion", "carrot", "bean"])
        self.assertEqual([x["start_in"] for x in segs], [0, 60, 180])
        self.assertTrue(all(x["grid"] for x in segs))
        self.assertIsNone(v["rows"][0]["crop"])  # no single crop owns the row
        self.assertEqual(v["rows"][0]["used_ft"], 25)
        self.assertEqual(next(c for c in v["crops"] if c["key"] == "carrot")["feet"], 10)
        with self.assertRaises(GardenError):
            m.add_layout_segment(gid, 0, "lettuce", 1)  # the row is full
        m.remove_layout_segment(gid, 0, 1)  # take out the carrots, the beans stay where they are
        segs = self.view(m, gid)["rows"][0]["segments"]
        self.assertEqual([(x["crop"], x["start_in"]) for x in segs], [("onion", 0), ("bean", 180)])
        m.add_layout_segment(gid, 0, "lettuce", 10, 5)  # the gap is 5 to 15 ft
        with self.assertRaises(GardenError):
            m.add_layout_segment(gid, 0, "lettuce", 1, 4.5)  # overlaps the onions
        m.remove_layout_segment(gid, 0)  # no index takes the last one
        m.remove_layout_segment(gid, 0)
        m.remove_layout_segment(gid, 0)
        self.assertEqual(self.view(m, gid)["rows"][0]["segments"], [])

    def test_one_row_can_hold_a_different_crop_and_be_cleared(self):
        m, gid = self.garden()
        m.set_layout(gid, 10, 10, 24, None, 0)
        m.assign_layout_rows(gid, "tomato")
        m.assign_layout_rows(gid, "carrot", [1])
        v = self.view(m, gid)
        self.assertEqual({c["key"] for c in v["crops"]}, {"tomato", "carrot"})
        m.assign_layout_rows(gid, None, [1])
        self.assertEqual({c["key"] for c in self.view(m, gid)["crops"]}, {"tomato"})

    def test_a_whole_row_can_be_trimmed_by_removing_its_section(self):
        m, gid = self.garden()
        m.set_layout(gid, 5, 20, 30, None, 0)
        m.assign_layout_rows(gid, "tomato", [0])
        self.assertEqual(self.view(m, gid)["rows"][0]["crop"], "tomato")
        m.remove_layout_segment(gid, 0, 0)
        self.assertIsNone(self.view(m, gid)["rows"][0]["crop"])

    def test_paths_sit_between_the_rows_and_the_rows_are_centred(self):
        m, gid = self.garden()
        m.set_layout(gid, 20, 10, 30)  # 240 in: rows of 30 with 24 in paths take 54 in each
        v = self.view(m, gid)
        self.assertEqual(v["path_in"], 24)
        self.assertEqual(v["totals"]["rows"], 4)  # 4 rows + 3 paths = 192 in
        self.assertEqual(round(v["rows"][1]["x0"] - v["rows"][0]["x0"], 1), 54)
        self.assertEqual(round(v["rows"][0]["x0"], 1), 24)  # centred: 48 in spare, half each side
        m.set_layout(gid, None, None, None, None, 36)
        self.assertEqual(self.view(m, gid)["path_in"], 36)
        m.set_layout(gid, None, None, None, None, 0)
        self.assertEqual(self.view(m, gid)["totals"]["rows"], 8)

    def test_planning_garlic_from_a_harvest_target(self):
        m, gid = self.garden()
        m.set_layout(gid, 10, 20, 30, None, 24)
        m.set_layout_draft(gid, "garlic", "weight", 20)
        d = self.view(m, gid)["draft"]
        self.assertEqual(d["need"], "yield")  # it has to know the weight of each plant
        m.set_layout_draft(gid, None, None, None, 0.25, 7)  # a quarter pound a head, 7 in apart
        d = self.view(m, gid)["draft"]
        self.assertEqual(d["plants_needed"], 80)
        self.assertEqual(d["length_ft"], 10)  # 5 lines x 8.57 plants a foot
        self.assertGreaterEqual(d["plants"], 80)
        self.assertEqual(d["est_lb"], round(d["plants"] * 0.25, 1))
        m.set_layout_draft(gid, None, "plants", 40)
        self.assertEqual(self.view(m, gid)["draft"]["length_ft"], 5)
        m.set_layout_draft(gid, None, "length", 4)
        self.assertEqual(self.view(m, gid)["draft"]["plants"], 30)  # 5 lines x 6

    def test_a_planned_crop_goes_where_you_pick_and_carries_into_the_next_row(self):
        m, gid = self.garden()
        m.set_layout(gid, 10, 20, 30, None, 24)  # two rows, 20 ft long
        m.set_layout_draft(gid, "garlic", "length", 25)
        m.place_layout_draft(gid, 0, 5)  # 15 ft left in row 1, then 10 ft in row 2
        rows = self.view(m, gid)["rows"]
        self.assertEqual([(s["crop"], s["start_in"], s["len_in"]) for s in rows[0]["segments"]], [("garlic", 60, 180)])
        self.assertEqual([(s["crop"], s["start_in"], s["len_in"]) for s in rows[1]["segments"]], [("garlic", 0, 120)])
        m.set_layout_draft(gid, "tomato", "length", 30)
        with self.assertRaises(GardenError):
            m.place_layout_draft(gid, 1, 0)  # no room, and nothing is half placed
        self.assertEqual(len(self.view(m, gid)["rows"][1]["segments"]), 1)

    def test_last_seasons_layout_is_kept_and_same_ground_is_flagged(self):
        m, gid = self.garden()
        m.set_layout(gid, 10, 20, 30, None, 24)
        m.assign_layout_rows(gid, "tomato", [0])
        m.assign_layout_rows(gid, "garlic", [1])
        year = self.view(m, gid)["year"]
        m.start_layout_season(gid)
        v = self.view(m, gid)
        self.assertEqual(v["year"], year + 1)
        self.assertEqual(v["totals"]["planted_rows"], 0)
        g = next(x for x in m.snapshot()["gardens"] if x["id"] == gid)
        self.assertEqual(g["layout_history"][str(year)]["totals"]["planted_rows"], 2)  # last year can be looked up
        m.assign_layout_rows(gid, "tomato", [0])  # the same crop in the same row
        m.assign_layout_rows(gid, "pepper", [1])  # not a rotation problem for garlic, but...
        v = self.view(m, gid)
        by_row = {(a["row"], a["crop"]): a for a in v["alerts"]}
        self.assertEqual(by_row[(0, "tomato")]["level"], "same")
        self.assertNotIn((1, "pepper"), by_row)  # garlic and pepper are different families
        m.assign_layout_rows(gid, "pepper", [0])  # pepper after tomato: the same nightshade family
        self.assertEqual({(a["row"], a["level"]) for a in self.view(m, gid)["alerts"]}, {(0, "family")})
        self.assertIn("Keep it off this spot until", self.view(m, gid)["alerts"][0]["text"])
        # the planner flags the rows too, before anything is placed
        m.set_layout_draft(gid, "pepper", "length", 5)
        flags = self.view(m, gid)["draft"]["flags"]
        self.assertEqual([f and f["level"] for f in flags], ["family", None])
        # a rest of three years clears it
        m.start_layout_season(gid)
        m.start_layout_season(gid)
        m.start_layout_season(gid)
        m.assign_layout_rows(gid, "tomato", [0])
        self.assertEqual([a for a in self.view(m, gid)["alerts"] if a["year"] == year], [])

    def test_the_garden_can_be_turned_in_90_degree_steps(self):
        m, gid = self.garden()
        m.set_layout(gid, 20, 40, 30, 90)
        self.assertEqual(self.view(m, gid)["rotation"], 90)
        m.set_layout(gid, None, None, None, 450)
        self.assertEqual(self.view(m, gid)["rotation"], 90)
        with self.assertRaises(GardenError):
            m.set_layout(gid, None, None, None, 45)

    def test_bad_input_is_refused(self):
        m, gid = self.garden()
        with self.assertRaises(GardenError):
            m.set_layout(gid, 20, 40, 28)
        with self.assertRaises(GardenError):
            m.set_layout(gid, 0, 40, 30)
        m.set_layout(gid, 20, 40, 30)
        with self.assertRaises(GardenError):
            m.assign_layout_rows(gid, "apple")  # a tree
        with self.assertRaises(GardenError):
            m.assign_layout_rows(gid, "tomato", [99])
        with self.assertRaises(GardenError):
            m.set_layout_crop(gid, "tomato", 0)
        with self.assertRaises(GardenError):
            m.set_layout_crop(gid, "tomato", None, None, None, None, None, "diagonal")

    def test_layout_survives_saving_and_is_json(self):
        a = App.app(self)
        a.call("add_garden", json.dumps({"name": "Back yard"}))
        gid = json.loads(a.snapshot())["gardens"][0]["id"]
        for svc, args in (("set_layout", {"width_ft": 8, "length_ft": 8, "row_in": 24, "path_in": 0}), ("assign_layout_rows", {"crop": "tomato"})):
            self.assertTrue(json.loads(a.call(svc, json.dumps({"garden": gid, **args})))["ok"])
        b = App.app(self, a.data())
        self.assertEqual(json.loads(b.snapshot())["gardens"][0]["layout"]["totals"]["plants"], 4 * 4)
