#!/usr/bin/env python3
"""Build WRIVA-style collections (images/ + metadata/) from UCSB capstone sources.

Each collection is written to <OUT_ROOT>/<name>/ as:
    images/image_000001.jpg ...     full copies of the source JPGs (HEIC converted to JPEG)
    metadata/image_000001.json ...  WRIVA image metadata (schema 4.2.0)
    metadata/site.json              site bounds polygon, timezone, type
    gps_map.html                    interactive map of image positions (tools/gps_map.py)
    manifest.csv                    new name -> original file, GPS source, raw orientation

Altitudes (`extrinsics.alt`) are WGS84 ellipsoidal heights in metres for every collection:
Emlid `Ellipsoidal height`, Wingtra PPK altitude, and above-sea-level altitudes (phone EXIF,
raw Wingtra GNSS) shifted by UCSB_GEOID_N. DJI video telemetry only has height above the
takeoff point, so DJI `alt` is null and that height is kept in manifest.csv.

Usage: build_wriva.py <collection>... | all | --list
Needs Pillow + pillow-heif for HEIC and openpyxl for Emlid .xlsx (see tools/requirements.txt).
"""
import csv
import datetime as dt
import json
import math
import re
import shutil
import struct
import sys
from pathlib import Path
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gps_map import write_map  # noqa: E402

OUT_ROOT = Path('/data_8tb/capstone_3d/wriva_format')
SCHEMA_VERSION = '4.2.0'
TIMEZONE = 'America/Los_Angeles'
# Geoid separation (ellipsoidal - orthometric) at UCSB, from Emlid exports with both heights
UCSB_GEOID_N = -35.8
EMLID_TOLERANCE_S = 5.0
BOUNDS_BUFFER_M = 15.0
IMAGE_EXTS = ('.jpg', '.jpeg', '.heic')


# --------------------------------------------------------------------------- EXIF

def _parse_ifd(t, bo, off):
    u16 = lambda o: struct.unpack(bo + 'H', t[o:o + 2])[0]
    u32 = lambda o: struct.unpack(bo + 'I', t[o:o + 4])[0]
    sizes = {1: 1, 2: 1, 3: 2, 4: 4, 5: 8, 7: 1, 9: 4, 10: 8}
    out = {}
    for i in range(u16(off)):
        e = off + 2 + 12 * i
        tag, typ, cnt = u16(e), u16(e + 2), u32(e + 4)
        sz = sizes.get(typ, 1) * cnt
        vo = e + 8 if sz <= 4 else u32(e + 8)
        if typ == 2:
            out[tag] = t[vo:vo + cnt].rstrip(b'\0').decode('latin1', 'ignore').strip()
        elif typ in (5, 10):
            fmt = bo + ('II' if typ == 5 else 'ii')
            out[tag] = [a / b if b else 0.0
                        for a, b in (struct.unpack(fmt, t[vo + 8 * k:vo + 8 * k + 8]) for k in range(cnt))]
        elif typ == 3:
            out[tag] = [u16(vo + 2 * k) for k in range(cnt)]
        elif typ == 4:
            out[tag] = [u32(vo + 4 * k) for k in range(cnt)]
        else:
            out[tag] = t[vo:vo + sz]
    return out


