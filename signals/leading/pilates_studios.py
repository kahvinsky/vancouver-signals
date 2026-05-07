"""Pilates studios: a hypothesized leading indicator of gentrification.

Definition:
    canonical_category = 'fitness_studio'
    AND (business_name ILIKE '%pilates%' OR trade_name ILIKE '%pilates%')

Rationale:
    Pilates has no dedicated city category. It lives across the same buckets as yoga
    (Fitness Centre, Sport and Fitness Instruction, Studio *Historic*, the Fitness
    Instruction subset of Instruction *Historic*). The shared `fitness_studio` canonical
    absorbs all of them; the name filter isolates pilates specifically.

Caveats:
    - 'pilates' in business_name or trade_name catches dedicated studios but misses
      generalist fitness studios that offer pilates classes.
    - Catches a small number of physical-therapist practices that include 'Pilates' in
      their name (e.g., 'Reformer Pilates Physiotherapy'). Acceptable; they're typically
      pilates-forward in identity.
"""

from __future__ import annotations

import duckdb
import polars as pl

from signals._common import aggregate_signal

SIGNAL_NAME = "pilates_studios"
SIGNAL_CLASS = "leading"


def get_signal(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    where = """
        canonical_category = 'fitness_studio'
        AND (business_name ILIKE '%pilates%' OR trade_name ILIKE '%pilates%')
    """
    return aggregate_signal(con, where, SIGNAL_NAME, SIGNAL_CLASS)
