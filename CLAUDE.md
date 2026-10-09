# CLAUDE.md

Guidance for Claude Code (and people) working in this repository.

## What this repo is

Tooling and documentation for the UCSB 3D campus capstone data. The data itself is not in the repo;
it lives on the `/data_8tb` drive of the workstation. This repo:

- documents where every dataset is (`docs/DATA_LOCATIONS.md`)
- lists every built collection with counts and GPS coverage (`docs/COLLECTIONS.md`)
- converts raw ground photos and drone images into WRIVA-format collections
  (`tools/build_wriva.py`, documented in `docs/WRIVA_FORMAT.md`)
- draws an HTML GPS map per collection (`tools/gps_map.py`)

## Project goal

Build a **"UCSB in 3D"** GitHub Pages site for the campus, modeled on
[JHU in 3D](https://cpeng93.github.io/JHU-in-3D/): a campus-wide aerial Gaussian splat plus per-building
ground and aerial splats, with fly-through camera paths, building labels, and aerial↔ground jumps.

- The organized `wriva_format` collections are the input for training those splats.
- The team trains the splats itself. Don't start the site until they're ready.
- Planned layout: site code in `site/` of this repo (GitHub Pages); large splat files on Hugging Face.
- JHU uses Three.js + [Spark](https://sparkjs.dev) (`@sparkjsdev/spark`, MIT) with `.rad` splat files and
  per-scene camera trajectory JSONs. Their source isn't published under a license, so write our own viewer.

## Key paths

| Path | What |
|---|---|
| `/data_8tb/capstone_3d/wriva_format/<collection>/` | Output: `images/`, `metadata/` (WRIVA 4.2.0 JSON + `site.json`), `manifest.csv`, `gps_map.html` |
| `/data_8tb/capstone_3d/capstone_emilid_data/extracted/` | Raw building photo zips (iPhone) + Emlid RTK CSV/XLSX, extracted |
| `/data_8tb/capstone_3d/Wingtra_Pilot_Projects_Mar30/` | Raw WingtraOne flights (`IMAGES/`, `DATA/*.json` onboard geotags) |
| `/data_8tb/Lizzy_web_data/` | Pix4D products + PPK geotags for Lagoon and Northwest (shared, group `charvi`) |
| `/data_8tb/capstone_3d/dji_drone_Apr9/100MEDIA/` | DJI videos, SRT telemetry, `DJI_*_iframes/` keyframes + `keyframe_manifest.csv` |
| `/data_8tb/data_chand_arxiv/sample_dataset_1/` | Reference layout the collections follow |
| `/data_8tb/wriva/` | Real WRIVA datasets, useful for schema examples |

## Commands

```bash
python3 -m venv .venv && .venv/bin/pip install -r tools/requirements.txt   # Pillow, pillow-heif, openpyxl
.venv/bin/python tools/build_wriva.py --list
.venv/bin/python tools/build_wriva.py <collection>          # skips folders that already exist
.venv/bin/python tools/gps_map.py <collection_dir>          # regenerate one map
```

To add a collection, add an entry to `GROUND`, `WINGTRA_FLIGHTS` or the extra `COLLECTIONS` in
`tools/build_wriva.py`, then document it in `docs/WRIVA_FORMAT.md`.

## Conventions that matter

- `extrinsics.alt` is WGS84 **ellipsoidal** height (m) in every collection. Above-sea-level sources
  are shifted by `UCSB_GEOID_N` (−35.8 m). DJI altitude is relative, so it is `null`.
- `extrinsic_calibration` / `geolocation` name the GPS source: `emlid_rtk`, `device_gps`,
  `wingtra_ppk`, `wingtra_gnss`, `dji_gps`, `none`.
- Emlid points are matched to photos by EXIF capture time within 5 s.
- Images are full copies named `image_NNNNNN.jpg` in capture-time order; `manifest.csv` maps back to
  the original file. HEIC is converted to JPEG (q95, upright, EXIF kept).
- Ground photos are built from the raw Drive exports, not the older `capstone_data/datasets/*`
  copies, whose written-back EXIF has a longitude sign bug in `lsb` / `elings_big_data`.

## Working on the data drive

- Treat `/data_8tb` sources as read-only. Do not delete or move originals (zips, duplicates) unless
  the user asks; known duplicates are listed in `docs/DATA_LOCATIONS.md`.
- Large reads and copies take minutes; run long builds in the background.
- Keep `docs/` up to date when data locations or the format change.
