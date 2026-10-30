/* Garden Tracker card for Home Assistant. Part of the garden_tracker integration. */
const DOMAIN = "garden_tracker";
const REASON_TEXT = { disease: "Disease", pests: "Pests", frost: "Frost", heat: "Heat", water: "Water",
  animal_damage: "Animal damage", other: "Other" };
const ARCH_TEXT = { season_over: "Season over", pulled_early: "Pulled early", died: "Died" };
const STATUS_TEXT = { alive: "Alive", dead: "Dead", pulled: "Pulled early", harvested: "Harvested" };

const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const num = (n, d = 2) => (n === null || n === undefined || n === "" ? "" : String(Math.round(Number(n) * 10 ** d) / 10 ** d));
const fmtMd = (md) => new Date(2000, Number(md.slice(0, 2)) - 1, Number(md.slice(3))).toLocaleDateString(undefined, { month: "short", day: "numeric" });
const fmtDate = (iso, withYear) => {
  if (!iso) return "";
  const d = new Date(iso + "T00:00:00");
  const y = withYear || d.getFullYear() !== new Date().getFullYear();
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric", ...(y ? { year: "numeric" } : {}) });
};
const fmtDur = (ms) => {
  const m = Math.max(1, Math.round(ms / 60000));
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60), r = m % 60;
  if (h < 24) return r ? `${h} h ${r} min` : `${h} h`;
  const d = Math.floor(h / 24), hr = h % 24;
  return hr ? `${d} d ${hr} h` : `${d} d`;
};
const fmtClock = (iso) => new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });
const dAgo = (n) => (n === null || n === undefined ? "–" : `${n} d`);
const dIn = (n) => (n === null || n === undefined ? "–" : n < 0 ? `${-n} d late` : n === 0 ? "today" : `${n} d`);
const yrs = (y) => `${Math.floor(y || 0)} yr${Math.floor(y || 0) === 1 ? "" : "s"}`;

const CSS = `
:host{display:block;width:100%;--ok:var(--success-color,#43a047);--spray:var(--warning-color,#ffa000);--hold:var(--error-color,#db4437);--info:var(--info-color,#039be5);--mut:var(--secondary-text-color);--line:var(--divider-color)}
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
.pdays{text-align:right;flex:none;align-self:flex-start}.pdays span{display:block;font-size:11px;color:var(--mut)}.pdays b{font-size:16px;font-weight:500}
.tiles2{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:12px;margin-bottom:12px}.tiles2 .tile{margin:0;display:flex;flex-direction:column;gap:6px;min-height:112px;padding:14px}.tiles2 .pic{width:36px;height:36px;border-radius:10px}.warn{border-radius:14px;background:color-mix(in srgb,var(--spray) 16%,var(--card-background-color));border:1px solid color-mix(in srgb,var(--spray) 55%,transparent);padding:12px 14px;margin-bottom:8px}.warn.bad{background:color-mix(in srgb,var(--hold) 12%,var(--card-background-color));border-color:color-mix(in srgb,var(--hold) 55%,transparent)}.warn .wt{font-size:15px;font-weight:700}.warn .wb{font-size:14px;line-height:1.4;margin-top:4px}.warn .wa{margin-top:8px;min-height:44px;border-radius:12px;border:1px solid currentColor;background:transparent;font-weight:600;padding:0 14px;color:inherit}.warn summary{font-size:14px;font-weight:600;min-height:44px;display:flex;align-items:center;cursor:pointer}.lgds{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}.lgd{display:inline-flex;align-items:center;gap:6px;min-height:32px;padding:0 10px;border-radius:16px;background:var(--secondary-background-color);font-size:13px}.lgd i{width:10px;height:10px;border-radius:5px;flex:none}.tile{cursor:pointer}.tile:hover{border-color:var(--primary-color)}
.acard{display:flex;gap:12px;align-items:center;border-radius:14px;padding:12px 14px;margin-bottom:8px;cursor:pointer;border:1px solid}.acard.soon{background:color-mix(in srgb,var(--spray) 14%,var(--card-background-color));border-color:color-mix(in srgb,var(--spray) 55%,transparent)}.acard.open{background:color-mix(in srgb,var(--hold) 12%,var(--card-background-color));border-color:color-mix(in srgb,var(--hold) 55%,transparent)}.acard .an{font-size:15px;font-weight:700}.acard .ar{display:flex;flex-direction:column;align-items:center;gap:2px;min-width:84px;text-align:center}.acard .ab{font-size:24px;font-weight:700;line-height:1.1}.acard button{margin-top:6px;width:100%;min-height:44px}.sec.attn{color:var(--spray)}.lbox{border:1px solid var(--line);border-radius:14px;overflow:hidden;margin-bottom:8px}.lrow{display:flex;align-items:center;gap:10px;min-height:44px;padding:0 14px;cursor:pointer}.lrow+.lrow{border-top:1px solid var(--line)}.lrow .sub{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;min-width:0}.lrow .small{white-space:nowrap}.crow{padding:8px 12px;margin-bottom:6px}.crow .pic{width:36px;height:36px;border-radius:10px}.crow .cn{font-size:15px;font-weight:500;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.crow .sub{overflow:hidden;text-overflow:ellipsis;white-space:nowrap}.crow .pill{margin:0;max-width:44%;text-align:center}
.pic{width:56px;height:56px;border-radius:12px;flex:none;display:flex;align-items:center;justify-content:center}
.pill{font-size:12px;padding:2px 10px;border-radius:8px;display:inline-block;margin-top:4px;color:var(--c);background:color-mix(in srgb,var(--c) 16%,transparent)}
.ok{--c:var(--ok)}.spray,.warn{--c:var(--spray)}.hold,.bad,.low,.high{--c:var(--hold)}.info{--c:var(--info)}.none{--c:var(--mut)}
.alarm{background:color-mix(in srgb,var(--hold) 16%,transparent);border:1px solid var(--hold);border-radius:10px;padding:10px 12px;margin:0 0 10px}
.alarm b{color:var(--hold)}.alarm .row{margin-top:8px}
.tbl{width:100%;border-collapse:collapse;font-size:13px}.tbl th{text-align:left;font-weight:500;color:var(--secondary-text-color);padding:4px 6px 4px 0}.tbl td{padding:5px 6px 5px 0;border-top:1px solid var(--divider-color)}
.airleg{display:grid;grid-template-columns:repeat(auto-fit,minmax(62px,1fr));gap:6px;margin:10px 0}.airleg .stat{padding:6px 8px}.airleg .stat span{display:block;font-size:11px}.airleg .stat b{font-size:16px}
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

// Phone layout for the standalone web app only (the card is given web:true there). The Home Assistant card never gets these rules.
const WEB_PHONE_CSS = `
@media (max-width:600px){
ha-card.web{padding:4px 0;background:none;box-shadow:none;border:none}
.web button{min-height:44px;padding:8px 12px}
.web button.on,.web button.bad{padding:7px 11px}
.web button.ic{min-width:44px;padding:10px}
.web .chip{min-height:36px;display:inline-flex;align-items:center;padding:6px 12px;font-size:13px}
.web .chips{padding-bottom:4px;scrollbar-width:none;margin-left:-4px;margin-right:-4px}
.web input,.web select,.web textarea{font-size:16px;min-height:44px;padding:10px}
.web label{font-size:13px}
.web .card{padding:12px;margin-bottom:12px}
.web .hd{position:sticky;top:52px;z-index:2;background:var(--page,var(--card-background-color));margin:0 0 10px;padding:4px 0}
.web .ttl{font-size:20px}
.web .stats{grid-template-columns:repeat(2,minmax(0,1fr))}
.web .stat b{font-size:18px}
.web .seg button{font-size:13px;min-height:44px}
.web .row.wrap>button,.web .conf button{flex:1 1 40%}
.web .tbl{font-size:14px}
.web .lg{padding:12px 0}
.web .plant{padding:12px}
.web .phases{grid-template-columns:repeat(2,minmax(0,1fr))}
}
`;

// Plant pictures (56x56 viewBox), one per built-in plant type. Anything else gets the generic sprout.
const ICONS = {
 "apple": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><path d=\"M28 18 C22 13 10 16 10 29 C10 41 19 51 24 51 C26 51 27 50 28 50 C29 50 30 51 32 51 C37 51 46 41 46 29 C46 16 34 13 28 18Z\" fill=\"#d93a3a\"/><path d=\"M17 24 C18 20 21 18 24 18\" stroke=\"#fff\" stroke-opacity=\".35\" stroke-width=\"3\" stroke-linecap=\"round\" fill=\"none\"/><path d=\"M28 18 C28 13 29 9 32 6\" stroke=\"#6d4c41\" stroke-width=\"3\" stroke-linecap=\"round\" fill=\"none\"/><path transform=\"translate(31 12) rotate(-20) scale(1.1)\" d=\"M0 0 C5 -7 13 -7 16 -3 C12 3 5 4 0 0Z\" fill=\"#4f9a2a\"/></svg>",
 "asian_pear": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><circle cx=\"28\" cy=\"32\" r=\"19\" fill=\"#e6b84a\"/><circle cx=\"20\" cy=\"26\" r=\"1.2\" fill=\"#9a6b1f\"/><circle cx=\"30\" cy=\"24\" r=\"1.2\" fill=\"#9a6b1f\"/><circle cx=\"37\" cy=\"30\" r=\"1.2\" fill=\"#9a6b1f\"/><circle cx=\"22\" cy=\"36\" r=\"1.2\" fill=\"#9a6b1f\"/><circle cx=\"32\" cy=\"38\" r=\"1.2\" fill=\"#9a6b1f\"/><circle cx=\"28\" cy=\"45\" r=\"1.2\" fill=\"#9a6b1f\"/><circle cx=\"40\" cy=\"38\" r=\"1.2\" fill=\"#9a6b1f\"/><circle cx=\"17\" cy=\"32\" r=\"1.2\" fill=\"#9a6b1f\"/><circle cx=\"26\" cy=\"31\" r=\"1.2\" fill=\"#9a6b1f\"/><path d=\"M28 13 C28 9 29 6 31 3\" stroke=\"#6d4c41\" stroke-width=\"3\" stroke-linecap=\"round\" fill=\"none\"/><path transform=\"translate(30 9) rotate(-15) scale(1)\" d=\"M0 0 C5 -7 13 -7 16 -3 C12 3 5 4 0 0Z\" fill=\"#4f9a2a\"/></svg>",
 "bean": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><path d=\"M10 46 C14 31 25 18 42 10\" stroke=\"#5aa832\" stroke-width=\"7.5\" stroke-linecap=\"round\" fill=\"none\"/><path d=\"M10 46 C14 31 25 18 42 10\" stroke=\"#a3da6a\" stroke-width=\"2\" stroke-linecap=\"round\" fill=\"none\"/><path d=\"M18 52 C25 40 36 30 49 26\" stroke=\"#6cb83c\" stroke-width=\"7.5\" stroke-linecap=\"round\" fill=\"none\"/><path d=\"M18 52 C25 40 36 30 49 26\" stroke=\"#b4e27c\" stroke-width=\"2\" stroke-linecap=\"round\" fill=\"none\"/><circle cx=\"15\" cy=\"39\" r=\"1.2\" fill=\"#2c6a1c\"/><circle cx=\"22\" cy=\"29\" r=\"1.2\" fill=\"#2c6a1c\"/><circle cx=\"31\" cy=\"20\" r=\"1.2\" fill=\"#2c6a1c\"/><circle cx=\"25\" cy=\"46\" r=\"1.2\" fill=\"#2c6a1c\"/><circle cx=\"33\" cy=\"38\" r=\"1.2\" fill=\"#2c6a1c\"/><circle cx=\"42\" cy=\"31\" r=\"1.2\" fill=\"#2c6a1c\"/><path d=\"M43 9 C47 6 50 7 51 10\" stroke=\"#2f6b20\" stroke-width=\"2\" stroke-linecap=\"round\" fill=\"none\"/></svg>",
 "cabbage": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><ellipse cx=\"14\" cy=\"36\" rx=\"9\" ry=\"14\" transform=\"rotate(-20 14 36)\" fill=\"#b6dc8f\"/><ellipse cx=\"42\" cy=\"36\" rx=\"9\" ry=\"14\" transform=\"rotate(20 42 36)\" fill=\"#b6dc8f\"/><circle cx=\"28\" cy=\"32\" r=\"19\" fill=\"#8fc46a\"/><path d=\"M28 14 C20 22 20 42 28 51 M28 14 C36 22 36 42 28 51 M12 28 C22 30 34 30 44 28\" stroke=\"#5f9a45\" stroke-width=\"1.5\" fill=\"none\" stroke-linecap=\"round\"/><path d=\"M19 22 C20 20 22 18 24 17\" stroke=\"#fff\" stroke-opacity=\".4\" stroke-width=\"3\" stroke-linecap=\"round\" fill=\"none\"/></svg>",
 "cantaloupe": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><g transform=\"translate(0 -3)\"><path d=\"M3 18 H53 A25 25 0 0 1 3 18Z\" fill=\"#d8c284\"/><path d=\"M50.2 19.8 L52.1 23.0\" stroke=\"#a88a4a\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><path d=\"M49.6 23.5 L51.0 26.9\" stroke=\"#a88a4a\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><path d=\"M48.4 27.0 L49.2 30.5\" stroke=\"#a88a4a\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><path d=\"M46.7 30.2 L46.8 33.8\" stroke=\"#a88a4a\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><path d=\"M44.4 33.1 L44.0 36.7\" stroke=\"#a88a4a\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><path d=\"M41.7 35.6 L40.7 39.1\" stroke=\"#a88a4a\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><path d=\"M38.6 37.6 L37.0 40.9\" stroke=\"#a88a4a\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><path d=\"M35.2 39.1 L33.1 42.1\" stroke=\"#a88a4a\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><path d=\"M31.7 40.0 L29.1 42.6\" stroke=\"#a88a4a\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><path d=\"M28.0 40.3 L25.1 42.4\" stroke=\"#a88a4a\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><path d=\"M24.3 40.0 L21.1 41.6\" stroke=\"#a88a4a\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><path d=\"M20.8 39.1 L17.3 40.1\" stroke=\"#a88a4a\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><path d=\"M17.4 37.6 L13.8 38.1\" stroke=\"#a88a4a\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><path d=\"M14.3 35.6 L10.7 35.5\" stroke=\"#a88a4a\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><path d=\"M11.6 33.1 L8.0 32.4\" stroke=\"#a88a4a\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><path d=\"M9.3 30.2 L5.9 28.9\" stroke=\"#a88a4a\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><path d=\"M7.6 27.0 L4.5 25.1\" stroke=\"#a88a4a\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><path d=\"M6.4 23.5 L3.6 21.1\" stroke=\"#a88a4a\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><path d=\"M5.8 19.8 L3.4 17.1\" stroke=\"#a88a4a\" stroke-width=\"1.1\" stroke-linecap=\"round\"/><path d=\"M6 18 H50 A22 22 0 0 1 6 18Z\" fill=\"#c4d68e\"/><path d=\"M8 18 H48 A20 20 0 0 1 8 18Z\" fill=\"#f6a65a\"/><path d=\"M17 18 C17 28 39 28 39 18Z\" fill=\"#f9c78f\"/><ellipse cx=\"21\" cy=\"21\" rx=\"1.2\" ry=\"2.1\" fill=\"#f6e6bd\" transform=\"rotate(-25 21 21)\"/><ellipse cx=\"25\" cy=\"23\" rx=\"1.2\" ry=\"2.1\" fill=\"#f6e6bd\" transform=\"rotate(-10 25 23)\"/><ellipse cx=\"29\" cy=\"23\" rx=\"1.2\" ry=\"2.1\" fill=\"#f6e6bd\" transform=\"rotate(0 29 23)\"/><ellipse cx=\"33\" cy=\"23\" rx=\"1.2\" ry=\"2.1\" fill=\"#f6e6bd\" transform=\"rotate(10 33 23)\"/><ellipse cx=\"37\" cy=\"21\" rx=\"1.2\" ry=\"2.1\" fill=\"#f6e6bd\" transform=\"rotate(25 37 21)\"/><ellipse cx=\"23\" cy=\"26\" rx=\"1.2\" ry=\"2.1\" fill=\"#f6e6bd\" transform=\"rotate(-15 23 26)\"/><ellipse cx=\"34\" cy=\"26\" rx=\"1.2\" ry=\"2.1\" fill=\"#f6e6bd\" transform=\"rotate(15 34 26)\"/></g></svg>",
 "carrot": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><g transform=\"rotate(30 28 30)\"><path d=\"M18 20 C18 13 38 13 38 20 L31 54 C30 56 26 56 25 54Z\" fill=\"#ef7d1a\"/><path d=\"M21 25 H27 M30 31 H35 M22 37 H27 M28 44 H32\" stroke=\"#c45f0c\" stroke-width=\"1.6\" stroke-linecap=\"round\"/><path d=\"M28 14 C26 9 22 6 19 3 M28 14 C28 9 28 6 28 2 M28 14 C30 9 34 6 37 3\" stroke=\"#4f9a2a\" stroke-width=\"3.2\" stroke-linecap=\"round\" fill=\"none\"/></g></svg>",
 "cauliflower": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><path d=\"M6 36 C6 46 16 52 28 52 C40 52 50 46 50 36 C46 40 40 42 28 42 C16 42 10 40 6 36Z\" fill=\"#6fae3d\"/><path d=\"M28 52 C22 44 14 40 8 34 M28 52 C34 44 42 40 48 34 M28 52 V42\" stroke=\"#4f8f2b\" stroke-width=\"1.3\" fill=\"none\"/><circle cx=\"16\" cy=\"32\" r=\"8\" fill=\"#f6f2e4\" stroke=\"#d8d0b4\" stroke-width=\"1.2\"/><circle cx=\"40\" cy=\"32\" r=\"8\" fill=\"#f6f2e4\" stroke=\"#d8d0b4\" stroke-width=\"1.2\"/><circle cx=\"22\" cy=\"22\" r=\"9\" fill=\"#f6f2e4\" stroke=\"#d8d0b4\" stroke-width=\"1.2\"/><circle cx=\"34\" cy=\"22\" r=\"9\" fill=\"#f6f2e4\" stroke=\"#d8d0b4\" stroke-width=\"1.2\"/><circle cx=\"28\" cy=\"14\" r=\"8\" fill=\"#f6f2e4\" stroke=\"#d8d0b4\" stroke-width=\"1.2\"/><circle cx=\"28\" cy=\"31\" r=\"9.5\" fill=\"#f6f2e4\" stroke=\"#d8d0b4\" stroke-width=\"1.2\"/><circle cx=\"21\" cy=\"38\" r=\"7\" fill=\"#f6f2e4\" stroke=\"#d8d0b4\" stroke-width=\"1.2\"/><circle cx=\"35\" cy=\"38\" r=\"7\" fill=\"#f6f2e4\" stroke=\"#d8d0b4\" stroke-width=\"1.2\"/></svg>",
 "cherry": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><path d=\"M19 33 C21 24 26 16 33 8 M38 35 C37 26 35 16 33 8\" stroke=\"#6d4c41\" stroke-width=\"2.4\" stroke-linecap=\"round\" fill=\"none\"/><circle cx=\"19\" cy=\"41\" r=\"10\" fill=\"#b3202a\"/><circle cx=\"38\" cy=\"43\" r=\"10\" fill=\"#c62833\"/><circle cx=\"16\" cy=\"38\" r=\"2.4\" fill=\"#fff\" fill-opacity=\".45\"/><circle cx=\"35\" cy=\"40\" r=\"2.4\" fill=\"#fff\" fill-opacity=\".45\"/><path transform=\"translate(31 9) rotate(-8) scale(1.15)\" d=\"M0 0 C5 -7 13 -7 16 -3 C12 3 5 4 0 0Z\" fill=\"#4f9a2a\"/></svg>",
 "cucumber": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><g transform=\"rotate(-40 28 28)\"><rect x=\"19\" y=\"3\" width=\"18\" height=\"50\" rx=\"9\" fill=\"#3f8a2b\"/><path d=\"M24 7 V49 M28 5 V51 M32 7 V49\" stroke=\"#8cc152\" stroke-width=\"1.8\" stroke-linecap=\"round\"/><circle cx=\"22\" cy=\"16\" r=\"1\" fill=\"#2c6a1c\"/><circle cx=\"34\" cy=\"20\" r=\"1\" fill=\"#2c6a1c\"/><circle cx=\"22\" cy=\"30\" r=\"1\" fill=\"#2c6a1c\"/><circle cx=\"34\" cy=\"36\" r=\"1\" fill=\"#2c6a1c\"/><circle cx=\"22\" cy=\"42\" r=\"1\" fill=\"#2c6a1c\"/><circle cx=\"30\" cy=\"12\" r=\"1\" fill=\"#2c6a1c\"/><rect x=\"25\" y=\"1\" width=\"6\" height=\"5\" rx=\"2\" fill=\"#6a8f2a\"/></g><path d=\"M41 11 C47 10 49 15 45 17 C42 18 41 15 44 14\" stroke=\"#4f9a2a\" stroke-width=\"1.6\" fill=\"none\" stroke-linecap=\"round\"/></svg>",
 "garlic": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><path d=\"M28 6 C27 13 22 16 17 23 C11 31 14 46 28 48 C42 46 45 31 39 23 C34 16 29 13 28 6Z\" fill=\"#f6f1e4\" stroke=\"#cdbf9f\" stroke-width=\"1.5\"/><path d=\"M28 14 C20 24 19 38 28 48 M28 14 C36 24 37 38 28 48\" stroke=\"#cdbf9f\" stroke-width=\"1.4\" fill=\"none\"/><path d=\"M24 22 C22 28 22 34 24 40\" stroke=\"#b58bb5\" stroke-width=\"1.4\" stroke-linecap=\"round\" fill=\"none\"/><path d=\"M24 48 L22 53 M28 48 V54 M32 48 L34 53\" stroke=\"#a38a63\" stroke-width=\"1.6\" stroke-linecap=\"round\"/></svg>",
 "generic": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><ellipse cx=\"28\" cy=\"49\" rx=\"19\" ry=\"5\" fill=\"#8b5e3c\"/><path d=\"M28 48 C27 40 28 32 28 24\" stroke=\"#2e7d32\" stroke-width=\"3.4\" stroke-linecap=\"round\" fill=\"none\"/><path d=\"M28 31 C18 31 11 25 10 15 C20 14 27 20 28 31Z\" fill=\"#43a047\"/><path d=\"M28 24 C29 14 37 7 47 8 C47 19 40 25 28 24Z\" fill=\"#66bb6a\"/></svg>",
 "habanero": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><path d=\"M13 25 C11 33 15 41 21 47 C24 50 26 53 28 54 C30 53 32 50 35 47 C41 41 45 33 43 25 C39 20 17 20 13 25Z\" fill=\"#f58a1f\"/><path d=\"M21 23 C19 31 21 41 26 50 M35 23 C37 31 35 41 30 50\" stroke=\"#c9600c\" stroke-width=\"1.5\" fill=\"none\" stroke-linecap=\"round\"/><path d=\"M17 30 C17 28 18 26 20 25\" stroke=\"#fff\" stroke-opacity=\".4\" stroke-width=\"3\" stroke-linecap=\"round\" fill=\"none\"/><ellipse cx=\"28\" cy=\"22\" rx=\"8\" ry=\"3.4\" fill=\"#3f8a2b\"/><path d=\"M28 21 C28 15 30 11 33 8\" stroke=\"#2f6b20\" stroke-width=\"3.6\" stroke-linecap=\"round\" fill=\"none\"/></svg>",
 "horseradish": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><path d=\"M23 26 C21 36 23 46 26 53 C27 54.5 29 54.5 30 53 C33 46 35 36 33 26Z\" fill=\"#e7dcc0\" stroke=\"#bfae86\" stroke-width=\"1.3\"/><path d=\"M23 33 H33 M24 40 H32 M25 46 H31\" stroke=\"#bfae86\" stroke-width=\"1.2\"/><path d=\"M33 40 L39 43 M23 44 L18 47\" stroke=\"#bfae86\" stroke-width=\"1.6\" stroke-linecap=\"round\"/><ellipse cx=\"17\" cy=\"17\" rx=\"12\" ry=\"5.5\" transform=\"rotate(-38 17 17)\" fill=\"#3f8a2b\"/><ellipse cx=\"39\" cy=\"17\" rx=\"12\" ry=\"5.5\" transform=\"rotate(38 39 17)\" fill=\"#4f9a2a\"/><ellipse cx=\"28\" cy=\"12\" rx=\"5.5\" ry=\"11\" fill=\"#5aa832\"/><path d=\"M28 26 V6\" stroke=\"#2f6b20\" stroke-width=\"1.2\"/></svg>",
 "jalapeno": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><g transform=\"rotate(14 28 30)\"><path d=\"M21 16 C16 20 17 40 23 51 C25 54 29 54 30 50 C34 39 36 22 33 17 C30 13 24 13 21 16Z\" fill=\"#3c8f2f\"/><path d=\"M21 22 C21 20 22 19 23 18\" stroke=\"#fff\" stroke-opacity=\".35\" stroke-width=\"2.6\" stroke-linecap=\"round\" fill=\"none\"/><path d=\"M25 26 L28 28 M24 34 L28 35 M26 42 L29 43 M30 24 L32 25\" stroke=\"#c9b27a\" stroke-width=\"1.4\" stroke-linecap=\"round\"/><path d=\"M27 15 C27 9 30 6 35 5\" stroke=\"#2f6b20\" stroke-width=\"4\" stroke-linecap=\"round\" fill=\"none\"/><ellipse cx=\"27\" cy=\"15\" rx=\"7\" ry=\"3\" fill=\"#2f6b20\"/></g></svg>",
 "jujube": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><path d=\"M10 14 C20 18 30 20 46 14\" stroke=\"#6d4c41\" stroke-width=\"2.4\" stroke-linecap=\"round\" fill=\"none\"/><path transform=\"translate(12 12) rotate(-30) scale(0.9)\" d=\"M0 0 C5 -7 13 -7 16 -3 C12 3 5 4 0 0Z\" fill=\"#4f9a2a\"/><path transform=\"translate(44 12) rotate(200) scale(0.9)\" d=\"M0 0 C5 -7 13 -7 16 -3 C12 3 5 4 0 0Z\" fill=\"#4f9a2a\"/><g><ellipse cx=\"17\" cy=\"35\" rx=\"7\" ry=\"10.5\" fill=\"#9b3d24\"/><ellipse cx=\"29\" cy=\"39\" rx=\"7\" ry=\"10.5\" fill=\"#b24a2a\"/><ellipse cx=\"41\" cy=\"35\" rx=\"7\" ry=\"10.5\" fill=\"#8f3520\"/></g><path d=\"M17 15 V25 M29 15 V29 M41 15 V25\" stroke=\"#6d4c41\" stroke-width=\"1.8\" stroke-linecap=\"round\"/><path d=\"M14 30 C14 28 15 26 16 25 M26 34 C26 32 27 30 28 29 M38 30 C38 28 39 26 40 25\" stroke=\"#fff\" stroke-opacity=\".4\" stroke-width=\"2\" stroke-linecap=\"round\" fill=\"none\"/></svg>",
 "lettuce": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><circle cx=\"14\" cy=\"32\" r=\"9\" fill=\"#8dc63f\"/><circle cx=\"42\" cy=\"32\" r=\"9\" fill=\"#8dc63f\"/><circle cx=\"19\" cy=\"20\" r=\"9\" fill=\"#8dc63f\"/><circle cx=\"37\" cy=\"20\" r=\"9\" fill=\"#8dc63f\"/><circle cx=\"28\" cy=\"15\" r=\"9\" fill=\"#8dc63f\"/><circle cx=\"16\" cy=\"43\" r=\"8\" fill=\"#8dc63f\"/><circle cx=\"40\" cy=\"43\" r=\"8\" fill=\"#8dc63f\"/><circle cx=\"28\" cy=\"46\" r=\"8\" fill=\"#8dc63f\"/><circle cx=\"22\" cy=\"30\" r=\"9\" fill=\"#b9de6a\"/><circle cx=\"34\" cy=\"30\" r=\"9\" fill=\"#b9de6a\"/><circle cx=\"28\" cy=\"24\" r=\"8\" fill=\"#b9de6a\"/><circle cx=\"28\" cy=\"38\" r=\"9\" fill=\"#b9de6a\"/><path d=\"M28 50 V32 M28 36 L20 28 M28 36 L36 28 M28 28 L24 20 M28 28 L32 20\" stroke=\"#6ea02c\" stroke-width=\"1.3\" fill=\"none\" stroke-linecap=\"round\"/></svg>",
 "nectarine": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><circle cx=\"28\" cy=\"32\" r=\"18\" fill=\"#f28c38\"/><path d=\"M28 14 A18 18 0 0 0 28 50 C22 40 22 24 28 14Z\" fill=\"#e0443a\" fill-opacity=\".75\"/><path d=\"M28 15 C23 25 23 39 28 49\" stroke=\"#b5321f\" stroke-width=\"1.6\" fill=\"none\" stroke-linecap=\"round\"/><path d=\"M28 14 C28 10 29 8 31 6\" stroke=\"#6d4c41\" stroke-width=\"3\" stroke-linecap=\"round\" fill=\"none\"/><path transform=\"translate(30 11) rotate(-25) scale(1.1)\" d=\"M0 0 C5 -7 13 -7 16 -3 C12 3 5 4 0 0Z\" fill=\"#4f9a2a\"/></svg>",
 "onion": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><path d=\"M28 15 C34 23 47 25 47 37 C47 46 39 51 28 51 C17 51 9 46 9 37 C9 25 22 23 28 15Z\" fill=\"#e0a032\"/><path d=\"M28 17 C21 27 18 40 23 51 M28 17 C35 27 38 40 33 51 M28 17 C28 28 28 40 28 51\" stroke=\"#b9791c\" stroke-width=\"1.3\" fill=\"none\"/><path d=\"M28 16 C26 11 24 8 22 4 M28 16 C29 11 31 8 34 5\" stroke=\"#5a9a2a\" stroke-width=\"3.2\" stroke-linecap=\"round\" fill=\"none\"/><path d=\"M25 51 L24 54 M28 51 V55 M31 51 L32 54\" stroke=\"#a38a63\" stroke-width=\"1.4\" stroke-linecap=\"round\"/></svg>",
 "onion_red": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><path d=\"M28 15 C34 23 47 25 47 37 C47 46 39 51 28 51 C17 51 9 46 9 37 C9 25 22 23 28 15Z\" fill=\"#a22d5c\"/><path d=\"M28 17 C21 27 18 40 23 51 M28 17 C35 27 38 40 33 51 M28 17 C28 28 28 40 28 51\" stroke=\"#6e1a3d\" stroke-width=\"1.3\" fill=\"none\"/><path d=\"M15 33 C15 29 17 26 20 25\" stroke=\"#fff\" stroke-opacity=\".4\" stroke-width=\"3\" stroke-linecap=\"round\" fill=\"none\"/><path d=\"M28 16 C26 11 24 8 22 4 M28 16 C29 11 31 8 34 5\" stroke=\"#5a9a2a\" stroke-width=\"3.2\" stroke-linecap=\"round\" fill=\"none\"/><path d=\"M25 51 L24 54 M28 51 V55 M31 51 L32 54\" stroke=\"#a38a63\" stroke-width=\"1.4\" stroke-linecap=\"round\"/></svg>",
 "onion_sweet": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><path d=\"M28 18 C36 23 50 26 50 38 C50 46 40 51 28 51 C16 51 6 46 6 38 C6 26 20 23 28 18Z\" fill=\"#f2d474\"/><path d=\"M28 19 C20 28 16 41 20 51 M28 19 C36 28 40 41 36 51 M28 19 C28 30 28 41 28 51\" stroke=\"#c9a43a\" stroke-width=\"1.3\" fill=\"none\"/><path d=\"M15 33 C15 29 17 26 20 25\" stroke=\"#fff\" stroke-opacity=\".4\" stroke-width=\"3\" stroke-linecap=\"round\" fill=\"none\"/><path d=\"M28 18 C26 13 24 10 22 6 M28 18 C29 13 31 10 34 7\" stroke=\"#6ab23a\" stroke-width=\"3.2\" stroke-linecap=\"round\" fill=\"none\"/><path d=\"M25 51 L24 54 M28 51 V55 M31 51 L32 54\" stroke=\"#a38a63\" stroke-width=\"1.4\" stroke-linecap=\"round\"/></svg>",
 "onion_white": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><path d=\"M28 15 C34 23 47 25 47 37 C47 46 39 51 28 51 C17 51 9 46 9 37 C9 25 22 23 28 15Z\" fill=\"#f6f2e6\"/><path d=\"M28 17 C21 27 18 40 23 51 M28 17 C35 27 38 40 33 51 M28 17 C28 28 28 40 28 51\" stroke=\"#cdbf9f\" stroke-width=\"1.3\" fill=\"none\"/><path d=\"M15 33 C15 29 17 26 20 25\" stroke=\"#fff\" stroke-opacity=\".4\" stroke-width=\"3\" stroke-linecap=\"round\" fill=\"none\"/><path d=\"M28 16 C26 11 24 8 22 4 M28 16 C29 11 31 8 34 5\" stroke=\"#7cb342\" stroke-width=\"3.2\" stroke-linecap=\"round\" fill=\"none\"/><path d=\"M25 51 L24 54 M28 51 V55 M31 51 L32 54\" stroke=\"#a38a63\" stroke-width=\"1.4\" stroke-linecap=\"round\"/></svg>",
 "pawpaw": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><ellipse cx=\"19\" cy=\"37\" rx=\"10\" ry=\"15\" transform=\"rotate(-14 19 37)\" fill=\"#9bbd45\" stroke=\"#5c7f26\" stroke-width=\"1\"/><ellipse cx=\"38\" cy=\"39\" rx=\"9.5\" ry=\"14\" transform=\"rotate(14 38 39)\" fill=\"#86ab3a\" stroke=\"#5c7f26\" stroke-width=\"1\"/><circle cx=\"16\" cy=\"33\" r=\"1.3\" fill=\"#5c7f26\"/><circle cx=\"21\" cy=\"42\" r=\"1.3\" fill=\"#5c7f26\"/><circle cx=\"40\" cy=\"36\" r=\"1.3\" fill=\"#4d6e1f\"/><circle cx=\"36\" cy=\"45\" r=\"1.3\" fill=\"#4d6e1f\"/><path d=\"M19 23 C22 19 25 18 28 17 M38 26 C35 21 31 18 28 17\" stroke=\"#6d4c41\" stroke-width=\"2.4\" stroke-linecap=\"round\" fill=\"none\"/><ellipse cx=\"38\" cy=\"12\" rx=\"12\" ry=\"4.8\" transform=\"rotate(-22 38 12)\" fill=\"#3d7a2a\"/><path d=\"M28 17 C32 14 38 11 45 8\" stroke=\"#2c5a1e\" stroke-width=\"1\" fill=\"none\"/></svg>",
 "pea": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><path d=\"M3 29 C10 8 46 8 53 29 C46 46 10 46 3 29Z\" fill=\"#3f8a2b\"/><path d=\"M7 29 C14 15 42 15 49 29 C42 41 14 41 7 29Z\" fill=\"#a8d86a\"/><circle cx=\"14\" cy=\"29\" r=\"6.2\" fill=\"#5fb52f\"/><circle cx=\"12\" cy=\"27\" r=\"1.7\" fill=\"#fff\" fill-opacity=\".5\"/><circle cx=\"23.5\" cy=\"29\" r=\"6.2\" fill=\"#5fb52f\"/><circle cx=\"21.5\" cy=\"27\" r=\"1.7\" fill=\"#fff\" fill-opacity=\".5\"/><circle cx=\"32.5\" cy=\"29\" r=\"6.2\" fill=\"#5fb52f\"/><circle cx=\"30.5\" cy=\"27\" r=\"1.7\" fill=\"#fff\" fill-opacity=\".5\"/><circle cx=\"42\" cy=\"29\" r=\"6.2\" fill=\"#5fb52f\"/><circle cx=\"40\" cy=\"27\" r=\"1.7\" fill=\"#fff\" fill-opacity=\".5\"/><path d=\"M49 20 C54 15 56 20 52 22 C49 23 49 20 52 19\" stroke=\"#4f9a2a\" stroke-width=\"1.6\" fill=\"none\" stroke-linecap=\"round\"/></svg>",
 "peach": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><circle cx=\"28\" cy=\"33\" r=\"18\" fill=\"#f8bb7c\"/><path d=\"M28 15 A18 18 0 0 1 28 51 C34 41 34 25 28 15Z\" fill=\"#f2848a\" fill-opacity=\".8\"/><path d=\"M28 16 C23 26 23 40 28 50\" stroke=\"#d96a58\" stroke-width=\"1.6\" fill=\"none\" stroke-linecap=\"round\"/><path d=\"M17 27 C19 23 22 21 25 20\" stroke=\"#fff\" stroke-opacity=\".45\" stroke-width=\"3\" stroke-linecap=\"round\" fill=\"none\"/><path d=\"M28 15 C28 11 29 9 31 7\" stroke=\"#6d4c41\" stroke-width=\"3\" stroke-linecap=\"round\" fill=\"none\"/><path transform=\"translate(30 12) rotate(-30) scale(1.1)\" d=\"M0 0 C5 -7 13 -7 16 -3 C12 3 5 4 0 0Z\" fill=\"#4f9a2a\"/><path transform=\"translate(27 12) rotate(-150) scale(1)\" d=\"M0 0 C5 -7 13 -7 16 -3 C12 3 5 4 0 0Z\" fill=\"#5aa832\"/></svg>",
 "pear": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><path d=\"M28 13 C33 13 34 19 36 24 C38 29 45 32 45 40 C45 48 38 52 28 52 C18 52 11 48 11 40 C11 32 18 29 20 24 C22 19 23 13 28 13Z\" fill=\"#b9cc3a\"/><path d=\"M17 38 C17 34 19 32 21 31\" stroke=\"#fff\" stroke-opacity=\".4\" stroke-width=\"3\" stroke-linecap=\"round\" fill=\"none\"/><path d=\"M28 13 C28 9 29 6 31 3\" stroke=\"#6d4c41\" stroke-width=\"3\" stroke-linecap=\"round\" fill=\"none\"/><path transform=\"translate(30 9) rotate(-15) scale(1)\" d=\"M0 0 C5 -7 13 -7 16 -3 C12 3 5 4 0 0Z\" fill=\"#4f9a2a\"/></svg>",
 "pepper": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><path d=\"M15 25 C10 32 11 43 17 49 C21 53 25 51 28 50 C31 51 35 53 39 49 C45 43 46 32 41 25 C37 20 19 20 15 25Z\" fill=\"#e8442a\"/><path d=\"M22 23 C19 31 20 42 24 50 M34 23 C37 31 36 42 32 50\" stroke=\"#b72f1a\" stroke-width=\"1.6\" fill=\"none\" stroke-linecap=\"round\"/><path d=\"M15 31 C15 28 17 26 19 25\" stroke=\"#fff\" stroke-opacity=\".35\" stroke-width=\"3\" stroke-linecap=\"round\" fill=\"none\"/><ellipse cx=\"28\" cy=\"22\" rx=\"7\" ry=\"3.2\" fill=\"#3f8a2b\"/><path d=\"M28 21 C28 15 30 11 34 9\" stroke=\"#2f6b20\" stroke-width=\"4\" stroke-linecap=\"round\" fill=\"none\"/></svg>",
 "potato": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><path d=\"M9 31 C7 20 18 11 30 12 C43 13 50 22 48 33 C46 44 36 50 25 49 C16 48 10 40 9 31Z\" fill=\"#c99a5b\"/><path d=\"M14 22 C16 18 20 16 24 15\" stroke=\"#fff\" stroke-opacity=\".3\" stroke-width=\"3\" stroke-linecap=\"round\" fill=\"none\"/><path d=\"M18 28 q2 -2.5 4 0\" stroke=\"#7a5428\" stroke-width=\"1.6\" stroke-linecap=\"round\" fill=\"none\"/><path d=\"M31 24 q2 -2.5 4 0\" stroke=\"#7a5428\" stroke-width=\"1.6\" stroke-linecap=\"round\" fill=\"none\"/><path d=\"M34 38 q2 -2.5 4 0\" stroke=\"#7a5428\" stroke-width=\"1.6\" stroke-linecap=\"round\" fill=\"none\"/><path d=\"M22 40 q2 -2.5 4 0\" stroke=\"#7a5428\" stroke-width=\"1.6\" stroke-linecap=\"round\" fill=\"none\"/><path d=\"M39 30 q2 -2.5 4 0\" stroke=\"#7a5428\" stroke-width=\"1.6\" stroke-linecap=\"round\" fill=\"none\"/></svg>",
 "pumpkin": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><ellipse cx=\"18\" cy=\"34\" rx=\"11\" ry=\"16\" fill=\"#e87a14\"/><ellipse cx=\"38\" cy=\"34\" rx=\"11\" ry=\"16\" fill=\"#e87a14\"/><ellipse cx=\"28\" cy=\"34\" rx=\"10\" ry=\"17.5\" fill=\"#f58f26\"/><path d=\"M28 17 C25 26 25 42 28 51 M20 20 C14 28 14 40 20 49 M36 20 C42 28 42 40 36 49\" stroke=\"#c45f0c\" stroke-width=\"1.4\" fill=\"none\" stroke-linecap=\"round\"/><path d=\"M28 17 C28 12 28 10 29 7\" stroke=\"#5f7a2a\" stroke-width=\"5\" stroke-linecap=\"round\" fill=\"none\"/><path d=\"M30 12 C36 10 38 14 35 16\" stroke=\"#4f9a2a\" stroke-width=\"1.6\" fill=\"none\" stroke-linecap=\"round\"/></svg>",
 "tomato": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><ellipse cx=\"28\" cy=\"33\" rx=\"20\" ry=\"17\" fill=\"#e5372d\"/><path d=\"M16 27 C18 23 21 21 24 21\" stroke=\"#fff\" stroke-opacity=\".4\" stroke-width=\"3\" stroke-linecap=\"round\" fill=\"none\"/><path d=\"M28 21 L22 14 L27 18 L28 11 L30 18 L36 14 L31 21 L38 23 L30 24 L28 27 L26 24 L18 23Z\" fill=\"#3f8a2b\"/><path d=\"M28 19 C28 14 29 11 31 8\" stroke=\"#2f6b20\" stroke-width=\"2.4\" stroke-linecap=\"round\" fill=\"none\"/></svg>",
 "watermelon": "<svg viewBox=\"0 0 56 56\" width=\"44\" height=\"44\" aria-hidden=\"true\"><g transform=\"translate(0 -3)\"><path d=\"M3 18 H53 A25 25 0 0 1 3 18Z\" fill=\"#3f8a2b\"/><path d=\"M6 18 H50 A22 22 0 0 1 6 18Z\" fill=\"#f1f3d0\"/><path d=\"M9 18 H47 A19 19 0 0 1 9 18Z\" fill=\"#ec4a5a\"/><ellipse cx=\"17\" cy=\"24\" rx=\"1.4\" ry=\"2.4\" fill=\"#2b1d1a\" transform=\"rotate(-20 17 24)\"/><ellipse cx=\"28\" cy=\"26\" rx=\"1.4\" ry=\"2.4\" fill=\"#2b1d1a\" transform=\"rotate(0 28 26)\"/><ellipse cx=\"39\" cy=\"24\" rx=\"1.4\" ry=\"2.4\" fill=\"#2b1d1a\" transform=\"rotate(20 39 24)\"/><ellipse cx=\"22\" cy=\"33\" rx=\"1.4\" ry=\"2.4\" fill=\"#2b1d1a\" transform=\"rotate(-10 22 33)\"/><ellipse cx=\"34\" cy=\"33\" rx=\"1.4\" ry=\"2.4\" fill=\"#2b1d1a\" transform=\"rotate(10 34 33)\"/><ellipse cx=\"28\" cy=\"38\" rx=\"1.4\" ry=\"2.4\" fill=\"#2b1d1a\" transform=\"rotate(0 28 38)\"/></g></svg>"
};
const pic = (v) => ICONS[v.species] || ICONS.generic;

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

function metricChart(m) {
  const hs = m.history;
  if (hs.length < 2) return `<div class="mut small">Two days of readings will draw a trend.</div>`;
  const W = 340, H = 110, L = 34, R = 8, T = 10, B = 20;
  const ds = hs.map((r) => Date.parse(r.date));
  const t0 = Math.min(...ds), t1 = Math.max(Math.max(...ds), t0 + 864e5 * 7);
  const all = hs.flatMap((r) => [r.value, r.min ?? r.value, r.max ?? r.value]);
  let lo = Math.min(...all), hi = Math.max(...all);
  if (hi - lo < 1e-6) { lo -= 1; hi += 1; }
  const pad = (hi - lo) * 0.1; lo -= pad; hi += pad;
  const x = (t) => L + ((t - t0) / (t1 - t0)) * (W - L - R);
  const y = (v) => T + ((hi - v) / (hi - lo)) * (H - T - B);
  const band = hs.filter((r) => r.max !== undefined);
  const area = band.length > 1 ? `<polygon points="${band.map((r) => `${x(Date.parse(r.date)).toFixed(1)},${y(r.max).toFixed(1)}`).join(" ")} ${band.slice().reverse().map((r) => `${x(Date.parse(r.date)).toFixed(1)},${y(r.min).toFixed(1)}`).join(" ")}" fill="var(--primary-color)" opacity="0.18"/>` : "";
  const pts = hs.map((r) => `${x(Date.parse(r.date)).toFixed(1)},${y(r.value).toFixed(1)}`).join(" ");
  const f = (v) => (Math.abs(hi - lo) < 10 ? v.toFixed(1) : Math.round(v));
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="${esc(m.name)} over time">
    <line x1="${L}" y1="${H - B}" x2="${W - R}" y2="${H - B}" stroke="var(--divider-color)"/>
    <text class="ax" x="2" y="${T + 8}">${f(hi)}</text><text class="ax" x="2" y="${H - B - 2}">${f(lo)}</text>
    ${area}<polyline points="${pts}" fill="none" stroke="var(--primary-color)" stroke-width="2"/>
    <text class="ax" x="${L}" y="${H - 5}">${fmtDate(hs[0].date)}</text><text class="ax" text-anchor="end" x="${W - R}" y="${H - 5}">${fmtDate(hs[hs.length - 1].date)}</text></svg>`;
}
// Several temperature histories on one set of axes: [{ name, hist, color }].
function tempChart(series, label) {
  series = series.filter((x) => x.hist.length);
  const pts = series.flatMap((x) => x.hist);
  const days = new Set(pts.map((r) => r.date));
  if (days.size < 2) return `<div class="mut small">Two days of readings will draw a trend.</div>`;
  const W = 340, H = 130, L = 34, R = 8, T = 10, B = 20;
  const ds = pts.map((r) => Date.parse(r.date)), t0 = Math.min(...ds), t1 = Math.max(Math.max(...ds), t0 + 864e5 * 7);
  const all = pts.flatMap((r) => [r.value, r.min ?? r.value, r.max ?? r.value]);
  let lo = Math.min(...all), hi = Math.max(...all);
  if (hi - lo < 1e-6) { lo -= 1; hi += 1; }
  const pad = (hi - lo) * 0.1; lo -= pad; hi += pad;
  const x = (t) => L + ((t - t0) / (t1 - t0)) * (W - L - R);
  const y = (v) => T + ((hi - v) / (hi - lo)) * (H - T - B);
  const f = (v) => (Math.abs(hi - lo) < 10 ? v.toFixed(1) : Math.round(v));
  const dated = (r) => `${x(Date.parse(r.date)).toFixed(1)},`;
  const body = series.map((sr) => {
    const band = sr.hist.filter((r) => r.max !== undefined);
    const area = band.length > 1 ? `<polygon points="${band.map((r) => dated(r) + y(r.max).toFixed(1)).join(" ")} ${band.slice().reverse().map((r) => dated(r) + y(r.min).toFixed(1)).join(" ")}" fill="${sr.color}" opacity="0.14"/>` : "";
    const last = sr.hist[sr.hist.length - 1];
    return `${area}<polyline points="${sr.hist.map((r) => dated(r) + y(r.value).toFixed(1)).join(" ")}" fill="none" stroke="${sr.color}" stroke-width="2"/><circle cx="${x(Date.parse(last.date))}" cy="${y(last.value)}" r="3.5" fill="${sr.color}"/>`;
  }).join("");
  const first = pts.map((r) => r.date).sort()[0], end = pts.map((r) => r.date).sort().pop();
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="${esc(label)} over time">
    <line x1="${L}" y1="${H - B}" x2="${W - R}" y2="${H - B}" stroke="var(--divider-color)"/>
    <text class="ax" x="2" y="${T + 8}">${f(hi)}</text><text class="ax" x="2" y="${H - B - 2}">${f(lo)}</text>
    ${body}<text class="ax" x="${L}" y="${H - 5}">${fmtDate(first)}</text><text class="ax" text-anchor="end" x="${W - R}" y="${H - 5}">${fmtDate(end)}</text></svg>`;
}
// Air quality on one graph. Particles (PM1, PM2.5, PM10, ug/m3) read on the left scale and the NOx and VOC indexes on the
// right. metrics is [[key, rows, color, side]], rows are [time, average, highest?], time in seconds or a date for whole days.
function airChart(metrics, label) {
  const lines = metrics.filter(([, rows]) => rows.length >= 2);
  if (!lines.length) return `<div class="mut small">Readings will draw a trend as they come in.</div>`;
  const W = 340, H = 150, L = 32, R = 32, T = 8, B = 18;
  const t = (r) => (typeof r[0] === "number" ? r[0] * 1000 : Date.parse(r[0] + "T12:00:00"));
  const all = lines.flatMap(([, rows]) => rows);
  const t0 = Math.min(...all.map(t)), t1 = Math.max(...all.map(t));
  const top = (side) => Math.max(1, ...lines.filter((l) => l[3] === side).flatMap(([, rows]) => rows.map((r) => (r[2] === undefined ? r[1] : r[2])))) * 1.08;
  const hi = { l: top("l"), r: top("r") };
  const x = (r) => L + ((t(r) - t0) / Math.max(1, t1 - t0)) * (W - L - R);
  const pts = (rows, side, i) => rows.map((r) => `${x(r).toFixed(1)},${(T + (1 - r[i] / hi[side]) * (H - T - B)).toFixed(1)}`).join(" ");
  const hasMax = lines.some(([, rows]) => rows[0].length > 2);
  const dash = hasMax ? lines.map(([, rows, c, side]) => `<polyline points="${pts(rows, side, 2)}" fill="none" stroke="${c}" stroke-width="1.2" stroke-dasharray="3 2" opacity=".7"/>`).join("") : "";
  const solid = lines.map(([, rows, c, side]) => `<polyline points="${pts(rows, side, 1)}" fill="none" stroke="${c}" stroke-width="2"/>`).join("");
  const short = (ms) => new Date(ms).toLocaleString(undefined, t1 - t0 <= 2 * 864e5 ? { hour: "numeric", minute: "2-digit" } : { month: "short", day: "numeric" });
  const hasL = lines.some((l) => l[3] === "l"), hasR = lines.some((l) => l[3] === "r");
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="${esc(label)}"><line x1="${L}" y1="${H - B}" x2="${W - R}" y2="${H - B}" stroke="var(--divider-color)"/>
    <line x1="${L}" x2="${W - R}" y1="${(T + (H - T - B) / 2).toFixed(1)}" y2="${(T + (H - T - B) / 2).toFixed(1)}" stroke="var(--divider-color)" opacity=".5"/>
    ${hasL ? `<text class="ax" x="2" y="${T + 8}">${Math.round(hi.l)}</text><text class="ax" x="2" y="${H - B - 2}">0</text>` : ""}
    ${hasR ? `<text class="ax" text-anchor="end" x="${W - 2}" y="${T + 8}">${Math.round(hi.r)}</text><text class="ax" text-anchor="end" x="${W - 2}" y="${H - B - 2}">0</text>` : ""}
    ${dash}${solid}<text class="ax" x="${L}" y="${H - 4}">${short(t0)}</text><text class="ax" text-anchor="end" x="${W - R}" y="${H - 4}">${short(t1)}</text></svg>
    <div class="small" style="display:flex;justify-content:space-between"><span>${hasL ? "◀ µg/m³ (particles)" : ""}</span><span>${hasR ? "index (NOx, VOC) ▶" : ""}</span></div>`;
}
// The last 24 hours of readings: series are [{ color, rows: [[seconds since the epoch, value], ...] }].
function dayChart(series, label) {
  const now = Date.now() / 1000, t0 = now - 86400;
  series = series.map((x) => ({ ...x, rows: x.rows.filter((r) => r[0] >= t0) })).filter((x) => x.rows.length);
  if (!series.some((x) => x.rows.length >= 2)) return `<div class="mut small">Readings are kept every 15 minutes from now on. The last 24 hours will fill in as they come.</div>`;
  const W = 340, H = 130, L = 34, R = 8, T = 10, B = 20;
  const all = series.flatMap((x) => x.rows.map((r) => r[1]));
  let lo = Math.min(...all), hi = Math.max(...all);
  if (hi - lo < 1e-6) { lo -= 1; hi += 1; }
  const pad = (hi - lo) * 0.1; lo -= pad; hi += pad;
  const x = (t) => L + ((t - t0) / 86400) * (W - L - R);
  const y = (v) => T + ((hi - v) / (hi - lo)) * (H - T - B);
  const f = (v) => (Math.abs(hi - lo) < 10 ? v.toFixed(1) : Math.round(v));
  const hr = (t) => new Date(t * 1000).toLocaleTimeString(undefined, { hour: "numeric" });
  const body = series.map((sr) => {
    const last = sr.rows[sr.rows.length - 1];
    return `<polyline points="${sr.rows.map((r) => `${x(r[0]).toFixed(1)},${y(r[1]).toFixed(1)}`).join(" ")}" fill="none" stroke="${sr.color}" stroke-width="2"/><circle cx="${x(last[0]).toFixed(1)}" cy="${y(last[1]).toFixed(1)}" r="3.5" fill="${sr.color}"/>`;
  }).join("");
  const ticks = [0, 0.25, 0.5, 0.75, 1].map((k) => `<line x1="${x(t0 + k * 86400).toFixed(1)}" x2="${x(t0 + k * 86400).toFixed(1)}" y1="${T}" y2="${H - B}" stroke="var(--divider-color)" opacity="0.5"/>`).join("");
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="${esc(label)}, last 24 hours">
    ${ticks}<line x1="${L}" y1="${H - B}" x2="${W - R}" y2="${H - B}" stroke="var(--divider-color)"/>
    <text class="ax" x="2" y="${T + 8}">${f(hi)}</text><text class="ax" x="2" y="${H - B - 2}">${f(lo)}</text>
    ${body}<text class="ax" x="${L}" y="${H - 5}">${hr(t0)}</text><text class="ax" text-anchor="middle" x="${x(t0 + 43200).toFixed(1)}" y="${H - 5}">${hr(t0 + 43200)}</text><text class="ax" text-anchor="end" x="${W - R}" y="${H - 5}">Now</text></svg>`;
}
function dualChart(ec, mo, band) {
  const rows = new Map();
  for (const r of ec.history) rows.set(r.date, { ...(rows.get(r.date) || {}), ec: r.value });
  for (const r of mo.history) rows.set(r.date, { ...(rows.get(r.date) || {}), mo: r.value });
  const days = [...rows.keys()].sort();
  if (days.length < 2) return `<div class="mut small">Two days of readings will draw a trend.</div>`;
  const W = 340, H = 130, L = 34, R = 34, T = 10, B = 20;
  const ds = days.map((d) => Date.parse(d)), t0 = Math.min(...ds), t1 = Math.max(Math.max(...ds), t0 + 864e5 * 7);
  const evs = ec.history.map((r) => r.value).concat(band[0], band[1]);
  const eHi = Math.max(...evs) * 1.15 || 1;
  const x = (t) => L + ((t - t0) / (t1 - t0)) * (W - L - R);
  const ye = (v) => T + ((eHi - v) / eHi) * (H - T - B), ym = (v) => T + ((100 - v) / 100) * (H - T - B);
  const line = (key, fy) => days.filter((d) => rows.get(d)[key] !== undefined).map((d) => `${x(Date.parse(d)).toFixed(1)},${fy(rows.get(d)[key]).toFixed(1)}`).join(" ");
  const f = (v) => v.toFixed(1);
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Soil EC and moisture over time">
    <rect x="${L}" y="${ye(band[1]).toFixed(1)}" width="${W - L - R}" height="${(ye(band[0]) - ye(band[1])).toFixed(1)}" fill="var(--ok)" opacity=".15"/>
    <line x1="${L}" y1="${H - B}" x2="${W - R}" y2="${H - B}" stroke="var(--divider-color)"/>
    <text class="ax" x="2" y="${T + 8}">${f(eHi)}</text><text class="ax" x="2" y="${H - B - 2}">0</text>
    <text class="ax" text-anchor="end" x="${W - 2}" y="${T + 8}">100%</text><text class="ax" text-anchor="end" x="${W - 2}" y="${H - B - 2}">0%</text>
    <polyline points="${line("mo", ym)}" fill="none" stroke="var(--info-color, #4aa3df)" stroke-width="1.6" stroke-dasharray="4 3"/>
    <polyline points="${line("ec", ye)}" fill="none" stroke="var(--primary-color,#03a9f4)" stroke-width="2"/>
    <text class="ax" x="${L}" y="${H - 5}">${fmtDate(days[0])}</text><text class="ax" text-anchor="end" x="${W - R}" y="${H - 5}">${fmtDate(days[days.length - 1])}</text></svg>
    <div class="small mut" style="display:flex;gap:14px;margin-top:2px"><span><b style="color:var(--primary-color)">&#9644;</b> EC (mS/cm, left)</span><span><b style="color:var(--info-color,#4aa3df)">&#9548;</b> Moisture (%, right)</span><span><b style="color:var(--ok)">&#9608;</b> Target</span></div>`;
}
function barChart(days) {
  const W = 340, H = 90, L = 30, B = 16, T = 8, n = days.length, max = Math.max(...days.map((d) => d.kwh), 0.01);
  const bw = (W - L - 4) / n;
  const bars = days.map((d, i) => { const h = Math.max(d.kwh > 0 ? 1.5 : 0, (d.kwh / max) * (H - T - B)); return `<rect x="${(L + i * bw + 1).toFixed(1)}" y="${(H - B - h).toFixed(1)}" width="${Math.max(1, bw - 2).toFixed(1)}" height="${h.toFixed(1)}" rx="1.5" fill="var(--primary-color,#03a9f4)"><title>${fmtDate(d.date)}: ${d.kwh} kWh${d.cost !== null && d.cost !== undefined ? `, $${d.cost.toFixed(2)}` : ""}</title></rect>`; }).join("");
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" role="img" aria-label="Energy used per day"><line x1="${L}" y1="${H - B}" x2="${W - 4}" y2="${H - B}" stroke="var(--divider-color)"/><text class="ax" x="2" y="${T + 8}">${max.toFixed(max < 10 ? 1 : 0)}</text><text class="ax" x="2" y="${H - B - 2}">0</text>${bars}<text class="ax" x="${L}" y="${H - 3}">${fmtDate(days[0].date)}</text><text class="ax" text-anchor="end" x="${W - 4}" y="${H - 3}">${fmtDate(days[n - 1].date)}</text></svg>`;
}
const COVER_TEXT = { mowed: "mowed", wilted: "wilted", plowed: "plowed", tilled: "tilled", roll_crimped: "roll-crimped", tarped: "tarped", winterkill: "winterkill", other: "other" };
const METRIC_ICON = { moisture: "water-percent", ec: "flash", soil_temp: "thermometer", air_temp: "thermometer", out_temp: "weather-partly-cloudy", par: "white-balance-sunny" };
const KIND_ICON = { garden: "flower", rack: "table-furniture", greenhouse: "greenhouse" };
const KIND_ORDER = { rack: 0, greenhouse: 1, garden: 2 };
const WEB_HIDDEN = new Set(["form-sensors", "toggle-probes", "form-climate", "form-alarm", "form-rate", "toggle-alarm", "toggle-sensor-alarm", "ack-sensor", "ack-alarm"]);
const METRIC_DEC = { moisture: 0, ec: 2, soil_temp: 0, air_temp: 1, out_temp: 1, par: 0 };