def read_jpeg_info(data):
    """EXIF fields we need plus the stored pixel size from the SOF marker."""
    info = {}
    i = 2
    while i < len(data) - 4 and data[i] == 0xFF:
        m = data[i + 1]
        ln = struct.unpack('>H', data[i + 2:i + 4])[0]
        if m == 0xE1 and data[i + 4:i + 10] == b'Exif\0\0' and 'model' not in info:
            t = data[i + 10:i + 2 + ln]
            bo = '<' if t[:2] == b'II' else '>'
            ifd0 = _parse_ifd(t, bo, struct.unpack(bo + 'I', t[4:8])[0])
            exif = _parse_ifd(t, bo, ifd0[0x8769][0]) if 0x8769 in ifd0 else {}
            gps = _parse_ifd(t, bo, ifd0[0x8825][0]) if 0x8825 in ifd0 else {}
            info['make'] = ifd0.get(0x010F, '')
            info['model'] = ifd0.get(0x0110, '')
            info['orientation'] = ifd0.get(0x0112, [1])[0]
            info['datetime'] = exif.get(0x9003) or ifd0.get(0x0132)
            info['offset'] = exif.get(0x9011)
            info['subsec'] = exif.get(0x9291)
            info['focal_mm'] = exif.get(0x920A, [None])[0]
            info['focal_35mm'] = exif.get(0xA405, [None])[0]
            if 2 in gps and 4 in gps and any(gps[2]):
                dms = lambda v: v[0] + v[1] / 60 + v[2] / 3600
                info['gps'] = {
                    'lat': dms(gps[2]) * (-1 if gps.get(1) == 'S' else 1),
                    'lon': dms(gps[4]) * (-1 if gps.get(3) == 'W' else 1),
                    'lon_ref_missing': 3 not in gps,
                    'alt': (gps[6][0] * (-1 if gps.get(5, b'\0')[:1] == b'\1' else 1)) if 6 in gps else None,
                    'herr': gps[31][0] if 31 in gps else None,
                    'img_direction': gps[17][0] if 17 in gps else None,
                }
        elif m in (0xC0, 0xC1, 0xC2):
            info['height'], info['width'] = struct.unpack('>HH', data[i + 5:i + 9])
            break
        elif m == 0xDA:
            break
        i += 2 + ln
    return info


def exif_timestamp(info):
    """UTC unix time from DateTimeOriginal + OffsetTimeOriginal (local TIMEZONE if no offset)."""
    if not info.get('datetime'):
        return None
    try:
        t = dt.datetime.strptime(info['datetime'], '%Y:%m:%d %H:%M:%S')
    except ValueError:
        return None
    if info.get('offset'):
        t = dt.datetime.strptime(info['datetime'] + info['offset'], '%Y:%m:%d %H:%M:%S%z')
    else:
        t = t.replace(tzinfo=ZoneInfo(TIMEZONE))
    ts = t.timestamp()
    if (info.get('subsec') or '').isdigit():
        ts += float('0.' + info['subsec'])
    return ts


def intrinsics_from_exif(info):
    """Pinhole estimate from 35mm-equivalent focal length (diagonal 43.27 mm); no distortion."""
    w, h, f35 = info.get('width'), info.get('height'), info.get('focal_35mm')
    if not (w and h and f35):
        return None
    f = f35 * math.hypot(w, h) / 43.2666
    return {'fx': f, 'fy': f, 'cx': w / 2, 'cy': h / 2,
            'k1': 0, 'k2': 0, 'k3': 0, 'p1': 0, 'p2': 0, 'rows': h, 'columns': w}


def heic_to_jpeg(src, dst):
    """Decode HEIC (rotation applied, EXIF orientation reset) and save as JPEG with its EXIF."""
    import pillow_heif
    from PIL import Image
    pillow_heif.register_heif_opener()
    with Image.open(src) as im:
        exif = im.getexif()
        exif[0x0112] = 1
        im.convert('RGB').save(dst, 'JPEG', quality=95, exif=exif.tobytes())


# --------------------------------------------------------------------------- sources

