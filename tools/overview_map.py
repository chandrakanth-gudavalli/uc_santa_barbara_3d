#!/usr/bin/env python3
"""Write overview_map.html: every collection's image positions on one campus map.

Points are coloured by group (Ground / drone / DJI); clicking a point opens a popup that links to
that collection's own gps_map.html. Written to <root>/overview_map.html.

Usage: overview_map.py [--root DIR] [out.html]
"""
import datetime as dt
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path('/data_8tb/capstone_3d/wriva_format')
GROUPS = {  # group folder -> (label, colour token)
    'Ground': ('Ground (phone photos)', '--series-1'),
    'drone': ('Drone (Wingtra)', '--series-2'),
    'DJI': ('DJI video keyframes', '--series-3'),
}

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>UCSB Collections Overview</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
:root {
  --surface-0: #f4f3f0; --surface-1: #fcfcfb; --border: #dddcd7;
  --text-primary: #0b0b0b; --text-secondary: #52514e; --ring: #ffffff;
  --series-1: #2a78d6; --series-2: #eb6834; --series-3: #1baf7a;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --surface-0: #111110; --surface-1: #1a1a19; --border: #383835;
    --text-primary: #ffffff; --text-secondary: #c3c2b7; --ring: #1a1a19;
    --series-1: #3987e5; --series-2: #d95926; --series-3: #199e70;
  }
}
:root[data-theme="dark"] {
  --surface-0: #111110; --surface-1: #1a1a19; --border: #383835;
  --text-primary: #ffffff; --text-secondary: #c3c2b7; --ring: #1a1a19;
  --series-1: #3987e5; --series-2: #d95926; --series-3: #199e70;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--surface-0); color: var(--text-primary);
  font: 14px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; }
header { padding: 16px; display: flex; flex-wrap: wrap; gap: 8px 24px; align-items: baseline; }
h1 { font-size: 18px; margin: 0; font-weight: 600; }
.sub { color: var(--text-secondary); }
.controls { display: flex; flex-wrap: wrap; gap: 8px; padding: 0 16px 12px; }
.chip { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border: 1px solid var(--border);
  border-radius: 999px; background: var(--surface-1); cursor: pointer; color: var(--text-primary); font: inherit; }
.chip[aria-pressed="false"] { opacity: .45; }
.dot { width: 10px; height: 10px; border-radius: 50%; box-shadow: 0 0 0 2px var(--surface-1); }
.count { color: var(--text-secondary); font-variant-numeric: tabular-nums; }
#map { height: calc(100vh - 110px); min-height: 360px; margin: 0 16px 16px; border: 1px solid var(--border); border-radius: 8px; }
.leaflet-popup-content { font-size: 13px; line-height: 1.4; }
.leaflet-popup-content dl { display: grid; grid-template-columns: auto 1fr; gap: 0 8px; margin: 4px 0 6px; }
.leaflet-popup-content dt { color: #52514e; }
.leaflet-popup-content dd { margin: 0; font-variant-numeric: tabular-nums; }
@media (max-width: 600px) { #map { height: 70vh; } }
</style>
</head>
<body>
<header><h1>UCSB in 3D: image collections</h1><span class="sub" id="summary"></span></header>
<div class="controls" id="controls"></div>
<div id="map" role="img" aria-label="Map of all image collections on the UCSB campus"></div>
<script>
const DATA = __DATA__;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
const map = L.map('map', { preferCanvas: true });
const sat = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
  { maxZoom: 21, maxNativeZoom: 19, attribution: 'Imagery &copy; Esri' }).addTo(map);
const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
  { maxZoom: 21, maxNativeZoom: 19, attribution: '&copy; OpenStreetMap contributors' });
L.control.layers({ 'Satellite': sat, 'Streets': osm }, null, { position: 'topright' }).addTo(map);
L.control.scale({ imperial: false }).addTo(map);

