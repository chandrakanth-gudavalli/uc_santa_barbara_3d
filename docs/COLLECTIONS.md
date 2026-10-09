# Collection Inventory

Built by `tools/build_wriva.py` into `/data_8tb/capstone_3d/wriva_format/` (format: [WRIVA_FORMAT.md](WRIVA_FORMAT.md)),
in three folders: `Ground/` (the Ground table below), `drone/` (Wingtra) and `DJI/`.
Machine-readable version with more columns (per-source counts, median uncertainty, cameras, centre
lat/lon): [collections_summary.csv](collections_summary.csv), also at
`/data_8tb/capstone_3d/wriva_format/collections_summary.csv`. Regenerate both with
`tools/summarize_collections.py`.

Every collection was checked for matching image / metadata / manifest counts, valid JSON,
`site.json` and `gps_map.html`.

- **Precise** = centimetre-level: Emlid RTK (ground) or Wingtra PPK (airborne).
- **Noisy** = metre-level: phone GPS, onboard Wingtra GNSS, DJI GPS.

| Group | Collections | Images | With GPS | No GPS | Precise | Noisy | Size (GB) |
|---|---|---|---|---|---|---|---|
| Ground (phone) | 23 | 6926 | 6026 | 900 | 4631 | 1395 | 34.9 |
| Wingtra (airborne) | 9 | 4490 | 4490 | 0 | 831 | 3659 | 112.9 |
| DJI video keyframes (airborne) | 32 | 5517 | 5514 | 3 | 0 | 5514 | 8.0 |
| **Total** | 64 | 16933 | 16030 | 903 | 5462 | 10568 | 155.8 |

## Ground (`Ground/`)

| Collection | Images | With GPS | No GPS | Precise | Noisy | GPS sources | Dates | Size (GB) |
|---|---|---|---|---|---|---|---|---|
| `ucsb_bio_sci_2_ground` | 263 | 263 | 0 | 126 | 137 | Emlid RTK 126, Phone GPS 137 | 2026-02-08 – 2026-02-21 | 1.03 |
| `ucsb_bren_ground` | 305 | 305 | 0 | 180 | 125 | Emlid RTK 180, Phone GPS 125 | 2026-01-23 – 2026-02-08 | 1.31 |
| `ucsb_broida_ground` | 438 | 438 | 0 | 379 | 59 | Emlid RTK 379, Phone GPS 59 | 2026-02-10 – 2026-02-22 | 2.42 |
| `ucsb_buchanan_ground` | 246 | 246 | 0 | 236 | 10 | Emlid RTK 236, Phone GPS 10 | 2026-02-20 – 2026-02-28 | 1.03 |
| `ucsb_campbell_ground` | 69 | 69 | 0 | 69 | 0 | Emlid RTK 69 | 2026-02-06 | 0.41 |
| `ucsb_chem_psnb_ground` | 376 | 376 | 0 | 303 | 73 | Emlid RTK 303, Phone GPS 73 | 2026-01-30 – 2026-02-06 | 1.6 |
| `ucsb_elings_lot10_ground` | 229 | 229 | 0 | 226 | 3 | Emlid RTK 226, Phone GPS 3 | 2026-01-13 – 2026-01-15 | 0.88 |
| `ucsb_elings_lot10_ground_2025` | 555 | 399 | 156 | 0 | 399 | Phone GPS 399 | 2025-10-28 | 2.71 |
| `ucsb_ellison_ground` | 390 | 390 | 0 | 387 | 3 | Emlid RTK 387, Phone GPS 3 | 2026-02-21 – 2026-02-24 | 1.63 |
| `ucsb_engr2_ground` | 221 | 221 | 0 | 221 | 0 | Emlid RTK 221 | 2026-01-19 – 2026-01-29 | 1.16 |
| `ucsb_esb_ground` | 217 | 217 | 0 | 215 | 2 | Emlid RTK 215, Phone GPS 2 | 2026-01-20 – 2026-01-27 | 1.47 |
| `ucsb_henley_ground` | 566 | 566 | 0 | 404 | 162 | Emlid RTK 404, Phone GPS 162 | 2026-03-01 | 3.71 |
| `ucsb_hfh_ground` | 145 | 145 | 0 | 117 | 28 | Emlid RTK 117, Phone GPS 28 | 2026-01-19 – 2026-01-22 | 0.58 |
| `ucsb_kavli_ground` | 194 | 194 | 0 | 189 | 5 | Emlid RTK 189, Phone GPS 5 | 2026-01-13 – 2026-01-19 | 1.22 |
| `ucsb_kavli_ground_2025` | 428 | 0 | 428 | 0 | 0 |  | 2025-03-31 – 2025-04-29 | 1.76 |
| `ucsb_lsb_ground` | 527 | 419 | 108 | 419 | 0 | Emlid RTK 419 | 2026-02-27 | 4.02 |
| `ucsb_marine_science_ground` | 208 | 208 | 0 | 179 | 29 | Emlid RTK 179, Phone GPS 29 | 2026-02-01 – 2026-02-08 | 0.86 |
| `ucsb_mrl_ground` | 158 | 158 | 0 | 115 | 43 | Emlid RTK 115, Phone GPS 43 | 2026-01-19 – 2026-01-22 | 0.54 |
| `ucsb_mrl_hfh_ground_2025` | 252 | 44 | 208 | 0 | 44 | Phone GPS 44 | 2025-10-27 | 0.89 |
| `ucsb_north_hall_ground` | 429 | 429 | 0 | 428 | 1 | Emlid RTK 428, Phone GPS 1 | 2026-02-28 | 2.22 |
| `ucsb_ose_ground` | 164 | 164 | 0 | 104 | 60 | Emlid RTK 104, Phone GPS 60 | 2026-02-01 – 2026-02-13 | 0.67 |
| `ucsb_phelps_ground` | 395 | 395 | 0 | 334 | 61 | Emlid RTK 334, Phone GPS 61 | 2026-02-20 | 1.85 |
| `ucsb_physical_science_south_ground` | 151 | 151 | 0 | 0 | 151 | Phone GPS 151 | 2026-02-08 | 0.96 |