def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load_emlid(paths):
    """Emlid Reach exports (.csv / .xlsx) -> de-duplicated points with UTC midpoint time."""
    rows = []
    for p in paths:
        if p.suffix.lower() == '.xlsx':
            import openpyxl
            ws = openpyxl.load_workbook(p, read_only=True, data_only=True).active
            it = ws.iter_rows(values_only=True)
            head = ['' if h is None else str(h) for h in next(it)]
            rows += [dict(zip(head, ['' if v is None else str(v) for v in r])) for r in it]
        else:
            with open(p, newline='', encoding='utf-8-sig') as f:
                rows += list(csv.DictReader(f))

    def t(v):
        return dt.datetime.strptime(v.replace(' UTC', ''), '%Y-%m-%d %H:%M:%S.%f%z').timestamp()

    pts, seen = [], set()
    for row in rows:
        lat, lon, h = (_num(row.get(c)) for c in ('Latitude', 'Longitude', 'Ellipsoidal height'))
        if lat is None or lon is None or h is None or not row.get('Averaging start'):
            continue
        key = (row['Averaging start'], round(lat, 8), round(lon, 8))
        if key in seen:
            continue
        seen.add(key)
        pts.append({
            'name': row.get('Name', ''), 'lat': lat, 'lon': lon, 'alt': h,
            'n_rms': _num(row.get('Northing RMS')), 'e_rms': _num(row.get('Easting RMS')),
            'v_rms': _num(row.get('Elevation RMS')),
            'status': row.get('Solution status', ''),
            'antenna_height': row.get('Antenna height', ''),
            'cs_name': row.get('CS name', ''),
            'time': (t(row['Averaging start']) + t(row.get('Averaging end') or row['Averaging start'])) / 2,
        })
    return pts


def match_emlid(ts, pts):
    """Nearest Emlid point by time within tolerance (one point may serve several photos)."""
    if ts is None or not pts:
        return None
    best = min(pts, key=lambda p: abs(p['time'] - ts))
    return best if abs(best['time'] - ts) <= EMLID_TOLERANCE_S else None


def photo_key(path):
    """Identity of a photo across formats/copies: 'Copy of IMG_1148.jpeg' == 'IMG_1148.HEIC'."""
    return re.sub(r'^copy of ', '', path.stem.strip(), flags=re.I).upper()


def find_photos(roots, exclude=()):
    """One file per photo under roots; a HEIC original wins over a JPG copy of it."""
    best = {}
    for root in roots:
        for p in sorted(Path(root).rglob('*')):
            if (not p.is_file() or p.suffix.lower() not in IMAGE_EXTS or p.name.startswith('._')
                    or any(x in str(p.relative_to(root)) for x in exclude)):
                continue
            k = photo_key(p)
            if k not in best or (p.suffix.lower() == '.heic' and best[k].suffix.lower() != '.heic'):
                best[k] = p
    return list(best.values())


def find_emlid_files(roots, exclude=()):
    return [p for root in roots for p in sorted(Path(root).rglob('*'))
            if p.suffix.lower() in ('.csv', '.xlsx') and not p.name.lower().startswith('manifest')
            and not any(x in str(p.relative_to(root)) for x in exclude)]


def load_wingtra_ppk(wgs84_csv, geotaglog=None):
    """PPK pose keyed by lowercase image name (angles in degrees)."""
    out = {}
    with open(wgs84_csv, newline='') as f:
        for r in csv.reader(f):
            if r and not r[0].startswith('#'):
                out[r[0].lower()] = {
                    'lat': float(r[1]), 'lon': float(r[2]), 'alt': float(r[3]),
                    'yaw': float(r[4]), 'pitch': float(r[5]), 'roll': float(r[6]),
                    'h_acc': float(r[7]), 'v_acc': float(r[8]), 'time': None}
    if geotaglog:
        for im in json.load(open(geotaglog))['images']:
            ref = im.get('geotaggedImage', {}).get('geoRef', {})
            if im['imageName'].lower() in out and 'timestamp' in ref:
                out[im['imageName'].lower()]['time'] = ref['timestamp']
    return out


def load_wingtra_raw(flight_dir):
    """Onboard (non-PPK) geotags keyed by image sequence number (angles converted to degrees)."""
    js = next((Path(flight_dir) / 'DATA').glob('*.json'))
    out = {}
    for g in json.load(open(js))['flights'][0]['geotag']:
        lat, lon, alt = (float(v) for v in g['coordinate'])
        out[int(g['sequence'])] = {
            'lat': lat, 'lon': lon, 'alt': alt + UCSB_GEOID_N,
            'yaw': math.degrees(float(g['yaw'])), 'pitch': math.degrees(float(g['pitch'])),
            'roll': math.degrees(float(g['roll'])),
            'h_acc': float(g['hAccuracy']), 'v_acc': float(g['vAccuracy']),
            'time': float(g['timestamp']) / 1000}
    return out


