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

    def test_weather_estimates_temperatures_and_manual_readings_win(self):
        a = self.app()
        a.call("add_garden", json.dumps({"name": "Back yard"}))
        w = {"daily": {"2026-10-22": [38, 60], "2026-10-23": [40, 62]},
             "now": {"temp": 57.0, "date": "2026-10-24", "lo": 41, "hi": 63},
             "soil": {"2026-10-22": [47, 52], "2026-10-23": [46, 51], "2026-10-24": [45, 52]}}
        self.assertTrue(json.loads(a.merge_weather(json.dumps(w)))["changed"])
        self.assertFalse(json.loads(a.merge_weather(json.dumps(w)))["changed"])
        m = json.loads(a.snapshot())["gardens"][0]["metrics"]
        self.assertEqual((m["out_temp"]["source"], m["out_temp"]["current"]), ("weather", 57.0))
        self.assertEqual(m["soil_temp"]["source"], "estimated")
        self.assertEqual(m["soil_temp"]["history"][-1]["min"], 45)
        gid = json.loads(a.snapshot())["gardens"][0]["id"]
        a.call("log_garden_reading", json.dumps({"garden": gid, "metric": "soil_temp", "value": 58, "date": "2026-10-24"}))
        m = json.loads(a.snapshot())["gardens"][0]["metrics"]
        self.assertEqual((m["soil_temp"]["source"], m["soil_temp"]["current"]), ("manual", 58))
        self.assertEqual(m["out_temp"]["source"], "weather")
        b = self.app(a.data())  # the estimate survives a restore
        self.assertEqual(json.loads(b.snapshot())["gardens"][0]["metrics"]["out_temp"]["source"], "weather")

    def test_moisture_is_estimated_from_watering_weather_soil_and_mulch(self):
        a = self.app()
        a.call("add_garden", json.dumps({"name": "Back yard"}))
        gid = json.loads(a.snapshot())["gardens"][0]["id"]
        daily = {f"2026-10-{d:02d}": [40, 70] for d in range(1, 24)}
        a.merge_weather(json.dumps({"daily": daily, "now": {"temp": 60, "date": "2026-10-24", "lo": 42, "hi": 68}}))

        def est():
            return json.loads(a.snapshot())["gardens"][0]["metrics"]["moisture"]
        self.assertEqual(est()["estimate"]["watered"], False)
        self.assertTrue(json.loads(a.call("log_watering", json.dumps({"garden": gid, "date": "2026-10-23"})))["ok"])
        fresh = est()
        self.assertEqual((fresh["source"], fresh["estimate"]["since_water"]), ("estimated", 1))
        self.assertGreater(fresh["estimate"]["avail"], 0.7)
        a.call("log_watering", json.dumps({"garden": gid, "date": "2026-10-17"}))
        a.call("set_irrigation", json.dumps({"garden": gid, "soil": "sand"}))
        sand = est()["estimate"]["avail"]
        a.call("set_irrigation", json.dumps({"garden": gid, "soil": "clay"}))
        clay = est()["estimate"]["avail"]
        a.call("set_irrigation", json.dumps({"garden": gid, "mulch": True}))
        mulched = est()["estimate"]["avail"]
        self.assertLess(sand, clay)  # sand dries out faster than clay
        self.assertGreater(mulched, clay)  # mulch slows the drying
        a.call("log_garden_reading", json.dumps({"garden": gid, "metric": "moisture", "value": 33, "date": "2026-10-24"}))
        self.assertEqual((est()["source"], est()["current"]), ("manual", 33))

    def test_watering_card_can_be_hidden(self):
        a = self.app()
        a.call("add_garden", json.dumps({"name": "Back yard"}))
        gid = json.loads(a.snapshot())["gardens"][0]["id"]
        self.assertTrue(json.loads(a.snapshot())["gardens"][0]["show_water"])
        a.call("set_watering_card", json.dumps({"garden": gid, "shown": False}))
        self.assertFalse(json.loads(self.app(a.data()).snapshot())["gardens"][0]["show_water"])

    def test_a_removed_garden_leaves_the_list_but_its_history_stays(self):
        a = self.app()
        a.call("add_garden", json.dumps({"name": "Old bed"}))
        a.call("add_garden", json.dumps({"name": "Rack", "kind": "rack"}))
        snap = json.loads(a.snapshot())
        gid = next(g["id"] for g in snap["gardens"] if g["name"] == "Old bed")
        a.call("log_ph", json.dumps({"garden": gid, "value": 6.4}))
        self.assertTrue(json.loads(a.call("remove_garden", json.dumps({"garden": gid})))["ok"])
        snap = json.loads(a.snapshot())
        self.assertEqual([g["name"] for g in snap["gardens"]], ["Rack"])
        self.assertEqual([g["name"] for g in snap["past_gardens"]], ["Old bed"])
        b = json.loads(self.app(a.data()).snapshot())  # still there after a save and restore
        self.assertEqual([g["name"] for g in b["past_gardens"]], ["Old bed"])
        self.assertEqual(len(json.loads(a.data())["gardens"][gid]["ph_readings"]), 1)  # its readings are kept
        a.call("add_garden", json.dumps({"name": "Old bed"}))  # the name can be used again
        self.assertEqual(len(json.loads(a.snapshot())["gardens"]), 2)
        self.assertTrue(json.loads(a.call("restore_garden", json.dumps({"garden": gid})))["ok"])
        self.assertEqual(len(json.loads(a.snapshot())["gardens"]), 3)
        self.assertEqual(json.loads(a.snapshot())["past_gardens"], [])

    def test_trees_can_grow_without_a_garden(self):
        a = self.app()
        self.assertTrue(json.loads(a.call("add_variety", json.dumps({"garden": "", "species": "Apple", "variety": "Gala"})))["ok"])
        self.assertFalse(json.loads(a.call("add_variety", json.dumps({"garden": "", "species": "Tomato", "variety": "Roma"})))["ok"])
        v = json.loads(a.snapshot())["varieties"][0]
        self.assertEqual((v["garden"], v["kind"]), ("", "tree"))
        a.call("add_garden", json.dumps({"name": "Yard"}))
        self.assertTrue(json.loads(a.call("move_plants", json.dumps({"plant": v["id"], "to": "Yard"})))["ok"])
        self.assertEqual(json.loads(a.snapshot())["varieties"][0]["garden_name"], "Yard")
        self.assertTrue(json.loads(a.call("move_plants", json.dumps({"plant": v["id"], "to": ""})))["ok"])  # and back out again
        self.assertEqual(json.loads(a.snapshot())["varieties"][0]["garden"], "")
        again = json.loads(a.call("plant_again", json.dumps({"plant": v["id"], "garden": ""})))
        self.assertTrue(again["ok"])
        self.assertEqual(len(json.loads(a.snapshot())["varieties"]), 2)

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

    def test_the_layout_can_be_planted_and_tracked(self):
        m, gid = self.garden()
        m.set_layout(gid, 20, 10, 30, None, 0)
        m.assign_layout_rows(gid, "tomato", [0, 1], "Sungold")
        m.assign_layout_rows(gid, "pepper", [2])
        v = self.view(m, gid)
        self.assertEqual({(x["crop"], x["variety"]): x["plants"] for x in v["to_plant"]},
                         {("tomato", "Sungold"): v["rows"][0]["plants"] + v["rows"][1]["plants"], ("pepper", ""): v["rows"][2]["plants"]})
        made = m.plant_layout(gid, "2026-10-20", "start")
        self.assertEqual(len(made), 2)
        snap = m.snapshot()
        got = {x["name"]: x for x in snap["varieties"] if x["garden"] == gid}
        self.assertEqual(got["Sungold"]["count"], v["rows"][0]["plants"] + v["rows"][1]["plants"])
        self.assertEqual((got["Sungold"]["origin"], got["Sungold"]["planted"], got["Sungold"]["in_ground"]), ("start", "2026-10-20", "2026-10-20"))
        self.assertIn("row 1, 2", got["Sungold"]["notes"].replace("rows", "row"))
        after = self.view(m, gid)
        self.assertEqual(after["to_plant"], [])
        self.assertEqual(after["tracked_plants"], v["totals"]["plants"])
        with self.assertRaises(GardenError):
            m.plant_layout(gid)  # nothing left to plant
        m.assign_layout_rows(gid, "tomato", [3], "Sungold")  # more added later: only the new row is planted
        self.assertEqual(self.view(m, gid)["to_plant"][0]["rows"], [4])
        self.assertEqual(len(m.plant_layout(gid, None, "seed")), 1)
        m.assign_layout_rows(gid, None, [0])  # clearing a row keeps the plantings
        self.assertEqual(len([x for x in m.snapshot()["varieties"] if x["garden"] == gid]), 3)

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

    def test_a_resistant_variety_shortens_the_wait_or_clears_the_alert(self):
        m, gid = self.garden()
        m.set_layout(gid, 5, 20, 30, None, 0)
        m.assign_layout_rows(gid, "tomato", [0])
        year = self.view(m, gid)["year"]
        m.start_layout_season(gid)
        m.assign_layout_rows(gid, "tomato", [0])
        a = self.view(m, gid)["alerts"][0]
        self.assertEqual((a["level"], a["back_in"]), ("same", year + 3))  # Verticillium and Fusarium wait three years
        self.assertIn("Verticillium wilt", a["risks"])
        # Roma VF resists Verticillium and Fusarium, so only the two-year diseases are left
        m.set_variety_traits("tomato", "Roma VF", ["verticillium", "fusarium"])
        m.assign_layout_rows(gid, "tomato", [0], "Roma VF")
        a = self.view(m, gid)["alerts"][0]
        self.assertEqual((a["level"], a["back_in"]), ("same", year + 2))
        self.assertNotIn("Verticillium wilt", a["risks"])
        self.assertEqual(a["resisted"], ["Verticillium wilt", "Fusarium wilt"])
        self.assertIn("Roma VF resists", a["text"])
        # a pepper that resists everything a tomato passes on is only a note
        m.assign_layout_rows(gid, "pepper", [0], "Carolina")
        self.assertEqual(self.view(m, gid)["alerts"][0]["level"], "family")
        m.set_variety_traits("pepper", "carolina", ["verticillium", "nematode", "bacterial_spot"])
        a = self.view(m, gid)["alerts"][0]
        self.assertEqual((a["level"], a["resisted"]), ("resistant", ["Verticillium wilt", "Root-knot nematodes", "Bacterial spot"]))
        # and the planner row marker allows for the variety before anything is placed
        m.set_layout_draft(gid, "pepper", "length", 5, None, None, "Carolina")
        self.assertEqual(self.view(m, gid)["draft"]["flags"][0]["level"], "resistant")
        m.set_layout_draft(gid, "pepper", None, None, None, None, "Other")
        self.assertEqual(self.view(m, gid)["draft"]["flags"][0]["level"], "family")
        with self.assertRaises(GardenError):
            m.set_variety_traits("tomato", "Roma VF", ["clubroot"])  # not a tomato disease

    def test_a_placed_section_keeps_its_variety(self):
        m, gid = self.garden()
        m.set_layout(gid, 5, 20, 30, None, 0)
        m.set_layout_draft(gid, "tomato", "length", 8, None, None, "Roma VF")
        m.place_layout_draft(gid, 0, 2)
        sg = self.view(m, gid)["rows"][0]["segments"][0]
        self.assertEqual((sg["crop"], sg["variety"], sg["start_in"]), ("tomato", "Roma VF", 24))
        m.set_layout_draft(gid, "pepper")  # changing the crop drops the variety
        self.assertEqual(self.view(m, gid)["draft"]["variety"], "")

    def test_the_rows_can_run_at_any_angle_off_north(self):
        m, gid = self.garden()
        m.set_layout(gid, 20, 40, 30, 90)
        self.assertEqual(self.view(m, gid)["rotation"], 90)
        m.set_layout(gid, None, None, None, 450)
        self.assertEqual(self.view(m, gid)["rotation"], 90)
        m.set_layout(gid, None, None, None, 37.5)
        self.assertEqual(self.view(m, gid)["rotation"], 37.5)
        m.set_layout(gid, None, None, None, -20)
        self.assertEqual(self.view(m, gid)["rotation"], 340)
        with self.assertRaises(GardenError):
            m.set_layout(gid, None, None, None, "sideways")

    def test_tall_crops_put_shade_on_shorter_ones_beside_them(self):
        m, gid = self.garden()
        m.set_layout(gid, 20, 40, 30, 0)  # rows run north-south, stacked east to west
        m.assign_layout_rows(gid, "tomato", [0])
        m.assign_layout_rows(gid, "lettuce", [1])
        sun = self.view(m, gid)["sun"]
        names = [w["name"] for w in sun["shading"]]
        self.assertTrue(any("ettuce" in n for n in names), sun["shading"])
        self.assertGreaterEqual(sun["shading"][0]["pct"], 10)
        # rows run east-west with a 9 ft crop: its shadow falls to the north, onto row 0 when it grows in row 1
        m.set_layout_crop(gid, "tomato", height_ft=9)
        m.set_layout(gid, None, None, None, 90)
        m.assign_layout_rows(gid, "tomato", [1])
        m.assign_layout_rows(gid, "lettuce", [0])
        south_tall = self.view(m, gid)["sun"]
        m.assign_layout_rows(gid, "tomato", [0])
        m.assign_layout_rows(gid, "lettuce", [1])
        north_tall = self.view(m, gid)["sun"]
        loss = lambda v: sum(w["pct"] for w in v["shading"])
        self.assertGreater(loss(south_tall), 0)
        self.assertLess(loss(north_tall), loss(south_tall))

    def test_variety_height_and_habit_change_the_shade(self):
        m, gid = self.garden()
        m.set_layout(gid, 30, 40, 30, 90)  # rows run east-west, row 0 on the north side
        m.assign_layout_rows(gid, "tomato", [1])
        m.assign_layout_rows(gid, "lettuce", [0])  # lettuce is north of the tomatoes, where their shade falls
        m.set_variety_traits("tomato", "Sungold", habit="determinate")
        m.assign_layout_rows(gid, "tomato", [1], "Sungold")
        low = self.view(m, gid)["sun"]
        self.assertEqual(low["tallest"]["height"], 3.5)
        m.set_variety_traits("tomato", "Sungold", habit="indeterminate")
        tall = self.view(m, gid)["sun"]
        self.assertEqual(tall["tallest"]["height"], 6.0)
        self.assertGreaterEqual(sum(w["pct"] for w in tall["shading"]), sum(w["pct"] for w in low["shading"]))
        m.set_variety_traits("tomato", "Sungold", height_ft=9)  # a plain height wins, and the habit stays
        huge = self.view(m, gid)["sun"]
        self.assertEqual(huge["tallest"]["height"], 9)
        self.assertEqual(low["shading"], [])
        self.assertTrue(huge["shading"] and "Sungold" in huge["shading"][0]["by"][0])
        self.assertEqual(next(t for t in m.snapshot()["variety_traits"] if t["name"] == "Sungold")["habit"], "indeterminate")
        with self.assertRaises(GardenError):
            m.set_variety_traits("tomato", "Sungold", habit="climbing")
        with self.assertRaises(GardenError):
            m.set_variety_traits("tomato", "Sungold", height_ft=60)

    def test_a_variety_keeps_its_resistance_when_only_the_height_changes(self):
        m, gid = self.garden()
        m.set_variety_traits("tomato", "Roma VF", ["verticillium", "fusarium"])
        m.set_variety_traits("tomato", "Roma VF", height_ft=4)
        t = next(t for t in m.snapshot()["variety_traits"] if t["name"] == "Roma VF")
        self.assertEqual(t["resist"], ["fusarium", "verticillium"])
        self.assertEqual(t["height_ft"], 4)

    def test_hops_and_corn_are_on_the_list_with_their_heights(self):
        m, gid = self.garden()
        m.set_layout(gid, 20, 40, 30, 0)
        m.assign_layout_rows(gid, "hops", [0])
        m.assign_layout_rows(gid, "corn", [1])
        v = self.view(m, gid)
        by = {c["key"]: c for c in v["available"]}
        self.assertEqual([h["key"] for h in by["hops"]["habits"]], ["dwarf", "standard", "tall"])
        self.assertEqual(by["hops"]["height_ft"], 15)
        self.assertEqual(by["corn"]["height_ft"], 7)
        self.assertEqual(v["sun"]["tallest"]["name"], "Hops")

    def test_corn_wants_a_48_inch_block(self):
        m, gid = self.garden()
        m.set_layout(gid, 30, 40, 30, 0)
        m.assign_layout_rows(gid, "corn", [0])
        w = self.view(m, gid)["warnings"]
        self.assertTrue(any("48" in x["text"] for x in w), w)
        m.set_layout(gid, None, None, 48)
        self.assertEqual(self.view(m, gid)["row_in"], 48)
        self.assertEqual(self.view(m, gid)["warnings"], [])
        m.add_layout_segment(gid, 1, "corn", 3, 0)  # a stretch under 4 ft is too small a block
        w = self.view(m, gid)["warnings"]
        self.assertTrue(any("row 2" in x["text"] for x in w), w)
        with self.assertRaises(GardenError):
            m.set_layout(gid, None, None, 40)

    def test_season_shows_what_has_time_before_frost(self):
        from datetime import date as d
        from custom_components.garden_tracker.core import season
        names = {"radish": "Radish", "tomato": "Tomato", "garlic": "Garlic", "pumpkin": "Pumpkin", "hops": "Hops"}
        aug = {c["key"]: c for c in season.analyse(names, "04-25", "10-15", d(2026, 8, 10))["crops"]}
        self.assertEqual(aug["radish"]["status"], "plant")
        self.assertGreater(aug["radish"]["rounds"], 3)  # quick crops fit many back-to-back
        self.assertEqual(aug["tomato"]["status"], "late")  # 75 days will not finish by Oct 15
        self.assertEqual(aug["garlic"]["status"], "wait")
        self.assertNotIn("hops", aug)  # a perennial is not in the table
        late = {c["key"]: c for c in season.analyse(names, "04-25", "10-15", d(2026, 10, 25))["crops"]}
        self.assertEqual(late["garlic"]["status"], "plant")  # garlic goes in around the first frost
        self.assertEqual(late["radish"]["status"], "late")
        short = {c["key"]: c for c in season.analyse(names, "05-20", "08-25", d(2026, 5, 25))["crops"]}
        self.assertEqual(short["pumpkin"]["status"], "short")  # 100 days do not fit between May 27 and Aug 25
        m, gid = self.garden()
        g = next(x for x in m.snapshot()["gardens"] if x["id"] == gid)
        self.assertTrue(g["season"]["crops"])

    def test_days_to_harvest_come_from_the_seed_packet(self):
        m, gid = self.garden()
        season = lambda: {c["key"]: c for c in next(x for x in m.snapshot()["gardens"] if x["id"] == gid)["season"]["crops"]}
        usual = season()["tomato"]["days"]
        m.set_crop_days("tomato", 62)
        t = season()["tomato"]
        self.assertEqual((t["days"], t["edited"], t["usual_days"]), (62, True, usual))
        m.set_crop_days("tomato", 90, "half")
        self.assertEqual(season()["tomato"]["hardy"], "half")
        m.reset_crop_days("tomato")
        self.assertEqual(season()["tomato"]["days"], usual)
        with self.assertRaises(GardenError):
            m.set_crop_days("tomato", 2)
        with self.assertRaises(GardenError):
            m.set_crop_days("tomato", 60, "icy")
        with self.assertRaises(GardenError):
            m.set_crop_days("nope", 60)
        # a crop with no time listed (a perennial herb) can be given one
        g = next(x for x in m.snapshot()["gardens"] if x["id"] == gid)
        self.assertIn("mint", [x["key"] for x in g["season"]["untimed"]])
        m.set_crop_days("mint", 30, "hardy")
        self.assertIn("mint", season())

    def test_berries_and_blueberry_acid_warning(self):
        m, gid = self.garden()
        for k in ("blueberry", "raspberry", "blackberry"):
            self.assertIn(k, m._plant_names())
        m.set_layout(gid, 6, 12, 36)
        m.assign_layout_rows(gid, "blueberry")

        def warn():
            L = next(g for g in m.snapshot()["gardens"] if g["id"] == gid)["layout"]
            return [w for w in L["warnings"] if w["crop"] == "blueberry"]
        self.assertTrue(warn() and "TESTED" in warn()[0]["text"])  # no reading: test first
        m.log_ph(gid, 6.8)
        w = warn()
        self.assertTrue(w and w[0]["strong"] and "6.8" in w[0]["text"])
        m.log_ph(gid, 5.2, "2099-01-01")
        self.assertEqual(warn(), [])

    def test_post_spacing_follows_tomato_habit(self):
        from custom_components.garden_tracker.core import layout as L2
        m, gid = self.garden()
        m.set_variety_traits("tomato", "Roma", habit="determinate")
        m.set_variety_traits("tomato", "Brandywine", habit="indeterminate")
        names = {"tomato": "Tomatoes"}
        lay = {"width_ft": 6, "length_ft": 40, "row_in": 36, "path_in": 24, "rotation": 0, "year": 2026, "crops": {"tomato": {"support": "tpost"}}, "draft": None}

        def post(variety):
            lay["rows"] = [[{"crop": "tomato", "ft": 40, "start_ft": 0, "variety": variety}]]
            return L2.plan(lay, names, None, 2026, m.data["variety_traits"])["rows"][0]["segments"][0]["post_ft"]
        self.assertEqual(post("Roma"), 8.0)
        self.assertEqual(post("Brandywine"), 4.0)
        self.assertEqual(post(""), 4.0)
        lay["crops"]["tomato"]["post_ft"] = 5  # the user's own spacing wins
        self.assertEqual(post("Roma"), 5)
        m.set_layout(gid, 6, 40, 36)
        m.set_layout_crop(gid, "tomato", post_ft=7)
        m.set_layout_crop(gid, "tomato", post_ft=0)  # back to the recommended
        self.assertIsNone(m._layout_of(gid)[1]["crops"]["tomato"]["post_ft"])
        self.assertEqual(L2.recommended_post("bean", "pole"), 6.0)

    def test_cover_crop_terminated_in_several_steps(self):
        m, gid = self.garden()
        cid = m.add_cover_crop(gid, "Winter rye")
        m.terminate_cover_crop(gid, cid, None, ["mowed", "wilted", "plowed", "tilled"])
        item = next(g for g in m.snapshot()["gardens"] if g["id"] == gid)["cover"]["items"][0]
        self.assertEqual(item["methods"], ["mowed", "wilted", "plowed", "tilled"])
        with self.assertRaises(Exception):
            m.terminate_cover_crop(gid, cid, None, ["mowed", "burned"])
        m.edit_entry("cover", gid, cid, {"method": "plowed,tilled"})
        self.assertEqual(next(g for g in m.snapshot()["gardens"] if g["id"] == gid)["cover"]["items"][0]["methods"], ["plowed", "tilled"])
        m.reopen_cover_crop(gid, cid)
        self.assertEqual(next(g for g in m.snapshot()["gardens"] if g["id"] == gid)["cover"]["items"][0]["methods"], [])
        # a record saved before this had one method as text
        g = m.find_garden(gid)
        g["cover_crops"][0].update(terminated=m.today().isoformat(), method="tarped")
        g["cover_crops"][0].pop("methods", None)
        m._touch()
        self.assertEqual(next(x for x in m.snapshot()["gardens"] if x["id"] == gid)["cover"]["items"][0]["methods"], ["tarped"])

    def test_more_trees_and_custom_types(self):
        m, gid = self.garden()
        for k in ("pear", "asian_pear", "apricot", "hazelnut", "english_walnut", "black_walnut", "plum", "quince", "fig", "persimmon", "mulberry", "chestnut"):
            self.assertEqual(m.get_species(k)["kind"], "tree", k)
        # a type that is not on the list is kept for next time and can be renamed or changed
        vid = m.add_variety(gid, "Loquat", "Champagne", 1, kind="tree")
        self.assertIn("loquat", m.snapshot()["species"] if isinstance(m.snapshot()["species"], dict) else {s["key"]: s for s in m.snapshot()["species"]})
        tree = next(v for v in m.snapshot()["varieties"] if v["id"] == vid)
        self.assertTrue(tree["custom_type"] and tree["kind"] == "tree")
        m.update_variety(vid, species_name="Japanese loquat")
        self.assertEqual(next(v for v in m.snapshot()["varieties"] if v["id"] == vid)["species_name"], "Japanese loquat")
        m.update_variety(vid, kind="plant")
        self.assertEqual(next(v for v in m.snapshot()["varieties"] if v["id"] == vid)["kind"], "plant")
        with self.assertRaises(Exception):
            m.update_variety(m.add_variety(gid, "apple", "Gala", 1), species_name="Crab")  # a built-in type stays as it is

    def test_walnut_husk_fly_is_timed_from_trap_catches(self):
        from datetime import date
        from custom_components.garden_tracker.core.model import GardenModel
        m, gid = self.garden()
        for k in ("english_walnut", "black_walnut"):
            self.assertEqual([p["key"] for p in m.get_species(k)["pests"]], ["walnut_husk_fly"], k)  # not codling moth
        pest = m.get_species("english_walnut")["pests"][0]
        v = {"biofix": {}, "sprays": []}
        tv = lambda today: GardenModel._trap_view(v, pest, today)  # noqa: E731
        self.assertEqual(tv(date(2026, 5, 1))["state"], "early")
        self.assertEqual(tv(date(2026, 7, 1))["state"], "watch")
        v["biofix"]["walnut_husk_fly"] = "2026-08-05"
        self.assertEqual((tv(date(2026, 8, 8))["state"], tv(date(2026, 8, 8))["days_left"], tv(date(2026, 8, 8))["spray_by"]), ("spray", 7, "2026-08-15"))
        self.assertEqual(tv(date(2026, 8, 20))["state"], "late")
        v["sprays"].append({"date": "2026-08-10", "product": "Malathion"})
        self.assertEqual(tv(date(2026, 8, 20))["state"], "sprayed")

    def test_tree_pruning_reminder(self):
        from datetime import date
        from custom_components.garden_tracker.core.model import GardenModel
        view = GardenModel._pruning_view
        v = {"prunings": [], "prune_month": None}
        self.assertEqual(view(v, date(2026, 1, 20))["state"], "waiting")
        self.assertEqual(view(v, date(2026, 2, 1))["state"], "due")  # starts on the first of the month
        self.assertEqual(view(v, date(2026, 10, 25))["state"], "due")  # and stays until it is marked
        v["prune_month"] = 8
        self.assertEqual(view(v, date(2026, 7, 31))["state"], "waiting")
        self.assertEqual(view(v, date(2026, 8, 1))["state"], "due")
        v["prunings"] = [{"id": "a", "date": "2026-03-05", "outcome": "pruned", "notes": ""}]
        self.assertEqual(view(v, date(2026, 10, 25))["state"], "pruned")
        v["prunings"] = [{"id": "a", "date": "2026-03-05", "outcome": "skipped", "notes": ""}]
        self.assertEqual(view(v, date(2026, 10, 25))["state"], "skipped")
        v["prune_month"] = None
        self.assertEqual(view(v, date(2027, 2, 1))["state"], "due")  # a new year starts over

    def test_pruning_log_and_status(self):
        m, gid = self.garden()
        vid = m.add_variety(gid, "apple", "Honeycrisp", 1)
        m.log_pruning(vid, "pruned")
        tree = next(v for v in m.snapshot()["varieties"] if v["id"] == vid)
        self.assertEqual(tree["pruning"]["state"], "pruned")
        m.set_prune_month(vid, 3)
        self.assertEqual(next(v for v in m.snapshot()["varieties"] if v["id"] == vid)["pruning"]["month"], 3)

    def test_walnut_pruning_starts_in_march(self):
        from datetime import date
        from custom_components.garden_tracker.core.model import GardenModel
        m, gid = self.garden()
        sp = m.get_species("english_walnut")
        v = {"prunings": [], "prune_month": None}
        self.assertEqual(GardenModel._pruning_view(v, date(2026, 2, 20), sp)["state"], "waiting")
        self.assertEqual(GardenModel._pruning_view(v, date(2026, 3, 1), sp)["state"], "due")
        self.assertEqual(GardenModel._pruning_view(v, date(2026, 3, 1), m.get_species("apple"))["state"], "due")
        self.assertEqual(GardenModel._pruning_view(v, date(2026, 2, 20), m.get_species("apple"))["state"], "due")  # apples start in February
        self.assertIn("March to April", GardenModel._pruning_view(v, date(2026, 3, 1), sp)["note"])

    def test_bramble_cut_back_in_fall(self):
        from datetime import date
        from custom_components.garden_tracker.core import chores
        self.assertEqual([c["crop"] for c in chores.due({"raspberry", "blackberry", "tomato"}, date(2026, 10, 25))], ["raspberry", "blackberry"])
        self.assertEqual(chores.due({"raspberry"}, date(2026, 6, 1)), [])
        self.assertEqual(chores.due({"blueberry"}, date(2026, 10, 25)), [])
        m, gid = self.garden()
        m.set_layout(gid, 6, 12, 36)
        m.assign_layout_rows(gid, "raspberry")
        g = next(g for g in m.snapshot()["gardens"] if g["id"] == gid)
        self.assertEqual(bool(g["chores"]), 9 <= m.today().month <= 11)

    def test_herbs_and_more_garden_plants_are_on_the_list(self):
        m, gid = self.garden()
        names = m._plant_names()
        self.assertIn("strawberry", names)
        self.assertIn("sweet_potato", names)
        from custom_components.garden_tracker.core import rotation
        self.assertIsNotNone(rotation.check("strawberry", "tomato", 1))  # not after nightshades: verticillium wilt
        for k in ("basil", "cilantro", "parsley", "dill", "chives", "mint", "oregano", "thyme", "rosemary", "sage", "broccoli", "kale",
                  "spinach", "radish", "beet", "zucchini", "eggplant", "sunflower", "corn", "hops"):
            self.assertIn(k, names, k)
        m.set_layout(gid, 20, 40, 30, 0)
        m.assign_layout_rows(gid, "basil", [0])
        self.assertTrue(self.view(m, gid)["rows"][0]["plants"] > 0)

    def test_best_row_angle_follows_the_sun_and_the_heights(self):
        from custom_components.garden_tracker.core import sun
        b = sun.best_heading(47.3, 4.0, 30, 24, 0)
        self.assertEqual(b["best"], 90)  # tall crops on the north side, rows east-west
        self.assertLess(b["best_pct"], b["current_pct"])
        m, gid = self.garden()
        m.set_layout(gid, 20, 40, 30, 0)
        m.assign_layout_rows(gid, "tomato", [0, 1])
        v = self.view(m, gid)["sun"]
        self.assertTrue(v["even"])  # nothing stands over anything else
        self.assertEqual(v["best"], 0)
        self.assertEqual(v["shading"], [])

    def test_sun_position_is_sane(self):
        from custom_components.garden_tracker.core import sun
        alt, az = sun.position(47.3, 172, 12)
        self.assertAlmostEqual(alt, 66.1, delta=0.5)
        self.assertAlmostEqual(az, 180, delta=1)
        self.assertLess(sun.position(47.3, 172, 8)[1], 180)  # morning sun is in the east
        self.assertGreater(sun.position(47.3, 172, 16)[1], 180)

    def test_crop_height_can_be_changed(self):
        m, gid = self.garden()
        m.set_layout(gid, 20, 40, 30, 0)
        m.assign_layout_rows(gid, "tomato", [0])
        m.set_layout_crop(gid, "tomato", height_ft=9)
        self.assertEqual(self.view(m, gid)["sun"]["tallest"]["height"], 9)
        with self.assertRaises(GardenError):
            m.set_layout_crop(gid, "tomato", height_ft=-1)

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


