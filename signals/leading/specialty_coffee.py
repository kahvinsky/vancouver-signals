"""Specialty coffee shops: a hypothesized leading indicator of gentrification.

Definition:
    canonical_category = 'cafe'
    AND (business_name OR trade_name) ILIKE any of: coffee, espresso, roaster, cafe, cafe
    AND name does NOT match any chain in EXCLUDE_CHAINS
    AND name does NOT contain bubble-tea / boba / tea-house tokens

Rationale:
    The city has no clean "coffee shop" category. The closest classification is "Ltd Service
    Food Establishment *Historic*" / "Limited Service Food Establishment" (the cafe canonical),
    which lumps coffee shops with donut shops, bubble tea, ice cream, sandwich counters, and
    quick-serve everything. We narrow with a name filter for coffee-specific tokens, then
    subtract obvious chains and obvious non-coffee.

Inclusion list (any one of these substrings in business_name OR trade_name):
    - coffee   — catches "X Coffee Co", "X Coffee Roasters", and JJ Bean (its trade_name
                 contains 'coffee' even though the business_name is 'JJ Bean Inc')
    - espresso — catches espresso bars
    - roaster  — catches roasteries
    - cafe / café — catches cafe-named places that may not say "coffee"

Exclusion list (chains, see EXCLUDE_CHAINS):
    - Tim Hortons, Starbucks, Blenz, Waves Coffee. JJ Bean is intentionally NOT excluded
      despite chain-like footprint; treated as third-wave / specialty per project rationale.

Bubble-tea exclusion: bubble tea is its own signal, not specialty coffee. We strip names
matching 'bubble', 'boba', 'tea house', 'tea co' even when they appear in cafe canonical.

Known limitations:
    - Misses specialty coffee shops whose registered business and trade names contain none
      of the inclusion tokens (some indie spots register under a holding-company name only).
    - Catches some non-coffee businesses that happen to call themselves "Cafe X" without
      serving specialty coffee (Vietnamese cafes, internet cafes).
    - Chain detection is name-substring; if a chain rebrands or franchises under a different
      name we miss the exclusion.
"""

from __future__ import annotations

import duckdb
import polars as pl

from signals._common import aggregate_signal

SIGNAL_NAME = "specialty_coffee"
SIGNAL_CLASS = "leading"

EXCLUDE_CHAINS: tuple[str, ...] = (
    "starbucks",
    "tim hortons",
    "blenz",
    "waves coffee",
    "mcdonald",
    "mccafe",
    "second cup",
)

EXCLUDE_NON_COFFEE: tuple[str, ...] = (
    "bubble tea",
    "boba",
    "tea house",
    "tea co",
    "donut",
    "doughnut",
    "ice cream",
)

INCLUDE_TOKENS: tuple[str, ...] = ("coffee", "espresso", "roaster", "cafe", "café")


def _ilike_any(col: str, tokens: tuple[str, ...]) -> str:
    return " OR ".join(f"{col} ILIKE '%{t}%'" for t in tokens)


def get_signal(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    include = (
        f"({_ilike_any('business_name', INCLUDE_TOKENS)} "
        f"OR {_ilike_any('trade_name', INCLUDE_TOKENS)})"
    )
    exclude_chains = (
        f"NOT ({_ilike_any('business_name', EXCLUDE_CHAINS)} "
        f"OR {_ilike_any('trade_name', EXCLUDE_CHAINS)})"
    )
    exclude_non_coffee = (
        f"NOT ({_ilike_any('business_name', EXCLUDE_NON_COFFEE)} "
        f"OR {_ilike_any('trade_name', EXCLUDE_NON_COFFEE)})"
    )
    where = (
        f"canonical_category = 'cafe' AND {include} "
        f"AND {exclude_chains} AND {exclude_non_coffee}"
    )
    return aggregate_signal(con, where, SIGNAL_NAME, SIGNAL_CLASS)
