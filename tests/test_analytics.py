"""Synthetic-data tests for survival analytics primitives.

These run without DuckDB and without the real licence corpus. They verify the math and the
edge cases on small fixtures, so the analytical layer can be trusted independent of the
specific signals it gets called with.
"""

from __future__ import annotations

from datetime import date

import polars as pl
import pytest

from signals.analytics import (
    cohort_survival_curve,
    median_lifespan_by_cohort,
    n_year_survival_rate,
)


def _make_signal(rows: list[dict]) -> pl.DataFrame:
    """Build a minimal signal DataFrame from a list of row dicts."""
    schema = {
        "business_id": pl.Utf8,
        "establishment_date": pl.Date,
        "closure_date": pl.Date,
    }
    return pl.DataFrame(rows, schema=schema)


# A 5-business cohort all opened 2010, with a clean closure pattern:
#   biz 1 closed 2011 (lifespan 1 year)
#   biz 2 closed 2012 (lifespan 2 years)
#   biz 3 closed 2015 (lifespan 5 years)
#   biz 4 closed 2020 (lifespan 10 years)
#   biz 5 still open
COHORT_2010 = _make_signal(
    [
        {"business_id": "1", "establishment_date": date(2010, 6, 1), "closure_date": date(2011, 12, 31)},
        {"business_id": "2", "establishment_date": date(2010, 6, 1), "closure_date": date(2012, 12, 31)},
        {"business_id": "3", "establishment_date": date(2010, 6, 1), "closure_date": date(2015, 12, 31)},
        {"business_id": "4", "establishment_date": date(2010, 6, 1), "closure_date": date(2020, 12, 31)},
        {"business_id": "5", "establishment_date": date(2010, 6, 1), "closure_date": None},
    ]
)


def test_cohort_survival_curve_known_pattern():
    curve = cohort_survival_curve(COHORT_2010, cohort_year=2010, max_years=12)
    pcts = dict(zip(curve["years_since_opening"].to_list(), curve["pct_surviving"].to_list()))

    # At year 0 everybody is alive.
    assert pcts[0] == pytest.approx(1.0)
    # At year 1 (end of 2011), biz 1 just closed -> 4 surviving / 5.
    assert pcts[1] == pytest.approx(0.8)
    # At year 2 (end of 2012), biz 2 also closed -> 3 surviving / 5.
    assert pcts[2] == pytest.approx(0.6)
    # At year 5 (end of 2015), biz 3 just closed -> 2 surviving / 5.
    assert pcts[5] == pytest.approx(0.4)
    # At year 10 (end of 2020), biz 4 just closed -> 1 surviving / 5.
    assert pcts[10] == pytest.approx(0.2)
    # At year 12, biz 5 (still open) is the only one left -> 0.2.
    assert pcts[12] == pytest.approx(0.2)


def test_cohort_survival_curve_empty_cohort():
    curve = cohort_survival_curve(COHORT_2010, cohort_year=1999)
    # No businesses opened in 1999: n_at_risk is 0, all pcts are 0.
    assert curve["n_at_risk"].unique().to_list() == [0]
    assert all(p == 0.0 for p in curve["pct_surviving"].to_list())


def test_median_lifespan_by_cohort_basic():
    out = median_lifespan_by_cohort(COHORT_2010)
    row = out.filter(pl.col("cohort_year") == 2010).to_dicts()[0]
    assert row["n_total"] == 5
    assert row["n_closed"] == 4
    # Closed lifespans: ~1.58, ~2.58, ~5.59, ~10.59 years (closure 12/31, opened 6/1).
    # Median of an even-length sample is mean of middle two: (~2.58 + ~5.59) / 2 = ~4.08.
    assert 3.5 < row["median_lifespan_years"] < 4.5


def test_median_lifespan_excludes_open_businesses():
    # Single-row cohort with no closures -> median is null.
    df = _make_signal(
        [
            {"business_id": "1", "establishment_date": date(2018, 1, 1), "closure_date": None},
        ]
    )
    out = median_lifespan_by_cohort(df)
    row = out.to_dicts()[0]
    assert row["n_total"] == 1
    assert row["n_closed"] == 0
    assert row["median_lifespan_years"] is None


def test_n_year_survival_rate_drops_recent_cohorts():
    # Today is fixed at 2026-05-06. With n_years=5, max observable cohort is 2021.
    # COHORT_2010 (opened 2010) IS observable; a hypothetical 2024 cohort would be dropped.
    df = pl.concat([
        COHORT_2010,
        _make_signal([
            {"business_id": "x", "establishment_date": date(2024, 1, 1), "closure_date": None},
        ]),
    ])
    out = n_year_survival_rate(df, n_years=5, today=date(2026, 5, 6))
    cohort_years = out["cohort_year"].to_list()
    assert 2010 in cohort_years
    assert 2024 not in cohort_years
    row_2010 = out.filter(pl.col("cohort_year") == 2010).to_dicts()[0]
    # 5-year survival for the 2010 cohort: at end of 2015, biz 1, 2, 3 have closed -> 2/5.
    assert row_2010["n_surviving_at_n"] == 2
    assert row_2010["pct_surviving_at_n"] == pytest.approx(0.4)


def test_validate_raises_on_bad_input():
    bad = pl.DataFrame({"business_id": ["1"]})
    with pytest.raises(ValueError, match="missing required columns"):
        cohort_survival_curve(bad, cohort_year=2010)
