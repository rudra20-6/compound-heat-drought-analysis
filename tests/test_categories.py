import numpy as np

from chd.categories import (
    classify_months, CATEGORY_NORMAL, CATEGORY_HOT_ONLY, CATEGORY_DRY_ONLY, CATEGORY_COMPOUND,
)


def test_classify_months_all_four_categories():
    tmax_z = np.array([0.0, 1.5, 0.0, 1.5, np.nan])
    spei = np.array([0.0, 0.0, -1.5, -1.5, -1.5])
    cats = classify_months(tmax_z, spei)
    assert list(cats) == [CATEGORY_NORMAL, CATEGORY_HOT_ONLY, CATEGORY_DRY_ONLY,
                          CATEGORY_COMPOUND, "nan"]


def test_classify_months_threshold_boundary():
    # exactly at the threshold counts as triggered (>=, <=)
    tmax_z = np.array([1.0, 0.99, 0.0, 0.0])
    spei = np.array([0.0, 0.0, -1.0, -0.99])
    cats = classify_months(tmax_z, spei, hot_z=1.0, dry_threshold=-1.0)
    assert list(cats) == [CATEGORY_HOT_ONLY, CATEGORY_NORMAL, CATEGORY_DRY_ONLY, CATEGORY_NORMAL]


def test_classify_months_keeps_2d_shape():
    tmax_z = np.array([[0.0, 2.0], [2.0, 0.0]])
    spei = np.array([[-2.0, -2.0], [0.0, 0.0]])
    cats = classify_months(tmax_z, spei)
    assert cats.shape == (2, 2)
    assert cats[0, 1] == CATEGORY_COMPOUND
