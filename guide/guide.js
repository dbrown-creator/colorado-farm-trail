/* Colorado Local Food Guide: a static, hash-routed draft over the supply network. */
(function () {
  const D = window.GUIDE_DATA;
  const N = D.nodes, E = D.edges, T = D.typeLabel;
  const byId = Object.fromEntries(N.map(n => [n.id, n]));
  const app = document.getElementById('app');
  const TYPES = ['farm', 'maker', 'restaurant', 'retail', 'market', 'distributor'];
  const PRODUCER = new Set(['farm', 'maker']);
  const REGIONS = ['Denver Metro', 'Boulder County', 'Northern Colorado', 'Summit & Mountains', 'Upper Arkansas Valley', 'Roaring Fork',
    'Western Slope', 'Southwest', 'Northwest', 'South & San Luis Valley', 'Eastern Plains', 'Statewide'];
  const STALE_BEFORE = 2020;
  let maps = [];

  const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
  const slug = s => s.toLowerCase().replace(/&/g, 'and').replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '');
  const color = t => `var(--${t})`;
  const cssColor = t => getComputedStyle(document.documentElement).getPropertyValue('--' + t).trim();
  const plural = (n, one, many) => `${n} ${n === 1 ? one : (many || one + 's')}`;
  const where = n => n.lat ? `${n.city} · ${n.region}` : (n.city && n.city !== 'unknown' ? `${n.city} · statewide` : 'Statewide');
  const domain = u => { try { return new URL(u).hostname.replace(/^www\./, ''); } catch { return 'source'; } };
  const typePill = t => `<span class="pill"><i style="background:${color(t)}"></i>${esc(T[t])}</span>`;
  const sup = n => n.sup.map(i => E[i]);   // current edges into n
  const buy = n => n.buy.map(i => E[i]);   // current edges out of n
  const older = n => [...n.supOld.map(i => [E[i], E[i].s]), ...n.buyOld.map(i => [E[i], E[i].b])];
  const isBuyer = n => n.sup.length > 0;

  function avgMiles(edges) {
    const m = edges.map(e => e.mi).filter(v => v != null);
    return m.length ? Math.round(m.reduce((a, b) => a + b, 0) / m.length) : null;
  }

  function factLine(n) {
    if (n.sup.length && !PRODUCER.has(n.type)) {
      const am = avgMiles(sup(n));
      return `Names <b>${plural(n.sup.length, 'Colorado supplier')}</b>${am != null ? ` · avg <b>${am} mi</b> away` : ''}`;
    }
    if (n.buy.length) {
      const towns = new Set(buy(n).map(e => byId[e.b].city)).size;
      return `Found at <b>${plural(n.buy.length, 'place')}</b> in ${plural(towns, 'town')}`;
    }
    if (n.sup.length) return `Names <b>${plural(n.sup.length, 'supplier')}</b>`;
    return `<span class="muted">Older mentions only, not reconfirmed</span>`;
  }

  function card(n) {
    const chips = [];
    if (n.trail) chips.push('<span class="chip trail">On the Farm Trail</span>');
    if (n.sup.length && n.buy.length) chips.push('<span class="chip">Buys &amp; sells local</span>');
    return `<a class="card" href="#/p/${n.id}">${typePill(n.type)}<h3>${esc(n.name)}</h3>
      <div class="where">${esc(where(n))}</div><div class="facts">${factLine(n)}</div>
      ${chips.length ? `<div class="chips">${chips.join('')}</div>` : ''}</a>`;
  }

  /* ---------- maps ---------- */
  // Same public CARTO basemap key as the main map (index.html); it ships in the page by necessity.
  const CARTO_KEY = 'cb1_3vh9_1_2876c53a17aa6fd35517591d';
  function tiles(map) {
    const dark = matchMedia('(prefers-color-scheme: dark)').matches;
    L.tileLayer(`https://basemaps.cartocdn.com/rastertiles/${dark ? 'dark_all' : 'light_all'}/{z}/{x}/{y}{r}.png?key=${CARTO_KEY}`, {
      maxZoom: 17, attribution: '&copy; OpenStreetMap contributors &copy; CARTO'
    }).addTo(map);
  }
  function newMap(el, opts) {
    const map = L.map(el, Object.assign({ scrollWheelZoom: false, zoomControl: true }, opts));
    tiles(map);
    map.setView([39.0, -105.6], 7);
    maps.push(map);
    return map;
  }
  // Businesses in the same town share a centroid; fan them out slightly so pins don't stack.
  const jitterCache = {};
  function pos(n) {
    if (n.trail && n.trail.lat) return [n.lat, n.lng];
    if (jitterCache[n.id]) return jitterCache[n.id];
    let h = 0; for (const c of n.id) h = (h * 31 + c.charCodeAt(0)) >>> 0;
    const a = (h % 360) * Math.PI / 180, r = 0.004 + (h % 7) * 0.0018;
    return (jitterCache[n.id] = [n.lat + r * Math.sin(a), n.lng + r * Math.cos(a)]);
  }
  function dot(n, map, big) {
    return L.circleMarker(pos(n), {
      radius: big ? 9 : 4 + Math.min(6, Math.sqrt(n.sup.length + n.buy.length) * 1.2),
      color: '#fff', weight: 1.2, fillColor: cssColor(n.type), fillOpacity: .9
    }).bindPopup(`<a href="#/p/${n.id}">${esc(n.name)}</a><br><small>${esc(T[n.type])} · ${esc(n.city)}</small>`).addTo(map);
  }

  /* ---------- search ---------- */
  function searchBox(placeholder) {
    return `<div class="search" role="search">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
      <input id="q" type="search" autocomplete="off" placeholder="${esc(placeholder)}" aria-label="Search the guide">
      <ul class="suggest" id="sugg" hidden></ul></div>`;
  }
  function matches(q) {
    q = q.trim().toLowerCase();
    if (!q) return [];
    const towns = [...new Set(N.filter(n => n.lat && n.city.toLowerCase().startsWith(q)).map(n => n.city))]
      .map(c => ({ town: c, count: N.filter(n => n.city === c).length }));
    const names = N.filter(n => n.name.toLowerCase().includes(q))
      .sort((a, b) => (b.name.toLowerCase().startsWith(q) - a.name.toLowerCase().startsWith(q)) || (b.sup.length + b.buy.length) - (a.sup.length + a.buy.length));
    return [...towns.slice(0, 3), ...names.slice(0, 8)];
  }
  function wireSearch() {
    const input = document.getElementById('q'), list = document.getElementById('sugg');
    if (!input) return;
    let hi = -1;
    const render = () => {
      const m = matches(input.value);
      hi = -1;
      list.hidden = !m.length;
      list.innerHTML = m.map(x => x.town
        ? `<li><a href="#/explore?town=${encodeURIComponent(x.town)}"><span>📍 ${esc(x.town)}</span><small>${plural(x.count, 'listing')}</small></a></li>`
        : `<li><a href="#/p/${x.id}"><span>${esc(x.name)}</span><small>${esc(T[x.type])} · ${esc(x.city)}</small></a></li>`).join('');
    };
    input.addEventListener('input', render);
    input.addEventListener('keydown', ev => {
      const items = [...list.querySelectorAll('a')];
      if (ev.key === 'ArrowDown' || ev.key === 'ArrowUp') {
        ev.preventDefault();
        hi = (hi + (ev.key === 'ArrowDown' ? 1 : -1) + items.length) % items.length;
        items.forEach((a, i) => a.classList.toggle('hi', i === hi));
      } else if (ev.key === 'Enter') {
        if (items[hi]) location.hash = items[hi].getAttribute('href');
        else if (input.value.trim()) location.hash = '#/explore?q=' + encodeURIComponent(input.value.trim());
      } else if (ev.key === 'Escape') list.hidden = true;
    });
    document.addEventListener('click', ev => { if (!ev.target.closest('.search')) list.hidden = true; }, { once: true });
  }

  /* ---------- pages ---------- */
  function home() {
    const s = D.stats;
    const restaurants = N.filter(n => n.type === 'restaurant').sort((a, b) => b.sup.length - a.sup.length).slice(0, 8);
    const producers = N.filter(n => PRODUCER.has(n.type)).sort((a, b) => b.buy.length - a.buy.length).slice(0, 8);
    const shops = N.filter(n => n.type === 'retail' && n.sup.length).sort((a, b) => b.sup.length - a.sup.length).slice(0, 4);
    app.innerHTML = `
    <section class="hero"><div class="wrap">
      <div class="kicker">Colorado local food guide</div>
      <h1>Eat Colorado.<br>Know where it grew.</h1>
      <p class="lede">The restaurants, shops and markets that buy from Colorado farms, and where to find each farm's food. Every connection is traced to a menu, stockist list or article you can check.</p>
      ${searchBox('Search a restaurant, farm or town…')}
      <div class="stats">
        <div class="stat"><b>${s.producers}</b><span>farms &amp; makers</span></div>
        <div class="stat"><b>${s.restaurants}</b><span>restaurants</span></div>
        <div class="stat"><b>${s.shops}</b><span>shops &amp; grocers</span></div>
        <div class="stat"><b>${s.links}</b><span>sourced connections</span></div>
      </div>
    </div></section>

    <section><div class="wrap">
      <div class="sec-head"><div><h2>Restaurants that name their farms</h2>
        <p>Chefs who publish where their ingredients come from. Open one to see each farm and how far it travelled.</p></div>
        <a class="more" href="#/explore?type=restaurant">All ${s.restaurants} restaurants →</a></div>
      <div class="grid">${restaurants.map(card).join('')}</div>
    </div></section>

    <section><div class="wrap">
      <div class="sec-head"><div><h2>Producers on the most menus</h2>
        <p>Farms, ranches and makers you can taste all over the state, without driving to the farm.</p></div>
        <a class="more" href="#/explore?type=farm">All producers →</a></div>
      <div class="grid">${producers.map(card).join('')}</div>
    </div></section>

    <section><div class="wrap">
      <div class="sec-head"><div><h2>Shop local, at the store</h2>
        <p>Grocers and co-ops that stock named Colorado producers.</p></div>
        <a class="more" href="#/explore?type=retail">All shops →</a></div>
      <div class="grid">${shops.map(card).join('')}</div>
    </div></section>

    <section><div class="wrap">
      <div class="sec-head"><div><h2>Eat local by region</h2><p>From Front Range farm-to-table to Western Slope orchards.</p></div>
        <a class="more" href="#/regions">All regions →</a></div>
      ${regionTiles()}
    </div></section>

    ${PL.length ? `<section><div class="wrap">
      <div class="sec-head"><div><h2>Plan a day of local food</h2>
        <p>Farm visits, a lunch and a dinner that name their farms, and the events worth timing a trip around.</p></div>
        <a class="more" href="#/events">All events →</a></div>
      <div class="grid">${PL.map(p => `<a class="card plan-card" href="#/plan/${p.id}"><span class="pill"><i style="background:var(--gold)"></i>Day plan</span>
        <h3>${esc(p.title)}</h3><div class="where">${esc(p.region)} · ${esc(p.best)}</div><div class="facts">${plural(p.stops.length, 'stop')} · ${esc(p.lede)}</div></a>`).join('')}</div>
    </div></section>` : ''}

    <section><div class="wrap">
      <h2>How the guide works</h2>
      <div class="how">
        <div><b>1</b><h3>We follow the food</h3><p class="muted">Starting from a chef's supplier list, we trace each farm to everywhere else it sells, and each buyer to its other farms.</p></div>
        <div><b>2</b><h3>Every link has a source</h3><p class="muted">A menu, a stockist page, a farm's "where to buy" list or a news story. Tap the source on any listing to check it yourself.</p></div>
        <div><b>3</b><h3>We re-check what's old</h3><p class="muted">Links are rated high, medium or low confidence. Anything from before ${STALE_BEFORE} gets re-checked: closed businesses come off, and links we can't reconfirm move to "older mentions".</p></div>
      </div>
    </div></section>

    <section><div class="wrap"><div class="cta">
      <div><h2>Do you grow, cook or sell Colorado food?</h2><p>Tell us who you buy from or sell to and we'll add the connection.</p></div>
      <a class="btn" href="#/about">Get listed</a>
    </div></div></section>`;
    wireSearch();
  }

  function regionStats(r) {
    const ns = N.filter(n => n.region === r);
    const by = Object.fromEntries(TYPES.map(t => [t, ns.filter(n => n.type === t).length]));
    // Of the links into this region's buyers, how many come from producers in the same region.
    const inbound = ns.flatMap(sup);
    const local = inbound.filter(e => byId[e.s].region === r).length;
    return { ns, by, inbound: inbound.length, local };
  }
  function regionTiles() {
    return `<div class="regions">${REGIONS.filter(r => r !== 'Statewide').map(r => {
      const st = regionStats(r);
      if (!st.ns.length) return '';
      const bar = TYPES.map(t => st.by[t] ? `<i style="flex:${st.by[t]};background:${color(t)}"></i>` : '').join('');
      return `<a class="region" href="#/region/${slug(r)}"><b>${esc(r)}</b><div class="bar">${bar}</div>
        <small>${plural(st.ns.length, 'listing')} · ${plural(st.by.restaurant, 'restaurant')} · ${plural(st.by.farm + st.by.maker, 'producer')}</small></a>`;
    }).join('')}</div>`;
  }

  function regionsPage() {
    app.innerHTML = `<section><div class="wrap">
      <div class="kicker">Regions</div><h1>Eat local by region</h1>
      <p class="muted" style="max-width:640px">Each bar shows the mix of farms, makers, restaurants and shops we've traced in that part of the state.</p>
      <div class="legend">${TYPES.map(t => `<span><i style="background:${color(t)}"></i>${esc(T[t])}</span>`).join('')}</div>
      ${regionTiles()}
      <div class="map" id="rmap" style="height:460px;border-radius:14px;overflow:hidden;border:1px solid var(--line);margin-top:24px"></div>
    </div></section>`;
    const map = newMap('rmap');
    N.filter(n => n.lat).forEach(n => dot(n, map));
  }

  function regionPage(rs) {
    const r = REGIONS.find(x => slug(x) === rs);
    if (!r) return notFound();
    const st = regionStats(r);
    const pct = st.inbound ? Math.round(100 * st.local / st.inbound) : null;
    const feeders = {};
    st.ns.flatMap(sup).forEach(e => { feeders[e.s] = (feeders[e.s] || 0) + 1; });
    const topFeeders = Object.entries(feeders).sort((a, b) => b[1] - a[1]).slice(0, 6).map(([id]) => byId[id]);
    const block = (title, list) => list.length ? `<div class="group"><h2>${title}</h2><div class="grid">${list.map(card).join('')}</div></div>` : '';
    const sortConn = (a, b) => (b.sup.length + b.buy.length) - (a.sup.length + a.buy.length);
    const plan = PL.find(p => p.region === r), evs = EV.filter(e => e.region === r);
    app.innerHTML = `
    <div class="place-head"><div class="wrap">
      <div class="crumbs"><a href="#/regions">Regions</a> / ${esc(r)}</div>
      <h1>${esc(r)}</h1>
      <p class="headline">${r === 'Statewide'
        ? `${plural(st.ns.length, 'business', 'businesses')} that sell across Colorado or don't list one home town.`
        : `${plural(st.ns.length, 'listing')} in ${plural(new Set(st.ns.map(n => n.city)).size, 'town')}.`}
      ${pct != null && r !== 'Statewide' ? `Of the <b>${st.inbound}</b> traced ingredients flowing into ${esc(r)} kitchens and shops, <b>${pct}%</b> come from producers in the region.` : ''}</p>
    </div></div>
    <div class="wrap"><div class="place-body"><div>
      ${plan ? `<a class="plan-cta" href="#/plan/${plan.id}"><span class="kicker">Plan a day</span><b>${esc(plan.title)}</b><span class="muted">${esc(plan.best)} · ${plan.stops.length} stops</span></a>` : ''}
      ${block('Where to eat', st.ns.filter(n => n.type === 'restaurant').sort(sortConn))}
      ${block('Where to shop', st.ns.filter(n => n.type === 'retail' || n.type === 'market').sort(sortConn))}
      ${block('Who grows and makes it', st.ns.filter(n => PRODUCER.has(n.type)).sort(sortConn))}
      ${block('Distributors &amp; food hubs', st.ns.filter(n => n.type === 'distributor'))}
      ${evs.length ? `<div class="group"><h2>Events</h2><div class="grid">${evs.map(evCard).join('')}</div></div>` : ''}
    </div><aside class="side">
      <div class="minimap" id="rgmap"></div>
      ${topFeeders.length ? `<div class="box"><h3>Who feeds ${esc(r)}</h3><p class="muted" style="margin-top:0;font-size:.9rem">Producers named most often by this region's restaurants and shops.</p>
        <ul class="links">${topFeeders.map(n => `<li><a class="nm" href="#/p/${n.id}">${esc(n.name)}</a><span class="meta">${esc(n.city)} · ${plural(feeders[n.id], 'buyer')} here</span></li>`).join('')}</ul></div>` : ''}
    </aside></div></div>`;
    const map = newMap('rgmap');
    const pts = st.ns.filter(n => n.lat);
    pts.forEach(n => dot(n, map));
    if (pts.length) map.fitBounds(L.latLngBounds(pts.map(pos)).pad(0.25), { maxZoom: 11 });
  }

  function explore(params) {
    const state = {
      q: params.get('q') || '', type: params.get('type') || '', region: params.get('region') || '',
      town: params.get('town') || '', sort: params.get('sort') || 'conn', trail: params.get('trail') === '1'
    };
    if (state.type === 'farm') state.type = 'producer';
    app.innerHTML = `<section><div class="wrap">
      <div class="kicker">Explore</div><h1>Find Colorado food</h1>
      <div class="filters">
        <input id="fq" type="search" placeholder="Name or town" value="${esc(state.q || state.town)}" aria-label="Filter by name or town">
        <select id="fr" aria-label="Region"><option value="">All regions</option>${REGIONS.map(r => `<option ${r === state.region ? 'selected' : ''}>${esc(r)}</option>`).join('')}</select>
        <select id="fs" aria-label="Sort"><option value="conn">Most connected</option><option value="az" ${state.sort === 'az' ? 'selected' : ''}>A–Z</option></select>
        <label class="muted" style="font-size:.9rem"><input type="checkbox" id="ft" ${state.trail ? 'checked' : ''}> On the Farm Trail map</label>
      </div>
      <div class="typebtns" id="ftype">
        <button data-t="" class="${!state.type ? 'on' : ''}">All</button>
        <button data-t="producer" class="${state.type === 'producer' ? 'on' : ''}"><i style="background:var(--farm)"></i>Farms &amp; makers</button>
        ${['restaurant', 'retail', 'market', 'distributor'].map(t => `<button data-t="${t}" class="${state.type === t ? 'on' : ''}"><i style="background:${color(t)}"></i>${esc(T[t])}</button>`).join('')}
      </div>
      <div class="explore" style="margin-top:16px">
        <div><div class="count" id="fcount"></div><div class="grid" id="flist"></div></div>
        <div class="map" id="emap"></div>
      </div>
    </div></section>`;
    const map = newMap('emap');
    const layer = L.layerGroup().addTo(map);
    const run = () => {
      const q = state.q.trim().toLowerCase();
      let list = N.filter(n =>
        (!state.type || (state.type === 'producer' ? PRODUCER.has(n.type) : n.type === state.type)) &&
        (!state.region || n.region === state.region) &&
        (!state.trail || n.trail) &&
        (!q || n.name.toLowerCase().includes(q) || n.city.toLowerCase().includes(q)));
      list.sort(state.sort === 'az' ? (a, b) => a.name.localeCompare(b.name)
        : (a, b) => (b.sup.length + b.buy.length) - (a.sup.length + a.buy.length));
      document.getElementById('fcount').textContent = `${plural(list.length, 'listing')}${list.length > 120 ? ' · showing the first 120' : ''}`;
      document.getElementById('flist').innerHTML = list.slice(0, 120).map(card).join('') || '<div class="empty">Nothing matches yet. Try a nearby town or clear a filter.</div>';
      layer.clearLayers();
      const pts = list.filter(n => n.lat);
      pts.forEach(n => dot(n, layer));
      if (pts.length) map.fitBounds(L.latLngBounds(pts.map(pos)).pad(0.15), { maxZoom: 11 });
      const p = new URLSearchParams();
      if (state.q) p.set('q', state.q); if (state.type) p.set('type', state.type);
      if (state.region) p.set('region', state.region); if (state.sort !== 'conn') p.set('sort', state.sort);
      if (state.trail) p.set('trail', '1');
      history.replaceState(null, '', '#/explore' + (p.toString() ? '?' + p : ''));
    };
    if (state.town) state.q = state.town;
    document.getElementById('fq').addEventListener('input', e => { state.q = e.target.value; run(); });
    document.getElementById('fr').addEventListener('change', e => { state.region = e.target.value; run(); });
    document.getElementById('fs').addEventListener('change', e => { state.sort = e.target.value; run(); });
    document.getElementById('ft').addEventListener('change', e => { state.trail = e.target.checked; run(); });
    document.getElementById('ftype').addEventListener('click', e => {
      const b = e.target.closest('button'); if (!b) return;
      state.type = b.dataset.t;
      document.querySelectorAll('#ftype button').forEach(x => x.classList.toggle('on', x === b));
      run();
    });
    run();
  }

  function linkRow(e, otherId) {
    const o = byId[otherId];
    const stale = e.y && e.y < STALE_BEFORE && !e.old;
    const bits = [esc(T[o.type]), esc(o.city && o.city !== 'unknown' ? o.city : 'statewide')];
    if (e.mi != null) bits.push(`${e.mi} mi`);
    if (e.note) bits.push(esc(e.note));
    return `<li class="${e.c}"><a class="nm" href="#/p/${o.id}">${esc(o.name)}</a>
      <span class="ev"><span class="conf ${e.c}" title="${e.c} confidence">${e.c}</span><br>
        <a href="${esc(e.src)}" target="_blank" rel="noopener">${esc(domain(e.src))}${e.y ? ', ' + e.y : ''} ↗</a>
        ${stale ? '<br><span class="stale">older source</span>' : ''}</span>
      <span class="meta">${bits.join(' · ')}</span></li>`;
  }
  function grouped(edges, side, title, emptyText) {
    if (!edges.length) return emptyText ? `<div class="group"><h2>${title}</h2><div class="empty">${emptyText}</div></div>` : '';
    const rank = { high: 0, medium: 1, low: 2 };
    const groups = {};
    edges.forEach(e => { const t = byId[e[side]].type; (groups[t] = groups[t] || []).push(e); });
    const order = side === 's' ? ['farm', 'maker', 'distributor', 'market', 'retail', 'restaurant'] : ['restaurant', 'retail', 'market', 'distributor', 'maker', 'farm'];
    return `<div class="group"><h2>${title}</h2>${order.filter(t => groups[t]).map(t => `
      <h3><i style="background:${color(t)}"></i>${esc(T[t])} <span class="muted" style="font-family:Inter;font-weight:400;font-size:.9rem">(${groups[t].length})</span></h3>
      <ul class="links">${groups[t].sort((a, b) => rank[a.c] - rank[b.c] || (a.mi ?? 999) - (b.mi ?? 999)).map(e => linkRow(e, e[side])).join('')}</ul>`).join('')}</div>`;
  }

  // Links from pre-2020 press that a later re-check couldn't confirm: both businesses
  // still operate, but no current source names the connection.
  function olderSection(n) {
    const rows = older(n);
    if (!rows.length) return '';
    return `<details class="group older"${!n.sup.length && !n.buy.length ? ' open' : ''}>
      <summary><h3>Older mentions <span class="muted" style="font-family:Inter;font-weight:400;font-size:.9rem">(${rows.length})</span></h3></summary>
      <p class="muted" style="font-size:.9rem;margin-top:0">These come from press before ${STALE_BEFORE}. Both businesses are still open, but when we re-checked on ${esc(D.stats.rechecked)} no current menu, stockist list or article named the connection. Ask before you count on it.</p>
      <ul class="links">${rows.map(([e, oid]) => linkRow(e, oid)).join('')}</ul></details>`;
  }

  // Businesses that share at least one supplier (for buyers) or one buyer (for producers).
  function kin(n) {
    const score = {};
    if (n.sup.length) sup(n).forEach(e => buy(byId[e.s]).forEach(f => { if (f.b !== n.id) score[f.b] = (score[f.b] || 0) + 1; }));
    else buy(n).forEach(e => sup(byId[e.b]).forEach(f => { if (f.s !== n.id) score[f.s] = (score[f.s] || 0) + 1; }));
    return Object.entries(score).map(([id, c]) => [byId[id], c])
      .filter(([o]) => n.sup.length ? o.type === n.type || (n.type !== 'restaurant' && o.type !== 'restaurant') : PRODUCER.has(o.type))
      .sort((a, b) => b[1] - a[1]).slice(0, 5);
  }

  function place(id) {
    const n = byId[id];
    if (!n) return notFound();
    const ins = sup(n), outs = buy(n);
    const am = avgMiles(ins);
    const localIns = ins.filter(e => e.mi != null && e.mi <= 100).length;
    let head = '';
    if (ins.length && !PRODUCER.has(n.type)) {
      const dist = am == null ? '' : am < 5 ? ', right in town' : `, on average <b>${am} miles</b> away`;
      const near = ins.length < 2 || !localIns ? '' : localIns === ins.length ? ' All are within 100 miles.' : ` ${localIns} of them are within 100 miles.`;
      head = `Buys from <b>${plural(ins.length, 'Colorado supplier')}</b>${dist}.${near}`;
    } else if (outs.length) {
      const towns = new Set(outs.map(e => byId[e.b].city)).size;
      const eat = outs.filter(e => byId[e.b].type === 'restaurant').length;
      const shop = outs.filter(e => ['retail', 'market'].includes(byId[e.b].type)).length;
      head = `Find it at <b>${plural(outs.length, 'place')}</b> across ${plural(towns, 'town')}${eat || shop ? `: ${[eat && plural(eat, 'restaurant'), shop && plural(shop, 'shop or market', 'shops and markets')].filter(Boolean).join(' and ')}` : ''}.`;
    }
    if (ins.length && PRODUCER.has(n.type)) head += ` Sources from ${plural(ins.length, 'other producer')}.`;
    if (!ins.length && !outs.length) head = 'Only older press mentions so far. We couldn\'t reconfirm them in 2026.';
    const k = kin(n);
    const t = n.trail;
    app.innerHTML = `
    <div class="place-head"><div class="wrap">
      <div class="crumbs"><a href="#/explore">Explore</a> / <a href="#/region/${slug(n.region)}">${esc(n.region)}</a> / ${esc(n.name)}</div>
      ${typePill(n.type)} ${t ? '<span class="chip trail" style="margin-left:6px">On the Farm Trail</span>' : ''}
      <h1 style="margin-top:8px">${esc(n.name)}</h1>
      <p class="headline">${esc(n.city && n.city !== 'unknown' ? n.city : 'Statewide')}${n.lat ? ' · ' + esc(n.region) : ''}${head ? '<br>' + head : ''}</p>
    </div></div>
    <div class="wrap"><div class="place-body"><div>
      ${PRODUCER.has(n.type) || !ins.length
        ? grouped(outs, 'b', 'Where to find it', PRODUCER.has(n.type) ? "We haven't traced where this producer sells yet." : '') + grouped(ins, 's', 'Where it comes from', '')
        : grouped(ins, 's', 'Where the food comes from', '') + grouped(outs, 'b', 'Also sells to', '')}
      ${olderSection(n)}
    </div><aside class="side">
      ${n.lat ? '<div class="minimap" id="pmap"></div>' : ''}
      ${t ? `<div class="box"><h3>Visit the farm</h3><dl class="kv">
        ${t.category ? `<dt>Type</dt><dd>${esc(t.category)}</dd>` : ''}
        ${t.address ? `<dt>Address</dt><dd>${esc(t.address)}, ${esc(n.city)}</dd>` : ''}
        ${t.monthsOpen && t.monthsOpen.length ? `<dt>Season</dt><dd>${esc(t.monthsOpen[0])} – ${esc(t.monthsOpen[t.monthsOpen.length - 1])}</dd>` : ''}
        ${t.hours ? `<dt>Hours</dt><dd>${esc(t.hours.split(';').slice(0, 3).join(';'))}${t.hours.split(';').length > 3 ? '…' : ''}</dd>` : ''}
        ${t.website ? `<dt>Website</dt><dd><a href="${esc(t.website)}" target="_blank" rel="noopener">${esc(domain(t.website))} ↗</a></dd>` : ''}
        </dl>
        ${t.products && t.products.length ? `<div class="tags" style="margin-top:10px">${t.products.slice(0, 14).map(p => `<span class="chip">${esc(p)}</span>`).join('')}${t.products.length > 14 ? `<span class="chip">+${t.products.length - 14}</span>` : ''}</div>` : ''}
        <p style="margin-bottom:0"><a class="btn" href="https://coloradofarmtrail.com" target="_blank" rel="noopener">Plan a stop on the Farm Trail</a></p></div>` : ''}
      ${k.length ? `<div class="box"><h3>${n.sup.length && !PRODUCER.has(n.type) ? 'Shares farms with' : 'Often on the same menus'}</h3>
        <ul class="links">${k.map(([o, c]) => `<li><a class="nm" href="#/p/${o.id}">${esc(o.name)}</a><span class="meta">${esc(T[o.type])} · ${esc(o.city)} · ${c} in common</span></li>`).join('')}</ul></div>` : ''}
      <div class="box"><h3>Is this right?</h3><p class="muted" style="margin:0 0 10px;font-size:.92rem">Links come from public sources and can go stale. If you run ${esc(n.name)}, tell us who you buy from or sell to.</p>
        <a class="btn ghost" href="#/about">Suggest a correction</a></div>
    </aside></div></div>`;
    if (n.lat) {
      const map = newMap('pmap');
      const me = pos(n);
      const pts = [me];
      [...ins.map(e => [e, e.s]), ...outs.map(e => [e, e.b])].forEach(([e, oid]) => {
        const o = byId[oid];
        if (!o.lat) return;
        const p = pos(o); pts.push(p);
        L.polyline([me, p], { color: cssColor(o.type), weight: e.c === 'high' ? 2 : 1.2, opacity: .55, dashArray: e.c === 'high' ? null : '4 4' }).addTo(map);
        dot(o, map);
      });
      older(n).forEach(([e, oid]) => {
        const o = byId[oid];
        if (!o || !o.lat) return;
        const p = pos(o); pts.push(p);
        L.polyline([me, p], { color: cssColor('muted'), weight: 1, opacity: .4, dashArray: '2 5' }).addTo(map);
        dot(o, map).setStyle({ fillOpacity: .35 });
      });
      if (pts.length > 1) map.fitBounds(L.latLngBounds(pts).pad(0.2), { maxZoom: 11 }); else map.setView(me, 10);
      dot(n, map, true).bindTooltip(esc(n.name), { permanent: true, direction: 'top', offset: [0, -8] });
    }
    window.scrollTo(0, 0);
  }

  function network() {
    app.innerHTML = `<section><div class="wrap">
      <div class="sec-head"><div><div class="kicker">The web</div><h1>Colorado's food web</h1>
        <p>Every dot is a business; every line is a published supplier link, pointing the way food flows. Drag to explore, scroll to zoom, click a dot to open it.</p></div>
        <div class="search" style="margin:0;min-width:260px"><input id="nq" type="search" placeholder="Highlight a business" aria-label="Highlight a business" style="padding-left:18px"></div></div>
      <div class="legend">${TYPES.map(t => `<span><i style="background:${color(t)}"></i>${esc(T[t])}</span>`).join('')}<span class="muted">· dashed = medium/low confidence</span></div>
      <div class="net-wrap" id="net"><div class="tip" id="tip"></div></div>
    </div></section>`;
    const wrap = document.getElementById('net'), tip = document.getElementById('tip');
    const W = wrap.clientWidth, H = wrap.clientHeight;
    const nodes = N.map(n => ({ id: n.id, n, deg: n.sup.length + n.buy.length }));
    const links = E.filter(e => byId[e.s] && byId[e.b]).map(e => ({ source: e.s, target: e.b, c: e.old ? 'old' : e.c }));
    const svg = d3.select(wrap).append('svg').attr('viewBox', [0, 0, W, H]);
    svg.append('defs').append('marker').attr('id', 'arr').attr('viewBox', '0 -4 8 8').attr('refX', 8).attr('markerWidth', 5).attr('markerHeight', 5).attr('orient', 'auto')
      .append('path').attr('d', 'M0,-4L8,0L0,4').attr('fill', cssColor('muted'));
    const g = svg.append('g');
    svg.call(d3.zoom().scaleExtent([.3, 6]).on('zoom', ev => g.attr('transform', ev.transform)));
    const r = d => 3 + Math.sqrt(d.deg) * 1.6;
    const link = g.append('g').attr('stroke', cssColor('muted')).attr('stroke-opacity', .28).selectAll('line').data(links).join('line')
      .attr('stroke-dasharray', d => d.c === 'high' ? null : '3 3');
    const node = g.append('g').selectAll('circle').data(nodes).join('circle')
      .attr('r', r).attr('fill', d => cssColor(d.n.type)).attr('stroke', cssColor('panel')).attr('stroke-width', 1).style('cursor', 'pointer')
      .on('click', (ev, d) => { location.hash = '#/p/' + d.id; })
      .on('mouseenter', (ev, d) => {
        tip.innerHTML = `<b>${esc(d.n.name)}</b><br>${esc(T[d.n.type])} · ${esc(d.n.city)}<br>${d.n.sup.length} suppliers · ${d.n.buy.length} buyers`;
        tip.style.opacity = 1; focus(d.id);
      })
      .on('mousemove', ev => { const b = wrap.getBoundingClientRect(); tip.style.left = (ev.clientX - b.left + 12) + 'px'; tip.style.top = (ev.clientY - b.top + 12) + 'px'; })
      .on('mouseleave', () => { tip.style.opacity = 0; focus(null); })
      .call(d3.drag().on('start', (ev, d) => { if (!ev.active) sim.alphaTarget(.2).restart(); d.fx = d.x; d.fy = d.y; })
        .on('drag', (ev, d) => { d.fx = ev.x; d.fy = ev.y; })
        .on('end', (ev, d) => { if (!ev.active) sim.alphaTarget(0); d.fx = null; d.fy = null; }));
    const labels = g.append('g').selectAll('text').data(nodes.filter(d => d.deg >= 9)).join('text')
      .text(d => d.n.name).attr('font-size', 10).attr('fill', cssColor('ink')).attr('pointer-events', 'none').attr('dx', d => r(d) + 3).attr('dy', 3)
      .attr('paint-order', 'stroke').attr('stroke', cssColor('panel')).attr('stroke-width', 3);
    const sim = d3.forceSimulation(nodes)
      .force('link', d3.forceLink(links).id(d => d.id).distance(38).strength(.5))
      .force('charge', d3.forceManyBody().strength(-46))
      .force('center', d3.forceCenter(W / 2, H / 2))
      .force('x', d3.forceX(W / 2).strength(.05)).force('y', d3.forceY(H / 2).strength(.07))
      .force('collide', d3.forceCollide().radius(d => r(d) + 1.5))
      .on('tick', () => {
        link.attr('x1', d => d.source.x).attr('y1', d => d.source.y).attr('x2', d => d.target.x).attr('y2', d => d.target.y);
        node.attr('cx', d => d.x).attr('cy', d => d.y);
        labels.attr('x', d => d.x).attr('y', d => d.y);
      });
    function focus(id, ids) {
      if (!id && !ids) { node.attr('opacity', 1); link.attr('stroke-opacity', .28).attr('marker-end', null); labels.attr('opacity', 1); return; }
      const keep = ids || new Set([id, ...links.filter(l => l.source.id === id || l.target.id === id).flatMap(l => [l.source.id, l.target.id])]);
      node.attr('opacity', d => keep.has(d.id) ? 1 : .12);
      labels.attr('opacity', d => keep.has(d.id) ? 1 : .1);
      link.attr('stroke-opacity', l => keep.has(l.source.id) && keep.has(l.target.id) && (!id || l.source.id === id || l.target.id === id) ? .8 : .04)
        .attr('marker-end', l => id && (l.source.id === id || l.target.id === id) ? 'url(#arr)' : null);
    }
    document.getElementById('nq').addEventListener('input', e => {
      const q = e.target.value.trim().toLowerCase();
      if (!q) return focus(null);
      const hits = nodes.filter(d => d.n.name.toLowerCase().includes(q));
      if (hits.length === 1) focus(hits[0].id); else focus(null, new Set(hits.map(d => d.id)));
    });
  }

  /* ---------- day plans & events ---------- */
  const EV = D.events || [], PL = D.plans || [];
  const evById = Object.fromEntries(EV.map(e => [e.id, e]));
  const byName = Object.fromEntries(N.map(n => [n.name, n]));
  const KIND = { farm: 'On the farm', food: 'Food festival', ranch: 'Ranch & rodeo', community: 'Community' };
  const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
  const fmtDay = (d, year) => new Date(d + 'T12:00').toLocaleDateString('en-US', Object.assign({ month: 'short', day: 'numeric' }, year ? { year: 'numeric' } : {}));
  function evDates(e) {
    if (e.status === 'canceled') return `${e.start ? e.start.slice(0, 4) + ' ' : ''}edition canceled`;
    if (!e.start) return 'Dates not yet announced';
    if (!e.end || e.end === e.start) return fmtDay(e.start, true);
    return `${fmtDay(e.start)} – ${fmtDay(e.end, true)}`;
  }
  function evCard(e) {
    const flag = e.status === 'canceled' ? '<span class="chip warn">Canceled this year</span>'
      : e.status === 'dates-pending' ? '<span class="chip">Dates TBA</span>' : '';
    const h = byName[e.host];
    return `<div class="card ev-card"><span class="pill"><i class="k-${esc(e.kind)}"></i>${esc(KIND[e.kind] || e.kind)}</span>
      <h3>${esc(e.name)}</h3>
      <div class="where">${esc(e.town)} · ${esc(e.season)}</div>
      <p class="ev-desc">${esc(e.desc)}</p>
      <div class="facts"><b>${esc(evDates(e))}</b>${e.recur ? `<br><span class="muted">${esc(e.recur)}</span>` : ''}</div>
      <div class="facts muted">${esc(e.venue)}${h ? ` · hosted by <a href="#/p/${h.id}">${esc(h.name)}</a>` : ''}</div>
      <div class="chips">${flag}<a class="chip" href="${esc(e.url)}" target="_blank" rel="noopener">${esc(domain(e.url))} ↗</a></div></div>`;
  }

  // A stop's place: a guide listing (node), a Farm Trail listing, or an event.
  function placeOf(p) {
    if (p.event) {
      const e = evById[p.event];
      return { name: e.name, city: e.town, kind: KIND[e.kind], href: e.url, ext: true, extra: `${e.season} · ${e.recur}` };
    }
    const n = p.node ? byId[p.node] : null;
    if (n && !p.name) {
      const names = sup(n).filter(e => e.c !== 'low').map(e => byId[e.s].name);
      return {
        name: n.name, city: n.city, kind: T[n.type], href: `#/p/${n.id}`, ll: n.lat ? pos(n) : null,
        extra: names.length ? `Buys from ${names.slice(0, 4).join(', ')}${names.length > 4 ? ` and ${names.length - 4} more` : ''}` : ''
      };
    }
    return {
      name: p.name, city: p.city, kind: p.kind, href: n ? `#/p/${n.id}` : p.website, ext: !n,
      ll: p.lat ? [p.lat, p.lng] : null, approx: p.approx, address: p.address, hours: p.hours
    };
  }
  const placeLink = pl => `<a href="${esc(pl.href || '#')}"${pl.ext ? ' target="_blank" rel="noopener"' : ''}>${esc(pl.name)}${pl.ext ? ' ↗' : ''}</a>`;
  function placeMeta(pl) {
    const rows = [`${esc(pl.kind)} · ${esc(pl.city)}`];
    if (pl.address) rows.push(`${esc(pl.address)}, ${esc(pl.city)}`);
    if (pl.hours) rows.push(esc(pl.hours));
    if (pl.extra) rows.push(esc(pl.extra));
    return rows.map(r => `<div class="stop-meta">${r}</div>`).join('');
  }

  function plansIndex() {
    if (PL.length === 1) { location.replace('#/plan/' + PL[0].id); return; }
    app.innerHTML = `<section><div class="wrap"><div class="kicker">Plan a day</div><h1>Day plans</h1>
      <div class="grid">${PL.map(p => `<a class="card" href="#/plan/${p.id}"><h3>${esc(p.title)}</h3><div class="where">${esc(p.region)}</div><div class="facts">${esc(p.best)}</div></a>`).join('')}</div></div></section>`;
  }

  function planPage(id) {
    const p = PL.find(x => x.id === id);
    if (!p) return notFound();
    const evs = EV.filter(e => e.region === p.region);
    const num = (s, i) => s.time === 'Or' ? 'or' : String(i + 1);
    const stops = p.stops.map((s, i) => {
      const pl = placeOf(s.place);
      const alts = (s.alt || []).map(a => {
        const ap = placeOf(a.place);
        return `<li><b>${placeLink(ap)}</b> <span class="muted">· ${esc(ap.kind)} · ${esc(ap.city)}</span><br>${esc(a.why)}</li>`;
      }).join('');
      return `<li class="stop" id="stop-${i + 1}">
        <div class="stop-dot${s.time === 'Or' ? ' alt' : ''}">${num(s, i)}</div>
        <div class="stop-body">
          <div class="stop-time">${esc(s.time === 'Or' ? (s.label || 'Or') : s.time)}</div>
          <h3>${esc(s.title)}</h3>
          <div class="stop-place">${placeLink(pl)}</div>
          ${placeMeta(pl)}
          <p>${esc(s.why)}</p>
          ${s.tip ? `<p class="tip">${esc(s.tip)}</p>` : ''}
          ${alts ? `<div class="alts"><div class="alts-h">${s.time === 'Or' ? 'Or instead' : 'Swap it for'}</div><ul>${alts}</ul></div>` : ''}
        </div></li>`;
    }).join('');
    const pantry = p.pantry ? `<div class="box"><h3>${esc(p.pantry.title)}</h3><p class="muted" style="margin-top:0;font-size:.92rem">${esc(p.pantry.why)}</p>
      <ul class="links">${p.pantry.places.map(r => { const pl = placeOf(r); return `<li>${placeLink(pl)}<span class="meta">${esc(pl.kind)} · ${esc(pl.city)}${pl.extra ? ' · ' + esc(pl.extra) : ''}</span></li>`; }).join('')}</ul></div>` : '';
    app.innerHTML = `
    <div class="place-head"><div class="wrap">
      <div class="crumbs"><a href="#/region/${slug(p.region)}">${esc(p.region)}</a> / Plan a day</div>
      <div class="kicker">Plan a day</div>
      <h1>${esc(p.title)}</h1>
      <p class="headline">${esc(p.lede)}</p>
      <div class="plan-facts"><span><b>Best</b> ${esc(p.best)}</span><span><b>Route</b> ${esc(p.route)}</span></div>
    </div></div>
    <div class="wrap"><div class="place-body"><div>
      <ol class="timeline">${stops}</ol>
      ${evs.length ? `<div class="group"><h2>Time your visit</h2><p class="muted">Local food and ranch events through the ${esc(p.region)} year.</p>
        <div class="grid">${evs.map(evCard).join('')}</div></div>` : ''}
    </div><aside class="side">
      <div class="minimap plan-map" id="plmap"></div>
      ${pantry}
      <div class="box"><h3>Where this plan comes from</h3><p class="muted" style="margin:0;font-size:.92rem">Built from the <a href="${esc(p.inspired.url)}" target="_blank" rel="noopener">${esc(p.inspired.label)} ↗</a>. ${esc(p.inspired.note)} Each “buys from” line is sourced on the listing's page. Hours change, so check before you go.</p></div>
    </aside></div></div>`;
    const map = newMap('plmap');
    const route = [], all = [];
    p.stops.forEach((s, i) => {
      const pl = placeOf(s.place);
      if (!pl.ll) return;
      all.push(pl.ll);
      if (s.time !== 'Or') route.push(pl.ll);
      L.marker(pl.ll, { icon: L.divIcon({ className: 'num-pin' + (s.time === 'Or' ? ' alt' : ''), html: num(s, i), iconSize: [26, 26] }) })
        .bindPopup(`<a href="#stop-${i + 1}" data-stop>${esc(pl.name)}</a><br><small>${esc(s.time)}${pl.approx ? ' · approximate location' : ''}</small>`).addTo(map);
    });
    if (route.length > 1) L.polyline(route, { color: cssColor('green'), weight: 2.5, opacity: .7, dashArray: '6 6' }).addTo(map);
    if (all.length) map.fitBounds(L.latLngBounds(all).pad(0.15), { maxZoom: 12, animate: false });
  }

  function eventsPage(params) {
    const region = params.get('region') || '';
    const regions = [...new Set(EV.map(e => e.region))];
    // Order by the month an event usually starts: its date if published, else its season's first month.
    const startMonth = e => e.start ? +e.start.slice(5, 7) - 1
      : Math.max(0, MONTHS.findIndex(m => e.season.toLowerCase().includes(m.slice(0, 3).toLowerCase())));
    const list = EV.filter(e => !region || e.region === region).sort((a, b) => startMonth(a) - startMonth(b) || a.name.localeCompare(b.name));
    const groups = {};
    list.forEach(e => { const m = MONTHS[startMonth(e)]; (groups[m] = groups[m] || []).push(e); });
    app.innerHTML = `<section><div class="wrap">
      <div class="kicker">Events</div><h1>Local food &amp; farm events</h1>
      <p class="muted" style="max-width:660px">Farm dinners, food festivals, rodeos and markets that celebrate Colorado food. Dates shown are the latest published; most summer dates are announced each spring.</p>
      <div class="typebtns" id="evr"><button data-r="" class="${!region ? 'on' : ''}">All regions</button>${regions.map(r => `<button data-r="${esc(r)}" class="${r === region ? 'on' : ''}">${esc(r)}</button>`).join('')}</div>
      ${Object.entries(groups).map(([m, es]) => `<div class="group"><h2>${m}</h2><div class="grid">${es.map(evCard).join('')}</div></div>`).join('') || '<div class="empty">No events yet for this region.</div>'}
      ${PL.length ? `<div class="cta" style="margin-top:32px"><div><h2>Make a day of it</h2><p>Pair an event with farm visits and a dinner that names its farms.</p></div><a class="btn" href="#/plan">Plan a day</a></div>` : ''}
    </div></section>`;
    document.getElementById('evr').addEventListener('click', ev => {
      const b = ev.target.closest('button'); if (!b) return;
      location.hash = '#/events' + (b.dataset.r ? '?region=' + encodeURIComponent(b.dataset.r) : '');
    });
  }

  function about() {
    const s = D.stats;
    app.innerHTML = `<section><div class="wrap prose">
      <div class="kicker">How it works</div><h1>Where the guide comes from</h1>
      <p>Most local food directories list farms. This guide lists <b>connections</b>: which restaurants, shops and markets buy from which Colorado producers. That way you can eat local without driving to the farm, and know which places actually put local food on the plate.</p>
      <h2>How we built it</h2>
      <p>We started with one restaurant's published supplier list (Rootstalk in Breckenridge) and worked outward. For every supplier we found its own "where to buy" or stockist page; for every buyer, its other farms. Then we added other Colorado restaurants that publish their sourcing, and press roundups. The current draft has <b>${s.businesses}</b> businesses and <b>${s.links}</b> links, researched ${esc(s.researched)}.</p>
      <h2>How sure are we?</h2>
      <table>
        <tr><td><span class="conf high">high</span></td><td>The farm or the restaurant names the other on its own website or menu (${s.high} links).</td></tr>
        <tr><td><span class="conf medium">medium</span></td><td>A news story, a third party, or a distributor's list.</td></tr>
        <tr><td><span class="conf low">low</span></td><td>Old or indirect evidence. Shown faded.</td></tr>
        <tr><td><span class="stale">older mention</span></td><td>From press before ${STALE_BEFORE}. Both businesses are still open, but a re-check found no current source naming the link. These sit in a separate "Older mentions" section and don't count toward totals (${s.older} links).</td></tr>
      </table>
      <p>On ${esc(s.rechecked)} we re-checked every link that rested on pre-${STALE_BEFORE} press. Links where the restaurant or the farm has since closed were removed. Links a current menu or partner list still confirms were updated, and a few new ones turned up along the way.</p>
      <p>Distances are between town centers, so "miles away" is approximate.</p>
      <h2>What's missing</h2>
      <ul>
        <li>Distributors (UNFI, Growers Organic, Farm Runners and others) don't publish who they sell to, so links through them are thin.</li>
        <li>The network grew from the mountains and Front Range out. Southern Colorado and the Eastern Plains are under-covered.</li>
        <li>Producers outside Colorado and its neighbors are left out, even when a Colorado restaurant uses them.</li>
      </ul>
      <h2>Get listed or fix a listing</h2>
      <p>If you're a chef, grocer or producer, send us who you buy from or sell to, with a link if you publish it. We add confirmed links as <b>high</b> confidence.</p>
      <p><a class="btn" href="https://coloradofarmtrail.com/about.html">Send us your sourcing</a></p>
    </div></section>`;
  }

  function notFound() {
    app.innerHTML = `<section><div class="wrap"><h1>Not found</h1><p>That page isn't in the guide. <a href="#/explore">Explore everything</a>.</p></div></section>`;
  }

  /* ---------- router ---------- */
  function route() {
    maps.forEach(m => m.remove()); maps = [];
    const h = location.hash.replace(/^#\/?/, '');
    const [path, qs] = h.split('?');
    const parts = path.split('/').filter(Boolean);
    document.querySelectorAll('[data-nav]').forEach(a => a.classList.toggle('on',
      a.dataset.nav === parts[0] || (a.dataset.nav === 'regions' && parts[0] === 'region')));
    const page = parts[0] || '';
    if (!page) home();
    else if (page === 'explore') explore(new URLSearchParams(qs || ''));
    else if (page === 'p') place(decodeURIComponent(parts[1] || ''));
    else if (page === 'regions') regionsPage();
    else if (page === 'region') regionPage(parts[1] || '');
    else if (page === 'network') network();
    else if (page === 'plan') parts[1] ? planPage(parts[1]) : plansIndex();
    else if (page === 'events') eventsPage(new URLSearchParams(qs || ''));
    else if (page === 'about') about();
    else notFound();
    const name = { explore: 'Explore', regions: 'Regions', region: 'Region', network: 'The web', about: 'How it works', events: 'Events',
      plan: PL.find(x => x.id === parts[1])?.title || 'Plan a day', p: byId[parts[1]]?.name }[page];
    document.title = (name ? name + ' · ' : '') + 'Colorado Local Food Guide';
    if (page !== 'p') window.scrollTo(0, 0);
  }
  window.addEventListener('hashchange', route);
  // Day-plan stop links (#stop-N, from the map popups) scroll in place instead of hitting the router.
  document.addEventListener('click', ev => {
    const a = ev.target.closest('a[href^="#stop-"]'); if (!a) return;
    ev.preventDefault(); document.querySelector(a.getAttribute('href'))?.scrollIntoView({ behavior: 'smooth' });
  });
  route();
})();
