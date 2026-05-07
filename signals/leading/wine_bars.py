"""Wine bars: a hypothesized leading indicator of gentrification.

Definition:
    canonical_category IN ('liquor_establishment', 'full_service_restaurant')
    AND name matches at least one wine token (wine, vintner, cellar, vintage, enoteca, cave)
    AND name does NOT match retail-wine or U-Brew exclusions

Rationale:
    Vancouver's licence vocabulary has no dedicated "wine bar" category. Wine bars register
    under a mix of liquor categories ("Liquor Establishment Standard *Historic*", "Lounge 'A'",
    new-vocab "Liquor Establishment") AND under restaurant categories when they serve food
    alongside wine. The signal is necessarily a category + name composite. The wine token
    list is intentionally short to keep precision high; broader matches like "bar" alone
    would catch every cocktail and dive bar in the city.

Wine tokens (case-insensitive substring match in business_name or trade_name):
    wine, vintner, cellar, vintage, enoteca, cave (as in cave-a-vin)

Exclusions:
    - 'liquor retail store' / 'specialty wine store' (categories): retail, not a bar.
      Already kept out via canonical scoping.
    - name contains 'u-brew', 'u-vin': make-your-own-wine places, not bars.
    - name contains 'wine store', 'wine shop', 'liquor store': retail.

Known limitations:
    - Many wine-forward restaurants don't have wine words in the name and won't be caught.
    - A few false positives slip through (e.g., a 'Vintage Lounge' with a 70s cocktail
      theme rather than a wine focus). The signal is best read as "bars/restaurants with
      visible wine identity," which correlates with but is narrower than "wine bars."
    - The category scoping deliberately includes Restaurant Class 1 / Dining Lounge to
      catch wine-focused restaurants. This pulls in noise that the name filter has to
      remove.
"""

from __future__ import annotations

import duckdb
import polars as pl

from signals._common import aggregate_signal

SIGNAL_NAME = "wine_bars"
SIGNAL_CLASS = "leading"

INCLUDE_TOKENS: tuple[str, ...] = (
    "wine",
    "vintner",
    "cellar",
    "vintage",
    "enoteca",
    "cave a vin",
)

EXCLUDE_TOKENS: tuple[str, ...] = (
    "u-brew",
    "u-vin",
    "u brew",
    "u vin",
    "wine store",
    "wine shop",
    "liquor store",
    "wine retail",
)


def _ilike_any(col: str, tokens: tuple[str, ...]) -> str:
    return " OR ".join(f"{col} ILIKE '%{t}%'" for t in tokens)


def get_signal(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    include = (
        f"({_ilike_any('business_name', INCLUDE_TOKENS)} "
        f"OR {_ilike_any('trade_name', INCLUDE_TOKENS)})"
    )
    exclude = (
        f"NOT ({_ilike_any('business_name', EXCLUDE_TOKENS)} "
        f"OR {_ilike_any('trade_name', EXCLUDE_TOKENS)})"
    )
    where = (
        "canonical_category IN ('liquor_establishment', 'full_service_restaurant') "
        f"AND {include} AND {exclude}"
    )
    return aggregate_signal(con, where, SIGNAL_NAME, SIGNAL_CLASS)
