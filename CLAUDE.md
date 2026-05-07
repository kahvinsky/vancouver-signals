# vancouver-signals

A signals dataset and analytical project tracking neighborhood change in Vancouver through the City's business licence history.

## Project context

The thesis: the appearance, density, and timing of certain consumer-facing business types function as leading indicators of neighborhood gentrification, while the closure of certain incumbent businesses functions as a coincident or lagging indicator of the same process. Tracking many such signals together, and watching how they lead and lag each other across neighborhoods and time, should reveal where Vancouver is changing now and where it is changing next.

The core analytical questions:

- Which business-type signals correlate most strongly with gentrification across the past decade?
- Which signals lead, which are coincident, and which lag?
- Which signals are strongest right now (the current frontier)?
- Where in Vancouver is next to gentrify, based on the leading indicators?
- Do composite signals predict more reliably than any individual one?

This repo holds the data pipeline, the signal definitions, and the cross-cutting analysis tooling. Individual analytical pieces live in `analysis/` and are written for publication on Substack under the Bearing Research brand. Each piece foregrounds a different signal or combination of signals, but all draw from the same underlying dataset.

The first published piece will likely lead with matcha-serving cafes (a sharp, current-frontier signal with cultural texture), but matcha is one signal among many. The repo is built around the general framework, not around any single piece.

## Tech stack

