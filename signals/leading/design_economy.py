"""Design economy: a leading-signal aggregate of architects, engineers, designers.

Definition:
    canonical_category = 'architect_or_designer'

Scope (be honest — this is broader than "architects"):
    The signal lumps together four distinct populations that all sit in the design /
    pre-construction economy:
        - Architects (building designers, mostly under Office *Historic* subcategory
          'Architect' with ~10k licence rows historically)
        - Engineers (mechanical, civil, electrical, software — Office *Historic*
          subcategory 'Engineer', ~6k rows)
        - Interior designers (Office *Historic* subcategory 'Interior Design/Decorator',
          ~7k rows)
        - Design firms (graphic, web, industrial, fashion — Office *Historic*
          subcategory 'Design Company' plus new-vocab 'Design Services')
    Plus the new-vocab 'Architectural and Engineering Services' bucket (2k rows).

    Originally named architects_designers. Renamed to design_economy because the original
    name overstated the architecture share. Pure-architect counts are ~600-800 in
    Vancouver per the AIBC professional registration; this signal returns ~5,000 unique
    businesses, indicating the "architects + everything else design-adjacent" framing.

Rationale:
    Design-economy density tracks new-money construction and renovation activity. Where
    architects, engineers, and interior designers cluster their offices is plausibly a
    leading indicator of where upmarket built-environment work is concentrated, even if
    the actual built work happens elsewhere. The signal is appropriate for time-series
    analysis (rising or falling design-economy presence in the city) and somewhat
    appropriate for spatial analysis (where the offices cluster: Mount Pleasant,
    Yaletown, Gastown).

Address-of-work caveat:
    Architects and design firms have ~54% geom coverage (much better than contractors,
    worse than storefront retail). Licence addresses are typically real offices, but the
    *projects* served may be anywhere. Neighborhood density reflects design-firm office
    geography, not the geography of the buildings they design.

Caveats:
    - 'Design Services' (new-vocab) is broad and includes graphic / web / fashion /
      industrial design. The signal accepts the noise; if the ratio of building-design
      to other-design shifts over time, the signal drifts in meaning. A future drill-down
      could split by subcategory.
    - 'Engineer' subcategory includes engineering disciplines unrelated to buildings
      (software, mining, mechanical). Acceptable noise for a design-economy aggregate.
    - For pure-architect counts, restrict to `Office *Historic*` subcategory='Architect'
      OR new-vocab name filter for "architect"; that's a different signal that hasn't
      been built.
"""

from __future__ import annotations

import duckdb
import polars as pl

from signals._common import aggregate_signal

SIGNAL_NAME = "design_economy"
SIGNAL_CLASS = "leading"


def get_signal(con: duckdb.DuckDBPyConnection) -> pl.DataFrame:
    where = "canonical_category = 'architect_or_designer'"
    return aggregate_signal(con, where, SIGNAL_NAME, SIGNAL_CLASS)
