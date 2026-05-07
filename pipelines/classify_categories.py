"""Map raw city categories (old + new vocabularies) onto the project's canonical taxonomy.

Effective May 6, 2024 the City consolidated 500+ business licence categories into <100, so
historical and current data do not share a vocabulary. This module is the single seam where
both vocabularies get mapped onto the same internal categories that downstream signals see.

For Weekend 1 we only define canonicals that the three Weekend 1 signals need
(auto_repair, fitness_studio, grocery_food_retail). Everything else maps to 'uncategorized'.
The canonical set will grow as new signals get added.
"""

from __future__ import annotations

from pathlib import Path

import duckdb

DUCKDB_PATH = Path("vancouver_signals.duckdb")


# Each canonical maps to a list of matchers. A matcher is a dict; raw_category is required,
# raw_subcategory is optional. A row matches the canonical if any of its matchers match.
#
# Notes per canonical:
#   auto_repair: clean. Old-vocab "Auto Repairs *Historic*" is unambiguous.
#                New-vocab "Vehicle Repair Detailing and Washing Services" is broader (includes
#                washing/detailing); the auto_repair signal can refine if needed.
#   fitness_studio: deliberately over-broad. Yoga has no dedicated category in either vocab,
#                   so it lives across Fitness Centre / Sport and Fitness Instruction / older
#                   Instruction and Studio buckets. Signal-level name filters refine to yoga.
#   grocery_food_retail: includes general food retail since the anchor signal (Whole Foods)
#                        filters by name regardless.
TAXONOMY: dict[str, list[dict[str, str]]] = {
    "auto_repair": [
        # The new-vocab "Vehicle Repair Detailing and Washing Services" lumps repair,
        # detailing, body work, and washing. The old vocab kept these as separate
        # categories. To make the canonical comparable across the May 2024 schema break,
        # we map all four old-vocab categories to the same canonical the new-vocab one
        # maps to. Without this, businesses that pre-2024 only ever held an Auto Detailing
        # licence appear "new" in 2024 the moment the city issues them under the merged
        # new-vocab category.
        {"raw_category": "Auto Repairs *Historic*"},
        {"raw_category": "Auto Detailing *Historic*"},
        {"raw_category": "Auto Painter & Body Shop *Historic*"},
        {"raw_category": "Auto Washer *Historic*"},
        {"raw_category": "Vehicle Repair Detailing and Washing Services"},
    ],
    "fitness_studio": [
        {"raw_category": "Fitness Centre"},
        {"raw_category": "Sport and Fitness Instruction"},
        {"raw_category": "Instruction *Historic*", "raw_subcategory": "Fitness Instruction"},
        {"raw_category": "Studio *Historic*"},
    ],
    "grocery_food_retail": [
        {"raw_category": "Grocery Store"},
        {"raw_category": "Retail Dealer - Grocery *Historic*"},
        {"raw_category": "Retail Dealer - Food"},
        {"raw_category": "Retail Dealer - Food *Historic*"},
    ],
    # TODO: extend taxonomy as new signals are defined.
    # Candidates already visible in the data: Restaurant, Beauty Services, Limited Service Food
    # Establishment, Caterer, Print Shops, Health Enhancement Services, Therapeutic Touch
    # Technique *Historic*, Massage Therapist *Historic*, etc.
}


def _build_case_sql() -> str:
    branches: list[str] = []
    for canonical, matchers in TAXONOMY.items():
        for m in matchers:
            cat = m["raw_category"].replace("'", "''")
            if "raw_subcategory" in m:
                subcat = m["raw_subcategory"].replace("'", "''")
                branches.append(
                    f"WHEN raw_category = '{cat}' AND raw_subcategory = '{subcat}' "
                    f"THEN '{canonical}'"
                )
            else:
                branches.append(f"WHEN raw_category = '{cat}' THEN '{canonical}'")
    return "CASE " + " ".join(branches) + " ELSE 'uncategorized' END"


def classify(con: duckdb.DuckDBPyConnection) -> None:
    case_sql = _build_case_sql()
    con.execute(
        f"""
        CREATE OR REPLACE TABLE classified_licences AS
        SELECT *,
               {case_sql} AS canonical_category
        FROM raw_licences
        """
    )

    print("classified_licences written.")
    print("\nCoverage by canonical category:")
    rows = con.execute(
        """
        SELECT canonical_category, COUNT(*) AS n
        FROM classified_licences
        GROUP BY canonical_category
        ORDER BY n DESC
        """
    ).fetchall()
    total = sum(n for _, n in rows)
    for cat, n in rows:
        print(f"  {cat:24s} {n:>10,}  ({100 * n / total:5.2f}%)")
    classified = sum(n for cat, n in rows if cat != "uncategorized")
    print(f"\n  classified (non-uncategorized): {classified:,} / {total:,} ({100 * classified / total:.2f}%)")


def main() -> None:
    con = duckdb.connect(str(DUCKDB_PATH))
    try:
        classify(con)
    finally:
        con.close()


if __name__ == "__main__":
    main()
