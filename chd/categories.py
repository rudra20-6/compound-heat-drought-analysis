"""
Stress-category classification: every cell-month goes into one of four boxes
(Normal / Hot-only / Dry-only / Compound) from its temperature anomaly and
its drought index.
"""
from __future__ import annotations

import numpy as np

from .config import THRESH

CATEGORY_NORMAL = "normal"
CATEGORY_HOT_ONLY = "hot_only"
CATEGORY_DRY_ONLY = "dry_only"
CATEGORY_COMPOUND = "compound"

CATEGORIES = (CATEGORY_NORMAL, CATEGORY_HOT_ONLY, CATEGORY_DRY_ONLY, CATEGORY_COMPOUND)


def classify_months(tmax_z: np.ndarray, dry_index: np.ndarray,
                    hot_z: float = THRESH.hot_z,
                    dry_threshold: float = THRESH.dry_spei) -> np.ndarray:
    """
    Classify each cell-month (element-wise) into one of the 4 stress categories.

        hot := tmax_z    >= hot_z          (default 1)
        dry := dry_index <= dry_threshold  (default -1; SPEI-3 or SPI-3)

    Returns an object array of strings; missing input -> "nan".
    """
    tmax_z = np.asarray(tmax_z, dtype=float)
    dry_index = np.asarray(dry_index, dtype=float)
    out = np.full(tmax_z.shape, "nan", dtype=object)

    valid = ~np.isnan(tmax_z) & ~np.isnan(dry_index)
    hot = tmax_z >= hot_z
    dry = dry_index <= dry_threshold

    out[valid & ~hot & ~dry] = CATEGORY_NORMAL
    out[valid & hot & ~dry] = CATEGORY_HOT_ONLY
    out[valid & ~hot & dry] = CATEGORY_DRY_ONLY
    out[valid & hot & dry] = CATEGORY_COMPOUND
    return out
