/* Garden Tracker card for Home Assistant. Part of the garden_tracker integration. */
const DOMAIN = "garden_tracker";
const REASON_TEXT = { disease: "Disease", pests: "Pests", frost: "Frost", heat: "Heat", water: "Water",
  animal_damage: "Animal damage", other: "Other" };
const ARCH_TEXT = { season_over: "Season over", pulled_early: "Pulled early", died: "Died" };
const STATUS_TEXT = { alive: "Alive", dead: "Dead", pulled: "Pulled early" };

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const num = (n, d = 2) => (n === null || n === undefined || n === "" ? "" : String(Math.round(Number(n) * 10 ** d) / 10 ** d));
const fmtDate = (iso, withYear) => {
  if (!iso) return "";
  const d = new Date(iso + "T00:00:00");
  const y = withYear || d.getFullYear() !== new Date().getFullYear();
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", ...(y ? { year: "numeric" } : {}) });
};
const dAgo = (n) => (n === null || n === undefined ? "–" : `${n} d`);
const dIn = (n) => (n === null || n === undefined ? "–" : n < 0 ? `${-n} d late` : n === 0 ? "today" : `${n} d`);
const yrs = (y) => (y < 1 ? "<1 yr" : `${Math.floor(y)} yr${Math.floor(y) === 1 ? "" : "s"}`);

const CSS = `
:host{--ok:var(--success-color,#43a047);--spray:var(--warning-color,#ffa000);--hold:var(--error-color,#db4437);--info:var(--info-color,#039be5);--mut:var(--secondary-text-color);--line:var(--divider-color)}
ha-card{padding:12px;display:block}
*{box-sizing:border-box}
button{font:inherit;color:var(--primary-text-color);background:transparent;border:1px solid var(--line);border-radius:8px;padding:6px 10px;cursor:pointer}
button:hover{background:var(--secondary-background-color)}
button.on{border:2px solid var(--primary-color);background:color-mix(in srgb,var(--primary-color) 14%,transparent);padding:5px 9px}
button.bad{border:2px solid var(--hold);background:color-mix(in srgb,var(--hold) 14%,transparent);padding:5px 9px}
button.primary{background:var(--primary-color);color:var(--text-primary-color,#fff);border-color:var(--primary-color)}
button.danger{border-color:var(--hold);color:var(--hold)}
button.ic{border:none;padding:6px;line-height:0;color:var(--mut)}
input,select,textarea{font:inherit;width:100%;color:var(--primary-text-color);background:var(--card-background-color);border:1px solid var(--line);border-radius:8px;padding:8px}
textarea{resize:vertical}
label{display:block;font-size:12px;color:var(--mut);margin-bottom:4px}
.row{display:flex;gap:8px;align-items:center}.grow{flex:1;min-width:0}.wrap{flex-wrap:wrap}
.hd{display:flex;gap:8px;align-items:center;margin-bottom:12px}
.ttl{font-size:18px;font-weight:500}.sub{font-size:12px;color:var(--mut)}.mut{color:var(--mut)}.small{font-size:12px}
.card{background:var(--ha-card-background,var(--card-background-color));border:1px solid var(--line);border-radius:12px;padding:12px;margin-bottom:10px}
.sec{font-size:12px;color:var(--mut);margin:0 0 6px}
.tile{cursor:pointer}.tile:hover{border-color:var(--primary-color)}
.pic{width:56px;height:56px;border-radius:12px;flex:none;display:flex;align-items:center;justify-content:center}
.pill{font-size:12px;padding:2px 10px;border-radius:8px;display:inline-block;margin-top:4px;color:var(--c);background:color-mix(in srgb,var(--c) 16%,transparent)}
.ok{--c:var(--ok)}.spray,.warn{--c:var(--spray)}.hold,.bad,.low,.high{--c:var(--hold)}.info{--c:var(--info)}.none{--c:var(--mut)}
.stats{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:10px}
.stat{background:var(--secondary-background-color);border-radius:8px;padding:8px 10px}
.stat span{display:block;font-size:11px;color:var(--mut)}.stat b{font-size:16px;font-weight:500}
.bar{height:6px;border-radius:3px;background:var(--line);overflow:hidden;margin-top:5px}.bar i{display:block;height:100%;background:var(--spray)}
.chips{display:flex;gap:6px;overflow-x:auto;margin-bottom:10px}
.chip{white-space:nowrap;border-radius:8px;padding:4px 10px;font-size:12px;border:1px solid var(--line);cursor:pointer;background:transparent}
.chip.on{background:var(--primary-text-color);color:var(--card-background-color);border-color:var(--primary-text-color)}
.lg{display:flex;align-items:center;gap:6px;padding:8px 0;border-top:1px solid var(--line);font-size:13px}
.lg .t{flex:1;min-width:0}.lg .t span{display:block;font-size:12px;color:var(--mut)}
.conf{background:color-mix(in srgb,var(--hold) 14%,transparent);color:var(--primary-text-color);border-radius:8px;padding:8px 10px;margin:4px 0;font-size:12px}
.conf .row{margin-top:6px}.conf button{flex:1}
.msg{padding:24px 8px;text-align:center;color:var(--mut)}
.err{background:color-mix(in srgb,var(--hold) 14%,transparent);color:var(--hold);border-radius:8px;padding:8px 10px;margin-bottom:10px;font-size:13px}
.undo{background:color-mix(in srgb,var(--info) 14%,transparent);border-radius:8px;padding:6px 10px;margin-bottom:10px;display:flex;align-items:center;justify-content:space-between;font-size:13px}
.npk{display:inline-block;font-size:12px;padding:1px 7px;border-radius:6px;margin-right:4px;font-weight:500}
.n{background:color-mix(in srgb,var(--ok) 18%,transparent)}.p{background:color-mix(in srgb,var(--spray) 22%,transparent)}.k{background:color-mix(in srgb,#8e24aa 18%,transparent)}
.seg{display:flex;gap:4px;flex-wrap:wrap}.seg button{flex:1;font-size:12px;padding:6px 4px}
.grid6{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:10px}
.plant{border:1px solid var(--line);border-radius:8px;padding:10px;margin-top:8px}
.big{font-size:22px;font-weight:500}.ph{font-size:30px;font-weight:500}
.phases{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:6px;margin:6px 0 10px}
.phase{border:1px solid var(--line);border-radius:8px;padding:6px 4px;text-align:center;font-size:11px;color:var(--mut)}
.phase b{display:block;font-size:12px;font-weight:500;color:var(--primary-text-color)}
.phase.cur{border:2px solid var(--primary-color);background:color-mix(in srgb,var(--primary-color) 12%,transparent)}
.adj{display:flex;align-items:center;gap:10px;padding:10px 0;border-top:1px solid var(--line)}
.adj .dot{width:36px;height:36px;border-radius:10px;display:flex;align-items:center;justify-content:center;background:color-mix(in srgb,var(--c) 16%,transparent);color:var(--c)}
.pips{display:flex;gap:4px;margin-top:5px}.pips i{width:14px;height:6px;border-radius:3px;background:var(--line)}.pips i.f{background:var(--c)}
svg .ax{fill:var(--secondary-text-color);font-size:10px}
ha-icon{--mdc-icon-size:20px}
`;

const tree = (canopy, fruit) => `<svg viewBox="0 0 56 56" width="44" height="44" aria-hidden="true"><rect x="26" y="34" width="5" height="16" rx="1" fill="#8d6e63"/><circle cx="28" cy="22" r="17" fill="${canopy}"/>${[[20, 18], [33, 14], [35, 27], [21, 29]].map(([x, y]) => `<circle cx="${x}" cy="${y}" r="3" fill="${fruit}"/>`).join("")}</svg>`;
const vine = (fruit) => `<svg viewBox="0 0 56 56" width="44" height="44" aria-hidden="true"><path d="M28 52 C28 38 26 28 28 10" stroke="#3b6d11" stroke-width="3" fill="none" stroke-linecap="round"/><ellipse cx="18" cy="20" rx="9" ry="4.5" transform="rotate(-25 18 20)" fill="#97c459"/><ellipse cx="38" cy="30" rx="9" ry="4.5" transform="rotate(25 38 30)" fill="#97c459"/><circle cx="20" cy="38" r="6" fill="${fruit}"/><circle cx="36" cy="44" r="5" fill="${fruit}"/></svg>`;
const PICS = { apple: tree("#639922", "#e24b4a"), pear: tree("#639922", "#c6d84a"), asian_pear: tree("#7cb342", "#e0b341"),
  cherry: tree("#3b6d11", "#a32d2d"), nectarine: tree("#7cb342", "#f4793a"), pawpaw: tree("#558b2f", "#9ccc65"),
  tomato: vine("#e24b4a"), pepper: vine("#f9a825"), cucumber: vine("#7cb342") };
