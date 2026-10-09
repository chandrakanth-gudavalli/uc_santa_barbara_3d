# WRIVA-Format Collections

All UCSB capstone imagery (ground photos and drone images) is reorganized into one folder per
collection, following the layout of `/data_8tb/data_chand_arxiv/sample_dataset_1` and WRIVA image
metadata schema **4.2.0**.

- **Output root:** `/data_8tb/capstone_3d/wriva_format/`
- **Builder:** `tools/build_wriva.py` (writes everything below)
- **Map:** `tools/gps_map.py` (writes `gps_map.html`; called by the builder)

## Collection layout

```
<collection>/
  images/image_000001.jpg ...      full copies of source images (HEIC converted to JPEG q95)
  metadata/image_000001.json ...   per-image WRIVA metadata
  metadata/site.json               site bounds + timezone + notes
  manifest.csv                     image -> original file, GPS source, extra per-image fields
  gps_map.html                     interactive map of image positions
```

Images are numbered in capture-time order. `manifest.csv` maps every `image_NNNNNN.jpg` back to its
original file.

## Per-image metadata (`metadata/image_NNNNNN.json`)

| Field | Value |
|---|---|
| `version` | `"4.2.0"` |
| `fname`, `collection`, `site` | image file name, collection folder name, human-readable site name |
| `source` | camera, e.g. `"Apple iPhone 14 Pro Max"`, `"SONY ILX-LR1"`, `"DJI drone (DJI_0042)"` |
| `timestamp` | UTC unix seconds of capture |
| `extrinsics.lat/lon/alt` | position (see GPS sources below); `omega/phi/kappa` are `null` |
| `extrinsic_uncertainty` | 1-sigma metres `{lat, lon, alt}` from the GPS source, or `null` |
| `extrinsic_calibration`, `geolocation` | GPS source tag (table below) |
| `intrinsics` | pinhole estimate from EXIF 35mm-equivalent focal length (`fx = f35 · diag_px / 43.27`), principal point at image centre, zero distortion; `null` for DJI frames (no EXIF) |
| `intrinsic_calibration` | `"exif_focal_length_35mm"` or `null` |
| `type` | `"ground"` (phone photos) or `"airborne"` (Wingtra, DJI) |
| `projection` | `"perspective"` |
| `exterior` / `interior` | `true` / `false` |
| `env_conditions`, `modes`, `transient_occlusions`, `artifacts`, `masks`, `calibration` | `null` (not annotated) |

`rows`/`columns` in `intrinsics` describe the **stored** pixels. Images are copied byte-for-byte, so
the EXIF orientation flag is kept: iPhone JPGs are usually orientation 6 (rotate 90°), Wingtra
images are orientation 3 (rotate 180°). HEIC conversions are written upright with orientation 1.
`manifest.csv` has an `exif_orientation` column for ground photos.

## GPS sources

| Tag | Where it comes from | Typical accuracy |
|---|---|---|
| `emlid_rtk` | Emlid Reach RX2 RTK point whose averaging time is within **5 s** of the photo's EXIF capture time (nearest wins; one point can serve several photos) | 1–3 cm |
| `device_gps` | phone EXIF GPS (`GPSHPositioningError` used as uncertainty) | 5–15 m |
| `wingtra_ppk` | Wingtra PPK geotags (Pix4D/WingtraHub output in `Lizzy_web_data`) | 2–3 cm |
| `wingtra_gnss` | onboard WingtraOne geotags from the flight `DATA/*.json` (no PPK available) | ~5 m h / 10 m v |
| `dji_gps` | DJI SRT telemetry row matched to each extracted keyframe (`keyframe_manifest.csv`) | several m |
| `none` | no usable position (photo has no GPS and no Emlid match) | — |

### Altitude

`extrinsics.alt` is **WGS84 ellipsoidal height in metres** in every collection (so ground values
around UCSB are about −20 m and drone values about +55 m):

- Emlid: `Ellipsoidal height` column. All Emlid exports fill the global lat/lon/ellipsoidal columns,
  including the ones whose CS is NAD83 California zone 5, so those columns are used everywhere.
- Wingtra PPK: geotag altitude (already ellipsoidal).
- Phone EXIF and raw Wingtra GNSS: above-sea-level altitude + `UCSB_GEOID_N = -35.8 m`.
- DJI: telemetry altitude is height above takeoff, so `alt` is `null`; it is kept in
  `manifest.csv` as `rel_alt_m`.

Emlid positions are the surveyed ground point (pole tip, antenna height 1.945 m), not the phone
camera position.

### Validation

Phelps Hall matching was checked against the existing `manifest_photo_emlid.xml` from the earlier
pipeline (`capstone_data/datasets/Phelps/testing_out/`): 332 photos matched the same Emlid point,
2 picked a different point where two points were ~3 s apart, and 1 sat just past the 5 s tolerance.

## `site.json`

```json
{
  "bounds": "POLYGON((lon lat, ...))",   // convex hull of image positions + 15 m buffer
  "timezone": "America/Los_Angeles",
  "type": "real",
  "name": "UCSB Phelps Hall",
  "alt_reference": "WGS84 ellipsoidal height, metres",
  "notes": "Emlid export CS, antenna height, matching tolerance, ..."
}
```

`name`, `alt_reference` and `notes` are additions beyond the sample's `site.json`.

## `gps_map.html`

