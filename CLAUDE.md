# CLAUDE.md

Guidance for Claude Code (and people) working in this repository.

## What this repo is

Tooling and documentation for the UCSB 3D campus capstone data. The data itself is not in the repo;
it lives on the `/data_8tb` drive of the workstation. This repo:

- documents where every dataset is (`docs/DATA_LOCATIONS.md`)
- lists every built collection with counts and GPS coverage (`docs/COLLECTIONS.md`)
- converts raw ground photos and drone images into WRIVA-format collections
  (`tools/build_wriva.py`, documented in `docs/WRIVA_FORMAT.md`)
- draws an HTML GPS map per collection (`tools/gps_map.py`) and a campus-wide overview
  (`tools/overview_map.py` → `wriva_format/overview_map.html`)
- `README.md` images live in `docs/images/` (screenshots of those maps + a sample-image strip)

## Project goal

Build a **"UCSB in 3D"** GitHub Pages site for the campus, modeled on
[JHU in 3D](https://cpeng93.github.io/JHU-in-3D/): a campus-wide aerial Gaussian splat plus per-building
ground and aerial splats, with fly-through camera paths, building labels, and aerial↔ground jumps.

- The organized `wriva_format` collections are the input for training those splats.
- Layout: site code in `site/` of this repo (GitHub Pages); large splat files on Hugging Face.
- JHU uses Three.js + [Spark](https://sparkjs.dev) (`@sparkjsdev/spark`, MIT) with `.rad` splat files and
  per-scene camera trajectory JSONs. Their source isn't published under a license, so write our own viewer.

## The site (`site/`)

- Plain HTML/CSS/JS, no build step: three.js 0.180 from jsDelivr, Spark 2.3.1 vendored in `site/vendor/`.
- `site/scenes.json` is the catalog. `assetBase` is where the `.spz` files are loaded from (the Hugging Face repo);
  `?assets=<url>` overrides it. `site/scenes/<clip>.json` holds each scene's photo poses.
- Every scene is in one GPS frame (east-north-up metres, z up). Each `.spz` stores centres relative to an
  integer `splat_origin` (float16 precision), and the viewer puts the mesh back at that origin. Keep that when
  adding a scene, or the model renders displaced.
- The **Move** setting keeps the camera near the photos, because a splat is only reliable there: `photos`
  (default, on a photo position, ±10°), `near` (0.75× the local photo spacing, ±20°), `free`. The limits are
  `REACH`, `NEAR_DEG` and `PHOTO_DEG` at the top of `site/main.js`; `?mode=` sets the mode.
- Opening the page without a scene in the link plays a **flythrough** (`flightPath` in `site/main.js`): an
  loop at drone height looking straight down (as the drone photos do) inside the photo footprint for aerial
  scenes, the photographer's route for building walks. Dragging, scrolling or a key hands control back. `?autoplay=0|1` overrides.
- **Level of detail**: `lod: true` builds Spark's LoD tree in the browser after download. It adds ~12 s per 3 M-splat
  scene and a desktop GPU doesn't need it, so it is on for touch devices only (`?lod=1|0` forces it). Pre-built
  `.rad` files (Spark's Rust `build-lod --quality`, as JHU uses) would load instantly and stream; not done yet.
- Deploys: `.github/workflows/pages.yml` publishes `site/` on every push to `main` that changes it
  (Settings → Pages → Source: GitHub Actions).
- Local preview: `cd site && python3 -m http.server 8765 --bind 127.0.0.1`.

## Key paths

| Path | What |
|---|---|
| `/data_8tb/capstone_3d/wriva_format/{Ground,drone,DJI}/<collection>/` | Output (Ground = phone photos, drone = Wingtra, DJI = DJI video keyframes): `images/`, `metadata/` (WRIVA 4.2.0 JSON + `site.json`), `manifest.csv`, `gps_map.html` |
| `/data_8tb/capstone_3d/capstone_emilid_data/extracted/` | Raw building photo zips (iPhone) + Emlid RTK CSV/XLSX, extracted |
| `/data_8tb/capstone_3d/Wingtra_Pilot_Projects_Mar30/` | Raw WingtraOne flights (`IMAGES/`, `DATA/*.json` onboard geotags) |
| `/data_8tb/Lizzy_web_data/` | Pix4D products for Lagoon and Northwest; PPK geotags for Northwest only (Lagoon geotags are onboard GNSS) (shared, group `charvi`) |
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
  `wingtra_ppk`, `wingtra_gnss`, `dji_gps`, `none`. A Wingtra geotag counts as PPK only if its stated
  horizontal accuracy is < 0.5 m (`PPK_MAX_H_ACC_M`); file names and folder names are not trusted.
- Per-collection counts are in `docs/collections_summary.csv` (regenerate with `tools/summarize_collections.py`).
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
