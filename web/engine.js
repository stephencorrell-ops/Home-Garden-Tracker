// The garden logic is the same Python used by the Home Assistant integration (core/), run in the browser with Pyodide.
// An engine takes actions as JSON text and hands back snapshots and saved data as JSON text.

const PY_START = `
import sys
from garden_core.api import GardenApp
app = GardenApp(_species, _stored, _today)
`;

export class PyodideEngine {
  async init({ stored, today, onStatus = () => {} }) {
    onStatus("Loading the garden engine...");
    const { loadPyodide } = await import("./pyodide/pyodide.mjs");
    const py = await loadPyodide({ indexURL: new URL("./pyodide/", import.meta.url).href });
    const files = await (await fetch("core/files.json")).json();
    py.FS.mkdirTree("/home/pyodide/garden_core");
    for (const f of files) {
      const text = await (await fetch(`core/${f}`)).text();
      py.FS.writeFile(`/home/pyodide/garden_core/${f}`, text);
    }
    this.py = py;
    this.species = await (await fetch("core/species.json")).text();
    this._start(stored, today);
  }
  _start(stored, today) {
    this.py.globals.set("_species", this.species);
    this.py.globals.set("_stored", stored || null);
    this.py.globals.set("_today", today);
    this.py.runPython(PY_START);
    this.app = this.py.globals.get("app");
  }
  call(service, data) { return JSON.parse(this.app.call(service, JSON.stringify(data || {}))); }
  snapshot() { return JSON.parse(this.app.snapshot()); }
  data() { return this.app.data(); }
  setToday(iso) { this.app.set_today(iso); }
  mergeWeather(w) { return JSON.parse(this.app.merge_weather(JSON.stringify(w))); }
  load(stored, today) { this.app.destroy?.(); this._start(stored, today); }
}

// For tests only: talks to a Python server running the same core, so the page can be tested without Pyodide.
export class HttpEngine {
  constructor(base) { this.base = base; }
  _post(path, body) {
    const x = new XMLHttpRequest();  // synchronous, like the Pyodide engine
    x.open("POST", `${this.base}/${path}`, false);
    x.setRequestHeader("content-type", "application/json");
    x.send(JSON.stringify(body || {}));
    return JSON.parse(x.responseText);
  }
  async init({ stored, today }) { this._post("start", { stored, today }); }
  call(service, data) { return this._post("call", { service, data }); }
  snapshot() { return this._post("snapshot"); }
  data() { return JSON.stringify(this._post("data")); }
  setToday(iso) { this._post("today", { today: iso }); }
  mergeWeather(w) { return this._post("weather", w); }
  load(stored, today) { this._post("start", { stored, today }); }
}
