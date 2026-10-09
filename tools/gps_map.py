#!/usr/bin/env python3
"""Write gps_map.html into a WRIVA-style collection folder (images/ + metadata/).

The page is a Leaflet map of every image's lat/lon, coloured by GPS source, with the
site.json bounds, optional uncertainty circles, a click-to-preview popup (images/ is
referenced relatively, so open the HTML from inside the collection folder), and a
table view of all points.

Usage: gps_map.py <collection_dir> [<collection_dir> ...]
"""
import csv
import datetime as dt
import json
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

# Fixed source -> categorical slot, so a source has the same colour in every collection.
SOURCES = {
    'emlid_rtk': ('Emlid RTK', 'var(--series-1)'),
    'device_gps': ('Phone GPS', 'var(--series-2)'),
    'wingtra_ppk': ('Wingtra PPK', 'var(--series-3)'),
    'wingtra_gnss': ('Wingtra GNSS (non-PPK)', 'var(--series-4)'),
    'dji_gps': ('DJI GPS', 'var(--series-5)'),
}

TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ GPS Map</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css">
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
:root {
  --surface-0: #f4f3f0; --surface-1: #fcfcfb; --border: #dddcd7;
  --text-primary: #0b0b0b; --text-secondary: #52514e; --text-muted: #77766f;
  --series-1: #2a78d6; --series-2: #eb6834; --series-3: #1baf7a; --series-4: #eda100; --series-5: #e87ba4;
  --bounds: #4a3aa7; --ring: #ffffff;
}
@media (prefers-color-scheme: dark) {
  :root:not([data-theme="light"]) {
    --surface-0: #111110; --surface-1: #1a1a19; --border: #383835;
    --text-primary: #ffffff; --text-secondary: #c3c2b7; --text-muted: #9a998f;
    --series-1: #3987e5; --series-2: #d95926; --series-3: #199e70; --series-4: #c98500; --series-5: #d55181;
    --bounds: #9085e9; --ring: #1a1a19;
  }
}
:root[data-theme="dark"] {
  --surface-0: #111110; --surface-1: #1a1a19; --border: #383835;
  --text-primary: #ffffff; --text-secondary: #c3c2b7; --text-muted: #9a998f;
  --series-1: #3987e5; --series-2: #d95926; --series-3: #199e70; --series-4: #c98500; --series-5: #d55181;
  --bounds: #9085e9; --ring: #1a1a19;
}
* { box-sizing: border-box; }
body { margin: 0; background: var(--surface-0); color: var(--text-primary);
  font: 14px/1.45 system-ui, -apple-system, "Segoe UI", sans-serif; }
header { padding: 16px; display: flex; flex-wrap: wrap; gap: 8px 24px; align-items: baseline; }
h1 { font-size: 18px; margin: 0; font-weight: 600; }
.sub { color: var(--text-secondary); }
.controls { display: flex; flex-wrap: wrap; gap: 8px 16px; padding: 0 16px 12px; align-items: center; }
.chip { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; border: 1px solid var(--border);
  border-radius: 999px; background: var(--surface-1); cursor: pointer; user-select: none; color: var(--text-primary); font: inherit; }
.chip[aria-pressed="false"] { opacity: .45; }
.dot { width: 10px; height: 10px; border-radius: 50%; box-shadow: 0 0 0 2px var(--surface-1); }
.count { color: var(--text-secondary); font-variant-numeric: tabular-nums; }
label.toggle { display: inline-flex; gap: 6px; align-items: center; color: var(--text-secondary); cursor: pointer; }
#map { height: calc(100vh - 150px); min-height: 360px; margin: 0 16px; border: 1px solid var(--border); border-radius: 8px; }
.leaflet-popup-content { font-size: 13px; line-height: 1.4; }
.leaflet-popup-content img { display: block; max-width: 240px; max-height: 240px; margin-top: 6px; border-radius: 4px; }
.leaflet-popup-content dl { display: grid; grid-template-columns: auto 1fr; gap: 0 8px; margin: 4px 0 0; }
.leaflet-popup-content dt { color: #52514e; }
.leaflet-popup-content dd { margin: 0; font-variant-numeric: tabular-nums; }
details { margin: 16px; background: var(--surface-1); border: 1px solid var(--border); border-radius: 8px; }
summary { padding: 10px 14px; cursor: pointer; color: var(--text-secondary); }
.tablewrap { overflow: auto; max-height: 50vh; }
table { border-collapse: collapse; width: 100%; font-variant-numeric: tabular-nums; font-size: 13px; }
th, td { text-align: left; padding: 4px 10px; border-top: 1px solid var(--border); white-space: nowrap; }
th { position: sticky; top: 0; background: var(--surface-1); color: var(--text-secondary); font-weight: 500; }
.notes { margin: 0 16px 16px; color: var(--text-muted); font-size: 12px; }
@media (max-width: 600px) { #map { height: 65vh; } }
</style>
</head>
<body>
<header>
  <h1>__TITLE__</h1>
  <span class="sub" id="summary"></span>
</header>
<div class="controls" id="controls"></div>
<div id="map" role="img" aria-label="Map of image GPS positions"></div>
<details>
  <summary>Table of all positions</summary>
  <div class="tablewrap"><table id="tbl"></table></div>
</details>
<p class="notes" id="notes"></p>
<script>
const DATA = __DATA__;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const map = L.map('map', { preferCanvas: true });
const sat = L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}',
  { maxZoom: 21, maxNativeZoom: 19, attribution: 'Imagery &copy; Esri' });
