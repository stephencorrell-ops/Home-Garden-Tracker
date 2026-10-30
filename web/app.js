import { PyodideEngine, HttpEngine } from "./engine.js";
import * as store from "./store.js";
import { fetchWeather, findPlaces } from "./weather.js";

const $ = (id) => document.getElementById(id);
const todayIso = () => { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`; };
const BACKUP_EVERY_DAYS = 14;
const params = new URLSearchParams(location.search);

let engine, today = todayIso(), saveTimer = null, saveFailed = false;
const listeners = new Set();

// ---- the card talks to this as if it were Home Assistant -------------------------------------------------
const hass = {
  states: {},
  config: {},
  connection: {
    subscribeMessage(cb) {
      listeners.add(cb);
      cb(engine.snapshot());
      return Promise.resolve(() => listeners.delete(cb));
    },
  },
  async callService(_domain, service, data) {
    const r = engine.call(service, data);
    if (!r.ok) throw new Error(r.error);
    changed();
  },
};

function changed() {
  const snap = engine.snapshot();
  for (const cb of listeners) cb(snap);
  clearTimeout(saveTimer);
  saveTimer = setTimeout(save, 300);
  checkBackupNotice(snap);
}
async function save() {
  clearTimeout(saveTimer);
  saveTimer = null;
  try { await store.set("data", engine.data()); saveFailed = false; }
  catch (e) { console.error("Not saved:", e); saveFailed = true; }
  checkBackupNotice();
}
function flushSave() { if (saveTimer) save(); }  // the page is closing or going to the background

// ---- backup and restore ----------------------------------------------------------------------------------
function hasData(snap) { return snap.gardens.length > 0 || snap.varieties.length > 0; }

function backupFile() {
  const body = { app: "garden-tracker", format: 1, saved: new Date().toISOString(), data: JSON.parse(engine.data()) };
  return new Blob([JSON.stringify(body)], { type: "application/json" });
}
function downloadBackup() {
  const url = URL.createObjectURL(backupFile());
  const a = Object.assign(document.createElement("a"), { href: url, download: `garden-tracker-backup-${todayIso()}.json` });
  document.body.append(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
  store.markBackup();
  checkBackupNotice();
}

function checkBackupNotice(snap = engine.snapshot()) {
  const box = $("notice");
  const age = (Date.now() - store.lastBackup()) / 864e5;
  let snoozed = false;
  try { snoozed = Date.now() < Number(localStorage.getItem("gt.snooze") || 0); } catch { /* ignore */ }
  if (saveFailed) {
    box.innerHTML = `<span style="flex:1">This browser didn't save your last change. Back up now so it isn't lost.</span><button class="link" id="nb">Back up now</button>`;
    box.hidden = false;
    $("nb").onclick = downloadBackup;
    return;
  }
  if (!hasData(snap) || snoozed || (store.lastBackup() && age < BACKUP_EVERY_DAYS)) { box.hidden = true; return; }
  box.innerHTML = `<span style="flex:1">${store.lastBackup() ? `Last backup ${Math.floor(age)} days ago.` : "Not backed up yet."} This browser can clear saved data.</span><button class="link" id="nb">Back up now</button><button class="link mut" id="ns" aria-label="Remind me later">Later</button>`;
  box.hidden = false;
  $("nb").onclick = downloadBackup;
  $("ns").onclick = () => { try { localStorage.setItem("gt.snooze", String(Date.now() + 3 * 864e5)); } catch { /* ignore */ } box.hidden = true; };
}

function parseBackup(text) {
  let obj;
  try { obj = JSON.parse(text); } catch { throw new Error("That file isn't a Garden Tracker backup."); }
  const data = obj && obj.app === "garden-tracker" ? obj.data : obj;  // a bare data file works too
  if (!data || typeof data !== "object" || !data.gardens || !data.varieties) throw new Error("That file isn't a Garden Tracker backup.");
  return { data, saved: obj.saved || null };
}

function dialog(html) {
  const d = $("dlg");
  d.innerHTML = html;
  if (!d.open) d.showModal();
  return d;
}
const closeDialog = () => { const d = $("dlg"); if (d.open) d.close(); };

async function restoreFrom(file) {
  try {
    const { data, saved } = parseBackup(await file.text());
    const n = (o) => Object.keys(o || {}).length;
    const d = dialog(`<h2>Restore this backup?</h2><p>${n(data.gardens)} location${n(data.gardens) === 1 ? "" : "s"} and ${n(data.varieties)} plant${n(data.varieties) === 1 ? "" : "s"}${saved ? `, saved ${new Date(saved).toLocaleDateString()}` : ""}.</p><p class="small">This replaces everything currently on this device.</p><div class="row"><button id="rc">Cancel</button><button class="primary" id="ry">Replace</button></div>`);
    d.querySelector("#rc").onclick = closeDialog;
    d.querySelector("#ry").onclick = async () => {
      engine.load(JSON.stringify(data), today);
      await save();
      closeDialog();
      changed();
      refreshWeather(true);
    };
  } catch (e) {
    dialog(`<h2>Can't restore</h2><p>${e.message}</p><div class="row"><button class="primary" id="ok">OK</button></div>`).querySelector("#ok").onclick = closeDialog;
  }
}

