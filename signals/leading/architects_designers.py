"""Architects and designers: hypothesized leading (or possibly coincident) signal.

Definition:
    canonical_category = 'architect_or_designer'

Rationale:
    The architect_or_designer canonical maps:
        - 'Architectural and Engineering Services' (new-vocab, 2k rows)
        - 'Office *Historic*' with subcategory in {Architect, Engineer,
          Interior Design/Decorator, Design Company} (old-vocab, ~30k rows combined)
        - 'Design Services' (new-vocab, 1.5k — broad, includes graphic/web/fashion design;
          accepted as noise)

    Architects and interior designers cluster around new-money construction and renovation
    activity. Their licence presence in a neighborhood is plausibly a leading indicator
    of upmarket residential and commercial transformation.

Address-of-work caveat:
    For architects and designers, the licence address is typically a real office (54%
    geom coverage, much better than contractors). But the *projects* they work on may be
    anywhere in the city. Neighborhood density of architects' offices reflects where
    architects' offices cluster (Mount Pleasant, Yaletown, Gastown), not where the
    buildings they design get built.

Caveats:
    - 'Design Services' lumps graphic design, web design, fashion design, industrial
      design alongside interior design. The signal treats them as one bucket; if the
      ratio of interior-to-other-design shifts over time (likely — graphic design has
      moved online), the signal drifts in meaning across years.
    - 'Engineer' subcategory includes mechanical, civil, electrical, software engineering
      consultancies — not just building engineers. Acceptable noise for an architect-
      adjacent signal.
"""

from __future__ import annotations

import duckdb
import polars as pl

from signals._common import aggregate_signal

SIGNAL_NAME = "architects_designers"
SIGNAL_CLASS = "leading"


def get_signal(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    where = "canonical_category = 'architect_or_designer'"
    return aggregate_signal(con, where, SIGNAL_NAME, SIGNAL_CLASS)