## Wingtra (`drone/`)

| Collection | Images | With GPS | No GPS | Precise | Noisy | GPS sources | Dates | Size (GB) |
|---|---|---|---|---|---|---|---|---|
| `ucsb_wingtra_east_f01` | 344 | 344 | 0 | 0 | 344 | Wingtra GNSS 344 | 2026-03-27 | 8.52 |
| `ucsb_wingtra_lagoon_f01` | 1847 | 1847 | 0 | 0 | 1847 | Wingtra GNSS 1847 | 2026-03-27 | 46.82 |
| `ucsb_wingtra_lagoon_f02` | 510 | 510 | 0 | 0 | 510 | Wingtra GNSS 510 | 2026-03-27 | 12.56 |
| `ucsb_wingtra_north_middle_f01` | 786 | 786 | 0 | 0 | 786 | Wingtra GNSS 786 | 2026-03-26 | 19.55 |
| `ucsb_wingtra_northeast_f01` | 81 | 81 | 0 | 0 | 81 | Wingtra GNSS 81 | 2026-03-26 | 1.8 |
| `ucsb_wingtra_northeast_f02` | 57 | 57 | 0 | 0 | 57 | Wingtra GNSS 57 | 2026-03-26 | 1.4 |
| `ucsb_wingtra_northwest_f01` | 831 | 831 | 0 | 831 | 0 | Wingtra PPK 831 | 2026-03-26 | 21.17 |
| `ucsb_wingtra_test_flight1_f01` | 20 | 20 | 0 | 0 | 20 | Wingtra GNSS 20 | 2026-01-09 | 0.63 |
| `ucsb_wingtra_test_flight1_f02` | 14 | 14 | 0 | 0 | 14 | Wingtra GNSS 14 | 2026-01-09 | 0.42 |

Only Northwest Flight 01 has PPK geotags. The Lagoon geotags in `Lizzy_web_data` are onboard GNSS
(5 m / 10 m accuracy, identical to the raw flight log), so Lagoon is counted as noisy.
`ucsb_wingtra_test_flight1_f01` / `_f02` were flown about 30 km east of campus (longitude −119.53,
near Carpinteria), not over UCSB.

## DJI video keyframes (`DJI/`)

