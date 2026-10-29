"""Opens the web app in a real browser and checks the main paths: add a garden, back up, lose the data, restore,
and fill in local weather. Run from the repo root: python -m tests.web_e2e [--pyodide]

By default the page talks to the Python core through a test server. With --pyodide it runs the core in the browser
exactly as users get it (needs web/dist built with Pyodide)."""
import json
import sys
import tempfile
import threading
from datetime import date, timedelta
from pathlib import Path

from playwright.sync_api import sync_playwright

from tests.web_server import serve

ROOT = Path(__file__).resolve().parents[1]
DIST = ROOT / "web" / "dist"
SHOTS = Path(sys.argv[sys.argv.index("--shots") + 1]) if "--shots" in sys.argv else None
PYODIDE = "--pyodide" in sys.argv


def weather_json(today: date, years=4):
    days, lo, hi, rain = [], [], [], []
    d = today - timedelta(days=365 * years)
    import math
    while d < today:
        doy = d.timetuple().tm_yday
        mean = 52 - 26 * math.cos((doy - 15) / 365 * 6.2832)
        l, h = mean - 9, mean + 9
        if d.month == 1 and d.day in (14, 15, 16):
            l -= 14
        days.append(d.isoformat()); lo.append(round(l, 1)); hi.append(round(h, 1)); rain.append(0.2 if d.day % 4 == 0 else 0.0)
        d += timedelta(days=1)
    days.append(today.isoformat()); lo.append(40.0); hi.append(61.0); rain.append(0.0)
    hours = [f"{(today - timedelta(days=n)).isoformat()}T{h:02d}:00" for n in range(3, -1, -1) for h in range(24)]
    soil = [48 + 6 * math.sin((i % 24 - 9) / 24 * 6.2832) for i in range(len(hours))]
    return {"daily": {"time": days, "temperature_2m_min": lo, "temperature_2m_max": hi, "precipitation_sum": rain},
            "current": {"temperature_2m": 55.5}, "hourly": {"time": hours, "soil_temperature_6cm": soil}}


def check(cond, msg):
    print(("ok   " if cond else "FAIL ") + msg)
    if not cond:
        check.failed = True
check.failed = False


