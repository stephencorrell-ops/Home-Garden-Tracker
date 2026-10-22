# Garden Tracker for Home Assistant

Track gardens, plant varieties, orchard trees, harvests, soil adjuncts, soil pH, sprays, and
insect degree days, with a visual Lovelace card.

## Install with HACS

[![Open your Home Assistant instance and open this repository in the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=stephencorrell-ops&repository=Home-Garden-Tracker&category=integration)

Tap the button above to open this repository in your own Home Assistant (it asks for your Home Assistant address the first time), then choose **Download**. Or add it by hand:

1. HACS > three dots > **Custom repositories** > add `https://github.com/stephencorrell-ops/Home-Garden-Tracker`, category **Integration**.
2. Install **Garden Tracker**, then restart Home Assistant.
3. Settings > Devices & services > **Add integration** > Garden Tracker, and pick your outdoor temperature sensor or weather entity (used for degree days).
4. Edit a dashboard, add a card, and choose **Garden Tracker** (or add `type: custom:garden-tracker-card`). The card file is served and loaded by the integration, so there is no resource to add by hand.

Optional card option: `garden: Raised beds` limits the card to one garden.

## What it tracks
- Gardens with soil pH, moisture, EC and soil temperature (one or several Home Assistant sensors, averaged, or manual entries) with daily lows and highs, plus a soil temperature planting guide.
- Soil adjuncts (sulfur, humic acid, compost, gypsum, micros, or anything you type in).
- Plant varieties with plant counts, harvests split across living plants, large plantings (like 180 garlic) shown as one summary, and root crops that finish when harvested.
- Slow crops such as horseradish with a years, months and days countdown.
- Orchard trees with spray, pre-harvest and degree-day tracking.
- Winter cover crops with days in the ground, termination, and a 3 week wait before planting.
- Frost countdowns (last spring frost, then first fall frost) with dates you set for your area.
- A seedling rack and a greenhouse for starting seeds: air temperature (and light on the rack), watering with days since and an optional reminder, 10x20 trays in use, pot and tray sizes with up-potting, and moving a number of plants from the rack to the greenhouse to the garden.
- A greenhouse and seedling rack thermostat that holds the air between a heat and a fan set point by switching your heaters (or heat mats) and fans, with a grow light schedule and a fan schedule, with minimum and maximum heater run times. Power use by day and month, with dollars from your electricity rate, when you pick energy or power sensors. A temperature alarm for a rack or greenhouse that stays until you acknowledge it and says how long the air was out of range. A warning when any sensor in use goes an hour with no reading.
- End of season: archive a whole garden's plantings at once and keep the history for next year.

## Concepts
- **Garden**: a bed or area. Holds soil adjuncts (sulfur, humic acid, compost, gypsum, micros, plus your own) and soil pH history (sensor or manual). Plants in a garden show its adjunct dates.
- **Plant record (variety)**: one per variety, such as Sungold or Thunderbird, with a plant count. Each individual plant tracks its own harvest total and status (alive, dead, pulled early with a reason).
- **Harvest**: log pounds for the variety. It is split evenly across living plants and accumulates per plant. Dead or pulled plants keep what they already produced and receive no later picks.
- **Trees**: age in years, spray and pre-harvest tracking, degree-day progress. No fertilizing schedule (feeding can still be logged).
- **Pull plant**: archives a plant and keeps its history. **Plant again** copies it into a new season, and past seasons feed the projected harvest date and yield.
- **Logs**: every entry can be edited (pencil) or removed (trash, with Undo).

## Services
Everything the card does is a service, so automations can use it: `add_garden`, `add_variety`, `log_harvest`, `log_fertilizer` (with N, P, K), `log_spray`, `log_adjunct`, `log_ph`, `set_plant_status`, `archive_plant`, `plant_again`, `edit_entry`, `delete_entry`, `undo_delete`, `add_species`, and more. See Developer tools > Actions.

## Sensors
Each garden and active plant record becomes a device: harvest total, plants alive, days to expected harvest, days since planted, in ground, or fertilized, tree age, days since spray, next spray, days until safe to harvest, degree days per pest, soil pH, soil moisture, EC and temperature, days until the next expected frost, days until planting after a cover crop, and days since each adjunct.

## Notes and limits
- Degree days are built from daily highs and lows recorded from your temperature source, starting when the integration is installed (average method with horizontal cutoffs, degrees F). Projections that use degree days need a full season of recorded data first, and fall back to calendar dates until then.
- `species.json` thresholds and feeding focus are **starter values**. Check them against your extension service and the product label. Pre-harvest and reapply intervals always come from you, per label.
- Projected harvest dates need at least one past season of logged harvests for that variety.
