// Offline gyorsítótár + „Megosztás” fogadása más appokból.
// Semmilyen külső szervert nem hív: csak a saját fájlokat szolgálja ki.
importScripts('db.js');

const CACHE = 'tar-v1';
const FILES = ['./', 'index.html', 'db.js', 'manifest.webmanifest', 'icon.svg', 'icon-192.png', 'icon-512.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)).then(() => self.skipWaiting()));
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys()
    .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
    .then(() => self.clients.claim()));
});

const URL_RE = /https?:\/\/[^\s]+/i;

async function saveShare(request) {
  const fd = await request.formData();
  const title = (fd.get('title') || '').toString().trim();
  const text = (fd.get('text') || '').toString().trim();
  let url = (fd.get('url') || '').toString().trim();
  // Sok app a linket a szövegbe teszi, nem az url mezőbe.
  if (!url) { const m = text.match(URL_RE); if (m) url = m[0]; }
  const note = url ? text.replace(url, '').trim() : text;
  const now = Date.now();
  let count = 0;
  for (const f of fd.getAll('files')) {
    if (!(f instanceof File) || !f.size) continue;
    await dbPut('vault', { id: newId(), type: f.type.startsWith('image/') ? 'image' : 'file', title: title || f.name, note, folder: '', blob: f, name: f.name, mime: f.type, ts: now + count });
    count++;
  }
  if (url) {
    await dbPut('vault', { id: newId(), type: 'link', title: title || '', url, note, folder: '', ts: now + count });
    count++;
  } else if (!count && (text || title)) {
    await dbPut('vault', { id: newId(), type: 'note', title: title || 'Megosztott szöveg', note: text, folder: '', ts: now });
    count++;
  }
  return count;
}

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (url.origin !== location.origin) return;
  if (e.request.method === 'POST' && url.pathname.endsWith('/share')) {
    e.respondWith(saveShare(e.request)
      .then(n => Response.redirect('./?shared=' + n, 303))
      .catch(() => Response.redirect('./?shared=0', 303)));
    return;
  }
  if (e.request.method !== 'GET') return;
  e.respondWith(
    fetch(e.request)
      .then(res => {
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(e.request, copy));
        return res;
      })
      .catch(() => caches.match(e.request, { ignoreSearch: true }))
  );
});
