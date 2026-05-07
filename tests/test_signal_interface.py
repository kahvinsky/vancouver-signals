"""Contract test: every signal module must conform to the standard interface.

This is the guardrail that keeps signals 4 through 20 consistent with 1 through 3. As new
signals get added under signals/, append them to SIGNALS below and rely on the same
parameterized assertions.
"""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path

import duckdb
import polars as pl
import pytest

from signals.anchor.whole_foods_openings import get_signal as get_whole_foods
from signals.coincident.construction_companies import get_signal as get_construction
from signals.coincident.landscaping import get_signal as get_landscaping
from signals.coincident.skilled_trades import get_signal as get_skilled_trades
from signals.counter.auto_repair import get_signal as get_auto_repair
from signals.counter.print_shops import get_signal as get_print_shops
from signals.leading.contractors import get_signal as get_contractors
from signals.leading.design_economy import get_signal as get_design_economy
from signals.leading.pilates_studios import get_signal as get_pilates
from signals.leading.real_estate_brokerages import get_signal as get_real_estate
from signals.leading.specialty_coffee import get_signal as get_specialty_coffee
from signals.leading.wine_bars import get_signal as get_wine_bars
from signals.leading.yoga_studios import get_signal as get_yoga

DUCKDB_PATH = Path("vancouver_signals.duckdb")

REQUIRED_COLUMNS: tuple[str, ...] = (
    "business_id",
    "name",
    "address",
    "neighborhood",
    "establishment_date",
    "closure_date",
    "is_left_censored",
    "signal_name",
    "signal_class",
)

# Columns that must never be null. address and neighborhood can be null because the city
# data has ~50% missingness on geometry/address; that's a data-quality reality, not a bug.
# closure_date is explicitly nullable per the signal contract.
NON_NULL_COLUMNS: tuple[str, ...] = (
    "business_id",
    "name",
    "establishment_date",
    "is_left_censored",
    "signal_name",
    "signal_class",
)

VALID_SIGNAL_CLASSES = {"leading", "counter", "anchor", "coincident"}

SIGNALS = [
    pytest.param(get_yoga, "yoga_studios", "leading", id="yoga_studios"),
    pytest.param(get_specialty_coffee, "specialty_coffee", "leading", id="specialty_coffee"),
    pytest.param(get_wine_bars, "wine_bars", "leading", id="wine_bars"),
    pytest.param(get_pilates, "pilates_studios", "leading", id="pilates_studios"),
    pytest.param(get_contractors, "contractors", "leading", id="contractors"),
    pytest.param(get_design_economy, "design_economy", "leading", id="design_economy"),
    pytest.param(get_real_estate, "real_estate_brokerages", "leading", id="real_estate_brokerages"),
    pytest.param(get_auto_repair, "auto_repair", "counter", id="auto_repair"),
    pytest.param(get_print_shops, "print_shops", "counter", id="print_shops"),
    pytest.param(get_whole_foods, "whole_foods_openings", "anchor", id="whole_foods_openings"),
    pytest.param(get_construction, "construction_companies", "coincident", id="construction_companies"),
    pytest.param(get_landscaping, "landscaping", "coincident", id="landscaping"),
    pytest.param(get_skilled_trades, "skilled_trades", "coincident", id="skilled_trades"),
]


@pytest.fixture(scope="module")
def con() -> duckdb.DuckDBPyConnection:
    if not DUCKDB_PATH.exists():
        pytest.skip(
            f"{DUCKDB_PATH} does not exist; run pipelines.load_licences, "
            f"classify_categories, geocode first"
        )
    c = duckdb.connect(str(DUCKDB_PATH), read_only=True)
    yield c
    c.close()


@pytest.mark.parametrize(("get_signal", "expected_name", "expected_class"), SIGNALS)
def test_signal_schema(get_signal, expected_name, expected_class, con):
    df = get_signal(con)
    assert isinstance(df, pl.DataFrame)
    for col in REQUIRED_COLUMNS:
        assert col in df.columns, f"missing required column: {col}"


@pytest.mark.parametrize(("get_signal", "expected_name", "expected_class"), SIGNALS)
def test_signal_has_rows(get_signal, expected_name, expected_class, con):
    df = get_signal(con)
    assert df.height > 0, f"signal {expected_name} returned no rows"


@pytest.mark.parametrize(("get_signal", "expected_name", "expected_class"), SIGNALS)
def test_signal_no_nulls_in_required_columns(get_signal, expected_name, expected_class, con):
    df = get_signal(con)
    for col in NON_NULL_COLUMNS:
        nulls = df[col].is_null().sum()
        assert nulls == 0, f"{expected_name}.{col} has {nulls} nulls (not allowed)"


@pytest.mark.parametrize(("get_signal", "expected_name", "expected_class"), SIGNALS)
def test_signal_name_and_class(get_signal, expected_name, expected_class, con):
    df = get_signal(con)
    assert df["signal_name"].unique().to_list() == [expected_name]
    assert df["signal_class"].unique().to_list() == [expected_class]
    assert expected_class in VALID_SIGNAL_CLASSES


@pytest.mark.parametrize(("get_signal", "expected_name", "expected_class"), SIGNALS)
def test_no_future_establishment_dates(get_signal, expected_name, expected_class, con):
    df = get_signal(con)
    today = datetime.now()
    future = df.filter(pl.col("establishment_date") > today)
    assert future.height == 0, (
        f"{expected_name} has {future.height} establishment dates in the future"
    )


@pytest.mark.parametrize(("get_signal", "expected_name", "expected_class"), SIGNALS)
def test_closure_after_establishment(get_signal, expected_name, expected_class, con):
    df = get_signal(con)
    with_closure = df.filter(pl.col("closure_date").is_not_null())
    bad = with_closure.filter(pl.col("closure_date") < pl.col("establishment_date"))
    assert bad.height == 0, (
        f"{expected_name} has {bad.height} rows where closure_date < establishment_date"
    )


@pytest.mark.parametrize(("get_signal", "expected_name", "expected_class"), SIGNALS)
def test_business_id_unique(get_signal, expected_name, expected_class, con):
    df = get_signal(con)
    assert df["business_id"].n_unique() == df.height, (
        f"{expected_name} has duplicate business_id rows"
    )


@pytest.mark.parametrize(("get_signal", "expected_name", "expected_class"), SIGNALS)
def test_date_dtypes_are_date(get_signal, expected_name, expected_class, con):
    df = get_signal(con)
    assert df["establishment_date"].dtype == pl.Date, (
        f"{expected_name}.establishment_date is {df['establishment_date'].dtype}, expected pl.Date"
    )
    assert df["closure_date"].dtype == pl.Date, (
        f"{expected_name}.closure_date is {df['closure_date'].dtype}, expected pl.Date"
    )


@pytest.mark.parametrize(("get_signal", "expected_name", "expected_class"), SIGNALS)
def test_is_left_censored_is_boolean(get_signal, expected_name, expected_class, con):
    df = get_signal(con)
    assert df["is_left_censored"].dtype == pl.Boolean, (
        f"{expected_name}.is_left_censored is {df['is_left_censored'].dtype}, expected pl.Boolean"
    )