A Leaflet map (satellite / street basemaps) of every image position, coloured by GPS source, with
the site bounds, toggleable uncertainty circles, hover tooltips, click popups (time, coordinates,
uncertainty, camera, original file and an image preview) and a table of all positions. Open it from
inside the collection folder so the previews can load `images/…`. Needs internet for Leaflet and map
tiles.

## Collections and sources

### Ground (phone photos)

Built from the **raw** Google Drive exports extracted under
`capstone_emilid_data/extracted/` (the processed "with emlid data" zips are subsets of these).
Each collection uses every Emlid `.csv`/`.xlsx` in its zip folders (duplicates removed).
When a photo exists as HEIC and as a JPG copy, the HEIC original is used.

| Collection | Source zip folder(s) |
|---|---|
| `ucsb_bio_sci_2_ground` | Biological Sciences II |
| `ucsb_bren_ground` | Bren |
| `ucsb_broida_ground` | Broida (parts 001 + 002) |
| `ucsb_buchanan_ground` | Buchanan Hall (…231808Z) |
| `ucsb_campbell_ground` | Campbell (HEIC originals; the stripped `jpg (conv from heic)` folder is skipped) |
| `ucsb_chem_psnb_ground` | Chem |
| `ucsb_elings_lot10_ground` | Elings_Lot10 |
| `ucsb_ellison_ground` | Ellison Hall |
| `ucsb_engr2_ground` | ENGR II |
| `ucsb_esb_ground` | ESB |
| `ucsb_henley_ground` | Henley (parts 001 + 002) |
| `ucsb_hfh_ground` | HFH |
| `ucsb_kavli_ground` | Kavli |
| `ucsb_lsb_ground` | Life Science Building (parts 001 + 002) |
| `ucsb_marine_science_ground` | Marine Science (`demo_geo/` SfM output skipped) |
| `ucsb_mrl_ground` | MRL |
| `ucsb_north_hall_ground` | North Hall (parts 001 + 002) |
| `ucsb_ose_ground` | Ocean Science Education |
| `ucsb_phelps_ground` | Phelps |
| `ucsb_physical_science_south_ground` | Physical Science South (no Emlid file) |
| `ucsb_kavli_ground_2025` | `capstone_data/datasets/KavliEmlidfix/images`, iPhone 12 Pro Max photos only (spring 2025, no GPS) |
| `ucsb_elings_lot10_ground_2025` | Old Stuff zips, `Elings_Lot10 (OLD)` (Oct 2025) |
| `ucsb_mrl_hfh_ground_2025` | Old Stuff zips, `MRL + HFH Pictures (OLD)` |

### Wingtra (airborne)

| Collection | Flight | Positions |
|---|---|---|
| `ucsb_wingtra_northwest_f01` | Northwest Flight 01 | PPK (`Lizzy_web_data/3D_Campus_Model__North_West`) |
| `ucsb_wingtra_lagoon_f01` / `_f02` | Lagoon Flights 01 / 02 | PPK (Lizzy Lagoon merged geotags) |
| `ucsb_wingtra_north_middle_f01` | North Middle Flight 01 | onboard GNSS |
| `ucsb_wingtra_northeast_f01` / `_f02` | Northeast Flights 01 / 02 | onboard GNSS |
| `ucsb_wingtra_east_f01` | East New (copy) Flight 01 | onboard GNSS |
| `ucsb_wingtra_test_flight1_f01` / `_f02` | Test Flight 1, Flights 01 / 02 | onboard GNSS |

Yaw/pitch/roll (degrees) for every Wingtra image are in `manifest.csv`.

### DJI video keyframes (airborne)

`ucsb_dji_0025` … `ucsb_dji_0056`: one collection per video in `dji_drone_Apr9/100MEDIA`, from
`DJI_00XX_iframes/frames/` and its `keyframe_manifest.csv` (~1 fps keyframes matched to SRT
telemetry). `manifest.csv` keeps `video_time_s`, `rel_alt_m` and `focal_len`.

### Not included

- `/data_8tb/capstone/prairie` — senseFly aerial images from Montana, not UCSB.
- `/data_8tb/capstone/ElingsLot10JPG` — metadata-stripped copies of the Oct 2025 Elings photos
  (the originals are used via the Old Stuff zips).
- DJI frames inside `capstone_data/datasets/chem_big_data` and `HFH_MRL_DJI` — the same videos are
  covered by the `ucsb_dji_*` collections.

## Rebuilding

```bash
python3 -m venv .venv && .venv/bin/pip install -r tools/requirements.txt
.venv/bin/python tools/build_wriva.py --list                 # collection names
.venv/bin/python tools/build_wriva.py ucsb_phelps_ground     # one collection
.venv/bin/python tools/build_wriva.py --list | xargs -P 4 -n 1 .venv/bin/python tools/build_wriva.py
.venv/bin/python tools/gps_map.py /data_8tb/capstone_3d/wriva_format/<collection>   # map only
```

Existing collection folders are skipped; delete one to rebuild it.

## Known limitations

- `omega/phi/kappa` are not derived (Wingtra yaw/pitch/roll and phone compass heading are in
  `manifest.csv`).
- Intrinsics are EXIF estimates, not calibrations.
- DJI altitude is relative to takeoff only.
- `UCSB_GEOID_N` is a single campus-wide value; Emlid exports with both heights show −35.6 to −36.0 m.
