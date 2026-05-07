"""Pull the three Vancouver business licence datasets into DuckDB as raw_licences.

The three CSVs are static (1997-2012, 2013-2024) plus a daily-updated current dataset.
We download once, normalize column names + types, concat, and write a single table.
Re-running is idempotent (CREATE OR REPLACE on the DuckDB side, skip-download on disk).

Name and address normalization powers the business_id hash. The same business renewing
year-on-year gets a new licencenumber each time, so name + house + normalized_street is
the most stable identity proxy we have. Aggressive normalization at this seam means
cross-year, cross-vocabulary, and cross-suffix variants of the same business produce the
same business_id without a separate dedup pass.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
import polars as pl
import requests

DATA_RAW = Path("data/raw")
DUCKDB_PATH = Path("vancouver_signals.duckdb")

DATASETS: dict[str, dict[str, str]] = {
    "1997-2012": {
        "slug": "business-licences-1997-to-2012",
        "filename": "business_licences_1997_to_2012.csv",
    },
    "2013-2024": {
        "slug": "business-licences-2013-to-2024",
        "filename": "business_licences_2013_to_2024.csv",
    },
    "current": {
        "slug": "business-licences",
        "filename": "business_licences_current.csv",
    },
}

EXPORT_BASE = "https://opendata.vancouver.ca/api/explore/v2.1/catalog/datasets"

# Trailing corporate suffixes stripped from business names. Order matters: longer phrases
# first, otherwise "incorporated" gets clipped to "incorporat" by an earlier "inc" rule.
_CORP_SUFFIX_RE = (
    r"\s+(incorporated|corporation|limited|holdings|"
    r"company|society|inc|ltd|llc|corp|co)\.?$"
)

# Street-type and directional standardizations. Each pattern uses \b to avoid eating
# substrings of unrelated words (e.g., AV inside DAVID).
_STREET_PAIRS: tuple[tuple[str, str], ...] = (
    (r"\bavenue\b", "ave"),
    (r"\bav\b", "ave"),
    (r"\bstreet\b", "st"),
    (r"\bstr\b", "st"),
    (r"\bboulevard\b", "blvd"),
    (r"\bbvd\b", "blvd"),
    (r"\bbl\b", "blvd"),
    (r"\broad\b", "rd"),
    (r"\bdrive\b", "dr"),
    (r"\bplace\b", "pl"),
    (r"\blane\b", "ln"),
    (r"\bcourt\b", "ct"),
    (r"\bcrescent\b", "cres"),
    (r"\bhighway\b", "hwy"),
    (r"\bterrace\b", "ter"),
    (r"\bnorth\b", "n"),
    (r"\bsouth\b", "s"),
    (r"\beast\b", "e"),
    (r"\bwest\b", "w"),
)


def normalize_name_expr(col: str) -> pl.Expr:
    """Lower-case, strip punctuation, drop trailing corporate suffix, collapse spaces."""
    expr = (
        pl.col(col)
        .fill_null("")
        .str.to_lowercase()
        .str.replace_all(r"[^\w\s&]", " ")
        .str.replace_all(r"\s+", " ")
        .str.strip_chars()
    )
    # Strip up to two trailing corp suffixes ("foo bar inc ltd" → "foo bar")
    expr = expr.str.replace(_CORP_SUFFIX_RE, "")
    expr = expr.str.replace(_CORP_SUFFIX_RE, "")
    return expr.str.strip_chars()


def normalize_street_expr(col: str) -> pl.Expr:
    """Lower-case, standardize street-type and directional abbreviations."""
    expr = (
        pl.col(col)
        .fill_null("")
        .str.to_lowercase()
        .str.replace_all(r"[^\w\s]", " ")
        .str.replace_all(r"\s+", " ")
        .str.strip_chars()
    )
    for pattern, replacement in _STREET_PAIRS:
        expr = expr.str.replace_all(pattern, replacement)
    return expr.str.replace_all(r"\s+", " ").str.strip_chars()


def download_if_missing(source: str) -> Path:
    spec = DATASETS[source]
    path = DATA_RAW / spec["filename"]
    if path.exists() and path.stat().st_size > 0:
        return path
    url = f"{EXPORT_BASE}/{spec['slug']}/exports/csv?delimiter=%2C&timezone=UTC"
    print(f"  downloading {source} from {url}")
    DATA_RAW.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=600) as resp:
        resp.raise_for_status()
        with open(path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=1 << 20):
                f.write(chunk)
    return path


def normalize(path: Path, source: str) -> pl.DataFrame:
    """Read one source CSV and project it onto the unified raw_licences schema."""
    df = pl.read_csv(
        path,
        infer_schema_length=20000,
        ignore_errors=True,
        try_parse_dates=False,
    )

    # Mixed date formats: bare YYYY-MM-DD in 1997-2012, ISO timestamps in newer files.
    # The first 10 chars are always the date portion, so slice then parse.
    issue_date = (
        pl.col("issueddate").cast(pl.Utf8, strict=False)
        .str.slice(0, 10)
        .str.to_date(format="%Y-%m-%d", strict=False)
    )
    expiry_date = (
        pl.col("expireddate").cast(pl.Utf8, strict=False)
        .str.slice(0, 10)
        .str.to_date(format="%Y-%m-%d", strict=False)
    )

    # Display address: keep the human-readable form for downstream UI.
    address_display = pl.concat_str(
        [
            pl.when(pl.col("unittype").is_not_null() & pl.col("unit").is_not_null())
            .then(pl.concat_str([pl.col("unittype"), pl.lit(" "), pl.col("unit"), pl.lit(", ")]))
            .otherwise(pl.lit("")),
            pl.col("house").cast(pl.Utf8).fill_null(""),
            pl.lit(" "),
            pl.col("street").fill_null(""),
        ]
    ).str.strip_chars().str.replace_all(r"\s+", " ")

    # Normalized name and address feed both the business_id hash and the bridging pass
    # in pipelines.classify_categories. Unit is intentionally excluded from the address
    # so two licence rows for the same business that disagree on unit (or where unit
    # was added/dropped) still hash to the same id.
    norm_name = normalize_name_expr("businessname")
    norm_street = normalize_street_expr("street")
    norm_house = pl.col("house").cast(pl.Utf8).fill_null("").str.strip_chars()
    norm_address = pl.concat_str([norm_house, pl.lit(" "), norm_street]).str.strip_chars()

    business_id_key = pl.concat_str([norm_name, pl.lit("|"), norm_address])

    # Geometry: 2013+ exposes geo_point_2d as "lat, lon"; 1997-2012 has only the geom JSON.
    if "geo_point_2d" in df.columns:
        lat = (
            pl.col("geo_point_2d").str.split(",")
            .list.get(0, null_on_oob=True).str.strip_chars()
            .cast(pl.Float64, strict=False)
        )
        lon = (
            pl.col("geo_point_2d").str.split(",")
            .list.get(1, null_on_oob=True).str.strip_chars()
            .cast(pl.Float64, strict=False)
        )
    else:
        coords = pl.col("geom").str.extract(r"\[([^\]]+)\]", 1)
        lon = coords.str.split(",").list.get(0, null_on_oob=True).str.strip_chars().cast(pl.Float64, strict=False)
        lat = coords.str.split(",").list.get(1, null_on_oob=True).str.strip_chars().cast(pl.Float64, strict=False)

    out = df.select(
        [
            business_id_key.hash().cast(pl.Utf8).alias("business_id"),
            pl.col("businessname").alias("business_name"),
            pl.col("businesstradename").alias("trade_name"),
            address_display.alias("address"),
            norm_name.alias("normalized_name"),
            norm_address.alias("normalized_address"),
            pl.col("businesstype").alias("raw_category"),
            pl.col("businesssubtype").alias("raw_subcategory"),
            pl.col("status"),
            issue_date.alias("issue_date"),
            expiry_date.alias("expiry_date"),
            pl.lit(source).alias("source_dataset"),
            lat.alias("lat"),
            lon.alias("lon"),
            pl.col("city"),
            pl.col("postalcode").alias("postal_code"),
            pl.col("localarea").alias("source_localarea"),
            pl.col("licencenumber").alias("licence_number"),
            pl.col("licencersn").cast(pl.Utf8, strict=False).alias("licence_rsn"),
        ]
    )
    return out


SCHEMA_BREAK = "2024-05-06"


def bridge_business_ids(con: duckdb.DuckDBPyConnection) -> None:
    """Bridge May 2024 schema-break "false new" business_ids to their pre-break match.

    A business_id is a candidate for bridging when:
      - its earliest issue_date is on or after the 2024-05-06 schema break
      - some pre-break business_id has the same (normalized_name, normalized_address)
      - normalized_address is non-empty (we don't bridge address-less rows; they all
        normalize to the same key and would over-merge).

    With normalization already applied at hash time, exact-match bridging is mostly a
    no-op for current data. The pass is here as defensive infrastructure: it catches
    any case where the hash-time normalization is later loosened, and it gives us a
    place to plug in fuzzier matching as the dataset reveals more failure modes.
    """
    con.execute(
        f"""
        CREATE OR REPLACE TEMPORARY TABLE bridge_candidates AS
        WITH biz_first AS (
            SELECT business_id,
                   MIN(issue_date) AS first_issue,
                   any_value(normalized_name) AS normalized_name,
                   any_value(normalized_address) AS normalized_address
            FROM raw_licences
            WHERE issue_date IS NOT NULL
            GROUP BY business_id
        ),
        new_block AS (
            SELECT * FROM biz_first
            WHERE first_issue >= DATE '{SCHEMA_BREAK}' AND normalized_address <> ''
        ),
        old_block AS (
            SELECT business_id, normalized_name, normalized_address
            FROM biz_first
            WHERE first_issue < DATE '{SCHEMA_BREAK}'
        )
        SELECT n.business_id AS new_id, o.business_id AS old_id
        FROM new_block n
        JOIN old_block o
          ON o.normalized_name = n.normalized_name
         AND o.normalized_address = n.normalized_address
        """
    )
    bridge_count = con.execute("SELECT COUNT(*) FROM bridge_candidates").fetchone()[0]
    if bridge_count == 0:
        print("  bridge pass: 0 remaps (hash-time normalization already collapses exact matches)")
        return

    con.execute(
        """
        UPDATE raw_licences
        SET business_id = bc.old_id
        FROM bridge_candidates bc
        WHERE raw_licences.business_id = bc.new_id
        """
    )
    print(f"  bridge pass: remapped {bridge_count:,} business_ids to pre-2024 matches")


def load(con: duckdb.DuckDBPyConnection) -> None:
    frames: list[pl.DataFrame] = []
    for source in DATASETS:
        path = download_if_missing(source)
        df = normalize(path, source)
        frames.append(df)
        print(f"  {source}: {df.height:,} rows")

    combined = pl.concat(frames, how="vertical_relaxed")
    print(f"  total: {combined.height:,} rows")

    con.execute("CREATE OR REPLACE TABLE raw_licences AS SELECT * FROM combined")

    bridge_business_ids(con)

    counts = con.execute(
        "SELECT source_dataset, COUNT(*) AS n FROM raw_licences GROUP BY source_dataset ORDER BY source_dataset"
    ).fetchall()
    print("\nraw_licences row counts:")
    for source, n in counts:
        print(f"  {source}: {n:,}")
    total = con.execute("SELECT COUNT(*) FROM raw_licences").fetchone()[0]
    unique_ids = con.execute("SELECT COUNT(DISTINCT business_id) FROM raw_licences").fetchone()[0]
    print(f"  total: {total:,}")
    print(f"  unique business_ids: {unique_ids:,}")


def main() -> None:
    print("Loading Vancouver business licences...")
    con = duckdb.connect(str(DUCKDB_PATH))
    try:
        load(con)
    finally:
        con.close()


if __name__ == "__main__":
    main()