class Irrigation(unittest.TestCase):
    def setUp(self):
        self.m = make()
        self.gid = self.m.add_garden("Back yard")
        self.m.set_layout(self.gid, 20, 40, 30, None, 0)
        self.m.assign_layout_rows(self.gid, "tomato", [0, 1, 2])
        self.m.assign_layout_rows(self.gid, "pepper", [3, 4])
        self.m.set_layout_crop(self.gid, "tomato", spacing_in=18)

    def water(self):
        return next(g for g in self.m.snapshot()["gardens"] if g["id"] == self.gid)["irrigation"]

    def crop(self, key):
        return next(c for c in self.water()["crops"] if c["key"] == key)

    def test_drip_is_the_default_and_loam_takes_one_gph_at_each_plant(self):
        w = self.water()
        self.assertEqual(w["method"], "drip")
        t = self.crop("tomato")
        self.assertEqual((t["flow_gph"], t["emit_in"], t["lines"]), (1.0, 18, 1))
        self.assertAlmostEqual(t["plant_gph"], 1.0, 2)
        self.assertEqual(t["emitters"], 3 * 26)  # 40 ft is 480 in, 26 emitters at 18 in, in 3 rows

    def test_clay_gets_half_gph_emitters_and_the_same_water_per_plant(self):
        self.m.set_irrigation(self.gid, soil="clay")
        t = self.crop("tomato")
        self.assertEqual((t["flow_gph"], t["emit_in"]), (0.5, 9))
        self.assertAlmostEqual(t["plant_gph"], 1.0, 1)

    def test_run_time_is_for_the_garden_and_footage_is_ordered_by_kind(self):
        w = self.water()
        self.assertEqual(sum(o["feet"] for o in w["order"]), 5 * 40)
        self.assertAlmostEqual(w["totals"]["gpm"], w["totals"]["gph"] / 60, 1)
        self.assertEqual(w["run_min"], w["auto_run_min"])
        self.m.set_irrigation(self.gid, run_min=30)
        self.assertEqual(self.water()["run_min"], 30)
        self.assertTrue(self.crop("tomato")["short"])  # too short for the thirstiest crop, so it says so
        self.m.set_irrigation(self.gid, run_min=None)
        self.assertEqual(self.water()["run_min_set"], None)

    def test_rolls_cover_the_footage_with_an_allowance(self):
        from custom_components.garden_tracker.core import irrigation as irr
        self.assertEqual(irr.rolls_for(200), [{"len": 100, "count": 3}])  # 210 ft with the allowance
        self.assertEqual(irr.rolls_for(480), [{"len": 500, "count": 1}, {"len": 100, "count": 1}])
        self.assertEqual(irr.rolls_for(450), [{"len": 500, "count": 1}])

    def test_grid_rows_in_a_30_inch_bed_get_two_runs_and_a_pinned_choice_sticks(self):
        self.m.assign_layout_rows(self.gid, "carrot", [5])
        self.assertEqual(self.crop("carrot")["lines"], 2)
        self.m.set_irrigation_crop(self.gid, "pepper", flow_gph=0.5, emit_in=9)
        p = self.crop("pepper")
        self.assertEqual((p["flow_gph"], p["emit_in"], p["pinned"]), (0.5, 9, True))
        self.m.set_irrigation_crop(self.gid, "pepper", flow_gph=None, emit_in=None)
        self.assertFalse(self.crop("pepper")["pinned"])

    def test_a_moved_sprinkler_gets_places_minutes_and_how_often(self):
        self.m.set_irrigation(self.gid, method="sprinkler")
        self.m.set_sprinkler(self.gid, gpm=4, radius_ft=20)
        w = self.water()
        s = w["sprinkler"]
        self.assertEqual(w["method"], "sprinkler")
        self.assertAlmostEqual(s["pr"], 96.3 * 4 / 400, 2)  # 0.96 in an hour on 400 sq ft a head
        self.assertEqual((s["mode"], s["needed"], s["sets"]), ("moved", 2, 2))  # the 20 x 40 garden is two places
        self.assertEqual((s["per_week"], s["per_week_auto"]), (2, True))  # clay loam does better with fewer, deeper waterings
        self.assertAlmostEqual(s["depth_in"], 0.75, 2)  # tomatoes want 1.5 in a week
        self.assertEqual(s["minutes"], round(0.75 / s["pr"] * 60))
        self.assertEqual(s["session_min"], s["minutes"] * 2)
        self.assertTrue(s["over_intake"])  # 0.96 in an hour is faster than clay loam takes it in
        self.assertLess(s["cycle_min"], s["minutes"])
        self.assertTrue(s["warnings"])
        self.assertEqual(w["totals"]["gpm"], 4)  # one sprinkler at a time
        self.assertAlmostEqual(s["gal_session"], 4 * s["session_min"], delta=2)
        self.assertEqual(w["fert"]["overfed"], [])  # no drip lines to valve off
        self.m.set_sprinkler(self.gid, per_week=3)
        self.assertEqual(self.water()["sprinkler"]["per_week"], 3)

    def test_fixed_sprinklers_run_together_and_can_be_measured(self):
        self.m.set_irrigation(self.gid, method="sprinkler")
        self.m.set_sprinkler(self.gid, mode="fixed", gpm=2, radius_ft=20, heads=1)
        s = self.water()["sprinkler"]
        self.assertEqual((s["heads"], s["sets"], s["covered"]), (1, 1, 0.5))
        self.assertTrue(any("50%" in w for w in s["warnings"]))
        self.m.set_sprinkler(self.gid, heads=None)
        w = self.water()
        self.assertEqual(w["sprinkler"]["heads"], 2)
        self.assertEqual(w["totals"]["gpm"], 4)  # two at 2 GPM, all on together
        self.m.set_sprinkler(self.gid, pr_mode="measured", pr_in_hr=0.25)
        s = self.water()["sprinkler"]
        self.assertEqual(s["pr"], 0.25)  # catch cans beat the arithmetic
        self.assertFalse(s["over_intake"])
        self.assertEqual(s["cycle_min"], None)
        with self.assertRaises(GardenError):
            self.m.set_sprinkler(self.gid, mode="flood")

    def _weather(self, lo, hi, rain=0.0, lat=47.3):
        today = self.m.today()
        self.m.set_location(lat, -119.5, "Ephrata")
        self.m.data["daily"].clear()
        self.m.data["rain"].clear()
        for n in range(7):
            k = (today - timedelta(days=n)).isoformat()
            self.m.data["daily"][k] = [lo, hi]
            if rain:
                self.m.data["rain"][k] = rain

    def test_weather_scales_the_watering(self):
        self._weather(55, 105)
        hot = self.water()
        self._weather(40, 60)
        cool = self.water()
        self.assertGreater(hot["weather"]["factor"], cool["weather"]["factor"])
        self.assertLess(cool["weather"]["factor"], 1.0)
        self.assertGreater(hot["run_min"], cool["run_min"])
        pick = lambda w: next(x for x in w["crops"] if x["key"] == "tomato")
        self.assertGreater(pick(hot)["water_in_week"], pick(cool)["water_in_week"])
        self.assertEqual(pick(hot)["usual_in_week"], pick(cool)["usual_in_week"])

    def test_a_hot_july_week_asks_for_more_than_the_usual(self):
        from custom_components.garden_tracker.core import irrigation as irr
        day = date(2026, 7, 15)
        rows = lambda lo, hi: {(day - timedelta(days=n)).isoformat(): [lo, hi] for n in range(7)}
        hot = irr.weather_need(rows(65, 102), {}, day, 47.3)
        mild = irr.weather_need(rows(50, 75), {}, day, 47.3)
        self.assertGreater(hot["factor"], 1.3)
        self.assertLess(mild["factor"], 1.0)
        self.assertEqual(irr.weather_need({}, {}, day), None)

    def test_weather_can_be_turned_off_and_rain_counts(self):
        self._weather(55, 90)
        on = self.water()
        self.m.set_irrigation(self.gid, weather=False)
        off = self.water()
        self.assertIsNone(off["weather"])
        self.assertFalse(off["use_weather"])
        self._weather(55, 90, rain=0.5)
        self.m.set_irrigation(self.gid, weather=True)
        wet = self.water()
        self.assertLess(wet["run_min"], on["run_min"])
        self.assertGreater(wet["weather"]["rain_credit"], 0)

    def test_no_temperatures_means_the_usual_amounts(self):
        self.m.data["daily"].clear()
        w = self.water()
        self.assertIsNone(w["weather"])
        c = next(x for x in w["crops"] if x["key"] == "tomato")
        self.assertEqual(c["water_in_week"], c["usual_in_week"])

    def test_weather_moves_sprinkler_minutes(self):
        self.m.set_irrigation(self.gid, method="sprinkler")
        self._weather(55, 105)
        hot = self.water()["sprinkler"]["minutes"]
        self._weather(40, 60)
        self.assertGreater(hot, self.water()["sprinkler"]["minutes"])

    def test_fertigation_works_with_sprinklers(self):
        self.m.set_irrigation(self.gid, method="sprinkler")
        f = self.water()["fert"]
        s = self.water()["sprinkler"]
        self.assertTrue(f["ready"])
        self.assertAlmostEqual(f["gal_watering"], s["gal_session"], delta=1)  # the water through the pump over the whole watering
        self.assertLessEqual(f["tanks"][0]["stock_gal"], 4.0)

    def test_a_crop_that_would_be_over_fed_gets_a_shorter_feeding_for_its_section(self):
        f = self.water()["fert"]
        self.assertEqual(f["ppm_n"], 90)  # tomato 100 and pepper 75 ppm, weighted by their water
        self.assertEqual(f["overfed"], [])  # 90 is within a quarter of both
        self.m.set_fert_mix(self.gid, "growth", ppm_n=110)
        f = self.water()["fert"]
        over = {o["key"]: o for o in f["overfed"]}
        self.assertEqual(list(over), ["pepper"])  # 110 is more than a quarter above the pepper's 75
        o = over["pepper"]
        self.assertEqual(o["rows"], [4, 5])
        self.assertEqual(o["full_minutes"], round(f["inject_min"]))
        self.assertAlmostEqual(o["minutes"], f["inject_min"] * 75 / 110, delta=1)
        self.assertNotIn("plants", f)  # no per plant list any more
        self.m.set_fert_mix(self.gid, "growth", ppm_n=60)
        self.assertEqual(self.water()["fert"]["overfed"], [])  # a weaker mix suits both

    def test_pump_defaults_to_the_dosatron_d14mz2_and_is_editable(self):
        f = self.water()["fert"]
        self.assertEqual(len(f["pumps"]), 1)
        i = f["pumps"][0]
        self.assertEqual((i["name"], i["min_ratio"], i["max_ratio"], i["max_gpm"], i["tank_gal"]), ("Dosatron D14MZ2", 50, 500, 14.0, 4.0))
        self.m.set_pump(self.gid, "pump1", name="Other", max_ratio=1000, tank_gal=3)
        i = self.water()["fert"]["pumps"][0]
        self.assertEqual((i["name"], i["max_ratio"], i["tank_gal"]), ("Other", 1000, 3))
        with self.assertRaises(GardenError):
            self.m.set_pump(self.gid, "pump1", min_ratio=1100)  # past the weakest dilution

    def test_a_venturi_has_no_dial_and_sizes_the_stock_from_its_suction(self):
        key = self.m.set_pump(self.gid, None, "Mazzei 484", kind="venturi", suction_gph=12, inlet_psi=40, outlet_psi=20, motive_gpm=3.4, tank_gal=10)
        self.m.set_tank_pump(self.gid, "A", key)
        f = self.water()["fert"]
        t = next(x for x in f["tanks"] if x["tank"] == "A")
        draw = 12 * f["inject_min"] / 60
        self.assertTrue(t["venturi"])
        self.assertAlmostEqual(t["stock_gal"], min(draw, 10), delta=0.01)
        self.assertTrue(t["dial"].startswith("suction"))
        self.assertAlmostEqual(t["grams"] / t["stock_gal"], t["g_per_gal"], delta=1)
        # a tank that holds less than it would draw means the suction is throttled
        self.m.set_pump(self.gid, key, tank_gal=0.5)
        t = next(x for x in self.water()["fert"]["tanks"] if x["tank"] == "A")
        self.assertEqual(t["stock_gal"], 0.5)
        self.assertLess(t["throttle_gph"], 12)
        self.assertIn("throttled", t["dial"])
        # too little pressure drop is called out; so is a back pressure higher than the inlet
        self.m.set_pump(self.gid, key, inlet_psi=30, outlet_psi=28)
        self.assertTrue(any("pressure to fall" in w for w in self.water()["fert"]["warnings"]))
        with self.assertRaises(GardenError):
            self.m.set_pump(self.gid, key, inlet_psi=20, outlet_psi=30)
        self.m.set_pump(self.gid, key, outlet_psi=None)  # clearing a pressure is allowed
        self.m.set_acid(self.gid, ph=8.0, ta_ppm=100)
        self.m.set_tank_pump(self.gid, "acid", key)
        self.assertTrue(self.water()["acid"]["tank"]["dial"].startswith("suction"))

    def test_a_second_pump_lets_the_tanks_run_together_and_acid_run_with_the_feeding(self):
        self.m.set_fertigation(self.gid, active="fruiting")
        f = self.water()["fert"]
        self.assertEqual([r["tanks"] for r in f["feed_runs"]], [["A"], ["B"]])  # one pump: calcium nitrate and the rest take turns
        a = self.water()["acid"]
        self.m.set_acid(self.gid, ph=8.0, ta_ppm=100)
        self.assertFalse(self.water()["acid"]["with_feed"])  # shares the only pump
        key = self.m.set_pump(self.gid, None, "Second Dosatron", tank_gal=3)
        self.m.set_tank_pump(self.gid, "B", key)
        f = self.water()["fert"]
        self.assertEqual([r["tanks"] for r in f["feed_runs"]], [["A", "B"]])  # together, one watering
        self.assertEqual({t["tank"]: t["pump"] for t in f["tanks"]}, {"A": "pump1", "B": key})
        self.assertLessEqual(next(t for t in f["tanks"] if t["tank"] == "B")["stock_gal"], 3.0)
        self.m.set_tank_pump(self.gid, "acid", key)
        self.m.set_tank_pump(self.gid, "B", "pump1")
        self.assertTrue(self.water()["acid"]["with_feed"])  # acid on its own pump can run with the feeding
        self.m.remove_pump(self.gid, key)
        self.assertEqual(self.water()["acid"]["pump"], "pump1")  # its tanks go back to the first pump
        self.assertFalse(self.water()["acid"]["with_feed"])
        with self.assertRaises(GardenError):
            self.m.remove_pump(self.gid, "pump1")

    def test_acid_applications_are_logged_by_garden(self):
        self.m.log_acid(self.gid, "2026-10-20", 99, 135, 8.0, 5.6, "first")
        self.m.log_acid(self.gid, None, 50)
        log = self.water()["acid_log"]
        self.assertEqual((log["count_year"], log["ml_year"]), (2, 149))
        self.assertEqual(log["entries"][0]["date"], TODAY.isoformat())
        eid = log["entries"][1]["id"]
        self.m.edit_entry("acid", self.gid, eid, {"ml": 120})
        self.assertEqual(self.water()["acid_log"]["ml_year"], 170)
        self.m.delete_entry("acid", self.gid, eid)
        self.assertEqual(self.water()["acid_log"]["count_year"], 1)
        with self.assertRaises(GardenError):
            self.m.log_acid(self.gid, None, -1)

    def test_growth_mix_sizes_the_tank_to_the_pump_and_the_nitrogen_to_the_plants(self):
        f = self.water()["fert"]
        self.assertTrue(f["ready"])
        self.assertEqual(f["ppm_from"], "plants")
        self.assertEqual(len(f["tanks"]), 1)
        t = f["tanks"][0]
        self.assertLessEqual(t["stock_gal"], 4.0)
        self.assertGreaterEqual(t["ratio"], 50)
        self.assertAlmostEqual(f["water_gal"] / t["ratio"], t["stock_gal"], 1)
        # grams of 20-10-20 for the nitrogen asked for: ppm is mg a litre
        self.assertAlmostEqual(t["grams"], f["water_gal"] * 3.78541 * f["ppm_n"] / 1000 / 0.20, delta=1)
        self.assertLess(f["inject_min"], f["run_min"])  # the end of the run is plain water

    def test_a_big_garden_needs_a_weaker_dilution_to_stay_within_four_gallons(self):
        self.m.set_layout(self.gid, 20, 100, 30, None, 0)  # more rows and longer ones, so much more water
        self.m.assign_layout_rows(self.gid, "tomato")
        f = self.water()["fert"]
        t = f["tanks"][0]
        self.assertGreater(t["ratio"], 50)
        self.assertLessEqual(t["stock_gal"], 4.0)

    def test_fruiting_mix_splits_calcium_nitrate_from_the_phosphate_and_sulfate(self):
        self.m.set_fertigation(self.gid, active="fruiting")
        f = self.water()["fert"]
        self.assertEqual([t["tank"] for t in f["tanks"]], ["A", "B"])
        a, b = f["tanks"]
        self.assertEqual([c["name"] for c in a["components"]], ["Calcium nitrate 15.5-0-0"])
        self.assertEqual(len(b["components"]), 2)
        self.assertTrue(any("cannot be mixed strong" in w for w in f["warnings"]))
        self.assertAlmostEqual(f["n_pct"], 7.8, 1)  # 2 of 4-18-38, 2 of 15.5-0-0 and 1 of 0-0-0
        self.assertGreater(f["analysis"]["Ca"], 0)
        self.assertGreater(f["analysis"]["Mg"], 0)
        c = {x["name"]: x["g"] for x in f["components"]}
        self.assertAlmostEqual(c["MasterBlend 4-18-38"], c["Calcium nitrate 15.5-0-0"], 1)  # 2:2:1
        self.assertAlmostEqual(c["MasterBlend 4-18-38"] / c["Epsom salt"], 2.0, 1)

    def test_mixes_can_be_added_changed_and_removed(self):
        key = self.m.set_fert_mix(self.gid, None, "Late feed", 80)
        self.m.set_fert_component(self.gid, key, None, "Potash 0-0-50", 0, 0, 50, 0, 0, 1, "A")
        self.m.set_fertigation(self.gid, active=key)
        f = self.water()["fert"]
        self.assertFalse(f["ready"])  # no nitrogen in it
        self.m.set_fert_component(self.gid, key, 0, n=10)
        f = self.water()["fert"]
        self.assertEqual((f["ppm_n"], f["ppm_from"]), (80, "mix"))
        self.m.remove_fert_component(self.gid, key, 0)
        self.m.remove_fert_mix(self.gid, key)
        self.assertEqual(self.water()["fert"]["active"], "growth")
        with self.assertRaises(GardenError):
            self.m.set_fertigation(self.gid, active="nope")

    def test_acid_for_a_water_test(self):
        a = self.water()["acid"]
        self.assertFalse(a["ready"])
        self.m.set_acid(self.gid, ph=8.0, ta_ppm=100)
        a = self.water()["acid"]
        self.assertTrue(a["ready"])
        self.assertAlmostEqual(a["meq_l"], 1.75, 1)  # most of the alkalinity (2 meq/L) is used up to reach pH 5.5
        self.assertAlmostEqual(a["meq_per_ml"], 8.99, 1)  # 35% sulfuric acid is about 9 normal
        self.assertAlmostEqual(a["ml_per_gal"], a["meq_l"] * 3.78541 / a["meq_per_ml"], 1)
        f = self.water()["fert"]
        self.assertAlmostEqual(a["tank"]["ml"], a["ml_per_gal"] * f["water_gal"], delta=1)
        self.assertLessEqual(a["tank"]["stock_gal"], 4.0)
        self.m.set_acid(self.gid, strength_pct=93)
        self.assertLess(self.water()["acid"]["ml_per_gal"], a["ml_per_gal"] / 2)  # stronger acid, less of it
        self.m.set_acid(self.gid, target_ph=6.5)
        self.assertLess(self.water()["acid"]["meq_l"], a["meq_l"])
        self.m.set_acid(self.gid, ph=5.5, ta_ppm=20, target_ph=5.5)
        self.assertEqual(self.water()["acid"]["ml_per_gal"], 0)  # already there
        self.assertTrue(self.water()["acid"]["warnings"])
        with self.assertRaises(GardenError):
            self.m.set_acid(self.gid, ph=20)

    def test_low_water_ph_gets_a_base_for_the_tank_instead_of_acid(self):
        self.m.set_acid(self.gid, ph=5.6, ta_ppm=20, target_ph=6.5)
        a = self.water()["acid"]
        self.assertEqual((a["mode"], a["base"]), ("raise", "kbic"))
        self.assertGreater(a["g_per_gal"], 0)
        self.assertNotIn("ml_per_gal", a)
        self.assertAlmostEqual(a["tank"]["g"], a["g_per_gal"] * a["water_gal"], delta=1)
        k = a["g_per_gal"]
        self.m.set_acid(self.gid, base="nabic")
        self.assertLess(self.water()["acid"]["g_per_gal"], k)  # a lighter salt, so less by weight
        self.m.set_acid(self.gid, base="koh")
        koh = self.water()["acid"]
        self.assertLess(koh["g_per_gal"], k)
        self.assertTrue(any("caustic" in w for w in koh["warnings"]))
        self.m.set_acid(self.gid, base="kbic", target_ph=8.8)
        self.assertTrue(any("8.3" in w for w in self.water()["acid"]["warnings"]))  # bicarbonate cannot get there
        with self.assertRaises(GardenError):
            self.m.set_acid(self.gid, base="lye")

    def test_lime_for_low_soil_ph(self):
        w = self.water()["lime"]
        self.assertFalse(w["ready"])  # no soil pH logged yet
        self.m.log_ph(self.gid, 5.5)
        w = self.water()["lime"]
        self.assertEqual((w["ready"], w["ph_from"], w["soil"]), (True, "log", "clay_loam"))
        self.assertAlmostEqual(w["lb_1000"], 90.0, 1)  # 90 lb a unit on clay loam, one unit up
        self.assertAlmostEqual(w["lb_total"], 90.0 * 20 * 40 / 1000, 1)  # the garden is 20 x 40 ft
        self.assertEqual(w["applications"], 1)
        self.m.set_lime(self.gid, lime_type="dolomitic", target_ph=7.0)
        w = self.water()["lime"]
        self.assertAlmostEqual(w["lb_1000"], 90 * 1.5 / 1.05, 0)
        self.assertEqual(w["applications"], 2)  # over the 100 lb a time limit
        self.m.set_lime(self.gid, lb_per_unit=50, ph=6.0, target_ph=6.5, lime_type="calcitic")
        w = self.water()["lime"]
        self.assertEqual((w["ph_from"], w["lb_1000"]), ("you", 25.0))
        self.m.set_lime(self.gid, ph=7.0)
        self.assertEqual(self.water()["lime"]["lb_total"], 0)
        with self.assertRaises(GardenError):
            self.m.set_lime(self.gid, lime_type="chalk")

    def test_bad_input(self):
        for bad in (dict(soil="gravel"), dict(per_week=0), dict(method="flood")):
            with self.assertRaises(GardenError):
                self.m.set_irrigation(self.gid, **bad)
        with self.assertRaises(GardenError):
            self.m.set_irrigation_crop(self.gid, "tomato", flow_gph=2)
        with self.assertRaises(GardenError):
            self.m.set_fert_component(self.gid, "growth", None, "", 1)

    def test_save_and_restore(self):
        a = GardenApp(SPECIES.read_text("utf-8"), None, TODAY.isoformat())
        for svc, data in (("add_garden", {"name": "Back yard"}),):
            a.call(svc, json.dumps(data))
        gid = json.loads(a.snapshot())["gardens"][0]["id"]
        a.call("set_layout", json.dumps({"garden": gid, "width_ft": 10, "length_ft": 10, "row_in": 30}))
        a.call("assign_layout_rows", json.dumps({"garden": gid, "crop": "tomato"}))
        a.call("set_irrigation", json.dumps({"garden": gid, "soil": "clay"}))
        a.call("set_fert_mix", json.dumps({"garden": gid, "mix": "growth", "ppm_n": 125}))
        a.call("set_pump", json.dumps({"garden": gid, "pump": "pump1", "tank_gal": 3}))
        b = GardenApp(SPECIES.read_text("utf-8"), a.data(), TODAY.isoformat())
        w = json.loads(b.snapshot())["gardens"][0]["irrigation"]
        self.assertEqual((w["soil"], w["fert_settings"]["mixes"]["growth"]["ppm_n"], w["fert"]["pumps"][0]["tank_gal"]), ("clay", 125, 3))


