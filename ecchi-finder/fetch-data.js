#!/usr/bin/env node
// Build időben fut (GitHub Actions). Dedikált uncensored hentai katalógus a
// hanime.tv API-jából; CSAK az uncensored (is_censored=false) címek.
// Több végpontot próbál (az API időnként költözik), és logolja a szerkezetet.
const fs = require('fs');
const path = require('path');
const OUT = path.join(__dirname, 'www', 'data.json');

const UA = 'Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Mobile Safari/537.36';
const HDRS = { 'Content-Type': 'application/json;charset=UTF-8', 'Accept': 'application/json', 'User-Agent': UA, 'X-Signature-Version': 'web2', 'Origin': 'https://hanime.tv', 'Referer': 'https://hanime.tv/' };

function sleep(ms){ return new Promise(r=>setTimeout(r,ms)); }
function body(page, orderBy){ return JSON.stringify({ search_text:'', tags:[], tags_mode:'AND', brands:[], blacklist:[], order_by:orderBy, ordering:'desc', page }); }

// Egy válaszból kiszedi a videók tömbjét, bármelyik ismert alakból
function extractList(data){
  if (!data) return [];
  if (Array.isArray(data.hentai_videos)) return data.hentai_videos;
  if (typeof data.hits === 'string') { try { return JSON.parse(data.hits || '[]'); } catch(_) { return []; } }
  if (Array.isArray(data.hits)) return data.hits;
  if (Array.isArray(data.results)) return data.results;
  return [];
}

const ENDPOINTS = [
  { url: 'https://hanime.tv/api/v8/search', method: 'POST' },
  { url: 'https://members.hanime.tv/api/v8/search', method: 'POST' },
  { url: 'https://search.htv-services.com/', method: 'POST' },
];

async function tryFetch(ep, page, orderBy){
  const opt = { method: ep.method, headers: HDRS };
  if (ep.method === 'POST') opt.body = body(page, orderBy);
  const r = await fetch(ep.url, opt);
  const txt = await r.text();
  if (!r.ok) throw new Error('HTTP ' + r.status + ' :: ' + txt.slice(0, 120));
  let data; try { data = JSON.parse(txt); } catch(e){ throw new Error('nem JSON :: ' + txt.slice(0, 120)); }
  return data;
}

function yearOf(h){
  const u = h.released_at_unix || h.created_at_unix;
  if (u) return new Date(u * 1000).getFullYear();
  const s = h.released_at || h.created_at;
  const y = s && new Date(s).getFullYear();
  return (y && !isNaN(y)) ? y : null;
}
function tagsOf(h){
  if (Array.isArray(h.tags)) return h.tags.map(t => (typeof t === 'string' ? t : (t && (t.text || t.name)) || '')).filter(Boolean);
  if (Array.isArray(h.hentai_tags)) return h.hentai_tags.map(t => t && (t.text || t.name)).filter(Boolean);
  return [];
}
function mapHit(h){
  const tags = tagsOf(h);
  return {
    id: h.id,
    title: h.name || (h.titles && h.titles[0]) || h.slug,
    rom: (h.titles && h.titles[0]) || h.name || '',
    cover: h.poster_url || h.cover_url,
    color: '#ff2d95',
    banner: h.cover_url || h.poster_url || null,
    score: null,
    views: h.views || null,
    year: yearOf(h),
    eps: null, format: null, status: null,
    brand: h.brand || null,
    genres: tags.slice(0, 6),
    tags: tags.slice(0, 16),
    adult: true, unc: true,
    desc: (h.description || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 700),
    url: 'https://hanime.tv/videos/hentai/' + (h.slug || ''),
  };
}

(async () => {
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  try {
    // 1) Melyik végpont él? (első oldal kipróbálása)
    let live = null, first = null;
    for (const ep of ENDPOINTS) {
      try {
        const d = await tryFetch(ep, 0, 'views');
        const list = extractList(d);
        console.log(`[${ep.url}] OK — kulcsok: ${Object.keys(d).join(',')} | lista: ${list.length}`);
        if (list.length){ console.log('   minta-elem kulcsai:', Object.keys(list[0]).join(',')); console.log('   is_censored a mintában:', list[0].is_censored); }
        if (list.length && !live){ live = ep; first = { d, list }; }
      } catch(e){
        console.log(`[${ep.url}] HIBA: ${e.message}`);
      }
      await sleep(300);
    }
    if (!live) throw new Error('egyik hanime végpont sem adott listát');

    // 2) Lapozás az élő végponton
    const all = [];
    let censored = 0, noCover = 0;
    const consume = (list) => {
      for (const h of list) {
        if (h.is_censored === true) { censored++; continue; }
        if (!(h.poster_url || h.cover_url)) { noCover++; continue; }
        all.push(h);
      }
    };
    consume(first.list);
    const nbPages = first.d.nbPages || first.d.number_of_pages || 20;
    console.log('nbPages:', nbPages);
    for (let p = 1; p < Math.min(nbPages, 25); p++) {
      try {
        const d = await tryFetch(live, p, 'views');
        const list = extractList(d);
        consume(list);
        console.log(`oldal ${p} -> ${list.length} (uncensored eddig: ${all.length}, censored kihagyva: ${censored})`);
        if (!list.length) break;
      } catch(e){ console.log(`oldal ${p} HIBA: ${e.message}`); break; }
      if (all.length >= 500) break;
      await sleep(400);
    }

    const seen = new Set();
    const result = all.filter(h => { if (seen.has(h.id)) return false; seen.add(h.id); return true; })
      .map(mapHit).filter(x => x.cover && x.id != null);

    if (!result.length) throw new Error('nincs uncensored találat');
    fs.writeFileSync(OUT, JSON.stringify({ at: Date.now(), anime: result, note: 'uncensored', source: 'hanime.tv' }));
    console.log(`\n✅ data.json kész: ${result.length} uncensored hentai (censored kihagyva: ${censored}, borító nélkül: ${noCover})`);
  } catch (e) {
    console.error('\n⚠️ Nem sikerült:', e.message);
    fs.writeFileSync(OUT, JSON.stringify({ at: Date.now(), anime: [], error: e.message }));
  }
})();
