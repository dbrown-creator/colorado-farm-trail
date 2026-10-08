/* Gunnison Valley Provides prototype — shared chrome, data loading and helpers. */
(function(){
  "use strict";
  var ROOT = document.documentElement.getAttribute("data-root") || ".";

  var TYPE_STYLE = {
    farm:       { emoji:"🐄", color:"var(--t-farm)",       hex:"#2f6b3c" },
    market:     { emoji:"🧺", color:"var(--t-market)",     hex:"#a8761d" },
    assistance: { emoji:"🥫", color:"var(--t-assistance)", hex:"#a94f28" },
    dining:     { emoji:"🍽️", color:"var(--t-dining)",     hex:"#5b6b8c" },
    community:  { emoji:"🌱", color:"var(--t-community)",  hex:"#3f7f9c" }
  };
  var OFFERING_EMOJI = { "veggies":"🥕", "fruit":"🍎", "beef-meat":"🥩", "poultry-eggs":"🥚",
    "dairy":"🧀", "flowers":"💐", "spices-garlic":"🧄", "staples":"🍯" };
  var MONTHS = ["January","February","March","April","May","June","July","August","September","October","November","December"];

  var SITE = "Gunnison Valley Provides";
  var NAV = [
    ["index.html","Home"], ["find-food.html","Find Food"],
    ["list-your-business.html","List Your Business"], ["about.html","About & How It Works"]
  ];

  function esc(s){
    return String(s == null ? "" : s).replace(/[&<>"']/g, function(c){
      return {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c];
    });
  }
  function url(path){ return ROOT + "/" + path; }

  function header(){
    var here = document.body.getAttribute("data-page");
    var links = NAV.map(function(n){
      var cur = n[0] === here ? ' aria-current="page"' : "";
      return '<a href="'+url(n[0])+'"'+cur+'>'+n[1]+'</a>';
    }).join("");
    return '<a class="skip" href="#main">Skip to content</a>'
      + '<div class="draft" role="note"><strong>Prototype for review</strong>, prepared by Colorado Farm Trail. Not the official site.</div>'
      + '<header class="site-header"><div class="wrap">'
      + '<a class="brand" href="'+url("index.html")+'"><span class="name">Gunnison Valley Provides</span><span class="tag">working title</span></a>'
      + '<button class="menu-btn" aria-expanded="false" aria-controls="sitenav">Menu</button>'
      + '<nav class="nav" id="sitenav" aria-label="Main">'+links+'</nav>'
      + '</div></header>';
  }
  function footer(){
    return '<footer class="site-footer"><div class="wrap"><div class="cols">'
      + '<div><a class="brand" href="'+url("index.html")+'"><span class="name">Gunnison Valley Provides</span><span class="tag">working title</span></a>'
      + '<p style="margin-top:14px">A prototype local-food map and directory for the Gunnison Valley, built from the Colorado producers data set. '
      + 'Prepared by <a href="https://coloradofarmtrail.com/" rel="noopener">Colorado Farm Trail</a> for review. It is not an official site, and no organization has endorsed it.</p></div>'
      + '<div><h3 style="color:#fff;font-size:1rem">Explore</h3><ul>'
      + NAV.map(function(n){ return '<li><a href="'+url(n[0])+'">'+n[1]+'</a></li>'; }).join("")
      + '</ul></div>'
      + '<div><h3 style="color:#fff;font-size:1rem">Contact</h3><ul>'
      + '<li>Questions about this prototype: <a href="mailto:coloradofarmtrail@gmail.com">coloradofarmtrail@gmail.com</a></li>'
      + '</ul></div></div>'
      + '<p class="fine">Listings combine Colorado Proud, the Colorado Farmers Market Association, USDA local-food directories and each provider\'s own website. '
      + 'This is a starter set; more producers are being verified. Every detail page shows where its information came from and when it was last checked.</p>'
      + '</div></footer>';
  }

  function mountChrome(){
    var h = document.getElementById("site-header");
    var f = document.getElementById("site-footer");
    if(h) h.outerHTML = header();
    if(f) f.outerHTML = footer();
    var btn = document.querySelector(".menu-btn"), nav = document.getElementById("sitenav");
    if(btn && nav) btn.addEventListener("click", function(){
      var open = nav.classList.toggle("open");
      btn.setAttribute("aria-expanded", open ? "true" : "false");
    });
  }

  var cache = {};
  function load(name){
    if(!cache[name]){
      cache[name] = fetch(url("data/"+name+".json")).then(function(r){
        if(!r.ok) throw new Error(name+".json: HTTP "+r.status);
        return r.json();
      });
    }
    return cache[name];
  }

  function thisMonth(){ return MONTHS[new Date().getMonth()]; }
  function openThisMonth(p){ return (p.monthsOpen || []).indexOf(thisMonth()) !== -1; }
  function primaryType(p){ return (p.types && p.types[0]) || "community"; }
  function typeStyle(t){ return TYPE_STYLE[t] || TYPE_STYLE.community; }
  // off = [dx, dy] pixel nudge for places that share one spot (see fanOut).
  function pinIcon(t, off){
    var st = typeStyle(t), dx = off ? off[0] : 0, dy = off ? off[1] : 0;
    return L.divIcon({ className:"", iconSize:[28,28], iconAnchor:[14-dx,28-dy], popupAnchor:[dx,dy-26],
      html:'<div class="pin" style="background:'+st.hex+'"><span>'+st.emoji+'</span></div>' });
  }
  // Basemaps. Default: OpenStreetMap's standard map (the reviewer's pick), in light and dark
  // mode alike. ?basemap=streets (Esri World Street Map) or ?basemap=voyager (CARTO, the
  // Farm Trail's map) on any page to compare.
  var BASEMAPS = {
    voyager: { url:"https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png?key=cb1_3vh9_1_2876c53a17aa6fd35517591d",
      attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a>', maxZoom:19 },
    streets: { url:"https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}",
      attribution:'Tiles &copy; <a href="https://www.esri.com/">Esri</a>, HERE, Garmin, USGS, &copy; OpenStreetMap', maxZoom:19 },
    osm: { url:"https://tile.openstreetmap.org/{z}/{x}/{y}.png",
      attribution:'&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>', maxZoom:19 }
  };
  function basemap(map){
    // Keep the required map credit, but drop Leaflet's own "Leaflet" prefix.
    if (map.attributionControl) map.attributionControl.setPrefix(false);
    var b = BASEMAPS[new URLSearchParams(location.search).get("basemap")] || BASEMAPS.osm;
    return L.tileLayer(b.url, { maxZoom:b.maxZoom, attribution:b.attribution }).addTo(map);
  }
  // Gunnison County boundary (US Census TIGERweb, GEOID 08051, simplified).
  // Draws the county line and softly dims everything outside it. Non-interactive so it
  // never steals clicks from pins; added to a low pane so markers stay on top.
  // Places within ~30 m of each other (two organizations at one address) would stack
  // and hide each other; give each a pixel offset in a small ring. Returns id -> [dx, dy].
  function fanOut(list){
    var groups = [], out = {}, NEAR = 30;
    list.forEach(function(p){
      var g = null;
      for(var j = 0; j < groups.length && !g; j++){
        var a = groups[j][0], dy = (p.lat - a.lat) * 111320, dx = (p.lng - a.lng) * 111320 * Math.cos(a.lat * Math.PI / 180);
        if(dx*dx + dy*dy <= NEAR*NEAR) g = groups[j];
      }
      if(g) g.push(p); else groups.push([p]);
    });
    groups.forEach(function(g){
      if(g.length < 2) return;
      g.forEach(function(p, i){
        var a = 2*Math.PI*i/g.length - Math.PI/2, r = 13 + 2*g.length;
        out[p.id] = [Math.round(r*Math.cos(a)), Math.round(r*Math.sin(a))];
      });
    });
    return out;
  }
  function countyOutline(map){
    return load("gunnison-county").then(function(gj){
      var ring = gj.features[0].geometry.coordinates[0].map(function(c){ return [c[1], c[0]]; });
      if(!map.getPane("county")){ map.createPane("county"); map.getPane("county").style.zIndex = 350; }
      // The basemap is light in both color schemes now, so one light style for the outline.
      var world = [[-89.9,-179.9],[-89.9,179.9],[89.9,179.9],[89.9,-179.9]];
      L.polygon([world, ring], { pane:"county", interactive:false, stroke:false,
        fillColor:"#1f2a1f", fillOpacity:.1 }).addTo(map);
      var line = L.polygon(ring, { pane:"county", interactive:false, fill:false,
        color:"#2f5d3a", weight:2.5, opacity:.9, dashArray:"6 5" }).addTo(map);
      return line;
    }).catch(function(){ return null; });  // the map still works without the outline
  }
  function fmtDate(iso){
    if(!iso) return "";
    var d = new Date(iso + "T12:00:00");
    return d.toLocaleDateString("en-US", { year:"numeric", month:"long", day:"numeric" });
  }
  function directions(p){
    if(p.lat != null && !p.approx) return "https://www.google.com/maps/dir/?api=1&destination="+p.lat+","+p.lng;
    return "https://www.google.com/maps/search/?api=1&query="+encodeURIComponent([p.name, p.address, p.town, "CO"].filter(Boolean).join(", "));
  }
  function providerUrl(p){ return url("provider.html?id="+encodeURIComponent(p.id)); }

  window.CP = { esc:esc, url:url, load:load, TYPE_STYLE:TYPE_STYLE, OFFERING_EMOJI:OFFERING_EMOJI, MONTHS:MONTHS,
    fanOut:fanOut, thisMonth:thisMonth, openThisMonth:openThisMonth, primaryType:primaryType, typeStyle:typeStyle,
    pinIcon:pinIcon, basemap:basemap, countyOutline:countyOutline, fmtDate:fmtDate, directions:directions, providerUrl:providerUrl };

  // Real height of the banner + header, so full-height layouts (the Find Food map) fit
  // the screen exactly even when the banner wraps or the text is enlarged.
  function measureChrome(){
    var h = 0;
    [".draft", ".site-header"].forEach(function(sel){
      var el = document.querySelector(sel);
      if(el) h += el.getBoundingClientRect().height;
    });
    if(h) document.documentElement.style.setProperty("--chrome", Math.round(h) + "px");
  }
  function start(){ mountChrome(); measureChrome(); window.addEventListener("resize", measureChrome); }

  if(document.readyState === "loading") document.addEventListener("DOMContentLoaded", start);
  else start();
})();