# --------------------------------------------------------------------------- output

def bounds_wkt(latlons):
    """Convex hull of positions, pushed out from its centroid by BOUNDS_BUFFER_M."""
    pts = sorted(set(latlons))
    if len(pts) < 3:
        return None
    cross = lambda o, a, b: (a[1] - o[1]) * (b[0] - o[0]) - (a[0] - o[0]) * (b[1] - o[1])
    lo, hi = [], []
    for p in pts:
        while len(lo) >= 2 and cross(lo[-2], lo[-1], p) <= 0:
            lo.pop()
        lo.append(p)
    for p in reversed(pts):
        while len(hi) >= 2 and cross(hi[-2], hi[-1], p) <= 0:
            hi.pop()
        hi.append(p)
    hull = lo[:-1] + hi[:-1]
    if len(hull) < 3:
        return None
    clat = sum(p[0] for p in hull) / len(hull)
    clon = sum(p[1] for p in hull) / len(hull)
    m_lat, m_lon = 111320.0, 111320.0 * math.cos(math.radians(clat))
    ring = []
    for lat, lon in hull:
        dy, dx = (lat - clat) * m_lat, (lon - clon) * m_lon
        d = math.hypot(dx, dy) or 1.0
        s = (d + BOUNDS_BUFFER_M) / d
        ring.append((clon + dx * s / m_lon, clat + dy * s / m_lat))
    ring.append(ring[0])
    return 'POLYGON((' + ', '.join(f'{x} {y}' for x, y in ring) + '))'


def image_json(fname, site, collection, source, ts, ext, unc, intr, ext_cal, img_type):
    return {
        'version': SCHEMA_VERSION,
        'fname': fname,
        'site': site,
        'source': source,
        'collection': collection,
        'timestamp': ts,
        'extrinsics': {'lat': ext['lat'], 'lon': ext['lon'], 'alt': ext['alt'],
                       'omega': None, 'phi': None, 'kappa': None},
        'extrinsic_uncertainty': unc,
        'intrinsics': intr,
        'projection': 'perspective',
        'calibration': None,
        'intrinsic_calibration': 'exif_focal_length_35mm' if intr else None,
        'extrinsic_calibration': ext_cal,
        'geolocation': ext_cal,
        'env_conditions': None,
        'type': img_type,
        'modes': None,
        'exterior': True,
        'interior': False,
        'transient_occlusions': None,
        'artifacts': None,
        'masks': None,
    }


NO_POS = {'lat': None, 'lon': None, 'alt': None}


def write_collection(name, site, img_type, records, notes, staging=None):
    """records: dicts with src (file to copy), orig, ts, ext, unc, intr, ext_cal, source, manifest."""
    out = OUT_ROOT / name
    (out / 'images').mkdir(parents=True)
    (out / 'metadata').mkdir()
    records.sort(key=lambda r: (r['ts'] is None, r['ts'] or 0, str(r['orig'])))
    extra_cols = sorted({k for r in records for k in r.get('manifest', {})})
    with open(out / 'manifest.csv', 'w', newline='') as mf:
        w = csv.writer(mf)
        w.writerow(['fname', 'original_path', 'gps_source'] + extra_cols)
        for i, r in enumerate(records, 1):
            fname = f'image_{i:06d}.jpg'
            shutil.copy2(r['src'], out / 'images' / fname)
            meta = image_json(fname, site, name, r['source'], r['ts'], r['ext'], r['unc'],
                              r['intr'], r['ext_cal'], img_type)
            (out / 'metadata' / f'image_{i:06d}.json').write_text(json.dumps(meta, indent=4) + '\n')
            m = r.get('manifest', {})
            w.writerow([fname, str(r['orig']), r['ext_cal']] + [m.get(c, '') for c in extra_cols])
    pos = [(r['ext']['lat'], r['ext']['lon']) for r in records if r['ext']['lat'] is not None]
    site_json = {'bounds': bounds_wkt(pos), 'timezone': TIMEZONE, 'type': 'real',
                 'name': site, 'alt_reference': 'WGS84 ellipsoidal height, metres', 'notes': notes}
    (out / 'metadata' / 'site.json').write_text(json.dumps(site_json, indent=4) + '\n')
    if staging:
        shutil.rmtree(staging, ignore_errors=True)
    write_map(out)
    counts = {}
    for r in records:
        counts[r['ext_cal']] = counts.get(r['ext_cal'], 0) + 1
    print(f'{name}: {len(records)} images -> {out}  gps sources: {counts}', flush=True)