class TreeNames(unittest.TestCase):
    def test_trees_are_named_tree(self):
        import json, pathlib
        p = pathlib.Path(__file__).parent.parent / "custom_components/garden_tracker/core/species.json"
        d = json.loads(p.read_text())
        names = {k: v["name"] for k, v in d.items() if isinstance(v, dict) and v.get("kind") == "tree"}
        self.assertEqual(names["black_walnut"], "Walnut tree, black")
        self.assertEqual(names["cherry"] if "cherry" in names else "Cherry tree", "Cherry tree")
        for k, n in names.items():
            self.assertIn("tree", n.lower(), k)


class SprayAttention(unittest.TestCase):
    def _orchard(self, today, per_day):
        """A tree with daily temperatures that give `per_day` degree days a day from Jan 1 to today."""
        m = make(today)
        m.add_variety("", "apple", "Gala")
        d = date(today.year, 1, 1)
        while d < today:
            m.data["daily"][d.isoformat()] = [50.0, 50.0 + 2 * per_day]
            d += timedelta(days=1)
        return m

    def _gala(self, m):
        return next(v for v in m.snapshot()["varieties"] if v["name"] == "Gala")

    def test_codling_moth_counts_from_jan_1_with_no_trap(self):
        m = self._orchard(date(2026, 3, 1), 2)  # 59 days at 2 degree days
        p = self._gala(m)["pests"][0]
        self.assertEqual(p["status"]["biofix"], "2026-01-01")
        self.assertEqual(p["status"]["next_dd"], 425)
        self.assertTrue(p["status"]["estimated_start"])
        self.assertFalse(p["needs_biofix"])

    def test_a_spray_within_seven_days_is_flagged_with_a_range(self):
        m = self._orchard(date(2026, 4, 11), 4)  # 100 days at 4 dd = 400, so 25 to go: 7 days
        v = self._gala(m)
        a = v["alert"]
        self.assertEqual(a["state"], "soon")
        self.assertEqual(a["days"], 7)
        self.assertEqual(a["date"], "2026-04-18")
        self.assertLessEqual(a["low"], a["days"])
        self.assertGreaterEqual(a["high"], a["days"])
        self.assertEqual(v["status"]["level"], "spray")

    def test_nothing_is_flagged_when_the_spray_is_weeks_away(self):
        m = self._orchard(date(2026, 3, 1), 2)
        self.assertIsNone(self._gala(m)["alert"])
        self.assertNotEqual(self._gala(m)["status"]["level"], "spray")

    def test_window_open_until_a_spray_is_logged(self):
        m = self._orchard(date(2026, 4, 20), 4)  # past 425
        a = self._gala(m)["alert"]
        self.assertEqual(a["state"], "open")
        m.log_spray("Gala", "Spinosad", "2026-04-19")
        self.assertIsNone(self._gala(m)["alert"])

    def test_a_logged_trap_catch_restarts_the_count_at_250(self):
        m = self._orchard(date(2026, 4, 10), 4)
        m.set_biofix("Gala", "codling_moth", "2026-03-20")
        st = self._gala(m)["pests"][0]["status"]
        self.assertEqual(st["next_dd"], 250)
        self.assertFalse(st["estimated_start"])
