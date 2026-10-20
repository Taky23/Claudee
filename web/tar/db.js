// Közös IndexedDB réteg az oldalnak és a service workernek.
// Minden adat csak a telefon böngészőjében, ebben az adatbázisban él.
const DB_NAME = 'gamer-tar';
const DB_VERSION = 2;
let dbPromise = null;

function openDb() {
  if (!dbPromise) {
    dbPromise = new Promise((resolve, reject) => {
      const req = indexedDB.open(DB_NAME, DB_VERSION);
      req.onupgradeneeded = () => {
        const d = req.result;
        if (!d.objectStoreNames.contains('kv')) d.createObjectStore('kv');
        for (const s of ['games', 'sessions', 'vault', 'music']) {
          if (!d.objectStoreNames.contains(s)) d.createObjectStore(s, { keyPath: 'id' });
        }
      };
      req.onsuccess = () => resolve(req.result);
      req.onerror = () => reject(req.error);
    });
  }
  return dbPromise;
}

async function dbRun(store, mode, fn) {
  const d = await openDb();
  return new Promise((resolve, reject) => {
    const t = d.transaction(store, mode);
    const s = t.objectStore(store);
    let result;
    const r = fn(s);
    if (r) r.onsuccess = () => { result = r.result; };
    t.oncomplete = () => resolve(result);
    t.onerror = () => reject(t.error);
    t.onabort = () => reject(t.error);
  });
}

const dbAll = store => dbRun(store, 'readonly', s => s.getAll());
const dbGet = (store, key) => dbRun(store, 'readonly', s => s.get(key));
const dbPut = (store, obj) => dbRun(store, 'readwrite', s => s.put(obj));
const dbDel = (store, key) => dbRun(store, 'readwrite', s => s.delete(key));
const dbClear = store => dbRun(store, 'readwrite', s => s.clear());
const kvGet = key => dbRun('kv', 'readonly', s => s.get(key));
const kvSet = (key, val) => dbRun('kv', 'readwrite', s => s.put(val, key));
const newId = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
