"""Cross-signal analytical primitives.

Each function takes a signal DataFrame (the standard-schema output of any signals/*.py
get_signal call) and returns a polars DataFrame. They are pure: no DuckDB, no I/O.

Conventions:
    - "cohort year" = year of establishment_date.
    - "still operating at year Y" = closure_date IS NULL or closure_date > Y-end.
    - "lifespan" = closure_date - establishment_date, in years (only defined for closed
      businesses).

Right-censoring caveat applies to all three functions: businesses opened recently have not
had time to close yet, so their apparent survival is artificially high. The
n_year_survival_rate and cohort_survival_curve functions silently include right-censored
data; it's the caller's job to exclude cohorts younger than the survival window. The
default in the survival notebook is to drop cohorts younger than 3 years for general
cross-signal comparison.
"""

from __future__ import annotations

from datetime import date, timedelta

import polars as pl

REQUIRED_COLS = ("business_id", "establishment_date", "closure_date")


def _validate(df: pl.DataFrame) -> None:
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"signal DataFrame missing required columns: {missing}")


def cohort_survival_curve(
    df: pl.DataFrame,
    cohort_year: int,
    max_years: int = 20,
) -> pl.DataFrame:
    """For businesses established in `cohort_year`, return survival % at each year offset.

    Output columns:
        years_since_opening: int (0..max_years)
        n_at_risk: int (cohort size; constant across rows)
        n_surviving: int
        pct_surviving: float (0..1)
    """
    _validate(df)
    cohort = df.filter(pl.col("establishment_date").dt.year() == cohort_year)
    n_at_risk = cohort.height
    rows = []
    for offset in range(max_years + 1):
        cutoff = date(cohort_year + offset, 12, 31)
        if n_at_risk == 0:
            n_surviving = 0
            pct = 0.0
        else:
            still_open = cohort.filter(
                pl.col("closure_date").is_null() | (pl.col("closure_date") > cutoff)
            )
            n_surviving = still_open.height
            pct = n_surviving / n_at_risk
        rows.append(
            {
                "years_since_opening": offset,
                "n_at_risk": n_at_risk,
                "n_surviving": n_surviving,
                "pct_surviving": pct,
            }
        )
    return pl.DataFrame(rows)


def median_lifespan_by_cohort(df: pl.DataFrame) -> pl.DataFrame:
    """For each cohort year, the median lifespan (in years) of businesses that have closed.

    Output columns:
        cohort_year: int
        n_closed: int — businesses in that cohort with a closure_date set
        n_total: int — total cohort size (closed + still-open)
        median_lifespan_years: float — null when n_closed == 0

    Methodology note: this excludes still-open businesses entirely. That biases the median
    downward for recent cohorts (their long-lived members haven't shown up as "open then
    closed" yet) and upward for old cohorts (their longest-lived members may not yet have
    closed). Read with care.
    """
    _validate(df)
    work = df.with_columns(
        pl.col("establishment_date").dt.year().alias("cohort_year"),
    )
    grouped = work.group_by("cohort_year").agg(
        pl.col("business_id").len().alias("n_total"),
        pl.col("closure_date").is_not_null().sum().alias("n_closed"),
        ((pl.col("closure_date") - pl.col("establishment_date")).dt.total_days() / 365.25)
        .median()
        .alias("median_lifespan_years"),
    )
    return grouped.sort("cohort_year")


def n_year_survival_rate(
    df: pl.DataFrame,
    n_years: int,
    today: date | None = None,
) -> pl.DataFrame:
    """For each cohort year, the % of businesses still operating `n_years` after opening.

    Cohorts where `cohort_year + n_years` is in the future are dropped, since we can't
    observe that survival window yet. Use `today` to override the cutoff (defaults to
    today's date).

    Output columns:
        cohort_year: int
        n_total: int
        n_surviving_at_n: int
        pct_surviving_at_n: float
    """
    _validate(df)
    if today is None:
        today = date.today()
    max_observable_cohort = today.year - n_years

    work = df.with_columns(
        pl.col("establishment_date").dt.year().alias("cohort_year"),
    ).filter(pl.col("cohort_year") <= max_observable_cohort)

    # For each row, "still operating at cohort_year + n_years end" means:
    # closure_date is NULL OR closure_date > date(cohort_year + n_years, 12, 31).
    # We compute the cutoff per-row.
    cutoff_expr = (
        pl.date(pl.col("cohort_year") + n_years, 12, 31)
    )
    work = work.with_columns(
        (pl.col("closure_date").is_null() | (pl.col("closure_date") > cutoff_expr)).alias(
            "_surviving"
        ),
    )
    return (
        work.group_by("cohort_year")
        .agg(
            pl.col("business_id").len().alias("n_total"),
            pl.col("_surviving").sum().alias("n_surviving_at_n"),
        )
        .with_columns(
            (pl.col("n_surviving_at_n") / pl.col("n_total")).alias("pct_surviving_at_n")
        )
        .sort("cohort_year")
    )