// ---- weather ---------------------------------------------------------------------------------------------
let weatherBusy = false, weatherAgain = false;
const placeKey = () => { const l = engine.snapshot().micro.settings.location; return l ? `${l.lat},${l.lon}` : null; };
async function refreshWeather(force = false) {
  const loc = engine.snapshot().micro.settings.location;
  if (weatherBusy) { weatherAgain = weatherAgain || force; return; }  // run again once the current fetch is done
  if (!loc || !navigator.onLine) return;
  const key = `${loc.lat},${loc.lon}`;
  let last = 0, fullFor = null;
  try { last = Number(localStorage.getItem("gt.weatherAt") || 0); fullFor = localStorage.getItem("gt.weatherFull"); } catch { /* ignore */ }
  if (!force && fullFor === key && Date.now() - last < 6 * 3600e3) return;
  weatherBusy = true;
  try {
    const w = await fetchWeather(loc, today, fullFor !== key || force);
    if (placeKey() !== key) { weatherAgain = true; return; }  // the place changed or a backup was restored meanwhile
    engine.mergeWeather(w);
    try { localStorage.setItem("gt.weatherAt", String(Date.now())); localStorage.setItem("gt.weatherFull", key); } catch { /* ignore */ }
    changed();
  } catch (e) {
    console.warn("Weather not updated:", e);
  } finally {
    weatherBusy = false;
    if (weatherAgain) { weatherAgain = false; refreshWeather(true); }
  }
}

function chooseLocation() {
  const d = dialog(`<h2>Where is your garden?</h2><input type="search" id="q" placeholder="Town or city" autocomplete="off"><ul id="res"></ul><div class="row"><button id="gps">Use my location</button><button id="lc">Cancel</button></div><p class="small">Used only to look up the weather. It is saved in your garden data.</p>`);
  const res = d.querySelector("#res");
  const pick = async (p) => {
    const r = engine.call("set_location", { lat: p.lat, lon: p.lon, name: p.name });
    if (!r.ok) { res.innerHTML = `<li class="small">${r.error}</li>`; return; }
    closeDialog(); changed(); refreshWeather(true);
  };
  const show = (list) => {
    res.innerHTML = list.length ? "" : `<li class="small">Nothing found. Try another spelling.</li>`;
    list.forEach((p) => { const li = document.createElement("li"), b = document.createElement("button"); b.textContent = p.name; b.onclick = () => pick(p); li.append(b); res.append(li); });
  };
  let timer;
  d.querySelector("#q").oninput = (e) => {
    clearTimeout(timer);
    const v = e.target.value.trim();
    if (v.length < 2) { res.innerHTML = ""; return; }
    timer = setTimeout(async () => { try { show(await findPlaces(v)); } catch { res.innerHTML = `<li class="small">Couldn't reach the search. Check your connection.</li>`; } }, 350);
  };
  d.querySelector("#lc").onclick = closeDialog;
  d.querySelector("#gps").onclick = () => {
    if (!navigator.geolocation) { res.innerHTML = `<li class="small">This browser can't share a location.</li>`; return; }
    navigator.geolocation.getCurrentPosition(
      (pos) => pick({ lat: pos.coords.latitude, lon: pos.coords.longitude, name: "My location" }),
      () => { res.innerHTML = `<li class="small">Couldn't get your location. Search for your town instead.</li>`; });
  };
}

// ---- start -----------------------------------------------------------------------------------------------
async function main() {
  const stored = await store.get("data");
  engine = params.get("engine") ? new HttpEngine(params.get("engine")) : new PyodideEngine();
  try {
    await engine.init({ stored, today, onStatus: (t) => { $("splash").textContent = t; } });
  } catch (e) {
    console.error(e);
    $("splash").innerHTML = `The garden engine didn't start (${e.message || e}).<br>It needs a connection the first time. Reload to try again.`;
    return;
  }
  store.keepSafe();
  await import("./garden-card.js");
  const card = document.createElement("garden-tracker-card");
  card.setConfig({ web: true });
  card.addEventListener("garden-location", chooseLocation);
  $("root").replaceChildren(card);
  card.hass = hass;
  window.__garden = { engine, hass, card, refreshWeather, downloadBackup, restoreFrom, save };

  $("backup").onclick = downloadBackup;
  $("restore").onclick = () => $("file").click();
  $("file").onchange = (e) => { const f = e.target.files[0]; e.target.value = ""; if (f) restoreFrom(f); };
  checkBackupNotice();
  refreshWeather();

  setInterval(() => {  // a new day: refresh the dates and the weather
    if (todayIso() !== today) { today = todayIso(); engine.setToday(today); changed(); refreshWeather(true); }
  }, 60e3);
  window.addEventListener("pagehide", flushSave);
  document.addEventListener("visibilitychange", () => { if (document.hidden) flushSave(); else { if (todayIso() !== today) { today = todayIso(); engine.setToday(today); changed(); } refreshWeather(); } });

  let prompt;
  window.addEventListener("beforeinstallprompt", (e) => { e.preventDefault(); prompt = e; $("install").hidden = false; });
  $("install").onclick = async () => { if (prompt) { prompt.prompt(); prompt = null; $("install").hidden = true; } };
}

if ("serviceWorker" in navigator && !params.get("engine")) {
  navigator.serviceWorker.register("sw.js").catch(() => {});
}
main();