# --------------------------------------------------------------------------- builders

def build_ground(name, site, roots, exclude=(), keep=None, notes=''):
    """Phone photos; Emlid RTK position when an Emlid point is within tolerance, else phone GPS."""
    pts = load_emlid(find_emlid_files(roots, exclude))
    staging = OUT_ROOT / '.staging' / name
    records = []
    for orig in find_photos(roots, exclude):
        src = orig
        if orig.suffix.lower() == '.heic':
            staging.mkdir(parents=True, exist_ok=True)
            src = staging / (orig.stem + '.jpg')
            heic_to_jpeg(orig, src)
        info = read_jpeg_info(src.read_bytes())
        if keep and not keep(info):
            continue
        ts = exif_timestamp(info)
        p = match_emlid(ts, pts)
        g = info.get('gps')
        man = {'phone_heading_deg': g['img_direction'] if g else '',
               'exif_orientation': info.get('orientation', '')}
        if p:
            ext = {'lat': p['lat'], 'lon': p['lon'], 'alt': p['alt']}
            unc = {'lat': p['n_rms'], 'lon': p['e_rms'], 'alt': p['v_rms']}
            cal = 'emlid_rtk'
            man.update(emlid_point=p['name'], emlid_dt_s=round(p['time'] - ts, 2),
                       emlid_status=p['status'])
        elif g and not g['lon_ref_missing']:
            alt = g['alt'] + UCSB_GEOID_N if g['alt'] is not None else None
            ext = {'lat': g['lat'], 'lon': g['lon'], 'alt': alt}
            unc = {'lat': g['herr'], 'lon': g['herr'], 'alt': None} if g['herr'] else None
            cal = 'device_gps'
        else:
            ext, unc, cal = dict(NO_POS), None, 'none'
        records.append({'src': src, 'orig': orig, 'ts': ts, 'ext': ext, 'unc': unc,
                        'intr': intrinsics_from_exif(info), 'ext_cal': cal,
                        'source': f"{info.get('make', '')} {info.get('model', '')}".strip() or None,
                        'manifest': man})
    if pts:
        cs = sorted({p['cs_name'] for p in pts if p['cs_name']})
        ant = sorted({p['antenna_height'] for p in pts if p['antenna_height']})
        notes = (notes + f' Emlid export CS: {cs} (lat/lon/ellipsoidal height columns used);'
                 f' antenna height(s) {ant} m; positions are the surveyed point (pole tip).'
                 f' Matched to photos by time within {EMLID_TOLERANCE_S} s.').strip()
    else:
        notes = (notes + ' No Emlid data for this capture.').strip()
    write_collection(name, site, 'ground', records, notes, staging)


