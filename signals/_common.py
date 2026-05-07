"""Shared aggregation logic for signal modules.

Each signal collapses multiple licence rows (year-by-year renewals, address corrections,
revisions) down to one row per business with an establishment date, optional closure date,
the descriptive fields from the most recent licence row, and a left-censoring flag.

Closure-date assumption: a business is considered closed if its most recent licence row
has status in {'Gone Out of Business', 'Inactive', 'Cancelled'} AND that row's expiry_date
is later than any 'Issued' row for the same business. This will *under-count* closures
because businesses that simply stop renewing without an explicit closed-status row never
get a closure_date. Closure_date is fuzzy by year, not by day, since expiry_date is the
licence-period end (typically Dec 31), not the actual day the business shut down.

Left-censoring: a business is flagged is_left_censored=True when its establishment_date
falls in 1996 or 1997, which is the cliff edge of our observation window (the 1997-2012
source has its earliest record on 1996-12-17). Businesses in this cohort were almost
certainly operating before our data starts, so their establishment_date is the earliest
date we *saw* them, not the date they actually opened.
"""

from __future__ import annotations

import duckdb
import polars as pl

CLOSED_STATUSES = ("Gone Out of Business", "Inactive", "Cancelled")

# Hard cliff: anything before this year (inclusive) is flagged left-censored. The actual
# minimum issue_date in the 1997-2012 source is 1996-12-17; cohort years 1996 and 1997
# both sit at the cliff. Businesses with first licence in 1998+ have at least one full
# prior year of observation we'd have seen them in.
LEFT_CENSOR_YEAR = 1997


def aggregate_signal(
    con: duckdb.DuckDBPyConnection,
    where_sql: str,
    signal_name: str,
    signal_class: str,
) -> pl.DataFrame:
    """Return one row per business_id matching `where_sql`, in the standard signal schema."""
    closed_list = ", ".join(f"'{s}'" for s in CLOSED_STATUSES)
    sql = f"""
        WITH matched AS (
            SELECT * FROM geocoded_licences
            WHERE {where_sql}
        ),
        business_agg AS (
            SELECT
                business_id,
                arg_max(business_name, issue_date) AS name,
                arg_max(address, issue_date) AS address,
                arg_max(neighborhood, issue_date) AS neighborhood,
                CAST(MIN(issue_date) AS DATE) AS establishment_date,
                CAST(MAX(CASE WHEN status IN ({closed_list}) THEN expiry_date END) AS DATE) AS closure_candidate,
                MAX(CASE WHEN status = 'Issued' THEN issue_date END) AS latest_issued
            FROM matched
            GROUP BY business_id
        )
        SELECT
            business_id,
            name,
            address,
            neighborhood,
            establishment_date,
            CAST(
                CASE
                    WHEN closure_candidate IS NOT NULL
                      AND closure_candidate >= establishment_date
                      AND (latest_issued IS NULL OR closure_candidate > latest_issued)
                    THEN closure_candidate
                    ELSE NULL
                END
                AS DATE
            ) AS closure_date,
            (YEAR(establishment_date) <= {LEFT_CENSOR_YEAR}) AS is_left_censored,
            '{signal_name}' AS signal_name,
            '{signal_class}' AS signal_class
        FROM business_agg
        WHERE establishment_date IS NOT NULL AND name IS NOT NULL
    """
    return pl.from_arrow(con.execute(sql).arrow())
