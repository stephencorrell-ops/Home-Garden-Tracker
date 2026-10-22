/* Garden Tracker card for Home Assistant. Part of the garden_tracker integration. */
const DOMAIN = "garden_tracker";
const REASON_TEXT = { disease: "Disease", pests: "Pests", frost: "Frost", heat: "Heat", water: "Water",
  animal_damage: "Animal damage", other: "Other" };
const ARCH_TEXT = { season_over: "Season over", pulled_early: "Pulled early", died: "Died" };
const STATUS_TEXT = { alive: "Alive", dead: "Dead", pulled: "Pulled early", harvested: "Harvested" };

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
const COVER_TEXT = { mowed: "mowed", roll_crimped: "roll-crimped", tarped: "tarped", tilled: "tilled", winterkill: "winterkill", other: "other" };
const METRIC_ICON = { moisture: "water-percent", ec: "flash", soil_temp: "thermometer" };
const METRIC_DEC = { moisture: 0, ec: 2, soil_temp: 0 };

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
    const n = g.frost && g.frost.next;
    if (!n) return "";
    const nm = n.event === "last" ? "Last spring frost" : "First fall frost";
    const soon = n.event === "first" && n.days <= 14;
    return `<div class="pill ${soon ? "warn" : "info"}" style="margin:4px 6px 4px 0">${this._icon("snowflake-alert")} ${named ? esc(g.name) + ": " : ""}${nm} ${n.days === 0 ? "expected today" : `in ${n.days} day${n.days === 1 ? "" : "s"}`} (${fmtDate(n.date)})</div>`;
  }
  _homeView() {
    const gs = this._gardens(), vs = this._vars();
    let h = `<div class="hd"><div class="ttl grow">Garden</div>${gs.length ? this._btn("form-variety", "plus", "Add plant", "", "primary") : ""}</div>`;
    if (!gs.length) {
      return h + `<div class="msg">Create your first garden to start adding plants.<br><br>${this._btn("form-garden", "plus", "Add garden", "", "primary")}</div>`;
    }
    h += `<div class="chips">${gs.map((g) => `<button class="chip" data-act="open-g" data-g="${g.id}">${esc(g.name)}</button>`).join("")}${this._config.garden ? "" : `<button class="chip" data-act="form-garden">+ Garden</button>`}</div>`;
    const frost = gs.map((g) => this._frostPill(g, gs.length > 1)).join("");
    if (frost) h += `<div>${frost}</div>`;
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
    h += this._frostPill(g, false);
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
    h += `</div>${this._soilCards(g)}${this._coverCard(g)}<div class="card"><div class="row"><div class="sec grow" style="margin:0">Soil adjuncts this season</div>${this._btn("form-adj", "plus", "Log something else", `data-g="${gid}" data-s="__new__"`)}${this._btn("form-atype", "calendar-plus", "Schedule", `data-g="${gid}"`)}</div>`;
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
    const mine = this._vars().filter((v) => v.garden === gid);
    h += `<div class="card"><div class="sec">Plants in this garden</div>${mine.map((v) => `<div class="lg" style="cursor:pointer" data-act="open-v" data-v="${v.id}"><div class="t">${esc(v.name)}<span>${esc(v.species_name)}${v.kind === "tree" ? "" : `, ${v.alive} of ${v.count} plants`}</span></div>${this._icon("chevron-right")}</div>`).join("") || `<div class="small mut">None yet.</div>`}<div class="row" style="margin-top:8px">${this._btn("form-variety", "plus", "Add plant", `data-g="${gid}"`)}${mine.some((v) => !v.archived && v.kind !== "tree") ? this._btn("form-endseason", "archive", "End season", `data-g="${gid}"`, "danger") : ""}</div></div>`;
    if (!mine.length) h += `<div class="card">${this._confirm === "rmg" ? `<div class="conf">Remove ${esc(g.name)}? Its adjunct and pH history will be lost.<div class="row"><button data-act="cancel-del">Keep</button><button class="danger" data-act="do-rmg" data-g="${gid}">Remove garden</button></div></div>` : `<button class="danger" data-act="ask-rmg">Remove garden</button>`}</div>`;
    return h;
  }

  _coverCard(g) {
    const c = g.cover, gid = g.id;
    let h = `<div class="card"><div class="row"><div class="sec grow" style="margin:0">${this._icon("grass")} Winter cover crop</div>${this._btn("form-cover", "plus", "Add cover crop", `data-g="${gid}"`)}</div>`;
    if (c.blocked) {
      const b = c.blocked;
      h += b.reason === "growing"
        ? `<div class="pill warn" style="margin:8px 0">Cover crop growing. Terminate it, then wait ${(c.items.find((i) => i.state === "growing") || {}).wait_days || 21} days before planting.</div>`
        : `<div class="pill warn" style="margin:8px 0">Wait ${b.days_left} more day${b.days_left === 1 ? "" : "s"} before planting. Ready ${fmtDate(b.date, true)}.</div>`;
    } else if (c.items.length) h += `<div class="pill ok" style="margin:8px 0">Waiting period is over. Garden plants can go in.</div>`;
    if (!c.items.length) h += `<div class="small mut" style="margin:6px 0">Nothing sown yet. Add rye, vetch, clover, winter wheat or peas to track days in the ground and the wait after you terminate it.</div>`;
    for (const i of c.items) {
      const pct = i.state === "growing" ? 0 : Math.min(100, Math.round(((i.wait_days - i.days_left) / Math.max(1, i.wait_days)) * 100));
      h += `<div class="plant"><div class="row"><div class="grow"><b style="font-weight:500">${esc(i.crop)}</b><div class="small mut">Sown ${fmtDate(i.sown)}, ${i.days_in_ground} day${i.days_in_ground === 1 ? "" : "s"} in the ground${i.terminated ? `, terminated ${fmtDate(i.terminated)}${i.method ? " (" + esc(COVER_TEXT[i.method] || i.method) + ")" : ""}` : ""}</div></div><span class="pill ${i.state === "growing" ? "ok" : i.state === "waiting" ? "warn" : "none"}" style="margin:0">${i.state === "growing" ? "Growing" : i.state === "waiting" ? `${i.days_left} d to plant` : "Ready"}</span></div>`;
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
    if (g.sensors_paused) h += `<div class="pill" style="margin:8px 0">Sensors out of the ground. New readings are ignored. Showing the last ones.</div>`;
    h += f.paused ? "" : f.action ? `<div class="pill ${cls}" style="margin:8px 0">${label}</div><div class="small" style="margin-bottom:8px">${esc(f.advice)}</div>` : `<div class="small mut" style="margin:6px 0">No EC readings yet. Pick sensors or log one by hand.</div>`;
    h += `<div class="row" style="align-items:baseline;gap:22px;margin:6px 0"><div><span class="ph">${ec.current === null ? "-" : num(ec.current, 2)}</span> <span class="small mut">mS/cm EC</span></div><div><span class="ph">${mo.current === null ? "-" : num(mo.current, 0) + "%"}</span> <span class="small mut">moisture</span></div></div>`;
    h += `<div class="small mut" style="margin-bottom:6px">Healthy EC ${f.ec_target[0]} to ${f.ec_target[1]}. EC is trusted when moisture is ${f.moisture_band[0]} to ${f.moisture_band[1]}%${f.moisture_state ? `, now ${f.moisture_state === "ok" ? "in that range" : f.moisture_state}` : ""}.${f.ec_change !== null && f.ec_change !== 0 ? ` EC ${f.ec_change < 0 ? "down" : "up"} ${Math.abs(f.ec_change).toFixed(2)} in two weeks.` : ""}${f.last_fed ? ` Last fed ${fmtDate(f.last_fed)}.` : ""}</div>`;
    h += dualChart(ec, mo, f.ec_target);
    h += `<div class="row" style="margin-top:8px;flex-wrap:wrap">${this._btn("form-metric", "plus", "Log EC", `data-g="${gid}" data-s="ec"`)}${this._btn("form-metric", "plus", "Log moisture", `data-g="${gid}" data-s="moisture"`)}${this._btn("form-sensors", "access-point", "EC sensors", `data-g="${gid}" data-s="ec"`)}${this._btn("form-sensors", "access-point", "Moisture sensors", `data-g="${gid}" data-s="moisture"`)}${this._btn("toggle-probes", g.sensors_paused ? "play" : "pause", g.sensors_paused ? "Resume sensors" : "Sensors out", `data-g="${gid}" data-p="${g.sensors_paused ? "0" : "1"}"`)}</div>`;
    h += `<div class="small mut" style="margin-top:4px">EC: ${src(ec)}. Moisture: ${src(mo)}.</div>`;
    for (const m of [ec, mo]) for (const r of m.history.slice().reverse().filter((x) => x.source === "manual").slice(0, 2)) h += this._logRow(m.key, gid, r.id, `${esc(m.name)} ${num(r.value, METRIC_DEC[m.key])}${m.unit === "%" ? "%" : " " + m.unit}`, `${fmtDate(r.date)}, manual`);
    return h + `</div>`;
  }
  _soilCards(g) {
    const gid = g.id;
    let h = this._fertCard(g);
    for (const m of Object.values(g.metrics)) {
      if (m.key === "moisture" || m.key === "ec") continue;
      const d = METRIC_DEC[m.key], u = m.unit === "%" ? "%" : ` ${m.unit}`;
      const src = m.entities.length ? `${m.entities.length} sensor${m.entities.length === 1 ? "" : "s"}, averaged` : "Manual";
      h += `<div class="card"><div class="row"><div class="sec grow" style="margin:0">${this._icon(METRIC_ICON[m.key])} ${esc(m.name)}</div><span class="small mut">${src}</span></div>`;
      if (m.current !== null) {
        h += `<div class="row" style="align-items:baseline;margin:6px 0"><span class="ph">${num(m.current, d)}${m.unit === "%" ? "%" : ""}</span><span class="small mut">${m.unit === "%" ? "" : esc(m.unit) + " "}${m.min !== null && m.min !== undefined ? `today ${num(m.min, d)} to ${num(m.max, d)}${m.unit === "%" ? "%" : ""}` : ""}</span></div>`;
        h += `<div class="small mut" style="margin-bottom:8px">${m.source === "sensor" ? "Sensor" : "Manual reading"}, ${fmtDate(m.date)}</div>`;
      } else h += `<div class="small mut" style="margin:6px 0">No readings yet. Pick sensors or log one by hand.</div>`;
      h += metricChart(m);
      if (g.sensors_paused) h += `<div class="small mut" style="margin-bottom:6px">Sensors out of the ground. New readings are ignored.</div>`;
      if (m.key === "soil_temp" && g.planting) {
        h += `<div class="small mut" style="margin:8px 0 4px">Planting guide, using the average of the last ${g.planting.days} night low${g.planting.days === 1 ? "" : "s"} (${num(g.planting.basis, 0)}°F)</div><div>${g.planting.crops.map((c) => `<span class="pill ${c.ready ? "ok" : "none"}" style="margin:2px 4px 2px 0">${esc(c.name)} ${c.min_f}°${c.ready ? "" : ", not yet"}</span>`).join("")}</div>`;
      }
      h += `<div class="row" style="margin-top:8px">${this._btn("form-metric", "plus", "Log reading", `data-g="${gid}" data-s="${m.key}"`)}${this._btn("form-sensors", "access-point", "Sensors", `data-g="${gid}" data-s="${m.key}"`)}</div>`;
      for (const r of m.history.slice().reverse().filter((x) => x.source === "manual").slice(0, 3)) h += this._logRow(m.key, gid, r.id, `${esc(m.name)} ${num(r.value, d)}${u}`, `${fmtDate(r.date)}, manual`);
      h += `</div>`;
    }
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
      case "form-endseason": return this._open(this._fEndSeason(this._garden(d.g)));
      case "form-cover": return this._open(this._fCover(this._garden(d.g)));
      case "form-terminate": return this._open(this._fTerminate(this._garden(d.g), d.e));
      case "toggle-probes": return this._act("set_soil_sensors_paused", { garden: d.g, paused: d.p === "1" });
      case "reopen-cover": return this._act("reopen_cover_crop", { garden: d.g, cover: d.e });
      case "form-metric": return this._open(this._fMetric(this._garden(d.g), d.s));
      case "form-sensors": return this._open(this._fSensors(this._garden(d.g), d.s));
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
      else if (x.type === "multi") { const on = new Set(String(val).split(",").filter(Boolean)); ctl = `<div class="seg" style="flex-wrap:wrap">${x.options.map(([v, t]) => `<button data-act="toggle" data-f="${x.name}" data-val="${esc(v)}" class="${on.has(v) ? "on" : ""}">${esc(t)}</button>`).join("") || `<span class="small mut">No matching sensors found. Type entity ids below.</span>`}</div>`; }
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
        { name: "single_harvest", label: "Pulled when harvested?", type: "seg", options: [["false", "No"], ["true", "Yes"]], value: "false", show: (v) => v.species === "other" && v.kind !== "tree", span: 3 },
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
      submit: (v) => this._call("add_variety", { garden: v.garden, species: v.species === "other" ? v.species_other : v.species, variety: v.variety, plants: v.plants, origin: v.origin, planted_date: v.planted_date, days_to_harvest: v.days_to_harvest, expected_harvest_date: v.expected_harvest_date, expected_yield: v.expected_yield, notes: v.notes, kind: v.species === "other" ? v.kind : undefined, single_harvest: v.species === "other" && v.kind !== "tree" ? v.single_harvest === "true" : undefined }),
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
        ...(v.kind === "tree" ? [] : [{ name: "multi_year", label: "Countdown in years, months, days", type: "seg", options: [["false", "No"], ["true", "Yes"]], value: String(!!v.multi_year), span: 3 }]),
        ...(v.kind === "tree" ? [] : [{ name: "single_harvest", label: "Pulled when harvested?", type: "seg", options: [["false", "No"], ["true", "Yes"]], value: String(!!v.single_harvest), span: 3 }]),
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
        ...(g ? [
          { name: "ec_min", label: "Healthy soil EC from (mS/cm)", type: "number", step: "0.1", value: g.fertility.ec_target[0], span: 3 },
          { name: "ec_max", label: "Healthy soil EC to (mS/cm)", type: "number", step: "0.1", value: g.fertility.ec_target[1], span: 3 },
          { name: "moisture_min", label: "Trust EC above moisture (%)", type: "number", step: "1", value: g.fertility.moisture_band[0], span: 3 },
          { name: "moisture_max", label: "Trust EC below moisture (%)", type: "number", step: "1", value: g.fertility.moisture_band[1], span: 3 },
          { name: "probe_depth", label: "Probe depth (inches)", type: "number", step: "0.5", value: g.fertility.depth },
          { name: "frost_last", label: "Expected last spring frost", type: "date", value: g.frost.last_date, span: 3 },
          { name: "frost_first", label: "Expected first fall frost", type: "date", value: g.frost.first_date, span: 3 },
          { name: "frost_scope", label: "Apply frost dates to", type: "seg", options: [["garden", "This garden"], ["all", "All gardens"]], value: "garden" },
        ] : []),
      ],
      note: "Leave the sensor empty to log pH by hand. EC and moisture ranges set when feeding advice shows. Frost dates repeat every year, so set the average for your area.",
      submit: async (x) => {
        const { frost_last, frost_first, frost_scope, ...rest } = x;
        if (!g) return this._call("add_garden", rest);
        await this._call("update_garden", { garden: g.id, ...rest, ph_entity: rest.ph_entity === undefined ? " " : rest.ph_entity });
        const changed = (frost_last && frost_last !== g.frost.last_date) || (frost_first && frost_first !== g.frost.first_date);
        if (frost_scope === "all" || changed) await this._call("set_frost_dates", { garden: g.id, last_frost: frost_last, first_frost: frost_first, all_gardens: frost_scope === "all" });
      },
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
        { name: "wait_days", label: "Wait after terminating (days)", type: "number", step: "1", value: 21, span: 3 },
        { name: "notes", label: "Notes", type: "text", placeholder: "Seeding rate, mix, bed" },
      ],
      note: "The wait is how long to leave the bed alone after terminating before planting. Three weeks is the usual rule.",
      submit: (x) => { const { pick, custom, ...rest } = x; return this._call("add_cover_crop", { garden: g.id, ...rest, crop: pick === "__other__" ? custom : pick }); },
    };
  }
  _fTerminate(g, id) {
    const i = g.cover.items.find((x) => x.id === id) || {};
    return {
      title: `Terminate ${i.crop || "cover crop"}`, submitLabel: "Terminate",
      fields: [
        { name: "date", label: "Date terminated", type: "date", value: this._snap.today, span: 3 },
        { name: "method", label: "How", type: "chips", options: Object.entries(COVER_TEXT), value: "mowed" },
        { name: "notes", label: "Notes", type: "text" },
      ],
      preview: (x) => (x.date ? `<div class="pill ok">Plant after ${fmtDate(this._isoAdd(x.date, i.wait_days || 21), true)} (${i.wait_days || 21} days)</div>` : ""),
      submit: (x) => this._call("terminate_cover_crop", { garden: g.id, cover: id, ...x }),
    };
  }
  _fMetric(g, key) {
    const m = g.metrics[key], u = m.unit;
    return {
      title: `Log ${m.name.toLowerCase()}: ${g.name}`, submitLabel: "Log",
      fields: [
        { name: "value", label: `${m.name} (${u})`, type: "number", step: key === "ec" ? "0.01" : "0.1", req: true, span: 3 },
        { name: "date", label: "Date", type: "date", value: this._snap.today, span: 3 },
      ],
      note: key === "ec" ? "EC in mS/cm (same as dS/m)." : key === "soil_temp" ? "Soil temperature in °F." : "",
      submit: (x) => this._call("log_garden_reading", { garden: g.id, metric: key, ...x }),
    };
  }
  _sensorCandidates(key, selected) {
    const st = (this._hass && this._hass.states) || {};
    const out = [];
    for (const [id, s] of Object.entries(st)) {
      if (!id.startsWith("sensor.")) continue;
      const a = s.attributes || {}, dc = a.device_class, unit = String(a.unit_of_measurement || "").toLowerCase();
      const ok = key === "soil_temp" ? dc === "temperature" || /^°?[cf]$/.test(unit) || /soil.*temp|temp.*soil/.test(id)
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
      note: "With several sensors, the garden uses their average. Leave all empty to log by hand. Today's low and high are tracked as readings come in.",
      submit: (x) => this._call("set_garden_sensors", { garden: g.id, metric: key, entities: [...String(x.pick || "").split(","), ...String(x.extra || "").split(",")].map((e) => e.trim()).filter(Boolean) }),
    };
  }
  _findEntry(kind, parent, id) {
    const v = this._variety(parent), g = this._garden(parent);
    const list = { harvest: v && v.harvests, fertilizer: v && v.fertilizations, spray: v && v.sprays, review: v && v.reviews, upotted: v && v.upotted, adjunct: g && g.adjunct_log, ph: g && g.ph.history, moisture: g && g.metrics.moisture.history, ec: g && g.metrics.ec.history, soil_temp: g && g.metrics.soil_temp.history, cover: g && g.cover.items }[kind];
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
      cover: [{ name: "crop", label: "Cover crop", type: "text", value: e.crop, req: true }, { name: "sown", label: "Sown", type: "date", value: e.sown, span: 3 }, { name: "terminated", label: "Terminated", type: "date", value: e.terminated, span: 3 }, { name: "method", label: "How terminated", type: "chips", options: Object.entries(COVER_TEXT), value: e.method }, { name: "wait_days", label: "Wait after terminating (days)", type: "number", step: "1", value: e.wait_days, span: 3 }, { name: "notes", label: "Notes", type: "text", value: e.notes }],
      ...Object.fromEntries(["moisture", "ec", "soil_temp"].map((k) => [k, [{ name: "value", label: g && g.metrics[k] ? `${g.metrics[k].name} (${g.metrics[k].unit})` : "Value", type: "number", step: "0.01", value: e.value, req: true, span: 3 }, { name: "date", label: "Date", type: "date", value: e.date, span: 3 }]])),
    }[kind];
    return {
      title: "Edit entry", fields: F,
      note: kind === "harvest" ? "Changing the pounds re-splits it evenly across the plants that received it." : "",
      submit: (x) => this._call("edit_entry", { kind, parent, entry_id: id, ...x }),
    };
  }
}

if (!customElements.get("garden-tracker-card")) customElements.define("garden-tracker-card", GardenTrackerCard);
window.customCards = window.customCards || [];
if (!window.customCards.some((c) => c.type === "garden-tracker-card")) window.customCards.push({ type: "garden-tracker-card", name: "Garden Tracker", description: "Plants, trees, harvests, adjuncts, soil pH, and sprays", preview: false });