def build_wingtra(name, site, flight_dir, ppk_csv=None, geotaglog=None, notes=''):
    """WingtraOne images; PPK geotags when available, else the onboard GNSS geotags."""
    ppk = load_wingtra_ppk(ppk_csv, geotaglog) if ppk_csv else {}
    raw = load_wingtra_raw(flight_dir)
    records = []
    for src in sorted((Path(flight_dir) / 'IMAGES').iterdir()):
        if src.suffix.lower() != '.jpg' or src.name.startswith('._'):
            continue
        seq = int(re.search(r'(\d+)$', src.stem).group(1))
        g, cal = ppk.get(src.name.lower()), 'wingtra_ppk'
        if not g:
            g, cal = raw.get(seq), 'wingtra_gnss'
        info = read_jpeg_info(src.read_bytes())
        if g:
            ext = {'lat': g['lat'], 'lon': g['lon'], 'alt': g['alt']}
            unc = {'lat': g['h_acc'], 'lon': g['h_acc'], 'alt': g['v_acc']}
            ts = g['time'] or (raw[seq]['time'] if seq in raw else None)
            man = {'yaw_deg': g['yaw'], 'pitch_deg': g['pitch'], 'roll_deg': g['roll']}
        else:
            ext, unc, cal, ts, man = dict(NO_POS), None, 'none', None, {}
        records.append({'src': src, 'orig': src, 'ts': ts, 'ext': ext, 'unc': unc,
                        'intr': intrinsics_from_exif(info), 'ext_cal': cal,
                        'source': f"{info.get('make', '')} {info.get('model', '')}".strip() or None,
                        'manifest': man})
    notes = (notes + (' Positions from Wingtra PPK geotags.' if ppk else
                      ' Positions from onboard (non-PPK) Wingtra GNSS geotags; altitude converted'
                      f' from above-sea-level with geoid N={UCSB_GEOID_N} m.') +
             ' Times from geotags (camera EXIF clock is not set). Camera yaw/pitch/roll are in'
             ' manifest.csv; omega/phi/kappa not derived.').strip()
    write_collection(name, site, 'airborne', records, notes)


def build_dji(name, site, frames_dir, notes=''):
    """Keyframes extracted from a DJI video, positioned by the matched SRT telemetry row."""
    video = frames_dir.name.split('_iframes')[0]
    records = []
    with open(frames_dir / 'keyframe_manifest.csv', newline='') as f:
        for r in csv.DictReader(f):
            src = frames_dir / 'frames' / Path(r['image_path'].replace('\\', '/')).name
            if r.get('status') != 'ok' or not src.exists():
                continue
            lat, lon = _num(r['latitude']), _num(r['longitude'])
            m = re.match(r'(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d),(\d+)', r.get('matched_telemetry_timestamp', ''))
            ts = None
            if m:
                t = dt.datetime.strptime(m.group(1), '%Y-%m-%d %H:%M:%S').replace(tzinfo=ZoneInfo(TIMEZONE))
                ts = t.timestamp() + int(m.group(2)) / 1000
            ok = bool(lat and lon)
            records.append({'src': src, 'orig': src, 'ts': ts,
                            'ext': {'lat': lat, 'lon': lon, 'alt': None} if ok else dict(NO_POS),
                            'unc': None, 'intr': None, 'ext_cal': 'dji_gps' if ok else 'none',
                            'source': f'DJI drone ({video})',
                            'manifest': {'video': video, 'video_time_s': r['time_sec'],
                                         'rel_alt_m': r['altitude'], 'focal_len': r['focal_len']}})
    notes = (notes + f' Keyframes of {video}.MP4 at ~1 fps; lat/lon from the DJI SRT telemetry row'
             ' matched to each frame. Telemetry altitude is relative to takeoff (manifest.csv'
             ' rel_alt_m), so extrinsics.alt is null.').strip()
    write_collection(name, site, 'airborne', records, notes)


# --------------------------------------------------------------------------- collections

CAP = Path('/data_8tb/capstone_3d')
EMLID = CAP / 'capstone_emilid_data/extracted'
OLD = [EMLID / 'Old Stuff-20260616T011527Z-3-001/Old Stuff', EMLID / 'Old Stuff-20260616T011527Z-3-002/Old Stuff']
WINGTRA = CAP / 'Wingtra_Pilot_Projects_Mar30'
DJI = CAP / 'dji_drone_Apr9/100MEDIA'
LIZZY = Path('/data_8tb/Lizzy_web_data')

