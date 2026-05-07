"""Landscaping: a coincident wealth signal.

Definition:
    canonical_category = 'landscaping'
    OR (canonical_category = 'general_contractor'
        AND (business_name ILIKE '%landscap%' OR trade_name ILIKE '%landscap%'))

Rationale:
    Landscapers serve people with property and discretionary income for outdoor
    aesthetics. Density of landscaping businesses tracks existing affluence rather than
    change: a wave of new landscapers opening in Marpole would suggest Marpole already
    has the buyers, not that gentrification is on its way. This is the prototype
    'coincident' signal class.

    The landscaping canonical is just the old-vocab 'Landscape Gardener *Historic*'
    (15k rows). Post-May-2024 the city collapsed landscapers into General Contractor
    (no equivalent new-vocab category exists). The signal includes both: the canonical
    plus general_contractor-with-landscape-name to recover post-2024 records.

Address-of-work caveat (CRITICAL):
    Landscapers are mobile by definition. Licence address is the operator's home or a
    small office; work happens at clients' properties anywhere in the city. About 97% of
    Landscape Gardener *Historic* rows have no lat/lon. Spatial analysis at neighborhood
    level reflects where landscapers *live*, not where lawns are being maintained. For
    this signal, the spatial dimension is essentially unusable; the temporal dimension
    (count of landscapers over time) carries the signal.
"""

from __future__ import annotations

import duckdb
import polars as pl

from signals._common import aggregate_signal

SIGNAL_NAME = "landscaping"
SIGNAL_CLASS = "coincident"


def get_signal(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    where = """
        canonical_category = 'landscaping'
        OR (canonical_category = 'general_contractor'
            AND (business_name ILIKE '%landscap%' OR trade_name ILIKE '%landscap%'))
    """
    return aggregate_signal(con, where, SIGNAL_NAME, SIGNAL_CLASS)
