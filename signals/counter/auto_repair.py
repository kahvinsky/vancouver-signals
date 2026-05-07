"""Auto repair shops: a hypothesized counter-signal (incumbent industry displaced by gentrification).

Definition:
    canonical_category = 'auto_repair'

This canonical maps from:
    - Old vocabulary: 'Auto Repairs *Historic*' (pre-2024)
    - New vocabulary: 'Vehicle Repair Detailing and Washing Services' (2024+)

Caveats:
    - The new-vocab category is broader than the old: it lumps repair, detailing, and washing.
      If we want pure repair (excluding car washes and detailers), we'd need a name-based
      refinement. For Weekend 1 we accept the broader inclusion and revisit when the data
      shows whether washes/detailers behave differently from repair shops.
    - No name filter applied; the category is clean enough on the old-vocab side that
      adding one would mostly create noise.
"""

from __future__ import annotations

import duckdb
import polars as pl

from signals._common import aggregate_signal

SIGNAL_NAME = "auto_repair"
SIGNAL_CLASS = "counter"


def get_signal(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    where = "canonical_category = 'auto_repair'"
    return aggregate_signal(con, where, SIGNAL_NAME, SIGNAL_CLASS)