# name: (site, extracted zip folders, kwargs)
GROUND = {
    'ucsb_bio_sci_2_ground': ('UCSB Biological Sciences II', ['Biological Sciences II-20260615T231358Z-3-001'], {}),
    'ucsb_bren_ground': ('UCSB Bren Hall', ['Bren-20260615T231426Z-3-001'], {}),
    'ucsb_broida_ground': ('UCSB Broida Hall', ['Broida-20260615T231802Z-3-001', 'Broida-20260615T231802Z-3-002'], {}),
    'ucsb_buchanan_ground': ('UCSB Buchanan Hall', ['Buchanan Hall-20260615T231808Z-3-001'], {}),
    'ucsb_campbell_ground': ('UCSB Campbell Hall', ['Campbell-20260615T232705Z-3-001'],
                             {'exclude': ('jpg (conv from heic)',)}),
    'ucsb_chem_psnb_ground': ('UCSB Chemistry / Physical Sciences North', ['Chem-20260615T232710Z-3-001'], {}),
    'ucsb_elings_lot10_ground': ('UCSB Elings Hall / Lot 10', ['Elings_Lot10-20260616T010635Z-3-001'], {}),
    'ucsb_ellison_ground': ('UCSB Ellison Hall', ['Ellison Hall-20260616T010642Z-3-001'], {}),
    'ucsb_engr2_ground': ('UCSB Engineering II', ['ENGR II-20260616T010650Z-3-001'], {}),
    'ucsb_esb_ground': ('UCSB Engineering Science Building', ['ESB-20260616T011324Z-3-001'], {}),
    'ucsb_henley_ground': ('UCSB Henley Hall', ['Henley -20260616T011416Z-3-001', 'Henley -20260616T011416Z-3-002'], {}),
    'ucsb_hfh_ground': ('UCSB Harold Frank Hall', ['HFH-20260616T011420Z-3-001'], {}),
    'ucsb_kavli_ground': ('UCSB Kavli Institute (KITP)', ['Kavli-20260616T011430Z-3-001'], {}),
    'ucsb_lsb_ground': ('UCSB Life Sciences Building', ['Life Science Building-20260616T011508Z-3-001',
                                                        'Life Science Building-20260616T011508Z-3-002'], {}),
    'ucsb_marine_science_ground': ('UCSB Marine Science Building', ['Marine Science-20260616T011512Z-3-001'],
                                   {'exclude': ('demo_geo',)}),
    'ucsb_mrl_ground': ('UCSB Materials Research Laboratory', ['MRL-20260616T011516Z-3-001'], {}),
    'ucsb_north_hall_ground': ('UCSB North Hall', ['North Hall-20260616T011521Z-3-001',
                                                   'North Hall-20260616T011521Z-3-002'], {}),
    'ucsb_ose_ground': ('UCSB Ocean Science Education Building', ['Ocean Science Education-20260616T011524Z-3-001'], {}),
    'ucsb_phelps_ground': ('UCSB Phelps Hall', ['Phelps-20260616T011609Z-3-001'], {}),
    'ucsb_physical_science_south_ground': ('UCSB Physical Sciences South',
                                           ['Physical Science South-20260616T011612Z-3-001'], {}),
}