| Collection | Images | With GPS | No GPS | Precise | Noisy | GPS sources | Dates | Size (GB) |
|---|---|---|---|---|---|---|---|---|
| `ucsb_dji_0025` | 12 | 12 | 0 | 0 | 12 | DJI GPS 12 | 2026-04-09 | 0.02 |
| `ucsb_dji_0026` | 291 | 291 | 0 | 0 | 291 | DJI GPS 291 | 2026-04-09 | 0.4 |
| `ucsb_dji_0027` | 23 | 23 | 0 | 0 | 23 | DJI GPS 23 | 2026-04-09 | 0.05 |
| `ucsb_dji_0028` | 160 | 160 | 0 | 0 | 160 | DJI GPS 160 | 2026-04-09 | 0.2 |
| `ucsb_dji_0029` | 132 | 132 | 0 | 0 | 132 | DJI GPS 132 | 2026-04-09 | 0.15 |
| `ucsb_dji_0030` | 124 | 124 | 0 | 0 | 124 | DJI GPS 124 | 2026-04-09 | 0.13 |
| `ucsb_dji_0031` | 219 | 219 | 0 | 0 | 219 | DJI GPS 219 | 2026-04-09 | 0.27 |
| `ucsb_dji_0032` | 11 | 11 | 0 | 0 | 11 | DJI GPS 11 | 2026-04-09 | 0.02 |
| `ucsb_dji_0033` | 291 | 291 | 0 | 0 | 291 | DJI GPS 291 | 2026-04-09 | 0.37 |
| `ucsb_dji_0034` | 126 | 126 | 0 | 0 | 126 | DJI GPS 126 | 2026-04-09 | 0.15 |
| `ucsb_dji_0035` | 111 | 111 | 0 | 0 | 111 | DJI GPS 111 | 2026-04-09 | 0.16 |
| `ucsb_dji_0036` | 291 | 291 | 0 | 0 | 291 | DJI GPS 291 | 2026-04-09 | 0.44 |
| `ucsb_dji_0037` | 215 | 215 | 0 | 0 | 215 | DJI GPS 215 | 2026-04-09 | 0.35 |
| `ucsb_dji_0038` | 92 | 92 | 0 | 0 | 92 | DJI GPS 92 | 2026-04-09 | 0.16 |
| `ucsb_dji_0039` | 291 | 291 | 0 | 0 | 291 | DJI GPS 291 | 2026-04-09 | 0.38 |
| `ucsb_dji_0040` | 291 | 291 | 0 | 0 | 291 | DJI GPS 291 | 2026-04-09 | 0.53 |
| `ucsb_dji_0041` | 131 | 131 | 0 | 0 | 131 | DJI GPS 131 | 2026-04-09 | 0.2 |
| `ucsb_dji_0042` | 117 | 117 | 0 | 0 | 117 | DJI GPS 117 | 2026-04-09 | 0.21 |
| `ucsb_dji_0043` | 291 | 291 | 0 | 0 | 291 | DJI GPS 291 | 2026-04-09 | 0.44 |
| `ucsb_dji_0044` | 291 | 291 | 0 | 0 | 291 | DJI GPS 291 | 2026-04-09 | 0.39 |
| `ucsb_dji_0045` | 113 | 113 | 0 | 0 | 113 | DJI GPS 113 | 2026-04-09 | 0.17 |
| `ucsb_dji_0046` | 146 | 146 | 0 | 0 | 146 | DJI GPS 146 | 2026-04-09 | 0.19 |
| `ucsb_dji_0047` | 216 | 216 | 0 | 0 | 216 | DJI GPS 216 | 2026-04-09 | 0.28 |
| `ucsb_dji_0048` | 243 | 243 | 0 | 0 | 243 | DJI GPS 243 | 2026-04-09 | 0.33 |
| `ucsb_dji_0049` | 291 | 291 | 0 | 0 | 291 | DJI GPS 291 | 2026-04-09 | 0.36 |
| `ucsb_dji_0050` | 129 | 129 | 0 | 0 | 129 | DJI GPS 129 | 2026-04-09 | 0.17 |
| `ucsb_dji_0051` | 123 | 123 | 0 | 0 | 123 | DJI GPS 123 | 2026-04-09 | 0.14 |
| `ucsb_dji_0052` | 1 | 1 | 0 | 0 | 1 | DJI GPS 1 | 2026-04-09 | 0.0 |
| `ucsb_dji_0053` | 138 | 135 | 3 | 0 | 135 | DJI GPS 135 | 2026-04-09 | 0.2 |
| `ucsb_dji_0054` | 236 | 236 | 0 | 0 | 236 | DJI GPS 236 | 2026-04-09 | 0.44 |
| `ucsb_dji_0055` | 291 | 291 | 0 | 0 | 291 | DJI GPS 291 | 2026-04-09 | 0.57 |
| `ucsb_dji_0056` | 80 | 80 | 0 | 0 | 80 | DJI GPS 80 | 2026-04-09 | 0.15 |

`ucsb_dji_0052` has a single keyframe.

## Gaps to know about

- `ucsb_lsb_ground`: 108 photos have no position (phone GPS was off and no Emlid point within 5 s).
- `ucsb_kavli_ground_2025`: no GPS at all (iPhone 12 photos without location).
- `ucsb_mrl_hfh_ground_2025`, `ucsb_elings_lot10_ground_2025`: no Emlid data; phone GPS only where recorded.
- `ucsb_physical_science_south_ground`: no Emlid file; phone GPS only.
- Every Wingtra flight except Northwest has only onboard GNSS (~5 m). PPK would need each flight's
  `.sbf` + base station data processed in WingtraHub.