class GardenTrackerCard extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
    this._view = { v: "home" };
    this._nav = [];
    this._form = null;
    this._confirm = null;
    this._filter = "all";
    this._q = {};
    this._pref = (k, d) => { try { const v = localStorage.getItem("gt_" + k); return v === null ? d : JSON.parse(v); } catch (e) { return d; } };
    this._setPref = (k, v) => { try { localStorage.setItem("gt_" + k, JSON.stringify(v)); } catch (e) { /* no storage */ } };
    this._sort = this._pref("sort", "garden");
    this._psort = this._pref("psort", "year");
    this._tab = this._pref("tab", "all");
    this._compact = this._pref("compact", true);
    this._show = { water: true, micro: true, cover: true, chores: true, frost: true, ...this._pref("show", {}) };
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
      this.shadowRoot.addEventListener("click", (e) => this._onClick(e));
      this.shadowRoot.addEventListener("input", (e) => this._onInput(e, false));
      this.shadowRoot.addEventListener("change", (e) => this._onInput(e, true));
      this.shadowRoot.addEventListener("focusin", (e) => {
        const el = e.target;
        if (el.dataset && el.dataset.lq !== undefined && (this._bq === null || this._bq === undefined)) { this._bq = ""; this._focusL = true; this._render(); return; }
        if (el.dataset && el.dataset.fs !== undefined && this._form && !(this._form.search && this._form.search[el.dataset.fs] !== undefined)) {
          this._form.search = this._form.search || {};
          this._form.search[el.dataset.fs] = "";
          this._focusF = el.dataset.fs;
          this._render();
        }
      });
    }
    this._render();
  }
  set hass(h) {
    this._hass = h;
    if (!this._subTried) this._subscribe();
  }
  getCardSize() { return 8; }
  getGridOptions() { return { columns: 12, rows: "auto", min_columns: 6 }; }
  static getStubConfig() { return { grid_options: { columns: "full" } }; }
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
  _searchBox(key, label) {
    return `<div class="row" style="margin:6px 0"><input type="search" class="grow" data-q="${key}" placeholder="${label}" value="${esc(this._q[key] || "")}" style="min-height:44px;padding:0 12px;border-radius:12px;border:1px solid var(--divider-color,#c9cfc8);background:var(--card-background-color,#fff);color:var(--primary-text-color,inherit);font:inherit" autocomplete="off"></div>`;
  }
  _matches(v, key) {
    const q = String(this._q[key] || "").trim().toLowerCase();
    if (!q) return true;
    const hay = [v.name, v.species_name, v.garden_name, v.container, v.notes].filter(Boolean).join(" ").toLowerCase();
    return q.split(/\s+/).every((w) => hay.includes(w));
  }
  _sortVars(list, mode) {
    const name = (a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
    if (mode === "name") return [...list].sort(name);
    if (mode === "harvest") return [...list].sort((a, b) => (a.days_to_expected === null || a.days_to_expected === undefined ? 1e9 : a.days_to_expected) - (b.days_to_expected === null || b.days_to_expected === undefined ? 1e9 : b.days_to_expected) || name(a, b));
    return list;
  }
  _variety(id) { return this._snap.varieties.find((v) => v.id === id); }
  _garden(id) { return this._snap.gardens.find((g) => g.id === id); }
  async _call(service, data) {
    const clean = {};
    for (const [k, v] of Object.entries(data)) {
      if (v === "" && (k === "garden" || k === "to")) { clean[k] = v; continue; }  // empty means "no garden" for a tree
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
      else if (w === "layout" && this._view.id && this._garden(this._view.id) && this._garden(this._view.id).layout) body = this._layoutView(this._garden(this._view.id));
      else if (w === "water" && this._view.id && this._garden(this._view.id) && this._garden(this._view.id).irrigation) body = this._irrView(this._garden(this._view.id));
      else if (w === "archive") body = this._archiveView();
      else if (w === "micro" && this._snap.micro) body = this._microView();
      else { this._view = { v: "home" }; body = this._homeView(); }
    }
    const banner = (this._err && this._snap ? `<div class="err">${esc(this._err)}</div>` : "") +
      (this._undo && this._snap && this._snap.can_undo && !this._form
        ? `<div class="undo"><span>Entry removed</span><button data-act="undo">Undo</button></div>` : "");
    this.shadowRoot.innerHTML = `<style>${CSS}${this._web ? WEB_PHONE_CSS : ""}</style><ha-card${this._web ? ' class="web"' : ""}>${banner}${body}</ha-card>`;
    if (this._focusL) {
      const el = this.shadowRoot.querySelector("input[data-lq]");
      this._focusL = false;
      if (el) { el.focus(); try { el.setSelectionRange(el.value.length, el.value.length); } catch (e) { /* not a text box */ } }
    }
    if (this._focusF) {
      const el = this.shadowRoot.querySelector(`input[data-fs="${this._focusF}"]`);
      this._focusF = null;
      if (el) { el.focus(); try { el.setSelectionRange(el.value.length, el.value.length); } catch (e) { /* not a text box */ } }
    }
    if (this._focusQ) {  // keep the cursor in a search box while its list is redrawn
      const el = this.shadowRoot.querySelector(`input[data-q="${this._focusQ}"]`);
      this._focusQ = null;
      if (el) { el.focus(); try { el.setSelectionRange(el.value.length, el.value.length); } catch (e) { /* not a text box */ } }
    }
  }

  _icon(name) { return `<ha-icon icon="mdi:${name}"></ha-icon>`; }
  // In the web app there are no Home Assistant sensors or devices, so those controls are left out.
  get _web() { return !!(this._config && this._config.web); }
  _btn(act, icon, label, attrs = "", cls = "") {
    if (this._web && WEB_HIDDEN.has(act)) return "";
    return `<button class="${cls}" data-act="${act}" ${attrs}>${icon ? this._icon(icon) : ""}${label ? " " + label : ""}</button>`;
  }
  _stats(v) {
    const d = v.days, out = [];
    if (v.kind === "tree") {
      out.push(["Age", yrs(v.age_years)], ["Last spray", dAgo(v.spray.days_since)]);
      if (v.days_to_expected !== null) out.push(["Harvest in", dIn(v.days_to_expected)]);
      else out.push(["Harvested", `${num(v.total_lbs, 1)} lb`]);
    } else {
      if (v.countdown_short) out.push(["Harvest in", v.countdown_short]);
      if (d.upotted !== null) out.push(["Up-potted", dAgo(d.upotted)]);
      if (d.in_ground !== null) out.push(["In ground", dAgo(d.in_ground)]);
      if (d.fertilized !== null) out.push(["Last fed", dAgo(d.fertilized)]);
      if (out.length < 3) out.push(["Planted", dAgo(d.planted)]);
      if (out.length < 3 && v.days_to_expected !== null && !v.countdown_short) out.push(["Harvest in", dIn(v.days_to_expected)]);
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
  _frostPill(g, named) {
    if (!this._show.frost) return "";
    const n = g.frost && g.frost.next;
    if (!n) {
      const r = g.frost && g.frost.recorded;
      if (!r || !(r.last_spring || r.first_fall)) return "";
      const bits = [r.last_spring ? `last spring frost ${fmtDate(r.last_spring)} (expected ${fmtMd(g.frost.last)})` : "", r.first_fall ? `first fall frost ${fmtDate(r.first_fall)} (expected ${fmtMd(g.frost.first)})` : ""].filter(Boolean);
      return `<div class="pill info" style="margin:4px 6px 4px 0">${this._icon("snowflake-alert")} ${named ? esc(g.name) + ": " : ""}Recorded by your sensors: ${bits.join(", ")}</div>`;
    }
    const nm = n.event === "last" ? "Last spring frost" : "First fall frost";
    const soon = n.event === "first" && n.days <= 14;
    const r = g.frost.recorded, rec = [];
    if (r && r.last_spring) rec.push(`last spring frost ${fmtDate(r.last_spring)}${r.spring_final ? "" : " so far"}`);
    if (r && r.first_fall) rec.push(`first fall frost ${fmtDate(r.first_fall)}`);
    return `<div class="pill ${soon ? "warn" : "info"}" style="margin:4px 6px 4px 0">${this._icon("snowflake-alert")} ${named ? esc(g.name) + ": " : ""}${nm} ${n.days === 0 ? "expected today" : `in ${n.days} day${n.days === 1 ? "" : "s"}`} (${fmtDate(n.date)})${rec.length ? `<div class="small" style="font-weight:400">Recorded by your sensors this year: ${rec.join(", ")}</div>` : ""}</div>`;
  }
  _microTile() {
    if (!this._show.micro) return "";
    const m = this._snap.micro;
    if (!m) return "";
    const z = m.zone, t = m.temps.year;
    const zt = z.zone ? `Zone ${esc(z.zone)}` : "Zone still being worked out";
    const sub = [z.usda ? `USDA says ${esc(z.usda)}` : "", t.low !== null ? `year ${num(t.low, 0)}° to ${num(t.high, 0)}°F` : "", m.rain.sensors.length ? `rain this year ${num(m.rain.year, 1)} in` : ""].filter(Boolean).join(", ");
    return `<div class="card tile" data-act="open-micro"><div class="row"><div class="pic" style="background:color-mix(in srgb,var(--info) 18%,transparent);color:var(--info)">${this._icon("map-marker-radius")}</div><div class="grow"><div style="font-size:15px;font-weight:500">Microclimate</div><div class="sub">${zt}</div><div class="small mut">${sub || "Your own frost dates, temperatures and rain"}</div></div>${this._icon("chevron-right")}</div></div>`;
  }
  _microView() {
    const m = this._snap.micro;
    let h = `<div class="hd">${this._btn("back", "arrow-left", "", "", "ic")}<div class="ttl grow">Microclimate</div>${this._web ? this._btn("web-location", "map-marker", m.settings.location && m.settings.location.name ? esc(m.settings.location.name) : "Location") : ""}${this._btn("form-micro", "cog", "Settings")}</div>`;
    if (this._web && !m.settings.location) h += `<div class="msg">Set where your garden is and the app fills in local weather: frost dates, your zone, temperatures and rain.<br><br>${this._btn("web-location", "map-marker", "Set location", "", "primary")}</div>`;
    else if (!this._web && !m.settings.outdoor_entity) h += `<div class="msg">Set an outside temperature sensor in the Garden Tracker integration options to start recording frost and temperatures here.</div>`;
    // zone
    const z = m.zone;
    h += `<div class="card"><div class="sec">Hardiness zone</div>`;
    if (z.zone) {
      h += `<div class="row"><div class="grow"><div style="font-size:28px;font-weight:600">${esc(z.zone)}</div><div class="sub">From your sensors: average yearly low ${num(z.avg_min, 1)}°F over ${z.count} winter${z.count === 1 ? "" : "s"}</div></div></div>`;
    } else {
      h += `<div class="small mut">Needs one full winter of readings. Your sensors have not recorded enough yet${z.so_far ? `, lowest so far this winter is ${num(z.so_far.lowest, 1)}°F on ${fmtDate(z.so_far.date)}` : ""}.</div>`;
    }
    if (z.usda) h += `<div class="pill info" style="margin-top:8px">USDA map says ${esc(z.usda)}</div>`;
    if (z.winters.length) h += `<div class="small mut" style="margin-top:8px">${z.winters.map((w) => `${esc(w.label)}: ${num(w.lowest, 1)}°F${w.complete ? "" : " so far"}`).join(" · ")}</div>`;
    h += `</div>`;
    // frost
    const f = m.frost;
    h += `<div class="card"><div class="sec">Frost, ${f.threshold}°F or colder</div>`;
    const yrs = f.years;
    if (!yrs.length) h += `<div class="small mut">No readings yet.</div>`;
    else {
      h += `<table class="tbl"><tr><th></th><th>Last spring</th><th>First fall</th><th>Lowest</th></tr>`;
      h += `<tr><td>Expected</td><td>${fmtMd(f.expected_last)}</td><td>${fmtMd(f.expected_first)}</td><td></td></tr>`;
      for (const y of yrs) {
        const sp = y.last_spring ? fmtDate(y.last_spring) + (y.spring_partial ? "*" : y.spring_final ? "" : " so far") : y.spring_partial ? "no data" : "none";
        h += `<tr><td>${y.year}</td><td>${sp}</td><td>${y.first_fall ? fmtDate(y.first_fall) : "none"}</td><td>${num(y.lowest, 0)}°F</td></tr>`;
      }
      h += `</table>`;
      if (yrs.some((y) => y.spring_partial)) h += `<div class="small mut">* Readings started after the winter, so an earlier frost may have been missed.</div>`;
    }
    h += `</div>`;
    // soil
    const s2 = m.soil;
    h += `<div class="card"><div class="sec">Soil temperature</div>`;
    if (s2.expected === null && s2.actual === null) h += `<div class="small mut">Needs a few days of outside readings and a soil temperature sensor.</div>`;
    else {
      h += this._statGrid([["Expected", s2.expected === null ? "n/a" : `${num(s2.expected, 1)}°F`], ["Actual", s2.actual === null ? "n/a" : `${num(s2.actual, 1)}°F`], ["Last year", s2.last_year === null ? "n/a" : `${num(s2.last_year, 1)}°F`]]);
      if (s2.diff !== null) h += `<div class="pill ${Math.abs(s2.diff) >= 5 ? "warn" : "ok"}" style="margin-top:8px">${s2.diff === 0 ? "Right on expected" : `${num(Math.abs(s2.diff), 1)}°F ${s2.diff > 0 ? "warmer" : "colder"} than expected`}</div>`;
      h += `<div class="small mut" style="margin-top:6px">Expected is the average of the last 10 days of outside air temperature. Soil follows the air with a delay.</div>`;
    }
    h += `</div>`;
    // temps and rain
    const P = [["day", "Today"], ["week", "Week"], ["month", "Month"], ["year", "Year"]];
    h += `<div class="card"><div class="sec">High and low</div><table class="tbl"><tr><th></th><th>High</th><th>Low</th></tr>${P.map(([k, n]) => { const t = m.temps[k]; return `<tr><td>${n}</td><td>${t.high === null ? "-" : num(t.high, 0) + "°F"}</td><td>${t.low === null ? "-" : num(t.low, 0) + "°F"}</td></tr>`; }).join("")}</table></div>`;
    h += `<div class="card"><div class="sec">Rainfall</div>`;
    if (!m.rain.sensors.length) h += `<div class="small mut">Pick rainfall total sensors in Settings to track rain.</div>`;
    else h += `<table class="tbl"><tr><th></th><th>Rain</th></tr>${P.map(([k, n]) => `<tr><td>${n}</td><td>${num(m.rain[k], 2)} in</td></tr>`).join("")}</table>`;
    h += `</div>`;
    const AIRC = { pm1: ["#4fc3f7", "l"], pm25: ["#ffb300", "l"], pm10: ["#ef5350", "l"], nox: ["#ba68c8", "r"], voc: ["#81c784", "r"] };
    const air = Object.entries(m.air.metrics).filter(([k]) => (m.air.sensors[k] || []).length);
    if (air.length) {
      const rng = this._airRange || "day", RN = { day: "Last 24 hours, 15 minute averages", week: "Last 7 days, hourly averages. Dashed lines are each hour's highest", month: "Last 30 days, daily averages. Dashed lines are each day's highest" };
      h += `<div class="card"><div class="sec">Air quality</div><div class="seg" style="margin-bottom:6px">${[["day", "Day"], ["week", "Week"], ["month", "Month"]].map(([k, t]) => `<button data-act="air-range" data-s="${k}" class="${rng === k ? "on" : ""}">${t}</button>`).join("")}</div><div class="small">${RN[rng]}</div>`;
      h += `<div class="airleg">${air.map(([k, a]) => `<div class="stat" style="border-left:4px solid ${AIRC[k][0]}"><span>${esc(a.name.replace(" index", ""))}</span><b>${a.current === null ? "-" : num(a.current, 0)}</b><span class="small">high ${a.max.today === null ? "-" : num(a.max.today, 0)}</span></div>`).join("")}</div>`;
      h += airChart(air.map(([k, a]) => [k, a[rng], AIRC[k][0], AIRC[k][1]]), "Air quality");
      h += `<div class="small mut" style="margin-top:6px">Highest this week ${air.map(([k, a]) => `${a.name} ${a.max.week === null ? "-" : num(a.max.week, 1)}`).join(", ")}.</div></div>`;
    }
    if (m.humidity.sensors.length) h += `<div class="card"><div class="sec">Humidity</div><table class="tbl"><tr><th></th><th>High</th><th>Low</th></tr>${P.map(([k, n]) => { const t = m.humidity[k]; return `<tr><td>${n}</td><td>${t.high === null ? "-" : num(t.high, 0) + "%"}</td><td>${t.low === null ? "-" : num(t.low, 0) + "%"}</td></tr>`; }).join("")}</table></div>`;
    if (m.solar.sensors.length) h += `<div class="card"><div class="sec">Sun</div><table class="tbl"><tr><th></th><th>Average</th><th>Energy</th></tr>${P.map(([k, n]) => { const t = m.solar[k]; return `<tr><td>${n}</td><td>${t.avg === null ? "-" : num(t.avg, 0) + " W/m²"}</td><td>${t.days ? num(t.kwh, 1) + " kWh/m²" : "-"}</td></tr>`; }).join("")}</table><div class="small mut" style="margin-top:6px">Average is over the whole 24 hours, night included. Energy is the sunlight that landed on each square metre. A clear summer day is about 7 to 8 kWh/m².</div></div>`;
    return h;
  }
  _weatherCandidates(selected, test) {
    const st = (this._hass && this._hass.states) || {}, out = [];
    for (const [id, s2] of Object.entries(st)) {
      if (!id.startsWith("sensor.")) continue;
      const a = s2.attributes || {}, unit = String(a.unit_of_measurement || "").toLowerCase();
      if (test(a, unit, id) || selected.includes(id)) out.push([id, `${a.friendly_name || id} (${s2.state}${a.unit_of_measurement ? " " + a.unit_of_measurement : ""})`]);
    }
    return out;
  }
  _fMicro() {
    const m = this._snap.micro, c = m.settings, W = this._weatherCandidates.bind(this);
    if (this._web) {
      return {
        title: "Microclimate settings", submitLabel: "Save",
        fields: [
          { name: "usda_zone", label: "What USDA says your zone is", type: "text", placeholder: "7a", value: c.usda_zone || "" },
          { name: "frost_f", label: "Counts as a frost at or below (°F)", type: "number", step: "0.5", value: c.frost_f },
        ],
        note: "Frost dates, your zone, temperatures and rain come from the weather service for your location.",
        submit: (x) => this._call("set_microclimate", { usda_zone: x.usda_zone || " ", frost_f: x.frost_f }),
      };
    }
    const airMatch = { pm1: /pm[\s_.]?1(?![0-9])/i, pm25: /pm[\s_.]?2[\s_.]?5/i, pm10: /pm[\s_.]?10/i, nox: /nox/i, voc: /voc|volatile/i };
    return {
      title: "Microclimate settings", submitLabel: "Save",
      fields: [
        { name: "temp_entities", label: `Outside temperature: more sensors to average${c.outdoor_entity ? ` with ${c.outdoor_entity}` : ""} (tap to include)`, type: "multi", options: W(c.temp_entities, (a, u) => a.device_class === "temperature"), value: c.temp_entities.join(",") },
        { name: "rain_entities", label: "Rainfall total sensors (tap to include)", type: "multi", options: W(c.rain_entities, (a, u) => a.device_class === "precipitation" || ["in", "mm", "cm"].includes(u)), value: c.rain_entities.join(",") },
        { name: "humidity_entities", label: "Humidity sensors (tap to include)", type: "multi", options: W(c.humidity_entities, (a, u) => a.device_class === "humidity"), value: c.humidity_entities.join(",") },
        { name: "solar_entities", label: "Solar radiation sensors, W/m² (tap to include)", type: "multi", options: W(c.solar_entities, (a, u) => a.device_class === "irradiance" || u.endsWith("w/m²") || u.endsWith("w/m2")), value: c.solar_entities.join(",") },
        ...Object.entries({ pm1: "PM1", pm25: "PM2.5", pm10: "PM10", nox: "NOx", voc: "VOC" }).map(([k, t]) => ({ name: `air_${k}`, label: `Air quality, ${t} sensors (tap to include)`, type: "multi", options: W(c.air_entities[k], (a, u, id) => airMatch[k].test(id + " " + (a.friendly_name || "")) || a.device_class === ({ pm1: "pm1", pm25: "pm25", pm10: "pm10", nox: "nitrogen_oxides", voc: "volatile_organic_compounds" })[k]), value: c.air_entities[k].join(",") })),
        { name: "usda_zone", label: "What USDA says your zone is", type: "text", placeholder: "7a", value: c.usda_zone || "" },
        { name: "frost_f", label: "Counts as a frost at or below (°F)", type: "number", step: "0.5", value: c.frost_f },
      ],
      note: "Several sensors of one kind are averaged. Rain needs totals that count up through the day, week or year, not a rain rate. Past weather is read from Home Assistant's long-term statistics for these sensors, so history is there right away. Humidity and sun cards show once you pick sensors for them.",
      submit: (x) => {
        const list = (v) => String(v || "").split(",").filter(Boolean);
        return this._call("set_microclimate", { temp_entities: list(x.temp_entities), rain_entities: list(x.rain_entities), humidity_entities: list(x.humidity_entities), solar_entities: list(x.solar_entities), air_entities: { pm1: list(x.air_pm1), pm25: list(x.air_pm25), pm10: list(x.air_pm10), nox: list(x.air_nox), voc: list(x.air_voc) }, usda_zone: x.usda_zone || " ", frost_f: x.frost_f });
      },
    };
  }
  _homeView() {
    const gs = this._gardens(), every = this._vars();
    const nTrees = every.filter((v) => v.kind === "tree").length, nPlants = every.length - nTrees;
    if (this._tab === "trees" && !nTrees) this._tab = "all";
    if (this._tab === "plants" && !nPlants) this._tab = "all";
    const vs = this._tab === "trees" ? every.filter((v) => v.kind === "tree") : this._tab === "plants" ? every.filter((v) => v.kind !== "tree") : every;
    const pastN = this._vars(true).length + (this._snap.past_gardens || []).length;
    let h = `<div class="hd"><div class="ttl grow">Garden</div>${this._btn("form-view", "tune", "View")}${this._btn("form-variety", "plus", "Add plant", "", "primary")}</div>`;
    if (!gs.length && !every.length) {
      return h + `<div class="msg">${pastN ? "Add a garden to start adding plants." : "Create your first garden to start adding plants."} Trees can be added without a garden.<br><br>${this._btn("form-garden", "plus", "Add garden", "", "primary")}</div>` + (pastN ? `<button style="width:100%" data-act="open-archive">${this._icon("history")} History (${pastN})</button>` : "");
    }
    h += `<div class="chips">${gs.map((g) => `<button class="chip" data-act="open-g" data-g="${g.id}">${g.kind === "garden" ? "" : this._icon(KIND_ICON[g.kind]) + " "}${esc(g.name)}</button>`).join("")}${pastN ? `<button class="chip" data-act="open-archive">${this._icon("history")} History</button>` : ""}${this._config.garden ? "" : `<button class="chip" data-act="form-garden">${this._icon("plus")} Add</button>`}</div>`;
    if (!this._web) h += gs.map((g) => this._sensorBanner(g)).join("");
    const frost = gs.filter((g) => g.kind === "garden").map((g) => this._frostPill(g, gs.length > 1)).join("");
    if (frost) h += `<div>${frost}</div>`;
    const cnt = (l) => vs.filter((v) => v.status.level === l).length;
    const filters = [["all", `All ${vs.length}`], ["spray", `Spray due ${cnt("spray")}`], ["hold", `Harvest hold ${cnt("hold")}`], ["ok", `On track ${cnt("ok")}`]];
    if (nTrees && nPlants) h += `<div class="chips tabs">${[["all", `All ${every.length}`], ["trees", `Trees ${nTrees}`], ["plants", `Plants ${nPlants}`]].map(([k, t]) => `<button class="chip ${this._tab === k ? "on" : ""}" data-act="tab" data-s="${k}">${t}</button>`).join("")}</div>`;
    if (vs.length) {
      h += this._searchBox("home", "Search plants");
      h += `<div class="chips">${filters.map(([k, t]) => `<button class="chip ${this._filter === k ? "on" : ""}" data-act="filter" data-s="${k}">${t}</button>`).join("")}</div>`;
      h += `<div class="chips"><span class="small mut" style="align-self:center">Sort</span>${[["garden", "Garden"], ["name", "Name"], ["harvest", "Harvest"]].map(([k, t]) => `<button class="chip ${this._sort === k ? "on" : ""}" data-act="sort" data-s="${k}">${t}</button>`).join("")}</div>`;
    }
    const searching = !!String(this._q.home || "").trim();
    const shown = vs.filter((v) => (this._filter === "all" || v.status.level === this._filter) && this._matches(v, "home"));
    const covers = (g) => (this._filter === "all" && !searching && this._show.cover && g.kind === "garden" && this._tab !== "trees" ? g.cover.items.filter((i) => i.state !== "done") : []);
    const anyCover = gs.some((g) => covers(g).length);
    if (!vs.length && !anyCover) h += `<div class="msg">No plants yet. Tap Add plant.</div>`;
    else if (!shown.length && !anyCover) h += `<div class="msg">${searching ? "No plants match your search." : "Nothing matches this filter."}</div>`;
    const ordered = [...gs].sort((a, b) => KIND_ORDER[a.kind] - KIND_ORDER[b.kind]);
    if (this._compact && shown.length) {
      const attn = shown.filter((v) => v.status.level === "spray" || v.status.level === "hold"), rest = shown.filter((v) => !attn.includes(v));
      if (attn.length) h += `<div class="sec attn">Needs attention · ${attn.length}</div>` + this._sortVars(attn, this._sort === "garden" ? "name" : this._sort).map((v) => this._attnCard(v)).join("");
      if (rest.length) {
        const list = this._sort === "garden" ? [...rest].sort((a, b) => (a.garden_name || "~").localeCompare(b.garden_name || "~") || a.name.localeCompare(b.name)) : this._sortVars(rest, this._sort);
        h += `<div class="sec">${attn.length ? "Everything else" : "Plants"} · ${rest.length}</div><div class="lbox">${list.map((v) => this._lineRow(v, true)).join("")}</div>`;
      }
      for (const g of ordered) {
        const cov = g.kind === "garden" ? covers(g) : [];
        const place = g.kind !== "garden" && this._filter === "all" && !searching && this._tab !== "trees" && (vs.some((v) => v.garden === g.id) || (g.alarm && g.alarm.enabled && g.alarm.alerts.length > 0));
        if (!cov.length && !place) continue;
        if (!place) h += `<div class="sec">${esc(g.name)}</div>`;
        if (place) h += this._placeSummary(g);
        if (cov.length) h += this._coverTile(g, cov);
      }
      return h + this._microTile();
    }
    const flat = this._sort !== "garden";
    if (flat) h += this._sortVars(shown, this._sort).map((v) => this._row(v, true)).join("");
    for (const g of ordered) {
      const mine = flat ? [] : shown.filter((v) => v.garden === g.id), cov = g.kind === "garden" ? covers(g) : [];
      const place = !flat && g.kind !== "garden" && this._filter === "all" && !searching && this._tab !== "trees" && (vs.some((v) => v.garden === g.id) || (g.alarm && g.alarm.enabled && g.alarm.alerts.length > 0));  // empty racks and greenhouses stay off the landing page (still in the chips)
      if (!mine.length && !cov.length && !place) continue;
      if ((gs.length > 1 || shown.some((v) => !v.garden)) && !place) h += `<div class="sec">${esc(g.name)}</div>`;
      if (place) h += this._placeSummary(g);
      h += mine.map((v) => this._row(v)).join("");
      if (cov.length) h += this._coverTile(g, cov);
    }
    const loose = flat ? [] : shown.filter((v) => !v.garden);
    if (loose.length) h += `<div class="sec">Trees, no garden</div>` + loose.map((v) => this._row(v)).join("");
    h += this._microTile();
    return h;
  }
  _mixText(g) {
    const m = g.cover.mix;
    return m ? `${m.parts.map((p) => `${num(p.lbs, 2)} lb ${esc(p.crop)} (${p.pct}%)`).join(", ")}` : "";
  }
  _coverTile(g, list) {
    const growing = list.some((i) => i.state === "growing");
    const names = list.map((i) => i.crop).join(" + ");
    const gr = list.filter((i) => i.state === "growing"), wt = list.filter((i) => i.state === "waiting");
    const sown = list.map((i) => i.sown).sort()[0];
    const i = {
      crop: names, sown,
      days_in_ground: Math.max(...list.map((x) => x.days_in_ground)),
      days_left: Math.max(0, ...wt.map((x) => x.days_left || 0)),
      ready_date: wt.map((x) => x.ready_date).sort().pop(),
      days_since_term: Math.max(0, ...wt.map((x) => x.days_since_term || 0)),
      wait_days: Math.max(...list.map((x) => x.wait_days)),
      id: "__all__",
    };
    const c = growing ? "var(--ok)" : "var(--spray)";
    const stats = growing
      ? [["In the ground", `${i.days_in_ground} d`], ["Sown", fmtDate(i.sown)]]
      : [["Plant in", `${i.days_left} d`], ["Ready", fmtDate(i.ready_date)]];
    return `<div class="card tile" data-act="open-g" data-g="${g.id}"><div class="row"><div class="pic" style="background:color-mix(in srgb,${c} 18%,transparent);color:${c}"><ha-icon icon="mdi:grass" style="--mdc-icon-size:34px"></ha-icon></div><div class="grow"><div style="font-size:15px;font-weight:500">${esc(i.crop)}</div><div class="sub">Winter cover crop${list.length > 1 ? " mix" : ""}</div>${g.cover.mix ? `<div class="small mut">${this._mixText(g)}</div>` : ""}<span class="pill ${growing ? "ok" : "warn"}" style="margin:4px 0 0">${growing ? (wt.length ? `Growing, ${wt.map((x) => x.crop).join(" + ")} terminated` : "Growing") : `Waiting, day ${i.days_since_term} of ${i.wait_days}`}</span></div></div>${this._statGrid(stats)}${growing ? `<div class="row" style="margin-top:10px">${this._btn("form-terminate", "scissors-cutting", gr.length > 1 ? "Terminate all" : "Terminate", `data-g="${g.id}" data-e="${gr.length > 1 ? "__all__" : gr[0].id}"`, "grow")}</div>` : ""}</div>`;
  }
  _trayRow(g) {
    return `<div class="row" style="align-items:center"><span class="grow">${this._icon("tray-full")} 10x20 trays in use</span>${this._btn("trays", "minus", "", `data-g="${g.id}" data-d="-1"`, "ic")}<b style="min-width:28px;text-align:center;font-size:18px">${g.trays}</b>${this._btn("trays", "plus", "", `data-g="${g.id}" data-d="1"`, "ic")}</div>`;
  }
  _waterPill(g) {
    if (!this._show.water) return "";
    const w = g.water;
    if (w.level === "due") return `<span class="pill warn" style="margin:0">Water now</span>`;
    if (w.level === "soon") return `<span class="pill info" style="margin:0">Water tomorrow</span>`;
    if (w.level === "none") return `<span class="pill info" style="margin:0">No watering logged</span>`;
    return "";
  }
  _alarmBanner(g) {
    const a = g.alarm;
    if (!a || !a.enabled) return "";
    return a.alerts.map((x) => {
      const hot = x.kind === "high", lim = hot ? a.high : a.low;
      const t0 = new Date(x.start).getTime(), t1 = x.end ? new Date(x.end).getTime() : Date.now();
      const text = x.ongoing
        ? `${hot ? "Above" : "Below"} ${num(lim, 0)}°F for ${fmtDur(t1 - t0)}, since ${fmtClock(x.start)}. ${hot ? "Highest" : "Lowest"} so far ${num(x.peak, 0)}°F.`
        : `Was ${hot ? "above" : "below"} ${num(lim, 0)}°F for ${fmtDur(t1 - t0)} (${fmtClock(x.start)} to ${fmtClock(x.end)}). ${hot ? "Highest" : "Lowest"} ${num(x.peak, 0)}°F. Back in range now.`;
      const earlier = x.prior_n ? ` Before that it went ${hot ? "over" : "under"} the limit ${x.prior_n} other time${x.prior_n === 1 ? "" : "s"} (${fmtDur(x.prior_s * 1000)} in all).` : "";
      return `<div class="alarm"><b>${this._icon(hot ? "thermometer-alert" : "snowflake-alert")} ${hot ? "Too hot" : "Too cold"}: ${esc(g.name)}</b><div class="small" style="margin-top:4px">${text}${earlier}</div><div class="row">${this._btn("ack-alarm", "check", "Acknowledge", `data-g="${g.id}" data-k="${x.kind}"`, "grow")}</div></div>`;
    }).join("");
  }
  _sensorBanner(g) {
    const a = g.sensor_alarm;
    if (!a || !a.enabled) return "";
    const st = (this._hass && this._hass.states) || {};
    const WHAT = { moisture: "soil moisture", ec: "soil EC", soil_temp: "soil temperature", air_temp: "air temperature", out_temp: "outside temperature", par: "light", ph: "pH", power: "power" };
    return a.alerts.map((x) => {
      const name = (st[x.entity] && st[x.entity].attributes && st[x.entity].attributes.friendly_name) || x.entity;
      const t0 = new Date(x.since).getTime(), t1 = x.end ? new Date(x.end).getTime() : Date.now();
      const text = x.ongoing
        ? `No reading for ${fmtDur(t1 - t0)}, since ${fmtClock(x.since)}.`
        : `Had no reading for ${fmtDur(t1 - t0)} (${fmtClock(x.since)} to ${fmtClock(x.end)}). It is reporting again now.`;
      const earlier = x.prior_n ? ` It also dropped out ${x.prior_n} other time${x.prior_n === 1 ? "" : "s"} before you acknowledged (${fmtDur(x.prior_s * 1000)} in all).` : "";
      return `<div class="alarm"><b>${this._icon("access-point-off")} Sensor offline: ${esc(name)}</b><div class="small" style="margin-top:4px">${esc(g.name)}, ${WHAT[x.metric] || x.metric}. ${text}${earlier}</div><div class="row">${this._btn("ack-sensor", "check", "Acknowledge", `data-g="${g.id}" data-e="${esc(x.entity)}"`, "grow")}</div></div>`;
    }).join("");
  }
  _sensorAlarmCard(g) {
    const a = g.sensor_alarm;
    if (!a || (!a.in_use && !a.enabled)) return "";
    let h = `<div class="card"><div class="row"><div class="sec grow" style="margin:0">${this._icon("access-point-off")} Sensor offline alarm</div>${this._btn("toggle-sensor-alarm", "power", a.enabled ? "Turn off" : "Turn on", `data-g="${g.id}" data-p="${a.enabled ? "0" : "1"}"`, a.enabled ? "" : "primary")}</div>`;
    h += `<div class="small mut" style="margin-top:6px">${a.enabled ? `Warns when any of the ${a.in_use} sensor${a.in_use === 1 ? "" : "s"} in use reports nothing for an hour. A probe marked out is ignored.` : "Off. No warnings for sensors that stop reporting."}</div>`;
    if (a.enabled && a.acknowledged.length) h += `<div class="small mut" style="margin-top:4px">${a.acknowledged.length} acknowledged and still offline. It warns again after it has reported once.</div>`;
    return h + `</div>`;
  }
  _alarmCard(g) {
    const a = g.alarm;
    const lim = [a.high !== null ? `Alarm above <b>${num(a.high, 0)}°F</b>` : "", a.low !== null ? `Alarm below <b>${num(a.low, 0)}°F</b>` : ""].filter(Boolean).join("<br>");
    let h = `<div class="card"><div class="row"><div class="sec grow" style="margin:0">${this._icon("alarm-light")} Temperature alarm</div>${this._btn("toggle-alarm", "power", a.enabled ? "Turn off" : "Turn on", `data-g="${g.id}" data-p="${a.enabled ? "0" : "1"}"`, a.enabled ? "" : "primary")}</div>`;
    h += `<div class="small" style="margin:6px 0">${a.enabled ? lim || "No limits set." : `<span class="mut">Off. ${lim ? lim.replace(/<br>/g, ", ").replace(/<\/?b>/g, "") + "." : "Set a limit to use it."}</span>`}</div>`;
    if (a.enabled && a.acknowledged.length) h += `<div class="small mut">Acknowledged and still ${a.acknowledged.map((k) => (k === "high" ? "above the high limit" : "below the low limit")).join(" and ")}. It will warn again after the air has been back in range.</div>`;
    h += `<div class="row" style="margin-top:8px">${this._btn("form-alarm", "cog", "Set limits", `data-g="${g.id}"`)}</div></div>`;
    return h;
  }
  _placeSummary(g) {
    const t = g.metrics.air_temp, w = g.water, c = g.climate, par = g.metrics.par;
    const out = g.metrics.out_temp;
    const stats = [["Temperature", t.current === null ? "–" : `${num(t.current, 0)}°F`], ...(out ? [["Outside", out.current === null ? "–" : `${num(out.current, 0)}°F`]] : []), ["Watered", w.days_since === null ? "Never" : w.days_since === 0 ? "Today" : `${w.days_since} d ago`]];
    if (par) stats.push(["Light", par.current === null ? "–" : `${num(par.current, 0)} PAR`]);
    return `<div class="card tile" data-act="open-g" data-g="${g.id}">${this._alarmBanner(g)}<div class="row"><div class="pic" style="background:color-mix(in srgb,var(--info) 18%,transparent);color:var(--info)"><ha-icon icon="mdi:${KIND_ICON[g.kind]}" style="--mdc-icon-size:34px"></ha-icon></div><div class="grow"><div style="font-size:15px;font-weight:500">${esc(g.name)}</div><div class="sub">${esc(g.kind_name)}</div>${this._climatePill(c)}${this._waterPill(g)}</div></div>${this._statGrid(stats)}<div style="margin-top:8px">${this._trayRow(g)}</div><div class="row" style="margin-top:10px">${this._btn("log-water", "watering-can", "Water", `data-g="${g.id}"`, "grow")}</div></div>`;
  }
  _climatePill(c) {
    if (!c || this._web) return "";
    const m = { heating: ["warn", "Heating"], cooling: ["info", "Fan on (too warm)"], idle: ["ok", "Holding"], resting: ["info", "Resting (max run reached)"], no_sensor: ["warn", "No temperature, heaters off"], off: ["none", "Thermostat off"] }[c.state] || ["none", c.state];
    let h = `<span class="pill ${m[0]}" style="margin:4px 6px 0 0">${m[1]}</span>`;
    if (c.fan_on && c.state !== "cooling") h += `<span class="pill info" style="margin:4px 6px 0 0">Fan running (schedule)</span>`;
    if (c.light_sched) h += `<span class="pill ${c.lights_on ? "spray" : "none"}" style="margin:4px 6px 0 0">Lights ${c.lights_on ? "on" : "off"}</span>`;
    return h;
  }
  _placeView(g) {
    const gid = g.id, all = this._vars().filter((v) => v.garden === gid), mine = this._sortVars(all.filter((v) => this._matches(v, "g" + gid)), this._sort);
    let h = `<div class="hd">${this._btn("back", "arrow-left", "", "", "ic")}<div class="grow"><div class="ttl">${esc(g.name)}</div><div class="sub">${esc(g.kind_name)}, ${mine.length} planting${mine.length === 1 ? "" : "s"}</div></div>${this._btn("edit-g", "cog", "", `data-g="${gid}"`, "ic")}</div>`;
    h += this._alarmBanner(g) + this._sensorBanner(g);
    if (g.climate && !this._web) h += this._climateCard(g);
    if (g.alarm && !this._web) h += this._alarmCard(g);
    h += this._soilCards(g);
    h += this._waterCard(g);
    if (g.power && !this._web) h += this._powerCard(g);
    h += `<div class="card">${this._trayRow(g)}${this._traysCalc(g)}</div>`;
    h += `<div class="card"><div class="row"><div class="sec grow" style="margin:0">Plants here</div>${this._btn("form-variety", "plus", "Add plant", `data-g="${gid}"`)}</div>${all.length > 3 ? this._searchBox("g" + gid, "Search plants here") : ""}${all.length && !mine.length ? `<div class="small mut" style="margin:6px 0">No plants match your search.</div>` : ""}${all.length ? "" : `<div class="small mut" style="margin:6px 0">None yet.</div>`}</div>`;
    h += mine.map((v) => this._tile(v)).join("");
    if (!this._web) h += this._sensorAlarmCard(g);
    if (all.length) h += `<div class="small mut" style="margin:8px 4px">To remove this place, archive its plants first. Its history is kept.</div>`;
    if (!all.length) h += `<div class="card">${this._confirm === "rmg" ? `<div class="conf">Remove ${esc(g.name)}? It leaves your list. Its history is kept under Past plants and you can bring it back.<div class="row"><button data-act="cancel-del">Keep</button><button class="danger" data-act="do-rmg" data-g="${gid}">Remove</button></div></div>` : `<button class="danger" data-act="ask-rmg">Remove ${esc(g.kind_name.toLowerCase())}</button>`}</div>`;
    return h;
  }
  _powerCard(g) {
    const p = g.power;
    const usd = (n) => (n === null || n === undefined ? "" : `$${n.toFixed(2)}`);
    let h = `<div class="card"><div class="row"><div class="sec grow" style="margin:0">${this._icon("flash")} Power use</div>${this._btn("form-rate", "cash", p.rate ? `${num(p.rate, 2)}¢ per kWh` : "Set rate", `data-g="${g.id}"`)}</div>`;
    h += `<div class="row" style="align-items:baseline;gap:22px;margin:6px 0"><div><span class="ph">${p.rate ? usd(p.today_cost) : num(p.today, 2)}</span> <span class="small mut">${p.rate ? `today, ${num(p.today, 2)} kWh` : "kWh today"}</span></div><div><span class="ph">${p.rate ? usd(p.month_cost) : num(p.month, 1)}</span> <span class="small mut">${p.rate ? `this month, ${num(p.month, 1)} kWh` : "kWh this month"}</span></div></div>`;
    if (!p.rate) h += `<div class="small mut" style="margin-bottom:6px">Set your rate in cents per kWh to see dollars.</div>`;
    if (p.groups.length > 1) h += `<div class="small mut" style="margin-bottom:6px">${p.groups.map((r) => `${esc(r.name)}: ${num(r.today, 2)} kWh${p.rate ? ` (${usd(r.today_cost)})` : ""} today, ${num(r.month, 1)} kWh${p.rate ? ` (${usd(r.month_cost)})` : ""} this month`).join("<br>")}</div>`;
    h += barChart(p.days);
    const ms = p.months.slice(-6).reverse();
    if (ms.length > 1) h += `<div class="small mut" style="margin-top:6px">${ms.map((m) => `${new Date(m.month + "-15").toLocaleDateString(undefined, { month: "short", year: "numeric" })}: ${num(m.kwh, 1)} kWh${p.rate ? `, ${usd(m.cost)}` : ""}`).join("<br>")}</div>`;
    return h + `</div>`;
  }
  _traysCalc(g) {
    const t = g.trays_calc;
    if (!t || !t.total) return "";
    const parts = t.rows.map((r) => `${r.plants} in ${esc(r.container)} (${r.per_tray} per tray)`).join(", ");
    return `<div class="small mut" style="margin-top:6px">Your plants fill about ${t.total} tray${t.total === 1 ? "" : "s"}: ${parts}.${t.unknown ? ` ${t.unknown} more are in other pots.` : ""}${t.total !== g.trays ? ` ${this._btn("trays-set", "", `Use ${t.total}`, `data-g="${g.id}" data-n="${t.total}"`)}` : ""}</div>`;
  }
  _waterCard(g) {
    if (!this._show.water) return "";
    const w = g.water, gid = g.id;
    let h = `<div class="card"><div class="row"><div class="sec grow" style="margin:0">${this._icon("watering-can")} Watering</div>${this._btn("log-water", "plus", "Water now", `data-g="${gid}"`, "primary")}</div>`;
    h += `<div class="row" style="align-items:baseline;margin:6px 0"><span class="ph">${w.days_since === null ? "–" : w.days_since === 0 ? "Today" : `${w.days_since} d`}</span><span class="small mut">${w.last ? `since ${fmtDate(w.last)}` : "no watering logged yet"}</span></div>`;
    h += `<div class="row" style="flex-wrap:wrap;gap:6px">${this._waterPill(g)}${this._btn("form-water-every", "bell-outline", w.every ? `Every ${w.every} days` : "Set reminder", `data-g="${gid}"`)}</div>`;
    const est = g.metrics && g.metrics.moisture && g.metrics.moisture.estimate;
    if (est) {
      const left = est.level === "dry" || est.days_left <= 0 ? "It is time to water." : est.days_left === 1 ? "Plan to water tomorrow." : est.days_left > 14 ? "No watering needed for two weeks or more." : `Plan to water in about ${est.days_left} days.`;
      h += `<div style="margin:10px 0 4px"><span class="ph">${num(g.metrics.moisture.current, 0)}%</span> <span class="small mut">estimated soil moisture, about ${Math.round(est.avail * 100)}% of the water this soil can hold</span></div>`;
      h += `<div class="small" style="margin-bottom:4px">${left} ${est.watered ? `Worked out from the watering ${est.since_water === 0 ? "today" : `${est.since_water} day${est.since_water === 1 ? "" : "s"} ago`}, ` : "No recent watering is logged, so this starts from half full. Worked out from "}the weather, ${esc(est.soil_name.toLowerCase())} soil${est.mulch ? " and the mulch" : ", no mulch"}. Log a moisture reading to replace it.</div>`;
    }
    if (g.soil_setup) h += `<div class="row" style="margin-top:6px">${this._btn("form-soil", "sprout", `${g.soil_setup.soils.find((x) => x.key === g.soil_setup.soil).name}, ${g.soil_setup.mulch ? "mulched" : "no mulch"}`, `data-g="${gid}"`)}</div>`;
    for (const e of w.log.slice(0, 5)) h += this._logRow("water", gid, e.id, "Watered", `${fmtDate(e.date)}${e.notes ? " · " + esc(e.notes) : ""}`);
    return h + `</div>`;
  }
  _clock(hhmm, addHours = 0) {
    const [h, m] = hhmm.split(":").map(Number), t = (h * 60 + m + Math.round(addHours * 60)) % 1440;
    return new Date(2000, 0, 1, Math.floor(t / 60), t % 60).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" });
  }
  _fanText(c) {
    if (!c.fan_sched) return "";
    const every = c.fan_every === 1 ? "hour" : `${num(c.fan_every, 1)} hours`;
    return `Fans also run ${c.fan_minutes} min every ${every}${c.fan_lights_only && c.light_sched ? ", only while the lights are on" : ""}.`;
  }
  _climateCard(g) {
    const c = g.climate, gid = g.id, rack = g.kind === "rack", st = (this._hass && this._hass.states) || {};
    const nm = (id) => ((st[id] && st[id].attributes && st[id].attributes.friendly_name) || id);
    const list = (a) => (a.length ? a.map((e) => esc(nm(e))).join(", ") : "none chosen");
    let h = `<div class="card"><div class="row"><div class="sec grow" style="margin:0">${this._icon("thermostat")} ${rack ? "Heat mats, fans and lights" : "Heating and fans"}</div>${this._btn("toggle-climate", "power", c.enabled ? "Turn off" : "Turn on", `data-g="${gid}" data-p="${c.enabled ? "0" : "1"}"`, c.enabled ? "" : "primary")}</div>`;
    h += `<div style="margin:6px 0">${this._climatePill(c)}</div>`;
    h += `<div class="row" style="align-items:baseline;gap:22px;margin:6px 0"><div><span class="ph">${c.temp === null ? "–" : num(c.temp, 0) + "°"}</span> <span class="small mut">now</span></div><div class="small">${rack ? "Heat mats on" : "Heat"} below <b>${num(c.heat_set, 0)}°F</b>, off at <b>${num(c.heat_off_at, 1)}°F</b><br>Fans on above <b>${num(c.cool_set, 0)}°F</b>, off at <b>${num(c.cool_off_at, 1)}°F</b></div></div>`;
    const lim = [c.heat_min_run ? `at least ${c.heat_min_run} min` : "", c.heat_max_run ? `at most ${c.heat_max_run} min, then rests ${c.heat_rest} min` : ""].filter(Boolean);
    if (lim.length) h += `<div class="small mut" style="margin-bottom:4px">Each heater run: ${lim.join(", ")}.</div>`;
    if (c.fan_min_run) h += `<div class="small mut" style="margin-bottom:4px">Once the fans start for heat they run at least ${c.fan_min_run} min.</div>`;
    if (c.light_sched) h += `<div class="small" style="margin-bottom:4px">${this._icon("lightbulb-on-outline")} Lights ${c.light_hours === 24 ? "on all day" : `${num(c.light_hours, 1)} h a day, ${this._clock(c.light_on)} to ${this._clock(c.light_on, c.light_hours)}`}${c.lights_on ? " (on now)" : " (off now)"}.</div>`;
    const fan = this._fanText(c);
    if (fan) h += `<div class="small" style="margin-bottom:4px">${this._icon("fan")} ${fan}</div>`;
    h += `<div class="small mut">${rack ? "Heat mats" : "Heaters"}: ${list(c.heaters)}<br>Fans: ${list(c.coolers)}${rack ? `<br>Lights: ${list(c.lights)}` : ""}</div>`;
    if (c.enabled && !c.heaters.length && !c.coolers.length) h += `<div class="pill warn" style="margin:8px 0">Pick ${rack ? "a heat mat or fan" : "a heater or fan"} under Set up.</div>`;
    if (c.light_sched && !c.lights.length) h += `<div class="pill warn" style="margin:8px 0">The light schedule is on but no lights are chosen. Pick them under Set up.</div>`;
    if (c.fan_sched && !c.coolers.length) h += `<div class="pill warn" style="margin:8px 0">The fan schedule is on but no fans are chosen. Pick them under Set up.</div>`;
    if (c.enabled && !g.metrics.air_temp.entities.length) h += `<div class="pill warn" style="margin:8px 0">Pick a temperature sensor below. Without one the heaters and thermostat fans stay off. The light and fan schedules don't need it.</div>`;
    h += `<div class="row" style="margin-top:8px">${this._btn("form-climate", "cog", "Set up", `data-g="${gid}"`)}</div></div>`;
    return h;
  }
  _whereCard(v) {
    const place = v.location_kind !== "garden";
    if (!place && !v.moves.length) return "";
    let h = `<div class="card"><div class="row"><div class="sec grow" style="margin:0">${this._icon(KIND_ICON[v.location_kind] || "map-marker")} ${esc(v.garden_name)}${place && v.container ? `, ${esc(v.container)}` : ""}</div>${place && !v.archived ? `${this._btn("form-move", "arrow-right-bold", "Move", `data-v="${v.id}"`)}${this._btn("form-upot", "arrow-up-bold-box-outline", "Up-pot", `data-v="${v.id}"`)}` : ""}</div>`;
    for (const m of v.moves) h += `<div class="small mut" style="margin-top:4px">${fmtDate(m.date)}: ${esc(m.from)} to ${esc(m.to)}, ${m.count} plant${m.count === 1 ? "" : "s"}</div>`;
    return h + `</div>`;
  }
  _row(v, withGarden) { return this._tile(v, withGarden); }
  _attnCard(v) {
    const a = v.alert, lvl = v.status.level;
    const kind = a ? (a.state === "open" ? "open" : "soon") : lvl === "hold" ? "open" : "soon";
    const est = (a && a.state === "soon" && a.date_low && a.date_low !== a.date_high) ? `<div class="small" style="margin-top:2px">Likely ${fmtDate(a.date_low)} to ${fmtDate(a.date_high)}</div>` : "";
    let mid;
    if (a) {
      const pct = Math.max(0, Math.min(100, (a.dd / a.target) * 100));
      mid = `<div class="small">${esc(v.species_name)} · ${esc(a.pest)}</div><div class="small" style="margin-top:6px">${num(a.dd, 0)} of ${a.target} degree days${v.pests.some((p) => p.status && p.status.estimated_start) ? " since Jan 1" : ""}</div><div class="bar"><i style="width:${pct}%"></i></div>${est}`;
    } else mid = `<div class="small">${esc(v.species_name)}</div><div class="small" style="margin-top:2px">${esc(v.status.text)}</div>`;
    const big = a ? (a.state === "open" ? "Now" : `${a.days} day${a.days === 1 ? "" : "s"}`) : lvl === "hold" ? "Hold" : "Soon";
    const small = a ? (a.state === "open" ? "spray window open" : `first spray about ${fmtDate(a.date)}`) : "";
    return `<div class="acard ${kind}" data-act="open-v" data-v="${v.id}"><div class="grow" style="min-width:0"><div class="an">${esc(v.name)}</div>${mid}</div><div class="ar"><div class="ab">${esc(big)}</div><div class="small">${esc(small)}</div>${a ? `<button data-act="form-spray" data-v="${v.id}">Sprayed</button>` : ""}</div></div>`;
  }
  _lineRow(v, withGarden) {
    const tree = v.kind === "tree", inPlace = v.location_kind !== "garden";
    const sub = [v.species_name, tree ? null : `${v.alive} of ${v.count}`, inPlace ? v.container : null, withGarden ? (v.garden_name || "No garden") : null].filter(Boolean).join(" · ");
    const hv = !tree ? this._stats(v).find((x) => x[0] === "Harvest in") : null;
    const stat = tree ? yrs(v.age_years) : hv ? "harvest in " + hv[1] : v.status.text;
    return `<div class="lrow" data-act="open-v" data-v="${v.id}"><b>${esc(v.name)}</b><span class="sub grow">${esc(sub)}</span><span class="small">${esc(stat)}</span></div>`;
  }
  _tile(v, withGarden) {
    const tree = v.kind === "tree";
    const inPlace = v.location_kind !== "garden";
    const sub = [v.species_name, tree ? null : `${v.alive} of ${v.count} plants`, inPlace ? v.container : null, withGarden ? (v.garden_name || "No garden") : null].filter(Boolean).join(", ");
    const pest = tree ? v.pests.find((p) => p.status && p.status.next_dd) : null;
    const stats = this._stats(v).slice(0, 3), planted = this._web ? stats.find((x) => x[0] === "Planted") : null;
    let h = `<div class="card tile" data-act="open-v" data-v="${v.id}"><div class="row">${this._picBox(v)}<div class="grow"><div style="font-size:15px;font-weight:500">${esc(v.name)}</div><div class="sub">${esc(sub)}</div><span class="pill ${v.status.level}">${esc(v.status.text)}</span></div>${planted ? `<div class="pdays"><span>Planted</span><b>${esc(planted[1])}</b></div>` : ""}</div>`;
    const rest = stats.filter((x) => x !== planted);
    if (rest.length) h += this._statGrid(rest);
    if (pest) {
      const s = pest.status;
      h += `<div style="margin-top:10px;font-size:12px" class="row"><span class="mut grow">${esc(pest.name)} degree days</span><b>${s.dd} / ${s.next_dd}</b></div><div class="bar"><i style="width:${Math.min(100, (s.dd / s.next_dd) * 100)}%"></i></div>`;
    }
    if (v.total_lbs > 0) h += `<div class="small mut" style="margin-top:8px">Harvested so far: ${num(v.total_lbs, 1)} lb</div>`;
    const q = inPlace ? [["form-move", "arrow-right-bold", "Move"], ["form-upot", "arrow-up-bold-box-outline", "Up-pot"]]
      : tree ? [["form-spray", "spray", "Sprayed"], ["form-harvest", "basket", "Harvest"]] : [["form-fert", "sprout", "Fed"], ["form-harvest", "basket", "Harvest"]];
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
    let h = `<div class="hd">${this._btn("back", "arrow-left", "", "", "ic")}<div class="grow"><div class="ttl">${esc(v.name)}</div><div class="sub">${esc([v.species_name, v.garden_name, tree ? "" : `${v.alive} of ${v.count} plants alive`].filter(Boolean).join(", "))}</div></div>${arch ? "" : this._btn("edit-v", "pencil", "", `data-v="${id}"`, "ic")}</div>`;
    if (arch) {
      h += `<div class="card"><span class="pill info">${esc(ARCH_TEXT[arch.reason])}, ${fmtDate(arch.date, true)}</span>${arch.notes ? `<p style="margin:8px 0 0">${esc(arch.notes)}</p>` : ""}<div class="row" style="margin-top:10px">${this._btn("form-again", "sprout", "Plant again", `data-v="${id}"`, "primary")}${this._btn("restore", "undo", "Restore", `data-v="${id}"`)}</div></div>`;
    } else {
      h += `<div class="card"><div class="row">${this._picBox(v)}<div class="grow"><span class="pill ${v.status.level}" style="margin:0">${esc(v.status.text)}</span></div></div>${this._statGrid(this._stats(v))}${tree ? "" : `<div class="row" style="margin-top:10px"><button class="grow" data-act="form-stage" data-v="${id}">${this._icon("sprout")} Log up-potting or in-ground</button></div>`}</div>`;
    }
    h += this._whereCard(v);
    h += this._projection(v);
    h += this._harvestCard(v, arch);
    if (tree) h += this._pruneCard(v, arch) + this._sprayCard(v, arch);
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
      h += `<div class="row" style="align-items:baseline"><span class="big">${fmtDate(v.expected_harvest)}</span><span class="small mut">${v.countdown ? esc(v.countdown) : dIn(v.days_to_expected)}${v.expected_yield ? `, about ${num(v.expected_yield * v.alive, 1)} lb expected` : ""}</span></div>`;
    }
    return h + `</div>`;
  }
  _harvestCard(v, arch) {
    const id = v.id;
    let h = `<div class="card"><div class="row"><div class="grow"><div class="sec" style="margin:0">Harvest</div><div class="big">${num(v.total_lbs, 1)} lb</div></div>${!arch && v.alive ? this._btn("form-harvest", "basket", v.single_harvest ? "Harvest" : "Log harvest", `data-v="${id}"`, "primary") : ""}</div>`;
    if (v.single_harvest) h += `<div class="small mut" style="margin-top:4px">Pulled when harvested: each plant is finished once it is harvested.</div>`;
    if (!arch && !v.alive) h += `<div class="small mut">No living plants to receive a harvest.</div>`;
    if (v.grouped) {
      h += `<div class="plant"><div class="row"><div class="grow"><b style="font-weight:500">${v.single_harvest ? `${v.alive} still growing${v.harvested ? `, ${v.harvested} harvested` : ""} of ${v.count} plants` : `${v.alive} of ${v.count} plants alive`}</b><div class="small mut">Average ${num(v.per_plant_avg, 2)} lb per plant. Each pick is split evenly across the living plants.</div></div>${!arch && v.alive ? this._btn("form-lost", "alert", "Mark lost", `data-v="${id}"`) : ""}</div>`;
      for (const g of v.lost) {
        h += `<div class="row" style="margin-top:8px"><div class="pill bad grow" style="margin:0">${g.count} ${g.status === "pulled" ? "pulled early" : "died"}, ${esc(REASON_TEXT[g.reason] || g.reason)}${g.date ? ` · ${fmtDate(g.date)}` : ""}${g.note ? `: ${esc(g.note)}` : ""}</div>${arch ? "" : `<button data-act="restore-lost" data-v="${id}" data-n="${g.count}" data-s="${g.status}" data-r="${esc(g.reason)}" data-d="${g.date || ""}">Restore</button>`}</div>`;
      }
      h += `</div>`;
    } else for (const p of v.plants) {
      h += `<div class="plant"><div class="row"><b style="font-weight:500" class="grow">${esc(p.label)}</b><span style="font-size:18px;font-weight:500">${num(p.total, 1)} lb</span></div>`;
      if (p.status === "harvested") h += `<div class="pill ok" style="margin:6px 0 0">Harvested${p.status_date ? ", " + fmtDate(p.status_date) : ""}</div>`;
      else if (p.status !== "alive") h += `<div class="pill bad" style="margin:6px 0 0">${esc(STATUS_TEXT[p.status])}, ${esc(REASON_TEXT[p.reason] || p.reason)}${p.note ? `: ${esc(p.note)}` : ""}</div>`;
      if (!arch && p.status !== "harvested") h += `<div class="seg" style="margin-top:8px">${["alive", "dead", "pulled"].map((s) => `<button class="${p.status === s ? (s === "alive" ? "on" : "bad") : ""}" data-act="${s === "alive" ? "plant-alive" : "form-status"}" data-v="${id}" data-p="${p.id}" data-s="${s}">${STATUS_TEXT[s]}</button>`).join("")}</div>`;
      h += `</div>`;
    }
    if (v.harvests.length) h += `<div class="sec" style="margin:12px 0 0">Pick history</div>`;
    for (const x of v.harvests) {
      h += this._logRow("harvest", id, x.id, `${fmtDate(x.date)}, ${num(x.lbs)} lb`,
        `${x.ended ? `${x.ended} plant${x.ended === 1 ? "" : "s"} pulled, ` : ""}${num(x.each)} lb each to ${esc(x.to_text)}${x.notes ? ` · ${esc(x.notes)}` : ""}`, x.ended ? `The ${x.ended} plant${x.ended === 1 ? "" : "s"} it harvested go back to growing, and the planting returns from Past plants if this was the last of it.` : `This takes ${num(x.each)} lb off each plant that received it.`);
    }
    return h + `</div>`;
  }
  _pruneCard(v, arch) {
    const p = v.pruning, id = v.id;
    if (!p) return "";
    const done = p.last ? `${p.state === "skipped" ? "No pruning needed" : "Pruned"} ${fmtDate(p.last.date)}` : "";
    const msg = { due: `Time to prune. ${p.note} This reminder stays until you mark the tree pruned or not needing it.`, waiting: `The reminder starts ${fmtDate(p.start, true)}. ${p.note}`, pruned: `${done}. No more reminders this year.`, skipped: `${done}. No more reminders this year.` }[p.state];
    let h = `<div class="card"><div class="row"><div class="sec grow" style="margin:0">${this._icon("scissors-cutting")} Pruning</div><span class="pill ${p.state === "due" ? "spray" : p.state === "waiting" ? "info" : "ok"}" style="margin:0">${{ due: "Due now", waiting: "Not yet", pruned: "Done", skipped: "Not needed" }[p.state]}</span></div>`;
    h += `<div class="small" style="margin-top:8px">${esc(msg)}</div>`;
    if (!arch) h += `<div class="row" style="margin-top:10px;flex-wrap:wrap;gap:6px">${this._btn("form-prune", "scissors-cutting", "Pruned", `data-v="${id}"`, p.state === "due" ? "primary" : "")}${this._btn("prune-skip", "check", "No pruning needed this year", `data-v="${id}"`)}${this._btn("form-prune-month", "calendar", `Remind me in ${p.month_name}`, `data-v="${id}"`)}</div>`;
    if (p.log.length) h += `<div class="sec" style="margin:12px 0 0">Pruning log</div>`;
    for (const x of p.log) h += this._logRow("prune", id, x.id, x.outcome === "skipped" ? "No pruning needed" : "Pruned", fmtDate(x.date) + (x.notes ? " · " + esc(x.notes) : ""));
    return h + `</div>`;
  }
  _sprayCard(v, arch) {
    const s = v.spray, id = v.id;
    let h = `<div class="card"><div class="row"><div class="sec grow" style="margin:0">Pest management</div>${arch ? "" : this._btn("form-spray", "spray", "Sprayed", `data-v="${id}"`, "primary")}</div>`;
    h += this._statGrid([["Next spray", s.next_in === null ? "–" : dIn(s.next_in)], ["Safe to harvest", s.safe_in === null ? "–" : s.safe_in === 0 ? "now" : `${s.safe_in} d`], ["Spray cutoff", s.cutoff_in === null ? "–" : dIn(s.cutoff_in)]]);
    for (const p of v.pests) {
      if (p.status) {
        const st = p.status;
        h += `<div style="margin-top:10px;font-size:12px" class="row"><span class="grow">${esc(p.name)} degree days</span><b>${st.dd}${st.next_dd ? ` / ${st.next_dd}` : ""}</b></div><div class="bar"><i style="width:${st.next_dd ? Math.min(100, (st.dd / st.next_dd) * 100) : 100}%"></i></div>${st.next_action ? `<div class="small mut" style="margin-top:4px">${esc(st.next_action)}${p.est_days ? `, about ${fmtDate(this._isoAdd(this._snap.today, p.est_days))} (in ${p.est_days} day${p.est_days === 1 ? "" : "s"}${p.est_low !== null && p.est_high !== null && p.est_low !== p.est_high ? `, likely ${fmtDate(this._isoAdd(this._snap.today, p.est_low))} to ${fmtDate(this._isoAdd(this._snap.today, p.est_high))}` : ""})` : ""}</div>` : ""}${st.estimated_start && !arch ? `<div class="row" style="margin-top:6px"><span class="small mut grow">Counted from Jan 1, no trap needed. If you trap, log the first catch and it replaces this.</span>${this._btn("form-biofix", "calendar", "Log first catch", `data-v="${id}" data-s="${p.key}"`)}</div>` : ""}`;
      } else if (p.trap) {
        const t = p.trap, id2 = v.id;
        const line = { early: `Hang traps high in the canopy by ${fmtDate(t.monitor_from, true)}.`, watch: `Check your traps. Spray within ${t.spray_within_days} days of a sharp rise in catches, usually ${t.usual}.`, spray: `Spray by ${fmtDate(t.spray_by, true)} (${t.days_left === 0 ? "today" : `${t.days_left} day${t.days_left === 1 ? "" : "s"} left`}).`, late: `Past the ${t.spray_within_days} days since the catches rose (${fmtDate(t.spray_by, true)}). Spray now.`, sprayed: `Sprayed ${fmtDate(t.sprayed)}. Bait is repeated every ${t.bait_every_days} days while flies are caught.` }[t.state];
        h += `<div style="margin-top:10px"><div class="row"><b class="grow" style="font-weight:500">${esc(p.name)}</b><span class="pill ${t.state === "spray" || t.state === "late" ? "spray" : "info"}" style="margin:0">${{ early: "Not yet", watch: "Watching", spray: "Spray due", late: "Overdue", sprayed: "Sprayed" }[t.state]}</span></div><div class="small" style="margin-top:4px">${esc(line)}</div><div class="small mut" style="margin-top:4px">No degree-day model. Timing comes from trap catches. ${esc(t.products)}</div>${arch ? "" : `<div class="row" style="margin-top:6px">${this._btn("form-biofix", "calendar", t.catch ? `Catches rose ${fmtDate(t.catch, true)}` : "Log the rise in catches", `data-v="${id2}" data-s="${p.key}"`)}</div>`}</div>`;
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
    if (v.feeding_off && !tree) h += `<div class="small mut" style="margin:6px 0">No feeding plan between the first fall frost and the last spring frost.</div>`;
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
    if (g.kind !== "garden") return this._placeView(g);
    const ph = g.ph, gid = g.id;
    let h = `<div class="hd">${this._btn("back", "arrow-left", "", "", "ic")}<div class="grow"><div class="ttl">${esc(g.name)}</div><div class="sub">${this._vars().filter((v) => v.garden === gid).length} plants</div></div>${this._btn("edit-g", "cog", "", `data-g="${gid}"`, "ic")}</div>`;
    h += this._frostPill(g, false) + this._sensorBanner(g) + this._choreCard(g) + this._tiles(g) + this._seasonCard(g);
    h += `<div class="card"><div class="row"><div class="sec grow" style="margin:0">Soil pH</div>${ph.level ? `<span class="pill ${ph.level === "ok" ? "ok" : "warn"}" style="margin:0">${ph.level === "ok" ? "In range" : ph.level === "low" ? "Below target" : "Above target"}</span>` : ""}</div>`;
    if (ph.current !== null) {
      const d = ph.first && ph.first.date !== ph.date ? ph.current - ph.first.value : null;
      h += `<div class="row" style="align-items:baseline;margin:6px 0"><span class="ph">${num(ph.current, 2)}</span><span class="small mut">target ${ph.target[0]} to ${ph.target[1]}${d !== null ? `, ${d < 0 ? "down" : "up"} ${num(Math.abs(d), 2)} since ${fmtDate(ph.first.date)}` : ""}</span></div>`;
      h += `<div class="small mut" style="margin-bottom:8px">${ph.source === "sensor" ? "Sensor" : "Manual reading"}, ${fmtDate(ph.date)}</div>`;
    } else h += `<div class="small mut" style="margin:6px 0">No readings yet. Pick a sensor in settings or log one by hand.</div>`;
    h += phChart(ph, g.adjunct_log);
    h += `<div class="row" style="margin-top:8px">${this._btn("form-ph", "plus", "Log reading", `data-g="${gid}"`)}</div>`;
    const recent = ph.history.slice().reverse().slice(0, 5);
    for (const r of recent) h += this._logRow("ph", gid, r.id, `pH ${num(r.value, 2)}`, `${fmtDate(r.date)}, ${r.source}`);
    h += `</div>${this._soilCards(g)}${g.show_water ? this._waterCard(g) : ""}${this._coverCard(g)}<div class="card"><div class="row"><div class="sec grow" style="margin:0">Soil adjuncts this season</div>${this._btn("form-adj", "plus", "Log something else", `data-g="${gid}" data-s="__new__"`)}${this._btn("form-atype", "calendar-plus", "Schedule", `data-g="${gid}"`)}</div>`;
    for (const a of g.adjuncts) {
      const per = a.per_year || 0;
      const pips = per && !a.as_needed ? `<div class="pips" style="--c:var(--${a.level === "ok" ? "ok" : "spray"})">${Array.from({ length: per }, (_, i) => `<i class="${i < a.count ? "f" : ""}"></i>`).join("")}</div>` : "";
      const sub = a.last ? `Last ${fmtDate(a.last.date)}${a.last.amount ? ", " + esc(a.last.amount) : ""}` : "Not applied yet";
      h += `<div class="adj ${a.level}"><div class="dot">${this._icon("flask-outline")}</div><div class="grow"><b style="font-weight:500;font-size:14px">${esc(a.name)}</b><div class="small mut">${sub}</div>${pips}</div><div style="text-align:right"><span class="pill ${a.level}" style="margin:0">${esc(a.label)}</span><div style="margin-top:4px"><button data-act="form-adj" data-g="${gid}" data-s="${a.key}">Log</button></div></div></div>`;
    }
    const log = g.adjunct_log;
    h += `<button style="width:100%;margin-top:8px" data-act="toggle-log">${this._icon(this._showLog ? "chevron-up" : "chevron-down")} Application log (${log.length})</button>`;
    if (this._showLog) for (const e of log) h += this._logRow("adjunct", gid, e.id, esc(e.type_name) + (e.product ? `, ${esc(e.product)}` : ""), fmtDate(e.date) + (e.amount ? ` · ${esc(e.amount)}` : ""));
    h += `</div>`;
    h += this._sensorAlarmCard(g);
    const all = this._vars().filter((v) => v.garden === gid), mine = this._sortVars(all.filter((v) => this._matches(v, "g" + gid)), this._sort);
    h += `<div class="card"><div class="sec">Plants in this garden</div>${all.length > 3 ? this._searchBox("g" + gid, "Search plants here") : ""}${all.length && !mine.length ? `<div class="small mut" style="margin:6px 0">No plants match your search.</div>` : ""}${mine.map((v) => `<div class="lg" style="cursor:pointer" data-act="open-v" data-v="${v.id}"><div class="t">${esc(v.name)}<span>${esc(v.species_name)}${v.kind === "tree" ? "" : `, ${v.alive} of ${v.count} plants`}</span></div>${this._icon("chevron-right")}</div>`).join("") || `<div class="small mut">None yet.</div>`}<div class="row" style="margin-top:8px">${this._btn("form-variety", "plus", "Add plant", `data-g="${gid}"`)}${mine.some((v) => !v.archived && v.kind !== "tree") ? this._btn("form-endseason", "archive", "End season", `data-g="${gid}"`, "danger") : ""}</div></div>`;
    if (mine.length) h += `<div class="small mut" style="margin:8px 4px">To remove this place, archive its plants first. Its history is kept.</div>`;
    if (!mine.length) h += `<div class="card">${this._confirm === "rmg" ? `<div class="conf">Remove ${esc(g.name)}? It leaves your list. Its history is kept under Past plants and you can bring it back.<div class="row"><button data-act="cancel-del">Keep</button><button class="danger" data-act="do-rmg" data-g="${gid}">Remove garden</button></div></div>` : `<button class="danger" data-act="ask-rmg">Remove garden</button>`}</div>`;
    return h;
  }

  _coverCard(g) {
    if (!this._show.cover) return "";
    const c = g.cover, gid = g.id;
    let h = `<div class="card"><div class="row"><div class="sec grow" style="margin:0">${this._icon("grass")} Winter cover crop</div>${this._btn("form-cover", "plus", "Add cover crop", `data-g="${gid}"`)}</div>`;
    if (c.blocked) {
      const b = c.blocked;
      h += b.reason === "growing"
        ? `<div class="pill warn" style="margin:8px 0">Cover crop growing. Terminate it, then wait ${(c.items.find((i) => i.state === "growing") || {}).wait_days || 21} days before planting.</div>`
        : `<div class="pill warn" style="margin:8px 0">Wait ${b.days_left} more day${b.days_left === 1 ? "" : "s"} before planting. Ready ${fmtDate(b.date, true)}.</div>`;
    } else if (c.items.length) h += `<div class="pill ok" style="margin:8px 0">Waiting period is over. Garden plants can go in.</div>`;
    if (c.mix) h += `<div class="small" style="margin:6px 0">Seed mix, ${num(c.mix.total_lbs, 2)} lb: ${this._mixText(g)}</div>`;
    if (!c.items.length) h += `<div class="small mut" style="margin:6px 0">Nothing sown yet. Add rye, vetch, clover, winter wheat or peas to track days in the ground and the wait after you terminate it.</div>`;
    for (const i of c.items) {
      const pct = i.state === "growing" ? 0 : Math.min(100, Math.round(((i.wait_days - i.days_left) / Math.max(1, i.wait_days)) * 100));
      h += `<div class="plant"><div class="row"><div class="grow"><b style="font-weight:500">${esc(i.crop)}</b><div class="small mut">${i.amount_lbs ? `${num(i.amount_lbs, 2)} lb seed${i.mix_pct !== undefined ? ` (${i.mix_pct}% of the mix)` : ""}. ` : ""}Sown ${fmtDate(i.sown)}, ${i.days_in_ground} day${i.days_in_ground === 1 ? "" : "s"} in the ground${i.terminated ? `, terminated ${fmtDate(i.terminated)}${i.methods && i.methods.length ? " (" + esc(i.methods.map((m) => COVER_TEXT[m] || m).join(", then ")) + ")" : ""}` : ""}</div></div><span class="pill ${i.state === "growing" ? "ok" : i.state === "waiting" ? "warn" : "none"}" style="margin:0">${i.state === "growing" ? "Growing" : i.state === "waiting" ? `${i.days_left} d to plant` : "Ready"}</span></div>`;
      if (i.terminated) h += `<div class="bar" title="Waiting period"><i style="width:${pct}%"></i></div><div class="small mut">${i.state === "waiting" ? `Day ${i.days_since_term} of ${i.wait_days} waiting` : `${i.wait_days} day wait finished`}</div>`;
      h += `<div class="row" style="margin-top:6px">${i.terminated ? `<button data-act="reopen-cover" data-g="${gid}" data-e="${i.id}">Undo terminate</button>` : this._btn("form-terminate", "scissors-cutting", "Terminate", `data-g="${gid}" data-e="${i.id}"`, "primary")}<span class="grow"></span>${this._acts("cover", gid, i.id)}</div>`;
      if (this._confirm === `cover:${i.id}`) h += `<div class="conf">Remove this cover crop record?<div class="row"><button data-act="cancel-del">Keep</button><button class="danger" data-act="do-del" data-k="cover" data-p="${gid}" data-e="${i.id}">Remove</button></div></div>`;
      h += `</div>`;
    }
    return h + `</div>`;
  }
  _fertCard(g) {
    const gid = g.id, f = g.fertility, mo = g.metrics.moisture, ec = g.metrics.ec;
    const cls = { ok: "ok", feed: "warn", hold: "warn", recheck: "" }[f.action] ?? "";
    const label = { ok: "No feeding needed", feed: "Consider feeding", hold: "Hold off feeding", recheck: "Check again later" }[f.action];
    const src = (m) => (m.entities.length ? `${m.entities.length} sensor${m.entities.length === 1 ? "" : "s"}` : "manual");
    let h = `<div class="card"><div class="row"><div class="sec grow" style="margin:0">${this._icon("flower")} Moisture and fertility</div><span class="small mut">Top ${f.depth} in</span></div>`;
    if (g.paused.ec || g.paused.moisture) h += `<div class="pill" style="margin:8px 0">Sensors out of the ground. New readings are ignored. Showing the last ones.</div>`;
    if (f.off_season) h += `<div class="small mut" style="margin:8px 0">No feeding advice from the first fall frost (${fmtMd(f.season.from)}) until after the last spring frost (${fmtMd(f.season.until)}).</div>`;
    h += f.paused ? "" : f.action ? `<div class="pill ${cls}" style="margin:8px 0">${label}</div><div class="small" style="margin-bottom:8px">${esc(f.advice)}</div>` : ec.current !== null ? "" : `<div class="small mut" style="margin:6px 0">No EC readings yet. Pick sensors or log one by hand.</div>`;
    h += `<div class="row" style="align-items:baseline;gap:22px;margin:6px 0"><div><span class="ph">${ec.current === null ? "-" : num(ec.current, 2)}</span> <span class="small mut">mS/cm EC</span></div><div><span class="ph">${mo.current === null ? "-" : num(mo.current, 0) + "%"}</span> <span class="small mut">moisture</span></div></div>`;
    h += `<div class="small mut" style="margin-bottom:6px">Healthy EC ${f.ec_target[0]} to ${f.ec_target[1]}. EC is trusted when moisture is ${f.moisture_band[0]} to ${f.moisture_band[1]}%${f.moisture_state ? `, now ${f.moisture_state === "ok" ? "in that range" : f.moisture_state}` : ""}.${f.ec_change !== null && f.ec_change !== 0 ? ` EC ${f.ec_change < 0 ? "down" : "up"} ${Math.abs(f.ec_change).toFixed(2)} in two weeks.` : ""}${f.last_fed ? ` Last fed ${fmtDate(f.last_fed)}.` : ""}</div>`;
    h += dualChart(ec, mo, f.ec_target);
    h += `<div class="row" style="margin-top:8px;flex-wrap:wrap">${this._btn("form-metric", "plus", "Log EC", `data-g="${gid}" data-s="ec"`)}${this._btn("form-metric", "plus", "Log moisture", `data-g="${gid}" data-s="moisture"`)}${this._btn("form-sensors", "access-point", "EC sensors", `data-g="${gid}" data-s="ec"`)}${this._btn("form-sensors", "access-point", "Moisture sensors", `data-g="${gid}" data-s="moisture"`)}${this._btn("toggle-probes", g.paused.ec ? "play" : "pause", g.paused.ec ? "Resume sensors" : "Sensors out", `data-g="${gid}" data-grp="moisture_ec" data-p="${g.paused.ec ? "0" : "1"}"`)}</div>`;
    h += `<div class="small mut" style="margin-top:4px">EC: ${src(ec)}. Moisture: ${src(mo)}.</div>`;
    for (const m of [ec, mo]) for (const r of m.history.slice().reverse().filter((x) => x.source === "manual").slice(0, 2)) h += this._logRow(m.key, gid, r.id, `${esc(m.name)} ${num(r.value, METRIC_DEC[m.key])}${m.unit === "%" ? "%" : " " + m.unit}`, `${fmtDate(r.date)}, manual`);
    return h + `</div>`;
  }
  _soilCards(g) {
    const gid = g.id;
    let h = g.fertility ? this._fertCard(g) : "";
    for (const m of Object.values(g.metrics)) {
      if (m.key === "moisture" || m.key === "ec") continue;
      if (m.key === "out_temp" && g.metrics.soil_temp) continue;  // drawn together with the soil temperature
      if (m.key === "soil_temp" && g.metrics.out_temp) { h += this._soilAirCard(g); continue; }
      const d = METRIC_DEC[m.key], u = m.unit === "%" ? "%" : ` ${m.unit}`;
      const src = m.entities.length ? `${m.entities.length} sensor${m.entities.length === 1 ? "" : "s"}, averaged` : m.fallback ? "Main outdoor sensor" : "Manual";
      h += `<div class="card"><div class="row"><div class="sec grow" style="margin:0">${this._icon(METRIC_ICON[m.key])} ${esc(m.name)}</div><span class="small mut">${src}</span></div>`;
      if (m.current !== null) {
        h += `<div class="row" style="align-items:baseline;margin:6px 0"><span class="ph">${num(m.current, d)}${m.unit === "%" ? "%" : ""}</span><span class="small mut">${m.unit === "%" ? "" : esc(m.unit) + " "}${m.min !== null && m.min !== undefined ? `today ${num(m.min, d)} to ${num(m.max, d)}${m.unit === "%" ? "%" : ""}` : ""}</span></div>`;
        h += `<div class="small mut" style="margin-bottom:8px">${m.source === "sensor" ? "Sensor" : "Manual reading"}, ${fmtDate(m.date)}</div>`;
      } else h += `<div class="small mut" style="margin:6px 0">No readings yet. Pick sensors or log one by hand.</div>`;
      h += metricChart(m);
      if (g.paused[m.key]) h += `<div class="pill" style="margin:8px 0">Sensors out. New readings are ignored. Showing the last ones.</div>`;
      if (m.key === "soil_temp" && g.planting) {
        h += `<div class="small mut" style="margin:8px 0 4px">Planting guide, using the average of the last ${g.planting.days} night low${g.planting.days === 1 ? "" : "s"} (${num(g.planting.basis, 0)}°F)</div><div>${g.planting.crops.map((c) => `<span class="pill ${c.ready ? "ok" : "none"}" style="margin:2px 4px 2px 0">${esc(c.name)} ${c.min_f}°${c.ready ? "" : ", not yet"}</span>`).join("")}</div>`;
      }
      h += `<div class="row" style="margin-top:8px">${this._btn("form-metric", "plus", "Log reading", `data-g="${gid}" data-s="${m.key}"`)}${this._btn("form-sensors", "access-point", "Sensors", `data-g="${gid}" data-s="${m.key}"`)}${this._btn("toggle-probes", g.paused[m.key] ? "play" : "pause", g.paused[m.key] ? "Resume sensors" : "Sensors out", `data-g="${gid}" data-grp="${m.key}" data-p="${g.paused[m.key] ? "0" : "1"}"`)}</div>`;
      for (const r of m.history.slice().reverse().filter((x) => x.source === "manual").slice(0, 3)) h += this._logRow(m.key, gid, r.id, `${esc(m.name)} ${num(r.value, d)}${u}`, `${fmtDate(r.date)}, manual`);
      h += `</div>`;
    }
    return h;
  }

  _soilAirCard(g) {
    const gid = g.id, soil = g.metrics.soil_temp, out = g.metrics.out_temp, SOIL = "var(--primary-color, #03a9f4)", AIR = "var(--spray, #ffa000)";
    const src = (m) => (m.source === "estimated" || m.source === "weather" ? "log a reading to override" : m.entities.length ? `${m.entities.length} sensor${m.entities.length === 1 ? "" : "s"}` : m.fallback ? "main outdoor sensor" : "manual");
    const col = (m, name, color) => `<div><span class="ph" style="color:${color}">${m.current === null ? "–" : num(m.current, 0) + "°"}</span> <span class="small mut">${name}${m.min !== null && m.min !== undefined ? `, today ${num(m.min, 0)} to ${num(m.max, 0)}` : ""}</span><div class="small mut">${m.current === null ? "No readings yet" : m.source === "estimated" ? `Estimated from local weather, ${fmtDate(m.date)}` : m.source === "weather" ? `Local weather, ${fmtDate(m.date)}` : `${m.source === "sensor" ? "Sensor" : "Manual"}, ${fmtDate(m.date)}`} (${src(m)})</div></div>`;
    let h = `<div class="card"><div class="sec">${this._icon("thermometer")} Soil and outside temperature</div>`;
    h += `<div class="row" style="align-items:flex-start;gap:22px;margin:6px 0">${col(soil, "soil", SOIL)}${col(out, "outside", AIR)}</div>`;
    const day = this._tempRange === "day", wk = Date.parse(this._snap.today) - 6 * 864e5;
    h += `<div class="row" style="gap:6px;margin:0 0 6px">${[["week", "Week"], ["day", "24 hours"]].map(([k, t]) => `<button class="chip ${(day ? "day" : "week") === k ? "on" : ""}" data-act="temp-range" data-s="${k}">${t}</button>`).join("")}</div>`;
    h += day
      ? dayChart([{ rows: soil.day || [], color: SOIL }, { rows: out.day || [], color: AIR }], "Soil and outside temperature")
      : tempChart([{ name: soil.name, hist: soil.history.filter((r) => Date.parse(r.date) >= wk), color: SOIL }, { name: out.name, hist: out.history.filter((r) => Date.parse(r.date) >= wk), color: AIR }], "Soil and outside temperature");
    h += `<div class="small" style="margin:2px 0 6px"><span style="color:${SOIL}">&#9632;</span> Soil &nbsp; <span style="color:${AIR}">&#9632;</span> Outside air</div>`;
    for (const m of [soil, out]) if (g.paused[m.key]) h += `<div class="pill" style="margin:4px 0">${esc(m.name)}: sensors out. New readings are ignored. Showing the last ones.</div>`;
    if (g.planting) h += `<div class="small mut" style="margin:8px 0 4px">Planting guide, using the average of the last ${g.planting.days} night low${g.planting.days === 1 ? "" : "s"} (${num(g.planting.basis, 0)}°F)</div><div>${g.planting.crops.map((c) => `<span class="pill ${c.ready ? "ok" : "none"}" style="margin:2px 4px 2px 0">${esc(c.name)} ${c.min_f}°${c.ready ? "" : ", not yet"}</span>`).join("")}</div>`;
    for (const [m, what] of [[soil, "soil"], [out, "outside"]]) {
      h += `<div class="row" style="margin-top:8px;flex-wrap:wrap"><span class="small mut" style="min-width:52px">${what[0].toUpperCase() + what.slice(1)}</span>${this._btn("form-metric", "plus", "Log reading", `data-g="${gid}" data-s="${m.key}"`)}${this._btn("form-sensors", "access-point", "Sensors", `data-g="${gid}" data-s="${m.key}"`)}${this._btn("toggle-probes", g.paused[m.key] ? "play" : "pause", g.paused[m.key] ? "Resume sensors" : "Sensors out", `data-g="${gid}" data-grp="${m.key}" data-p="${g.paused[m.key] ? "0" : "1"}"`)}</div>`;
      for (const r of m.history.slice().reverse().filter((x) => x.source === "manual").slice(0, 3)) h += this._logRow(m.key, gid, r.id, `${esc(m.name)} ${num(r.value, METRIC_DEC[m.key])} ${m.unit}`, `${fmtDate(r.date)}, manual`);
    }
    return h + `</div>`;
  }

  // ---- past plants -----------------------------------------------------------------------------
  _pastCard(v, withGarden) {
    return `<div class="card"><div class="row"><div class="grow" style="cursor:pointer" data-act="open-v" data-v="${v.id}"><div style="font-weight:500">${esc(v.name)}</div><div class="sub">${esc(v.species_name)}, ${v.count} plant${v.count === 1 ? "" : "s"}, ${num(v.total_lbs, 1)} lb, ${esc(ARCH_TEXT[v.archived.reason])}${withGarden ? `, ${esc(v.garden_name || "no garden")}, ${v.archived.year}` : ""}</div></div>${this._btn("form-again", "sprout", "Plant again", `data-v="${v.id}"`)}</div></div>`;
  }
  _archiveView() {
    const all = this._vars(true), vs = all.filter((v) => this._matches(v, "past"));
    const pg = (this._snap.past_gardens || []).filter((g) => !String(this._q.past || "").trim() || g.name.toLowerCase().includes(String(this._q.past).trim().toLowerCase()));
    let h = `<div class="hd">${this._btn("back", "arrow-left", "", "", "ic")}<div class="ttl grow">History</div></div>`;
    h += this._searchBox("past", "Search past plants and places");
    h += `<div class="chips"><span class="small mut" style="align-self:center">Sort</span>${[["year", "Year"], ["garden", "Garden"], ["name", "Name"]].map(([k, t]) => `<button class="chip ${this._psort === k ? "on" : ""}" data-act="psort" data-s="${k}">${t}</button>`).join("")}</div>`;
    const byName = (a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: "base" });
    if (this._psort === "garden") {
      const names = [...new Set(vs.map((v) => v.garden_name || "No garden"))].sort((a, b) => a.localeCompare(b));
      for (const n of names) h += `<div class="sec">${esc(n)}</div>` + vs.filter((v) => (v.garden_name || "No garden") === n).sort((a, b) => b.archived.year - a.archived.year || byName(a, b)).map((v) => this._pastCard(v, false)).join("");
    } else if (this._psort === "name") {
      h += [...vs].sort(byName).map((v) => this._pastCard(v, true)).join("");
    } else {
      const years = [...new Set(vs.map((v) => v.archived.year))].sort((a, b) => b - a);
      for (const y of years) h += `<div class="sec">${y}</div>` + vs.filter((x) => x.archived.year === y).map((v) => this._pastCard(v, false)).join("");
    }
    if (pg.length) {
      h += `<div class="sec">Removed places</div>`;
      for (const g of pg) h += `<div class="card"><div class="row"><div class="grow"><div style="font-weight:500">${esc(g.name)}</div><div class="sub">${esc(g.kind_name)}, removed ${fmtDate(g.removed)}, ${g.plants} plant${g.plants === 1 ? "" : "s"} in its history</div></div>${this._btn("restore-g", "restore", "Bring back", `data-g="${g.id}"`)}</div></div>`;
    }
    if (!vs.length && !pg.length) h += `<div class="msg">${all.length ? "Nothing matches your search." : "Nothing archived yet."}</div>`;
    return h;
  }

  // ---- events ------------------------------------------------------------------------------------
  _onClick(e) {
    const el = e.target.closest("[data-act]");
    if (!el) return;
    const a = el.dataset.act, d = el.dataset;
    if (a !== "brush-pick") this._bq = null;
    const home = () => { this._view = { v: "home" }; this._nav = []; this._confirm = null; };
    switch (a) {
      case "back": return this._back();
      case "open-v": return this._go({ v: "variety", id: d.v });
      case "open-g": return this._go({ v: "garden", id: d.g });
      case "open-archive": return this._go({ v: "archive" });
      case "open-micro": return this._go({ v: "micro" });
      case "open-layout": this._season = null; this._placeRow = "0"; this._placeStart = ""; this._brush = null; this._bq = null; this._selRow = null; this._brushLen = ""; return this._go({ v: "layout", id: d.g });
      case "open-water": return this._go({ v: "water", id: d.g });
      case "form-extra": {
        const f = this._form;
        return f.extra.act().then(() => { this._form = null; this._err = null; }, (e) => { f.err = e.message || String(e); }).then(() => this._render());
      }
      case "irr-method": return this._act("set_irrigation", { garden: d.g, method: d.m });
      case "form-soil": return this._open(this._fSoil(this._garden(d.g)));
      case "irr-set": return this._open(this._fIrr(this._garden(d.g)));
      case "irr-crop": return this._open(this._fIrrCrop(this._garden(d.g), d.c));
      case "irr-acid": return this._open(this._fAcid(this._garden(d.g)));
      case "irr-pump": return this._open(this._fPump(this._garden(d.g), d.k));
      case "irr-tanks": return this._open(this._fTanks(this._garden(d.g)));
      case "toggle-sec": this._exp = { ...(this._exp || {}), [d.s]: !(this._exp || {})[d.s] }; return this._render();
      case "season-days": return this._open(this._fDays(this._garden(d.g), d.c));
      case "irr-sprk": return this._open(this._fSprk(this._garden(d.g)));
      case "irr-lime": return this._open(this._fLime(this._garden(d.g)));
      case "irr-acid-log": return this._open(this._fAcidLog(this._garden(d.g), d.q === "1"));
      case "irr-sched": return this._open(this._fSched(this._garden(d.g)));
      case "irr-mix": return this._open(this._fMix(this._garden(d.g), d.k));
      case "irr-mix-sel": return this._act("set_fertigation", { garden: d.g, active: d.k });
      case "irr-comp": return this._open(this._fComp(this._garden(d.g), d.k, d.i === undefined ? undefined : Number(d.i)));
      case "irr-auto": return this._act("set_irrigation", { garden: d.g, run_min: null });
      case "lay-start": {
        const val = (k) => Number(this.shadowRoot.querySelector(`[data-lay="${k}"]`).value);
        return this._act("set_layout", { garden: d.g, width_ft: val("width_ft"), length_ft: val("length_ft") });
      }
      case "lay-rowin": return this._act("set_layout", { garden: d.g, row_in: Number(d.n) });
      case "lay-row": {
        const L = this._garden(d.g).layout, i = Number(d.r), row = L.rows[i], brush = this._brushFor(L), len = Number(this._brushLen) || 0;
        this._selRow = i;
        const vr = L.draft && L.draft.crop === brush ? L.draft.variety || undefined : undefined;
        if (len > 0) return this._act("add_layout_segment", { garden: d.g, row: i, crop: brush, length_ft: len, variety: vr });
        return this._act("assign_layout_rows", { garden: d.g, crop: row.crop === brush ? null : brush, rows: [i], variety: vr });
      }
      case "lay-traits": {
        const L = this._garden(d.g).layout, crop = this._brushFor(L);
        return this._open(this._fTraits(this._garden(d.g), crop, (L.draft && L.draft.crop === crop && L.draft.variety) || ""));
      }
      case "lay-mode": return this._act("set_layout_draft", { garden: d.g, crop: this._brushFor(this._garden(d.g).layout), mode: d.m });
      case "lay-place": return this._act("place_layout_draft", { garden: d.g, row: Number(this._placeRow || 0), start_ft: this._placeStart === "" || this._placeStart === undefined ? undefined : Number(this._placeStart) }, () => { this._selRow = Number(this._placeRow || 0); });
      case "lay-season": this._season = d.y || null; this._selRow = null; return this._render();
      case "ask-season": this._confirm = "season"; return this._render();
      case "do-season": return this._act("start_layout_season", { garden: d.g }, () => { this._season = null; this._selRow = null; this._confirm = null; });
      case "lay-seg-rm": return this._act("remove_layout_segment", { garden: d.g, row: Number(d.r), index: Number(d.i) });
      case "lay-row-clear": return this._act("assign_layout_rows", { garden: d.g, crop: null, rows: [Number(d.r)] });
      case "acc": { this._acc = { ...(this._acc || {}), [d.k]: !(((this._acc || {})[d.k]) ?? d.k === "crop") }; return this._render(); }
      case "lay-view": { const v = this._turnOf(d.g) === 90 ? 0 : 90; this._turns[d.g] = v; try { localStorage.setItem("gt_turn_" + d.g, String(v)); } catch (e) { /* no storage */ } return this._render(); }
      case "lay-ang": return this._act("set_layout", { garden: d.g, rotation: Number(d.n) });
      case "lay-fill": return this._act("assign_layout_rows", { garden: d.g, crop: this._brushFor(this._garden(d.g).layout) });
      case "lay-clear": return this._act("assign_layout_rows", { garden: d.g, crop: null });
      case "lay-edit": return this._open(this._fLayCrop(this._garden(d.g), d.c));
      case "ask-lay": this._confirm = "lay"; return this._render();
      case "do-lay": return this._act("remove_layout", { garden: d.g }, () => this._back());
      case "form-micro": return this._open(this._fMicro());
      case "web-location": return this.dispatchEvent(new CustomEvent("garden-location", { bubbles: true, composed: true }));
      case "filter": this._filter = d.s; return this._render();
      case "tab": this._tab = d.s; this._filter = "all"; this._setPref("tab", d.s); return this._render();
      case "sort": this._sort = d.s; this._setPref("sort", d.s); return this._render();
      case "psort": this._psort = d.s; this._setPref("psort", d.s); return this._render();
      case "lay-plant": return this._open(this._fPlantLayout(this._garden(d.g)));
      case "brush-pick": this._brush = d.k; this._bq = null; return this._act("set_layout_draft", { garden: d.g, crop: d.k });
      case "find-pick": { const f = this._form; f.values[d.f] = d.val; if (f.search) delete f.search[d.f]; return this._render(); }
      case "form-view": return this._open(this._fView());
      case "air-range": this._airRange = d.s; return this._render();
      case "temp-range": this._tempRange = d.s; return this._render();
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
      case "restore-g": return this._act("restore_garden", { garden: d.g });
      case "do-rmg": return this._act("remove_garden", { garden: d.g }, home);
      case "restore": return this._act("restore_plant", { plant: d.v }, () => this._back());
      case "plant-alive": return this._act("set_plant_status", { plant: d.v, individual: d.p, status: "alive" });
      case "form-variety": return this._open(this._fVariety(d.g));
      case "form-garden": return this._open(this._fGarden());
      case "edit-g": return this._open(this._fGarden(this._garden(d.g)));
      case "edit-v": return this._open(this._fEditVariety(this._variety(d.v)));
      case "form-harvest": return this._open(this._fHarvest(this._variety(d.v)));
      case "form-prune": return this._open(this._fPrune(this._variety(d.v)));
      case "form-prune-month": return this._open(this._fPruneMonth(this._variety(d.v)));
      case "prune-skip": return this._call("log_pruning", { plant: d.v, outcome: "skipped" });
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
      case "form-endseason": return this._open(this._fEndSeason(this._garden(d.g)));
      case "form-cover": return this._open(this._fCover(this._garden(d.g)));
      case "form-terminate": return this._open(this._fTerminate(this._garden(d.g), d.e));
      case "toggle-probes": return this._act("set_soil_sensors_paused", { garden: d.g, group: d.grp, paused: d.p === "1" });
      case "reopen-cover": return this._act("reopen_cover_crop", { garden: d.g, cover: d.e });
      case "form-metric": return this._open(this._fMetric(this._garden(d.g), d.s));
      case "form-sensors": return this._open(this._fSensors(this._garden(d.g), d.s));
      case "trays-set": return this._act("set_trays", { garden: d.g, trays: Number(d.n) });
      case "log-water": return this._act("log_watering", { garden: d.g });
      case "trays": return this._act("set_trays", { garden: d.g, trays: Math.max(0, this._garden(d.g).trays + Number(d.d)) });
      case "form-move": return this._open(this._fMove(this._variety(d.v)));
      case "form-upot": return this._open(this._fUpPot(this._variety(d.v)));
      case "form-climate": return this._open(this._fClimate(this._garden(d.g)));
      case "toggle-climate": return this._act("set_greenhouse_climate", { garden: d.g, enabled: d.p === "1" });
      case "ack-sensor": return this._act("ack_sensor_alarm", { garden: d.g, entity: d.e });
      case "toggle-sensor-alarm": return this._act("set_sensor_alarm", { garden: d.g, enabled: d.p === "1" });
      case "ack-alarm": return this._act("ack_temp_alarm", { garden: d.g, kind: d.k });
      case "toggle-alarm": {
        const al = this._garden(d.g).alarm;
        if (d.p === "1" && al.high === null && al.low === null) return this._open(this._fAlarm(this._garden(d.g), true));
        return this._act("set_temp_alarm", { garden: d.g, enabled: d.p === "1" });
      }
      case "form-alarm": return this._open(this._fAlarm(this._garden(d.g)));
      case "form-rate": return this._open(this._fRate(this._garden(d.g)));
      case "form-water-every": return this._open(this._fWaterEvery(this._garden(d.g)));
      case "toggle": {
        const cur = (this._form.values[d.f] || "").split(",").filter(Boolean);
        const i = cur.indexOf(d.val);
        if (i >= 0) cur.splice(i, 1); else cur.push(d.val);
        this._form.values[d.f] = cur.join(",");
        return this._render();
      }
      case "form-atype": return this._open(this._fAType(this._garden(d.g)));
      case "edit-entry": return this._open(this._fEntry(d.k, d.p, d.e));
      case "pick": this._form.values[d.f] = d.val; return this._render();
      case "use-days": this._form.values.days_to_harvest = d.n; return this._render();
      case "form-cancel": this._form = null; return this._render();
      case "form-submit": return this._submit();
    }
  }
  _onInput(e, isChange) {
    const el = e.target;
    if (el.dataset && el.dataset.lq !== undefined && !isChange) { this._bq = el.value; this._focusL = true; return this._render(); }
    if (el.dataset && el.dataset.fs !== undefined && this._form) {
      if (isChange) return;
      this._form.search = this._form.search || {};
      this._form.search[el.dataset.fs] = el.value;
      this._focusF = el.dataset.fs;
      return this._render();
    }
    if (el.dataset && el.dataset.q !== undefined && !isChange) { this._q[el.dataset.q] = el.value; this._focusQ = el.dataset.q; return this._render(); }
    if (el.dataset && el.dataset.lay && isChange && el.tagName === "INPUT") {
      const L = this._garden(el.dataset.g).layout;
      if (L && L.configured) this._act("set_layout", { garden: el.dataset.g, [el.dataset.lay]: Number(el.value) });
      return;
    }
    if (el.dataset && el.dataset.brushlen !== undefined && isChange) { this._brushLen = el.value; return this._render(); }
    if (el.dataset && el.dataset.draft && isChange) {
      const L = this._garden(el.dataset.g).layout, d = L.draft || {};
      return this._act("set_layout_draft", { garden: el.dataset.g, crop: this._brushFor(L), mode: d.mode || "weight", [el.dataset.draft]: Number(el.value) });
    }
    if (el.dataset && el.dataset.dvar !== undefined && isChange) {
      const L = this._garden(el.dataset.g).layout, d = L.draft || {};
      return this._act("set_layout_draft", { garden: el.dataset.g, crop: this._brushFor(L), mode: d.mode || "weight", variety: el.value.trim() });
    }
    if (el.dataset && el.dataset.placerow !== undefined && isChange) { this._placeRow = el.value; return; }
    if (el.dataset && el.dataset.placestart !== undefined && isChange) { this._placeStart = el.value; return; }
    if (el.dataset && el.dataset.brush !== undefined && isChange) { this._brush = el.value; return this._act("set_layout_draft", { garden: el.dataset.g, crop: el.value }); }
    if (el.dataset && el.dataset.fd && this._form && isChange) {
      const [nm, part] = el.dataset.fd.split(":"), f = this._form;
      f.dp = f.dp || {};
      const cur = f.dp[nm] || this._dateParts(f.values[nm]);
      cur[part] = el.value;
      f.dp[nm] = cur;
      const full = cur.y && cur.m && cur.d;
      if (full) cur.d = String(Math.min(Number(cur.d), new Date(Number(cur.y), Number(cur.m), 0).getDate()));
      f.values[nm] = full ? `${cur.y}-${String(cur.m).padStart(2, "0")}-${String(cur.d).padStart(2, "0")}` : "";
      return this._render();
    }
    const name = el.dataset && el.dataset.f;
    if (!name || !this._form || el.tagName === "BUTTON") return;
    const isSelect = el.tagName === "SELECT";
    if (isSelect !== isChange) return;
    this._form.values[name] = el.value;
    if (isSelect) this._render();
    else this._updatePreview();
  }
  _dateParts(iso) {
    const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso || "");
    return m ? { y: m[1], m: String(Number(m[2])), d: String(Number(m[3])) } : { y: "", m: "", d: "" };
  }
  _dateField(x, val) {
    const f = this._form, c = (f.dp && f.dp[x.name]) || this._dateParts(val);
    const yr = new Date().getFullYear(), years = [];
    for (let y = yr - 2; y <= yr + 8; y++) years.push(y);
    if (c.y && !years.includes(Number(c.y))) years.push(Number(c.y));
    years.sort((a, b) => a - b);
    const mons = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const days = c.y && c.m ? new Date(Number(c.y), Number(c.m), 0).getDate() : 31;
    const sel = (part, ph, opts, cur) => `<select data-fd="${x.name}:${part}" style="flex:1;min-width:0"><option value="">${ph}</option>${opts.map(([v, t]) => `<option value="${v}" ${String(cur) === String(v) ? "selected" : ""}>${t}</option>`).join("")}</select>`;
    return `<div class="row" style="gap:4px;flex-wrap:nowrap">${sel("m", "Month", mons.map((t, i) => [i + 1, t]), c.m)}${sel("d", "Day", Array.from({ length: days }, (_, i) => [i + 1, i + 1]), c.d)}${sel("y", "Year", years.map((y) => [y, y]), c.y)}</div>`;
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
      else if (x.type === "find") {
        const typed = f.search && f.search[x.name] !== undefined ? f.search[x.name] : null;
        const cur = x.options.find(([v]) => String(v) === String(val));
        const q = (typed || "").trim().toLowerCase();
        const hits = typed === null ? [] : x.options.filter(([v, t]) => v !== "other" && (!q || q.split(/\s+/).every((w) => t.toLowerCase().includes(w))));
        const shown = hits.slice(0, q ? 10 : 14), more = hits.length - shown.length;
        const last = x.options.find(([v]) => v === "other");
        ctl = `<input data-fs="${x.name}" type="search" autocomplete="off" placeholder="${esc(x.placeholder || "Search")}" value="${esc(typed !== null ? typed : cur ? cur[1] : "")}">`;
        if (typed !== null) ctl += `<div class="seg" style="flex-wrap:wrap;margin-top:6px">${shown.map(([v, t]) => `<button data-act="find-pick" data-f="${x.name}" data-val="${esc(v)}" class="${String(val) === String(v) ? "on" : ""}">${esc(t)}</button>`).join("")}${last ? `<button data-act="find-pick" data-f="${x.name}" data-val="other">${esc(last[1])}</button>` : ""}</div>${more > 0 ? `<div class="small mut" style="margin-top:4px">${more} more. Keep typing to narrow it down.</div>` : ""}${!hits.length ? `<div class="small mut" style="margin-top:4px">Nothing matches. Pick Other to add your own.</div>` : ""}`;
      }
      else if (x.type === "multi") { const on = new Set(String(val).split(",").filter(Boolean)); ctl = `<div class="seg" style="flex-wrap:wrap">${x.options.map(([v, t]) => `<button data-act="toggle" data-f="${x.name}" data-val="${esc(v)}" class="${on.has(v) ? "on" : ""}">${esc(t)}</button>`).join("") || `<span class="small mut">No matching sensors found. Type entity ids below.</span>`}</div>`; }
      else if (x.type === "seg" || x.type === "chips") ctl = `<div class="seg">${x.options.map(([v, t]) => `<button data-act="pick" data-f="${x.name}" data-val="${esc(v)}" class="${val === v ? "on" : ""}">${esc(t)}</button>`).join("")}</div>`;
      else if (x.type === "date") ctl = this._dateField(x, val);
      else if (x.type === "textarea") ctl = `<textarea data-f="${x.name}" rows="3">${esc(val)}</textarea>`;
      else ctl = `<input data-f="${x.name}" type="${x.type || "text"}" value="${esc(val)}" ${x.step ? `step="${x.step}"` : ""} ${x.placeholder ? `placeholder="${esc(x.placeholder)}"` : ""} ${x.type === "number" ? 'inputmode="decimal"' : ""}>`;
      h += `<div style="grid-column:span ${x.type === "date" ? 6 : x.span || 6}"><label>${esc(label)}${x.req ? " *" : ""}</label>${ctl}</div>`;
    }
    h += `</div>${f.note ? `<p class="small mut">${f.note}</p>` : ""}<div id="pv">${f.preview ? f.preview(vals) : ""}</div>`;
    h += `<div class="row" style="margin-top:12px"><button class="grow" data-act="form-cancel">Cancel</button><button class="grow primary" data-act="form-submit">${esc(f.submitLabel || "Save")}</button></div>${f.extra ? `<div class="row" style="margin-top:8px"><button class="grow" data-act="form-extra">${esc(f.extra.label)}</button></div>` : ""}</div>`;
    return h;
  }

  // ---- form definitions -----------------------------------------------------------------------------------
  _isoAdd(iso, n) {
    const d = new Date(iso + "T00:00:00"); d.setDate(d.getDate() + n);
    const p = (x) => String(x).padStart(2, "0");
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
  }
  _brushFind(L, gid, brush) {
    const cur = L.available.find((a) => a.key === brush), typed = this._bq === undefined ? null : this._bq;
    const q = (typed || "").trim().toLowerCase();
    const hits = typed === null ? [] : L.available.filter((a) => !q || q.split(/\s+/).every((w) => a.name.toLowerCase().includes(w)));
    const shown = hits.slice(0, q ? 10 : 14), more = hits.length - shown.length;
    let h = `<input data-lq data-g="${gid}" type="search" autocomplete="off" placeholder="Search crops" value="${esc(typed !== null ? typed : cur ? cur.name : "")}">`;
    if (typed !== null) h += `<div class="seg" style="flex-wrap:wrap;margin-top:6px">${shown.map((a) => `<button data-act="brush-pick" data-g="${gid}" data-k="${esc(a.key)}" class="${a.key === brush ? "on" : ""}">${esc(a.name)}</button>`).join("")}</div>${more > 0 ? `<div class="small mut" style="margin-top:4px">${more} more. Keep typing to narrow it down.</div>` : ""}${!hits.length ? `<div class="small mut" style="margin-top:4px">No crop matches.</div>` : ""}`;
    return h;
  }
  _fPlantLayout(g) {
    const L = g.layout, n = L.to_plant.reduce((a, x) => a + x.plants, 0);
    return {
      title: `Plant ${g.name}'s layout`, submitLabel: "Plant and track",
      fields: [
        { name: "date", label: "Planting date", type: "date", value: this._snap.today, span: 3 },
        { name: "origin", label: "Started from", type: "seg", options: [["start", "Starts"], ["seed", "Seed"]], value: "start", span: 3 },
      ],
      note: `Adds ${L.to_plant.length} planting${L.to_plant.length === 1 ? "" : "s"} (${n} plants): ${L.to_plant.map((x) => `${x.variety || x.name} ${x.plants}`).join(", ")}. Days to harvest come from each crop's usual time; change them on the plant afterward.`,
      submit: (x) => this._call("plant_layout", { garden: g.id, date: x.date, origin: x.origin || "start" }),
    };
  }
  _fView() {
    const on = (k) => (this._show[k] ? "1" : "0"), seg = [["1", "Show"], ["0", "Hide"]];
    return {
      title: "What to show", submitLabel: "Save",
      fields: [
        { name: "sort", label: "Sort plants by", type: "seg", options: [["garden", "Garden"], ["name", "Name"], ["harvest", "Harvest"]], value: this._sort },
        { name: "compact", label: "Plant list", type: "seg", options: [["1", "Compact rows"], ["0", "Cards"]], value: this._compact ? "1" : "0" },
        { name: "water", label: "Watering", type: "seg", options: seg, value: on("water") },
        { name: "chores", label: "To do list", type: "seg", options: seg, value: on("chores") },
        { name: "cover", label: "Cover crops", type: "seg", options: seg, value: on("cover") },
        { name: "frost", label: "Frost dates", type: "seg", options: seg, value: on("frost") },
        { name: "micro", label: "Weather and microclimate", type: "seg", options: seg, value: on("micro") },
      ],
      note: "Saved on this device only. Hiding something only hides it from view; nothing is deleted.",
      submit: (x) => {
        for (const k of ["water", "chores", "cover", "frost", "micro"]) if (x[k] !== undefined) this._show[k] = x[k] === "1";
        if (x.compact !== undefined) { this._compact = x.compact === "1"; this._setPref("compact", this._compact); }
        if (x.sort) { this._sort = x.sort; this._setPref("sort", x.sort); }
        this._setPref("show", this._show);
      },
    };
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
        { name: "garden", label: "Where", type: "select", options: [...gs.map((g) => [g.id, g.kind === "garden" ? g.name : `${g.name} (${g.kind_name.toLowerCase()})`]), ["", "No garden (trees only)"]], value: gid || (gs[0] ? gs[0].id : ""), span: 6 },
        { name: "species", label: "Type", type: "find", placeholder: "Search plants", options: [...sp.map((s) => [s.key, s.name]), ["other", "Other..."]], value: this._snap.species.tomato ? "tomato" : sp[0] ? sp[0].key : "other", span: 6 },
        { name: "species_other", label: "Type name", type: "text", req: true, show: (v) => v.species === "other", span: 3 },
        { name: "kind", label: "Kind", type: "seg", options: [["plant", "Plant"], ["tree", "Tree"]], value: "plant", show: (v) => v.species === "other", span: 3 },
        { name: "single_harvest", label: "Pulled when harvested?", type: "seg", options: [["false", "No"], ["true", "Yes"]], value: "false", show: (v) => v.species === "other" && v.kind !== "tree", span: 3 },
        { name: "variety", label: "Variety", type: "text", req: true, placeholder: "Sungold" },
        ...this._containerFields("", (v) => { const x = this._snap.gardens.find((y) => y.id === v.garden); return !!x && x.kind !== "garden"; }, false),
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
        const cg = this._snap.gardens.find((x) => x.id === v.garden), cb = cg && cg.cover && cg.cover.blocked;
        if (cb && kind(v) !== "tree") h += `<div class="pill warn">${cb.reason === "growing" ? "A cover crop is still growing here." : `Cover crop wait: ${cb.days_left} more day${cb.days_left === 1 ? "" : "s"} (ready ${fmtDate(cb.date, true)}).`}</div>`;
        const spc = this._snap.species[v.species] || {}, rule = spc.harvest_rule;
        if (rule && !v.days_to_harvest && !v.expected_harvest_date && v.planted_date) {
          const gd = this._snap.gardens.find((x) => x.id === v.garden), md = gd ? gd.frost.first : "10-15";
          const when = this._isoAdd(`${Number(String(v.planted_date).slice(0, 4)) + (rule.year_offset || 1)}-${md}`, rule.after_first_frost_days || 21);
          h += `<div class="pill ok">Expected harvest ${fmtDate(when, true)}: ${Math.round((rule.after_first_frost_days || 21) / 7)} weeks after the first fall frost, ${rule.year_offset === 1 ? "second" : "later"} year</div>`;
        }
        const dth = Number(v.days_to_harvest) || (rule ? 0 : spc.default_days) || 0;
        if (kind(v) !== "tree" && dth && v.planted_date) h += `<div class="pill ok">Expected first harvest ${fmtDate(this._isoAdd(v.planted_date, dth), true)}${v.days_to_harvest ? "" : ` (${dth} days, the usual for this crop)`}</div>`;
        const past = this._snap.varieties.filter((x) => x.species === key(v) && v.variety && x.name.toLowerCase() === v.variety.toLowerCase());
        const s = past.map((x) => x.seasons).sort((a, b) => b.length - a.length)[0];
        const last = s && s.filter((z) => z.days_to_first !== null).pop();
        if (last && kind(v) !== "tree") h += `<div class="small" style="margin-top:8px">From your past seasons: ${esc(v.variety)} took ${last.days_to_first} days. <button data-act="use-days" data-n="${last.days_to_first}">Use ${last.days_to_first}</button></div>`;
        return h;
      },
      submit: (v) => this._call("add_variety", { garden: v.garden || "", species: v.species === "other" ? v.species_other : v.species, variety: v.variety, plants: v.plants, origin: v.origin, planted_date: v.planted_date, days_to_harvest: v.days_to_harvest, expected_harvest_date: v.expected_harvest_date, expected_yield: v.expected_yield, notes: v.notes, container: v.container === undefined ? undefined : this._containerOf(v), kind: v.species === "other" ? v.kind : undefined, single_harvest: v.species === "other" && v.kind !== "tree" ? v.single_harvest === "true" : undefined }),
    };
  }
  _fEditVariety(v) {
    return {
      title: `Edit ${v.name}`,
      fields: [
        { name: "name", label: "Variety name", type: "text", value: v.name, req: true },
        ...(v.custom_type ? [{ name: "species_name", label: "Type name (a type you added)", type: "text", value: v.species_name, req: true, span: 3 }, { name: "kind", label: "Kind", type: "seg", options: [["plant", "Plant"], ["tree", "Tree"]], value: v.kind, span: 3 }] : []),
        { name: "planted_date", label: "Planted or transplanted", type: "date", value: v.planted, span: 3 },
        { name: "in_ground_date", label: "In ground", type: "date", value: v.in_ground, span: 3 },
        ...(v.kind === "tree" ? [] : [{ name: "days_to_harvest", label: "Days to harvest", type: "number", step: "1", value: v.days_to_harvest, span: 3 }]),
        { name: "expected_harvest_date", label: "Expected harvest date", type: "date", value: v.expected_harvest, span: 3 },
        { name: "expected_yield", label: "Expected yield per plant (lb)", type: "number", step: "0.1", value: v.expected_yield, span: 3 },
        { name: "add_plants", label: "Add plants", type: "number", step: "1", span: 3 },
        ...(v.kind === "tree" ? [] : [{ name: "multi_year", label: "Countdown in years, months, days", type: "seg", options: [["false", "No"], ["true", "Yes"]], value: String(!!v.multi_year), span: 3 }]),
        ...(v.kind === "tree" ? [] : [{ name: "single_harvest", label: "Pulled when harvested?", type: "seg", options: [["false", "No"], ["true", "Yes"]], value: String(!!v.single_harvest), span: 3 }]),
        ...(v.location_kind !== "garden" ? this._containerFields(v.container || "", null, true) : []),
        { name: "notes", label: "Notes", type: "textarea", value: v.notes },
      ],
      submit: (x) => { const { container, container_other, ...rest } = x; return this._call("update_variety", { plant: v.id, ...rest, ...(container === undefined && container_other === undefined ? {} : { container: this._containerOf({ container, container_other }) || " " }) }); },
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
      title: `${v.single_harvest ? "Harvest" : "Log harvest"}: ${v.name}`, submitLabel: v.single_harvest ? "Harvest" : "Log harvest",
      fields: [
        { name: "lbs", label: "Pounds picked", type: "number", step: "0.1", req: true, span: 3 },
        { name: "date", label: "Date", type: "date", value: this._snap.today, span: 3 },
        ...(v.single_harvest ? [{ name: "plants", label: `Plants pulled (of ${v.alive})`, type: "number", step: "1", value: v.alive }] : []),
        { name: "notes", label: "Notes", type: "text" },
      ],
      preview: (x) => {
        const l = Number(x.lbs);
        if (!(l > 0)) return "";
        if (!v.alive) return `<div class="err">No living plants to receive this harvest</div>`;
        if (v.single_harvest) {
          const n = Number(x.plants) || v.alive;
          if (n > v.alive || n < 1) return `<div class="err">Pick between 1 and ${v.alive} plants</div>`;
          return `<div class="small mut">${num(l)} lb from ${n} plant${n === 1 ? "" : "s"}: ${num(l / n)} lb each. ${n === v.alive ? "That is the last of them, so the planting moves to Past plants." : `${v.alive - n} stay in the ground.`}</div>`;
        }
        return `<div class="small mut">${num(l)} lb split across ${v.alive} living plant${v.alive === 1 ? "" : "s"}: ${num(l / v.alive)} lb each</div>`;
      },
      submit: (x) => this._call("log_harvest", { plant: v.id, ...x }),
    };
  }
  _fPrune(v) {
    return {
      title: `Pruned: ${v.name}`, submitLabel: "Log pruning",
      fields: [{ name: "date", label: "Date", type: "date", value: this._snap.today }, { name: "notes", label: "Notes", type: "text" }],
      submit: (x) => this._call("log_pruning", { plant: v.id, outcome: "pruned", ...x }),
    };
  }
  _fPruneMonth(v) {
    const names = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
    return {
      title: `Pruning reminder: ${v.name}`, submitLabel: "Save",
      note: `The reminder starts on the first of this month each year and stays until you mark the tree pruned or not needing it. ${v.pruning.note}`,
      fields: [{ name: "month", label: "Start the reminder in", type: "select", options: names.map((n, i) => [String(i + 1), n]), value: String(v.pruning.month) }],
      submit: (x) => this._call("set_prune_month", { plant: v.id, month: Number(x.month) }),
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
        { name: "garden", label: "Garden", type: "select", options: [...gs.map((g) => [g.id, g.name]), ...(v.kind === "tree" ? [["", "No garden"]] : [])], value: gs.some((g) => g.id === v.garden) || (v.kind === "tree" && !v.garden) ? v.garden : (gs[0] ? gs[0].id : "") },
        { name: "plants", label: "Number of plants", type: "number", step: "1", value: v.count, span: 3 },
        { name: "planted_date", label: "Planting date", type: "date", value: this._snap.today, span: 3 },
      ],
      note: "Copies the variety and days to harvest. Past seasons feed the projection automatically.",
      submit: (x) => this._call("plant_again", { plant: v.id, ...x, garden: x.garden || "" }),
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
      title: `${p && p.trap ? "Trap catches" : "Biofix"}: ${p ? p.name : pest}`,
      fields: [{ name: "date", label: p && p.trap ? "Date catches rose sharply" : "Date of first sustained catch", type: "date", value: this._snap.today }],
      submit: (x) => this._call("set_biofix", { plant: v.id, pest, ...x }),
    };
  }
  _fGarden(g) {
    const isGarden = !g || g.kind === "garden", create = !g;
    const gOnly = create ? (v) => !v.kind || v.kind === "garden" : undefined;
    const kindName = g ? g.kind_name.toLowerCase() : "location";
    return {
      title: g ? `Edit ${g.name}` : "Add location",
      fields: [
        ...(create ? [{ name: "kind", label: "What is it?", type: "seg", options: [["garden", "Garden"], ["rack", "Seedling rack"], ["greenhouse", "Greenhouse"]], value: "garden" }] : []),
        { name: "name", label: "Name", type: "text", req: true, value: g && g.name },
        ...(isGarden ? [
          ...(this._web ? [] : [{ name: "ph_entity", label: "Soil pH sensor (optional)", type: "text", placeholder: "sensor.garden_soil_ph", value: g && g.ph.entity, show: gOnly }]),
          { name: "ph_min", label: "Target pH from", type: "number", step: "0.1", value: g ? g.ph.target[0] : 6.0, span: 3, show: gOnly },
          { name: "ph_max", label: "Target pH to", type: "number", step: "0.1", value: g ? g.ph.target[1] : 6.8, span: 3, show: gOnly },
        ] : []),
        ...(g && !isGarden && !this._web ? Object.entries(g.power_groups).map(([k, label]) => ({ name: `power_${k}`, label: `${label}: power or energy sensors (tap to include)`, type: "multi", options: this._energyCandidates((g.power_sensors || {})[k] || []), value: ((g.power_sensors || {})[k] || []).join(",") })) : []),
        ...(g && isGarden ? [
          { name: "ec_min", label: "Healthy soil EC from (mS/cm)", type: "number", step: "0.1", value: g.fertility.ec_target[0], span: 3 },
          { name: "ec_max", label: "Healthy soil EC to (mS/cm)", type: "number", step: "0.1", value: g.fertility.ec_target[1], span: 3 },
          { name: "moisture_min", label: "Trust EC above moisture (%)", type: "number", step: "1", value: g.fertility.moisture_band[0], span: 3 },
          { name: "moisture_max", label: "Trust EC below moisture (%)", type: "number", step: "1", value: g.fertility.moisture_band[1], span: 3 },
          { name: "probe_depth", label: "Probe depth (inches)", type: "number", step: "0.5", value: g.fertility.depth },
          { name: "frost_last", label: "Expected last spring frost", type: "date", value: g.frost.last_date, span: 3 },
          { name: "frost_first", label: "Expected first fall frost", type: "date", value: g.frost.first_date, span: 3 },
          { name: "show_water", label: "Watering log and moisture estimate", type: "seg", options: [["1", "Show"], ["0", "Hide"]], value: g.show_water ? "1" : "0" },
          { name: "frost_scope", label: "Apply frost dates to", type: "seg", options: [["garden", "This garden"], ["all", "All gardens"]], value: "garden" },
        ] : []),
      ],
      note: isGarden ? "Leave the sensor empty to log pH by hand. EC and moisture ranges set when feeding advice shows. Frost dates repeat every year, so set the average for your area." : `A ${kindName} tracks temperature${g && g.kind === "rack" ? ", light" : ""}, watering and 10x20 trays. Pick its temperature sensors from its page. Choosing power or energy sensors here adds a power use card with usage by day and month. Without them the card stays hidden.`,
      submit: async (x) => {
        const { frost_last, frost_first, frost_scope, show_water, ...rest } = x;
        if (!g) return this._call("add_garden", rest);
        if (!isGarden) {
          const pw = Object.fromEntries(Object.entries(rest).filter(([k]) => k.startsWith("power_")));
          const base = Object.fromEntries(Object.entries(rest).filter(([k]) => !k.startsWith("power_")));
          await this._call("update_garden", { garden: g.id, ...base });
          for (const k of Object.keys(g.power_groups)) {
            const now = String(pw[`power_${k}`] || "").split(",").filter(Boolean), was = (g.power_sensors || {})[k] || [];
            if (now.join(",") !== was.join(",")) await this._call("set_power_sensors", { garden: g.id, group: k, entities: now });
          }
          return;
        }
        await this._call("update_garden", { garden: g.id, ...rest, ph_entity: rest.ph_entity === undefined ? " " : rest.ph_entity });
        if (show_water !== undefined && (show_water === "1") !== g.show_water) await this._call("set_watering_card", { garden: g.id, shown: show_water === "1" });
        const changed = (frost_last && frost_last !== g.frost.last_date) || (frost_first && frost_first !== g.frost.first_date);
        if (frost_scope === "all" || changed) await this._call("set_frost_dates", { garden: g.id, last_frost: frost_last, first_frost: frost_first, all_gardens: frost_scope === "all" });
      },
    };
  }
  _containerFields(current, showFn, allowNone) {
    const list = this._snap.containers || [], known = list.includes(current);
    return [
      { name: "container", label: "Pot or tray", type: "select", options: [...(allowNone ? [["", "Not set"]] : []), ...list.map((c) => [c, c]), ["__other__", "Other..."]], value: known ? current : current ? "__other__" : allowNone ? "" : list[0], span: 3, show: showFn },
      { name: "container_other", label: "Pot or tray name", type: "text", req: true, value: !known && current ? current : "", span: 3, show: (v) => (!showFn || showFn(v)) && v.container === "__other__" },
    ];
  }
  _containerOf(x) { return x.container === "__other__" ? x.container_other : x.container; }
  _fUpPot(v) {
    const list = this._snap.containers || [], at = list.indexOf(v.container);
    const next = list[at + 1] || list[list.length - 1] || "";
    const fields = [
      ...this._containerFields(next, null, false).map((f) => (f.name === "container" ? { ...f, label: "Move up to", span: 6 } : f)),
      { name: "date", label: "Date", type: "date", value: this._snap.today },
    ];
    return {
      title: `Up-pot ${v.name}`, submitLabel: "Up-pot", fields,
      note: `${v.container ? `Now in: ${esc(v.container)}. ` : ""}Pot sizes are only tracked until the plants go in the ground.`,
      submit: (x) => this._call("up_pot", { plant: v.id, container: this._containerOf(x), date: x.date }),
    };
  }
  _fMove(v) {
    const order = this._snap.gardens.filter((g) => g.id !== v.garden).sort((a, b) => KIND_ORDER[a.kind] - KIND_ORDER[b.kind]);
    const here = KIND_ORDER[v.location_kind], next = order.find((g) => KIND_ORDER[g.kind] > here) || order[0];
    return {
      title: `Move ${v.name}`, submitLabel: "Move",
      fields: [
        { name: "to", label: "Move to", type: "select", options: [...order.map((g) => [g.id, `${g.name} (${g.kind_name.toLowerCase()})`]), ...(v.kind === "tree" && v.garden ? [["", "No garden"]] : [])], value: next ? next.id : (v.kind === "tree" ? "" : ""), req: false },
        { name: "count", label: `How many (of ${v.alive} living plants)`, type: "number", step: "1", value: v.alive, span: 3 },
        { name: "date", label: "Date", type: "date", value: this._snap.today, span: 3 },
      ],
      note: "Move some of them to split the batch. The rest stay where they are. Moving to a garden marks them as in the ground.",
      preview: (x) => {
        const dest = this._snap.gardens.find((g) => g.id === x.to);
        let h = "";
        const n = Number(x.count);
        if (n && n < v.alive) h += `<div class="pill info">${n} move, ${v.alive - n} stay in ${esc(v.garden_name)}</div>`;
        const cb = dest && dest.cover && dest.cover.blocked;
        if (cb && dest.kind === "garden") h += `<div class="pill warn">${cb.reason === "growing" ? "A cover crop is still growing there." : `Cover crop wait there: ${cb.days_left} more day${cb.days_left === 1 ? "" : "s"} (ready ${fmtDate(cb.date, true)}).`}</div>`;
        return h;
      },
      submit: (x) => this._call("move_plants", { plant: v.id, to: x.to || "", ...(x.count && x.count < v.alive ? { count: x.count } : {}), date: x.date }),
    };
  }
  _deviceCandidates(selected, lights = false) {
    const st = (this._hass && this._hass.states) || {};
    const out = [];
    const re = lights ? /^(switch|light|fan|input_boolean)\./ : /^(switch|fan|input_boolean|climate)\./;
    for (const [id, s2] of Object.entries(st)) {
      if (!re.test(id)) continue;
      const a = s2.attributes || {};
      if (a.heaters && (a.coolers || a.fans)) continue; // this integration's own thermostat
      out.push([id, a.friendly_name || id]);
    }
    for (const id of selected) if (!out.some((o) => o[0] === id)) out.push([id, id]);
    return out.sort((p, q) => p[1].localeCompare(q[1]));
  }
  _fClimate(g) {
    const c = g.climate, rack = g.kind === "rack", yn = [["true", "On"], ["false", "Off"]];
    const csv = (x) => String(x || "").split(",").filter(Boolean);
    const fields = [
      { name: "heat_set", label: rack ? "Heat mats on below (°F)" : "Heat when below (°F)", type: "number", step: "1", value: c.heat_set, req: true, span: 3 },
      { name: "heat_off", label: rack ? "Heat mats off at (°F)" : "Heat off at (°F)", type: "number", step: "0.5", value: c.heat_off === null ? "" : c.heat_off, placeholder: `${num(c.heat_set + 1, 1)} (1° above)`, span: 3 },
      { name: "cool_set", label: "Fans on above (°F)", type: "number", step: "1", value: c.cool_set, req: true, span: 3 },
      { name: "cool_off", label: "Fans off at (°F)", type: "number", step: "0.5", value: c.cool_off === null ? "" : c.cool_off, placeholder: `${num(c.cool_set - 1, 1)} (1° below)`, span: 3 },
      { name: "fan_min_run", label: "Fan minimum run (min)", type: "number", step: "1", value: c.fan_min_run, span: 3 },
      { name: "heaters", label: rack ? "Heat mats (tap to include)" : "Heaters (tap to include)", type: "multi", options: this._deviceCandidates(c.heaters), value: c.heaters.join(",") },
      { name: "coolers", label: "Fans (tap to include)", type: "multi", options: this._deviceCandidates(c.coolers), value: c.coolers.join(",") },
    ];
    if (!rack) fields.push(
      { name: "heat_min_run", label: "Heater minimum run (min)", type: "number", step: "1", value: c.heat_min_run, span: 2 },
      { name: "heat_max_run", label: "Heater maximum run (min)", type: "number", step: "1", value: c.heat_max_run, span: 2 },
      { name: "heat_rest", label: "Rest after maximum (min)", type: "number", step: "1", value: c.heat_rest, span: 2 });
    fields.push({ name: "enabled", label: "Thermostat (heat and too-warm fans)", type: "seg", options: yn, value: String(c.enabled) });
    if (rack) fields.push(
      { name: "lights", label: "Grow lights (tap to include)", type: "multi", options: this._deviceCandidates(c.lights, true), value: c.lights.join(",") },
      { name: "light_sched", label: "Light schedule", type: "seg", options: yn, value: String(c.light_sched) },
      { name: "light_on", label: "Lights come on at", type: "time", value: c.light_on, span: 3, show: (v) => v.light_sched === "true" },
      { name: "light_hours", label: "Hours on per day", type: "number", step: "0.5", value: c.light_hours, span: 3, show: (v) => v.light_sched === "true" });
    fields.push(
      { name: "fan_sched", label: "Fan schedule", type: "seg", options: yn, value: String(c.fan_sched) },
      { name: "fan_minutes", label: "Fans run (min)", type: "number", step: "1", value: c.fan_minutes, span: 3, show: (v) => v.fan_sched === "true" },
      { name: "fan_every", label: "Every (hours)", type: "number", step: "0.5", value: c.fan_every, span: 3, show: (v) => v.fan_sched === "true" });
    if (rack) fields.push({ name: "fan_lights_only", label: "Scheduled fans run", type: "seg", options: [["true", "Only with lights on"], ["false", "Any time"]], value: String(c.fan_lights_only), show: (v) => v.fan_sched === "true" && v.light_sched === "true" });
    return {
      title: `${rack ? "Heat mats, fans and lights" : "Heating and fans"}: ${g.name}`, submitLabel: "Save",
      fields,
      note: `The thermostat switches ${rack ? "heat mats" : "heaters"} on below the first temperature and fans on above the second, with ${num(c.gap, 0)} degrees minimum between them. Heat switches off at the "Heat off at" temperature, so 60 on and 65 off gives a five degree dead zone; leave it empty to switch off one degree above the on point. Fans switch off at the "Fans off at" temperature, so 90 on and 85 off gives a five degree dead zone; leave it empty to switch off one degree below the on point. Fan minimum run keeps the fans on for at least that long once they start for heat, so they don't cycle quickly. A device that is a climate device is set to heat, cool or off. It uses this ${g.kind_name.toLowerCase()}'s temperature sensors. If they stop reporting, the heaters switch off, so keep their own safety thermostat as a backup.${rack ? "" : " Minimum run keeps the heater on for at least that long once it starts. Maximum run turns it off after that long, then it rests before it can start again. Use 0 to turn either off. Below 36°F the maximum run never holds the heater off."}${rack ? " The light schedule switches the lights on at the time you choose for that many hours a day, for example 16 hours on and 8 off." : ""} The fan schedule runs the fans for a few minutes every so many hours${rack ? ", counted from the time the lights come on (or midnight with no light schedule)" : ", counted from midnight"}. Fans also run whenever it gets too warm, even between scheduled runs. Schedules work even if the thermostat is off.`,
      submit: (x) => this._call("set_greenhouse_climate", {
        garden: g.id, heat_set: x.heat_set, cool_set: x.cool_set, heat_off: x.heat_off === undefined ? null : x.heat_off, cool_off: x.cool_off === undefined ? null : x.cool_off, fan_min_run: x.fan_min_run ?? 0, enabled: x.enabled === "true", heaters: csv(x.heaters), coolers: csv(x.coolers),
        ...(rack ? { lights: csv(x.lights), light_sched: x.light_sched === "true", ...(x.light_sched === "true" ? { light_on: x.light_on, light_hours: x.light_hours } : {}), fan_lights_only: x.fan_lights_only !== "false" }
          : { heat_min_run: x.heat_min_run ?? 0, heat_max_run: x.heat_max_run ?? 0, heat_rest: x.heat_rest ?? 10 }),
        fan_sched: x.fan_sched === "true", ...(x.fan_sched === "true" ? { fan_minutes: x.fan_minutes, fan_every: x.fan_every } : {}),
      }),
    };
  }
  _energyCandidates(selected) {
    const st = (this._hass && this._hass.states) || {};
    const out = [];
    for (const [id, s2] of Object.entries(st)) {
      if (!id.startsWith("sensor.")) continue;
      const a = s2.attributes || {}, unit = String(a.unit_of_measurement || "").toLowerCase();
      if (["energy", "power"].includes(a.device_class) || ["kwh", "wh", "mwh", "w", "kw"].includes(unit) || selected.includes(id)) out.push([id, `${a.friendly_name || id}${s2.state && s2.state !== "unknown" ? ` (${s2.state}${a.unit_of_measurement ? " " + a.unit_of_measurement : ""})` : ""}`]);
    }
    return out.sort((p, q) => p[1].localeCompare(q[1]));
  }
  _fAlarm(g, turnOn) {
    const a = g.alarm, cold = g.kind === "greenhouse";
    return {
      title: `Temperature alarm: ${g.name}`, submitLabel: "Save",
      fields: [
        { name: "high", label: "Alarm when above (°F)", type: "number", step: "1", value: a.high === null ? (cold ? 90 : 85) : a.high, span: 3 },
        { name: "low", label: "Alarm when below (°F)", type: "number", step: "1", value: a.low === null ? (cold ? 38 : 55) : a.low, span: 3 },
        { name: "enabled", label: "Alarm", type: "seg", options: [["true", "On"], ["false", "Off"]], value: String(turnOn ? true : a.enabled) },
      ],
      note: "When the air goes past a limit the alarm shows here and on the main page, and stays until you tap Acknowledge, even if the temperature has come back. It says how long the air was out of range. Leave a limit empty to ignore that direction. Turning the alarm off clears it and it won't come back until you turn it on again. When the alarm is on, Home Assistant also gets a Temperature alarm sensor you can use for notifications.",
      submit: (x) => this._call("set_temp_alarm", { garden: g.id, high: x.high === "" || x.high === undefined ? null : x.high, low: x.low === "" || x.low === undefined ? null : x.low, enabled: x.enabled === "true" }),
    };
  }
  _fRate(g) {
    return {
      title: "Electricity rate", submitLabel: "Save",
      fields: [{ name: "cents", label: "Cents per kWh", type: "number", step: "0.01", value: g.power && g.power.rate ? g.power.rate : "", req: true }],
      note: "Used for the dollar figures on every power use card. Dollars are worked out from the rate you set now, so changing it also changes past days and months. Enter 0 to remove it.",
      submit: (x) => this._call("set_power_rate", { cents: x.cents }),
    };
  }
  _fWaterEvery(g) {
    return {
      title: `Watering reminder: ${g.name}`, submitLabel: "Save",
      fields: [{ name: "days", label: "Water every (days)", type: "number", step: "1", value: g.water.every || "" }],
      note: "Shows Water now once this many days have passed. Enter 0 to turn it off.",
      submit: (x) => this._call("set_water_interval", { garden: g.id, days: x.days === undefined ? 0 : x.days }),
    };
  }
  _fAdjunct(g, key) {
    return {
      title: `Log adjunct: ${g.name}`, submitLabel: "Log",
      fields: [
        { name: "adjunct", label: "Adjunct", type: "select", options: [...g.adjuncts.map((a) => [a.key, a.name]), ["__new__", "Something else..."]], value: key },
        { name: "custom", label: "What did you add?", type: "text", req: true, placeholder: "Lime, kelp meal, bone meal", show: (v) => v.adjunct === "__new__" },
        { name: "date", label: "Date", type: "date", value: this._snap.today, span: 3 },
        { name: "amount", label: "Amount", type: "text", placeholder: "2 lb per bed", span: 3 },
        { name: "product", label: "Product", type: "text" },
        { name: "notes", label: "Notes", type: "text" },
      ],
      note: "Pick Something else for anything your soil needs. It is added to the list so you can log it again next time.",
      submit: (x) => { const { custom, ...rest } = x; return this._call("log_adjunct", { garden: g.id, ...rest, adjunct: x.adjunct === "__new__" ? custom : x.adjunct }); },
    };
  }
  // ---- layout planner ------------------------------------------------------------------------------
  _brushFor(L) {
    const keys = L.available.map((a) => a.key);
    if (this._brush && keys.includes(this._brush)) return this._brush;
    return (L.crops[0] && L.crops[0].key) || (keys.includes("tomato") ? "tomato" : keys[0]);
  }
  _layDesc(L, c) {
    const sp = `${num(c.spacing_in, 1)} in`;
    return c.pattern === "grid" ? `offset grid, ${sp} between plants` : c.pattern === "double" ? `double line, ${sp} apart${c.stagger ? ", staggered" : ""}` : `single line, ${sp} apart`;
  }
  _tile2(act, g, icon, color, title, sub) {
    return `<div class="card tile t2" data-act="${act}" data-g="${g.id}"><div class="pic" style="background:color-mix(in srgb,var(--${color}) 18%,transparent);color:var(--${color})">${this._icon(icon)}</div><div style="font-size:15px;font-weight:600">${esc(title)}</div><div class="sub">${esc(sub)}</div></div>`;
  }
  _tiles(g) {
    const L = g.layout, W = g.irrigation, out = [];
    if (L) {
      const t = L.configured ? L.totals : null;
      out.push(this._tile2("open-layout", g, "grass", "ok", "Layout", t ? `${t.rows} rows${t.plants ? `, ${t.plants} plants` : ""}` : "Plan rows and plant counts"));
    }
    if (W) out.push(this._tile2("open-water", g, "sprinkler-variant", "info", "Watering", W.configured ? `${W.method === "drip" ? "Drip" : "Sprinklers"}, ${num(W.run_min, 0)} min` : "Lay out the garden first"));
    return out.length ? `<div class="tiles2">${out.join("")}</div>` : "";
  }
  _layoutTile(g) {
    const L = g.layout;
    if (!L) return "";
    const t = L.configured ? L.totals : null;
    const sub = t ? `${num(L.length_ft, 1)} ft rows, ${num(L.width_ft, 1)} ft deep, ${t.rows} rows${t.plants ? `, ${t.plants} plants` : ""}` : "Plan rows, plant counts, T-posts and cages";
    return `<div class="card tile" data-act="open-layout" data-g="${g.id}"><div class="row"><div class="pic" style="background:color-mix(in srgb,var(--ok) 18%,transparent);color:var(--ok)">${this._icon("grass")}</div><div class="grow"><div style="font-size:15px;font-weight:500">Layout planner</div><div class="sub">${esc(sub)}</div></div>${this._icon("chevron-right")}</div></div>`;
  }
  _irrTile(g) {
    const W = g.irrigation;
    if (!W) return "";
    const sub = W.configured ? `${W.method === "drip" ? "Drip" : "Sprinklers"}, ${num(W.run_min, 0)} min, ${num(W.totals.gpm, 2)} GPM` : "Drip line, run times and fertigation. Lay out the garden first";
    return `<div class="card tile" data-act="open-water" data-g="${g.id}"><div class="row"><div class="pic" style="background:color-mix(in srgb,var(--info) 18%,transparent);color:var(--info)">${this._icon("sprinkler-variant")}</div><div class="grow"><div style="font-size:15px;font-weight:500">Watering and fertigation</div><div class="sub">${esc(sub)}</div></div>${this._icon("chevron-right")}</div></div>`;
  }
  _irrView(g) {
    const W = g.irrigation, gid = g.id, drip = W.method === "drip";
    let h = `<div class="hd">${this._btn("back", "arrow-left", "", "", "ic")}<div class="grow"><div class="ttl">Watering</div><div class="sub">${esc(g.name)}, one irrigation zone</div></div></div>`;
    if (!W.configured) return h + `<div class="card"><div class="small mut">Lay out the garden first (rows and crops), then this page works out the drip line and run times.</div></div>`;
    const T = W.totals, soil = W.soils.find((x) => x.key === W.soil);
    h += `<div class="card"><div class="seg">${Object.entries(W.methods).map(([k, n]) => `<button class="${W.method === k ? "on" : ""}" data-act="irr-method" data-g="${gid}" data-m="${k}">${esc(n)}</button>`).join("")}</div>`;
    if (!drip) h += this._sprinklerPlan(W, gid);
    else {
    h += `<div class="stats" style="margin-top:10px"><div class="stat"><span>Run time</span><b>${num(W.run_min, 0)} min</b></div><div class="stat"><span>Waterings a week</span><b>${W.per_week}</b></div><div class="stat"><span>Whole garden</span><b>${num(T.gpm, 2)} GPM</b></div><div class="stat"><span>Each watering</span><b>${num(T.gal_watering, 0)} gal</b></div><div class="stat"><span>Each week</span><b>${num(T.gal_week, 0)} gal</b></div>${drip ? `<div class="stat"><span>Emitters</span><b>${T.emitters}</b></div>` : ""}</div>`;
    h += `<div class="small mut" style="margin-top:8px">${drip ? (W.run_min_set ? `Run time set by you (${num(W.auto_run_min, 0)} min would be the shortest that fits). ` : "Run time worked out from the thirstiest crop at about 1 gph per plant. ") : (W.sprinkler_gpm ? "" : "Sprinkler GPM worked out from the water needed and the run time. ")}${esc(soil.name)} soil: ${esc(W.soil_note)}</div>`;
    }
    h += `<div class="row" style="margin-top:8px;flex-wrap:wrap;gap:6px">${this._btn("irr-set", "cog", "Soil and run time", `data-g="${gid}"`)}${W.run_min_set ? this._btn("irr-auto", "auto-fix", "Work out run time", `data-g="${gid}"`) : ""}</div></div>`;
    h += this._wxCard(W);
    if (!drip) {
      const sk = W.sprinkler, start = h.length;
      h += `<div class="card"><div class="row"><div class="sec grow" style="margin:0">${this._icon("sprinkler-variant")} Sprinkler setup</div>${this._btn("irr-sprk", "pencil", "Edit", `data-g="${gid}"`)}${this._btn("toggle-sec", "chevron-up", "", `data-s="sprk"`, "ic")}</div><div class="small mut" style="margin-top:6px">${esc(sk.modes[sk.mode])}, ${num(sk.gpm, 1)} GPM, ${num(sk.radius_ft, 0)} ft ${sk.arc === 360 ? "full circle" : `${sk.arc} degree arc`}. ${sk.pr_mode === "measured" && sk.pr_in_hr ? `Rate measured at ${num(sk.pr_in_hr, 2)} in an hour.` : `Works out to ${num(sk.pr_calc, 2)} in an hour over ${num(sk.cover_sqft, 0)} sq ft a sprinkler.`} ${sk.mode === "fixed" ? `${sk.heads} fixed sprinkler${sk.heads === 1 ? "" : "s"}${sk.needed > sk.heads ? ` (${sk.needed} would cover the garden)` : ""}.` : `The garden is ${sk.needed} place${sk.needed === 1 ? "" : "s"} for it.`}</div></div>`;
      h = this._collapsible(h, start, "sprk", "sprinkler-variant", "Sprinkler setup", `${sk.modes[sk.mode]}, ${num(sk.gpm, 1)} GPM, ${num(sk.radius_ft, 0)} ft: ${num(sk.pr, 2)} in an hour`);
    }
    if (drip && T.lines_over.length) h += `<div class="alarm" style="--hold:var(--spray)"><b>${this._icon("alert")} Too much water for one line</b><div class="small">Row${T.lines_over.length === 1 ? "" : "s"} ${T.lines_over.map((i) => i + 1).join(", ")} would put more than ${num(W.max_line_gph, 0)} gph through a single run of 1/2 inch line. Feed the line from the middle or split the row.</div></div>`;
    h += `<div class="card"><div class="sec">By crop</div>`;
    for (const c of W.crops) {
      const note = c.short ? `<span class="pill warn" style="margin:0">${c.pct}% of need</span>` : c.over ? `<span class="pill info" style="margin:0">${c.pct}% of need</span>` : c.pct ? `<span class="pill ok" style="margin:0">${c.pct}% of need</span>` : "";
      h += `<div class="row" style="align-items:flex-start;margin:8px 0;gap:8px"><div class="grow"><div style="font-weight:500">${esc(c.name)} <span class="mut small">${num(c.water_in_week, 2)} in a week${c.custom_water ? "" : ", default"}</span></div>`;
      if (drip) {
        h += `<div class="small"><b>${esc(c.label)}</b>, ${c.lines} line${c.lines === 1 ? "" : "s"} a row${c.pinned ? " (your choice)" : ""}</div><div class="small mut">${num(c.plant_gph, 2)} gph a plant, ${num(c.gal_plant_watering, 2)} gal a plant each watering${c.alternatives.length ? `. Other options: ${c.alternatives.map((a) => `${esc(a.label)} (${a.minutes} min to meet need)`).join(", ")}` : ""}</div>`;
      } else h += `<div class="small mut">${num(c.water_in_week, 2)} in a week${c.usual_in_week !== c.water_in_week ? ` (usually ${num(c.usual_in_week, 2)})` : ""}; sprinklers put down ${num(W.need_in_week, 2)} in</div>`;
      h += `</div>${note}${this._btn("irr-crop", "pencil", "", `data-g="${gid}" data-c="${esc(c.key)}"`, "ic")}</div>`;
    }
    h += `</div>`;
    if (drip) {
      h += `<div class="card"><div class="sec">By row</div>`;
      for (const r of W.rows) h += `<div class="small" style="margin:6px 0"><b>Row ${r.i + 1}</b>, ${r.lines} line${r.lines === 1 ? "" : "s"}: ${r.items.map((it) => `${esc(it.name)} ${num(it.ft, 1)} ft, ${esc(it.label)}`).join("; ")} <span class="mut">(${num(r.line_gph, 0)} gph in a line${r.over ? ", over the limit" : ""})</span></div>`;
      h += `</div><div class="card"><div class="sec">Drip line to order</div>`;
      for (const o of W.order) h += `<div class="row" style="margin:8px 0;align-items:flex-start"><div class="grow"><div style="font-weight:500">${esc(o.label)}</div><div class="small mut">${o.emitters} emitters, ${num(o.feet, 0)} ft laid</div></div><div style="text-align:right"><b>${o.order_ft} ft</b><div class="small mut">${o.rolls.map((r) => `${r.count} x ${r.len} ft`).join(" + ")}</div></div></div>`;
      h += `<div class="row" style="margin-top:8px"><div class="grow"><b>Total</b></div><b>${num(T.feet, 0)} ft laid</b></div><div class="small mut" style="margin-top:6px">Feet are for the drip line in the rows, with ${Math.round((W.waste - 1) * 100)}% added for cuts and fittings when ordering. Supply tubing from the valve to the garden is not counted. Flows (${W.flows.join(", ")} gph), spacings (${W.spacings.join(", ")} in) and rolls (${W.rolls.join(", ")} ft) are for <a href="https://www.dripdepot.com/half-inch-polyethylene-pressure-compensating-drip-line" target="_blank" rel="noopener">Drip Depot's 1/2 inch pressure compensating drip line</a>; check them on the product page when you order.</div></div>`;
    }
    const F = W.fert;
    h += `<div class="card"><div class="row"><div class="sec grow" style="margin:0">${this._icon("flask-outline")} Fertigation</div>${this._btn("irr-pump", "plus", "Injector", `data-g="${gid}"`)}${F.tank_names.length ? this._btn("irr-tanks", "swap-horizontal", "Tanks", `data-g="${gid}"`) : ""}</div>`;
    for (const p of F.pumps) h += `<div class="row small" style="margin:4px 0"><div class="grow"><b>${esc(p.name)}</b> <span class="mut">${p.type === "venturi" ? `venturi, draws ${num(p.suction_gph, 1)} gph${p.inlet_psi !== null && p.outlet_psi !== null ? ` at ${num(p.inlet_psi, 0)} to ${num(p.outlet_psi, 0)} psi` : ""}, ${p.install === "bypass" ? "bypass" : "in the main line"}, tank up to ${num(p.tank_gal, 1)} gal` : `1:${num(p.min_ratio, 0)} to 1:${num(p.max_ratio, 0)}, ${num(p.min_gpm, 2)} to ${num(p.max_gpm, 1)} GPM, tank up to ${num(p.tank_gal, 1)} gal`}</span></div>${this._btn("irr-pump", "pencil", "", `data-g="${gid}" data-k="${esc(p.key)}"`, "ic")}</div>`;
    h += `<div class="small mut" style="margin:2px 0 8px">Feeding every ${F.every_days} days.</div>`;
    h += `<div class="chips">${F.mixes.map((m) => `<button class="chip ${m.active ? "on" : ""}" data-act="irr-mix-sel" data-g="${gid}" data-k="${esc(m.key)}">${esc(m.name)}</button>`).join("")}<button class="chip" data-act="irr-mix" data-g="${gid}">+ Mix</button></div>`;
    if (F.mix) {
      h += `<div class="row" style="margin:8px 0 4px;flex-wrap:wrap;gap:6px"><div class="grow small mut">${F.mix.ppm_n ? `Strength set to ${num(F.mix.ppm_n, 0)} ppm nitrogen.` : "Strength worked out from your plants' needs."}</div>${this._btn("irr-mix", "pencil", "Edit mix", `data-g="${gid}" data-k="${esc(F.mix.key)}"`)}${this._btn("irr-comp", "plus", "Fertilizer", `data-g="${gid}" data-k="${esc(F.mix.key)}"`)}</div>`;
      F.mix.components.forEach((c, i) => { h += `<div class="row small" style="margin:3px 0"><div class="grow">${esc(c.name)} <span class="mut">${esc(c.name).includes(`${num(c.n, 1)}-${num(c.p, 1)}-${num(c.k, 1)}`) ? "" : `${num(c.n, 1)}-${num(c.p, 1)}-${num(c.k, 1)}, `}${c.ca ? `${num(c.ca, 1)}% Ca, ` : ""}${c.mg ? `${num(c.mg, 1)}% Mg, ` : ""}${num(c.parts, 2)} part${c.parts === 1 ? "" : "s"}, tank ${esc(c.tank)}</span></div>${this._btn("irr-comp", "pencil", "", `data-g="${gid}" data-k="${esc(F.mix.key)}" data-i="${i}"`, "ic")}</div>`; });
    }
    if (F.warnings.length) for (const w of F.warnings) h += `<div class="alarm" style="--hold:var(--spray)"><div class="small">${this._icon("alert")} ${esc(w)}</div></div>`;
    if (!F.ready) h += `<div class="small mut" style="margin-top:8px">Add a fertilizer with some nitrogen to see amounts.</div>`;
    else {
      h += `<div class="sec" style="margin-top:12px">Each feeding</div><div class="stats"><div class="stat"><span>Nitrogen strength</span><b>${num(F.ppm_n, 0)} ppm</b></div><div class="stat"><span>Water through the pump</span><b>${num(F.water_gal, 0)} gal</b></div><div class="stat"><span>Injector on for</span><b>${num(F.inject_min, 0)} min</b></div><div class="stat"><span>Then plain water</span><b>${num(F.flush_min, 0)} min</b></div></div>`;
      for (const t of F.tanks) {
        h += `<div class="card" style="margin:10px 0 0;background:color-mix(in srgb,var(--c,var(--ok)) 6%,transparent)"><div class="row"><div class="sec grow" style="margin:0">Tank ${esc(t.tank)}${t.batches > 1 ? `, ${t.batches} batches` : ""} <span class="small mut">on ${esc(t.pump_name)}</span></div>${t.venturi ? "" : `<b>Dial ${esc(t.dial)}</b>`}</div>${t.venturi ? `<div class="small" style="margin:2px 0 6px"><b>Venturi:</b> ${esc(t.dial)}</div>` : ""}`;
        for (const c of t.components) h += `<div class="row" style="margin:4px 0"><div class="grow">${esc(c.name)}</div><div style="text-align:right"><b>${num(c.g, 0)} g</b> <span class="small mut">${num(c.oz, 1)} oz${c.lb >= 0.5 ? `, ${num(c.lb, 2)} lb` : ""}</span></div></div>`;
        h += `<div class="small mut">Dissolve in water to make ${num(t.stock_gal, 2)} gal${t.batches > 1 ? " each batch" : ""} (${num(t.g_per_gal, 0)} g a gallon). ${t.venturi ? "Run the venturi with" : "Set the pump to"} ${esc(t.dial)} and run it for ${num(F.inject_min, 0)} minutes with the zone, then ${num(F.flush_min, 0)} minutes of plain water.</div></div>`;
      }
      if (F.feed_runs.length > 1) h += `<div class="small" style="margin-top:10px"><b>Run plan:</b> ${F.feed_runs.map((r) => `watering ${r.n}: tank ${r.tanks.join(" and ")}`).join("; ")}.</div>`;
      const an = F.analysis;
      h += `<div class="small mut" style="margin-top:10px">What the plants get in the water: ${num(an.N, 0)} ppm N, ${num(an.P2O5, 0)} ppm P2O5, ${num(an.K2O, 0)} ppm K2O${an.Ca ? `, ${num(an.Ca, 0)} ppm Ca` : ""}${an.Mg ? `, ${num(an.Mg, 0)} ppm Mg` : ""}. The blend is ${num(F.n_pct, 1)}% nitrogen. That is ${num(F.lb_n_1000, 2)} lb of nitrogen per 1,000 sq ft a feeding, ${num(F.lb_n_week, 3)} lb a week for the garden.</div><div style="margin-top:6px">${this._btn("irr-sched", "calendar-clock", `Every ${F.every_days} days`, `data-g="${gid}"`)}</div>`;
      if (F.overfed.length) {
        h += `<div class="sec" style="margin-top:12px">Shorten these sections</div>`;
        for (const o of F.overfed) h += `<div class="alarm" style="--hold:var(--spray)"><div class="small"><b>${esc(o.name)}</b>${o.rows.length ? ` (row${o.rows.length === 1 ? "" : "s"} ${o.rows.join(", ")})` : ""} wants about ${num(o.your_ppm, 0)} ppm and this mix is ${num(F.ppm_n, 0)}. Valve off its drip lines after ${o.minutes} of the ${o.full_minutes} minutes the injector is on.</div></div>`;
      }
    }
    h += `</div>`;
    const accStart = h.length;
    const A = W.acid, raise = A.mode === "raise";
    h += `<div class="card"><div class="row"><div class="sec grow" style="margin:0">${this._icon("beaker-outline")} Water pH ${raise ? "(raise)" : "and acid"}</div>${this._btn("irr-acid", "pencil", "Water test", `data-g="${gid}"`)}${this._btn("toggle-sec", "chevron-up", "", `data-s="acid"`, "ic")}</div>`;
    if (!A.ready) h += `<div class="small mut" style="margin-top:6px">Enter your water's pH and total alkalinity (TA, in ppm as calcium carbonate) from a test. Water above your target pH gets sulfuric acid (${num(A.strength_pct, 0)}% by weight); water below it gets a base such as potassium bicarbonate.</div>`;
    else {
      h += `<div class="small mut" style="margin:6px 0">Water tested pH ${num(A.ph, 2)}, TA ${num(A.ta_ppm, 0)} ppm. Target pH ${num(A.target_ph, 1)}${raise ? ` with ${esc(A.base_name || "a base")}` : ` with ${num(A.strength_pct, 0)}% sulfuric acid (${num(A.sg, 3)} specific gravity, ${num(A.meq_per_ml, 1)} meq a mL)`}.</div>`;
      for (const w of A.warnings) h += `<div class="alarm" style="--hold:var(--spray)"><div class="small">${this._icon("alert")} ${esc(w)}</div></div>`;
      const amt = raise ? A.g_per_gal : A.ml_per_gal;
      if (amt) {
        h += raise
          ? `<div class="stats"><div class="stat"><span>Base per gallon of water</span><b>${num(A.g_per_gal, 2)} g</b></div><div class="stat"><span>Per 1,000 gal</span><b>${num(A.kg_per_1000, 2)} kg</b></div></div>`
          : `<div class="stats"><div class="stat"><span>Acid per gallon of water</span><b>${num(A.ml_per_gal, 2)} mL</b></div><div class="stat"><span>Per 1,000 gal</span><b>${num(A.ml_per_1000 / 1000, 2)} L</b></div></div>`;
        if (A.tank) h += `<div class="card" style="margin:10px 0 0;background:color-mix(in srgb,var(--c,var(--ok)) 6%,transparent)"><div class="row"><div class="sec grow" style="margin:0">${raise ? "Base" : "Acid"} tank <span class="small mut">on ${esc(A.pump_name)}</span></div>${/^suction/.test(A.tank.dial) ? "" : `<b>Dial ${esc(A.tank.dial)}</b>`}</div>${/^suction/.test(A.tank.dial) ? `<div class="small" style="margin:2px 0 6px"><b>Venturi:</b> ${esc(A.tank.dial)}</div>` : ""}<div class="row" style="margin:4px 0"><div class="grow">${raise ? esc(A.base_name) : `${num(A.strength_pct, 0)}% sulfuric acid`}</div><div style="text-align:right"><b>${raise ? `${A.tank.g} g` : `${A.tank.ml} mL`}</b> <span class="small mut">${raise ? `${num(A.tank.oz, 1)} oz` : `${num(A.tank.oz, 1)} fl oz`}</span></div></div><div class="small mut">${raise ? "Dissolve it in" : "Pour the acid slowly into"} about ${num(A.tank.stock_gal, 1)} gal of water${raise ? "" : " (never water into acid)"} so it makes ${num(A.tank.stock_gal, 2)} gal${A.tank.batches > 1 ? ` a batch, ${A.tank.batches} batches` : ""}. Set the pump to ${esc(A.tank.dial)} and run it with the zone for the ${num(A.water_gal, 0)} gal of a watering. ${esc(A.note || "")}</div></div>`;
        if (A.tank) h += `<div class="row" style="margin-top:10px;flex-wrap:wrap;gap:6px">${this._btn("irr-acid-log", "check", "Log this application", `data-g="${gid}" data-q="1"`)}${this._btn("irr-acid-log", "plus", "Log another amount", `data-g="${gid}"`)}</div>`;
        if (A.table.length) h += `<div class="small mut" style="margin-top:8px">${raise ? "Base" : "Acid"} for other targets, per gallon: ${A.table.map((t) => `pH ${t.ph} ${raise ? `${num(t.g_per_gal, 2)} g` : `${num(t.ml_per_gal, 2)} mL`}`).join(", ")}.</div>`;
        h += `<div class="small mut" style="margin-top:6px">This is for the water alone and assumes no carbon dioxide escapes, so measure at an emitter with a meter and adjust. Fertilizer in the water changes the pH too. Keep ${raise ? "base" : "acid"} in its own labeled tank, away from fertilizer, wear eye protection and gloves, and make sure your pump's seals and tubing are rated for it.</div>`;
      }
    }
    const AL = W.acid_log;
    if (AL.entries.length) {
      h += `<div class="sec" style="margin-top:12px">Applied</div><div class="small mut" style="margin-bottom:4px">${AL.days_since === 0 ? "Today" : `${AL.days_since} days ago`} was the last. ${AL.count_year} application${AL.count_year === 1 ? "" : "s"} in ${AL.year}${AL.ml_year ? `, ${num(AL.ml_year / 1000, 2)} L of acid` : ""}${AL.g_year ? `, ${num(AL.g_year / 1000, 2)} kg of base` : ""}.</div>`;
      for (const e of AL.entries.slice(0, 8)) h += this._logRow("acid", gid, e.id, `${fmtDate(e.date)}, ${e.g ? `${num(e.g, 0)} g${e.product ? " " + esc(e.product) : ""}` : `${num(e.ml, 0)} mL`}`, `${e.water_gal ? `${num(e.water_gal, 0)} gal` : ""}${e.ph_before ? `${e.water_gal ? ", " : ""}pH ${num(e.ph_before, 2)}${e.ph_after ? ` to ${num(e.ph_after, 2)}` : ""}` : ""}${e.notes ? " · " + esc(e.notes) : ""}`);
    }
    h += `</div>`;
    h = this._collapsible(h, accStart, "acid", "beaker-outline", raise ? "Water pH (raise)" : "Water pH and acid",
      !A.ready ? "Enter a water test to work out the acid" : (raise ? `pH ${num(A.ph, 1)} to ${num(A.target_ph, 1)}: ${num(A.g_per_gal, 2)} g of base a gallon${A.tank ? `, ${A.tank.g} g in the tank` : ""}`
        : `pH ${num(A.ph, 1)} to ${num(A.target_ph, 1)}: ${num(A.ml_per_gal, 2)} mL of acid a gallon${A.tank ? `, ${A.tank.ml} mL in the tank` : ""}`) + (W.acid_log.last ? `. Last applied ${W.acid_log.days_since === 0 ? "today" : `${W.acid_log.days_since} days ago`}` : ""));
    const limeStart = h.length;
    const Li = W.lime;
    h += `<div class="card"><div class="row"><div class="sec grow" style="margin:0">${this._icon("shovel")} Raise soil pH</div>${this._btn("irr-lime", "pencil", "Lime", `data-g="${gid}"`)}${this._btn("toggle-sec", "chevron-up", "", `data-s="lime"`, "ic")}</div>`;
    if (!Li.ready) h += `<div class="small mut" style="margin-top:6px">Log a soil pH on the garden's page, or enter one under Lime, to work out how much garden lime to spread.</div>`;
    else {
      h += `<div class="small mut" style="margin:6px 0">Soil pH ${num(Li.ph, 1)} (${Li.ph_from === "you" ? "entered here" : "your latest log"}) to ${num(Li.target_ph, 1)}, ${esc(Li.type_name.toLowerCase())}, ${Li.tilled ? "worked in" : "left on top"} to ${num(Li.depth_in, 0)} in.</div>`;
      for (const w of Li.warnings) h += `<div class="alarm" style="--hold:var(--spray)"><div class="small">${this._icon("alert")} ${esc(w)}</div></div>`;
      if (Li.lb_1000) {
        h += `<div class="stats"><div class="stat"><span>Per 1,000 sq ft</span><b>${num(Li.lb_1000, 0)} lb</b></div><div class="stat"><span>Per 100 sq ft</span><b>${num(Li.lb_100, 1)} lb</b></div><div class="stat"><span>${Li.area_given ? `This garden (${num(Li.area_sqft, 0)} sq ft)` : "Per 1,000 sq ft"}</span><b>${num(Li.lb_total, 0)} lb</b></div><div class="stat"><span>Applications</span><b>${Li.applications}</b></div></div>`;
        if (Li.applications > 1) h += `<div class="small" style="margin-top:8px">Spread ${num(Li.per_application_total, 0)} lb (${num(Li.per_application_1000, 0)} lb per 1,000 sq ft) each time, months apart, and re-test the soil between.</div>`;
        h += `<div class="small mut" style="margin-top:6px">Spread it dry and rake or till it in; it takes 3 to 9 months to work, so fall is a good time. Based on about ${num(Li.lb_per_unit, 0)} lb of pure limestone per 1,000 sq ft for each pH unit on ${esc((W.soils.find((x) => x.key === Li.soil) || {}).name || "this soil").toLowerCase()}. ${esc(Li.notes)}</div>`;
      }
    }
    h += `</div>`;
    return this._collapsible(h, limeStart, "lime", "shovel", "Raise soil pH", !Li.ready ? "Log a soil pH to work out the lime" : Li.lb_1000 ? `pH ${num(Li.ph, 1)} to ${num(Li.target_ph, 1)}: ${num(Li.lb_1000, 0)} lb per 1,000 sq ft${Li.area_given ? `, ${num(Li.lb_total, 0)} lb for this garden` : ""}` : "No lime needed");
  }
  _collapsible(h, start, key, icon, title, summary) {
    if ((this._exp || {})[key]) return h;
    return h.slice(0, start) + `<div class="card tile" data-act="toggle-sec" data-s="${key}"><div class="row"><div class="grow"><div class="sec" style="margin:0">${this._icon(icon)} ${esc(title)}</div><div class="small mut" style="margin-top:2px">${esc(summary)}</div></div>${this._icon("chevron-down")}</div></div>`;
  }
  _shadeWarn(SU) {
    if (!SU || !SU.shading.length) return "";
    let h = "";
    for (const w of SU.shading.slice(0, 4)) {
      const by = w.by.length ? w.by.join(" and ") : "A taller crop";
      h += `<div class="alarm" style="--hold:var(--spray);margin-top:8px"><div class="small">${this._icon("alert")} <b>${esc(by)}</b> shades <b>${esc(w.name)}</b> (${num(w.height, 1)} ft): about ${w.pct}% of its sun from ${SU.months}, mostly in the ${esc(w.when)}. Put the tall crops on the ${esc(SU.current_side)} side, so their shade falls off the garden.</div></div>`;
    }
    return h;
  }
  _sunCard(L, gid) {
    const SU = L.sun;
    const planted = SU.planted, ang = (n) => `${num(n, 0)} degrees`;
    let t;
    if (!planted) t = `Plant some rows to see the sun and shade. For tall crops beside short ones, rows running ${SU.best} degrees with the tall crops on the ${SU.tall_side} side lose the least sun.`;
    else if (SU.even) t = `No crop stands more than ${num(1.5, 1)} ft over another, so shade between rows is small whichever way they run. Rows running north-south (0 degrees) give both sides of each row the same sun.`;
    else {
      const turn = Math.abs(((SU.best - SU.heading + 270) % 180) - 90) >= 5;
      t = `Tallest is ${esc(SU.tallest.name)} at ${num(SU.tallest.height, 1)} ft, over ${esc(SU.shortest.name)} at ${num(SU.shortest.height, 1)} ft. At ${ang(SU.heading)} the shorter crops beside tall rows can lose about ${SU.current_pct}% of their sun, ${SU.months}, if they sit on the shaded side. ${turn ? `Rows at ${SU.best} degrees with the tall crops on the ${esc(SU.tall_side)} side cut that to ${SU.best_pct}%.` : `That is about the best angle for this garden.`} With your rows as they are, put the tall crops on the ${esc(SU.current_side)} side.`;
    }
    const show = (this._exp || {}).sun;
    const body = `<div class="small" style="margin-top:6px">${t}</div><div class="small mut" style="margin-top:6px">Worked out from where the sun stands over ${SU.lat_assumed ? "a garden at 40 degrees north (set your location for a closer figure)" : `${num(SU.lat, 1)} degrees north`} on the 15th of each month, ${SU.months}, hour by hour. Shade is the sun a crop loses to a taller crop beside it. It is a guide, and trees, fences and buildings are not counted.</div>`;
    const turnBtn = planted && !SU.even && Math.abs(((SU.best - SU.heading + 270) % 180) - 90) >= 5 ? `<div class="row" style="margin-top:8px">${this._btn("lay-ang", "", `Turn the rows to ${SU.best} degrees`, `data-g="${gid}" data-n="${SU.best}"`, "primary")}</div>` : "";
    const sum = !planted ? `Best angle for tall crops: ${SU.best} degrees` : SU.even ? "Crops are about the same height" : SU.shading.length ? `${SU.shading.length} crop${SU.shading.length === 1 ? "" : "s"} shaded, best angle ${SU.best} degrees` : `No shading problems, best angle ${SU.best} degrees`;
    if (!show) return `<div class="card tile" data-act="toggle-sec" data-s="sun"><div class="row"><div class="grow"><div class="sec" style="margin:0">${this._icon("weather-sunny")} Sun and shade</div><div class="small mut">${esc(sum)}</div></div>${this._icon("chevron-down")}</div></div>`;
    return `<div class="card"><div class="row"><div class="sec grow" style="margin:0">${this._icon("weather-sunny")} Sun and shade</div>${this._btn("toggle-sec", "chevron-up", "", `data-s="sun"`, "ic")}</div>${body}${turnBtn}</div>`;
  }
  _fDays(g, key) {
    const S = g.season, c = key ? S.crops.find((x) => x.key === key) : null;
    const hard = Object.entries(S.hardiness);
    return {
      title: c ? `Days to harvest: ${c.name}` : "Give a crop a time", submitLabel: "Save",
      fields: [
        ...(c ? [] : [{ name: "crop", label: "Crop", type: "select", options: S.untimed.map((x) => [x.key, x.name]), value: S.untimed[0].key }]),
        { name: "days", label: "Days from planting to harvest (seed packet)", type: "number", step: "1", value: c ? c.days : "", req: true },
        { name: "hardy", label: "Frost", type: "select", options: hard, value: c ? c.hardy : "tender" },
      ],
      note: `${c && c.usual_days ? `The usual figure is ${c.usual_days} days. ` : ""}Use the days to maturity on the packet. For tomatoes, peppers and other transplants it counts from setting out the plant, so start the clock then. Perennials like mint or rosemary have no season to fit.`,
      extra: c && c.edited ? { label: "Back to the usual", act: () => this._call("reset_crop_days", { crop: key }) } : null,
      submit: (x) => this._call("set_crop_days", { crop: key || x.crop, days: x.days, hardy: x.hardy }),
    };
  }
  _choreCard(g) {
    if (!this._show.chores) return "";
    const cs = g.chores || [];
    return cs.map((c) => `<div class="card"><div class="alarm" style="--hold:var(--spray)"><div class="small"><b>${this._icon("alert")} ${esc(c.title)}.</b> ${esc(c.text)}</div></div></div>`).join("");
  }

  _seasonCard(g) {
    const S = g.season;
    if (!S) return "";
    const dt = (iso) => fmtDate(iso);
    const left = S.days_to_frost;
    const frost = left >= 0 ? `First frost ${dt(S.first_frost)}, in ${left} days` : `First frost was ${dt(S.first_frost)}`;
    const sum = `${frost}. ${S.now ? `${S.now} crop${S.now === 1 ? "" : "s"} can still be planted` : "Nothing more to plant until spring"}`;
    if (!(this._exp || {}).season) return `<div class="card tile" data-act="toggle-sec" data-s="season" style="background:color-mix(in srgb,var(--spray) ${S.now ? 14 : 6}%,var(--card-background-color))"><div class="row"><div class="pic" style="background:color-mix(in srgb,var(--spray) 18%,transparent);color:var(--spray)">${this._icon("snowflake-alert")}</div><div class="grow"><div style="font-size:15px;font-weight:500">Time before frost</div><div class="small mut">${esc(sum)}</div></div>${this._icon("chevron-down")}</div></div>`;
    const group = (title, rows, empty) => rows.length ? `<div class="sec" style="margin-top:12px">${title}</div>` + rows.map((c) => {
      const cls = c.status === "plant" ? "ok" : c.status === "tight" ? "warn" : c.status === "short" || c.status === "late" ? "bad" : "none";
      const extra = c.rounds > 1 && (c.status === "plant" || c.status === "tight" || c.status === "wait") ? `, up to ${c.rounds} plantings back to back` : "";
      return `<div class="row" style="align-items:flex-start;margin:6px 0;gap:8px"><div class="grow"><div style="font-weight:500">${esc(c.name)}${c.planted ? ` <span class="mut small">in your layout</span>` : ""}</div><div class="small mut">${c.fall ? "Harvest next summer" : `${c.days} days to harvest${extra}`}</div></div><span class="pill ${cls}" style="margin:0;text-align:right">${esc(c.text)}</span>${this._btn("season-days", "pencil", "", `data-g="${g.id}" data-c="${esc(c.key)}"`, "ic")}</div>`;
    }).join("") : (empty ? `<div class="small mut" style="margin-top:8px">${empty}</div>` : "");
    const by = (st) => S.crops.filter((c) => st.includes(c.status));
    let h = `<div class="card"><div class="row"><div class="sec grow" style="margin:0">${this._icon("snowflake-alert")} Time before frost</div>${this._btn("toggle-sec", "chevron-up", "", `data-s="season"`, "ic")}</div>`;
    h += `<div class="small" style="margin-top:6px">${esc(frost)}. Last spring frost ${dt(S.last_frost)}, so the season runs about ${S.season_days} days.</div>`;
    h += group("Plant now", by(["plant", "tight"]), "Nothing is left to plant this year except what is listed below.");
    h += group("Opens later", by(["wait"]));
    h += group("Too late this year", by(["late"]));
    h += group("Season too short", by(["short"]));
    if (S.untimed.length) h += `<div class="row" style="margin-top:10px">${this._btn("season-days", "plus", "Give another crop a time", `data-g="${g.id}"`)}</div>`;
    h += `<div class="small mut" style="margin-top:10px">Tap the pencil to enter the days to harvest from your seed packet. Planting windows come from the frost dates of this garden (change them on the frost pill) and typical days to harvest. Frost-hardy crops go out up to four weeks early and keep growing a little past the first frost, tender ones wait until after the last frost. Fast crops like radishes can be sown again as soon as the last is out. Garlic goes in around the first frost for harvest next summer. A guide, not a promise.</div></div>`;
    return h;
  }
  _wxCard(W) {
    const x = W.weather;
    if (!W.use_weather) return `<div class="card"><div class="small mut">${this._icon("weather-sunny")} Watering is not adjusted for the weather. Turn it on in Soil and run time.</div></div>`;
    if (!x) return `<div class="card"><div class="small mut">${this._icon("weather-sunny")} No temperatures recorded yet, so these are the usual amounts. Pick a temperature sensor (or in the web app set a location) and the plan follows the weather.</div></div>`;
    const sign = x.pct > 0 ? "+" : "", cls = x.pct >= 30 ? "warn" : "info";
    let t = `Last ${x.days} day${x.days === 1 ? "" : "s"}: highs averaged ${x.avg_high}°F (hottest ${x.hottest}°F), lows ${x.avg_low}°F, so plants lose about ${num(x.et_week, 1)} in a week against ${num(x.ref_week, 1)} in a typical warm one.`;
    t += x.rain_in ? ` Rain ${num(x.rain_in, 2)} in, ${num(x.rain_credit, 2)} in of it counted.` : " No rain recorded.";
    if (x.lat_assumed) t += " Set your location for a closer figure.";
    return `<div class="card"><div class="row"><div class="sec grow" style="margin:0">${this._icon("weather-sunny")} This week's weather</div><span class="pill ${cls}" style="margin:0">${x.pct === 0 ? "usual" : `${sign}${x.pct}% water`}</span></div><div class="small" style="margin-top:6px">${esc(x.word[0].toUpperCase() + x.word.slice(1))} week. ${esc(t)}</div></div>`;
  }
  _sprinklerPlan(W, gid) {
    const sk = W.sprinkler, T = W.totals;
    let h = `<div class="sec" style="margin-top:12px">How to water</div>`;
    if (sk.mode === "fixed") h += `<div class="stats"><div class="stat"><span>Run all ${sk.heads} sprinkler${sk.heads === 1 ? "" : "s"} for</span><b>${sk.minutes} min</b></div><div class="stat"><span>Times a week</span><b>${sk.per_week}</b></div><div class="stat"><span>Whole garden</span><b>${num(T.gpm, 1)} GPM</b></div><div class="stat"><span>Each watering</span><b>${num(sk.gal_session, 0)} gal</b></div></div>`;
    else h += `<div class="stats"><div class="stat"><span>Each place</span><b>${sk.minutes} min</b></div><div class="stat"><span>Places in the garden</span><b>${sk.sets}</b></div><div class="stat"><span>Times a week</span><b>${sk.per_week}</b></div><div class="stat"><span>A watering takes</span><b>${num(sk.session_hours, 1)} h</b></div></div>`;
    h += `<div class="small" style="margin-top:8px">${sk.mode === "fixed" ? `Run the sprinklers ${sk.minutes} minutes, ${sk.per_week} times a week` : `Set the sprinkler in ${sk.sets} place${sk.sets === 1 ? "" : "s"} across the garden, overlapping them so each throws to the next, and run it ${sk.minutes} minutes in each, ${sk.per_week} times a week`}. That puts down ${num(sk.depth_in, 2)} in a watering, ${num(W.need_in_week, 2)} in a week, the most the thirstiest crop wants.${sk.per_week_auto ? " The number of days suits the soil; change it in the setup." : ""}</div>`;
    if (sk.over_intake) h += `<div class="alarm" style="--hold:var(--spray)"><div class="small">${this._icon("alert")} Water in ${sk.cycles} cycle${sk.cycles === 1 ? "" : "s"} of ${sk.cycle_min} minutes with about ${sk.soak_min} minutes between, because the sprinkler puts down ${num(sk.pr, 2)} in an hour and this soil takes in about ${num(sk.intake_in_hr, 1)}.</div></div>`;
    for (const w of sk.warnings.filter((x) => !x.includes("takes in about"))) h += `<div class="alarm" style="--hold:var(--spray)"><div class="small">${this._icon("alert")} ${esc(w)}</div></div>`;
    return h;
  }
  _fSprk(g) {
    const sk = g.irrigation.sprinkler;
    return {
      title: "Sprinkler setup", submitLabel: "Save",
      fields: [
        { name: "mode", label: "How they are used", type: "select", options: Object.entries(sk.modes), value: sk.mode },
        { name: "gpm", label: "Gallons a minute through one sprinkler", type: "number", step: "any", value: sk.gpm, req: true },
        { name: "radius_ft", label: "How far it throws (feet)", type: "number", step: "any", value: sk.radius_ft, req: true },
        { name: "arc", label: "Arc", type: "select", options: sk.arcs.map((a) => [String(a), a === 360 ? "Full circle" : `${a} degrees`]), value: String(sk.arc) },
        { name: "pr_mode", label: "Rate of water", type: "select", options: [["calc", "Work it out from flow and radius"], ["measured", "I measured it (catch cans)"]], value: sk.pr_mode },
        { name: "pr_in_hr", label: "Measured inches an hour", type: "number", step: "any", value: sk.pr_in_hr || "", show: (v) => v.pr_mode === "measured" },
        { name: "heads", label: "Fixed sprinklers in this garden (empty for as many as it needs)", type: "number", step: "1", value: sk.mode === "fixed" ? (sk.heads || "") : "", show: (v) => v.mode === "fixed" },
        { name: "per_week", label: "Waterings a week (empty to suit the soil)", type: "number", step: "1", value: sk.per_week_auto ? "" : sk.per_week },
      ],
      note: "Set this up once a year. A sprinkler's rate is about 96 x gallons a minute / the square feet it waters, with the sprinklers laid head to head, so each one throws as far as the next one is placed. To measure it, put straight-sided cans around the garden, run it for 15 minutes and average the depth. A moved sprinkler is placed so its throw reaches the next place.",
      submit: (x) => this._call("set_sprinkler", { garden: g.id, mode: x.mode, gpm: x.gpm, radius_ft: x.radius_ft, arc: Number(x.arc), pr_mode: x.pr_mode, pr_in_hr: x.pr_mode === "measured" ? (x.pr_in_hr === undefined ? null : x.pr_in_hr) : null, heads: x.mode === "fixed" ? (x.heads === undefined ? null : x.heads) : null, per_week: x.per_week === undefined ? null : x.per_week }),
    };
  }
  _fSoil(g) {
    const S = g.soil_setup;
    return {
      title: `Soil and mulch: ${g.name}`, submitLabel: "Save",
      fields: [
        { name: "soil", label: "Soil", type: "select", options: S.soils.map((x) => [x.key, x.name]), value: S.soil },
        { name: "mulch", label: "Mulch layer", type: "select", options: [["0", "No mulch"], ["1", "Mulched"]], value: S.mulch ? "1" : "0" },
      ],
      note: "Used to estimate soil moisture from your last watering and the weather when you have no probe. Mulch slows the drying. A moisture reading you log replaces the estimate.",
      submit: (x) => this._call("set_irrigation", { garden: g.id, soil: x.soil, mulch: x.mulch === "1" }),
    };
  }
  _fIrr(g) {
    const W = g.irrigation;
    return {
      title: `Soil and run time: ${g.name}`, submitLabel: "Save",
      fields: [
        { name: "soil", label: "Soil", type: "select", options: W.soils.map((x) => [x.key, x.name]), value: W.soil },
        { name: "mulch", label: "Mulch layer", type: "select", options: [["0", "No mulch"], ["1", "Mulched"]], value: g.soil_setup && g.soil_setup.mulch ? "1" : "0" },
        { name: "per_week", label: "Waterings a week", type: "number", step: "1", value: W.per_week, req: true },
        { name: "run_min", label: "Minutes each watering (empty to work it out)", type: "number", step: "any", value: W.run_min_set || "" },
        { name: "weather", label: "Adjust for the week's weather", type: "select", options: [["1", "Yes, from my temperature and rain sensors"], ["0", "No, use the usual amounts"]], value: W.use_weather ? "1" : "0" },
        { name: "max_line_gph", label: "Most gph through one run of drip line", type: "number", step: "any", value: W.max_line_gph, show: () => W.method === "drip" },
      ],
      note: "Clay soaks in slowly and only takes 1/2 gph emitters; the other soils take 1 gph. Each garden is its own irrigation zone, so its lines all run together for the same time. The weather adjustment uses the daily low and high and the rain your sensors recorded over the last week, so a hot week asks for more water and a cool or rainy one for less.",
      submit: (x) => this._call("set_irrigation", { garden: g.id, soil: x.soil, mulch: x.mulch === "1", per_week: x.per_week, run_min: x.run_min === undefined ? null : x.run_min, max_line_gph: x.max_line_gph, weather: x.weather === "1" }),
    };
  }
  _fIrrCrop(g, key) {
    const W = g.irrigation, c = W.crops.find((x) => x.key === key), drip = W.method === "drip";
    return {
      title: `Water: ${c.name}`, submitLabel: "Save",
      fields: [
        { name: "water_in_week", label: "Inches of water a week in a typical warm week", type: "number", step: "any", value: c.usual_in_week, req: true },
        { name: "ppm_n", label: "Nitrogen it likes (ppm)", type: "number", step: "any", value: c.ppm_n },
        { name: "lines", label: "Runs of drip line along each row", type: "number", step: "1", value: c.lines, show: () => drip },
        { name: "flow_gph", label: "Emitter flow", type: "select", options: [["", "Suggested"], ...W.flows.map((f) => [String(f), `${f} gph`])], value: c.pinned ? String(c.flow_gph) : "", show: () => drip },
        { name: "emit_in", label: "Emitter spacing", type: "select", options: [["", "Suggested"], ...W.spacings.map((f) => [String(f), `${f} in`])], value: c.pinned ? String(c.emit_in) : "", show: () => drip },
      ],
      note: "Choosing a flow or spacing here overrides the suggestion for this crop. Leave both on Suggested to let the planner pick.",
      submit: (x) => this._call("set_irrigation_crop", { garden: g.id, crop: key, water_in_week: x.water_in_week, ppm_n: x.ppm_n, lines: x.lines, flow_gph: drip ? (x.flow_gph ? Number(x.flow_gph) : null) : undefined, emit_in: drip ? (x.emit_in ? Number(x.emit_in) : null) : undefined }),
    };
  }
  _fLime(g) {
    const L = g.irrigation.lime;
    return {
      title: "Lime for low soil pH", submitLabel: "Save",
      fields: [
        { name: "ph", label: "Soil pH (empty to use your latest log)", type: "number", step: "any", value: L.ph_from === "you" ? L.ph : "" },
        { name: "target_ph", label: "Target soil pH", type: "number", step: "any", value: L.target_ph, req: true },
        { name: "type", label: "What you spread", type: "select", options: L.types.map((t) => [t.key, t.name]), value: L.type },
        { name: "tilled", label: "How it goes on", type: "select", options: [["1", "Worked in"], ["0", "Left on the surface"]], value: L.tilled ? "1" : "0" },
        { name: "depth_in", label: "Depth worked in (inches)", type: "number", step: "any", value: L.depth_in },
        { name: "lb_per_unit", label: "Lab figure: lb of limestone per 1,000 sq ft for 1 pH unit (empty to estimate)", type: "number", step: "any", value: L.lb_per_unit_set || "" },
      ],
      note: "Most vegetables like 6.0 to 6.8. The estimate follows the soil type set under Soil and run time, and grows with clay and organic matter, so a lab test is better. Hydrated lime acts faster and is stronger; wood ash is about two thirds as strong as limestone.",
      submit: (x) => this._call("set_lime", { garden: g.id, ph: x.ph === undefined ? null : x.ph, target_ph: x.target_ph, type: x.type, tilled: x.tilled === "1", depth_in: x.depth_in, lb_per_unit: x.lb_per_unit === undefined ? null : x.lb_per_unit }),
    };
  }
  _fAcid(g) {
    const A = g.irrigation.acid;
    return {
      title: "Water test and acid", submitLabel: "Save",
      fields: [
        { name: "ph", label: "Water pH", type: "number", step: "any", value: A.ph === null ? "" : A.ph, req: true },
        { name: "ta_ppm", label: "Total alkalinity, TA (ppm as calcium carbonate)", type: "number", step: "any", value: A.ta_ppm === null ? "" : A.ta_ppm, req: true },
        { name: "target_ph", label: "Target pH", type: "number", step: "any", value: A.target_ph },
        { name: "strength_pct", label: "Sulfuric acid strength (% by weight)", type: "number", step: "any", value: A.strength_pct },
        { name: "sg", label: "Specific gravity (empty to work it out)", type: "number", step: "any", value: A.sg_set || "" },
        { name: "base", label: "Base to raise a low pH", type: "select", options: (A.bases || [["kbic", "Potassium bicarbonate"], ["nabic", "Sodium bicarbonate (baking soda)"], ["koh", "Potassium hydroxide"]].map(([key, name]) => ({ key, name }))).map((b) => [b.key, b.name]), value: A.base || "kbic" },
      ],
      note: "Test the water before it goes through the pump. If it is below the target pH you get a base to add instead. 35% is battery acid and 93% is concentrated; the specific gravity follows from the strength. Re-test now and then, as the water changes with the seasons.",
      submit: (x) => this._call("set_acid", { garden: g.id, ph: x.ph, ta_ppm: x.ta_ppm, target_ph: x.target_ph, strength_pct: x.strength_pct, sg: x.sg === undefined ? null : x.sg, base: x.base }),
    };
  }
  _fPump(g, key) {
    const F = g.irrigation.fert, i = key ? F.pumps.find((p) => p.key === key) : { name: "", type: "dosing", min_ratio: 50, max_ratio: 500, min_gpm: 0.05, max_gpm: 14, tank_gal: 4, flush_min: 5, suction_gph: 10, motive_gpm: null, inlet_psi: null, outlet_psi: null, install: "inline" };
    const dosing = (v) => (v.kind || "dosing") === "dosing", vent = (v) => v.kind === "venturi";
    return {
      title: key ? `Injector: ${i.name}` : "Add an injector", submitLabel: "Save",
      fields: [
        { name: "kind", label: "Type", type: "seg", options: [["dosing", "Dosing pump (Dosatron)"], ["venturi", "Venturi"]], value: i.type || "dosing" },
        { name: "name", label: "Name", type: "text", value: i.name, req: true, placeholder: "Dosatron D14MZ2 or Mazzei 484" },
        { name: "min_ratio", label: "Strongest dilution (the 50 in 1:50)", type: "number", step: "any", value: i.min_ratio, req: true, show: dosing },
        { name: "max_ratio", label: "Weakest dilution (the 500 in 1:500)", type: "number", step: "any", value: i.max_ratio, req: true, show: dosing },
        { name: "min_gpm", label: "Lowest flow (GPM)", type: "number", step: "any", value: i.min_gpm, show: dosing },
        { name: "max_gpm", label: "Highest flow (GPM)", type: "number", step: "any", value: i.max_gpm, show: dosing },
        { name: "suction_gph", label: "Suction at your pressures, valve wide open (gallons an hour)", type: "number", step: "any", value: i.suction_gph ?? 10, req: true, show: vent },
        { name: "install", label: "Where it is plumbed", type: "seg", options: [["inline", "In the main line"], ["bypass", "On a bypass"]], value: i.install || "inline", show: vent },
        { name: "inlet_psi", label: "Pressure going in (psi)", type: "number", step: "any", value: i.inlet_psi === null || i.inlet_psi === undefined ? "" : i.inlet_psi, span: 3, show: vent },
        { name: "outlet_psi", label: "Pressure coming out (psi)", type: "number", step: "any", value: i.outlet_psi === null || i.outlet_psi === undefined ? "" : i.outlet_psi, span: 3, show: vent },
        { name: "motive_gpm", label: "Water through the venturi at those pressures (GPM)", type: "number", step: "any", value: i.motive_gpm === null || i.motive_gpm === undefined ? "" : i.motive_gpm, show: vent },
        { name: "tank_gal", label: "Most stock solution to mix for this injector (gallons)", type: "number", step: "any", value: i.tank_gal, req: true },
        { name: "flush_min", label: "Plain water at the end of a run (minutes)", type: "number", step: "any", value: i.flush_min },
      ],
      note: "A dosing pump has a dial for the dilution. A venturi has none: it draws a fixed amount that depends on the pressure going in and coming out, so the app works out how strong to make the stock tank for the amount it draws. Read the suction off the maker's performance chart for your two pressures, or measure it: run the zone with the suction line in a jug of plain water, time how long it takes to empty and divide. Throttle the suction valve to draw less. A venturi needs the pressure to fall by about 20 to 25 percent across it. A 5 gallon bucket is easiest to mix at about 4 gallons. With a second injector, tanks on different ones run together. After adding one, use Tanks to say which injector runs which tank.",
      submit: (x) => this._call("set_pump", { garden: g.id, pump: key || undefined, ...x, ...(x.kind === "venturi" ? { motive_gpm: x.motive_gpm === undefined ? null : x.motive_gpm, inlet_psi: x.inlet_psi === undefined ? null : x.inlet_psi, outlet_psi: x.outlet_psi === undefined ? null : x.outlet_psi } : {}) }),
      extra: key && F.pumps.length > 1 ? { label: "Remove this injector", act: () => this._call("remove_pump", { garden: g.id, pump: key }) } : null,
    };
  }
  _fTanks(g) {
    const F = g.irrigation.fert;
    return {
      title: "Which pump runs which tank", submitLabel: "Save",
      fields: F.tank_names.map((t) => ({ name: t, label: t === "acid" ? "Acid tank" : `Tank ${t}`, type: "select", options: F.pumps.map((p) => [p.key, p.name]), value: F.tank_pump[t] || F.first_pump })),
      note: "Tanks on the same pump take turns on separate waterings. Tanks on different pumps can run at the same time, so acid on its own pump can run with a feeding.",
      submit: async (x) => { for (const t of F.tank_names) if (x[t] && x[t] !== (F.tank_pump[t] || F.first_pump)) await this._call("set_tank_pump", { garden: g.id, tank: t, pump: x[t] }); },
    };
  }
  _fAcidLog(g, quick) {
    const A = g.irrigation.acid, t = A.tank, raise = A.mode === "raise";
    return {
      title: raise ? "Log a base application" : "Log an acid application", submitLabel: "Log",
      fields: [
        { name: "date", label: "Date", type: "date", value: "", span: 3 },
        raise ? { name: "g", label: "Base put in the tank (g)", type: "number", step: "any", value: quick && t ? t.g : "", req: true, span: 3 }
          : { name: "ml", label: "Acid put in the tank (mL)", type: "number", step: "any", value: quick && t ? t.ml : "", req: true, span: 3 },
        { name: "water_gal", label: "Water it went into (gal)", type: "number", step: "any", value: quick && t ? A.water_gal : "", span: 3 },
        { name: "ph_before", label: "pH before", type: "number", step: "any", value: quick && A.ph ? A.ph : "", span: 3 },
        { name: "ph_after", label: "pH after (measured at an emitter)", type: "number", step: "any", value: "", span: 3 },
        { name: "notes", label: "Notes", type: "text", value: "" },
      ],
      note: quick ? "Filled in from the calculation. Change anything that was different." : "",
      submit: (x) => this._call("log_acid", { garden: g.id, ...x, product: raise ? A.base_name : undefined }),
    };
  }
  _fSched(g) {
    const F = g.irrigation.fert;
    return {
      title: "Feeding schedule", submitLabel: "Save",
      fields: [{ name: "every_days", label: "Days between feedings", type: "number", step: "1", value: F.every_days, req: true }],
      note: "A feeding runs on one watering. Waterings between feedings use plain water.",
      submit: (x) => this._call("set_fertigation", { garden: g.id, every_days: x.every_days }),
    };
  }
  _fMix(g, key) {
    const m = key ? g.irrigation.fert.mixes.find((x) => x.key === key) : null;
    const mix = key ? g.irrigation.fert.mix && g.irrigation.fert.mix.key === key ? g.irrigation.fert.mix : null : null;
    return {
      title: m ? `Mix: ${m.name}` : "New mix", submitLabel: "Save",
      fields: [
        { name: "name", label: "Name", type: "text", value: m ? m.name : "", req: true, placeholder: "Early growth" },
        { name: "ppm_n", label: "Nitrogen strength, ppm (empty to work it out from the plants)", type: "number", step: "any", value: mix && mix.ppm_n ? mix.ppm_n : "" },
      ],
      note: "A mix is a set of fertilizers in proportion by weight. Add the fertilizers after saving.",
      submit: async (x) => { await this._call("set_fert_mix", { garden: g.id, mix: key || undefined, name: x.name, ppm_n: x.ppm_n === undefined ? null : x.ppm_n }); if (!key) { const f = this._garden(g.id).irrigation.fert; await this._call("set_fertigation", { garden: g.id, active: f.mixes[f.mixes.length - 1].key }); } },
      extra: m && g.irrigation.fert.mixes.length > 1 ? { label: "Remove this mix", act: () => this._call("remove_fert_mix", { garden: g.id, mix: key }) } : null,
    };
  }
  _fComp(g, mix, idx) {
    const F = g.irrigation.fert, cur = F.mix && F.mix.key === mix ? F.mix.components : [];
    const c = idx === undefined ? { name: "", n: "", p: "", k: "", ca: "", mg: "", parts: 1, tank: "A" } : cur[idx];
    return {
      title: idx === undefined ? "Add a fertilizer" : `Fertilizer: ${c.name}`, submitLabel: "Save",
      fields: [
        { name: "name", label: "Name", type: "text", value: c.name, req: true, placeholder: "MasterBlend 4-18-38" },
        { name: "n", label: "Nitrogen (N) %", type: "number", step: "any", value: c.n },
        { name: "p", label: "Phosphate (P2O5) %", type: "number", step: "any", value: c.p },
        { name: "k", label: "Potash (K2O) %", type: "number", step: "any", value: c.k },
        { name: "ca", label: "Calcium %", type: "number", step: "any", value: c.ca },
        { name: "mg", label: "Magnesium %", type: "number", step: "any", value: c.mg },
        { name: "parts", label: "Parts by weight in the mix", type: "number", step: "any", value: c.parts, req: true },
        { name: "tank", label: "Stock tank (letter)", type: "text", value: c.tank },
      ],
      note: "Percentages are what the label says. Parts are the proportion by weight to the other fertilizers in the mix; 2 of MasterBlend, 2 of calcium nitrate and 1 of Epsom salt is 2:2:1. Fertilizers that cannot be mixed strong, like calcium nitrate with sulfates and phosphates, go in different tanks.",
      submit: (x) => this._call("set_fert_component", { garden: g.id, mix, index: idx, name: x.name, n: x.n === undefined ? 0 : x.n, p: x.p === undefined ? 0 : x.p, k: x.k === undefined ? 0 : x.k, ca: x.ca === undefined ? 0 : x.ca, mg: x.mg === undefined ? 0 : x.mg, parts: x.parts, tank: x.tank || "A" }),
      extra: idx === undefined ? null : { label: "Remove", act: () => this._call("remove_fert_component", { garden: g.id, mix, index: idx }) },
    };
  }
  _turnOf(gid) { // how the plan is shown on screen: 0 has the rows up and down, 90 has them sideways. Only this screen's view, not the garden.
    this._turns = this._turns || {};
    if (this._turns[gid] === undefined) { let v = 0; try { v = Number(localStorage.getItem("gt_turn_" + gid)) || 0; } catch (e) { /* no storage */ } this._turns[gid] = v === 90 ? 90 : 0; }
    return this._turns[gid];
  }
  _legend(L) {
    const COL = ["#e5372d", "#2e7d32", "#f28c38", "#8e24aa", "#039be5", "#c0a000", "#795548", "#d81b60"];
    const chips = (L.crops || []).map((c) => {
      const rows = L.rows.filter((r) => r.segments.some((sg) => sg.crop === c.key)).map((r) => r.i + 1);
      const span = !rows.length ? "" : rows.length > 1 && rows[rows.length - 1] - rows[0] === rows.length - 1 ? `rows ${rows[0]}–${rows[rows.length - 1]}` : `row${rows.length > 1 ? "s" : ""} ${rows.join(", ")}`;
      const col = COL[Math.max(0, L.available.findIndex((a) => a.key === c.key)) % COL.length];
      return `<span class="lgd"><i style="background:${col}"></i>${esc(c.name)}${span ? ` · ${span}` : ""}</span>`;
    });
    return chips.length ? `<div class="lgds">${chips.join("")}</div>` : "";
  }
  _layoutSvg(L, g, ro) {
    const COL = ["#e5372d", "#2e7d32", "#f28c38", "#8e24aa", "#039be5", "#c0a000", "#795548", "#d81b60"];
    const color = (k) => COL[Math.max(0, L.available.findIndex((a) => a.key === k)) % COL.length];
    const turn = this._turnOf(g.id), north = (L.rotation || 0) - turn, rot = turn, W = L.width_ft * 12, N = L.length_ft * 12, M = 24; // the plan stays square to the screen; the arrow turns
    const th = rot * Math.PI / 180, cs0 = Math.cos(th), sn0 = Math.sin(th), named = false; // crop names are in the legend under the plan, where they cannot run into each other
    const corners = [[0, 0], [W, 0], [W, N], [0, N]].map(([x, y]) => [x * cs0 - y * sn0, x * sn0 + y * cs0]);
    const ux = corners.map((c) => c[0]), uy = corners.map((c) => c[1]);
    const s = Math.min(300 / (Math.max(...ux) - Math.min(...ux)), 440 / (Math.max(...uy) - Math.min(...uy)));
    const R = (lx, ly) => [(lx * cs0 - ly * sn0) * s, (lx * sn0 + ly * cs0) * s];
    // the crop names sit just outside the start of each row; work out where they go before the picture is sized to hold them
    const labels = [];
    if (named) for (const r of L.rows) if (r.segments.length) {
      const nm = r.segments[0].name + (r.segments.length > 1 ? ` +${r.segments.length - 1}` : ""), t = nm.length > 11 ? nm.slice(0, 10) + "." : nm;
      const [px, py] = R(r.x, 0), ox = sn0, oy = -cs0, wd = t.length * 6.2;
      const anchor = ox > 0.35 ? "start" : ox < -0.35 ? "end" : "middle";
      labels.push({ t, x: px + ox * 7, y: py + oy * 7 + (oy < -0.35 ? -2 : oy > 0.35 ? 9 : 4), anchor, wd, color: color(r.segments[0].crop) });
    }
    let x0 = Math.min(...corners.map((c) => c[0] * s)), x1 = Math.max(...corners.map((c) => c[0] * s));
    let y0 = Math.min(...corners.map((c) => c[1] * s)), y1 = Math.max(...corners.map((c) => c[1] * s));
    for (const l of labels) {
      x0 = Math.min(x0, l.anchor === "start" ? l.x : l.anchor === "end" ? l.x - l.wd : l.x - l.wd / 2); x1 = Math.max(x1, l.anchor === "start" ? l.x + l.wd : l.anchor === "end" ? l.x : l.x + l.wd / 2);
      y0 = Math.min(y0, l.y - 10); y1 = Math.max(y1, l.y + 3);
    }
    const left = M - x0, top = M + 34 - y0, VW = x1 - x0 + 2 * M + 30, VH = y1 - y0 + 2 * M + 34;
    const tf = `translate(${left.toFixed(1)} ${top.toFixed(1)}) rotate(${rot})`;
    const P = (lx, ly) => { const [a, b] = R(lx, ly); return [left + a, top + b]; };
    const total = L.rows.reduce((a, r) => a + r.segments.reduce((b, sg) => b + sg.ys.length * sg.lines.length, 0), 0);
    const dots = total <= 2500, fix = (n) => n.toFixed(1);
    const info = (k) => L.crops.find((c) => c.key === k) || {};
    let o = `<g transform="${tf}"><rect width="${W * s}" height="${N * s}" fill="var(--secondary-background-color)" stroke="var(--line)"/>`;
    let names = "";
    for (const r of L.rows) {
      const x0 = r.x0 * s, sel = !ro && this._selRow === r.i;
      o += `<rect ${ro ? 'pointer-events="none"' : `data-act="lay-row" data-g="${g.id}" data-r="${r.i}" style="cursor:pointer"`} x="${fix(x0)}" y="0" width="${fix(L.row_in * s)}" height="${N * s}" fill="var(--card-background-color)" stroke="${sel ? "var(--primary-color)" : "var(--line)"}" stroke-width="${sel ? 2 : 1}" stroke-dasharray="${sel ? "" : "3 3"}"/>`;
      for (const sg of r.segments) {
        const c = color(sg.crop), cs = info(sg.crop);
        o += `<rect x="${fix(x0)}" y="${fix(sg.start_in * s)}" width="${fix(L.row_in * s)}" height="${fix(sg.len_in * s)}" fill="${c}" fill-opacity="0.16" pointer-events="none"/>`;
        const rad = Math.max(1.6, Math.min(cs.spacing_in * 0.32, 5) * s);
        sg.lines.forEach((lx, li) => {
          const x = lx * s, ys = li % 2 === 1 && sg.ys2.length ? sg.ys2 : sg.ys;
          if (dots) for (const y of ys) {
            o += `<circle cx="${fix(x)}" cy="${fix(y * s)}" r="${fix(rad)}" fill="${c}" pointer-events="none"/>`;
            if (cs.support === "cage") o += `<circle cx="${fix(x)}" cy="${fix(y * s)}" r="${fix(rad + 2)}" fill="none" stroke="var(--primary-text-color)" pointer-events="none"/>`;
          } else o += `<line x1="${x}" x2="${x}" y1="${fix(sg.start_in * s)}" y2="${fix((sg.start_in + sg.len_in) * s)}" stroke="${c}" stroke-width="${fix(Math.max(1.5, rad))}" stroke-dasharray="1 ${Math.max(2, cs.spacing_in * s)}" stroke-linecap="round" pointer-events="none"/>`;
        });
        const stations = []; for (let k = 0; k * (sg.post_ft || cs.post_ft) * 12 <= sg.len_in + 1e-6; k++) stations.push(sg.start_in + k * (sg.post_ft || cs.post_ft) * 12);
        if (cs.support === "tpost") for (const y of stations) o += `<rect x="${fix(r.x * s - 2.5)}" y="${fix(y * s - 2.5)}" width="5" height="5" fill="var(--primary-text-color)" pointer-events="none"/>`;
        if (cs.support === "corral") {
          const half = Math.min(sg.block_w_in, L.row_in - 2) / 2, xa = (r.x - half) * s, xb = (r.x + half) * s, sz = cs.post_kind === "tpost" ? 5 : 3.5;
          o += `<rect x="${fix(xa)}" y="${fix(sg.start_in * s)}" width="${fix(xb - xa)}" height="${fix(sg.len_in * s)}" fill="none" stroke="#b8860b" stroke-width="1.6" stroke-dasharray="4 2" pointer-events="none"/>`;
          for (const y of stations) for (const px of [xa, xb]) o += `<rect x="${fix(px - sz / 2)}" y="${fix(y * s - sz / 2)}" width="${sz}" height="${sz}" fill="var(--primary-text-color)" pointer-events="none"/>`;
        }
      }
    }
    for (const l of labels) names += `<text class="ax" x="${fix(left + l.x)}" y="${fix(top + l.y)}" font-size="11" fill="${l.color}" text-anchor="${l.anchor}" pointer-events="none">${esc(l.t)}</text>`;
    const nx = -Math.sin(north * Math.PI / 180), ny = -Math.cos(north * Math.PI / 180), ax = VW - 26, ay = 28;
    names += `<g pointer-events="none"><circle cx="${fix(ax)}" cy="${fix(ay)}" r="19" fill="none" stroke="var(--line)"/><path d="M${fix(ax - nx * 12)} ${fix(ay - ny * 12)} L${fix(ax + nx * 13)} ${fix(ay + ny * 13)} M${fix(ax + nx * 13 + (nx * 0.55 - ny * 0.55) * -6)} ${fix(ay + ny * 13 + (ny * 0.55 + nx * 0.55) * -6)} L${fix(ax + nx * 13)} ${fix(ay + ny * 13)} L${fix(ax + nx * 13 + (nx * 0.55 + ny * 0.55) * -6)} ${fix(ay + ny * 13 + (ny * 0.55 - nx * 0.55) * -6)}" stroke="var(--primary-text-color)" stroke-width="1.8" fill="none" stroke-linecap="round" stroke-linejoin="round"/><text class="ax" x="${fix(ax + nx * 26)}" y="${fix(ay + ny * 26 + 4)}" font-size="11" font-weight="600" text-anchor="middle" fill="var(--primary-text-color)">N</text></g>`;
    return `<svg viewBox="0 0 ${fix(VW)} ${fix(VH)}" width="100%" style="max-width:${Math.round(VW * 1.15)}px;display:block;margin:0 auto" role="img" aria-label="Garden layout, ${L.totals.rows} rows">${o}</g>${names}</svg>`;
  }
  _layoutView(g) {
    const gid = g.id, hist = g.layout_history || {}, years = Object.keys(hist).sort();
    const past = this._season && hist[this._season] ? this._season : null;
    const L = past ? hist[past] : g.layout, ok = L.configured;
    let h = `<div class="hd">${this._btn("back", "arrow-left", "", "", "ic")}<div class="grow"><div class="ttl">Layout planner</div><div class="sub">${esc(g.name)}${past ? `, ${past} (last season, view only)` : ok ? `, ${L.year}` : ""}</div></div></div>`;
    if (years.length && ok) {
      h += `<div class="chips">${years.map((y) => `<button class="chip ${past === y ? "on" : ""}" data-act="lay-season" data-g="${gid}" data-y="${y}">${y}</button>`).join("")}<button class="chip ${past ? "" : "on"}" data-act="lay-season" data-g="${gid}" data-y="">${g.layout.year}</button></div>`;
    }
    const dim = (k, label, v, span = 3, min = 1) => `<div style="grid-column:span ${span}"><label>${label}</label><input type="number" inputmode="decimal" min="${min}" max="500" step="any" value="${v}" data-lay="${k}" data-g="${gid}"></div>`;
    if (!ok) {
      h += `<div class="card"><div class="sec">Garden size</div><div class="grid6">${dim("length_ft", "Row length (ft)", 20)}${dim("width_ft", "Depth (ft)", 20)}</div><div class="small mut" style="margin:8px 0">Rows run along the row length and are stacked across the depth, with a 24 in access path between them.</div><div class="row">${this._btn("lay-start", "plus", "Start planning", `data-g="${gid}"`, "primary")}</div></div>`;
      return h;
    }
    const t = L.totals;
    const M = {};
    if (!past) {
      M.size0 = h.length;
      h += `<div class="card"><div class="sec">Garden size</div><div class="grid6">${dim("length_ft", "Row length (ft)", num(L.length_ft, 2))}${dim("width_ft", "Depth (ft)", num(L.width_ft, 2))}${dim("path_in", "Access path between rows (in)", num(L.path_in, 1), 6, 0)}</div>`;
      h += `<label style="margin-top:10px">Row width</label><div class="seg">${L.row_widths.map((n) => `<button class="${L.row_in === n ? "on" : ""}" data-act="lay-rowin" data-g="${gid}" data-n="${n}">${n} in</button>`).join("")}</div>`;
      h += `<div class="small mut" style="margin-top:8px">Fits ${t.rows} row${t.rows === 1 ? "" : "s"} of ${L.row_in} in with ${num(L.path_in, 0)} in paths between them. Each crop has its own pattern: a single line, a double line or an offset grid.</div></div>`;
      M.size1 = h.length;
      if (false) h += `<div class="card">` + (L.warnings || []).map((w) => `<div class="alarm" style="--hold:var(${w.strong ? "--error-color,#db4437" : "--spray"})"><div class="small"${w.strong ? ' style="font-weight:700"' : ""}>${this._icon("alert")} ${esc(w.text)}</div></div>`).join("") + `</div>`;
      M.warn1 = h.length;
      if (L.alerts.length) {
        h += `<div class="card"><div class="sec">Crop rotation</div>`;
        h += L.alerts.map((a) => `<div class="alarm" ${a.level === "family" ? 'style="--hold:var(--spray)"' : a.level === "resistant" ? 'style="--hold:var(--ok)"' : ""}><b>${this._icon(a.level === "resistant" ? "check" : "alert")} ${esc(a.name)}${a.variety ? ` (${esc(a.variety)})` : ""}, row ${a.row + 1}</b><div class="small" style="margin-top:4px">${esc(a.text)}</div></div>`).join("");
        h += `<div class="small mut">Rest times follow <a href="${L.rotation_sources[0]}" target="_blank" rel="noopener">WSU Extension</a> and <a href="${L.rotation_sources[1]}" target="_blank" rel="noopener">Cornell Vegetable MD Online</a>.</div></div>`;
      }
      M.rot1 = h.length;
      const brush = this._brushFor(L), cur = L.available.find((a) => a.key === brush), d = L.draft && L.draft.crop === brush ? L.draft : null;
      const mode = (d && d.mode) || "weight";
      h += `<div class="card"><div class="sec">Plan a crop</div><div class="row wrap" style="margin-bottom:10px"><div class="grow" style="min-width:140px">${this._brushFind(L, gid, brush)}</div>${this._btn("lay-edit", "pencil", "Spacing", `data-g="${gid}" data-c="${esc(brush)}"`)}</div>`;
      const names = [...new Set([...(this._snap.variety_traits || []).filter((t) => t.crop === brush).map((t) => t.name), ...this._snap.varieties.filter((v) => v.species === brush).map((v) => v.name)])];
      const vr = (d && d.variety) || "";
      h += `<label>Variety (optional)</label><div class="row" style="margin-bottom:10px"><div class="grow"><input type="text" list="vl" placeholder="Roma VF" value="${esc(vr)}" data-dvar data-g="${gid}"><datalist id="vl">${names.map((n) => `<option value="${esc(n)}"></option>`).join("")}</datalist></div>${this._btn("lay-traits", "pencil", "Height and resists", `data-g="${gid}"`)}</div>`;
      if (d && d.resist && d.resist.length) h += `<div class="small mut" style="margin:-4px 0 10px">${esc(vr)} resists ${esc(d.resist.map((k) => (cur.diseases.find((x) => x.key === k) || { name: k }).name).join(", "))}. Rotation alerts allow for that.</div>`;
      if (cur.min_row_in && L.row_in < cur.min_row_in) h += `<div class="alarm" style="--hold:var(--spray)"><div class="small">${this._icon("alert")} ${esc(cur.name)} is pollinated by wind, so it needs a block at least ${cur.min_row_in / 12} ft across. Your rows are ${L.row_in} in wide: set the row width to ${cur.min_row_in} in, or grow it where the rows are ${cur.min_row_in} in.</div></div>`;
      if (d && d.height_ft) h += `<div class="small mut" style="margin:-4px 0 10px">${vr ? esc(vr) : esc(cur.name)} grows about ${num(d.height_ft, 1)} ft tall, which is what the shade check uses.</div>`;
      h += `<div class="seg">${[["weight", "Harvest weight"], ["plants", "Plants"], ["length", "Row length"]].map(([m, t2]) => `<button class="${mode === m ? "on" : ""}" data-act="lay-mode" data-g="${gid}" data-m="${m}">${t2}</button>`).join("")}</div>`;
      const lab = { weight: "Pounds you want to harvest", plants: "Number of plants", length: "Feet of row" }[mode];
      h += `<div class="grid6" style="margin-top:10px"><div style="grid-column:span 6"><label>${lab}</label><input type="number" inputmode="decimal" min="0" step="any" value="${d && d.value ? num(d.value, 2) : ""}" data-draft="value" data-g="${gid}"></div>`;
      if (mode === "weight") h += `<div style="grid-column:span 3"><label>Pounds per plant</label><input type="number" inputmode="decimal" min="0" step="any" value="${cur.yield_lb ? num(cur.yield_lb, 3) : ""}" data-draft="yield_lb" data-g="${gid}"></div>`;
      h += `<div style="grid-column:span ${mode === "weight" ? 3 : 6}"><label>Inches between plants</label><input type="number" inputmode="decimal" min="1" step="any" value="${num(cur.spacing_in, 2)}" data-draft="spacing_in" data-g="${gid}"></div></div>`;
      h += `<div class="small mut" style="margin-top:6px">${esc(cur.name)}: ${this._layDesc(L, cur)}${cur.support === "tpost" ? `, T-post every ${num(cur.post_ft, 1)} ft` : cur.support === "cage" ? ", one cage each" : cur.support === "corral" ? `, ${cur.post_kind === "tpost" ? "T-post" : "stake"} corral every ${num(cur.post_ft, 1)} ft with ${cur.twine_levels} twine line${cur.twine_levels === 1 ? "" : "s"}` : ""}</div>`;
      if (d && d.ready) {
        h += `<div class="stats" style="margin-top:10px">${d.plants_needed ? `<div class="stat"><span>Plants needed</span><b>${d.plants_needed}</b></div>` : ""}<div class="stat"><span>Row length</span><b>${num(d.length_ft, 1)} ft</b></div><div class="stat"><span>Plants that fit</span><b>${d.plants}</b></div>${d.est_lb ? `<div class="stat"><span>Harvest</span><b>${num(d.est_lb, 1)} lb</b></div>` : ""}</div>`;
        h += `<div class="small mut" style="margin-top:6px">${d.plants} plants in ${num(d.length_ft, 1)} ft of ${L.row_in} in row (${d.lines} line${d.lines === 1 ? "" : "s"})${d.rows > 1 ? `, which is ${num(d.rows, 1)} rows` : ""}.</div>`;
        const opts = L.rows.map((r) => { const f = d.flags[r.i]; return `<option value="${r.i}" ${String(this._placeRow || "0") === String(r.i) ? "selected" : ""}>Row ${r.i + 1}${r.used_ft ? `, ${num(r.used_ft, 1)} ft planted` : ", empty"}${f ? ` (${f.level === "same" ? "same crop" : f.level === "resistant" ? "resistant" : "shared disease"}: ${f.text})` : ""}</option>`; }).join("");
        h += `<div class="grid6" style="margin-top:10px"><div style="grid-column:span 4"><label>Put it in</label><select data-placerow>${opts}</select></div><div style="grid-column:span 2"><label>Start (ft)</label><input type="number" inputmode="decimal" min="0" step="any" placeholder="0" value="${esc(this._placeStart || "")}" data-placestart></div></div>`;
        h += `<div class="row" style="margin-top:10px">${this._btn("lay-place", "plus", "Add to garden", `data-g="${gid}"`, "primary grow")}</div>`;
      } else if (d && d.need) {
        h += `<div class="small mut" style="margin-top:10px">${{ value: "Enter an amount to see how much row it needs.", yield: "Enter the pounds each plant should give to turn weight into plants.", size: "That is more than the garden can hold." }[d.need]}</div>`;
      } else h += `<div class="small mut" style="margin-top:10px">Enter an amount to see how much row it needs.</div>`;
      h += `</div>`;
      M.crop1 = h.length;
    }
    M.lay0 = h.length;
    h += `<div class="card"><div class="sec">${past ? `${past} layout` : "Plan"}</div>${past ? "" : `<div class="small mut" style="margin:-4px 0 8px">Tap a row to plant it with the crop chosen under Plan a crop, or enter feet to plant part of a row.</div>`}`;
    if (!past) {
      const brush = this._brushFor(L);
      h += `<label>Feet of the row to plant (leave empty for the whole row)</label><input type="number" inputmode="decimal" min="0.5" step="any" placeholder="Whole row" value="${esc(this._brushLen || "")}" data-brushlen style="margin-bottom:10px">`;
    }
    h += this._layoutSvg(L, g, !!past) + this._legend(L);
    if (!past) h += this._shadeWarn(L.sun);
    const SU = L.sun, rotv = L.rotation || 0;
    h += `<div class="row" style="justify-content:center;margin-top:6px">${this._btn("lay-view", "restore", this._turnOf(gid) === 90 ? "Show the rows up and down" : "Show the rows sideways", `data-g="${gid}"`)}</div>`;
    h += `<div class="small mut" style="margin-top:6px;text-align:center">${num(L.length_ft, 1)} ft row length, ${num(L.width_ft, 1)} ft deep. Rows run ${esc(SU.runs)}, row 1 is on the ${esc(SU.x_side)} side and they start at the ${esc(SU.start_end)} end.</div>`;
    const sel = !past && this._selRow !== null && this._selRow !== undefined ? L.rows[this._selRow] : null;
    if (sel) {
      h += `<div class="card" style="margin:10px 0 0"><div class="row"><div class="sec grow" style="margin:0">Row ${sel.i + 1}: ${num(sel.used_ft, 1)} of ${num(L.length_ft, 1)} ft planted</div>${sel.segments.length ? this._btn("lay-row-clear", "", "Clear row", `data-g="${gid}" data-r="${sel.i}"`) : ""}</div>`;
      if (!sel.segments.length) h += `<div class="small mut" style="margin-top:6px">Empty. Tap the row to plant it. To split it between crops, enter feet above and tap once for each crop, or use Plan a crop and pick where it goes.</div>`;
      sel.segments.forEach((sg, k) => { h += `<div class="lg"><div class="t">${esc(sg.name)}${sg.variety ? ` (${esc(sg.variety)})` : ""}<span>${num(sg.start_in / 12, 1)} to ${num((sg.start_in + sg.len_in) / 12, 1)} ft, ${sg.plants} plants</span></div>${this._btn("lay-seg-rm", "close", "", `data-g="${gid}" data-r="${sel.i}" data-i="${k}"`, "ic")}</div>`; });
      h += `</div>`;
    }
    M.ang0 = h.length;
    if (!past) {
      const chip = (n, t) => `<button class="chip ${Math.abs(rotv - n) < 0.05 ? "on" : ""}" data-act="lay-ang" data-g="${gid}" data-n="${n}">${t}</button>`;
      h += `<div class="card" style="margin-top:10px"><div class="sec">Which way the rows run</div><div class="row" style="align-items:end;gap:10px"><div style="flex:1"><label>Degrees off north</label><input type="number" inputmode="decimal" step="any" min="0" max="360" value="${num(rotv, 1)}" data-lay="rotation" data-g="${gid}"></div></div><div class="chips" style="margin:8px 0 0">${chip(0, "North-south (0)")}${chip(90, "East-west (90)")}${chip(45, "45")}${chip(135, "135")}${chip(180, "180")}${chip(270, "270")}</div><div class="small mut" style="margin-top:6px">Any angle works. 0 runs rows north-south, 90 east-west, and an angle between runs them across the compass. The plan stays square to the screen, and the arrow in its corner points to north.</div></div>`;
      h += this._sunCard(L, gid);
    }
    M.fill0 = h.length;
    if (!past) h += `<div class="row" style="margin-top:10px">${this._btn("lay-fill", "", "Fill every row", `data-g="${gid}"`, "grow")}${this._btn("lay-clear", "", "Clear rows", `data-g="${gid}"`)}</div>`;
    h += `</div>`;
    M.end = h.length;
    if (!past) {
      const sl = (a, b) => h.slice(a, b), acc = (k, title, sum, body, open) => {
        const on = (this._acc || {})[k] ?? open;
        return `<div class="card tile" data-act="acc" data-k="${k}"><div class="row"><div class="grow" style="font-size:15px;font-weight:600">${title}</div><span class="small mut">${esc(sum)}</span>${this._icon(on ? "chevron-up" : "chevron-right")}</div></div>` + (on ? body : "");
      };
      const warn = (L.warnings || []).map((w) => `<div class="warn ${w.strong ? "bad" : ""}"><div class="wt">${esc(w.title || "Check this")}</div><div class="wb">${esc(w.short || w.text)}</div>${w.action ? `<button class="wa" data-act="lay-rowin" data-g="${gid}" data-n="${w.action.n}">${esc(w.action.label)}</button>` : ""}${w.short && w.short !== w.text ? `<details><summary>Why, and what to do instead</summary><div class="wb" style="margin-top:6px">${esc(w.text)}</div></details>` : ""}</div>`).join("");
      const brushName = ((L.available || []).find((a) => a.key === this._brushFor(L)) || {}).name || "";
      h = h.slice(0, M.size0) + sl(M.lay0, M.ang0) + sl(M.fill0, M.end) + warn + sl(M.warn1, M.rot1)
        + acc("crop", "Plan a crop", brushName, sl(M.rot1, M.crop1), true)
        + acc("rows", "Rows and angle", `${num(rotv, 0)}°, ${L.row_in} in`, sl(M.ang0, M.fill0), false)
        + acc("size", "Garden size", `${num(L.length_ft, 0)} × ${num(L.width_ft, 0)} ft`, sl(M.size0, M.size1), false);
    }
    h += `<div class="card"><div class="sec">What you need</div><div class="stats"><div class="stat"><span>Plants</span><b>${t.plants}</b></div><div class="stat"><span>Per sq ft</span><b>${num(t.density, 2)}</b></div><div class="stat"><span>Rows planted</span><b>${t.planted_rows} of ${t.rows}</b></div><div class="stat"><span>T-posts</span><b>${t.posts}</b></div><div class="stat"><span>Stakes</span><b>${t.stakes}</b></div><div class="stat"><span>Twine</span><b>${num(t.twine_ft, 0)} ft</b></div><div class="stat"><span>Cages</span><b>${t.cages}</b></div><div class="stat"><span>Garden area</span><b>${num(t.area_sqft, 0)} sq ft</b></div></div>`;
    if (t.planted_rows) h += `<div class="small mut" style="margin-top:8px">Inside the planted rows it is ${num(t.bed_density, 2)} plants per sq ft.</div>`;
    if (L.crops.length) {
      h += `<table class="tbl" style="margin-top:10px"><tr><th>Crop</th><th>Planted</th><th>Plants</th><th>Support</th></tr>`;
      for (const c of L.crops) h += `<tr><td>${esc(c.name)}<div class="small mut">${this._layDesc(L, c)}</div></td><td>${num(c.feet, 1)} ft<div class="small mut">${c.rows} row${c.rows === 1 ? "" : "s"}</div></td><td>${c.plants}</td><td>${c.support === "tpost" ? `${c.posts} T-posts` : c.support === "cage" ? `${c.cages} cages` : c.support === "corral" ? `${c.posts || c.stakes} ${c.posts ? "T-posts" : "stakes"}, ${num(c.twine_ft, 0)} ft twine` : "none"}</td></tr>`;
      h += `</table>`;
    }
    h += `<div class="small mut" style="margin-top:8px">T-posts go at both ends of a planted section and then at the spacing set for the crop. A double line shares one set of posts down its middle. A corral puts a post on each side at every station, with twine run along both sides and across the ends.</div></div>`;
    if (!past && ((L.to_plant || []).length || L.tracked_plants)) {
      h += `<div class="card"><div class="sec">Plant this layout</div>`;
      if (L.to_plant.length) {
        h += L.to_plant.map((x) => `<div class="row small" style="margin:4px 0"><div class="grow"><b>${esc(x.variety || x.name)}</b>${x.variety ? ` <span class="mut">${esc(x.name)}</span>` : ""}<div class="mut">Row${x.rows.length === 1 ? "" : "s"} ${x.rows.join(", ")}</div></div><b>${x.plants} plants</b></div>`).join("");
        h += `<div class="small mut" style="margin:6px 0">Adds each crop to your plants in ${esc(g.name)} with this many plants, so you can track feeding, sprays and harvests. Rows already planted${L.tracked_plants ? ` (${L.tracked_plants} plants)` : ""} are left alone.</div>`;
        h += `<div class="row">${this._btn("lay-plant", "sprout", "Plant and track these", `data-g="${gid}"`, "primary grow")}</div>`;
      } else h += `<div class="pill ok" style="margin:0">All ${L.tracked_plants} plants are planted and tracked</div>`;
      h += `</div>`;
    }
    if (!past) {
      h += `<div class="card">${this._confirm === "season" ? `<div class="conf">Keep ${L.year}'s layout and start ${L.year + 1} with empty rows? ${L.year}'s layout stays here to look up, and your rotation is checked against it.<div class="row"><button data-act="cancel-del">Not yet</button><button class="primary" data-act="do-season" data-g="${gid}">Start ${L.year + 1}</button></div></div>` : `<button data-act="ask-season">Start the ${L.year + 1} season</button>`}</div>`;
      h += `<div class="card">${this._confirm === "lay" ? `<div class="conf">Remove this season's layout? Your plants are not affected.<div class="row"><button data-act="cancel-del">Keep</button><button class="danger" data-act="do-lay" data-g="${gid}">Remove</button></div></div>` : `<button class="danger" data-act="ask-lay">Remove layout</button>`}</div>`;
    }
    return h;
  }
  _fTraits(g, crop, variety) {
    const L = g.layout, c = L.available.find((a) => a.key === crop);
    const have = (name) => (this._snap.variety_traits || []).find((t) => t.crop === crop && t.name.toLowerCase() === name.toLowerCase());
    const cur = have(variety) || {};
    const fields = [{ name: "variety", label: "Variety", type: "text", req: true, value: variety, placeholder: "Roma VF" }];
    if (c.habits.length) fields.push({ name: "habit", label: "Growth habit", type: "select", options: [["", `Usual for ${c.name.toLowerCase()} (${num(c.height_ft, 1)} ft)`], ...c.habits.map((h) => [h.key, `${h.name} (${num(h.height, 1)} ft)`])], value: cur.habit || "" });
    fields.push({ name: "height_ft", label: `Height when grown (ft), empty for ${c.habits.length ? "the habit's" : "the usual"} height`, type: "number", step: "any", value: cur.height_ft && !cur.habit ? cur.height_ft : "" });
    fields.push({ name: "resist", label: "Resistant to (tap the letters on the seed packet)", type: "multi", options: c.diseases.map((x) => [x.key, x.code ? `${x.name} (${x.code})` : x.name]), value: (cur.resist || []).join(",") });
    return {
      title: `${c.name}: height and resistance`, submitLabel: "Save", fields,
      note: "Height decides which crops shade which: a determinate tomato or a bush bean stays low, while a vining tomato, a climbing bean or hops can tower over their neighbours. A resistant variety can follow its own family sooner, because the diseases it resists are left out of the rotation wait. It lowers the risk but does not remove it.",
      submit: async (x) => {
        const hab = (c.habits || []).find((h) => h.key === x.habit);
        await this._call("set_variety_traits", { crop, variety: x.variety, resist: (x.resist || "").split(",").filter(Boolean), habit: x.habit || null, height_ft: x.height_ft || (hab ? hab.height : null) });
        await this._call("set_layout_draft", { garden: g.id, crop, variety: x.variety });
      },
    };
  }
  _fLayCrop(g, key) {
    const L = g.layout, c = L.available.find((a) => a.key === key);
    return {
      title: `Spacing: ${c.name}`, submitLabel: "Save",
      note: c.post_rec && c.post_rec.length ? `Recommended post spacing: ${c.post_rec.map((r) => `${num(r.post_ft, 1)} ft for ${r.habit.toLowerCase()}`).join(", ")}. It follows the growth habit set on the variety, and a spacing you enter here replaces it.` : undefined,
      fields: [
        { name: "pattern", label: "How the plants sit across the row", type: "select", options: Object.entries(L.patterns), value: c.pattern },
        { name: "spacing_in", label: "Inches between plants", type: "number", step: "any", value: c.spacing_in, req: true },
        { name: "stagger", label: "The two lines", type: "select", options: [["0", "Side by side"], ["1", "Staggered"]], value: c.stagger ? "1" : "0", show: (v) => v.pattern === "double" },
        { name: "yield_lb", label: "Pounds harvested per plant (optional)", type: "number", step: "any", value: c.yield_lb || "" },
        { name: "height_ft", label: "Full-grown height (ft), for shade", type: "number", step: "any", value: c.height_ft },
        { name: "support", label: "Support", type: "select", options: Object.entries(L.supports), value: c.support },
        { name: "post_kind", label: "Corral posts", type: "select", options: Object.entries(L.totals.post_kinds), value: c.post_kind, show: (v) => v.support === "corral" },
        { name: "post_ft", label: `Feet between posts${c.post_rec && c.post_rec.length ? " (empty for the recommended)" : ""}`, type: "number", step: "any", value: c.post_set || !(c.post_rec && c.post_rec.length) ? c.post_ft : "", show: (v) => v.support === "tpost" || v.support === "corral" },
        { name: "twine_levels", label: "Lines of twine up the posts", type: "number", step: "1", value: c.twine_levels, show: (v) => v.support === "corral" },
      ],
      submit: (x) => this._call("set_layout_crop", { garden: g.id, crop: key, spacing_in: x.spacing_in, support: x.support, post_ft: Number.isFinite(Number(x.post_ft)) && x.post_ft !== "" && x.post_ft != null ? x.post_ft : 0, post_kind: x.post_kind, twine_levels: x.twine_levels, pattern: x.pattern, stagger: x.pattern === "double" ? x.stagger === "1" : undefined, yield_lb: x.yield_lb, height_ft: x.height_ft }),
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
        { name: "value", label: "pH", type: "number", step: "0.01", req: true, span: 3 },
        { name: "date", label: "Date", type: "date", value: this._snap.today, span: 3 },
      ],
      note: "From a test kit or lab report.",
      submit: (x) => this._call("log_ph", { garden: g.id, ...x }),
    };
  }
  _fEndSeason(g) {
    const live = this._vars().filter((v) => v.garden === g.id && !v.archived && v.kind !== "tree");
    const presets = g.cover.presets;
    return {
      title: `End the season: ${g.name}`, submitLabel: "End season",
      fields: [
        { name: "date", label: "Date", type: "date", value: this._snap.today, span: 3 },
        { name: "cover_crop", label: "Sow a cover crop now", type: "select", options: [["", "None"], ...presets.map((p) => [p, p])], value: "", span: 3 },
        { name: "notes", label: "Notes for next year", type: "textarea", placeholder: "What worked, what to change" },
      ],
      preview: () => `<div class="small mut">${live.length} planting${live.length === 1 ? "" : "s"} move to Past plants: ${live.map((v) => esc(v.name)).join(", ") || "none"}. Harvests, fertilizer, and notes are kept. Trees stay in the garden.</div>`,
      note: "Use this at the end of the growing season. Soil pH, sensor history, and adjuncts stay with the garden.",
      submit: (x) => this._call("end_season", { garden: g.id, ...x }),
    };
  }
  _fCover(g) {
    const presets = g.cover.presets;
    return {
      title: `Cover crop: ${g.name}`, submitLabel: "Add",
      fields: [
        { name: "pick", label: "Cover crop", type: "select", options: [...presets.map((p) => [p, p]), ["__other__", "Other..."]], value: presets[0] },
        { name: "custom", label: "Name", type: "text", req: true, show: (v) => v.pick === "__other__", placeholder: "Daikon radish, oats" },
        { name: "sown_date", label: "Sown", type: "date", value: this._snap.today, span: 3 },
        { name: "amount_lbs", label: "Seed (lb), for mix ratio", type: "number", step: "0.1", span: 3 },
        { name: "wait_days", label: "Wait after terminating (days)", type: "number", step: "1", value: 21, span: 3 },
        { name: "notes", label: "Notes", type: "text", placeholder: "Seeding rate, bed" },
      ],
      note: "The wait is how long to leave the bed alone after terminating before planting. Three weeks is the usual rule.",
      submit: (x) => { const { pick, custom, ...rest } = x; return this._call("add_cover_crop", { garden: g.id, ...rest, crop: pick === "__other__" ? custom : pick }); },
    };
  }
  _fTerminate(g, id) {
    const all = id === "__all__" ? g.cover.items.filter((x) => x.state === "growing") : null;
    const i = all ? { crop: all.map((x) => x.crop).join(" + "), wait_days: Math.max(...all.map((x) => x.wait_days)) } : (g.cover.items.find((x) => x.id === id) || {});
    return {
      title: `Terminate ${i.crop || "cover crop"}`, submitLabel: "Terminate",
      fields: [
        { name: "date", label: "Date terminated", type: "date", value: this._snap.today, span: 3 },
        { name: "method", label: "How (tap each one in the order you do it)", type: "multi", options: Object.entries(COVER_TEXT), value: "mowed" },
        { name: "notes", label: "Notes", type: "text" },
      ],
      preview: (x) => (x.method && x.method.includes(",") ? `<div class="small mut" style="margin-bottom:6px">Order: ${esc(x.method.split(",").map((m) => COVER_TEXT[m] || m).join(" → "))}</div>` : "") + (x.date ? `<div class="pill ok">Plant after ${fmtDate(this._isoAdd(x.date, i.wait_days || 21), true)} (${i.wait_days || 21} days)</div>` : ""),
      submit: async (x) => { for (const c of all || [{ id }]) await this._call("terminate_cover_crop", { garden: g.id, cover: c.id, ...x, method: x.method ? String(x.method).split(",").filter(Boolean) : undefined }); },
    };
  }
  _fMetric(g, key) {
    const m = g.metrics[key], u = m.unit;
    return {
      title: `Log ${m.name.toLowerCase()}: ${g.name}`, submitLabel: "Log",
      fields: [
        { name: "value", label: `${m.name} (${u})`, type: "number", step: key === "ec" ? "0.01" : key === "par" ? "1" : "0.1", req: true, span: 3 },
        { name: "date", label: "Date", type: "date", value: this._snap.today, span: 3 },
      ],
      note: key === "ec" ? "EC in mS/cm (same as dS/m)." : key === "soil_temp" ? "Soil temperature in °F." : key === "air_temp" ? "Air temperature in °F." : key === "out_temp" ? "Outside air temperature in °F." : key === "par" ? "Light in µmol/m²/s." : "",
      submit: (x) => this._call("log_garden_reading", { garden: g.id, metric: key, ...x }),
    };
  }
  _sensorCandidates(key, selected) {
    const st = (this._hass && this._hass.states) || {};
    const out = [];
    for (const [id, s] of Object.entries(st)) {
      if (!id.startsWith("sensor.")) continue;
      const a = s.attributes || {}, dc = a.device_class, unit = String(a.unit_of_measurement || "").toLowerCase();
      const ok = key === "par" ? dc === "illuminance" || /par|ppfd|photosynth|micromol|µmol/.test(id + unit)
        : key === "soil_temp" || key === "air_temp" || key === "out_temp" ? dc === "temperature" || /^°?[cf]$/.test(unit) || /soil.*temp|temp.*soil/.test(id)
        : key === "ec" ? dc === "conductivity" || /s\/cm|ds\/m|s\/m/.test(unit) || /(^|_)ec(_|$)|conductiv/.test(id)
        : dc === "moisture" || /moisture/.test(id);
      if (ok || selected.includes(id)) out.push([id, `${a.friendly_name || id}${s.state && s.state !== "unknown" ? ` (${s.state}${a.unit_of_measurement ? " " + a.unit_of_measurement : ""})` : ""}`]);
    }
    return out.sort((p, q) => p[1].localeCompare(q[1]));
  }
  _fSensors(g, key) {
    const m = g.metrics[key];
    return {
      title: `${m.name} sensors: ${g.name}`, submitLabel: "Save",
      fields: [
        { name: "pick", label: "Tap every sensor to include", type: "multi", options: this._sensorCandidates(key, m.entities), value: m.entities.join(",") },
        { name: "extra", label: "Other entity ids (comma separated)", type: "text", placeholder: "sensor.bed_3_moisture" },
      ],
      note: key === "out_temp" ? "Pick a sensor out in the open, in the shade, for the outside air. With several, Garden Tracker uses their average. Leave all empty to use your main outdoor temperature sensor from the integration's settings." : "With several sensors, the garden uses their average. Leave all empty to log by hand. Today's low and high are tracked as readings come in.",
      submit: (x) => this._call("set_garden_sensors", { garden: g.id, metric: key, entities: [...String(x.pick || "").split(","), ...String(x.extra || "").split(",")].map((e) => e.trim()).filter(Boolean) }),
    };
  }
  _findEntry(kind, parent, id) {
    const v = this._variety(parent), g = this._garden(parent);
    const mh = (k) => (g && g.metrics[k] ? g.metrics[k].history : undefined);
    const list = { acid: g && g.irrigation && g.irrigation.acid_log.entries, harvest: v && v.harvests, fertilizer: v && v.fertilizations, spray: v && v.sprays, review: v && v.reviews, upotted: v && v.upotted, adjunct: g && g.adjunct_log, ph: g && g.ph.history, moisture: mh("moisture"), ec: mh("ec"), soil_temp: mh("soil_temp"), air_temp: mh("air_temp"), par: mh("par"), water: g && g.water.log, cover: g && g.cover.items }[kind];
    return (list || []).find((e) => e.id === id) || {};
  }
  _fEntry(kind, parent, id) {
    const e = this._findEntry(kind, parent, id), g = this._garden(parent);
    const F = {
      harvest: [{ name: "lbs", label: "Pounds", type: "number", step: "0.1", value: e.lbs, req: true, span: 3 }, { name: "date", label: "Date", type: "date", value: e.date, span: 3 }, { name: "notes", label: "Notes", type: "text", value: e.notes }],
      fertilizer: [{ name: "product", label: "Product", type: "text", value: e.product, req: true }, { name: "n", label: "N", type: "number", step: "0.1", value: e.n, span: 2 }, { name: "p", label: "P", type: "number", step: "0.1", value: e.p, span: 2 }, { name: "k", label: "K", type: "number", step: "0.1", value: e.k, span: 2 }, { name: "date", label: "Date", type: "date", value: e.date }, { name: "notes", label: "Notes", type: "text", value: e.notes }],
      prune: [{ name: "outcome", label: "What happened", type: "chips", options: [["pruned", "Pruned"], ["skipped", "No pruning needed"]], value: e.outcome }, { name: "date", label: "Date", type: "date", value: e.date }, { name: "notes", label: "Notes", type: "text", value: e.notes }],
      spray: [{ name: "product", label: "Product", type: "text", value: e.product, req: true }, { name: "target", label: "Target pest", type: "text", value: e.target }, { name: "date", label: "Date", type: "date", value: e.date }, { name: "phi_days", label: "Days before harvest", type: "number", step: "1", value: e.phi_days, span: 3 }, { name: "reapply_days", label: "Reapply after days", type: "number", step: "1", value: e.reapply_days, span: 3 }],
      review: [{ name: "notes", label: "Note", type: "textarea", value: e.notes, req: true }, { name: "year", label: "Season", type: "number", step: "1", value: e.year }],
      upotted: [{ name: "date", label: "Date", type: "date", value: e.date }],
      adjunct: [{ name: "type", label: "Adjunct", type: "select", options: g ? g.adjuncts.map((a) => [a.key, a.name]) : [], value: e.type }, { name: "date", label: "Date", type: "date", value: e.date, span: 3 }, { name: "amount", label: "Amount", type: "text", value: e.amount, span: 3 }, { name: "product", label: "Product", type: "text", value: e.product }, { name: "notes", label: "Notes", type: "text", value: e.notes }],
      ph: [{ name: "value", label: "pH", type: "number", step: "0.1", value: e.value, req: true, span: 3 }, { name: "date", label: "Date", type: "date", value: e.date, span: 3 }],
      cover: [{ name: "crop", label: "Cover crop", type: "text", value: e.crop, req: true }, { name: "amount_lbs", label: "Seed (lb)", type: "number", step: "0.1", value: e.amount_lbs }, { name: "sown", label: "Sown", type: "date", value: e.sown, span: 3 }, { name: "terminated", label: "Terminated", type: "date", value: e.terminated, span: 3 }, { name: "method", label: "How terminated (tap in the order done)", type: "multi", options: Object.entries(COVER_TEXT), value: (e.methods || []).join(",") }, { name: "wait_days", label: "Wait after terminating (days)", type: "number", step: "1", value: e.wait_days, span: 3 }, { name: "notes", label: "Notes", type: "text", value: e.notes }],
      water: [{ name: "date", label: "Date", type: "date", value: e.date }, { name: "notes", label: "Notes", type: "text", value: e.notes }],
      acid: [{ name: "date", label: "Date", type: "date", value: e.date, span: 3 }, { name: "ml", label: "Acid (mL)", type: "number", step: "any", value: e.ml, span: 3 }, { name: "g", label: "Base (g)", type: "number", step: "any", value: e.g, span: 3 }, { name: "water_gal", label: "Water (gal)", type: "number", step: "any", value: e.water_gal, span: 3 }, { name: "ph_before", label: "pH before", type: "number", step: "any", value: e.ph_before, span: 3 }, { name: "ph_after", label: "pH after", type: "number", step: "any", value: e.ph_after, span: 3 }, { name: "notes", label: "Notes", type: "text", value: e.notes }],
      ...Object.fromEntries(["moisture", "ec", "soil_temp", "air_temp", "out_temp", "par"].map((k) => [k, [{ name: "value", label: g && g.metrics[k] ? `${g.metrics[k].name} (${g.metrics[k].unit})` : "Value", type: "number", step: "0.01", value: e.value, req: true, span: 3 }, { name: "date", label: "Date", type: "date", value: e.date, span: 3 }]])),
    }[kind];
    return {
      title: "Edit entry", fields: F,
      note: kind === "harvest" ? "Changing the pounds re-splits it evenly across the plants that received it." : "",
      submit: (x) => this._call("edit_entry", { kind, parent, entry_id: id, ...x, ...(kind === "cover" && "method" in x ? { method: x.method ? String(x.method).split(",").filter(Boolean) : [] } : {}) }),
    };
  }
}

if (!customElements.get("garden-tracker-card")) customElements.define("garden-tracker-card", GardenTrackerCard);
window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "garden-tracker-card")) window.customCards.push({ type: "garden-tracker-card", name: "Garden Tracker", description: "Plants, trees, harvests, adjuncts, soil pH, and sprays", preview: false });
