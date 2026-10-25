// Tarkov Hardcore – felület. Minden adat csak a telefonon (localStorage).
(function () {
  'use strict';
  const G = window.TGen;
  const KEY = 'tarkov-hc-v1';
  const $ = id => document.getElementById(id);
  const esc = s => String(s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

  const blank = () => ({
    diff: 2, players: 1,
    gen: null,            // { m, state: 'new'|'active', startedAt }
    daily: null,          // { date, m, state: 'new'|'active'|'won'|'lost', startedAt }
    st: { points: 0, won: 0, lost: 0, fled: 0, streak: 0, best: 0, dWon: 0, dLost: 0, dStreak: 0, dLastWin: null, punishDone: 0 },
    punish: null,         // a legutóbbi bukás büntetése, amíg le nem tudod
    hist: [], maps: {},
  });
  let S;
  try { S = Object.assign(blank(), JSON.parse(localStorage.getItem(KEY) || '{}')); S.st = Object.assign(blank().st, S.st); }
  catch (e) { S = blank(); }
  const save = () => { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) { /* tele vagy tiltott tár */ } };

  function today() {
    const d = new Date();
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0');
  }
  function yesterday() { const d = new Date(); d.setDate(d.getDate() - 1); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); }
  const buzz = ms => { try { navigator.vibrate && navigator.vibrate(ms); } catch (e) {} };
  let toastT;
  function toast(t) { const el = $('toast'); el.textContent = t; el.classList.add('on'); clearTimeout(toastT); toastT = setTimeout(() => el.classList.remove('on'), 2200); }

  function confirmBox(title, text, yes, no, onYes, danger) {
    $('mTitle').textContent = title; $('mText').textContent = text;
    $('mBtns').innerHTML = `<button id="mNo">${esc(no)}</button><button id="mYes" class="${danger ? 'die' : 'go'}">${esc(yes)}</button>`;
    $('modal').classList.add('on');
    $('mNo').onclick = () => $('modal').classList.remove('on');
    $('mYes').onclick = () => { $('modal').classList.remove('on'); onYes(); };
  }
  $('modal').addEventListener('click', e => { if (e.target.id === 'modal') $('modal').classList.remove('on'); });

  // ---------- Fülek ----------
  document.querySelectorAll('nav button').forEach(b => b.onclick = () => {
    document.querySelectorAll('nav button').forEach(x => x.classList.toggle('on', x === b));
    document.querySelectorAll('.tab').forEach(t => t.classList.toggle('on', t.id === 't-' + b.dataset.tab));
    render(); window.scrollTo(0, 0);
  });

  const HINTS = {
    1: 'Két extra szabály, 3 újrasorsolás. Kemény, de túlélhető.',
    2: 'Három szabály, 1 újrasorsolás, gyakran kötött extract és időlimit. Ha elbuksz, büntetés jár.',
    3: 'Négy szabály, nulla újrasorsolás, átkozott fegyverek, szűk időlimit, brutális büntetés. ×4 pont.',
  };

  // ---------- Küldetés kártya ----------
  function fmtTime(ms) {
    const s = Math.max(0, Math.floor(ms / 1000));
    return String(Math.floor(s / 60)).padStart(2, '0') + ':' + String(s % 60).padStart(2, '0');
  }

  function line(k, v, cls, rrKey, canRR) {
    return `<div class="row"><div class="k">${k}</div><div class="v ${cls || ''}">${esc(v)}</div>` +
      (rrKey ? `<button class="rr" data-rr="${rrKey}" ${canRR ? '' : 'disabled'} aria-label="Újrasorsolás">🔄</button>` : '') + '</div>';
  }

  function missionHtml(m, ctx, state) {
    const D = G.DIFFS[m.diff];
    const canRR = ctx === 'gen' && state === 'new' && m.rerollsLeft > 0;
    const rr = k => (ctx === 'gen' && state === 'new' && D.rerolls > 0) ? k : null;
    const stamp = state === 'won' ? '<div class="stamp ok">TELJESÍTVE</div>' : state === 'lost' ? '<div class="stamp">ELBUKOTT</div>' : '';
    let h = `<div class="card">${stamp}
      <div class="head"><span>${m.daily ? 'Napi szerződés' : 'Szerződés'} #${String(m.seed).slice(-5)}</span><b>${D.icon} ${D.name}</b></div>`;
    h += line('Pálya', m.map, 'map', rr('map'), canRR);
    h += line('Napszak', m.time.t, '', rr('time'), canRR);
    h += line('Cél', m.objective.t, 'obj', rr('objective'), canRR);
    h += line('Extract', m.extract.t, '', rr('extract'), canRR);
    if (m.timeLimit) h += line('Időlimit', `${m.timeLimit} perc a raid kezdetétől`, '', null);
    m.rules.forEach((t, i) => { h += line('Szabály ' + (i + 1), t, '', rr('rule:' + i), canRR); });
    m.players.forEach((p, i) => {
      h += `<div class="player">${m.players.length > 1 ? `<div class="ph">▸ ${i + 1}. játékos</div>` : ''}`;
      h += line('Fegyver', p.weapon, '', rr(`p:${i}:weapon`), canRR);
      if (p.ammo) h += line('Lőszer', p.ammo, '', rr(`p:${i}:ammo`), canRR);
      h += line('Páncél', p.armor, '', rr(`p:${i}:armor`), canRR);
      h += line('Gyógyszer', p.meds, '', rr(`p:${i}:meds`), canRR);
      h += line('Felszerelés', p.gear, '', rr(`p:${i}:gear`), canRR);
      h += '</div>';
    });
    h += `<p class="punish"><b>HA ELBUKSZ</b>${esc(m.punish)}</p>`;
    h += `<div class="foot"><span>${ctx === 'gen' && state === 'new' ? (D.rerolls ? `Újrasorsolás: ${m.rerollsLeft}/${D.rerolls}` : 'Nincs újrasorsolás') : (m.players.length > 1 ? m.players.length + ' fős csapat' : 'Egyedül')}</span><span>Jutalom: <b>${m.points} pont</b></span></div>`;
    return h + '</div>';
  }

  function timerHtml(m, startedAt) {
    const el = Date.now() - startedAt;
    const late = m.timeLimit && el > m.timeLimit * 60000;
    const sub = m.timeLimit ? (late ? 'LEJÁRT AZ IDŐ – ha még bent vagy, ez bukás' : `Hátra: ${fmtTime(m.timeLimit * 60000 - el)}`) : 'Raid folyamatban';
    return `<div class="timer ${late ? 'late' : ''}"><div class="t" data-timer>${fmtTime(el)}</div><div class="s" data-timer-sub>${sub}</div></div>`;
  }

  // ---------- Pontozás ----------
  function streakBonus() { return Math.min(0.5, S.st.streak * 0.1); }
  function finish(ctx, ok) {
    const slot = ctx === 'gen' ? S.gen : S.daily;
    const m = slot.m;
    let delta;
    if (ok) {
      const bonus = streakBonus();
      delta = Math.round(m.points * (1 + bonus));
      S.st.points += delta; S.st.won++; S.st.streak++; S.st.best = Math.max(S.st.best, S.st.streak);
      if (m.daily) { S.st.dWon++; S.st.dStreak = S.st.dLastWin === yesterday() ? S.st.dStreak + 1 : 1; S.st.dLastWin = m.daily; }
      buzz([40, 60, 40]);
      toast(`✅ +${delta} pont${bonus ? ` (széria-bónusz +${Math.round(bonus * 100)}%)` : ''}`);
    } else {
      delta = -Math.round(m.points * 0.25);
      S.st.points = Math.max(0, S.st.points + delta); S.st.lost++; S.st.streak = 0;
      if (m.daily) { S.st.dLost++; S.st.dStreak = 0; }
      S.punish = { t: m.punish, map: m.map };
      buzz(300);
      toast(`💀 ${delta} pont. Jön a büntetés.`);
    }
    const mm = S.maps[m.mapId] || (S.maps[m.mapId] = { w: 0, l: 0 });
    ok ? mm.w++ : mm.l++;
    S.hist.unshift({ ok, map: m.map, obj: m.objective.t, pts: delta, diff: m.diff, daily: !!m.daily, at: Date.now(),
      dur: slot.startedAt ? Date.now() - slot.startedAt : null });
    S.hist = S.hist.slice(0, 60);
    if (ctx === 'gen') S.gen = null; else S.daily.state = ok ? 'won' : 'lost';
    save(); render();
  }

  function flee() {
    const m = S.gen.m;
    const pen = Math.round(m.points * 0.1);
    S.st.points = Math.max(0, S.st.points - pen); S.st.fled++; S.st.streak = 0;
    S.hist.unshift({ ok: false, fled: true, map: m.map, obj: 'Megfutamodás', pts: -pen, diff: m.diff, at: Date.now() });
    S.hist = S.hist.slice(0, 60);
    return pen;
  }

  function newMission() {
    const go = () => {
      S.gen = { m: G.generate({ diff: S.diff, players: S.players }), state: 'new', startedAt: null };
      buzz(25); save(); render();
      const out = $('genOut'); if (out.firstElementChild) out.firstElementChild.scrollIntoView({ behavior: 'smooth', block: 'start' });
    };
    if (S.gen && S.gen.state === 'new' && S.gen.m.diff >= 2) {
      confirmBox('Megfutamodás?', `Ezt a szerződést már láttad. Ha újat kérsz, az megfutamodásnak számít: −${Math.round(S.gen.m.points * 0.1)} pont, és nullázódik a szériád (${S.st.streak}).`,
        'Új szerződés', 'Maradok', () => { const p = flee(); toast(`🐔 Megfutamodtál: −${p} pont`); go(); }, true);
    } else go();
  }

  // ---------- Megjelenítés ----------
  function renderGen() {
    $('diffSeg').innerHTML = [1, 2, 3].map(d => `<button data-d="${d}" class="${S.diff === d ? 'on' : ''}">${G.DIFFS[d].icon} ${G.DIFFS[d].name}</button>`).join('');
    $('diffHint').textContent = HINTS[S.diff];
    $('playerSeg').innerHTML = [1, 2, 3, 4, 5].map(n => `<button data-p="${n}" class="${S.players === n ? 'on' : ''}">${n === 1 ? 'Solo' : n + ' fő'}</button>`).join('');
    const locked = S.gen && S.gen.state === 'active';
    document.querySelectorAll('#diffSeg button, #playerSeg button').forEach(b => b.disabled = locked);

    let h = '';
    if (S.punish) {
      h += `<div class="card"><div class="head"><span>Tartozol</span><b>Büntetés</b></div><p class="punish" style="border:0"><b>${esc(S.punish.map)} · ELBUKOTT</b>${esc(S.punish.t)}</p>
        <div class="btns" style="padding:0 12px 12px"><button class="go" id="punDone">Letudtam</button></div></div>`;
    }
    if (!S.gen) {
      h += `<button class="big" id="newBtn">☢️ Szerződés sorsolása</button>`;
      if (!S.punish) h += `<p class="empty">Válassz nehézséget, aztán sorsolj. A szerződést el kell fogadnod a raid előtt – utána nincs visszaút.</p>`;
    } else {
      h += missionHtml(S.gen.m, 'gen', S.gen.state);
      if (S.gen.state === 'new') {
        h += `<div class="btns"><button id="shareBtn">📋 Másolás</button><button class="go" id="acceptBtn">Elfogadom, indul a raid</button></div>`;
        h += `<button class="big alt" id="newBtn">Másik szerződés${S.gen.m.diff >= 2 ? ' (megfutamodás)' : ''}</button>`;
      } else {
        h += timerHtml(S.gen.m, S.gen.startedAt);
        h += `<div class="btns"><button class="die" id="failBtn">💀 Elbuktam</button><button class="go" id="winBtn">✅ Kijutottam</button></div>`;
        h += `<div class="btns"><button id="shareBtn">📋 Másolás</button></div>`;
      }
    }
    $('genOut').innerHTML = h;
  }

  function renderDaily() {
    const t = today();
    if (!S.daily || S.daily.date !== t) { S.daily = { date: t, m: G.daily(t), state: 'new', startedAt: null }; save(); }
    const d = S.daily;
    let h = missionHtml(d.m, 'daily', d.state);
    if (d.state === 'new') h += `<div class="btns"><button id="dShare">📋 Másolás</button><button class="go" id="dAccept">Elfogadom, indul a raid</button></div>`;
    else if (d.state === 'active') {
      h += timerHtml(d.m, d.startedAt);
      h += `<div class="btns"><button class="die" id="dFail">💀 Elbuktam</button><button class="go" id="dWin">✅ Kijutottam</button></div>`;
    } else {
      h += `<p class="empty">${d.state === 'won' ? '✅ A mai napi megvan.' : '💀 A mai napi elbukott.'} Holnap jön az új. Napi széria: <b>${S.st.dStreak}</b></p>`;
      h += `<div class="btns"><button id="dShare">📋 Eredmény másolása</button></div>`;
    }
    $('dailyOut').innerHTML = h;
  }

  function renderStats() {
    const st = S.st, rk = G.rank(st.points);
    const tried = st.won + st.lost;
    const prog = rk.next ? Math.min(100, (st.points - rk.min) / (rk.next.at - rk.min) * 100) : 100;
    let h = `<div class="rankbox"><div class="lbl" style="margin:0 0 4px">Rang</div><div class="n">${rk.icon} ${esc(rk.name)}</div>
      <div class="bar"><i style="width:${prog.toFixed(1)}%"></i></div>
      <p class="hint">${rk.next ? `${st.points} / ${rk.next.at} pont a következőig: ${esc(rk.next.name)}` : `${st.points} pont – a csúcson vagy.`}</p></div>`;
    h += `<div class="stats">
      <div><b>${st.points}</b><span>pont</span></div>
      <div><b>${tried ? Math.round(st.won / tried * 100) + '%' : '–'}</b><span>túlélés</span></div>
      <div><b>${st.streak}</b><span>széria</span></div>
      <div><b>${st.won}</b><span>teljesítve</span></div>
      <div><b>${st.lost}</b><span>elbukva</span></div>
      <div><b>${st.best}</b><span>legjobb széria</span></div>
      <div><b>${st.fled}</b><span>megfutamodás</span></div>
      <div><b>${st.dWon}</b><span>napi kész</span></div>
      <div><b>${st.punishDone}</b><span>büntetés letudva</span></div>
    </div>`;
    const mapRows = G.MAPS.filter(m => S.maps[m.id]).map(m => {
      const x = S.maps[m.id];
      return `<div class="hist"><span>${esc(m.name)}</span><span>${x.w} ✅ · ${x.l} 💀</span></div>`;
    });
    if (mapRows.length) h += `<div class="lbl">Pályák</div><div class="card maps" style="margin-top:0">${mapRows.join('')}</div>`;
    h += `<div class="lbl">Előzmények</div>`;
    h += S.hist.length ? `<div class="card" style="margin-top:0">${S.hist.map(x => `<div class="hist"><span>${x.fled ? '🐔' : x.ok ? '✅' : '💀'} <b>${esc(x.map)}</b>${x.daily ? ' · napi' : ''} · ${esc(x.obj)}</span><small>${x.pts > 0 ? '+' : ''}${x.pts}<br>${new Date(x.at).toLocaleDateString('hu-HU', { month: 'short', day: 'numeric' })}</small></div>`).join('')}</div>`
      : `<p class="empty">Még nincs lejátszott szerződés.</p>`;
    h += `<button class="link" id="resetBtn">Profil törlése</button>`;
    $('statsOut').innerHTML = h;
  }

  function renderHeader() { const rk = G.rank(S.st.points); $('hdrRank').innerHTML = `${rk.icon} ${esc(rk.name)}<br>${S.st.points} pont`; }

  function render() {
    renderHeader();
    const tab = document.querySelector('nav button.on').dataset.tab;
    if (tab === 'gen') renderGen(); else if (tab === 'daily') renderDaily(); else renderStats();
  }

  // ---------- Megosztás ----------
  function missionText(m, result) {
    const D = G.DIFFS[m.diff];
    const L = [`☢️ TARKOV HARDCORE – ${m.daily ? 'Napi (' + m.daily + ')' : 'Szerződés #' + String(m.seed).slice(-5)} – ${D.name}`,
      `🗺️ ${m.map} · ${m.time.t}`, `🎯 ${m.objective.t}`, `🚪 ${m.extract.t}`];
    if (m.timeLimit) L.push(`⏱️ ${m.timeLimit} perc`);
    m.rules.forEach(r => L.push(`📜 ${r}`));
    m.players.forEach((p, i) => {
      L.push(`${m.players.length > 1 ? `👤 ${i + 1}. játékos: ` : '🔫 '}${p.weapon}${p.ammo ? ' | ' + p.ammo : ''}`);
      L.push(`   🛡️ ${p.armor} | 💉 ${p.meds} | 🎒 ${p.gear}`);
    });
    L.push(`💀 Ha elbukod: ${m.punish}`, `🏅 ${m.points} pont`);
    if (result) L.push(result);
    return L.join('\n');
  }
  function copy(text) {
    const done = () => toast('📋 Kimásolva – illeszd be a haveroknak');
    const fallback = () => {
      const ta = document.createElement('textarea'); ta.value = text; ta.style.position = 'fixed'; ta.style.opacity = '0';
      document.body.appendChild(ta); ta.select();
      try { document.execCommand('copy'); done(); } catch (e) { toast('Nem sikerült a másolás'); }
      ta.remove();
    };
    if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(text).then(done, fallback); else fallback();
  }

  // ---------- Események ----------
  document.addEventListener('click', e => {
    const b = e.target.closest('button'); if (!b) return;
    if (b.dataset.d && !b.disabled) { S.diff = +b.dataset.d; save(); renderGen(); return; }
    if (b.dataset.p && !b.disabled) { S.players = +b.dataset.p; save(); renderGen(); return; }
    if (b.dataset.rr && S.gen && S.gen.state === 'new') {
      if (S.gen.m.rerollsLeft <= 0) { toast('Elfogyott az újrasorsolás. Ez van.'); return; }
      G.reroll(S.gen.m, b.dataset.rr); S.gen.m.rerollsLeft--; buzz(15); save(); renderGen(); return;
    }
    switch (b.id) {
      case 'newBtn': newMission(); break;
      case 'acceptBtn': S.gen.state = 'active'; S.gen.startedAt = Date.now(); buzz(60); save(); renderGen(); toast('🎯 A szerződés él. Sok szerencsét.'); break;
      case 'winBtn': {
        const m = S.gen.m, late = m.timeLimit && Date.now() - S.gen.startedAt > m.timeLimit * 60000;
        confirmBox('Kijutottál?', late ? 'Lejárt az időlimit. Ha tényleg időn túl jutottál ki, az bukás. Becsületszóra időben voltál kint?' : 'Csak akkor, ha a cél és minden szabály teljesült. Becsületszó?',
          'Igen, minden megvan', 'Mégse', () => finish('gen', true));
        break;
      }
      case 'failBtn': confirmBox('Elbuktál?', 'Meghaltál, megszegtél egy szabályt vagy nem lett meg a cél. Jön a büntetés.', 'Elbuktam', 'Mégse', () => finish('gen', false), true); break;
      case 'shareBtn': copy(missionText(S.gen.m)); break;
      case 'punDone': S.st.punishDone++; S.punish = null; save(); renderGen(); toast('🫡 Becsületes vagy.'); break;
      case 'dAccept': S.daily.state = 'active'; S.daily.startedAt = Date.now(); buzz(60); save(); renderDaily(); break;
      case 'dWin': confirmBox('Napi teljesítve?', 'Csak ha a cél és minden szabály megvan.', 'Igen', 'Mégse', () => finish('daily', true)); break;
      case 'dFail': confirmBox('Napi elbukva?', 'Egy próbálkozás volt. Holnap új jön.', 'Elbuktam', 'Mégse', () => finish('daily', false), true); break;
      case 'dShare': copy(missionText(S.daily.m, S.daily.state === 'won' ? '✅ TELJESÍTVE' : S.daily.state === 'lost' ? '💀 ELBUKVA' : '')); break;
      case 'resetBtn': confirmBox('Profil törlése?', 'Minden pont, statisztika és előzmény törlődik. Nem vonható vissza.', 'Törlés', 'Mégse', () => { S = blank(); save(); render(); toast('Tiszta lap.'); }, true); break;
    }
  });

  // Időzítő frissítése másodpercenként (csak a szöveget írja át).
  setInterval(() => {
    const tab = document.querySelector('nav button.on').dataset.tab;
    const slot = tab === 'gen' ? S.gen : tab === 'daily' ? S.daily : null;
    if (!slot || slot.state !== 'active') return;
    const t = document.querySelector('[data-timer]'); if (!t) return;
    const el = Date.now() - slot.startedAt;
    t.textContent = fmtTime(el);
    const m = slot.m, sub = document.querySelector('[data-timer-sub]');
    if (m.timeLimit) {
      const late = el > m.timeLimit * 60000;
      sub.textContent = late ? 'LEJÁRT AZ IDŐ – ha még bent vagy, ez bukás' : `Hátra: ${fmtTime(m.timeLimit * 60000 - el)}`;
      if (late && !t.parentElement.classList.contains('late')) { t.parentElement.classList.add('late'); buzz([200, 100, 200]); }
    }
  }, 1000);

  render();
})();
