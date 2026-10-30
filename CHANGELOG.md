# Changelog

All notable changes to Garden Tracker. Newest first.

After updating in HACS, restart Home Assistant and refresh your dashboard (close and reopen the app on a phone or tablet) so the new card loads.

## 0.31.5 - 2026-10-30

- **Microclimate sensors no longer vanish after a restart.** Home Assistant removed the Microclimate device every time it started, so the zone, frost, temperature, rain, humidity, sun and air sensors were missing until you next changed something, and any names or areas you gave them were lost.
- **The temperature alarm sensor now appears when you turn it on.** On a rack or greenhouse that already had the sensor offline alarm, turning on the temperature alarm later did not add its sensor until Home Assistant restarted.
- **The thermostat says idle while the heater rests** after its maximum run time, instead of off.
- **A rejected edit changes nothing.** Editing a log entry with one bad value (such as negative pounds) showed an error but still kept the other changes, like a new date.
- **Web app: weather stays with the right place.** Weather that was still downloading when you restored a backup or picked a new location is no longer saved to it, and the new place's weather is fetched after.
- **Web app: your last change is saved when you leave.** Changes are saved when the page closes or goes to the background, and a banner asks you to back up if the browser fails to save.

## 0.31.5 - 2026-10-30

- **Fix a plant in the wrong garden.** The Edit form has a "Where it is" field listing every garden, rack and greenhouse (trees also get "No garden"). It only corrects where the plant shows. It adds nothing to its move history and does not split the planting. The Move button is still there for a real move.

## 0.31.4 - 2026-10-30

- **Pruning reminder no longer runs all year.** It was due from February until you logged a pruning, so trees in full leaf still said "Due now" in the fall. It now runs from the prune month through two months after it (February to April, or March to May for walnuts), then waits for next year and shows the next reminder date. Logging "Pruned" or "No pruning needed" still clears it for the year.

## 0.31.3 - 2026-10-30

- **Frost info moved to Microclimate.** The frost banners no longer appear on the home list or the garden pages. The next frost, or what your sensors recorded this year, is one line at the top of the Microclimate page, since every garden at your address shares the same frost dates. The "Frost dates" option in View is gone.

## 0.31.2 - 2026-10-30

- **Clearer zone card.** Microclimate shows "Your zone", based on N winters of readings with the average yearly low, above the "Official USDA zone". A line says whether your garden runs warmer or colder than the USDA map. The frost year table now sits inside the same card, and the other sections start folded.
- **Fixed the Microclimate header** overlapping on narrow screens in the web app.

## 0.31.1 - 2026-10-30

- **Microclimate is a chip.** The card at the bottom of the home list is now one chip in the top row, with your hardiness zone on it.
- **Microclimate page opens on a summary.** Zone, expected last and first frost, soil temperature and rain this week sit at the top. Frost by year, soil, high and low, rain, air quality, humidity and sun fold underneath, each with a one-line peek. The sections you open are remembered.
- **Cover crops are one line** in the compact list instead of a full card.

## 0.31.0 - 2026-10-30

- **Shorter plant list.** The home list has All, Trees and Plants tabs when you have both. In compact mode, plants with something due get a card under Needs attention, and everything else is one line each. View lets you switch back to full cards. Tree ages show in whole years.
- **Spray countdown.** A spray 7 days or less away shows its countdown, the likely date and a range, built from the last 3, 7 and 14 days of warmth. Once the window opens the card says Now until you log a spray. The plant page shows the same projection.
- **Codling moth without traps** (apple, pear, Asian pear). Degree days count from January 1. Spray at 425 and again 10 days later, no spraying from 925 to 1,400, then spray at 1,400 and again 10 days later. If you log a first trap catch, the count restarts from it.
- **Peaches, nectarines and apricots.** Peach leaf curl alerts for peaches and nectarines (Nov 20 to Dec 15, and Feb 1 to Feb 28). Peach twig borer alerts for all three (delayed dormant Mar 1 to Mar 24, bloom Mar 25 to Apr 20). A matching logged spray clears a window. Each pest gets its own Home Assistant sensor.
- **Searchable plant and crop pickers.** The Type field when adding a plant and the layout planner's crop picker both search as you type. Built-in trees are named "X tree", and the walnuts are "Walnut tree, black" and "Walnut tree, English".