- Python 3.12+
- DuckDB for the analytical layer (single file at `vancouver_signals.duckdb`, gitignored)
- Polars for in-memory dataframe work (preferred over pandas; pandas is fine in notebooks if it's already in hand)
- Parquet for all intermediate and processed data
- GeoPandas + Shapely for spatial joins against Vancouver neighborhood boundaries
- Jupyter for exploratory work and analytical notebooks
- Matplotlib + Plotly for static and interactive visualizations
- `uv` for environment and dependency management

No dbt. The transformation graph is shallow and doesn't justify the overhead.

## Repo structure

```
vancouver-signals/
  data/
    raw/             # original downloads, never edited, gitignored
    interim/         # cleaned, geocoded, neighborhood-tagged, gitignored
    processed/       # final analytical parquet tables, gitignored
    README.md        # documents data sources and download instructions
  pipelines/
    load_licences.py        # pull and clean Vancouver business licence data
    geocode.py              # address → lat/lon → neighborhood tagging
    classify_categories.py  # collapse city categories into project taxonomy
  signals/           # signal definitions, each one a defined query
    leading/         # hypothesized leading indicators
      specialty_coffee.py
      yoga_studios.py
      pilates_studios.py
      wine_bars.py
      natural_wine.py
      independent_bookstores.py
      pet_grooming.py
      matcha_cafes.py
    counter/         # hypothesized displaced / declining businesses
      auto_repair.py
      print_shops.py
      thrift_stores.py
      family_diners.py
    anchor/          # rare but high-signal events
      whole_foods_openings.py
      independent_bookstore_openings.py
    analytics.py     # reusable cross-signal analytical primitives
  analysis/         # publication artifacts, one directory per piece
    composite_index/        # the cross-cutting framework piece
    leading_vs_lagging/     # which signals lead, which lag
    where_next/             # neighborhood-level forecasting
    matcha/                 # matcha-specific deep dive
    yoga/
  viz/              # shared visualization code (maps, timelines, animations)
  notebooks/        # exploratory and scratch work, not for publication
  tests/
  pyproject.toml
  README.md
  CLAUDE.md
```

## Conventions

- Type hints on all function signatures in `pipelines/`, `signals/`, and `viz/`. Notebooks can be loose.
- Docstrings: short, explain *why* not *what*. One-liners are fine.
- Snake_case everywhere. No Hungarian notation.
- Each signal in `signals/` exposes a single function `get_signal(con: duckdb.DuckDBPyConnection) -> pl.DataFrame` returning establishment-dated rows with at minimum: `business_id`, `name`, `address`, `neighborhood`, `establishment_date`, `closure_date` (nullable), `signal_name`, `signal_class` (one of `leading`, `counter`, `anchor`).
- Each signal also documents its definition: which licence categories are included, any name-based filtering rules, and the rationale for inclusion.
- Parquet files use snake_case names matching the table they represent.
- Notebooks are numbered (`01_`, `02_`) within each analysis directory and run top-to-bottom without state from prior runs.

## Analytical primitives

The repo should make it easy to ask the following kinds of questions across any signal or combination of signals:

- **Density**: how many of signal X exist per neighborhood right now, normalized by area or population?
- **Velocity**: how fast is signal X opening (or closing) in neighborhood Y, by year?
- **Lead-lag**: does signal X in a neighborhood predict signal Y appearing N years later in the same neighborhood?
- **Composite**: weighted combination of multiple signals into a single neighborhood-level index, plotted over time.
- **Frontier**: which neighborhoods have the highest current velocity in leading signals but low absolute density (i.e., where change is starting)?
- **Forecast**: given current leading-signal velocity, which neighborhoods are likely to see the broader pattern in the next 2-5 years?

These should be implemented as reusable functions in `signals/analytics.py`, not re-derived in each notebook.

## Data sources

- **Vancouver business licences** (primary). Open Vancouver portal at open.vancouver.ca. Full historical records. This is the spine.
- **Vancouver neighborhood boundaries**. Open Vancouver portal, GeoJSON.
- **Census trajectory data** (validation). StatsCan census tract data on income, education, age, tenure changes.
- **MacroLens housing data** (cross-reference, where useful). Already in hand from the existing MacroLens warehouse.
- **Google Places API** (current cafe inventory and review excerpts for menu-level classification signals like matcha). Free tier sufficient for project scope.
- **Wayback Machine** (targeted bellwether deep-dives and listicle archaeology, manual not automated).
- **Reddit + food blog archives** (cultural timeline for narrative pieces, supplementary).

Do not use Yelp Fusion / Yelp Places API. The licence terms prohibit analytical use.

## Things to do

- Always read this file at the start of a session.
- Before adding a dependency, check if an existing one covers it. Ask before adding anything not in `pyproject.toml`.
- For any script that makes external API calls or LLM calls: print the call count and estimated cost before executing. Require explicit confirmation for runs over 100 calls or $1 in expected cost.
- Prefer composing existing signals and analytical primitives over writing new ad-hoc queries.
- When adding a new signal, follow the existing template exactly. Consistency across signals is what makes composite analysis possible.
- When writing visualizations, default to matplotlib for static publication-quality and Plotly for interactive web. Use the project's shared style in `viz/style.py` once it exists.
- Commit messages: imperative mood, present tense ("add yoga signal" not "added yoga signal"). Reference the signal class or analysis directory if the change supports a specific area.

## Things not to do

- Do not commit anything in `data/` (raw, interim, or processed). All gitignored.
- Do not commit the DuckDB file or any `.env` files.
- Do not commit scraped data even if the scraping is benign. Keep scraped artifacts local.
- Do not run pipelines that touch external APIs without confirming first.
- Do not refactor working code unless asked. Stability over cleverness.
- Do not introduce new abstractions until the second use case appears. Premature abstraction is the main failure mode for projects of this scope.
- Do not privilege any single signal in pipeline or analytical code. Matcha is one signal among many; the framework should treat it identically to yoga, wine bars, or any other.
- Do not add tests for exploratory notebook code. Add tests for `pipelines/`, `signals/`, and analytical primitives only.

## Voice and tone

When writing prose for analysis pieces, draft outputs, READMEs, or any user-facing text in this repo, follow the conventions in the `kevin-book-voice` skill. Plain English, mixed sentence lengths leaning longer, parentheticals welcome, no em dashes, no exclamation points, no ellipses. Lead with sharpest claims. No throat-clearing.

For code comments and internal documentation, just be clear and brief.

## What "done" looks like for the repo as infrastructure

By end of Weekend 1: licence data loaded into DuckDB, geocoded, neighborhood-tagged, and 2-3 signals (one leading, one counter, one anchor) defined and working end-to-end through the standard signal interface.

By end of Weekend 2: 8-10 signals defined across the three classes. Analytical primitives (density, velocity, lead-lag, composite, frontier) implemented and tested against any signal.

By end of Weekend 3: at least one cross-cutting analysis complete (composite index across all signals, validated against known gentrification patterns; or lead-lag analysis showing which signals predict which).

The repo is in good shape when adding a new signal takes under an hour and any analytical question can be answered against any signal without writing new infrastructure.

## What "done" looks like for the inaugural Substack piece

The first published piece will lead with whichever angle is sharpest after the data is in hand. Candidate framings:

- **Composite gentrification index**: here are the strongest signals, here is how they combine, here is what the index says about Vancouver right now.
- **Lead-lag analysis**: which signals predict change earliest, with whichever signal turns out to be the sharpest leading indicator highlighted.
- **Where next**: forecast piece using leading signals to identify the next 2-3 neighborhoods to gentrify.
- **Matcha index**: cultural-texture entry point, with the broader framework in the methodology section.

Decide the framing after the data is built, not before. Let the strongest finding lead.
