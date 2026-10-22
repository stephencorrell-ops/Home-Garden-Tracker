# Changelog

All notable changes to Garden Tracker. Newest first.

After updating in HACS, restart Home Assistant and refresh your dashboard (close and reopen the app on a phone or tablet) so the new card loads.

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