const osm = L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
  { maxZoom: 21, maxNativeZoom: 19, attribution: '&copy; OpenStreetMap contributors' });
sat.addTo(map);
L.control.layers({ 'Satellite': sat, 'Streets': osm }, null, { position: 'topright' }).addTo(map);
L.control.scale({ imperial: false }).addTo(map);

const fmt = (v, d) => v == null ? '—' : Number(v).toFixed(d);
const esc = s => String(s ?? '').replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
function popup(p) {
  const u = p.unc ? `${fmt(p.unc.lat, 3)} m h${p.unc.alt != null ? ' / ' + fmt(p.unc.alt, 3) + ' m v' : ''}` : '—';
  return `<strong>${esc(p.fname)}</strong> <span style="color:#52514e">${esc(DATA.sources[p.src].label)}</span>
    <dl><dt>Time</dt><dd>${esc(p.time)}</dd><dt>Lat, lon</dt><dd>${fmt(p.lat, 7)}, ${fmt(p.lon, 7)}</dd>
    <dt>Alt</dt><dd>${fmt(p.alt, 2)} m</dd><dt>Uncertainty</dt><dd>${u}</dd>
    <dt>Camera</dt><dd>${esc(p.camera)}</dd><dt>Original</dt><dd>${esc(p.orig)}</dd></dl>
    <img loading="lazy" src="images/${esc(p.fname)}" alt="${esc(p.fname)}">`;
}

const groups = {}, circles = {};
const all = [];
for (const [key, s] of Object.entries(DATA.sources)) {
  groups[key] = L.layerGroup().addTo(map);
  circles[key] = L.layerGroup();
}
function draw() {
  for (const key in groups) { groups[key].clearLayers(); circles[key].clearLayers(); }
  for (const p of DATA.points) {
    if (p.lat == null) continue;
    const color = css(DATA.sources[p.src].color.slice(4, -1));
    L.circleMarker([p.lat, p.lon], { radius: 5, color: css('--ring'), weight: 2, fillColor: color, fillOpacity: 1 })
      .bindTooltip(`${p.fname} · ${DATA.sources[p.src].label}`, { direction: 'top', offset: [0, -4] })
      .bindPopup(() => popup(p), { maxWidth: 280 })
      .addTo(groups[p.src]);
    if (p.unc && p.unc.lat)
      L.circle([p.lat, p.lon], { radius: p.unc.lat, color, weight: 1, opacity: .6, fillOpacity: .05, interactive: false })
        .addTo(circles[p.src]);
  }
}
draw();
matchMedia('(prefers-color-scheme: dark)').addEventListener('change', draw);

let bounds = null;
if (DATA.bounds) {
  const ring = DATA.bounds.replace(/^POLYGON\(\(|\)\)$/g, '').split(',').map(s => s.trim().split(/\s+/).map(Number)).map(([x, y]) => [y, x]);
  bounds = L.polygon(ring, { color: css('--bounds'), weight: 2, dashArray: '6 4', fill: false, interactive: false }).addTo(map);
}
const pts = DATA.points.filter(p => p.lat != null).map(p => [p.lat, p.lon]);
if (pts.length) map.fitBounds(L.latLngBounds(pts).pad(0.08)); else map.setView([34.414, -119.845], 16);

