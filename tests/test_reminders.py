import unittest
from datetime import date

from . import _load  # noqa: F401
from .test_core import make
from custom_components.garden_tracker.core import reminders as rem


def fc(*rows):
    return [{"date": d, "lo": lo, "hi": hi} for d, lo, hi in rows]


class NoteReminders(unittest.TestCase):
    def setUp(self):
        self.today = date(2026, 9, 25)
        self.m = make(self.today)
        self.gid = self.m.add_garden("Back Garden")
        self.vid = self.m.add_variety(self.gid, "garlic", "Music", 4, "seed", "2025-10-20")
        self.m.add_review(self.vid, "Add potassium sulfate before planting.", 2026)
        for r in self.m.data["varieties"][self.vid]["reviews"]:
            r["added"] = "2026-06-01"

    def due(self, today):
        self.m.today = lambda: today
        self.m._rev += 1
        return self.m.snapshot()["reminders"]

    def test_note_shows_before_the_fall_planting_window(self):
        r = self.due(date(2026, 9, 25))
        self.assertEqual([x["note"] for x in r], ["Add potassium sulfate before planting."])
        self.assertIn(r[0]["state"], ("open", "soon"))

    def test_not_shown_in_midsummer(self):
        self.assertEqual(self.due(date(2026, 7, 1)), [])

    def test_done_hides_it_for_this_season_only(self):
        r = self.due(date(2026, 10, 5))[0]
        self.m.review_done(self.vid, r["id"], r["cycle"])
        self.assertEqual(self.due(date(2026, 10, 6)), [])
        self.assertEqual(len(self.due(date(2027, 10, 5))), 1)

    def test_snooze_hides_for_a_week(self):
        r = self.due(date(2026, 10, 5))[0]
        self.m.review_snooze(self.vid, r["id"], 7)
        self.assertEqual(self.due(date(2026, 10, 8)), [])
        self.assertEqual(len(self.due(date(2026, 10, 13))), 1)

    def test_a_note_you_just_wrote_is_not_a_reminder(self):
        self.m.today = lambda: date(2026, 10, 5)
        self.m.add_review(self.vid, "Fresh note", 2026)
        self.assertNotIn("Fresh note", [x["note"] for x in self.due(date(2026, 10, 6))])

    def test_past_plants_notes_still_remind(self):
        self.m.today = lambda: date(2026, 10, 5)
        self.m.archive_variety(self.vid, "season_over")
        self.assertEqual(len(self.due(date(2026, 10, 5))), 1)
        self.assertTrue(self.due(date(2026, 10, 5))[0]["archived"])

    def test_tree_notes_show_before_bloom(self):
        v = self.m.add_variety("", "Loquat", "Champagne", 1, kind="tree")
        self.m.add_review(v, "Thin fruit earlier.", 2026)
        for r in self.m.data["varieties"][v]["reviews"]:
            r["added"] = "2026-01-01"
        notes = [x["note"] for x in self.due(date(2027, 3, 1))]
        self.assertIn("Thin fruit earlier.", notes)


