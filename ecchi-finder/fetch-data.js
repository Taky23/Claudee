#!/usr/bin/env node
// Build időben fut (GitHub Actions). Az AniList nyilvános GraphQL API-jából
// kétféle tartalmat tölt le:
//   1) ECCHI (isAdult:false) – csak az "uncensored" jellegű (erős Nudity-besorolás),
//   2) HENTAI (isAdult:true) – a legkeményebb, explicit címek (külön jelölve).
// www/data.json-be menti, hogy az app offline, azonnal betöltsön.
const fs = require('fs');
const path = require('path');
const OUT = path.join(__dirname, 'www', 'data.json');

const Q = `query($page:Int,$genre:String,$adult:Boolean){ Page(page:$page, perPage:50){ pageInfo{hasNextPage} media(genre:$genre, type:ANIME, isAdult:$adult, sort:POPULARITY_DESC){ id title{romaji english} coverImage{large color} bannerImage averageScore seasonYear episodes format status genres tags{name rank} description(asHtml:false) siteUrl } } }`;

function sleep(ms){ return new Promise(r=>setTimeout(r,ms)); }

const NUDE_TAGS = ['Nudity', 'Boobs', 'Breasts', 'Nipples', 'Sex', 'Full Color'];
function uncScore(tags){
  let best = 0;
  (tags || []).forEach(t => { if (NUDE_TAGS.includes(t.name)) best = Math.max(best, t.rank || 0); });
  return best;
}

function mapMedia(m, adult){
  const rawTags = m.tags || [];
  return {
    id: m.id,
    title: (m.title.english || m.title.romaji),
    rom: m.title.romaji,
    cover: m.coverImage && m.coverImage.large,
    color: (m.coverImage && m.coverImage.color) || '#ff4d8d',
    banner: m.bannerImage || null,
    score: m.averageScore || null,
    year: m.seasonYear || null,
    eps: m.episodes || null,
    format: m.format || null,
    status: m.status || null,
    genres: m.genres || [],
    tags: rawTags.slice(0, 14).map(t => t.name),
    unc: uncScore(rawTags),
    adult: !!adult,
    desc: (m.description || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 700),
    url: m.siteUrl,
  };
}

async function fetchGenre(genre, adult, pages){
  const out = [];
  for (let p = 1; p <= pages; p++) {
    const r = await fetch('https://graphql.anilist.co', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
      body: JSON.stringify({ query: Q, variables: { page: p, genre, adult } }),
    });
    if (!r.ok) { console.error('HTTP', r.status, genre, (await r.text()).slice(0, 160)); break; }
    const j = await r.json();
    if (j.errors) { console.error('AniList hiba', genre, JSON.stringify(j.errors).slice(0, 200)); break; }
    const media = (j.data && j.data.Page && j.data.Page.media) || [];
    media.forEach(m => out.push(mapMedia(m, adult)));
    console.log(`[${genre}/${adult?'18+':'ecchi'}] oldal ${p} -> ${media.length} (összes ${out.length})`);
    if (!j.data.Page.pageInfo.hasNextPage) break;
    await sleep(900);
  }
  return out;
}

(async () => {
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  try {
    // 1) Uncensored ecchi
    const ecchiRaw = await fetchGenre('Ecchi', false, 6);
    let uncensored = [];
    for (const thr of [55, 45, 35, 25, 15]) {
      uncensored = ecchiRaw.filter(a => (a.unc || 0) >= thr);
      console.log(`  Nudity-rank >= ${thr}: ${uncensored.length} uncensored ecchi`);
      if (uncensored.length >= 20) break;
    }
    uncensored.sort((a, b) => (b.unc || 0) - (a.unc || 0));

    // 2) Legkeményebbek: hentai (explicit, 18+)
    const hentai = await fetchGenre('Hentai', true, 4);

    // Egyesítés, dedup id szerint, csak borítóval
    const seen = new Set();
    const merged = [...uncensored, ...hentai].filter(a => {
      if (!a.cover) return false;
      if (seen.has(a.id)) return false;
      seen.add(a.id); return true;
    });

    if (!merged.length) throw new Error('nincs találat');
    fs.writeFileSync(OUT, JSON.stringify({ at: Date.now(), anime: merged }));
    const nA = merged.filter(a => a.adult).length;
    console.log(`\n✅ data.json kész: ${merged.length} cím (${merged.length - nA} uncensored ecchi + ${nA} hardcore/18+)`);
  } catch (e) {
    console.error('\n⚠️ Nem sikerült:', e.message);
    fs.writeFileSync(OUT, JSON.stringify({ at: Date.now(), anime: [], error: e.message }));
  }
})();
