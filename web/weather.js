// Local weather from Open-Meteo (free, CC BY 4.0): daily lows, highs and rain for the garden's location.
const DAILY = "temperature_2m_max,temperature_2m_min,precipitation_sum";
const HOURLY = "soil_temperature_6cm";
const UNITS = "temperature_unit=fahrenheit&precipitation_unit=inch&timezone=auto";
const iso = (d) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
const addDays = (d, n) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };

function rows(json, today) {
  const d = json && json.daily;
  if (!d || !d.time) return { daily: {}, rain: {} };
  const out = { daily: {}, rain: {} };
  d.time.forEach((day, i) => {
    if (day >= today) return;  // today is not over, so its low and high are only a forecast
    const lo = d.temperature_2m_min[i], hi = d.temperature_2m_max[i];
    if (lo !== null && hi !== null) out.daily[day] = [lo, hi];
    if (d.precipitation_sum[i] !== null) out.rain[day] = d.precipitation_sum[i];
  });
  return out;
}

// Hourly soil temperature at 6 cm, as [lowest, highest] per day (today included, it is only an estimate).
function soilRows(json) {
  const h = json && json.hourly, out = {};
  if (!h || !h.time) return out;
  h.time.forEach((t, i) => {
    const v = h.soil_temperature_6cm[i];
    if (v === null || v === undefined) return;
    const day = t.slice(0, 10), c = out[day];
    out[day] = c ? [Math.min(c[0], v), Math.max(c[1], v)] : [v, v];
  });
  return out;
}

async function getJson(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`Weather service said ${r.status}`);
  return r.json();
}

// First run: ten years of history. After that: just the last couple of weeks.
export async function fetchWeather(loc, todayIso, full) {
  const today = new Date(todayIso + "T12:00:00");
  const q = `latitude=${loc.lat}&longitude=${loc.lon}`;
  const recent = getJson(`https://api.open-meteo.com/v1/forecast?${q}&daily=${DAILY}&hourly=${HOURLY}&current=temperature_2m&past_days=14&forecast_days=1&${UNITS}`);
  let all = { daily: {}, rain: {} };
  if (full) {
    const hist = await getJson(`https://archive-api.open-meteo.com/v1/archive?${q}&start_date=${iso(addDays(today, -3650))}&end_date=${iso(addDays(today, -7))}&daily=${DAILY}&${UNITS}`);
    all = rows(hist, todayIso);
  }
  const rj = await recent, r = rows(rj, todayIso);
  const td = rj.daily && rj.daily.time ? rj.daily.time.indexOf(todayIso) : -1;
  const now = rj.current && rj.current.temperature_2m !== undefined && rj.current.temperature_2m !== null
    ? { temp: rj.current.temperature_2m, date: todayIso, lo: td >= 0 ? rj.daily.temperature_2m_min[td] : null, hi: td >= 0 ? rj.daily.temperature_2m_max[td] : null } : null;
  return { daily: { ...all.daily, ...r.daily }, rain: { ...all.rain, ...r.rain }, now, soil: soilRows(rj) };
}

export async function findPlaces(name) {
  const j = await getJson(`https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(name)}&count=6&language=en&format=json`);
  return (j.results || []).map((p) => ({ name: [p.name, p.admin1, p.country_code].filter(Boolean).join(", "), lat: p.latitude, lon: p.longitude }));
}
