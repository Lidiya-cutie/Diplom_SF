from __future__ import annotations

from pathlib import Path

import pandas as pd

from oilwells.config import REGION_FILES, DuplicateIdPolicy


REQUIRED_COLUMNS = ("id", "f0", "f1", "f2", "product")


def load_region(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    missing = [c for c in REQUIRED_COLUMNS if c not in df.columns]
    if missing:
        raise ValueError(f"{path}: missing columns {missing}")
    return df


def load_all_regions(data_dir: Path) -> dict[str, pd.DataFrame]:
    out: dict[str, pd.DataFrame] = {}
    for name, filename in REGION_FILES.items():
        out[name] = load_region(data_dir / filename)
    return out


def apply_duplicate_id_policy(df: pd.DataFrame, policy: DuplicateIdPolicy) -> tuple[pd.DataFrame, dict]:
    n_before = len(df)
    n_dup_id = int(df["id"].duplicated().sum())
    if policy == DuplicateIdPolicy.KEEP_ALL:
        cleaned = df.copy()
    elif policy == DuplicateIdPolicy.DROP_KEEP_FIRST:
        cleaned = df.drop_duplicates(subset=["id"], keep="first").copy()
    elif policy == DuplicateIdPolicy.DROP_KEEP_LAST:
        cleaned = df.drop_duplicates(subset=["id"], keep="last").copy()
    else:
        raise ValueError(policy)
    meta = {
        "policy": policy.value,
        "rows_before": n_before,
        "rows_after": len(cleaned),
        "rows_removed": n_before - len(cleaned),
        "duplicate_id_count": n_dup_id,
    }
    return cleaned, meta