def main():
    server = serve(str(DIST))
    port = server.server_address[1]
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}/index.html" + ("" if PYODIDE else f"?engine=http://127.0.0.1:{port}")
    today = date.today()
    with sync_playwright() as p, tempfile.TemporaryDirectory() as tmp:
        b = p.chromium.launch(executable_path="/opt/pw-browsers/chromium") if Path("/opt/pw-browsers/chromium").exists() else p.chromium.launch()
        ctx = b.new_context(viewport={"width": 430, "height": 900}, accept_downloads=True)
        pg = ctx.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))

        def route(r):
            u = r.request.url
            if "geocoding-api" in u:
                r.fulfill(json={"results": [{"name": "Ephrata", "admin1": "Washington", "country_code": "US", "latitude": 47.32, "longitude": -119.55}]})
            elif "archive-api" in u or "api.open-meteo.com" in u:
                r.fulfill(json=weather_json(today))
            else:
                r.continue_()
        ctx.route("**/*open-meteo.com/**", route)

        pg.goto(url)
        pg.wait_for_selector("garden-tracker-card")
        card = pg.locator("garden-tracker-card")
        card.get_by_text("Create your first garden").wait_for(timeout=120000 if PYODIDE else 15000)
        check(True, "app starts with an empty garden")
        card.get_by_role("button", name="Add garden").click()
        card.locator("input").first.fill("Back yard")
        card.get_by_role("button", name="Save").click() if card.get_by_role("button", name="Save").count() else card.locator("[data-act=form-submit]").click()
        card.get_by_text("Back yard").first.wait_for()
        check(True, "a garden can be added")
        pg.wait_for_timeout(600)  # let the save happen
        if SHOTS: pg.screenshot(path=str(SHOTS / "home.png"))

        # backup
        with pg.expect_download() as dl:
            pg.click("#backup")
        path = Path(tmp) / "backup.json"
        dl.value.save_as(path)
        body = json.loads(path.read_text())
        check(body["app"] == "garden-tracker" and [g["name"] for g in body["data"]["gardens"].values()] == ["Back yard"], "backup file holds the garden")
        check(dl.value.suggested_filename.startswith("garden-tracker-backup-"), "backup file is named with the date")

        # wipe the browser's storage and reload
        pg.evaluate("""() => new Promise((res) => { const r = indexedDB.deleteDatabase('garden-tracker'); r.onsuccess = r.onerror = r.onblocked = () => res(); })""")
        pg.evaluate("localStorage.clear()")
        pg.goto(url)
        card = pg.locator("garden-tracker-card")
        card.get_by_text("Create your first garden").wait_for(timeout=120000 if PYODIDE else 15000)
        check(True, "after a wipe the garden is gone")

        # restore
        pg.set_input_files("#file", str(path))
        pg.get_by_text("Restore this backup?").wait_for()
        if SHOTS: pg.screenshot(path=str(SHOTS / "restore.png"))
        pg.click("#ry")
        card.get_by_text("Back yard").first.wait_for()
        check(True, "restoring brings the garden back")

        # a file that is not a backup
        bad = Path(tmp) / "bad.txt"; bad.write_text("hello")
        pg.set_input_files("#file", str(bad))
        pg.get_by_text("isn't a Garden Tracker backup").wait_for()
        check(True, "a wrong file is refused")
        pg.click("#ok")

        # weather: set location, open the microclimate page
        card.get_by_role("button", name="Microclimate").first.click() if card.get_by_role("button", name="Microclimate").count() else card.locator("[data-act=open-micro]").click()
        card.get_by_text("Set location").first.click()
        pg.fill("#q", "Ephrata")
        pg.get_by_role("button", name="Ephrata, Washington, US").click()
        card.get_by_text("Hardiness zone").wait_for(timeout=20000)
        pg.wait_for_timeout(500)
        text = card.evaluate("el => el.shadowRoot.querySelector('ha-card').innerText")
        check("Zone" in text or "zone" in text, "microclimate page shows after location is set")
        check("Ephrata" in text, "location name shown")
        snap = pg.evaluate("window.__garden.engine.snapshot()")
        z = snap["micro"]["zone"]
        check(z["zone"] is not None and snap["micro"]["frost"]["years"], f"weather filled in zone {z['zone']} and frost years")
        if SHOTS:
            card.evaluate("el => el.scrollIntoView()")
            pg.screenshot(path=str(SHOTS / "micro.png"), full_page=True)
        mt = snap["gardens"][0]["metrics"]
        check(mt["out_temp"]["source"] == "weather" and mt["out_temp"]["current"] == 55.5, "outside temperature comes from local weather")
        check(mt["soil_temp"]["source"] == "estimated" and mt["soil_temp"]["current"] is not None, "soil temperature is estimated")
        # layout planner: size a garden, fill it with tomatoes and read the counts off the page
        card.locator("[data-act=back]").first.click()
        card.locator("[data-act=open-g]").first.click()
        if SHOTS:
            card.get_by_text("Soil and outside temperature").first.scroll_into_view_if_needed()
            pg.screenshot(path=str(SHOTS / "temps.png"))
            card.get_by_text("Soil and outside temperature").first.evaluate("e => e.closest('.card').scrollIntoView()")
            pg.screenshot(path=str(SHOTS / "temps2.png"))
        text = card.evaluate("el => el.shadowRoot.querySelector('ha-card').innerText")
        check("Estimated from local weather" in text and "Local weather" in text, "the temperature card says where the numbers come from")
        card.locator("[data-act=log-water]").first.click()
        pg.wait_for_timeout(400)
        mm = pg.evaluate("window.__garden.engine.snapshot()")["gardens"][0]["metrics"]["moisture"]
        check(mm["source"] == "estimated" and mm["estimate"]["since_water"] == 0 and mm["estimate"]["avail"] > 0.9, "moisture is estimated from the watering just logged")
        text = card.evaluate("el => el.shadowRoot.querySelector('ha-card').innerText")
        check("estimated soil moisture" in text, "garden page shows the moisture estimate")
        if SHOTS:
            card.get_by_text("estimated soil moisture").first.evaluate("e => e.closest('.card').scrollIntoView()")
            pg.screenshot(path=str(SHOTS / "moist.png"))
        card.locator("[data-act=open-layout]").click()
        card.locator("[data-act=lay-start]").click()
        card.locator("[data-act=lay-fill]").wait_for(timeout=5000)
        card.locator("[data-act=lay-fill]").click()
        card.locator("svg [data-act=lay-row]").first.wait_for(timeout=5000)
        pg.wait_for_timeout(300)
        lay = pg.evaluate("window.__garden.engine.snapshot()")["gardens"][0]["layout"]
        check(lay["configured"] and lay["totals"]["planted_rows"] == lay["totals"]["rows"] > 0, f"layout rows filled: {lay['totals']}")
        check(lay["totals"]["posts"] > 0, "tomato rows need T-posts")
        text = card.evaluate("el => el.shadowRoot.querySelector('ha-card').innerText")
        check("T-posts" in text and "Per sq ft" in text, "layout page shows the counts")
        # plant the layout: the rows become tracked plantings
        lay_n = pg.evaluate("window.__garden.engine.snapshot()")["gardens"][0]["layout"]["totals"]["plants"]
        if SHOTS:
            card.locator("[data-act=lay-plant]").evaluate("e => e.closest('.card').scrollIntoView()")
            pg.screenshot(path=str(SHOTS / "plant_layout.png"))
        card.locator("[data-act=lay-plant]").click()
        card.locator("[data-act=form-submit]").click()
        card.get_by_text("planted and tracked").wait_for(timeout=5000)
        pv = [v for v in pg.evaluate("window.__garden.engine.snapshot()")["varieties"] if v["garden"] == pg.evaluate("window.__garden.engine.snapshot()")["gardens"][0]["id"]]
        check(len(pv) == 1 and pv[0]["count"] == lay_n, f"planting the layout adds {lay_n} tracked plants")
        if SHOTS:
            card.get_by_text("planted and tracked").first.evaluate("e => e.scrollIntoView()")
            pg.screenshot(path=str(SHOTS / "planted.png"))
        # watering: drip is the default, with a run time, a GPM and drip line to order
        card.locator("[data-act=back]").first.click()
        card.locator("[data-act=open-water]").click()
        card.locator("[data-act=irr-pump]").first.wait_for(timeout=5000)
        w = pg.evaluate("window.__garden.engine.snapshot()")["gardens"][0]["irrigation"]
        check(w["method"] == "drip" and w["order"] and w["totals"]["gpm"] > 0, f"drip line planned: {w['totals']}")
        text = card.evaluate("el => el.shadowRoot.querySelector('ha-card').innerText")
        check("Drip line to order" in text and "GPM" in text and "Fertigation" in text, "watering page shows the order and fertigation")
        if SHOTS:
            pg.screenshot(path=str(SHOTS / "water.png"), full_page=True)
        # a venturi injector: add one through the form, then run the tank through it
        card.locator("[data-act=irr-pump]:not([data-k])").first.click()
        card.get_by_text("Venturi").first.click()
        card.get_by_label("Name").fill("Mazzei 484") if card.get_by_label("Name").count() else card.locator("input[type=text]").first.fill("Mazzei 484")
        if SHOTS:
            pg.screenshot(path=str(SHOTS / "venturi_form.png"), full_page=True)
        card.locator("[data-act=form-submit]").click()
        pg.wait_for_timeout(400)
        fp = pg.evaluate("window.__garden.engine.snapshot()")["gardens"][0]["irrigation"]["fert"]
        vp = next((p for p in fp["pumps"] if p["type"] == "venturi"), None)
        check(vp is not None and vp["name"] == "Mazzei 484" and vp["suction_gph"] > 0, "a venturi injector can be added")
        pg.evaluate("(k) => { const e = window.__garden.engine, g = e.snapshot().gardens[0].id; for (const t of ['A', 'B']) e.call('set_tank_pump', { garden: g, tank: t, pump: k }); }", vp["key"] if vp else "")
        card.locator("[data-act=irr-pump][data-k=pump1]").click()  # turn the first injector into a venturi so the tanks run through it
        card.get_by_text("Venturi").first.click()
        card.locator("[data-act=form-submit]").click()
        pg.wait_for_timeout(400)
        text = card.evaluate("el => el.shadowRoot.querySelector('ha-card').innerText")
        check("venturi, draws" in text and "Venturi: suction" in text.replace("\n", " "), "the water page shows the venturi and how to run it")
        if SHOTS:
            card.get_by_text("Venturi: ").first.evaluate("e => e.closest('.card').scrollIntoView()")
            pg.screenshot(path=str(SHOTS / "venturi_tank.png"))
        # lists: a tree without a garden, search, sort and what to show
        card.locator("[data-act=back]").first.click()  # water page to the garden
        card.locator("[data-act=back]").first.click()  # and home
        for n, sp in (("Gala", "Apple"), ("Bartlett", "Pear"), ("Sungold", "Tomato")):
            r = pg.evaluate("([n, sp]) => { const e = window.__garden.engine; return e.call('add_variety', { garden: sp === 'Tomato' ? e.snapshot().gardens[0].id : '', species: sp, variety: n }); }", [n, sp])
            check(r["ok"], f"{sp} added" + (" with no garden" if sp != "Tomato" else ""))
        pg.evaluate("window.__garden.refreshWeather(true)")
        card.get_by_text("Trees, no garden").wait_for(timeout=5000)
        check(True, "trees without a garden get their own section")
        # the Add plant form with "No garden" chosen, the way the HA card sends it (an empty garden)
        card.locator("[data-act=form-variety]").first.click()
        card.locator("select").nth(0).select_option("")
        card.locator("select").nth(1).select_option(label="Cherry")
        card.get_by_placeholder("Sungold").fill("Rainier")
        card.locator("[data-act=form-submit]").click()
        pg.wait_for_timeout(500)
        rv = [v for v in pg.evaluate("window.__garden.engine.snapshot()")["varieties"] if v["name"] == "Rainier"]
        check(len(rv) == 1 and rv[0]["garden"] == "" and rv[0]["kind"] == "tree", "a tree can be added from the form with no garden")
        card.locator("input[data-q=home]").fill("bart")
        pg.wait_for_timeout(300)
        text = card.evaluate("el => el.shadowRoot.querySelector('ha-card').innerText")
        check("Bartlett" in text and "Gala" not in text and "Sungold" not in text, "typing in the search box filters the plants")
        check(card.evaluate("el => el.shadowRoot.activeElement && el.shadowRoot.activeElement.dataset.q") == "home", "the search box keeps focus while typing")
        card.locator("input[data-q=home]").fill("")
        card.locator("[data-act=sort][data-s=name]").click()
        names = card.evaluate("el => [...el.shadowRoot.querySelectorAll('.tile[data-act=open-v]')].map((t) => t.querySelector('[style*=\"font-weight:500\"], [style*=\"font-size:15px\"]').innerText)")
        check(names == sorted(names, key=str.lower) and len(names) == 5, f"sorted by name: {names}")
        if SHOTS:
            pg.screenshot(path=str(SHOTS / "lists.png"), full_page=True)
        card.locator("[data-act=form-view]").click()
        card.get_by_role("button", name="Hide").nth(0).click()
        card.locator("[data-act=form-submit]").click()
        pg.wait_for_timeout(300)
        check(card.evaluate("el => !el.shadowRoot.querySelector('ha-card').innerText.includes('Every 14 days')"), "watering can be hidden from view")
        card.locator("[data-act=form-view]").click()
        card.get_by_role("button", name="Show").nth(0).click()
        card.locator("[data-act=form-submit]").click()
        card.locator("[data-act=sort][data-s=garden]").click()
        # removing a garden keeps its history under Past plants, and it can be brought back
        pg.evaluate("() => { const e = window.__garden.engine; for (const v of e.snapshot().varieties) e.call('remove_plant', { plant: v.id }); }")
        pg.evaluate("window.__garden.refreshWeather(true)")
        card.locator("[data-act=open-g]").first.click()
        card.locator("[data-act=ask-rmg]").click()
        card.locator("[data-act=do-rmg]").click()
        card.get_by_text("History").first.wait_for(timeout=5000)
        sn = pg.evaluate("window.__garden.engine.snapshot()")
        check(not sn["gardens"] and [g["name"] for g in sn["past_gardens"]] == ["Back yard"], "a removed garden leaves the list but is kept")
        card.locator("[data-act=open-archive]").first.click()
        if SHOTS:
            pg.screenshot(path=str(SHOTS / "removed.png"))
        card.locator("[data-act=restore-g]").click()
        pg.wait_for_timeout(400)
        check(len(pg.evaluate("window.__garden.engine.snapshot()")["gardens"]) == 1, "a removed garden can be brought back")
        check(not errors, f"no page errors {errors[:2]}")
        b.close()
    server.shutdown()
    sys.exit(1 if check.failed else 0)


if __name__ == "__main__":
    main()