// controls: one chip per source (toggle), plus uncertainty and bounds toggles
const ctl = document.getElementById('controls');
const counts = {};
for (const p of DATA.points) counts[p.src] = (counts[p.src] || 0) + 1;
for (const [key, s] of Object.entries(DATA.sources)) {
  if (!counts[key]) continue;
  const b = document.createElement('button');
  b.className = 'chip'; b.setAttribute('aria-pressed', 'true');
  b.innerHTML = `<span class="dot" style="background:${s.color}"></span>${esc(s.label)} <span class="count">${counts[key]}</span>`;
  b.onclick = () => {
    const on = b.getAttribute('aria-pressed') !== 'true';
    b.setAttribute('aria-pressed', on);
    if (on) { groups[key].addTo(map); if (unc.checked) circles[key].addTo(map); }
    else { map.removeLayer(groups[key]); map.removeLayer(circles[key]); }
  };
  ctl.appendChild(b);
}
const mk = (text, checked, fn) => {
  const l = document.createElement('label'); l.className = 'toggle';
  const i = document.createElement('input'); i.type = 'checkbox'; i.checked = checked; i.onchange = () => fn(i.checked);
  l.append(i, text); ctl.appendChild(l); return i;
};
const unc = mk('Uncertainty circles', false, on => {
  for (const key in circles) {
    const chipOn = map.hasLayer(groups[key]);
    if (on && chipOn) circles[key].addTo(map); else map.removeLayer(circles[key]);
  }
});
if (bounds) mk('Site bounds', true, on => on ? bounds.addTo(map) : map.removeLayer(bounds));

const missing = DATA.points.filter(p => p.lat == null).length;
document.getElementById('summary').textContent =
  `${DATA.points.length} images · ${DATA.type} · ${DATA.date_range}` + (missing ? ` · ${missing} without GPS` : '');
document.getElementById('notes').textContent =
  `Altitude: ${DATA.alt_reference}. ${DATA.notes} Click a point to preview the image (open this file from inside the collection folder).`;

const tbl = document.getElementById('tbl');
tbl.innerHTML = '<thead><tr><th>Image</th><th>Source</th><th>Time</th><th>Lat</th><th>Lon</th><th>Alt (m)</th><th>Horiz. unc. (m)</th><th>Original</th></tr></thead><tbody>' +
  DATA.points.map(p => `<tr><td>${esc(p.fname)}</td><td>${esc(DATA.sources[p.src].label)}</td><td>${esc(p.time)}</td>
    <td>${fmt(p.lat, 7)}</td><td>${fmt(p.lon, 7)}</td><td>${fmt(p.alt, 2)}</td><td>${p.unc ? fmt(p.unc.lat, 3) : '—'}</td><td>${esc(p.orig)}</td></tr>`).join('') +
  '</tbody>';
</script>
</body>
</html>
"""


def write_map(coll_dir):
    coll_dir = Path(coll_dir)
    site = json.loads((coll_dir / 'metadata' / 'site.json').read_text())
    tz = ZoneInfo(site.get('timezone') or 'UTC')
    orig = {}
    with open(coll_dir / 'manifest.csv', newline='') as f:
        for r in csv.DictReader(f):
            orig[r['fname']] = Path(r['original_path']).name
    points, times, img_type = [], [], None
    for p in sorted((coll_dir / 'metadata').glob('image_*.json')):
        m = json.loads(p.read_text())
        img_type = img_type or m.get('type')
        ts = m.get('timestamp')
        local = dt.datetime.fromtimestamp(ts, tz) if ts else None
        if local:
            times.append(local)
        src = m.get('extrinsic_calibration') or 'none'
        points.append({
            'fname': m['fname'], 'src': src, 'camera': m.get('source'),
            'lat': m['extrinsics']['lat'], 'lon': m['extrinsics']['lon'], 'alt': m['extrinsics']['alt'],
            'unc': m.get('extrinsic_uncertainty'),
            'time': local.strftime('%Y-%m-%d %H:%M:%S %Z') if local else None,
            'orig': orig.get(m['fname'], ''),
        })
    sources = {k: {'label': lab, 'color': col} for k, (lab, col) in SOURCES.items()}
    sources['none'] = {'label': 'No GPS', 'color': 'var(--text-muted)'}
    dates = sorted({t.date().isoformat() for t in times})
    data = {
        'points': points, 'sources': sources, 'bounds': site.get('bounds'), 'type': img_type,
        'alt_reference': site.get('alt_reference', 'unknown'), 'notes': site.get('notes', ''),
        'date_range': (dates[0] if len(dates) == 1 else f'{dates[0]} – {dates[-1]}') if dates else 'no timestamps',
    }
    title = site.get('name') or coll_dir.name
    html = (TEMPLATE.replace('__TITLE__', title.replace('<', '&lt;'))
            .replace('__DATA__', json.dumps(data).replace('</', '<\\/')))
    (coll_dir / 'gps_map.html').write_text(html)
    return coll_dir / 'gps_map.html'


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    for d in sys.argv[1:]:
        print(write_map(d))
