"""Skilled trades (plumbers, electricians, HVAC): a combined coincident wealth signal.

Definition:
    canonical_category = 'skilled_trade_specialist'
    OR (canonical_category = 'general_contractor'
        AND (business_name OR trade_name) matches plumber/electrician/HVAC/heating tokens)

Rationale:
    Plumbers, electricians, and HVAC specialists are demand-driven by people who own
    property and pay for servicing. Combined into one signal because:
        1. Individually each old-vocab category is dense (Electrical Contractor 35k,
           Plumber 10k+) but new-vocab collapses them into Trade Contractor / General
           Contractor and we can't cleanly separate post-2024.
        2. Collectively they tell one story: home-service trade activity, which tracks
           existing wealth and renovation density.
        3. HVAC has no dedicated category in either vocabulary; it's only identifiable by
           name within the broader Gas Contractor / Trade Contractor buckets.

    The skilled_trade_specialist canonical maps the per-trade old-vocab categories
    (Plumber, Plumber & Gas Contractor, Electrical Contractor, Gas Contractor, etc.).
    Post-May-2024 trades register under General Contractor / Trade Contractor; the signal
    pulls them back via name filter.

Trade-name tokens for new-vocab recovery:
    plumb, electric, hvac, heating, gas fit, gas tech, gasfit

Intentional exclusions:
    Painter *Historic*, Roofer *Historic*, Sprinkler Contractor *Historic*: these are
    skilled trades but the user's spec was specifically plumber/electrician/HVAC. Painter
    and roofer are typically lower-skill / lower-licence-fee tradesmen with different
    economics; sprinkler contractors are mostly commercial.

Address-of-work caveat (CRITICAL):
    Same as landscaping. Plumbers and electricians are mobile by definition; licence
    address is their home or a small office. About 97-98% of Plumber and Electrical
    Contractor rows have no lat/lon. Spatial analysis at the neighborhood level is
    structurally unusable for this signal. The temporal trend (rising or falling count
    of registered trade specialists in Vancouver) is what carries the signal.
"""

from __future__ import annotations

import duckdb
import polars as pl

from signals._common import aggregate_signal

SIGNAL_NAME = "skilled_trades"
SIGNAL_CLASS = "coincident"

NAME_TOKENS = ("plumb", "electric", "hvac", "heating", "gas fit", "gas tech", "gasfit")


def _ilike_any(col: str, tokens: tuple[str, ...]) -> str:
    return " OR ".join(f"{col} ILIKE '%{t}%'" for t in tokens)


def get_signal(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    name_filter = (
        f"({_ilike_any('business_name', NAME_TOKENS)} "
        f"OR {_ilike_any('trade_name', NAME_TOKENS)})"
    )
    where = f"""
        canonical_category = 'skilled_trade_specialist'
        OR (canonical_category = 'general_contractor' AND {name_filter})
    """
    return aggregate_signal(con, where, SIGNAL_NAME, SIGNAL_CLASS)
