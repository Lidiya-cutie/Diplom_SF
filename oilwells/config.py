from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any


class DuplicateIdPolicy(str, Enum):
    """How to treat duplicate well ids before modeling."""

    KEEP_ALL = "keep_all"  # SF default: keep all rows even if id repeats
    DROP_KEEP_FIRST = "drop_keep_first"
    DROP_KEEP_LAST = "drop_keep_last"


@dataclass(frozen=True)
class BusinessConfig:
    budget: float = 10_000_000_000
    wells_target: int = 200
    wells_pool: int = 500
    product_revenue: float = 450_000
    loss_threshold: float = 0.025
    n_bootstrap: int = 1000
    test_size: float = 0.25
    random_state: int = 12345
    duplicate_id_policy: DuplicateIdPolicy = DuplicateIdPolicy.KEEP_ALL

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["duplicate_id_policy"] = self.duplicate_id_policy.value
        return d


REGION_FILES = {
    "region_0": "geo_data_0.csv",
    "region_1": "geo_data_1.csv",
    "region_2": "geo_data_2.csv",
}
