# Capstone Data Locations

All capstone 3D-reconstruction data lives on the `/data_8tb` drive. This document maps where each dataset is, what it contains, and where copies overlap.

_Last surveyed: 2026-10-09. Sizes are from `du -sh`._

## Overview

| Path | Size | Contents |
|---|---|---|
| `/data_8tb/capstone_3d/wriva_format/` | — | **Organized collections** in `Ground/` (buildings), `drone/` (Wingtra) and `DJI/` (DJI video): one folder per building / flight / video with `images/`, WRIVA `metadata/`, `manifest.csv`, `gps_map.html`. See [WRIVA_FORMAT.md](WRIVA_FORMAT.md) |
| `/data_8tb/capstone_3d/` | 513 GB | Main capstone workspace: raw drone data, Emlid building captures, prepared datasets, SfM and Gaussian Splatting results |
| `/data_8tb/Wingtra_Pilot_Projects_Mar30/` | 107 GB | Raw WingtraOne flights (same as the copy in `capstone_3d/`) |
| `/data_8tb/Lizzy_web_data/` | 237 GB | Pix4D-processed Wingtra surveys (Lagoon, Northwest): ortho, DSM, point cloud, mesh, geotags (PPK for Northwest only) |
| `/data_8tb/capstone/` | 6 GB | Early ground-level image sets (Elings Lot 10, prairie) |
| `/data_8tb/UCSB_3D Campus Model _ Northwest_point_cloud.laz` | 870 MB | Northwest Pix4D point cloud (same as the copy in `Lizzy_web_data/`) |

---

## `/data_8tb/capstone_3d/`

### `Wingtra_Pilot_Projects_Mar30/` (107 GB)
Raw WingtraOne fixed-wing VTOL flights. Each flight has `IMAGES/`, `DATA/`, and `FLIGHT RECORD/` (PX4 `.ulg` logs).

| Flight | Size |
|---|---|
| 3D Campus Model - Lagoon Flight 01 | 44 GB |
| 3D Campus Model - Northwest Flight 01 | 20 GB |
| 3D Campus Model - North Middle Flight 01 | 19 GB |
| 3D Campus Model - Lagoon Flight 02 | 12 GB |
| 3D Campus Flight - East New (copy) Flight 01 | 8.1 GB |
| 3D Campus Model - Northeast Flight 01 / 02 | 1.9 GB / 1.4 GB |
| Test Flight 1 Flight 01 / 02 | 652 MB / 445 MB |

### `dji_drone_Apr9/` (77 GB)
DJI drone video captured on April 9.
- `100MEDIA/`: 33 MP4 videos (`DJI_0025` to `DJI_0056`), 32 `.SRT` telemetry files, a `DJI_00XX_iframes/` frame folder for each video, plus 2 helper `.py` scripts and 2 `.html` files.
- `DJI_0042_frames/`: 118 extracted frames.

### `capstone_emilid_data/` (44 GB)
Ground-level iPhone captures of campus buildings, with Emlid Reach RX2 GNSS point logs (37 zips, all extracted under `extracted/`).
- `Dataset/Phelps/`: 1.4 GB, 328 `IMG_*.JPG`, extracted from `Dataset-…-023.zip`.
- `extracted/<zip name>/`: every data zip extracted into its own folder (35 zips, 42 GB; file counts verified against the zips). Skipped: `nixos-config-main.zip` (unrelated), `Untitled folder…zip` (empty), `Dataset-…-023.zip` (already in `Dataset/Phelps/`). The zips themselves are kept.

#### Two kinds of zip

**Raw Google Drive exports** (`<Building>-2026061…Z-3-00N.zip`)
- Original photos, often a mix of `.jpg`, `.jpeg`, and `.HEIC`.
- A `.csv` / `.xlsx` export of Emlid points: point number, lat/lon, elevation, RMS accuracy, solution status (RTK FIX), timestamp, CRS `NAD83(2011) / California zone 5 + EGM2008 height`. These list measured points only; they do not link points to photos.

**Processed versions** (`… (with emlid data).zip`, `…(emlidversion).zip`, `CHEMPSNB.zip`)
- `testing_out/*.jpg`: photos converted to JPG and renamed with a hash (e.g. `IMG_2581_9e0b95f5.jpg`). This is the format used in `capstone_data/datasets/*/testing_out/`.
- `manifest.csv` / `manifest.jsonl`: source → converted file mapping, with SHA1 checksums, width/height, and input format.
- `manifest_photo_emlid.xml` (most of them): matches photos to Emlid points by timestamp (5 s tolerance) and records that GNSS positions were written back to EXIF. Example: CHEM matched 303 of 376 photos.

#### Contents by building

