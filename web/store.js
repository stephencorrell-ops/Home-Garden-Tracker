// Saves the garden in the browser (IndexedDB). Back it up from the page, because a browser can wipe its storage.
const DB = "garden-tracker", STORE = "kv";

function open() {
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB, 1);
    req.onupgradeneeded = () => req.result.createObjectStore(STORE);
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}
async function tx(mode, fn) {
  const db = await open();
  return new Promise((resolve, reject) => {
    const t = db.transaction(STORE, mode), r = fn(t.objectStore(STORE));
    t.oncomplete = () => resolve(r && r.result);
    t.onerror = () => reject(t.error);
  });
}
export const get = (key) => tx("readonly", (s) => s.get(key)).catch(() => null);
export const set = (key, value) => tx("readwrite", (s) => s.put(value, key));

export async function keepSafe() {
  // Ask the browser not to clear this site's data when it is short on space.
  try { return !!(navigator.storage && navigator.storage.persist && (await navigator.storage.persist())); } catch { return false; }
}

const num = (k) => { try { return Number(localStorage.getItem(k)) || 0; } catch { return 0; } };
export const lastBackup = () => num("gt.lastBackup");
export const markBackup = () => { try { localStorage.setItem("gt.lastBackup", String(Date.now())); } catch { /* private mode */ } };
