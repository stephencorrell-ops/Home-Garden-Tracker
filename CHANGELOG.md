# Changelog

All notable changes to Garden Tracker. Newest first.

After updating in HACS, restart Home Assistant and refresh your dashboard (close and reopen the app on a phone or tablet) so the new card loads.

## 0.12.0 - 2026-10-22

### Added
- Two new kinds of place besides gardens: a **seedling rack** and a **greenhouse**. Add them with "+ Location" on the main page. They don't have soil, pH, EC, fertilizer or cover crops. Each tracks:
  - Air temperature from one or more Home Assistant sensors (averaged) or manual readings, with daily lows and highs and a chart. The seedling rack can also track light (PAR) from a sensor.
  - Watering: a "Water" button, days since last watered, and an optional "water every N days" reminder that shows Water now. A "Days since watered" sensor for each place.
  - How many 10x20 trays are in use, with minus and plus buttons, and a "10x20 trays in use" sensor.
  - A "Sensors out" button for each sensor type, the same as on gardens.
- **Moving plants.** Plants in the rack or greenhouse have Move and Up-pot buttons on their card. Move takes a number of plants, so half a tray can go now and the rest later (the rest stay as their own planting). Moving into a garden marks them as in the ground and warns if a cover crop is still growing or waiting there. Each planting keeps a history of where it has been.
- **Pot and tray sizes** for seedlings: 6-cell tray, 4-cell tray, 3.3 in pot and 5 in pot, or type your own. Set it when you add a plant, change it by up-potting (which logs the date) or in the plant's Edit form. Pot sizes are hidden once plants are in a garden.
- **Greenhouse thermostat.** A greenhouse gets a Home Assistant climate entity with a heat set point and a cool set point, so it works with the standard thermostat card. You choose its heaters and coolers (switches, fans, input booleans or climate devices). Garden Tracker turns heaters on below the heat set point and coolers on above the cool set point, and turns them off 1 degree past it, checking on every temperature change and once a minute. Turning control off switches the devices off. If the temperature sensors stop reporting or are set to Sensors out, everything is switched off. The set points must be at least 3 degrees apart and a device can't be both a heater and a cooler.
- New services: set_trays, log_watering, set_water_interval, move_plants, up_pot and set_greenhouse_climate. add_garden takes a kind, and add_variety and update_variety take a container.

### Changed
- "Add garden" is now "Add location". Existing gardens are unchanged.

## 0.11.0 - 2026-10-22

### Added
- Seed amount (pounds) for each cover crop, in the Add cover crop and Edit forms. When two or more crops with amounts are in the ground together, Garden Tracker shows the mix ratio, for example "10 lb Winter rye (67%), 5 lb Snow peas (33%)", on the main Garden page card and at the top of the garden's cover crop card. Each crop also shows its share of the mix. Amounts are optional; set one to 0 in Edit to clear it.
- The add_cover_crop and edit_entry services accept amount_lbs.

## 0.10.1 - 2026-10-22

### Changed
- The main Garden page now shows one cover crop card per garden, named after the mix (for example "Winter rye + Snow peas"), instead of a card for each crop. It shows the oldest sown date and days in the ground, and a "Terminate all" button that terminates every growing crop in the mix with one date and method. If part of the mix has been terminated, the card says which. The garden page still lists each crop separately.

## 0.10.0 - 2026-10-22

### Added
- Cover crops now show on the main Garden page, under each garden's plants. Each card shows the crop, whether it is growing (with days in the ground and the sown date) or in its waiting period (days until you can plant and the ready date), and a Terminate button while it is growing. Tap a card to open the garden. Finished cover crops are hidden here but stay in the garden's history. The cards are hidden when you filter by spray due, harvest hold or on track.

## 0.9.2 - 2026-10-22

### Added
- The Soil temperature card has its own "Sensors out" / "Resume sensors" button, so the temperature probe can be pulled without stopping moisture and EC, and the other way around. The Moisture and fertility card's button now only covers moisture and EC. If you already pressed the old single button, it is carried over to all three.
- The set_soil_sensors_paused service takes a group: moisture_ec, soil_temp or all.

## 0.9.1 - 2026-10-22

### Fixed
- The Moisture and fertility card said "No EC readings yet" above a current EC reading whenever feeding advice was hidden. It now only says that when there really is no EC reading.

## 0.9.0 - 2026-10-22

### Added
- A "Sensors out" button on each garden's Moisture and fertility card for when you pull the soil probes out of the ground. While it is on, new moisture, EC and soil temperature readings from the sensors are ignored, so a probe lying on the surface does not log false data. The card shows the last readings with a notice, and feeding advice is hidden. Tap "Resume sensors" to start logging again; the current sensor values are read straight away. Manual readings still work, and soil pH is not affected.
- A set_soil_sensors_paused service for the same switch.

## 0.8.2 - 2026-10-22

### Changed
- While a cover crop is growing in a garden, the feed, hold and check-again advice is hidden and the "Soil fertility" sensor shows unavailable. Moisture and EC are still logged and charted. The advice returns when the cover crop is terminated.

## 0.8.1 - 2026-10-22

### Fixed
- Soil pH is now shown to two decimals. A reading of 7.15 was saved correctly but displayed as 7.2. The latest reading, the change since your first reading and the log entries all show the full value, and the pH form and sensor accept two decimals.

## 0.8.0 - 2026-10-22

