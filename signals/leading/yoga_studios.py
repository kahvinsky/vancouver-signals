"""Yoga studios: a hypothesized leading indicator of gentrification.

Definition:
    canonical_category = 'fitness_studio'
    AND (business_name ILIKE '%yoga%' OR trade_name ILIKE '%yoga%')

Rationale: Yoga has no dedicated city category in either the pre-2024 or post-2024 vocabulary.
It lives across Fitness Centre, Sport and Fitness Instruction, Studio *Historic*, and the
Fitness Instruction subset of Instruction *Historic*. The fitness_studio canonical absorbs
all those categories; the name filter then isolates yoga specifically.

Caveats:
    - "yoga" in business_name catches studios but misses places that teach yoga without it
      in the name (e.g., generalist fitness studios that offer yoga classes).
    - It will catch some non-studio businesses with "yoga" in their name (e.g., a yoga-themed
      retailer). For Weekend 1 the canonical_category filter limits this contamination.
"""

from __future__ import annotations

import duckdb
import polars as pl

from signals._common import aggregate_signal

SIGNAL_NAME = "yoga_studios"
SIGNAL_CLASS = "leading"


def get_signal(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    where = """
        canonical_category = 'fitness_studio'
        AND (business_name ILIKE '%yoga%' OR trade_name ILIKE '%yoga%')
    """
    return aggregate_signal(con, where, SIGNAL_NAME, SIGNAL_CLASS)