## 0.30.1 - 2026-10-29

- **Dates can always be picked.** Date fields (expected harvest, planting date and the rest) are now Month, Day and Year dropdowns. Before, some phones only let you change the month and year, so the day stayed on today's date.

## 0.30.0 - 2026-10-29

- **Search when adding a plant.** The Type field is now a search box: type a few letters and pick from the matches.
- **Search the layout crop picker.** "Plan a crop" in the layout planner works the same way.
- **Trees are named "X tree".** Cherry tree, Apple tree, Peach tree and so on, with the walnuts as "Walnut tree, black" and "Walnut tree, English". Plants you already added show the new names.

## 0.29.0 - 2026-10-29

### Added
- **Plant this layout.** The layout planner's new "Plant this layout" card turns the planted rows into tracked plantings: one per crop (and variety), with the number of plants the layout holds, a planting date, seed or starts, and a note of which rows. Sections already turned into plantings are skipped, so you can run it again after adding more rows. New `plant_layout` service.

## 0.28.1 - 2026-10-29

### Fixed
- **Adding a tree with "No garden" in Home Assistant** failed with "required key not provided at 'garden'", because the card dropped the empty garden before sending it. The card now sends it, and `garden` (add_variety) and `to` (move_plants) default to empty in the service schemas.

## 0.28.0 - 2026-10-26

### Added
- **Remove a garden, greenhouse or seedling rack and keep its history.** Remove hides it from your list (its plants must be archived first). Its readings, waterings and plant records stay, and History has a Removed places section with a Bring back button. Sensors, heating and alarms on a removed place are switched off. New `restore_garden` service; `remove_garden` now keeps the history instead of deleting it.
- **History page.** Replaces Past plants, with a History chip on the home page. Sort by year, garden or name, and search.
- **Trees without a garden.** Pick "No garden (trees only)" when adding, moving or replanting a tree. They show under "Trees, no garden".
- **Search and sort.** A search box on the home page, in History and in a garden's plant list. Sort plants by garden, name or soonest harvest.
- **Choose what to show.** The View button hides or shows Watering, the to-do list, Cover crops, Frost dates and Weather. Saved on the device, not in your data.

## 0.27.0 - 2026-10-26

