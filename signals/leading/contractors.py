"""Renovation and general contractors: hypothesized leading (or possibly coincident) signal.

Definition:
    canonical_category = 'general_contractor'
    AND name does NOT contain 'construction' (those go to construction_companies signal)

Rationale:
    The general_contractor canonical includes the full contractor universe (Contractor
    *Historic*, Contractor - Special Trades *Historic*, General Contractor, Trade
    Contractor — about 147k licence rows). It mixes one-person renovation outfits, mid-
    sized renovation firms, and larger construction companies. The contractors and
    construction_companies signals partition that canonical by name: anything with
    "construction" in business or trade name is treated as a (typically larger)
    construction company; everything else is treated as a general / renovation contractor.

Address-of-work caveat (CRITICAL):
    Contractor licences register the business address (often a home or small office), not
    the address where work happens. Spatial analysis at the neighborhood level reflects
    where contractors are *based*, not where they're renovating. About 92% of
    Contractor *Historic* rows have no usable lat/lon at all (per data/README.md "Known
    limitations"). For this signal, neighborhood density should be read as "where
    contractors live and register" not "where renovations are happening."
"""

from __future__ import annotations

import duckdb
import polars as pl

from signals._common import aggregate_signal

SIGNAL_NAME = "contractors"
SIGNAL_CLASS = "leading"


def get_signal(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    where = """
        canonical_category = 'general_contractor'
        AND NOT (business_name ILIKE '%construction%' OR trade_name ILIKE '%construction%')
    """
    return aggregate_signal(con, where, SIGNAL_NAME, SIGNAL_CLASS)
