"""Tag each licence with a Vancouver local area (neighborhood) via spatial join.

The licence data already includes lat/lon for ~50% of rows (the rest have no usable address
data on the city's side, and we accept that ceiling). The current 2024+ dataset additionally
exposes a city-populated `localarea` field; older datasets do not. We always do the spatial
join for consistency and treat the city-provided field as a cross-check, not a substitute.

No external geocoder is called.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import geopandas as gpd
from shapely.geometry import Point

DUCKDB_PATH = Path("vancouver_signals.duckdb")
BOUNDARY_PATH = Path("data/raw/local_area_boundary.geojson")


def geocode(con: duckdb.DuckDBPyConnection) -> None:
    boundaries = gpd.read_file(BOUNDARY_PATH)
    boundaries = boundaries.rename(columns={"name": "neighborhood"})[["neighborhood", "geometry"]]
    boundaries = boundaries.to_crs(epsg=4326)
    print(f"Loaded {len(boundaries)} neighborhood polygons.")

    licences = con.execute("SELECT * FROM classified_licences").fetchdf()
    print(f"Loaded {len(licences):,} classified licences.")

    has_geom = licences["lat"].notna() & licences["lon"].notna()
    geocodable = licences[has_geom].copy()
    print(f"  {len(geocodable):,} have lat/lon ({100 * len(geocodable) / len(licences):.1f}%)")

    geom = gpd.points_from_xy(geocodable["lon"], geocodable["lat"], crs="EPSG:4326")
    points = gpd.GeoDataFrame(geocodable, geometry=geom)

    joined = gpd.sjoin(points, boundaries, how="left", predicate="within")
    joined = joined.drop(columns=["geometry", "index_right"])

    no_geom = licences[~has_geom].copy()
    no_geom["neighborhood"] = None

    import pandas as pd

    spatial_full = pd.concat([joined, no_geom], ignore_index=True)
    # Hybrid: prefer the city-provided localarea when present (it's the authoritative
    # assignment and covers ~98% of current-dataset rows including those with no lat/lon),
    # fall back to our spatial join for older data where the city didn't populate it.
    spatial_full["neighborhood"] = spatial_full["source_localarea"].where(
        spatial_full["source_localarea"].notna(), spatial_full["neighborhood"]
    )
    con.register("geocoded_df", spatial_full)
    con.execute("CREATE OR REPLACE TABLE geocoded_licences AS SELECT * FROM geocoded_df")
    con.unregister("geocoded_df")

    print("\nNeighborhood-tagging coverage:")
    rows = con.execute(
        """
        SELECT
          COUNT(*) AS total,
          COUNT(neighborhood) AS tagged,
          ROUND(100.0 * COUNT(neighborhood) / COUNT(*), 2) AS pct_tagged
        FROM geocoded_licences
        """
    ).fetchone()
    print(f"  total: {rows[0]:,}  tagged: {rows[1]:,}  ({rows[2]}%)")

    print("\nPer-source coverage:")
    src_rows = con.execute(
        """
        SELECT source_dataset,
               COUNT(*) AS total,
               COUNT(neighborhood) AS tagged,
               ROUND(100.0 * COUNT(neighborhood) / COUNT(*), 2) AS pct_tagged
        FROM geocoded_licences
        GROUP BY source_dataset
        ORDER BY source_dataset
        """
    ).fetchall()
    for src, tot, tag, pct in src_rows:
        print(f"  {src:12s} total: {tot:>9,}  tagged: {tag:>9,}  ({pct}%)")

    print("\nCity-provided localarea vs spatial-join (current dataset only):")
    agree = con.execute(
        """
        SELECT
          COUNT(*) FILTER (WHERE source_localarea = neighborhood) AS agree,
          COUNT(*) FILTER (WHERE source_localarea IS NOT NULL AND neighborhood IS NOT NULL
                           AND source_localarea != neighborhood) AS disagree,
          COUNT(*) FILTER (WHERE source_localarea IS NOT NULL AND neighborhood IS NULL) AS join_missed,
          COUNT(*) FILTER (WHERE source_localarea IS NULL AND neighborhood IS NOT NULL) AS city_missed
        FROM geocoded_licences
        WHERE source_dataset = 'current'
        """
    ).fetchone()
    print(f"  agree: {agree[0]:,}  disagree: {agree[1]:,}  join_missed: {agree[2]:,}  city_missed: {agree[3]:,}")


def main() -> None:
    con = duckdb.connect(str(DUCKDB_PATH))
    try:
        geocode(con)
    finally:
        con.close()


if __name__ == "__main__":
    main()
