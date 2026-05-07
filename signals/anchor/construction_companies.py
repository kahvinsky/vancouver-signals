"""Construction companies: anchor signal for larger-scale construction firms.

Definition:
    canonical_category = 'general_contractor'
    AND (business_name ILIKE '%construction%' OR trade_name ILIKE '%construction%')

Rationale:
    Without an employee-count or revenue field in raw_licences, we partition the
    general_contractor canonical by name. Businesses that include "Construction" in their
    registered name skew larger and more established than independent renovators (median
    of 6 licence rows per business, max 43; many are multi-decade firms). The
    contractors signal takes the rest.

    The two signals together fully cover general_contractor canonical without
    double-counting. They answer different questions: contractors tracks the renovation
    economy at the household scale; construction_companies tracks larger-scale firms
    that build buildings.

Address-of-work caveat (CRITICAL):
    Same as the contractors signal. Construction firms register their head-office address;
    they build elsewhere across the city and region. Neighborhood density of construction
    company head offices does NOT correlate with where construction is happening. About
    8.5% geom coverage in Contractor *Historic* — most rows have no address at all.
    Spatial analysis is structurally limited.

Note on signal_class:
    Classified as 'anchor' per project specification. Note that construction_companies
    here is denser than the other anchor signal (Whole Foods has 3 rows; this signal has
    ~3,000). The "anchor" framing reflects the user's intent (rare-but-meaningful
    arrivals/departures of larger firms) rather than an absolute volume threshold.
"""

from __future__ import annotations

import duckdb
import polars as pl

from signals._common import aggregate_signal

SIGNAL_NAME = "construction_companies"
SIGNAL_CLASS = "anchor"


def get_signal(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    where = """
        canonical_category = 'general_contractor'
        AND (business_name ILIKE '%construction%' OR trade_name ILIKE '%construction%')
    """
    return aggregate_signal(con, where, SIGNAL_NAME, SIGNAL_CLASS)
