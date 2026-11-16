#!/usr/bin/env node
// Build időben fut (GitHub Actions). A hanime.tv nyilvános kereső-API-jából tölt le
// hentai címeket, és CSAK az uncensored (is_censored=false) címeket tartja meg.
// www/data.json-be menti, hogy az app offline, azonnal betöltsön.
const fs = require('fs');
const path = require('path');
const OUT = path.join(__dirname, 'www', 'data.json');

const API = 'https://search.htv-services.com/';
const UA = 'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 Chrome/120 Mobile Safari/537.36';

function sleep(ms){ return new Promise(r=>setTimeout(r,ms)); }

async function searchPage(page, orderBy){
  const r = await fetch(API, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json;charset=UTF-8', 'Accept': 'application/json', 'User-Agent': UA, 'Origin': 'https://hanime.tv', 'Referer': 'https://hanime.tv/' },
    body: JSON.stringify({
      search_text: '', tags: [], tags_mode: 'AND', brands: [], blacklist: [],
      order_by: orderBy, ordering: 'desc', page,
    }),
  });
  if (!r.ok) throw new Error('HTTP ' + r.status + ' ' + (await r.text()).slice(0, 160));
  const data = await r.json();
  let hits = data.hits;
  if (typeof hits === 'string') hits = JSON.parse(hits || '[]');
  return { hits: hits || [], nbPages: data.nbPages || 1 };
}

function yearOf(h){
  const u = h.released_at_unix || h.created_at_unix;
  if (u) return new Date(u * 1000).getFullYear();
  const s = h.released_at || h.created_at;
  const y = s && new Date(s).getFullYear();
  return (y && !isNaN(y)) ? y : null;
}
function tagsOf(h){
  if (Array.isArray(h.tags)) return h.tags.map(t => (typeof t === 'string' ? t : (t && t.text) || '')).filter(Boolean);
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
    eps: null,
    format: null,
    status: null,
    brand: h.brand || null,
    genres: tags.slice(0, 6),
    tags: tags.slice(0, 16),
    adult: true,
    unc: true,
    desc: (h.description || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 700),
    url: 'https://hanime.tv/videos/hentai/' + (h.slug || ''),
  };
}

(async () => {
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  try {
    const all = [];
    let censoredSkipped = 0, noCover = 0;
    // Több oldal, népszerűség (views) szerint; biztonsági felső korlát.
    let nbPages = 25;
    for (let p = 0; p < Math.min(nbPages, 25); p++) {
      const { hits, nbPages: np } = await searchPage(p, 'views');
      if (p === 0) { nbPages = np; console.log('nbPages:', np); }
      for (const h of hits) {
        if (h.is_censored === true) { censoredSkipped++; continue; }  // CSAK uncensored
        if (!(h.poster_url || h.cover_url)) { noCover++; continue; }
        all.push(h);
      }
      console.log(`oldal ${p} -> ${hits.length} hit (eddig uncensored: ${all.length}, censored kihagyva: ${censoredSkipped})`);
      if (p + 1 >= np) break;
      if (all.length >= 500) break;
      await sleep(400);
    }

    // dedup id szerint
    const seen = new Set();
    const list = all.filter(h => { if (seen.has(h.id)) return false; seen.add(h.id); return true; }).map(mapHit)
      .filter(x => x.cover && x.id != null);

    if (!list.length) throw new Error('nincs uncensored találat (API válasz üres vagy megváltozott)');
    fs.writeFileSync(OUT, JSON.stringify({ at: Date.now(), anime: list, note: 'uncensored', source: 'hanime.tv' }));
    console.log(`\n✅ data.json kész: ${list.length} uncensored hentai cím (censored kihagyva: ${censoredSkipped}, borító nélkül: ${noCover})`);
  } catch (e) {
    console.error('\n⚠️ Nem sikerült:', e.message);
    fs.writeFileSync(OUT, JSON.stringify({ at: Date.now(), anime: [], error: e.message }));
  }
})();
