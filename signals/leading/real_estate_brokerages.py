"""Real estate brokerages: hypothesized leading (or possibly coincident) signal.

Definition:
    canonical_category = 'real_estate'

Rationale:
    Maps:
        - 'Real Estate Dealer *Historic*' (old-vocab, 9.7k rows)
        - 'Real Estate Services' (new-vocab, 3.3k rows)
        - 'Office *Historic*' subcategory 'Real Estate Development/Investment' (4.5k rows)

    The hypothesis: real estate brokerage density rises when a neighborhood is being
    actively transacted upon (high turnover, new listings, capital flowing in). New
    brokerages opening in a neighborhood plausibly leads broader gentrification by 12-36
    months as the brokerages chase emerging markets. Existing brokerages closing or moving
    out is a coincident indicator that the volume opportunity has saturated or shifted.

Address-of-work caveat:
    Real estate brokerages have decent geom coverage (~74%, better than most categories
    in this batch). But brokerages serve listings across the entire city (and often the
    region) regardless of their own office location. Neighborhood density of brokerage
    *offices* should be read as "where brokerages prefer to plant flags" — typically
    high-foot-traffic commercial strips — not "where they're transacting."

Intentional exclusion:
    'Brokerage Services' (new-vocab, 822 rows) is intentionally not mapped. The category
    name is generic and includes insurance brokerages, freight brokerages, and other
    non-real-estate intermediaries. Catching it would pollute the signal.
"""

from __future__ import annotations

import duckdb
import polars as pl

from signals._common import aggregate_signal

SIGNAL_NAME = "real_estate_brokerages"
SIGNAL_CLASS = "leading"


def get_signal(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    where = "canonical_category = 'real_estate'"
    return aggregate_signal(con, where, SIGNAL_NAME, SIGNAL_CLASS)
