# Data card — Diplom_SF geo datasets

## Overview

Three regional well datasets used for SkillFactory oil-well location diploma.

| File | Region key | Rows | Columns |
|------|------------|------|---------|
| `geo_data_0.csv` | `region_0` | 100_000 | id, f0, f1, f2, product |
| `geo_data_1.csv` | `region_1` | 100_000 | id, f0, f1, f2, product |
| `geo_data_2.csv` | `region_2` | 100_000 | id, f0, f1, f2, product |

## Fields

| Column | Type | Description |
|--------|------|-------------|
| id | string | Well identifier (not unique in all files) |
| f0, f1, f2 | float | Synthetic geologic features |
| product | float | Oil reserves, thousand barrels (target) |

## Units / business constants (default)

- Budget: 10e9 RUB for 200 wells → 50e6 RUB / well
- Revenue: 450e3 RUB per thousand barrels
- Breakeven ≈ 111.11 thousand barrels / well

## Known DQ issues

- `region_1` (`geo_data_1`): ~12 unique `product` values, ~8.2% zeros, corr(f2, product) ≈ 0.999 → **critical** (likely synthetic/leaked target).
- All regions: duplicate `id` values exist without full-row duplicates.

## Duplicate id policy

Configured via `--dup-id-policy`:

- `keep_all` (default, SkillFactory-compatible)
- `drop_keep_first` / `drop_keep_last`

Audit: `python -m oilwells dq`

## Provenance

Source: SkillFactory course materials («ГлавРосГосНефть» synthetic task). Not production field data.
