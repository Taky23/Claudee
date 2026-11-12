#!/usr/bin/env node
// Build időben fut (GitHub Actions). Az AniList nyilvános GraphQL API-jából
// letölti a legnépszerűbb ECCHI (TV) animéket (isAdult:false => hentai kizárva),
// és www/data.json-be menti, hogy az app offline, azonnal betöltsön.
const fs = require('fs');
const path = require('path');
const OUT = path.join(__dirname, 'www', 'data.json');

const query = `query($page:Int){ Page(page:$page, perPage:50){ pageInfo{hasNextPage} media(genre:"Ecchi", type:ANIME, isAdult:false, sort:POPULARITY_DESC){ id title{romaji english} coverImage{large color} bannerImage averageScore seasonYear episodes format status genres description(asHtml:false) siteUrl } } }`;

function sleep(ms){ return new Promise(r=>setTimeout(r,ms)); }

(async () => {
  fs.mkdirSync(path.dirname(OUT), { recursive: true });
  const all = [];
  try {
    for (let p = 1; p <= 4; p++) {
      const r = await fetch('https://graphql.anilist.co', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'Accept': 'application/json' },
        body: JSON.stringify({ query, variables: { page: p } }),
      });
      if (!r.ok) { console.error('HTTP', r.status, (await r.text()).slice(0, 160)); break; }
      const j = await r.json();
      if (j.errors) { console.error('AniList hiba:', JSON.stringify(j.errors).slice(0, 200)); break; }
      const media = (j.data && j.data.Page && j.data.Page.media) || [];
      media.forEach(m => all.push({
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
        desc: (m.description || '').replace(/<[^>]+>/g, ' ').replace(/\s+/g, ' ').trim().slice(0, 700),
        url: m.siteUrl,
      }));
      console.log('oldal', p, '->', media.length, 'cím (összes:', all.length + ')');
      if (!j.data.Page.pageInfo.hasNextPage) break;
      await sleep(900); // AniList rate-limit udvariasság
    }
    // dedup id szerint
    const seen = new Set(); const uniq = all.filter(a => { if (seen.has(a.id)) return false; seen.add(a.id); return !!a.cover; });
    fs.writeFileSync(OUT, JSON.stringify({ at: Date.now(), anime: uniq }));
    console.log('\n✅ data.json kész:', uniq.length, 'ecchi cím');
    if (!uniq.length) throw new Error('üres lista');
  } catch (e) {
    console.error('\n⚠️ Nem sikerült:', e.message);
    fs.writeFileSync(OUT, JSON.stringify({ at: Date.now(), anime: [], error: e.message }));
  }
})();