const pic = (v) => PICS[v.species] || (v.kind === "tree" ? tree("#689f38", "#e0a030") : vine("#9ccc65"));

function phChart(ph, adjLog) {
  const hs = ph.history;
  if (hs.length < 2) return `<div class="mut small">Log at least two readings to see the trend.</div>`;
  const W = 340, H = 130, L = 30, R = 8, T = 12, B = 22;
  const ds = hs.map((r) => Date.parse(r.date));
  const t0 = Math.min(...ds);
  const t1 = Math.max(Math.max(...ds), t0 + 864e5 * 30);
  const vals = hs.map((r) => r.value).concat(ph.target);
  const lo = Math.min(...vals) - 0.3, hi = Math.max(...vals) + 0.3;
  const x = (t) => L + ((t - t0) / (t1 - t0)) * (W - L - R);
  const y = (v) => T + ((hi - v) / (hi - lo)) * (H - T - B);
  const seen = new Set();
  const marks = adjLog.filter((e) => { const t = Date.parse(e.date); const k = e.date + e.type; if (t < t0 || t > t1 || seen.has(k)) return false; seen.add(k); return true; })
    .map((e) => `<line x1="${x(Date.parse(e.date))}" x2="${x(Date.parse(e.date))}" y1="${T}" y2="${H - B}" stroke="var(--spray)" stroke-dasharray="3 3"/><text class="ax" x="${x(Date.parse(e.date)) + 3}" y="${T + 8}">${esc(e.type_name)}</text>`).join("");
  const pts = hs.map((r) => `${x(Date.parse(r.date)).toFixed(1)},${y(r.value).toFixed(1)}`).join(" ");
  const dots = hs.map((r, i) => `<circle cx="${x(Date.parse(r.date))}" cy="${y(r.value)}" r="${i === hs.length - 1 ? 5 : 3.5}" fill="var(--primary-color)"/>`).join("");
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Soil pH over time">
    <rect x="${L}" y="${y(ph.target[1])}" width="${W - L - R}" height="${Math.max(2, y(ph.target[0]) - y(ph.target[1]))}" fill="var(--ok)" opacity="0.22"/>
    <line x1="${L}" y1="${H - B}" x2="${W - R}" y2="${H - B}" stroke="var(--divider-color)"/>
    <text class="ax" x="2" y="${y(hi) + 10}">${hi.toFixed(1)}</text><text class="ax" x="2" y="${y(lo) - 2}">${lo.toFixed(1)}</text>
    ${marks}<polyline points="${pts}" fill="none" stroke="var(--primary-color)" stroke-width="2"/>${dots}
    <text class="ax" x="${L}" y="${H - 6}">${fmtDate(hs[0].date)}</text><text class="ax" text-anchor="end" x="${W - R}" y="${H - 6}">${fmtDate(hs[hs.length - 1].date)}</text></svg>`;
}

class GardenTrackerCard extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
    this._view = { v: "home" };
    this._nav = [];
    this._form = null;
    this._confirm = null;
    this._filter = "all";
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this.shadowRoot.addEventListener("click", (e) => this._onClick(e));
      this.shadowRoot.addEventListener("input", (e) => this._onInput(e, false));
      this.shadowRoot.addEventListener("change", (e) => this._onInput(e, true));
    }
    this._render();
  }
  set hass(h) {
    this._hass = h;
    if (!this._subTried) this._subscribe();
  }
  getCardSize() { return 8; }
  static getStubConfig() { return {}; }
  connectedCallback() { if (this._hass && !this._sub) { this._subTried = false; this._subscribe(); } }
  disconnectedCallback() {
    if (this._sub) { this._sub.then((u) => u()).catch(() => {}); this._sub = null; this._subTried = false; }
  }
  _subscribe() {
    this._subTried = true;
    this._sub = this._hass.connection.subscribeMessage((snap) => {
      this._snap = snap; this._err = null;
      if (!this._form) this._render();
    }, { type: `${DOMAIN}/subscribe` });
    this._sub.catch(() => { this._err = "Garden Tracker isn't set up yet. Add the integration under Settings, Devices & services."; this._sub = null; this._render(); });
  }

  // ---- data helpers ----------------------------------------------------------
  _gardens() {
    const want = this._config.garden;
    return this._snap.gardens.filter((g) => !want || g.id === want || g.name.toLowerCase() === String(want).toLowerCase());
  }
  _vars(archived = false) {
    const ids = new Set(this._gardens().map((g) => g.id));
    const all = !this._config.garden;
    return this._snap.varieties.filter((v) => !!v.archived === archived && (all || ids.has(v.garden)));
  }
  _variety(id) { return this._snap.varieties.find((v) => v.id === id); }
  _garden(id) { return this._snap.gardens.find((g) => g.id === id); }
  async _call(service, data) {
    const clean = {};
    for (const [k, v] of Object.entries(data)) {
      if (v === "" || v === undefined || v === null || (typeof v === "number" && isNaN(v))) continue;
      clean[k] = v;
    }
    return this._hass.callService(DOMAIN, service, clean);
  }
  async _act(service, data, after) {
    try { await this._call(service, data); this._err = null; if (after) after(); }
    catch (e) { this._err = e.message || String(e); }
    this._render();
  }
  _go(view) { this._nav.push(this._view); this._view = view; this._confirm = null; this._render(); }
  _back() { this._view = this._nav.pop() || { v: "home" }; this._confirm = null; this._render(); }

  // ---- render -----------------------------------------------------------------
  _render() {
    if (!this.shadowRoot) return;
    let body;
    if (!this._snap) body = `<div class="msg">${esc(this._err || "Loading...")}</div>`;
    else if (this._form) body = this._formView();
    else {
      const w = this._view.v;
      const v = this._view.id && w === "variety" ? this._variety(this._view.id) : null;
      const g = this._view.id && w === "garden" ? this._garden(this._view.id) : null;
      if (w === "variety" && v) body = this._varietyView(v);
      else if (w === "garden" && g) body = this._gardenView(g);
      else if (w === "archive") body = this._archiveView();
      else { this._view = { v: "home" }; body = this._homeView(); }
    }
    const banner = (this._err && this._snap ? `<div class="err">${esc(this._err)}</div>` : "") +
      (this._undo && this._snap && this._snap.can_undo && !this._form
        ? `<div class="undo"><span>Entry removed</span><button data-act="undo">Undo</button></div>` : "");
    this.shadowRoot.innerHTML = `<style>${CSS}</style><ha-card>${banner}${body}</ha-card>`;
  }

  _icon(name) { return `<ha-icon icon="mdi:${name}"></ha-icon>`; }
  _btn(act, icon, label, attrs = "", cls = "") {
    return `<button class="${cls}" data-act="${act}" ${attrs}>${icon ? this._icon(icon) : ""}${label ? " " + label : ""}</button>`;
  }
  _stats(v) {
    const d = v.days, out = [];
    if (v.kind === "tree") {
      out.push(["Age", yrs(v.age_years)], ["Last spray", dAgo(v.spray.days_since)]);
      if (v.days_to_expected !== null) out.push(["Harvest in", dIn(v.days_to_expected)]);
      else out.push(["Harvested", `${num(v.total_lbs, 1)} lb`]);
    } else {
      if (d.upotted !== null) out.push(["Up-potted", dAgo(d.upotted)]);
      if (d.in_ground !== null) out.push(["In ground", dAgo(d.in_ground)]);
      if (d.fertilized !== null) out.push(["Last fed", dAgo(d.fertilized)]);
      if (out.length < 3) out.push(["Planted", dAgo(d.planted)]);
      if (out.length < 3 && v.days_to_expected !== null) out.push(["Harvest in", dIn(v.days_to_expected)]);
    }
    return out;
  }
  _statGrid(list) {
    return `<div class="stats">${list.map(([k, val]) => `<div class="stat"><span>${esc(k)}</span><b>${esc(val)}</b></div>`).join("")}</div>`;
  }
  _picBox(v) {
    const c = { ok: "var(--ok)", spray: "var(--spray)", hold: "var(--hold)", info: "var(--info)" }[v.status.level];
    return `<div class="pic" style="background:color-mix(in srgb,${c} 18%,transparent)">${pic(v)}</div>`;
  }

  // ---- home ---------------------------------------------------------------------
  _homeView() {
    const gs = this._gardens(), vs = this._vars();
    let h = `<div class="hd"><div class="ttl grow">Garden</div>${gs.length ? this._btn("form-variety", "plus", "Add plant", "", "primary") : ""}</div>`;
    if (!gs.length) {
      return h + `<div class="msg">Create your first garden to start adding plants.<br><br>${this._btn("form-garden", "plus", "Add garden", "", "primary")}</div>`;
    }
    h += `<div class="chips">${gs.map((g) => `<button class="chip" data-act="open-g" data-g="${g.id}">${esc(g.name)}</button>`).join("")}${this._config.garden ? "" : `<button class="chip" data-act="form-garden">+ Garden</button>`}</div>`;
    const cnt = (l) => vs.filter((v) => v.status.level === l).length;
    const filters = [["all", `All ${vs.length}`], ["spray", `Spray due ${cnt("spray")}`], ["hold", `Harvest hold ${cnt("hold")}`], ["ok", `On track ${cnt("ok")}`]];
    if (vs.length) h += `<div class="chips">${filters.map(([k, t]) => `<button class="chip ${this._filter === k ? "on" : ""}" data-act="filter" data-s="${k}">${t}</button>`).join("")}</div>`;
    const shown = vs.filter((v) => this._filter === "all" || v.status.level === this._filter);
    if (!vs.length) h += `<div class="msg">No plants yet. Tap Add plant.</div>`;
    else if (!shown.length) h += `<div class="msg">Nothing matches this filter.</div>`;
    for (const g of gs) {
      const mine = shown.filter((v) => v.garden === g.id);
      if (!mine.length) continue;
      if (gs.length > 1) h += `<div class="sec">${esc(g.name)}</div>`;
      h += mine.map((v) => this._tile(v)).join("");
    }
    const past = this._vars(true).length;
    if (past) h += `<button style="width:100%" data-act="open-archive">${this._icon("archive")} Past plants (${past})</button>`;
    return h;
  }
  _tile(v) {
    const tree = v.kind === "tree";
    const sub = [v.species_name, tree ? null : `${v.alive} of ${v.count} plants`].filter(Boolean).join(", ");
    const pest = tree ? v.pests.find((p) => p.status && p.status.next_dd) : null;
    let h = `<div class="card tile" data-act="open-v" data-v="${v.id}"><div class="row">${this._picBox(v)}<div class="grow"><div style="font-size:15px;font-weight:500">${esc(v.name)}</div><div class="sub">${esc(sub)}</div><span class="pill ${v.status.level}">${esc(v.status.text)}</span></div></div>`;
    h += this._statGrid(this._stats(v).slice(0, 3));
    if (pest) {
      const s = pest.status;
      h += `<div style="margin-top:10px;font-size:12px" class="row"><span class="mut grow">${esc(pest.name)} degree days</span><b>${s.dd} / ${s.next_dd}</b></div><div class="bar"><i style="width:${Math.min(100, (s.dd / s.next_dd) * 100)}%"></i></div>`;
    }
    if (v.total_lbs > 0) h += `<div class="small mut" style="margin-top:8px">Harvested so far: ${num(v.total_lbs, 1)} lb</div>`;
    const q = tree ? [["form-spray", "spray", "Sprayed"], ["form-harvest", "basket", "Harvest"]] : [["form-fert", "sprout", "Fed"], ["form-harvest", "basket", "Harvest"]];
    h += `<div class="row" style="margin-top:10px">${q.map(([a, i, t]) => `<button class="grow" data-act="${a}" data-v="${v.id}">${this._icon(i)} ${t}</button>`).join("")}</div></div>`;
    return h;
  }

  // ---- log rows -----------------------------------------------------------------
  _acts(kind, parent, id) {
    return `<button class="ic" data-act="edit-entry" data-k="${kind}" data-p="${parent}" data-e="${id}" aria-label="Edit">${this._icon("pencil")}</button>` +
      `<button class="ic" data-act="ask-del" data-key="${kind}:${id}" aria-label="Remove">${this._icon("trash-can-outline")}</button>`;
  }
  _logRow(kind, parent, id, main, sub, warn) {
    let h = `<div class="lg"><div class="t">${main}<span>${sub}</span></div>${this._acts(kind, parent, id)}</div>`;
    if (this._confirm === `${kind}:${id}`) {
      h += `<div class="conf">Remove this entry? ${esc(warn || "It leaves the log and everything recalculates.")}<div class="row"><button data-act="cancel-del">Keep</button><button class="danger" data-act="do-del" data-k="${kind}" data-p="${parent}" data-e="${id}">Remove</button></div></div>`;
    }
    return h;
  }
  _npk(e) {
    const bits = [["n", "N", e.n], ["p", "P", e.p], ["k", "K", e.k]].filter(([, , x]) => x !== null && x !== undefined);
    return bits.map(([c, l, x]) => `<span class="npk ${c}">${l} ${num(x, 1)}</span>`).join("");
  }

  // ---- plant (variety) view -----------------------------------------------------------
  _varietyView(v) {
    const arch = v.archived, tree = v.kind === "tree", id = v.id;
    let h = `<div class="hd">${this._btn("back", "arrow-left", "", "", "ic")}<div class="grow"><div class="ttl">${esc(v.name)}</div><div class="sub">${esc(v.species_name)}, ${esc(v.garden_name)}${tree ? "" : `, ${v.alive} of ${v.count} plants alive`}</div></div>${arch ? "" : this._btn("edit-v", "pencil", "", `data-v="${id}"`, "ic")}</div>`;
    if (arch) {
      h += `<div class="card"><span class="pill info">${esc(ARCH_TEXT[arch.reason])}, ${fmtDate(arch.date, true)}</span>${arch.notes ? `<p style="margin:8px 0 0">${esc(arch.notes)}</p>` : ""}<div class="row" style="margin-top:10px">${this._btn("form-again", "sprout", "Plant again", `data-v="${id}"`, "primary")}${this._btn("restore", "undo", "Restore", `data-v="${id}"`)}</div></div>`;
    } else {
      h += `<div class="card"><div class="row">${this._picBox(v)}<div class="grow"><span class="pill ${v.status.level}" style="margin:0">${esc(v.status.text)}</span></div></div>${this._statGrid(this._stats(v))}${tree ? "" : `<div class="row" style="margin-top:10px"><button class="grow" data-act="form-stage" data-v="${id}">${this._icon("sprout")} Log up-potting or in-ground</button></div>`}</div>`;
    }
    h += this._projection(v);
    h += this._harvestCard(v, arch);
    if (tree) h += this._sprayCard(v, arch);
    h += this._feedCard(v, arch, tree);
    h += this._adjunctChips(v);
    h += `<div class="card"><div class="row"><div class="sec grow" style="margin:0">Notes for next year</div>${arch ? "" : this._btn("form-review", "plus", "Add", `data-v="${id}"`)}</div>${v.notes ? `<p class="small" style="margin:6px 0">${esc(v.notes)}</p>` : ""}${v.reviews.map((r) => this._logRow("review", id, r.id, esc(r.notes), String(r.year))).join("") || `<div class="small mut" style="margin-top:6px">No notes yet.</div>`}</div>`;
    if (!arch) {
      if (tree) h += `<div class="card">${this._confirm === "rm" ? `<div class="conf">Remove ${esc(v.name)} and all its history? This can't be undone.<div class="row"><button data-act="cancel-del">Keep</button><button class="danger" data-act="do-rm" data-v="${id}">Remove tree</button></div></div>` : `<button class="danger" data-act="ask-rm">${this._icon("delete-outline")} Remove tree</button>`}</div>`;
      else h += `<div class="card">${this._btn("form-pull", "archive", "Pull plant", `data-v="${id}"`, "danger")}<div class="small mut" style="margin-top:6px">Moves it to Past plants. Harvests, fertilizer, and notes are kept for next year.</div></div>`;
    }
    return h;
  }
  _projection(v) {
    const p = v.projection;
    if (!p && !v.expected_harvest) return "";
    let h = `<div class="card"><div class="sec">${p ? "Projected harvest, from your past seasons" : "Expected harvest"}</div>`;
    if (p) {
      const d = p.vs_last_days;
      const cmp = d === 0 ? "same day as last season" : `${Math.abs(d)} day${Math.abs(d) === 1 ? "" : "s"} ${d < 0 ? "earlier" : "later"} than last season`;
      h += `<div class="row" style="align-items:baseline"><span class="big">${fmtDate(p.date)}</span><span class="small mut">${cmp}</span></div><div class="small mut">${p.yield_total ? `About ${num(p.yield_total, 1)} lb total (${num(p.yield_per_plant, 1)} lb per plant). ` : ""}Based on ${p.basis_seasons} season${p.basis_seasons === 1 ? "" : "s"}, using ${esc(p.method)}.</div>`;
      if (v.expected_harvest) h += `<div class="small mut" style="margin-top:4px">Your entered date: ${fmtDate(v.expected_harvest)}</div>`;
    } else {
      h += `<div class="row" style="align-items:baseline"><span class="big">${fmtDate(v.expected_harvest)}</span><span class="small mut">${dIn(v.days_to_expected)}${v.expected_yield ? `, about ${num(v.expected_yield * v.alive, 1)} lb expected` : ""}</span></div>`;
    }
    return h + `</div>`;
  }
  _harvestCard(v, arch) {
    const id = v.id;
    let h = `<div class="card"><div class="row"><div class="grow"><div class="sec" style="margin:0">Harvest</div><div class="big">${num(v.total_lbs, 1)} lb</div></div>${!arch && v.alive ? this._btn("form-harvest", "basket", "Log harvest", `data-v="${id}"`, "primary") : ""}</div>`;
    if (!arch && !v.alive) h += `<div class="small mut">No living plants to receive a harvest.</div>`;
    if (v.grouped) {
      h += `<div class="plant"><div class="row"><div class="grow"><b style="font-weight:500">${v.alive} of ${v.count} plants alive</b><div class="small mut">Average ${num(v.per_plant_avg, 2)} lb per plant. Each pick is split evenly across the living plants.</div></div>${!arch && v.alive ? this._btn("form-lost", "alert", "Mark lost", `data-v="${id}"`) : ""}</div>`;
      for (const g of v.lost) {
        h += `<div class="row" style="margin-top:8px"><div class="pill bad grow" style="margin:0">${g.count} ${g.status === "pulled" ? "pulled early" : "died"}, ${esc(REASON_TEXT[g.reason] || g.reason)}${g.date ? ` · ${fmtDate(g.date)}` : ""}${g.note ? `: ${esc(g.note)}` : ""}</div>${arch ? "" : `<button data-act="restore-lost" data-v="${id}" data-n="${g.count}" data-s="${g.status}" data-r="${esc(g.reason)}" data-d="${g.date || ""}">Restore</button>`}</div>`;
      }
      h += `</div>`;
    } else for (const p of v.plants) {
      h += `<div class="plant"><div class="row"><b style="font-weight:500" class="grow">${esc(p.label)}</b><span style="font-size:18px;font-weight:500">${num(p.total, 1)} lb</span></div>`;
      if (p.status !== "alive") h += `<div class="pill bad" style="margin:6px 0 0">${esc(STATUS_TEXT[p.status])}, ${esc(REASON_TEXT[p.reason] || p.reason)}${p.note ? `: ${esc(p.note)}` : ""}</div>`;
      if (!arch) h += `<div class="seg" style="margin-top:8px">${["alive", "dead", "pulled"].map((s) => `<button class="${p.status === s ? (s === "alive" ? "on" : "bad") : ""}" data-act="${s === "alive" ? "plant-alive" : "form-status"}" data-v="${id}" data-p="${p.id}" data-s="${s}">${STATUS_TEXT[s]}</button>`).join("")}</div>`;
      h += `</div>`;
    }
    if (v.harvests.length) h += `<div class="sec" style="margin:12px 0 0">Pick history</div>`;
    for (const x of v.harvests) {
      h += this._logRow("harvest", id, x.id, `${fmtDate(x.date)}, ${num(x.lbs)} lb`,
        `${num(x.each)} lb each to ${esc(x.to_text)}${x.notes ? ` · ${esc(x.notes)}` : ""}`, `This takes ${num(x.each)} lb off each plant that received it.`);
    }
    return h + `</div>`;
  }
  _sprayCard(v, arch) {
    const s = v.spray, id = v.id;
    let h = `<div class="card"><div class="row"><div class="sec grow" style="margin:0">Pest management</div>${arch ? "" : this._btn("form-spray", "spray", "Sprayed", `data-v="${id}"`, "primary")}</div>`;
    h += this._statGrid([["Next spray", s.next_in === null ? "–" : dIn(s.next_in)], ["Safe to harvest", s.safe_in === null ? "–" : s.safe_in === 0 ? "now" : `${s.safe_in} d`], ["Spray cutoff", s.cutoff_in === null ? "–" : dIn(s.cutoff_in)]]);
    for (const p of v.pests) {
      if (p.status) {
        const st = p.status;
        h += `<div style="margin-top:10px;font-size:12px" class="row"><span class="grow">${esc(p.name)} degree days</span><b>${st.dd}${st.next_dd ? ` / ${st.next_dd}` : ""}</b></div><div class="bar"><i style="width:${st.next_dd ? Math.min(100, (st.dd / st.next_dd) * 100) : 100}%"></i></div>${st.next_action ? `<div class="small mut" style="margin-top:4px">${esc(st.next_action)}${p.est_days ? `, in about ${p.est_days} days` : ""}</div>` : ""}`;
      } else if (p.needs_biofix && !arch) {
        h += `<div style="margin-top:10px" class="row"><span class="small grow">${esc(p.name)}: set the biofix date to start counting</span>${this._btn("form-biofix", "calendar", "Set biofix", `data-v="${id}" data-s="${p.key}"`)}</div>`;
      }
    }
    if (v.sprays.length) h += `<div class="sec" style="margin:12px 0 0">Spray log</div>`;
    for (const x of v.sprays) {
      const bits = [x.target, x.phi_days !== null && x.phi_days !== undefined ? `PHI ${x.phi_days} d` : null, x.reapply_days ? `reapply ${x.reapply_days} d` : null].filter(Boolean);
      h += this._logRow("spray", id, x.id, `${esc(x.product)}`, `${fmtDate(x.date)}${bits.length ? " · " + esc(bits.join(", ")) : ""}`);
    }
    return h + `</div>`;
  }
  _feedCard(v, arch, tree) {
    if (tree && !v.fertilizations.length) {
      return arch ? "" : `<div class="card"><div class="row"><div class="small mut grow">Feeding is optional for trees.</div>${this._btn("form-fert", "sprout", "Log feeding", `data-v="${v.id}"`)}</div></div>`;
    }
    let h = `<div class="card"><div class="row"><div class="sec grow" style="margin:0">Fertilizer</div>${arch ? "" : this._btn("form-fert", "sprout", "Fertilized", `data-v="${v.id}"`, "primary")}</div>`;
    if (v.feeding) {
      const f = v.feeding;
      h += `<div class="phases" style="grid-template-columns:repeat(${f.phases.length},minmax(0,1fr))">${f.phases.map((ph, i) => `<div class="phase ${i === f.current ? "cur" : ""}">${esc(ph.name)}<b>${esc(ph.focus)}</b></div>`).join("")}</div>`;
    }
    if (v.last_fert) h += `<div class="small" style="margin-top:8px">${this._npk(v.last_fert)} <span class="mut">${esc(v.last_fert.product)}, ${dAgo(v.days.fertilized)} ago</span></div>`;
    for (const e of v.fertilizations) h += this._logRow("fertilizer", v.id, e.id, `${esc(e.product)} ${this._npk(e)}`, fmtDate(e.date) + (e.notes ? " · " + esc(e.notes) : ""));
    return h + `</div>`;
  }
  _adjunctChips(v) {
    const g = this._garden(v.garden);
    if (!g) return "";
    const used = g.adjuncts.filter((a) => a.last);
    if (!used.length) return "";
    return `<div class="card"><div class="sec">From ${esc(g.name)}</div>${used.map((a) => `<span class="npk" style="background:var(--secondary-background-color)">${esc(a.name)}, ${fmtDate(a.last.date)}</span>`).join("")}</div>`;
  }

  // ---- garden view ------------------------------------------------------------------------
  _gardenView(g) {
    const ph = g.ph, gid = g.id;
    let h = `<div class="hd">${this._btn("back", "arrow-left", "", "", "ic")}<div class="grow"><div class="ttl">${esc(g.name)}</div><div class="sub">${this._vars().filter((v) => v.garden === gid).length} plants</div></div>${this._btn("edit-g", "cog", "", `data-g="${gid}"`, "ic")}</div>`;
    h += `<div class="card"><div class="row"><div class="sec grow" style="margin:0">Soil pH</div>${ph.level ? `<span class="pill ${ph.level === "ok" ? "ok" : "warn"}" style="margin:0">${ph.level === "ok" ? "In range" : ph.level === "low" ? "Below target" : "Above target"}</span>` : ""}</div>`;
    if (ph.current !== null) {
      const d = ph.first && ph.first.date !== ph.date ? ph.current - ph.first.value : null;
      h += `<div class="row" style="align-items:baseline;margin:6px 0"><span class="ph">${num(ph.current, 1)}</span><span class="small mut">target ${ph.target[0]} to ${ph.target[1]}${d !== null ? `, ${d < 0 ? "down" : "up"} ${Math.abs(d).toFixed(1)} since ${fmtDate(ph.first.date)}` : ""}</span></div>`;
      h += `<div class="small mut" style="margin-bottom:8px">${ph.source === "sensor" ? "Sensor" : "Manual reading"}, ${fmtDate(ph.date)}</div>`;
    } else h += `<div class="small mut" style="margin:6px 0">No readings yet. Pick a sensor in settings or log one by hand.</div>`;
    h += phChart(ph, g.adjunct_log);
    h += `<div class="row" style="margin-top:8px">${this._btn("form-ph", "plus", "Log reading", `data-g="${gid}"`)}</div>`;
    const recent = ph.history.slice().reverse().slice(0, 5);
    for (const r of recent) h += this._logRow("ph", gid, r.id, `pH ${num(r.value, 1)}`, `${fmtDate(r.date)}, ${r.source}`);
    h += `</div><div class="card"><div class="row"><div class="sec grow" style="margin:0">Soil adjuncts this season</div>${this._btn("form-atype", "plus", "Add", `data-g="${gid}"`)}</div>`;
    for (const a of g.adjuncts) {
      const per = a.per_year || 0;
      const pips = per ? `<div class="pips" style="--c:var(--${a.level === "ok" ? "ok" : "spray"})">${Array.from({ length: per }, (_, i) => `<i class="${i < a.count ? "f" : ""}"></i>`).join("")}</div>` : "";
      const sub = a.last ? `Last ${fmtDate(a.last.date)}${a.last.amount ? ", " + esc(a.last.amount) : ""}` : "Not applied yet";
      h += `<div class="adj ${a.level}"><div class="dot">${this._icon("flask-outline")}</div><div class="grow"><b style="font-weight:500;font-size:14px">${esc(a.name)}</b><div class="small mut">${sub}</div>${pips}</div><div style="text-align:right"><span class="pill ${a.level}" style="margin:0">${esc(a.label)}</span><div style="margin-top:4px"><button data-act="form-adj" data-g="${gid}" data-s="${a.key}">Log</button></div></div></div>`;
    }
    const log = g.adjunct_log;
    h += `<button style="width:100%;margin-top:8px" data-act="toggle-log">${this._icon(this._showLog ? "chevron-up" : "chevron-down")} Application log (${log.length})</button>`;
    if (this._showLog) for (const e of log) h += this._logRow("adjunct", gid, e.id, esc(e.type_name) + (e.product ? `, ${esc(e.product)}` : ""), fmtDate(e.date) + (e.amount ? ` · ${esc(e.amount)}` : ""));
    h += `</div>`;
    const mine = this._vars().filter((v) => v.garden === gid);
    h += `<div class="card"><div class="sec">Plants in this garden</div>${mine.map((v) => `<div class="lg" style="cursor:pointer" data-act="open-v" data-v="${v.id}"><div class="t">${esc(v.name)}<span>${esc(v.species_name)}${v.kind === "tree" ? "" : `, ${v.alive} of ${v.count} plants`}</span></div>${this._icon("chevron-right")}</div>`).join("") || `<div class="small mut">None yet.</div>`}<div class="row" style="margin-top:8px">${this._btn("form-variety", "plus", "Add plant", `data-g="${gid}"`)}</div></div>`;
    if (!mine.length) h += `<div class="card">${this._confirm === "rmg" ? `<div class="conf">Remove ${esc(g.name)}? Its adjunct and pH history will be lost.<div class="row"><button data-act="cancel-del">Keep</button><button class="danger" data-act="do-rmg" data-g="${gid}">Remove garden</button></div></div>` : `<button class="danger" data-act="ask-rmg">Remove garden</button>`}</div>`;
    return h;
  }

  // ---- past plants -----------------------------------------------------------------------------
  _archiveView() {
    const vs = this._vars(true);
    const years = [...new Set(vs.map((v) => v.archived.year))].sort((a, b) => b - a);
    let h = `<div class="hd">${this._btn("back", "arrow-left", "", "", "ic")}<div class="ttl grow">Past plants</div></div>`;
    for (const y of years) {
      h += `<div class="sec">${y}</div>`;
      for (const v of vs.filter((x) => x.archived.year === y)) {
        h += `<div class="card"><div class="row"><div class="grow" style="cursor:pointer" data-act="open-v" data-v="${v.id}"><div style="font-weight:500">${esc(v.name)}</div><div class="sub">${esc(v.species_name)}, ${v.count} plant${v.count === 1 ? "" : "s"}, ${num(v.total_lbs, 1)} lb, ${esc(ARCH_TEXT[v.archived.reason])}</div></div>${this._btn("form-again", "sprout", "Plant again", `data-v="${v.id}"`)}</div></div>`;
      }
    }
    return h || `<div class="msg">Nothing archived yet.</div>`;
  }

  // ---- events ------------------------------------------------------------------------------------
  _onClick(e) {
    const el = e.target.closest("[data-act]");
    if (!el) return;
    const a = el.dataset.act, d = el.dataset;
    const home = () => { this._view = { v: "home" }; this._nav = []; this._confirm = null; };
    switch (a) {
      case "back": return this._back();
      case "open-v": return this._go({ v: "variety", id: d.v });
      case "open-g": return this._go({ v: "garden", id: d.g });
      case "open-archive": return this._go({ v: "archive" });
      case "filter": this._filter = d.s; return this._render();
      case "toggle-log": this._showLog = !this._showLog; return this._render();
      case "undo": return this._act("undo_delete", {}, () => { this._undo = false; });
      case "ask-del": this._confirm = d.key; return this._render();
      case "ask-rm": this._confirm = "rm"; return this._render();
      case "ask-rmg": this._confirm = "rmg"; return this._render();
      case "cancel-del": this._confirm = null; return this._render();
      case "do-del":
        return this._act("delete_entry", { kind: d.k, parent: d.p, entry_id: d.e }, () => {
          this._confirm = null; this._undo = true;
          clearTimeout(this._undoTimer);
          this._undoTimer = setTimeout(() => { this._undo = false; if (!this._form) this._render(); }, 10000);
        });
      case "do-rm": return this._act("remove_plant", { plant: d.v }, home);
      case "do-rmg": return this._act("remove_garden", { garden: d.g }, home);
      case "restore": return this._act("restore_plant", { plant: d.v }, () => this._back());
      case "plant-alive": return this._act("set_plant_status", { plant: d.v, individual: d.p, status: "alive" });
      case "form-variety": return this._open(this._fVariety(d.g));
      case "form-garden": return this._open(this._fGarden());
      case "edit-g": return this._open(this._fGarden(this._garden(d.g)));
      case "edit-v": return this._open(this._fEditVariety(this._variety(d.v)));
      case "form-harvest": return this._open(this._fHarvest(this._variety(d.v)));
      case "form-fert": return this._open(this._fFert(this._variety(d.v)));
      case "form-spray": return this._open(this._fSpray(this._variety(d.v)));
      case "form-lost": return this._open(this._fLost(this._variety(d.v)));
      case "restore-lost": return this._act("restore_plants", { plant: d.v, count: Number(d.n), status: d.s, reason: d.r, ...(d.d ? { date: d.d } : {}) });
      case "form-status": return this._open(this._fStatus(this._variety(d.v), d.p, d.s));
      case "form-pull": return this._open(this._fPull(this._variety(d.v)));
      case "form-again": return this._open(this._fAgain(this._variety(d.v)));
      case "form-review": return this._open(this._fReview(this._variety(d.v)));
      case "form-stage": return this._open(this._fStage(this._variety(d.v)));
      case "form-biofix": return this._open(this._fBiofix(this._variety(d.v), d.s));
      case "form-adj": return this._open(this._fAdjunct(this._garden(d.g), d.s));
      case "form-ph": return this._open(this._fPh(this._garden(d.g)));
      case "form-atype": return this._open(this._fAType(this._garden(d.g)));
      case "edit-entry": return this._open(this._fEntry(d.k, d.p, d.e));
      case "pick": this._form.values[d.f] = d.val; return this._render();
      case "use-days": this._form.values.days_to_harvest = d.n; return this._render();
      case "form-cancel": this._form = null; return this._render();
      case "form-submit": return this._submit();
    }
  }
  _onInput(e, isChange) {
    const el = e.target, name = el.dataset && el.dataset.f;
    if (!name || !this._form || el.tagName === "BUTTON") return;
    const isSelect = el.tagName === "SELECT";
    if (isSelect !== isChange) return;
    this._form.values[name] = el.value;
    if (isSelect) this._render();
    else this._updatePreview();
  }
  _updatePreview() {
    const pv = this.shadowRoot.getElementById("pv");
    if (pv && this._form && this._form.preview) pv.innerHTML = this._form.preview(this._form.values);
  }

  // ---- generic form engine --------------------------------------------------------------------------
  _open(f) {
    f.values = {};
    for (const x of f.fields) f.values[x.name] = x.value === undefined || x.value === null ? "" : String(x.value);
    this._form = f;
    this._confirm = null;
    this._render();
  }
  _typed(f) {
    const out = {};
    for (const x of f.fields) {
      if (x.show && !x.show(f.values)) continue;
      const raw = f.values[x.name];
      out[x.name] = raw === "" || raw === undefined ? undefined : x.type === "number" ? Number(raw) : raw;
    }
    return out;
  }
  async _submit() {
    const f = this._form, vals = this._typed(f);
    const missing = f.fields.filter((x) => (!x.show || x.show(f.values)) && x.req && vals[x.name] === undefined);
    if (missing.length) { f.err = `Fill in: ${missing.map((x) => x.label || x.name).join(", ")}`; return this._render(); }
    try { await f.submit(vals); this._form = null; this._err = null; if (f.after) f.after(); }
    catch (e) { f.err = e.message || String(e); }
    this._render();
  }
  _formView() {
    const f = this._form, vals = f.values;
    let h = `<div class="hd">${this._btn("form-cancel", "close", "", "", "ic")}<div class="ttl grow">${esc(f.title)}</div></div>`;
    if (f.err) h += `<div class="err">${esc(f.err)}</div>`;
    h += `<div class="card"><div class="grid6">`;
    for (const x of f.fields.filter((y) => !y.show || y.show(vals))) {
      const label = x.labelFn ? x.labelFn(vals) : x.label, val = vals[x.name] ?? "";
      let ctl;
      if (x.type === "select") ctl = `<select data-f="${x.name}">${x.options.map(([v, t]) => `<option value="${esc(v)}" ${String(val) === String(v) ? "selected" : ""}>${esc(t)}</option>`).join("")}</select>`;
      else if (x.type === "seg" || x.type === "chips") ctl = `<div class="seg">${x.options.map(([v, t]) => `<button data-act="pick" data-f="${x.name}" data-val="${esc(v)}" class="${val === v ? "on" : ""}">${esc(t)}</button>`).join("")}</div>`;
      else if (x.type === "textarea") ctl = `<textarea data-f="${x.name}" rows="3">${esc(val)}</textarea>`;
      else ctl = `<input data-f="${x.name}" type="${x.type || "text"}" value="${esc(val)}" ${x.step ? `step="${x.step}"` : ""} ${x.placeholder ? `placeholder="${esc(x.placeholder)}"` : ""} ${x.type === "number" ? 'inputmode="decimal"' : ""}>`;
      h += `<div style="grid-column:span ${x.span || 6}"><label>${esc(label)}${x.req ? " *" : ""}</label>${ctl}</div>`;
    }
    h += `</div>${f.note ? `<p class="small mut">${f.note}</p>` : ""}<div id="pv">${f.preview ? f.preview(vals) : ""}</div>`;
    h += `<div class="row" style="margin-top:12px"><button class="grow" data-act="form-cancel">Cancel</button><button class="grow primary" data-act="form-submit">${esc(f.submitLabel || "Save")}</button></div></div>`;
    return h;
  }

  // ---- form definitions -----------------------------------------------------------------------------------
  _isoAdd(iso, n) {
    const d = new Date(iso + "T00:00:00"); d.setDate(d.getDate() + n);
    const p = (x) => String(x).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
  }
  _fVariety(gid) {
    const gs = this._gardens(), today = this._snap.today;
    const sp = Object.values(this._snap.species).sort((a, b) => a.name.localeCompare(b.name));
    const slug = (t) => String(t).toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
    const key = (v) => (v.species === "other" ? slug(v.species_other || "") : v.species);
    const kind = (v) => (v.species === "other" ? v.kind : (this._snap.species[v.species] || {}).kind || "plant");
    return {
      title: "Add plant", submitLabel: "Add plant",
      fields: [
        { name: "garden", label: "Garden", type: "select", options: gs.map((g) => [g.id, g.name]), value: gid || gs[0].id, span: 3 },
        { name: "species", label: "Type", type: "select", options: [...sp.map((s) => [s.key, s.name]), ["other", "Other..."]], value: this._snap.species.tomato ? "tomato" : sp[0] ? sp[0].key : "other", span: 3 },
        { name: "species_other", label: "Type name", type: "text", req: true, show: (v) => v.species === "other", span: 3 },
        { name: "kind", label: "Kind", type: "seg", options: [["plant", "Plant"], ["tree", "Tree"]], value: "plant", show: (v) => v.species === "other", span: 3 },
        { name: "variety", label: "Variety", type: "text", req: true, placeholder: "Sungold" },
        { name: "plants", label: "Number of plants", type: "number", step: "1", value: 1, span: 3 },
        { name: "origin", label: "Started from", type: "seg", options: [["seed", "Seed"], ["start", "Start"]], value: "start", span: 3 },
        { name: "planted_date", labelFn: (v) => (v.origin === "seed" ? "Sow date" : kind(v) === "tree" ? "Planting date" : "Transplant date"), type: "date", value: today, span: 3 },
        { name: "days_to_harvest", label: "Days to harvest", type: "number", step: "1", show: (v) => kind(v) !== "tree", span: 3 },
        { name: "expected_harvest_date", label: "Expected harvest date", type: "date", show: (v) => kind(v) === "tree", span: 3 },
        { name: "expected_yield", label: "Expected yield per plant (lb)", type: "number", step: "0.1" },
        { name: "notes", label: "Notes", type: "text" },
      ],
      note: "Days to harvest is counted from transplanting, like a seed packet. For seed-sown crops it is counted from sowing.",
      preview: (v) => {
        let h = "";
        if (kind(v) !== "tree" && v.days_to_harvest && v.planted_date) h += `<div class="pill ok">Expected first harvest ${fmtDate(this._isoAdd(v.planted_date, Number(v.days_to_harvest)), true)}</div>`;
        const past = this._snap.varieties.filter((x) => x.species === key(v) && v.variety && x.name.toLowerCase() === v.variety.toLowerCase());
        const s = past.map((x) => x.seasons).sort((a, b) => b.length - a.length)[0];
        const last = s && s.filter((z) => z.days_to_first !== null).pop();
        if (last && kind(v) !== "tree") h += `<div class="small" style="margin-top:8px">From your past seasons: ${esc(v.variety)} took ${last.days_to_first} days. <button data-act="use-days" data-n="${last.days_to_first}">Use ${last.days_to_first}</button></div>`;
        return h;
      },
      submit: (v) => this._call("add_variety", { garden: v.garden, species: v.species === "other" ? v.species_other : v.species, variety: v.variety, plants: v.plants, origin: v.origin, planted_date: v.planted_date, days_to_harvest: v.days_to_harvest, expected_harvest_date: v.expected_harvest_date, expected_yield: v.expected_yield, notes: v.notes, kind: v.species === "other" ? v.kind : undefined }),
    };
  }
  _fEditVariety(v) {
    return {
      title: `Edit ${v.name}`,
      fields: [
        { name: "name", label: "Variety name", type: "text", value: v.name, req: true },
        { name: "planted_date", label: "Planted or transplanted", type: "date", value: v.planted, span: 3 },
        { name: "in_ground_date", label: "In ground", type: "date", value: v.in_ground, span: 3 },
        ...(v.kind === "tree" ? [] : [{ name: "days_to_harvest", label: "Days to harvest", type: "number", step: "1", value: v.days_to_harvest, span: 3 }]),
        { name: "expected_harvest_date", label: "Expected harvest date", type: "date", value: v.expected_harvest, span: 3 },
        { name: "expected_yield", label: "Expected yield per plant (lb)", type: "number", step: "0.1", value: v.expected_yield, span: 3 },
        { name: "add_plants", label: "Add plants", type: "number", step: "1", span: 3 },
        { name: "notes", label: "Notes", type: "textarea", value: v.notes },
      ],
      submit: (x) => this._call("update_variety", { plant: v.id, ...x }),
    };
  }
  _fStage(v) {
    return {
      title: `Log stage: ${v.name}`,
      fields: [
        { name: "stage", label: "Stage", type: "seg", options: [["upotted", "Up-potted"], ["in_ground", "In ground"], ["planted", "Planted"]], value: "upotted" },
        { name: "date", label: "Date", type: "date", value: this._snap.today },
      ],
      submit: (x) => this._call("log_stage", { plant: v.id, ...x }),
    };
  }
  _fHarvest(v) {
    return {
      title: `Log harvest: ${v.name}`, submitLabel: "Log harvest",
      fields: [
        { name: "lbs", label: "Pounds picked", type: "number", step: "0.1", req: true, span: 3 },
        { name: "date", label: "Date", type: "date", value: this._snap.today, span: 3 },
        { name: "notes", label: "Notes", type: "text" },
      ],
      preview: (x) => {
        const l = Number(x.lbs);
        if (!(l > 0)) return "";
        if (!v.alive) return `<div class="err">No living plants to receive this harvest</div>`;
        return `<div class="small mut">${num(l)} lb split across ${v.alive} living plant${v.alive === 1 ? "" : "s"}: ${num(l / v.alive)} lb each</div>`;
      },
      submit: (x) => this._call("log_harvest", { plant: v.id, ...x }),
    };
  }
  _fFert(v) {
    const l = v.last_fert || {};
    const ph = v.feeding ? v.feeding.phases[v.feeding.current] : null;
    return {
      title: `Fertilized: ${v.name}`, submitLabel: "Log feeding",
      fields: [
        { name: "product", label: "Product", type: "text", req: true, value: l.product },
        { name: "n", label: "N", type: "number", step: "0.1", value: l.n, span: 2 },
        { name: "p", label: "P", type: "number", step: "0.1", value: l.p, span: 2 },
        { name: "k", label: "K", type: "number", step: "0.1", value: l.k, span: 2 },
        { name: "date", label: "Date", type: "date", value: this._snap.today },
        { name: "notes", label: "Notes", type: "text" },
      ],
      preview: () => (ph ? `<div class="small mut">Current stage: ${esc(ph.name)}. Focus: ${esc(ph.focus)}.</div>` : ""),
      submit: (x) => this._call("log_fertilizer", { plant: v.id, ...x }),
    };
  }
  _fSpray(v) {
    const l = v.sprays[0] || {};
    return {
      title: `Sprayed: ${v.name}`, submitLabel: "Log spray",
      fields: [
        { name: "product", label: "Product", type: "text", req: true, value: l.product },
        { name: "target", label: "Target pest", type: "text", value: l.target || (v.pests[0] ? v.pests[0].name : "") },
        { name: "date", label: "Date", type: "date", value: this._snap.today },
        { name: "phi_days", label: "Days before harvest (label)", type: "number", step: "1", value: l.phi_days, span: 3 },
        { name: "reapply_days", label: "Reapply after days (label)", type: "number", step: "1", value: l.reapply_days, span: 3 },
      ],
      note: "Take the pre-harvest and reapply intervals from the product label.",
      submit: (x) => this._call("log_spray", { plant: v.id, ...x }),
    };
  }
  _fStatus(v, pid, status) {
    const p = v.plants.find((x) => x.id === pid);
    return {
      title: `Why was ${p.label} ${status === "dead" ? "lost" : "pulled early"}?`, submitLabel: "Confirm",
      fields: [
        { name: "reason", label: "Reason", type: "chips", options: Object.entries(REASON_TEXT), req: true },
        { name: "note", label: "Note (optional)", type: "text", placeholder: "Blossom end rot" },
      ],
      note: "Its harvest so far stays on this plant. Later picks are split across the plants still alive.",
      submit: (x) => this._call("set_plant_status", { plant: v.id, individual: pid, status, ...x }),
    };
  }
  _fLost(v) {
    return {
      title: `Plants lost: ${v.name}`, submitLabel: "Confirm",
      fields: [
        { name: "count", label: `How many (of ${v.alive} alive)`, type: "number", step: "1", req: true, span: 3 },
        { name: "status", label: "What happened", type: "seg", options: [["dead", "Died"], ["pulled", "Pulled early"]], value: "dead", span: 3 },
        { name: "reason", label: "Reason", type: "chips", options: Object.entries(REASON_TEXT), req: true },
        { name: "date", label: "Date", type: "date", value: this._snap.today, span: 3 },
        { name: "note", label: "Note (optional)", type: "text", span: 3 },
      ],
      note: "Harvest so far stays with the lost plants. Later picks are split across the plants still alive.",
      submit: (x) => this._call("mark_plants_lost", { plant: v.id, ...x }),
    };
  }
  _fPull(v) {
    return {
      title: `Pull ${v.name}`, submitLabel: "Archive plant",
      fields: [
        { name: "reason", label: "Why", type: "seg", options: Object.entries(ARCH_TEXT), value: "season_over" },
        { name: "final_lbs", label: "Final harvest (lb, optional)", type: "number", step: "0.1", span: 3 },
        { name: "date", label: "Date pulled", type: "date", value: this._snap.today, span: 3 },
        { name: "notes", label: "Notes for next year", type: "textarea", placeholder: "Great flavor, split after rain" },
      ],
      note: "Kept for next year: harvest dates and yields, fertilizer log, days to harvest, and your notes. The plant moves to Past plants.",
      submit: (x) => this._call("archive_plant", { plant: v.id, ...x }),
      after: () => { this._view = { v: "home" }; this._nav = []; },
    };
  }
  _fAgain(v) {
    const gs = this._snap.gardens;
    return {
      title: `Plant ${v.name} again`, submitLabel: "Add plants",
      fields: [
        { name: "garden", label: "Garden", type: "select", options: gs.map((g) => [g.id, g.name]), value: gs.some((g) => g.id === v.garden) ? v.garden : gs[0].id },
        { name: "plants", label: "Number of plants", type: "number", step: "1", value: v.count, span: 3 },
        { name: "planted_date", label: "Planting date", type: "date", value: this._snap.today, span: 3 },
      ],
      note: "Copies the variety and days to harvest. Past seasons feed the projection automatically.",
      submit: (x) => this._call("plant_again", { plant: v.id, ...x }),
      after: () => { this._view = { v: "home" }; this._nav = []; },
    };
  }
  _fReview(v) {
    return {
      title: `Note for next year: ${v.name}`,
      fields: [
        { name: "notes", label: "Note", type: "textarea", req: true },
        { name: "year", label: "Season", type: "number", step: "1", value: new Date().getFullYear() },
      ],
      submit: (x) => this._call("add_review", { plant: v.id, ...x }),
    };
  }
  _fBiofix(v, pest) {
    const p = v.pests.find((x) => x.key === pest);
    return {
      title: `Biofix: ${p ? p.name : pest}`,
      fields: [{ name: "date", label: "Date of first sustained catch", type: "date", value: this._snap.today }],
      submit: (x) => this._call("set_biofix", { plant: v.id, pest, ...x }),
    };
  }
  _fGarden(g) {
    return {
      title: g ? `Edit ${g.name}` : "Add garden",
      fields: [
        { name: "name", label: "Name", type: "text", req: true, value: g && g.name },
        { name: "ph_entity", label: "Soil pH sensor (optional)", type: "text", placeholder: "sensor.garden_soil_ph", value: g && g.ph.entity },
        { name: "ph_min", label: "Target pH from", type: "number", step: "0.1", value: g ? g.ph.target[0] : 6.0, span: 3 },
        { name: "ph_max", label: "Target pH to", type: "number", step: "0.1", value: g ? g.ph.target[1] : 6.8, span: 3 },
      ],
      note: "Leave the sensor empty to log pH by hand.",
      submit: (x) => (g ? this._call("update_garden", { garden: g.id, ...x, ph_entity: x.ph_entity === undefined ? " " : x.ph_entity }) : this._call("add_garden", x)),
    };
  }
  _fAdjunct(g, key) {
    return {
      title: `Log adjunct: ${g.name}`, submitLabel: "Log",
      fields: [
        { name: "adjunct", label: "Adjunct", type: "select", options: g.adjuncts.map((a) => [a.key, a.name]), value: key },
        { name: "date", label: "Date", type: "date", value: this._snap.today, span: 3 },
        { name: "amount", label: "Amount", type: "text", placeholder: "2 lb per bed", span: 3 },
        { name: "product", label: "Product", type: "text" },
        { name: "notes", label: "Notes", type: "text" },
      ],
      submit: (x) => this._call("log_adjunct", { garden: g.id, ...x }),
    };
  }
  _fAType(g) {
    return {
      title: "Add adjunct", submitLabel: "Add",
      fields: [
        { name: "name", label: "Name", type: "text", req: true, placeholder: "Lime, kelp, bone meal" },
        { name: "mode", label: "How often", type: "seg", options: [["per_year", "Times per year"], ["interval_days", "Every N days"]], value: "per_year" },
        { name: "count", label: "Number", type: "number", step: "1", value: 1, req: true },
      ],
      submit: (x) => this._call("add_adjunct_type", { garden: g.id, name: x.name, [x.mode]: x.count }),
    };
  }
  _fPh(g) {
    return {
      title: `Log pH: ${g.name}`, submitLabel: "Log",
      fields: [
        { name: "value", label: "pH", type: "number", step: "0.1", req: true, span: 3 },
        { name: "date", label: "Date", type: "date", value: this._snap.today, span: 3 },
      ],
      note: "From a test kit or lab report.",
      submit: (x) => this._call("log_ph", { garden: g.id, ...x }),
    };
  }
  _findEntry(kind, parent, id) {
    const v = this._variety(parent), g = this._garden(parent);
    const list = { harvest: v && v.harvests, fertilizer: v && v.fertilizations, spray: v && v.sprays, review: v && v.reviews, upotted: v && v.upotted, adjunct: g && g.adjunct_log, ph: g && g.ph.history }[kind];
    return (list || []).find((e) => e.id === id) || {};
  }
  _fEntry(kind, parent, id) {
    const e = this._findEntry(kind, parent, id), g = this._garden(parent);
    const F = {
      harvest: [{ name: "lbs", label: "Pounds", type: "number", step: "0.1", value: e.lbs, req: true, span: 3 }, { name: "date", label: "Date", type: "date", value: e.date, span: 3 }, { name: "notes", label: "Notes", type: "text", value: e.notes }],
      fertilizer: [{ name: "product", label: "Product", type: "text", value: e.product, req: true }, { name: "n", label: "N", type: "number", step: "0.1", value: e.n, span: 2 }, { name: "p", label: "P", type: "number", step: "0.1", value: e.p, span: 2 }, { name: "k", label: "K", type: "number", step: "0.1", value: e.k, span: 2 }, { name: "date", label: "Date", type: "date", value: e.date }, { name: "notes", label: "Notes", type: "text", value: e.notes }],
      spray: [{ name: "product", label: "Product", type: "text", value: e.product, req: true }, { name: "target", label: "Target pest", type: "text", value: e.target }, { name: "date", label: "Date", type: "date", value: e.date }, { name: "phi_days", label: "Days before harvest", type: "number", step: "1", value: e.phi_days, span: 3 }, { name: "reapply_days", label: "Reapply after days", type: "number", step: "1", value: e.reapply_days, span: 3 }],
      review: [{ name: "notes", label: "Note", type: "textarea", value: e.notes, req: true }, { name: "year", label: "Season", type: "number", step: "1", value: e.year }],
      upotted: [{ name: "date", label: "Date", type: "date", value: e.date }],
      adjunct: [{ name: "type", label: "Adjunct", type: "select", options: g ? g.adjuncts.map((a) => [a.key, a.name]) : [], value: e.type }, { name: "date", label: "Date", type: "date", value: e.date, span: 3 }, { name: "amount", label: "Amount", type: "text", value: e.amount, span: 3 }, { name: "product", label: "Product", type: "text", value: e.product }, { name: "notes", label: "Notes", type: "text", value: e.notes }],
      ph: [{ name: "value", label: "pH", type: "number", step: "0.1", value: e.value, req: true, span: 3 }, { name: "date", label: "Date", type: "date", value: e.date, span: 3 }],
    }[kind];
    return {
      title: "Edit entry", fields: F,
      note: kind === "harvest" ? "Changing the pounds re-splits it evenly across the plants that received it." : "",
      submit: (x) => this._call("edit_entry", { kind, parent, entry_id: id, ...x }),
    };
  }
}

customElements.define("garden-tracker-card", GardenTrackerCard);
window.customCards = window.customCards || [];
window.customCards.push({ type: "garden-tracker-card", name: "Garden Tracker", description: "Plants, trees, harvests, adjuncts, soil pH, and sprays", preview: false });