class Alerts(unittest.TestCase):
    PLANTS = [{"id": "t", "name": "Tomato", "species": "tomato", "hardy": "tender", "count": 6},
              {"id": "p", "name": "Pepper", "species": "pepper", "hardy": "tender", "count": 4},
              {"id": "g", "name": "Garlic", "species": "garlic", "hardy": "fall", "count": 180},
              {"id": "k", "name": "Kale", "species": "kale", "hardy": "hardy", "count": 8},
              {"id": "c", "name": "Cauliflower", "species": "cauliflower", "hardy": "half", "count": 3}]
    TODAY = date(2026, 11, 5)

    def alerts(self, rows, acked=()):
        return rem.forecast_alerts(fc(*rows), self.TODAY, self.PLANTS, 32.0, 95.0, acked)

    def test_frost_names_tender_plants_and_what_is_fine(self):
        a = self.alerts([("2026-11-05", 29, 50)])
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0]["kind"], "frost")
        self.assertEqual(a[0]["title"], "Frost tonight: low of 29°F")
        self.assertEqual([p["name"] for p in a[0]["plants"]], ["Tomato", "Pepper"])
        self.assertIn("Garlic, Kale and Cauliflower are fine", a[0]["text"])

    def test_half_hardy_only_hurt_by_a_hard_frost(self):
        a = self.alerts([("2026-11-05", 30, 50)])
        self.assertNotIn("Cauliflower", [p["name"] for p in a[0]["plants"]])
        a = self.alerts([("2026-11-05", 26, 50)])
        self.assertIn("Cauliflower", [p["name"] for p in a[0]["plants"]])

    def test_no_alert_when_it_stays_above_freezing(self):
        self.assertEqual(self.alerts([("2026-11-05", 36, 55), ("2026-11-06", 34, 55)]), [])

    def test_only_the_next_three_days(self):
        self.assertEqual(self.alerts([("2026-11-05", 40, 60), ("2026-11-09", 20, 40)]), [])

    def test_heat_run_groups_days(self):
        a = rem.forecast_alerts(fc(("2026-07-09", 70, 101), ("2026-07-10", 72, 103), ("2026-07-11", 70, 99)),
                                date(2026, 7, 9), self.PLANTS, 32.0, 95.0, ())
        self.assertEqual(len(a), 1)
        self.assertEqual(a[0]["kind"], "heat")
        self.assertEqual(a[0]["title"], "Heat Thursday to Saturday: highs of 103°F")
        self.assertIn("Tomato and Pepper may drop blossoms", a[0]["text"])

    def test_acknowledged_alert_is_flagged(self):
        a = self.alerts([("2026-11-05", 29, 50)], acked=["frost:2026-11-05"])
        self.assertTrue(a[0]["acked"])

    def test_model_forecast_to_alert_and_ack(self):
        m = make(self.TODAY)
        gid = m.add_garden("Beds")
        m.add_variety(gid, "tomato", "Sungold", 3)
        m.set_forecast(fc(("2026-11-05", 28, 49), ("2026-11-06", 33, 55)), "test")
        a = m.snapshot()["alerts"]
        self.assertEqual([x["kind"] for x in a], ["frost"])
        self.assertEqual(a[0]["plants"][0]["count"], 3)
        m.ack_alert(a[0]["id"])
        self.assertTrue(m.snapshot()["alerts"][0]["acked"])

    def test_plants_not_in_a_garden_bed_are_ignored(self):
        m = make(self.TODAY)
        rack = m.add_garden("Rack", kind="rack")
        m.add_variety(rack, "tomato", "Sungold", 3)
        m.set_forecast(fc(("2026-11-05", 20, 49)), "test")
        self.assertEqual(m.snapshot()["alerts"], [])


class YearInReview(unittest.TestCase):
    def test_totals_compare_to_last_year_and_find_the_drop(self):
        m = make(date(2026, 11, 5))
        a = m.add_garden("Back Garden")
        b = m.add_garden("Raised bed")
        t = m.add_variety(a, "tomato", "Sungold", 2)
        p = m.add_variety(b, "pepper", "Jalapeno", 2)
        m.log_harvest(t, 100, "2025-08-01")
        m.log_harvest(p, 40, "2025-08-10")
        m.log_harvest(t, 120, "2026-08-01")
        m.log_harvest(p, 20, "2026-08-10")
        m.log_spray(t, "Neem", "2026-06-01")
        y = m.snapshot()["years"]
        self.assertEqual(list(y), ["2026", "2025"])
        self.assertEqual(y["2026"]["lbs"], 140.0)
        self.assertEqual(y["2026"]["prev_lbs"], 140.0)
        self.assertEqual(y["2026"]["change_pct"], 0)
        self.assertEqual(y["2026"]["drop"], {"name": "Pepper", "pct": -50})
        self.assertEqual(y["2026"]["best_garden"]["name"], "Back Garden")
        self.assertEqual(y["2026"]["sprays"], 1)
        self.assertEqual(y["2026"]["crops"][0]["name"], "Tomato")

    def test_a_year_still_in_progress_is_not_compared(self):
        m = make(date(2026, 6, 1))
        g = m.add_garden("Back Garden")
        t = m.add_variety(g, "tomato", "Sungold", 2)
        m.log_harvest(t, 100, "2025-08-01")
        m.log_harvest(t, 5, "2026-05-20")
        y = m.snapshot()["years"]["2026"]
        self.assertTrue(y["in_progress"])
        self.assertIsNone(y["change_pct"])
        self.assertIsNone(y["drop"])