| Building | Raw export | Processed version |
|---|---|---|
| Biological Sciences II | 263 jpg + csv/xlsx | 204 jpg + manifest + xml |
| Bren | 305 jpg + csv | 181 jpg + manifest (no xml) |
| Broida | 2 parts: 356 + 82 jpg, xlsx | 438 jpg + manifest + xml (stored twice; the two zips are byte-identical) |
| Buchanan Hall | 246 jpg + csv (2 zips with the same file list) | 102 jpg + manifest + xml |
| Campbell | 69 heic + 69 jpg converted from them, csv, docx of azimuth values | — |
| Chem / PSNB | 376 jpg + csv | `CHEMPSNB.zip`: 376 jpg + manifest + xml |
| Elings Lot 10 | 151 jpg + 78 heic, csv | 229 jpg + manifest |
| Ellison Hall | 390 jpg + csv | 106 jpg + manifest + xml |
| ENGR II | 221 jpg/jpeg + xlsx | 221 jpg + manifest + xml |
| ESB | 217 jpg/jpeg + xlsx | — |
| Henley Hall | 2 parts: 521 jpeg + 48 heic, xlsx | — |
| HFH | 118 heic + 27 jpg, csv | — |
| Kavli | 155 jpg/jpeg + 69 heic, csv | — |
| Life Science Building | 2 parts: 220 + 307 jpg, csv | — |
| Marine Science | 208 jpg + csv, plus a full `demo_geo/` SfM output (h5 files, `sfm/`, `enu_origin.txt`) | — |
| MRL | 103 heic + 55 jpg, xlsx | — |
| North Hall | 2 parts: 401 + 28 jpg, csv | — |
| Ocean Science Education | 164 jpg + csv | — |
| Phelps Hall | 395 jpg + csv | — |
| Physical Science South | 151 jpeg, **no GNSS file** | — |

#### Other zips
- `Dataset-…-023.zip`: 328 Phelps photos (source of `Dataset/Phelps/`).
- `Old Stuff-…-001/002.zip`: older Elings Lot 10 and MRL + HFH captures (mostly HEIC), plus `Image Dataset Format_.docx`.
- `nixos-config-main.zip`: a NixOS desktop config, unrelated to the project.
- `Untitled folder-…zip`: empty.

#### Notes
- Not yet in `capstone_data/datasets/`: Bio Sci II, Bren, Broida, Campbell, Ellison, ENGR II, Henley, North Hall, Physical Science South.
- HEIC needs converting for Campbell, Elings, Henley, HFH, Kavli, MRL, and Old Stuff.
- Processed versions often have fewer photos than the raw export (e.g. Buchanan 102 vs 246, Ellison 106 vs 390), either a filtered subset or a different capture day.

### `capstone_data/` (287 GB)

#### `datasets/` (70 GB): prepared input scenes
Most scenes use a `testing_out/` folder. Some use `images/` instead.

| Scene | Size | Layout |
|---|---|---|
| `buchanan` | 962 MB | `testing_out/` |
| `chem_big_data` / `chem_big_data_test` | 5.1 GB / 98 MB | `testing_out/` |
| `drone_east` | 8.0 GB | `images/` |
| `drone_north_middle` / `_test` | 19 GB / 218 MB | `testing_out/` |
| `drone_northwest` / `_test` | 20 GB / 323 MB | `testing_out/` |
| `elings_big_data` | 3.4 GB | `testing_out/` |
| `elings_test` | 579 MB | `images/` |
| `esb` | 1.4 GB | `testing_out/` |
| `HFH_MRL_DJI` | 2.6 GB | `images/` + COLMAP `sparse/0` |
| `KavliEmlidfix` | 2.7 GB | `images/` |
| `lsb` | 3.9 GB | `testing_out/` |
| `MSB` | 814 MB | `testing_out/` |
| `OSE` / `OSE_test` | 632 MB / 113 MB | `testing_out/` |
| `Phelps` | 1.8 GB | `testing_out/` |

#### `capstone_results/outputs/` (150 GB): SfM reconstructions
Scenes: `kitp`, `kitp_big_data`, `chem_psnb`, `elings_lot10`, `HFH_MRL_DJI_sfm`, `demo_geo`, `wingtraNW01`.

Each run typically contains:
- `global-feats-netvlad.h5`, `features.h5`, `matches.h5`, `pairs-sfm.txt`: retrieval, features, and matches
- `sfm/`: sparse reconstruction
- `dense/` or `gsplat_dense_dataset/` (some scenes only)
- `enu_origin.txt`: ENU georeference origin (most scenes)
- `reconstruction_3d_pose_prior.html`: interactive viewer

#### `capstone_results/gsplats/` (12 GB): Gaussian Splatting runs
Scenes: `HFH`, `Kavli`, `lsb`, `MRL_dense`, `elings_lot10_2`, `kitp_more-gs`, `drone_east_dense_2`.

Each run typically has `cfg.yml`, `ckpts/`, `ply/`, `renders/`, `stats/`, `tb/` (TensorBoard), `videos/`, and (most scenes) `ppisp_reports/`. `drone_east_dense_2` holds only `point_cloud_24999.ply` and `point_cloud_199999.ply`.

#### `wingtra_post_processed/` (56 GB)
- `3D_Campus_Model_-_Lagoon_Flight_01/` (44 GB): `DATA/`, `FLIGHT RECORD/`, `IMAGES/`
- `Lagoon2_dense/` (12 GB): `IMAGES/` + `sparse/`