function popup(c) {
  return `<strong>${esc(c.site)}</strong><br><code>${esc(c.name)}</code>
    <dl><dt>Images</dt><dd>${c.n}</dd><dt>With GPS</dt><dd>${c.with_gps}</dd>
    <dt>Precise (cm)</dt><dd>${c.precise}</dd><dt>Dates</dt><dd>${esc(c.dates)}</dd></dl>
    <a href="${esc(c.group)}/${esc(c.name)}/gps_map.html">Open collection map →</a>`;
}
const layers = {}, counts = {};
for (const g in DATA.groups) { layers[g] = L.layerGroup().addTo(map); counts[g] = { colls: 0, imgs: 0 }; }
function draw() {
  for (const g in layers) layers[g].clearLayers();
  // drone footprints are dense and wide, so they go underneath; ground photos are drawn last, on top
  const order = { drone: 0, DJI: 1, Ground: 2 };
  for (const c of [...DATA.collections].sort((a, b) => order[a.group] - order[b.group])) {
    const color = css(DATA.groups[c.group].color);
    const style = c.group === 'drone'
      ? { radius: 2.5, color, weight: 0, fillColor: color, fillOpacity: 0.55 }
      : { radius: 3.5, color: css('--ring'), weight: 1, fillColor: color, fillOpacity: 0.95 };
    for (const [lat, lon] of c.pts)
      L.circleMarker([lat, lon], style)
        .bindTooltip(`${c.site} · ${c.name}`, { direction: 'top' })
        .bindPopup(() => popup(c)).addTo(layers[c.group]);
  }
}
for (const c of DATA.collections) { counts[c.group].colls++; counts[c.group].imgs += c.n; }
draw();
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', draw);
// frame the buildings (ground photos); drone footprints extend well past them
const all = DATA.collections.filter(c => c.group === 'Ground').flatMap(c => c.pts);
map.fitBounds(L.latLngBounds(all).pad(0.05));

const ctl = document.getElementById('controls');
for (const [g, s] of Object.entries(DATA.groups)) {
  const b = document.createElement('button');
  b.className = 'chip'; b.setAttribute('aria-pressed', 'true');
  b.innerHTML = `<span class="dot" style="background:var(${s.color})"></span>${esc(s.label)}
    <span class="count">${counts[g].colls} collections · ${counts[g].imgs.toLocaleString()} images</span>`;
  b.onclick = () => { const on = b.getAttribute('aria-pressed') !== 'true'; b.setAttribute('aria-pressed', on);
    on ? layers[g].addTo(map) : map.removeLayer(layers[g]); };
  ctl.appendChild(b);
}
const tot = DATA.collections.reduce((a, c) => a + c.n, 0);
document.getElementById('summary').textContent =
  `${DATA.collections.length} collections · ${tot.toLocaleString()} images · click a point to open its collection map`;
</script>
</body>
</html>
"""


def main(argv):
    root = ROOT
    if argv[:1] == ['--root']:
        root, argv = Path(argv[1]), argv[2:]
    out = Path(argv[0]) if argv else root / 'overview_map.html'
    colls = []
    for group in GROUPS:
        for d in sorted((root / group).iterdir()) if (root / group).is_dir() else []:
            if not (d / 'metadata' / 'site.json').exists():
                continue
            site = json.loads((d / 'metadata' / 'site.json').read_text())
            pts, n, precise, times = [], 0, 0, []
            for p in sorted((d / 'metadata').glob('image_*.json')):
                m = json.loads(p.read_text())
                n += 1
                e = m['extrinsics']
                if e['lat'] is not None:
                    pts.append([round(e['lat'], 6), round(e['lon'], 6)])
                if m.get('extrinsic_calibration') in ('emlid_rtk', 'wingtra_ppk'):
                    precise += 1
                if m.get('timestamp'):
                    times.append(m['timestamp'])
            tz = ZoneInfo(site.get('timezone') or 'UTC')
            days = sorted({dt.datetime.fromtimestamp(t, tz).date().isoformat() for t in times})
            colls.append({'name': d.name, 'group': group, 'site': site.get('name', d.name), 'n': n,
                          'with_gps': len(pts), 'precise': precise, 'pts': pts,
                          'dates': (days[0] if len(days) == 1 else f'{days[0]} – {days[-1]}') if days else '—'})
    data = {'groups': {g: {'label': lab, 'color': col} for g, (lab, col) in GROUPS.items()}, 'collections': colls}
    out.write_text(TEMPLATE.replace('__DATA__', json.dumps(data, separators=(',', ':')).replace('</', '<\\/')))
    print(f'{out}: {len(colls)} collections, {sum(c["n"] for c in colls)} images')


if __name__ == '__main__':
    main(sys.argv[1:])