### Added
- Soil moisture and EC now share one "Moisture and fertility" card on the garden page, with both readings, one chart (EC solid, moisture dashed, healthy EC range shaded) and buttons for logging and picking sensors for each.
- Feeding advice from soil EC read together with moisture: no feeding needed, consider feeding, hold off, or check again later. EC reads high in dry soil and low in wet soil, so a reading outside your moisture range is flagged to recheck instead of acted on.
- Garden settings for the healthy EC range (default 0.8 to 1.8 mS/cm), the moisture range where EC is trusted (default 25 to 60%) and the probe depth in inches (default 4). The card is labeled with the probe depth.
- Shows how EC has changed over two weeks and the last date a plant in the garden was fed.
- A "Soil fertility" sensor for each garden (ok, feed, hold or recheck) with the advice and readings as attributes, for automations and notifications.
- The update_garden service accepts ec_min, ec_max, moisture_min, moisture_max and probe_depth.

## 0.7.1 - 2026-10-21

### Fixed
- Soil EC sensors that report in µS/cm without a unit (for example 1200) were silently ignored because the value looked too large. These are now read as µS/cm and converted to mS/cm. Sensors reporting mS/m are converted too.
- When a soil sensor reading is rejected as out of range, Home Assistant now logs a warning naming the sensor, so you can see why nothing was recorded.

## 0.7.0 - 2026-10-20

### Added
- A picture for every built-in plant type: apple, pear, Asian pear, cherry, nectarine, peach, pawpaw, jujube, tomato, pepper, jalapeño, habanero, cucumber, beans, peas, watermelon, cantaloupe, pumpkin, cabbage, lettuce, cauliflower, garlic, onion, carrot, potato and horseradish. Anything else gets a generic sprout.
- New plant types: peach, jujube, jalapeño, habanero, beans, peas, watermelon, cantaloupe, pumpkin, cabbage, lettuce, cauliflower.
- Onion types: red, white and sweet, each with its own picture. The original onion is now labeled "Onion (yellow)" and keeps its existing plantings.

### Changed
- Cabbage, cauliflower and all onion types finish when harvested (like carrots and garlic). Lettuce does not. Switch either way in a plant's Edit form.
- Jalapeño and habanero use the pepper feeding stages.

## 0.6.1 - 2026-10-20

### Changed
- Horseradish harvest date is now 3 weeks after the first fall frost in the second year, instead of a flat 730 days. It follows the garden's first fall frost date. A manual date or days-to-harvest overrides it.

### Added
- The README has an install button that opens the repository in your own Home Assistant, plus a feature overview.
- A GitHub release is now published automatically whenever the version changes, so HACS can show real version numbers and update notifications.

## 0.6.0 - 2026-10-20

### Added
- Horseradish plant type with a countdown in years, months and days, for example "1 year 3 months 6 days". Any plant can switch this on in its Edit form.
- Frost countdowns for each garden: days to the last spring frost until it passes, then days to the first fall frost. The default dates are Ephrata, WA averages (Apr 25 and Oct 15). Set your own for one garden or all gardens in the garden's settings.
- A "days until expected frost" sensor for each garden.

## 0.5.0 - 2026-10-20

### Added
- Crops that are pulled when harvested (carrot, onion, garlic, potato, horseradish) end automatically when harvested. You say how many plants you pulled, the pounds are split across those plants, and when the last ones are pulled the planting moves to Past plants.
- A "Pulled when harvested?" switch in Add plant (for other types) and in a plant's Edit form.

### Changed
- Deleting a harvest that ended plants puts those plants back, and Undo reapplies it.

## 0.4.1 - 2026-10-20

### Added
- End season on each garden: moves all of its vegetable plantings to Past plants in one step, keeps their history, and can start a cover crop at the same time. Trees stay.

## 0.4.0 - 2026-10-20

### Added
- Winter cover crops on each garden (winter rye, cereal rye, hairy vetch, winter wheat, Austrian winter peas, crimson clover, snow peas, or your own): days in the ground, a Terminate button with the method used, and a countdown for the wait (3 weeks by default) before garden plants can go in.
- A warning in Add plant while a cover crop is growing or in its waiting period.
- A "days until planting after cover crop" sensor for each garden.

## 0.3.2 - 2026-10-20

### Fixed
- New cards from the card picker start at full width.

## 0.3.1 - 2026-10-20

### Added
- The card asks for full width on sections dashboards.
- A sprout icon for HACS and Home Assistant (needs Home Assistant 2026.3 or newer).

### Fixed
- The card could appear twice in the card picker when its script was loaded more than once.

## 0.3.0 - 2026-10-20

### Added
- Soil moisture, soil EC and soil temperature for each garden. Pick one or several Home Assistant sensors (their average is used) or log readings by hand. Daily lows and highs are tracked and charted.
- A soil temperature planting guide based on the average of the last three nightly lows.
- "Log something else" for adjuncts: type whatever your soil needs and it is added to the list.
- Sensors for soil moisture, EC and temperature.

## 0.2.1 - 2026-10-20

### Added
- Large plantings (more than 6 plants, such as 180 garlic) show as one summary instead of a list of every plant.
- Mark lost: record how many plants died or were pulled early, with a reason, and restore them if you made a mistake.
- Garlic plant type.

### Changed
- Plant sensors no longer list every plant, which keeps them under Home Assistant's attribute size limit.

## 0.2.0 - 2026-10-20

First release.
- Gardens with soil pH (sensor or manual) and adjunct tracking (sulfur, humic acid, compost, gypsum, micros).
- Plant records with plant counts, days to harvest, projected harvest from past seasons, and harvests split across living plants.
- Dead or pulled plants with a reason, Past plants, and Plant again.
- Orchard trees with spray, pre-harvest and degree-day tracking.
- Fertilizer logging with N, P and K, and edit or remove for every log entry.
- A visual Lovelace card and services for everything the card does.
