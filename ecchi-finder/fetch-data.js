#!/usr/bin/env node
// Build időben fut (GitHub Actions). Az AniList nyilvános GraphQL API-jából
// CSAK uncensored HENTAI címeket tölt le (isAdult:true), kétféle jelből:
//   1) ha létezik AniList "Uncensored" tag -> azzal szűrve,
//   2) a legnépszerűbb hentai címek közül azok, amelyek címében/szinonimájában
//      szerepel az "uncensored" (az AniList gyakran külön bejegyzésként viszi az
//      uncensored vágást).
// www/data.json-be menti, hogy az app offline, azonnal betöltsön.
const fs = require('fs');
const path = require('path');
const OUT = path.join(__dirname, 'www', 'data.json');

const FIELDS = `id title{romaji english native} synonyms coverImage{large color} bannerImage averageScore seasonYear episodes format status genres tags{name rank} description(asHtml:false) siteUrl`;

function sleep(ms){ return new Promise(r=>setTimeout(r,ms)); }

async function gql(query, variables){
  const r = await fetch('https://graphql.anilist.co', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
    body: JSON.stringify({ query, variables }),
  });
  if (!r.ok) throw new Error('HTTP ' + r.status + ' ' + (await r.text()).slice(0, 160));
  const j = await r.json();
  if (j.errors) throw new Error('AniList: ' + JSON.stringify(j.errors).slice(0, 200));
  return j.data;
}

function mapMedia(m){
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
    adult: true,
    unc: true,
    desc: (m.description || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 700),
    url: m.siteUrl,
  };
}

// Van-e "uncensored" jel a címek/szinonimák közt?
function looksUncensored(m){
  const parts = [m.title && m.title.romaji, m.title && m.title.english, m.title && m.title.native, ...(m.synonyms || [])];
  return parts.some(s => s && /uncensor/i.test(s));
}

// Hentai lekérés, opcionális tag-szűrővel
async function fetchHentai(pages, tag){
  const out = [];
  const q = `query($page:Int){ Page(page:$page, perPage:50){ pageInfo{hasNextPage}
    media(genre:"Hentai", type:ANIME, isAdult:true, ${tag ? `tag:"${tag}", ` : ''}sort:POPULARITY_DESC){ ${FIELDS} } } }`;
  for (let p = 1; p <= pages; p++) {
    const d = await gql(q, { page: p });
    const media = (d.Page && d.Page.media) || [];
    media.forEach(m => out.push(m));
    console.log(`[hentai${tag ? ' tag:' + tag : ''}] oldal ${p} -> ${media.length} (összes ${out.length})`);
    if (!d.Page.pageInfo.hasNextPage) break;
    await sleep(900);
  }
  return out;
}

(async () => {
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  try {
    let tagged = [];
    // 1) Próbáljuk a hivatalos "Uncensored" taget (ha nincs ilyen tag, AniList hibát dob -> csendben tovább)
    try {
      tagged = await fetchHentai(6, 'Uncensored');
      console.log('  Uncensored tag találatok:', tagged.length);
    } catch (e) {
      console.log('  (nincs használható "Uncensored" tag:', e.message.slice(0, 80), ')');
    }

    // 2) Népszerű hentai, cím/szinonima alapján uncensored szűrés
    const popular = await fetchHentai(12);
    const scanned = popular.filter(looksUncensored);
    console.log('  cím alapján uncensored:', scanned.length, '/', popular.length);

    // Egyesítés + dedup id szerint, csak borítóval
    const seen = new Set();
    let list = [...tagged, ...scanned]
      .filter(m => m.coverImage && m.coverImage.large)
      .filter(m => { if (seen.has(m.id)) return false; seen.add(m.id); return true; })
      .map(mapMedia);

    let note = 'uncensored';
    // Ha túl kevés az egyértelműen uncensored, essünk vissza a legnépszerűbb hentaikra
    if (list.length < 12) {
      console.log('  ⚠️ Kevés egyértelmű uncensored (', list.length, ') – kiegészítés a legnépszerűbb hentaikkal.');
      const seen2 = new Set(list.map(x => x.id));
      const extra = popular
        .filter(m => m.coverImage && m.coverImage.large && !seen2.has(m.id))
        .map(mapMedia);
      list = list.concat(extra);
      note = 'hentai (uncensored jelölés korlátozott)';
    }

    if (!list.length) throw new Error('nincs hentai találat');
    fs.writeFileSync(OUT, JSON.stringify({ at: Date.now(), anime: list, note }));
    console.log(`\n✅ data.json kész: ${list.length} cím (${note})`);
  } catch (e) {
    console.error('\n⚠️ Nem sikerült:', e.message);
    fs.writeFileSync(OUT, JSON.stringify({ at: Date.now(), anime: [], error: e.message }));
  }
})();
