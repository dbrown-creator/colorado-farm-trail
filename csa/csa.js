(function () {
  "use strict";
  var D = window.CSA_DATA;
  var TODAY = new Date(); TODAY.setHours(0, 0, 0, 0);
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  var STATUS = { open: "Sign-up open", waitlist: "Waitlist", full: "Full", opens_later: "Sign-up opens later", closed_season: "Sign-up closed", unknown: "Sign-up status unknown" };
  var TYPES = ["Vegetables", "Fruit", "Eggs", "Meat", "Flowers", "Mushrooms", "Bread/Baked", "Dairy", "Grains"];
  var state = { here: null, way: "any", radius: 25, sort: "start", types: {}, openOnly: false };
  var $ = function (s) { return document.querySelector(s); };
  var esc = function (s) { return String(s == null ? "" : s).replace(/[&<>"']/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]; }); };
  function store(k, v) { try { if (v === undefined) return localStorage.getItem(k); localStorage.setItem(k, v); } catch (e) { return null; } }

  /* ---------- distance ---------- */
  function miles(a, b, c, d) {
    var r = function (x) { return x * Math.PI / 180; }, R = 3958.8;
    var h = Math.pow(Math.sin(r(c - a) / 2), 2) + Math.cos(r(a)) * Math.cos(r(c)) * Math.pow(Math.sin(r(d - b) / 2), 2);
    return 2 * R * Math.asin(Math.sqrt(h));
  }

  /* ---------- seasons ---------- */
  function iso(s) { var p = s.split("-"); return new Date(+p[0], +p[1] - 1, +p[2]); }
  function dayOfYear(d) { return (d - new Date(d.getFullYear(), 0, 1)) / 864e5 / (((d.getFullYear() % 4 === 0) ? 366 : 365)) * 100; }
  function fmt(d, prec, withYear) {
    var s = prec === "month" ? MONTHS[d.getMonth()] : MONTHS[d.getMonth()] + " " + d.getDate();
    return withYear ? s + ", " + d.getFullYear() : s;
  }
  // rank: 0 in season, 1 upcoming, 2 ended (shown by when it usually starts), 3 no dates
  function season(c) {
    var s = c.season_start && iso(c.season_start), e = c.season_end && iso(c.season_end), p = c.season_precision;
    var o = { rank: 3, key: 0, html: '<span class="nodates">Season dates not posted. See the farm\'s page.</span>', bar: null };
    if (s && e) {
      var range = fmt(s, p) + " – " + fmt(e, p, true), wk = Math.round((e - s) / 6048e5) + 1;
      var span = p === "month" ? "" : " · " + wk + " weeks";
      if (e < TODAY) {
        var nxt = new Date(s); nxt.setFullYear(nxt.getFullYear() + 1);
        return { rank: 2, key: +nxt, html: '<div class="season tab">' + range + ' <em>· ended. Next dates not posted</em></div>', bar: [s, e, true] };
      }
      if (s <= TODAY) return { rank: 0, key: +s, html: '<div class="season tab">' + range + ' <em>· in season now</em></div>', bar: [s, e, false] };
      var days = Math.round((s - TODAY) / 864e5);
      return { rank: 1, key: +s, html: '<div class="season tab">' + range + ' <em>' + span + (days < 90 ? " · starts in " + days + " days" : "") + '</em></div>', bar: [s, e, false] };
    }
    if (s) return { rank: s <= TODAY ? 0 : 1, key: +s, html: '<div class="season tab">Starts ' + fmt(s, p, true) + ' <em>· end date not posted</em></div>', bar: null };
    return o;
  }
  function barHtml(b) {
    if (!b) return "";
    var l = dayOfYear(b[0]), r = dayOfYear(b[1]);
    return '<div class="track" aria-hidden="true"><div class="bar' + (b[2] ? " past" : "") + '" style="left:' + l + '%;width:' + Math.max(2, r - l) + '%"></div><div class="tnow" style="left:' + dayOfYear(TODAY) + '%"></div></div>';
  }

  /* ---------- matching ---------- */
  function evaluate(c) {
    var h = state.here, res = { delivery: null, pickups: [], farmMi: null, unplaced: [] };
    if (!h) return res;
    if (c.lat != null) res.farmMi = miles(h.lat, h.lon, c.lat, c.lon);
    var d = c.delivery;
    if (d && d.offered) {
      var town = (h.city || "").toLowerCase();
      var vague = !d.towns.length && !d.zips.length && !d.radius;
      if (h.zip && d.zips.indexOf(h.zip) >= 0) res.delivery = "yes";
      else if (town && d.towns.some(function (t) { var tl = t.toLowerCase(); return tl === town || tl.indexOf(town) >= 0; })) res.delivery = "yes";
      else if (d.radius && res.farmMi != null && res.farmMi <= d.radius) res.delivery = "yes";
      else if (vague && res.farmMi != null && res.farmMi <= 60) res.delivery = "maybe";
    }
    c.pickups.forEach(function (p) {
      if (p.lat == null) { res.unplaced.push(p); return; }
      var mi = miles(h.lat, h.lon, p.lat, p.lon);
      if (mi <= state.radius) res.pickups.push({ p: p, mi: mi });
    });
    res.pickups.sort(function (a, b) { return a.mi - b.mi; });
    res.farmOnly = !c.pickups.some(function (p) { return p.lat != null; }) && res.farmMi != null && res.farmMi <= state.radius;
    return res;
  }

  function results() {
    var out = D.csas.map(function (c) { return { c: c, ev: evaluate(c), se: season(c) }; });
    if (state.here) {
      out = out.filter(function (r) {
        var e = r.ev, pick = e.pickups.length > 0, del = !!e.delivery, farm = e.farmOnly;
        if (state.way === "delivery") return del;
        if (state.way === "pickup") return pick;
        return pick || del || farm;
      });
    }
    var picked = Object.keys(state.types).filter(function (k) { return state.types[k]; });
    if (picked.length) out = out.filter(function (r) { return r.c.share_types.some(function (t) { return state.types[t]; }); });
    if (state.openOnly) out = out.filter(function (r) { return r.c.status === "open"; });
    var near = function (r) {
      var e = r.ev; if (!state.here) return 0;
      if (e.delivery === "yes") return 0;
      return e.pickups.length ? e.pickups[0].mi : (e.farmMi != null ? e.farmMi : 9999);
    };
    out.sort(function (a, b) {
      if (state.sort === "dist" && state.here) return near(a) - near(b);
      return (a.se.rank - b.se.rank) || (a.se.key - b.se.key) || (near(a) - near(b));
    });
    return out;
  }

  /* ---------- rendering ---------- */
  var I_PIN = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--green)" stroke-width="2" aria-hidden="true"><path d="M12 22s7-6.5 7-12a7 7 0 1 0-14 0c0 5.5 7 12 7 12z"/><circle cx="12" cy="10" r="2.5"/></svg>';
  var I_TRUCK = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--gold)" stroke-width="2" aria-hidden="true"><path d="M2 6h11v10H2zM13 10h5l3 3v3h-8"/><circle cx="6" cy="17.5" r="1.8"/><circle cx="17" cy="17.5" r="1.8"/></svg>';
  var I_INFO = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="var(--muted)" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="9"/><path d="M12 11v5M12 8v.5"/></svg>';
  function when(p) { var w = [p.day, p.time].filter(Boolean).join(" "); return w ? " · " + esc(w) : ""; }
  function dist(mi, prec) { if (mi < 1) return "under 1 mi";
    return (prec === "town" ? "about " : "") + mi.toFixed(mi < 10 ? 1 : 0) + " mi"; }
  function host(u) { try { return new URL(u).hostname.replace(/^www\./, ""); } catch (e) { return "the farm's site"; } }
  function pickLine(p, mi) {
    var addr = p.address || "", showTown = p.town && p.name !== p.town && addr.toLowerCase().indexOf(p.town.toLowerCase()) < 0;
    var place = [p.name, showTown ? p.town : ""].filter(Boolean).join(", ");
    return '<b class="tab">' + dist(mi, p.prec) + '</b> <span class="sub">· ' + esc(place) + (p.address ? ", " + esc(p.address) : "") + when(p) + (p.prec === "town" ? " · exact spot not posted" : "") + "</span>";
  }

  function card(r) {
    var c = r.c, e = r.ev, ways = [], more = "";
    if (e.delivery) {
      var d = c.delivery;
      ways.push("<li>" + I_TRUCK + "<span><b>" + (e.delivery === "yes" ? "Delivers to your area" : "Offers delivery, confirm your address") + '</b> <span class="sub">· ' + esc(d.details || "Area not posted") + (d.fee ? " · " + esc(d.fee) : "") + "</span></span></li>");
    }
    if (e.pickups.length) {
      ways.push("<li>" + I_PIN + "<span>" + pickLine(e.pickups[0].p, e.pickups[0].mi) + "</span></li>");
      var rest = e.pickups.slice(1);
      if (rest.length) more = "<details><summary>" + rest.length + " more pickup" + (rest.length > 1 ? "s" : "") + " within " + state.radius + " mi</summary><ul>" +
        rest.map(function (x) { return '<li class="tab">' + pickLine(x.p, x.mi) + "</li>"; }).join("") + "</ul></details>";
    } else if (e.farmOnly) {
      ways.push("<li>" + I_INFO + '<span><b class="tab">Farm is ' + dist(e.farmMi) + ' away</b> <span class="sub">· pickup and delivery details not posted. Ask the farm.</span></span></li>');
    }
    if (!state.here) {
      ways.push("<li>" + I_PIN + '<span><span class="sub">Farm in ' + esc(titleCase(c.city.toLowerCase())) + ", " + esc(c.county) + " County" + (c.pickups.length ? " · " + c.pickups.length + " pickup site" + (c.pickups.length > 1 ? "s" : "") + " listed" : "") + "</span></span></li>");
    }
    var tags = c.share_types.map(function (t) { return '<span class="tag">' + esc(t) + "</span>"; }).join("") +
      (c.frequency ? '<span class="tag">' + esc(c.frequency) + "</span>" : "") + (c.snap ? '<span class="tag snap">SNAP/EBT accepted</span>' : "");
    var link = c.signup_url || c.website, open = c.status === "open" || c.status === "waitlist";
    var cta = link ? '<a class="signup' + (open ? "" : " ghost") + '" href="' + esc(link) + '" target="_blank" rel="noopener">' +
      (c.status === "open" ? "Sign up" : c.status === "waitlist" ? "Join waitlist" : c.signup_url ? "See CSA details" : "Visit farm site") + " on " + esc(host(link)) + " ↗</a>" : "";
    var st = STATUS[c.status] + (c.status === "opens_later" && c.signup_opens ? " " + c.signup_opens : "");
    return '<article class="csa" data-id="' + esc(c.id) + '"><div class="head"><div><h3>' + esc(c.name) + '</h3><p class="meta">' + esc(titleCase(c.city.toLowerCase())) + ", " + esc(c.county) + " County</p></div>" +
      '<span class="status s-' + esc(c.status) + '">' + esc(st) + "</span></div>" +
      "<div>" + r.se.html + barHtml(r.se.bar) + "</div>" +
      '<ul class="ways">' + ways.join("") + "</ul>" + more + (tags ? '<div class="tags">' + tags + "</div>" : "") +
      '<div class="foot-row"><span class="price">' + (c.price ? "<b>" + esc(c.price) + "</b>" : "Price not posted") + "</span>" + cta + "</div></article>";
  }

  var map, layer, circle;
  function drawMap(list) {
    if (!map) return;
    layer.clearLayers(); if (circle) { map.removeLayer(circle); circle = null; }
    var pts = [], h = state.here;
    function dot(lat, lon, color, id, title, faded, r) {
      var m = L.circleMarker([lat, lon], { radius: r || 7, color: "#fff", weight: 2, fillColor: color, fillOpacity: faded ? .5 : 1 }).addTo(layer);
      m.bindTooltip(title); m.on("click", function () { focusCard(id); }); pts.push([lat, lon]);
    }
    list.forEach(function (r) {
      var c = r.c, shown = false;
      if (h) r.ev.pickups.forEach(function (x) { dot(x.p.lat, x.p.lon, "#3f7d3a", c.id, c.name + " · " + (x.p.name || x.p.town), x.p.prec === "town"); shown = true; });
      if (c.lat != null && (!h || !shown)) dot(c.lat, c.lon, "#c8902a", c.id, c.name + " (farm)", false, 6);
    });
    if (h) {
      circle = L.circle([h.lat, h.lon], { radius: state.radius * 1609.34, color: "#5d6656", weight: 1.2, dashArray: "4 4", fill: false }).addTo(map);
      L.circleMarker([h.lat, h.lon], { radius: 8, color: "#fff", weight: 2, fillColor: "#20301f", fillOpacity: 1 }).addTo(layer).bindTooltip("You");
      pts.push([h.lat, h.lon]);
      map.fitBounds(circle.getBounds().extend(pts), { padding: [20, 20], maxZoom: 11 });
    } else if (pts.length) map.fitBounds(pts, { padding: [20, 20] });
  }
  function focusCard(id) {
    var el = document.querySelector('.csa[data-id="' + id + '"]'); if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "center" }); hl(id);
  }
  function hl(id) { document.querySelectorAll(".csa").forEach(function (c) { c.classList.toggle("hot", c.dataset.id === id); }); }

  function render() {
    var list = results(), h = state.here;
    $("#count").textContent = h ? (list.length ? list.length + " CSA" + (list.length > 1 ? "s" : "") + " reach you" : "No CSAs reach you yet") : D.csas.length + " Colorado CSAs";
    $("#where").textContent = h ? "Near " + h.label + " · sorted by " + (state.sort === "dist" ? "closest" : "season start") : "Enter an address above to see which ones deliver to you or have a pickup nearby. Sorted by season start.";
    $("#list").innerHTML = list.length ? list.map(card).join("") :
      '<div class="empty">Nothing delivers to ' + esc(h && h.label) + " or has a pickup within " + state.radius + " miles with these filters." +
      (state.radius < 100 ? '<br><button class="chip" type="button" id="widen">Search within 100 miles</button>' : "") + "</div>";
    drawMap(list);
    var w = $("#widen"); if (w) w.onclick = function () { $("#radius").value = "100"; state.radius = 100; render(); };
  }

  /* ---------- finding the user ---------- */
  function jsonp(url, cb, fail) {
    var name = "cb_" + Date.now(), s = document.createElement("script"), done = false;
    var t = setTimeout(function () { if (!done) { done = true; clean(); fail(); } }, 9000);
    function clean() { delete window[name]; s.remove(); clearTimeout(t); }
    window[name] = function (d) { if (done) return; done = true; clean(); cb(d); };
    s.onerror = function () { if (!done) { done = true; clean(); fail(); } };
    s.src = url + (url.indexOf("?") < 0 ? "?" : "&") + "callback=" + name; document.head.appendChild(s);
  }
  function titleCase(s) { return s.replace(/\b\w/g, function (c) { return c.toUpperCase(); }); }
  function setHere(h) { state.here = h; $("#err").hidden = true; store("csa.addr", $("#addr").value); render(); $("#results").scrollIntoView({ behavior: "smooth", block: "start" }); }
  function fail(msg) { $("#err").textContent = msg; $("#err").hidden = false; }

  function locate(q) {
    q = q.trim(); if (!q) return fail("Type an address, town or ZIP code first.");
    var norm = q.toLowerCase().replace(/,?\s*(co|colorado)\.?$/, "").replace(/\s+/g, " ").trim();
    var zip = norm.match(/^\d{5}$/);
    if (zip) {
      var z = D.zips[zip[0]];
      if (z) return setHere({ lat: z[0], lon: z[1], zip: zip[0], city: "", label: "ZIP " + zip[0] });
      return fetch("https://api.zippopotam.us/us/" + zip[0]).then(function (r) { if (!r.ok) throw 0; return r.json(); }).then(function (j) {
        var p = j.places[0]; setHere({ lat: +p.latitude, lon: +p.longitude, zip: zip[0], city: p["place name"], label: p["place name"] + " " + zip[0] });
      }).catch(function () { fail("We couldn't find that ZIP code. Try a street address or a town name."); });
    }
    if (D.towns[norm]) return setHere({ lat: D.towns[norm][0], lon: D.towns[norm][1], zip: "", city: titleCase(norm), label: titleCase(norm) });
    var url = "https://geocoding.geo.census.gov/geocoder/locations/onelineaddress?benchmark=Public_AR_Current&format=jsonp&address=" +
      encodeURIComponent(/\b(co|colorado)\b/i.test(q) ? q : q + ", CO");
    $("#goBtn").disabled = true;
    jsonp(url, function (d) {
      $("#goBtn").disabled = false;
      var m = d && d.result && d.result.addressMatches && d.result.addressMatches[0];
      if (!m) return fail("We couldn't place that address. Check the spelling, or try just your town or ZIP code.");
      var ac = m.addressComponents || {};
      setHere({ lat: m.coordinates.y, lon: m.coordinates.x, zip: ac.zip || "", city: titleCase((ac.city || "").toLowerCase()), label: m.matchedAddress ? titleCase(m.matchedAddress.toLowerCase()).replace(/, Co\b/, ", CO") : q });
    }, function () { $("#goBtn").disabled = false; fail("The address lookup didn't respond. Try your town or ZIP code instead."); });
  }

  /* ---------- wire up ---------- */
  function init() {
    document.getElementById("draftBar").textContent = "Preview · CSA details researched from each farm's own site · last updated " + D.built;
    $("#months").innerHTML = MONTHS.map(function (m) { return "<span>" + m[0] + "</span>"; }).join("");
    TYPES.forEach(function (t) {
      if (!D.csas.some(function (c) { return c.share_types.indexOf(t) >= 0; })) return;
      var b = document.createElement("button"); b.className = "chip"; b.type = "button"; b.textContent = t; b.setAttribute("aria-pressed", "false");
      b.onclick = function () { state.types[t] = !state.types[t]; b.setAttribute("aria-pressed", state.types[t]); render(); };
      $("#types").appendChild(b);
    });
    document.querySelectorAll("[data-way]").forEach(function (b) {
      b.onclick = function () { state.way = b.dataset.way; document.querySelectorAll("[data-way]").forEach(function (x) { x.setAttribute("aria-pressed", x === b); }); render(); };
    });
    $("#openOnly").onclick = function (e) { state.openOnly = !state.openOnly; e.currentTarget.setAttribute("aria-pressed", state.openOnly); render(); };
    $("#radius").onchange = function (e) { state.radius = +e.target.value; render(); };
    $("#sort").onchange = function (e) { state.sort = e.target.value; render(); };
    $("#form").addEventListener("submit", function (e) { e.preventDefault(); locate($("#addr").value); });
    document.querySelectorAll("[data-try]").forEach(function (b) { b.onclick = function () { $("#addr").value = b.dataset.try; locate(b.dataset.try); }; });
    $("#locBtn").onclick = function () {
      if (!navigator.geolocation) return fail("Your browser can't share its location. Type a town or ZIP instead.");
      navigator.geolocation.getCurrentPosition(function (p) { $("#addr").value = ""; setHere({ lat: p.coords.latitude, lon: p.coords.longitude, zip: "", city: "", label: "your location" }); },
        function () { fail("Location is turned off for this site. Allow it in your browser, or type a town or ZIP."); }, { timeout: 10000 });
    };
    $("#list").addEventListener("mouseover", function (e) { var c = e.target.closest(".csa"); hl(c ? c.dataset.id : null); });
    $("#list").addEventListener("mouseleave", function () { hl(null); });
    if (window.L) {
      map = L.map("map", { scrollWheelZoom: false }).setView([39.0, -105.55], 6);
      var KEY = "cb1_3vh9_1_2876c53a17aa6fd35517591d", dark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)");
      var url = function (d) { return "https://basemaps.cartocdn.com/rastertiles/" + (d ? "dark_all" : "light_all") + "/{z}/{x}/{y}{r}.png?key=" + KEY; };
      var tiles = L.tileLayer(url(dark && dark.matches), { maxZoom: 19, attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>' }).addTo(map);
      if (dark && dark.addEventListener) dark.addEventListener("change", function (e) { tiles.setUrl(url(e.matches)); });
      layer = L.layerGroup().addTo(map);
    }
    var last = store("csa.addr"); if (last) $("#addr").value = last;
    render();
  }
  init();
})();