# name: (site, flight folder, PPK csv, geotaglog)
LAGOON_PPK = LIZZY / 'Lagoon/3D Campus Model - Lagoon Flight 01 - Merged datasets geotags - WGS84 - 4326.csv'
NW = LIZZY / '3D_Campus_Model__North_West'
WINGTRA_FLIGHTS = {
    'ucsb_wingtra_northwest_f01': ('UCSB Campus Northwest', '3D Campus Model - Northwest Flight 01',
                                   NW / '3D Campus Model - Northwest geotags - WGS84 - 4326.csv',
                                   NW / '3D Campus Model - Northwest.geotaglog'),
    'ucsb_wingtra_lagoon_f01': ('UCSB Campus Lagoon', '3D Campus Model - Lagoon Flight 01', LAGOON_PPK, None),
    'ucsb_wingtra_lagoon_f02': ('UCSB Campus Lagoon', '3D Campus Model - Lagoon Flight 02', LAGOON_PPK, None),
    'ucsb_wingtra_north_middle_f01': ('UCSB Campus North Middle', '3D Campus Model - North Middle Flight 01', None, None),
    'ucsb_wingtra_northeast_f01': ('UCSB Campus Northeast', '3D Campus Model - Northeast Flight 01', None, None),
    'ucsb_wingtra_northeast_f02': ('UCSB Campus Northeast', '3D Campus Model - Northeast Flight 02', None, None),
    'ucsb_wingtra_east_f01': ('UCSB Campus East', '3D Campus Flight - East New (copy) Flight 01', None, None),
    'ucsb_wingtra_test_flight1_f01': ('UCSB Wingtra Test Flight 1', 'Test Flight 1  Flight 01', None, None),
    'ucsb_wingtra_test_flight1_f02': ('UCSB Wingtra Test Flight 1', 'Test Flight 1  Flight 02', None, None),
}

COLLECTIONS = {}
for _n, (_site, _zips, _kw) in GROUND.items():
    COLLECTIONS[_n] = (lambda n=_n, s=_site, z=_zips, kw=_kw:
                       build_ground(n, s, [EMLID / x for x in z], **kw))
COLLECTIONS.update({
    'ucsb_kavli_ground_2025': lambda: build_ground(
        'ucsb_kavli_ground_2025', 'UCSB Kavli Institute (KITP)', [CAP / 'capstone_data/datasets/KavliEmlidfix/images'],
        keep=lambda i: i.get('model') == 'iPhone 12 Pro Max', notes='Spring 2025 capture (iPhone 12 Pro Max).'),
    'ucsb_elings_lot10_ground_2025': lambda: build_ground(
        'ucsb_elings_lot10_ground_2025', 'UCSB Elings Hall / Lot 10', [p / 'Elings_Lot10 (OLD)' for p in OLD],
        notes='October 2025 capture ("Old Stuff" zips).'),
    'ucsb_mrl_hfh_ground_2025': lambda: build_ground(
        'ucsb_mrl_hfh_ground_2025', 'UCSB Materials Research Lab / Harold Frank Hall',
        [p / 'MRL + HFH Pictures (OLD)' for p in OLD], notes='Earlier capture ("Old Stuff" zips).'),
})
for _n, (_site, _dir, _ppk, _log) in WINGTRA_FLIGHTS.items():
    COLLECTIONS[_n] = (lambda n=_n, s=_site, d=_dir, p=_ppk, g=_log:
                       build_wingtra(n, s, WINGTRA / d, p, g))
for _d in sorted(DJI.glob('DJI_*_iframes*')):
    if (_d / 'keyframe_manifest.csv').exists():
        _vid = _d.name.split('_iframes')[0]
        _n = 'ucsb_dji_' + _vid.split('_')[1]
        COLLECTIONS[_n] = (lambda n=_n, d=_d, v=_vid:
                           build_dji(n, f'UCSB campus (DJI video {v})', d))

if __name__ == '__main__':
    args = sys.argv[1:]
    if args == ['--list']:
        print('\n'.join(COLLECTIONS))
        sys.exit()
    names = list(COLLECTIONS) if args == ['all'] else args
    unknown = [n for n in names if n not in COLLECTIONS]
    if not names or unknown:
        sys.exit(f'usage: build_wriva.py <collection>... | all | --list   (unknown: {unknown})')
    for n in names:
        if (OUT_ROOT / n).exists():
            print(f'skip {n}: {OUT_ROOT / n} already exists (remove it to rebuild)', flush=True)
            continue
        COLLECTIONS[n]()
