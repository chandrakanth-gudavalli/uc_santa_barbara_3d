#!/usr/bin/env python3
"""Summarize every WRIVA collection into one CSV row per collection.

Reads <root>/<group>/<collection>/metadata/*.json (+ site.json, images/) and writes the CSV to each
output path given (default: docs/collections_summary.csv and <root>/collections_summary.csv).

Usage: summarize_collections.py [--root DIR] [out.csv ...]
"""
import csv
import datetime as dt
import json
import statistics
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path('/data_8tb/capstone_3d/wriva_format')
REPO = Path(__file__).resolve().parent.parent
PRECISE = ('emlid_rtk', 'wingtra_ppk')          # centimetre-level
NOISY = ('device_gps', 'wingtra_gnss', 'dji_gps')  # metre-level
SOURCES = PRECISE + NOISY

COLUMNS = [
    'dataset_name', 'group', 'dataset_type', 'site_name', 'total_image_count',
    'with_gps_image_count', 'no_gps_image_count', 'precise_gps_count', 'noisy_gps_count',
    'pct_with_gps', 'pct_precise_gps',
    *[f'{s}_count' for s in SOURCES],
    'median_h_uncertainty_precise_m', 'median_h_uncertainty_noisy_m',
    'with_altitude_count', 'with_intrinsics_count',
    'cameras', 'date_start', 'date_end',
    'center_lat', 'center_lon', 'images_size_gb', 'path',
]


def summarize(coll):
    site = json.loads((coll / 'metadata' / 'site.json').read_text())
    tz = ZoneInfo(site.get('timezone') or 'UTC')
    counts = dict.fromkeys(SOURCES + ('none',), 0)
    unc = {'precise': [], 'noisy': []}
    lats, lons, dates, cameras = [], [], set(), {}
    n = with_alt = with_intr = 0
    img_type = None
    for p in sorted((coll / 'metadata').glob('image_*.json')):
        m = json.loads(p.read_text())
        n += 1
        img_type = img_type or m.get('type')
        src = m.get('extrinsic_calibration') or 'none'
        counts[src] = counts.get(src, 0) + 1
        e = m['extrinsics']
        if e['lat'] is not None:
            lats.append(e['lat'])
            lons.append(e['lon'])
        if e['alt'] is not None:
            with_alt += 1
        if m.get('intrinsics'):
            with_intr += 1
        u = (m.get('extrinsic_uncertainty') or {}).get('lat')
        if u is not None:
            unc['precise' if src in PRECISE else 'noisy'].append(u)
        if m.get('timestamp'):
            dates.add(dt.datetime.fromtimestamp(m['timestamp'], tz).date().isoformat())
        if m.get('source'):
            cam = m['source'] if not m['source'].startswith('DJI drone') else 'DJI drone'
            cameras[cam] = cameras.get(cam, 0) + 1
    precise = sum(counts[s] for s in PRECISE)
    noisy = sum(counts[s] for s in NOISY)
    with_gps = precise + noisy
    med = lambda v: round(statistics.median(v), 3) if v else ''
    size = sum(f.stat().st_size for f in (coll / 'images').iterdir())
    return {
        'dataset_name': coll.name,
        'group': coll.parent.name,
        'dataset_type': img_type,
        'site_name': site.get('name', ''),
        'total_image_count': n,
        'with_gps_image_count': with_gps,
        'no_gps_image_count': n - with_gps,
        'precise_gps_count': precise,
        'noisy_gps_count': noisy,
        'pct_with_gps': round(100 * with_gps / n, 1) if n else '',
        'pct_precise_gps': round(100 * precise / n, 1) if n else '',
        **{f'{s}_count': counts[s] for s in SOURCES},
        'median_h_uncertainty_precise_m': med(unc['precise']),
        'median_h_uncertainty_noisy_m': med(unc['noisy']),
        'with_altitude_count': with_alt,
        'with_intrinsics_count': with_intr,
        'cameras': '; '.join(f'{c} ({k})' for c, k in sorted(cameras.items(), key=lambda x: -x[1])),
        'date_start': min(dates) if dates else '',
        'date_end': max(dates) if dates else '',
        'center_lat': round(statistics.median(lats), 6) if lats else '',
        'center_lon': round(statistics.median(lons), 6) if lons else '',
        'images_size_gb': round(size / 1e9, 2),
        'path': str(coll),
    }


def main(argv):
    root = ROOT
    if argv[:1] == ['--root']:
        root, argv = Path(argv[1]), argv[2:]
    outs = [Path(a) for a in argv] or [REPO / 'docs' / 'collections_summary.csv',
                                        root / 'collections_summary.csv']
    groups = ['Ground', 'drone', 'DJI']
    colls = [d for g in groups if (root / g).is_dir() for d in sorted((root / g).iterdir())
             if d.is_dir() and (d / 'metadata' / 'site.json').exists()]
    rows = sorted((summarize(c) for c in colls), key=lambda r: (groups.index(r['group']), r['dataset_name']))
    for out in outs:
        with open(out, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=COLUMNS)
            w.writeheader()
            w.writerows(rows)
        print(f'{out}: {len(rows)} collections')


if __name__ == '__main__':
    main(sys.argv[1:])
