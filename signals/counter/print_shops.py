"""Print shops: a hypothesized counter signal (incumbent industry being displaced).

Definition:
    canonical_category = 'print_shop'

Mapped from:
    - Old vocabulary: 'Printing Services *Historic*' (Kinko's-style print/copy shops),
      'Blueprint Printing *Historic*'
    - New vocabulary: 'Printing Imaging and Photo Services'

Intentional exclusions:
    - 'Sign Permit *Historic*': despite the name, this is the city's permit registry for
      building signage (a regulatory record), not a category for sign-making businesses.
    - 'Design Services': graphic / web / fashion / industrial design grouped together. Too
      broad to count as print shops; many design firms never touch a printer.
    - T-shirt and screen printing: live under garment manufacturing categories
      ('Manufacturer *Historic*', subtype 'Garments'). Different industry, different
      gentrification dynamics; not folded in.

The print/copy/blueprint cluster is exactly the kind of incumbent retail business that gets
priced out as commercial rents rise. Used to be a fixture of every commercial strip in
Vancouver. The hypothesis is that decline in print-shop density is coincident-or-lagging
with neighborhood gentrification.
"""

from __future__ import annotations

import duckdb
import polars as pl

from signals._common import aggregate_signal

SIGNAL_NAME = "print_shops"
SIGNAL_CLASS = "counter"


def get_signal(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    where = "canonical_category = 'print_shop'"
    return aggregate_signal(con, where, SIGNAL_NAME, SIGNAL_CLASS)