---

## `/data_8tb/Lizzy_web_data/` (237 GB)
Pix4D photogrammetry products from Wingtra flights. Northwest has PPK-corrected geotags (2–3 cm); the Lagoon geotag CSVs are onboard GNSS (5 m / 10 m), identical to the raw flight log. These are useful as survey-grade reference / ground truth. Owned by group `charvi`. Each subfolder has its own `CLAUDE.md` with format and CRS details.

### `Lagoon/` (140 GB)
Lagoon Flights 01 + 02 merged (2,357 raw images).
- `*_ortho.tiff` (5.6 GB), `*_dsm.tiff` (6.7 GB), `*_point_cloud.laz` (2.7 GB)
- `*_mesh/`: tiled OBJ+MTL+JPG mesh (54 tiles) and `*_offset.xyz`
- Merged geotag CSVs (WGS84 and NAD83)
- Folders: `Images RAW`, `Csv files`, `Json files`, `Sbf files`, `Ulog files`, `Base files`
- Each folder is also stored as a `.zip` alongside it (the Images RAW zip is 56 GB).

### `3D_Campus_Model__North_West/` (32 GB)
Northwest flight, 2026-03-26 (831 images).
- `images/` (20 GB)
- `*_ortho.tiff` (2.6 GB), `*_dsm.tiff` (2.9 GB), `*_point_cloud.laz` (870 MB)
- `*_mesh/` (51 OBJ tiles) + `*_mesh.zip`. Add the offset in `*_offset.xyz` to OBJ vertices to get world coordinates.
- PPK chain: drone `.sbf`, base-station Emlid Reach RINEX (`base-*/`), Trimble RTX `ppp_result_*.xml/.pdf`, `.geotaglog`, geotag CSVs
- Flight logs: `*.ulg`, `sess30_fmu.ulg`, `sess30_fts.ulg`
- `code/render_pcd.ipynb`. The folder is a git repo.

### Coordinate systems
- **WGS84** (EPSG:4326): lat/lon, altitude in meters
- **NAD83(2011) California zone 5** (EPSG:6424) + **NAVD88 height** (EPSG:6360): US survey feet

---

## `/data_8tb/capstone/` (6 GB)
- `ElingsLot10JPG/` (2.6 GB): ground-level photos of Elings Lot 10
- `prairie/images/` (3.4 GB, 328 images)

---

## Duplicate copies
Nothing has been deleted. These overlaps are known:

1. **Wingtra raw flights**: `/data_8tb/Wingtra_Pilot_Projects_Mar30/` and `/data_8tb/capstone_3d/Wingtra_Pilot_Projects_Mar30/` have identical flight lists, and every flight folder matches exactly in byte size (~107 GB). Not yet checksum-verified.
2. **Lagoon Flight 01** appears in:
   - both Wingtra copies above
   - `capstone_3d/capstone_data/wingtra_post_processed/3D_Campus_Model_-_Lagoon_Flight_01/` (same size, 44 GB). A partial diff against the raw copy found only macOS `._*` resource-fork files differing so far; the JPGs are not yet fully verified.
   - `Lizzy_web_data/Lagoon/` (merged with Flight 02, as both a zip and an extracted folder)
3. **Lizzy Lagoon zips** (~63 GB) sit next to their extracted folders.
4. **Northwest point cloud**: `/data_8tb/UCSB_3D Campus Model _ Northwest_point_cloud.laz` is byte-identical to the copy in `Lizzy_web_data/3D_Campus_Model__North_West/`.
5. **Emlid zips**: `Broida (with emlid data).zip` and `Broida (with emlid data) (1).zip` are byte-identical. The two `Buchanan Hall-…zip` files contain the same file list (zip headers differ).

---

## Ground images and camera GPS

Every building's ground photos, with their GPS, are now organized in
`/data_8tb/capstone_3d/wriva_format/Ground/` (see [WRIVA_FORMAT.md](WRIVA_FORMAT.md)).
Notes on the original sources:

- Phone photos carry phone GPS in EXIF (5–15 m) except: LSB (no phone GPS), Campbell's
  `jpg (conv from heic)` folder (EXIF stripped), the spring-2025 Kavli iPhone 12 photos, and
  `/data_8tb/capstone/ElingsLot10JPG` (stripped / Samsung).
- Emlid exports list RTK points (1–3 cm) but do not say which photo they belong to; photos are matched
  by capture time (within 5 s).
- The older pipeline's prepared datasets (`capstone_data/datasets/*/testing_out/`) have Emlid positions
  written into EXIF, with a per-photo log in `manifest_photo_emlid.xml`. In `lsb` and part of
  `elings_big_data` the written longitude has no W reference tag, so EXIF readers show +119.84 instead
  of −119.84. The `wriva_format` collections are built from the raw photos and are not affected.
- `/data_8tb/capstone/prairie/` is senseFly aerial imagery from Montana, not UCSB.