### Added
- **Venturi fertilizer injectors.** An injector is now a dosing pump (with a dilution dial) or a venturi. A venturi has no dial: it draws a fixed number of gallons an hour at the pressures going in and coming out, so you enter its suction (from the maker's chart, or measured), the pressures, the water through it and whether it is in the main line or on a bypass. The app works out the stock tank strength from what it draws, tells you when to throttle the suction valve, and warns if the pressure drop is under about 20 to 25 percent or an in-line venturi does not match the zone's flow. Acid and base tanks work with a venturi too. New `kind`, `suction_gph`, `motive_gpm`, `inlet_psi`, `outlet_psi` and `install` fields on `set_pump`.

### Changed
- The "Pump" button on the watering page is now "Injector".

## 0.26.0 - 2026-10-25

### Added
- **Web app: outside temperature from local weather.** The outside air temperature (now, and each day's low and high) comes from your location's weather. A sensor or a manual reading replaces it.
- **Web app: estimated soil temperature.** Estimated from local weather (soil at 6 cm). Log a reading and it replaces the estimate. The planting guide uses it.
- **Web app: estimated soil moisture.** Worked out from your last logged watering, the weather, the soil type (sand to clay) and whether the garden is mulched, with a "plan to water in about N days" note. A moisture reading you log replaces it.
- **Watering log for gardens.** Gardens now have a Watering card (Water now, days since, optional reminder). It can be hidden per garden when you edit the garden. New `set_watering_card` service; `log_watering` and `set_water_interval` now work on gardens.
- **Mulch setting.** New `mulch` option on `set_irrigation`, and a soil and mulch button on the garden page.

## 0.25.0 - 2026-10-25

### Added
- **Tree pruning reminders.** Every tree has a Pruning section. The reminder starts on the first of the month and stays until you mark the tree pruned or "No pruning needed this year", then starts over each January. Fruit trees start in February (the Chelan-Douglas Master Gardeners give January to March), walnuts start in March (pruned before bud break, March to April), and you can set any month per tree. Each tree keeps a pruning log, and a Pruning sensor (waiting, due, pruned, skipped) is available in Home Assistant. New services `log_pruning` and `set_prune_month`.
- **More trees.** Apricot, hazelnut (filbert), English walnut, black walnut, plum, quince, fig, persimmon, mulberry and chestnut.
- **Your own tree types are kept.** A type added with "Other..." is saved for next time, and its name and plant or tree kind can be edited. New `species_name` and `kind` fields on `update_variety`.
- **Walnut husk fly.** Walnuts track the husk fly instead of codling moth. There is no degree-day model for it, so log the date trap catches rise sharply and the app counts 10 days to spray, with malathion or spinosad bait (GF-120) from the PNW Pest Management Handbook.

## 0.24.0 - 2026-10-25

### Added
- **Cover crops can be terminated in several steps.** Tap each step in the order you do it, for example mowed, wilted, plowed, tilled. Plowed and wilted are new options. The cover crop shows the steps in order, and the Edit form has the same chips.

### Changed
- The `terminate_cover_crop` service and the cover crop edit accept a list of methods as well as a single one. Cover crops terminated before this keep their one method.

## 0.23.0 - 2026-10-25

### Changed
- **Layout planner redesign.** The plan drawing comes first. Crop names move from above the rows to a row of colour chips under the plan, so they no longer run together. Warnings have a bold headline, one short sentence and a button where there is something to do (for example "Use 48 in rows" for corn), with the full explanation in a "Why, and what to do instead" fold-out. Plan a crop, Rows and angle (with sun and shade) and Garden size are now sections that open when tapped.
- **Garden page.** Layout and Watering are two tiles side by side, and Time before frost has an amber tint.
- **Web app.** The backup notice is one slim line instead of a large banner.

## 0.22.0 - 2026-10-25

### Added
- **Recommended post spacing by growth habit.** Determinate tomatoes default to 8 ft between T-posts and indeterminate tomatoes to 4 ft, following the habit set on the variety. Climbing beans, climbing peas and vining cucumbers default to 6 ft. The Spacing form shows the recommendation, a spacing you enter replaces it, and leaving the field empty goes back to the recommended one.

### Changed
- Raspberry and blackberry trellis posts default to 20 ft apart (was 10 ft).

## 0.21.0 - 2026-10-25

### Added
- **Fall cut-back reminder for brambles.** From September to November, a garden with raspberries or blackberries planted shows a reminder at the top of its page to cut the canes that fruited this year down to the ground. The plants live for years, but each cane fruits in its second year and then dies.

## 0.20.0 - 2026-10-25

### Added
- **Berries.** Blackberries, raspberries and blueberries join the plant list, with spacing, T-post support and heights. Raspberries and blackberries join the verticillium rotation check.
- **Blueberry soil warning.** Planting blueberries in a garden with a tested or estimated pH above 5.5 shows a strong red warning, and so does planting them with no pH reading at all.

### Fixed
- Layout warnings (corn blocks, shade, blueberries) now show on their own, not only when a crop rotation alert is also showing.

## 0.19.0 - 2026-10-25

### Added
- **Rows at any angle.** The layout planner takes the angle the rows run off north (0 north-south, 90 east-west, any number between). The plan stays square to the screen with a north arrow, and a button shows the rows sideways or up and down on that screen. The size boxes are now "Row length" and "Depth".
- **Sun and shade.** From the sun's path on the 15th of each month, April to September, at your latitude: the row angle that costs the least sun, a button to turn the rows to it, and warnings when a tall crop shades a shorter one beside it, with the side to plant the tall crops on.
- **Heights.** Every crop has a full-grown height you can edit, and a variety can have its own: determinate or indeterminate tomatoes, bush or pole beans, short or tall corn, dwarf to tall hops, or any height you enter.
- **48 in rows and corn blocks.** Row width gains 48 in, and corn warns when the rows are narrower or a stretch is under 4 ft.
- **Time before frost.** For each garden, which crops can still be planted before the first frost, when each window opens, and how many quick crops fit back to back. The days to harvest and frost tolerance are editable from your seed packets, and any crop can be given a time.
- **More plants.** Corn, hops, strawberries, sweet potatoes, broccoli, kale, spinach, radish, beets, zucchini, eggplant, sunflower, basil, cilantro, parsley, dill, chives, mint, oregano, thyme, rosemary and sage. Strawberries and eggplant join the verticillium rotation check.
- New services: `set_variety_traits` takes `height_ft` and `habit`, `set_layout_crop` takes `height_ft`, `set_layout` takes any `rotation` angle and a 48 in `row_in`, and `set_crop_days` and `reset_crop_days` are new.

## 0.18.0 - 2026-10-25

### Added
- **Watering planner** for each garden (also in the web app). Drip is the default; sprinklers are the other choice. Each garden is its own irrigation zone.
- **Drip layout.** Per crop: runs of drip line, emitter flow and spacing suggested from the plants, the soil (clay is held to 1/2 gph) and the crop's weekly water, all editable. Run time is worked out from the thirstiest crop or set by you. Footage to order per line type with a 5% allowance and roll sizes, whole-garden GPM, and a warning when a line carries too much. The emitter and roll catalogue is editable data, so check it against your supplier.
- **Sprinklers.** One sprinkler moved around or fixed sprinklers; the rate comes from flow and radius or from your own catch-can measurement. It suggests the places, minutes and waterings a week to get the plants enough, with cycle and soak on soil that takes water slowly. Set up once a year in a collapsed card.
- **Weather.** The last week's lows, highs and rain from your sensors (or the web app's weather service) scale each crop's weekly water, so a hot week runs longer and a cool or rainy one shorter. It can be switched off.
- **Fertigation.** Editable injector pumps (the Dosatron D14MZ2 is the default) with tanks assigned to them, named mixes of fertilizers (a high nitrogen mix and a MasterBlend tomato mix with calcium nitrate and Epsom salt to start), feeding every 14 days. It works out the grams for each tank, the dial setting, how long to inject and the plain-water flush, the nutrient strength, and a run plan when tanks share a pump. Crops that would be over-fed get a "valve off these lines after X minutes" note.
- **Acid and base.** From the water's pH and alkalinity, how much diluted sulfuric acid to put in the stock tank for a target pH (5.5 by default), or potassium bicarbonate, sodium bicarbonate or KOH when the water is below the target. Acid and base applications are logged for each garden.
- **Lime** for low soil pH, from the garden's latest soil pH reading, with worked-in and surface limits and split applications.
- New services: `set_irrigation`, `set_sprinkler`, `set_irrigation_crop`, `reset_irrigation_crop`, `set_pump`, `remove_pump`, `set_tank_pump`, `set_fertigation`, `set_fert_mix`, `remove_fert_mix`, `set_fert_component`, `remove_fert_component`, `set_acid`, `set_lime`, `log_acid`.

## 0.17.0 - 2026-10-25

### Added
- **Layout planner** for each garden (also in the web app). Enter the garden's width and length in feet, pick a row width (24, 30 or 36 in) and an access path between rows (24 in by default, any size you like), and the garden is drawn to scale. You can turn the drawing in 90 degree steps to match how you look at the garden.
- **Crops in rows.** Tap a row and plant a crop in the whole row or in a stretch of it; a row can hold several crops, each with its own start, length, spacing and variety (5 ft of onion, 10 ft of carrot, 10 ft of beans). Each crop has a pattern: single line, double line (12 in apart, optionally staggered) or an offset grid where every plant is its plant spacing from its neighbours.
- **Supports.** Per crop: none, T-posts, cages, or a corral (stakes or T-posts on both sides with levels of twine). The totals count plants, plants per square foot, planted rows, T-posts, stakes, feet of twine, cages and area, with a table for each crop.
- **Plan a crop.** Say how much you want to harvest (with pounds per plant), how many plants, or how many feet of row, and it works out the plants, row length and expected harvest, then places it in the row and start you choose and carries on into the next rows.
- **Seasons.** "Start the next season" files this year's layout away (past years stay readable) and begins empty rows with the same settings.
- **Rotation alerts.** Planting where the same crop, or one that shares a soil disease, grew in recent years is flagged (red for the same crop, amber for a shared disease), and the row picker marks the rows to avoid. Rules are per disease, from Washington State University Extension and Cornell Vegetable MD Online.
- **Varieties and disease resistance.** Enter what a variety resists from its seed packet (V, F, N, A and so on) and the wait shortens: Roma VF after tomato needs 2 years instead of 3. No variety resistances come preloaded.
- New services: `set_layout`, `assign_layout_rows`, `add_layout_segment`, `remove_layout_segment`, `set_layout_crop`, `set_layout_draft`, `place_layout_draft`, `start_layout_season`, `set_variety_traits`, `remove_variety_traits`, `remove_layout`.

## 0.16.0 - 2026-10-24

### Added
- **A web app for people without Home Assistant** (in the `web` folder, published to GitHub Pages). It is the same card and the same garden logic, running in the browser, and you can install it on a phone from the browser's menu. It works offline after the first load and saves in the browser. **Back up** saves a file with all your data and **Restore** puts it back, in case the browser clears its storage. It reminds you to back up every 14 days. You set your location and it fills in daily temperatures and rain for the last ten years from Open-Meteo, so frost dates, your zone, the planting guide and degree days work with no sensors. Greenhouse and rack controls, alarms and power tracking are left out, because they need Home Assistant devices.

### Changed
- The garden logic now lives in `custom_components/garden_tracker/core`, plain Python with no Home Assistant code, with its own tests (`python -m unittest discover -s tests -t .`). Adding a location now needs a name.

## 0.15.0 - 2026-10-24

### Added
- **Microclimate** page, opened from a tile on the main page. It works from your own sensors and shows: your **local hardiness zone** (the average of each winter's lowest temperature, with what USDA says beside it, which you can edit), **recorded last spring and first fall frost** for each year next to the expected dates, **expected against actual soil temperature** (expected is the last 10 days of outside air temperature), **high and low** for today, the week, the month and the year, and **rainfall** for today, the week, the month and the year. Frost and temperatures come from your outside temperature sensor and are filled in from Home Assistant's long-term statistics when it starts, so history is there on day one. In the page's Settings you can pick **several sensors for each kind** and they are averaged: extra outside temperature sensors (added to your main one), rainfall totals (sensors that count up through the day, week or year), **humidity** and **solar radiation in W/m²**. **Air quality** shows PM1, PM2.5, PM10, NOx and VOC from your outside air sensors (a SEN65, say): all on one graph (particles on the left scale, NOx and VOC on the right): 15 minute averages for the last day, hourly averages for the last week, daily averages for the last month, and the highest reading for each day, today, this week and this month. The last 35 days are filled in from Home Assistant's history, and there is a "highest today" sensor for each. Humidity gets high and low, and the sun gets average W/m² (over the whole 24 hours) and energy in kWh/m², for today, the week, the month and the year. Recorded frost dates also show on each garden's frost banner and as attributes on its frost sensor. A zone needs a full winter of readings. Frost counts at 32°F or colder, which you can change. Home Assistant gets a Microclimate device with zone, frost dates, expected soil temperature, and rain, high and low, humidity and sun sensors, plus a `set_microclimate` service.
- **Outside temperature** for every garden and greenhouse. Each has an "Outside temperature" card with the current reading, today's low and high and a chart. Tap Sensors to pick the outdoor sensors for that place (several are averaged), or leave it empty and the place uses your main outdoor temperature sensor from the integration's settings (a weather entity works too). Log reading, Sensors out and the "Outside" figure on the greenhouse's card on the main page work like the other temperatures. Home Assistant gets an "Outside temperature" sensor for each.

### Changed
- **Soil and outside temperature share one graph** on a garden's page: both current readings side by side, one chart with the soil line and the outside air line (each with its daily low-to-high band), the planting guide, and Log reading, Sensors and Sensors out for each. A **Week / 24 hours** switch on the chart shows either the last seven days or the last 24 hours. The 24 hour view uses readings Garden Tracker now keeps every 15 minutes (for eight days, for soil, outside and greenhouse air temperature), so it fills in over the first day after you update.
- **No feeding advice in the off season.** From each garden's first expected fall frost until after its last expected spring frost, the garden's Moisture and fertility card no longer says "Consider feeding", "Hold off feeding" or "No feeding needed", the "Soil fertility" sensor reads unavailable, and plants in that garden don't show their fertilizer plan. You still see the EC and moisture readings and the chart, and you can still log a feeding. It uses the frost dates set for that garden (Oct 15 to Apr 25 by default), and it comes back on its own after the spring date. Seedling racks and greenhouses are not affected.
- **The planting guide now drops crops that can't finish before the first fall frost.** Each group of crops in the "Planting guide" on a garden's soil temperature card shows only while there are enough days left before that garden's first frost date for the crop to grow (for example 50 days for peas, 75 for carrots, 85 for melons). Once none fit, which is the case from early September, the guide is hidden for the rest of the year. On January 1 it comes back, counting toward next fall's frost.
- Logging a reading or choosing sensors for a kind of measurement a place doesn't track (soil moisture on a greenhouse, say) now gives a clear message instead of being saved silently.

## 0.14.0 - 2026-10-22

### Added
- **Heat mats, fans and grow lights on the seedling rack.** Open the rack and tap Set up under "Heat mats, fans and lights".
  - **Heat mats** come on when the air is below a set point, and **fans** come on when it is above another, the same way the greenhouse thermostat works. A rack starts with 70°F and 82°F. The fans are your cooling: if the rack gets too warm they run, even between scheduled runs.
  - **Light schedule.** Pick your grow lights (switches or lights), the time they come on and how many hours a day, for example on at 6:00 AM for 16 hours, off for 8. The lights follow the clock every minute, so they also come back on correctly after a restart.
  - **Fan schedule.** Run the fans for a few minutes every so many hours, for example 5 minutes every 6 hours. On the rack the cycle is counted from the time the lights come on, and you can limit the scheduled runs to while the lights are on. Schedules work even when the thermostat is off.
  - The rack's page and its card on the main page show whether the lights are on and when the fans are running. Home Assistant gets a climate device for the rack too.
- **Heat dead zone.** "Heat off at" sets the temperature the heaters (or the rack's heat mats) switch off at, so 60 on and 65 off gives a five degree dead zone. Leave it empty and they switch off one degree above the on point, as before. It works together with the heater minimum and maximum run times. Your existing settings are unchanged.
- **Fan dead zone and minimum run time** for the greenhouse and the rack. "Fans off at" sets the temperature the fans switch off at, so 90 on and 85 off gives a five degree dead zone. Leave it empty and they switch off one degree below the on point, as before. "Fan minimum run" keeps the fans on for at least that long once they start for heat, so they don't cycle quickly (it never holds them on once the air is cold enough to need heat). Either one or both can be used. Your existing settings are unchanged.
- **Fan schedule in the greenhouse.** The same "5 minutes every 6 hours" fan schedule, counted from midnight.

### Changed
- In the greenhouse, "Cooling" is now **Fans** everywhere: the set point reads "Fans on above", the device list is "Fans", and the power use split says Fans. Your existing settings and power history carry over unchanged.
- The set_greenhouse_climate service also works for a seedling rack, and takes lights, light_sched, light_on, light_hours, fan_sched, fan_minutes, fan_every and fan_lights_only. The Home Assistant thermostat device's "coolers" attribute is now called "fans".

## 0.13.0 - 2026-10-22

### Added
- **Temperature alarm** for a seedling rack and a greenhouse. Open the place and tap Set limits under Temperature alarm to choose a high limit, a low limit, or both.
  - When the air goes past a limit, a red warning appears on the place's page and on the main page (even if the place is empty). It says how long the air has been out of range, since when, and the highest or lowest it reached.
  - The warning stays until you tap **Acknowledge**, even after the temperature has come back, so you can see what happened while you were away. If it went out of range more than once before you looked, it tells you how many times and for how long in all.
  - If you acknowledge while it is still too hot or too cold, it stays quiet and only warns again after the air has been back in range.
  - The **Turn off** button switches the alarm off completely and clears any warning. It won't come back until you turn it on again.
  - When the alarm is on, Home Assistant gets a "Temperature alarm" sensor for that place (on while a warning is waiting to be acknowledged), so you can send yourself a notification. A reading that stops coming in never clears or starts an alarm.
- **Sensor offline alarm** for every place (gardens, seedling racks and greenhouses). If a sensor that is in use reports no value (unavailable, unknown, missing or not a number) for more than an hour, a warning shows on the main page and on that place's page, naming the sensor, what it measures, and how long it has been offline.
  - It stays until you tap **Acknowledge**, even if the sensor has come back, and then says how long it was out. If it dropped out more than once before you looked, it tells you how many times and for how long in all.
  - Sensors you have marked as out (Sensors out) are ignored, and so is a sensor you remove. A gap shorter than an hour never raises a warning.
  - Each place has a "Sensor offline alarm" card with a **Turn off** button. It is on by default. Turning it off clears any warning and it won't come back until you turn it on again.
  - When it is on and the place has sensors, Home Assistant gets a "Sensor offline alarm" sensor for that place.
- New services: set_temp_alarm, ack_temp_alarm, set_sensor_alarm and ack_sensor_alarm.

## 0.12.1 - 2026-10-22

### Changed
- A seedling rack or greenhouse with no plants in it is no longer shown on the main page. Its button at the top still opens it, and it appears on the main page as soon as you move or add a plant to it.

## 0.12.0 - 2026-10-22

### Added
- Two new kinds of place besides gardens: a **seedling rack** and a **greenhouse**. Add them with "+ Location" on the main page. They don't have soil, pH, EC, fertilizer or cover crops. Each tracks:
  - Air temperature from one or more Home Assistant sensors (averaged) or manual readings, with daily lows and highs and a chart. The seedling rack can also track light (PAR) from a sensor.
  - Watering: a "Water" button, days since last watered, and an optional "water every N days" reminder that shows Water now. A "Days since watered" sensor for each place.
  - How many 10x20 trays are in use, with minus and plus buttons, and a "10x20 trays in use" sensor.
  - A "Sensors out" button for each sensor type, the same as on gardens.
- **Moving plants.** Plants in the rack or greenhouse have Move and Up-pot buttons on their card. Move takes a number of plants, so half a tray can go now and the rest later (the rest stay as their own planting). Moving into a garden marks them as in the ground and warns if a cover crop is still growing or waiting there. Each planting keeps a history of where it has been.
- **Pot and tray sizes** for seedlings: 6-cell tray, 4-cell tray, 3.3 in pot and 5 in pot, or type your own. Set it when you add a plant, change it by up-potting (which logs the date) or in the plant's Edit form. Pot sizes are hidden once plants are in a garden.
- **Power use by day and month.** On a greenhouse (heating and cooling) or seedling rack (lights and power), pick energy sensors (kWh, Wh) or power sensors (W, kW) in the place's Edit form. A Power use card then shows kWh today, this month, a 30 day chart, previous months, and the split between heating and cooling. Garden Tracker adds up the readings once a minute and keeps about 18 months of days. A meter that resets to zero is handled. If you don't choose any sensors, the card is not shown at all. "Energy today" and "Energy this month" sensors are added for Home Assistant too, only when sensors are chosen.
- **Dollar cost of power use.** Tap "Set rate" on the Power use card and enter your price in cents per kWh (for example 5.15). The card then shows dollars for today and this month (kWh in smaller print), the cost of heating and cooling separately, each previous month, and the cost of each day when you touch its bar. "Energy cost today" and "Energy cost this month" sensors are added for Home Assistant, in your Home Assistant currency. One rate is used everywhere and applies to past days too, so changing it re-prices history. Without a rate the card shows kWh only.
- **How many trays your plants fill.** Garden Tracker knows how many of each Bootstrap Farmer size fit in one 10x20 tray (72 six-cell, 32 four-cell, 18 of the 3.3 in pots, 8 of the 5 in pots) and shows "Your plants fill about N trays" with a Use N button to set the tray count.
- **Greenhouse thermostat.** A greenhouse gets a Home Assistant climate entity with a heat set point and a cool set point, so it works with the standard thermostat card. You choose its heaters and coolers (switches, fans, input booleans or climate devices). Garden Tracker turns heaters on below the heat set point and coolers on above the cool set point, and turns them off 1 degree past it, checking on every temperature change and once a minute. Turning control off switches the devices off. If the temperature sensors stop reporting or are set to Sensors out, everything is switched off. The set points must be at least 3 degrees apart and a device can't be both a heater and a cooler.
- New services: set_trays, log_watering, set_water_interval, move_plants, up_pot and set_greenhouse_climate (with heat_min_run, heat_max_run and heat_rest) set_power_sensors and set_power_rate. add_garden takes a kind, and add_variety and update_variety take a container.

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
