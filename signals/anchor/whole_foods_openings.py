"""Whole Foods openings: an anchor signal.

Definition:
    business_name ILIKE '%whole foods market%' OR trade_name ILIKE '%whole foods market%'

The 'market' suffix is what distinguishes the grocery chain from unrelated businesses
that happen to use 'whole foods' in their name (e.g., 'Forte Whole Foods Inc', a
supplement company). The chain registers under multiple corporate entities ('Whole
Foods Market - Wo Inc', 'Whole Foods Market Canada Inc') but all carry the 'Market'
trademark.

No category filter; the chain's licence categories drift across years (Grocery Store,
Retail Dealer - Food, Limited Service Food Establishment depending on the corporate
entity and year). Filtering by name is more reliable than chasing category drift.

Anchor signals are rare by construction. Expect 3-4 distinct locations in Vancouver
(Cambie/8th, Robson, Kitsilano/4th); West Vancouver's Park Royal store is outside the
city limits and won't appear.
"""

from __future__ import annotations

import duckdb
import polars as pl

from signals._common import aggregate_signal

SIGNAL_NAME = "whole_foods_openings"
SIGNAL_CLASS = "anchor"


def get_signal(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    where = (
        "business_name ILIKE '%whole foods market%' "
        "OR trade_name ILIKE '%whole foods market%'"
    )
    return aggregate_signal(con, where, SIGNAL_NAME, SIGNAL_CLASS)
