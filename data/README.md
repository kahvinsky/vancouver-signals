# Data

Everything inside `data/` is gitignored except this file and the `.gitkeep` markers that hold the directory shape. This README is the single source of truth for what should be present locally and where it came from. Re-download manually as needed; there is no automated portal sync.

## Layout

- `data/raw/`: original downloads, never edited
- `data/interim/`: cleaned, geocoded, neighborhood-tagged
- `data/processed/`: final analytical parquet tables loaded into DuckDB

## Sources

### Vancouver business licences (the spine)

The City publishes business licence records as three separate datasets, split by category schema. All three are needed for full historical coverage from 1997 to present.

- **Business licences 1997 to 2012**: static historical record, original categories.
  https://opendata.vancouver.ca/explore/dataset/business-licences-1997-to-2012/
  Save as `data/raw/business_licences_1997_to_2012.csv`.

- **Business licences 2013 to 2024**: static, covers 2013 through May 3, 2024, original categories (`BusinessType` field).
  https://opendata.vancouver.ca/explore/dataset/business-licences-2013-to-2024/
  Save as `data/raw/business_licences_2013_to_2024.csv`.

- **Business licences** (current): 2024 onwards, updated daily, new consolidated categories.
  https://opendata.vancouver.ca/explore/dataset/business-licences/
  Save as `data/raw/business_licences_current.csv`.

**Schema break to be aware of.** Effective May 6, 2024, the City consolidated over 500 business licence categories into fewer than 100. The historical datasets and the current dataset do not share a category vocabulary. Any signal that touches both eras needs an explicit category-mapping step. The project's collapsed taxonomy lives in `pipelines/classify_categories.py` and sits below both city schemas, mapping each into a stable internal category set.

### Vancouver local area boundaries

- **Local area boundary**: the city's 22 local planning areas. Boundaries follow street centrelines and do not change.
  https://opendata.vancouver.ca/explore/dataset/local-area-boundary/
  Download as GeoJSON. Save as `data/raw/local_area_boundary.geojson`.

These are the "neighborhoods" used throughout the project. Every signal output is tagged to one of them via spatial join in `pipelines/geocode.py`.

## Other sources

The signals reach beyond business licences for cross-validation and menu-level signal detection. See `CLAUDE.md` for the full list (StatsCan census, MacroLens housing, Google Places, Wayback Machine, Reddit and food blog archives). None are required for Weekend 1.

## Known limitations

### Lat/lon coverage is roughly 50% and biased by business model

About half of all licence rows have no usable lat/lon (49.4% as of the 2026-05-06 pull, fairly stable across all three source datasets). The other half cannot be retroactively geocoded from the source data because the address fields are themselves blank: there is no street, no house number, often not even a unit. The pattern of missingness is structural and worth understanding before drawing spatial conclusions.

**Storefront businesses have nearly full coverage.** Categories whose business model requires a physical commercial address show 4-10% missingness:

| Category | rows | % missing geom |
|---|---|---|
| Restaurant | 6,110 | 4.1% |
| Health and Beauty *Historic* | 18,879 | 5.2% |
| Limited Service Food Establishment | 4,751 | 5.6% |
| Legal Services | 6,342 | 6.8% |
| Tattoo Parlour *Historic* | 1,361 | 6.8% |
| Retail Dealer - Grocery *Historic* | 1,565 | 9.8% |
| Restaurant Class 1 *Historic* | 53,637 | 10.2% |

**Home-based, mobile, and dwelling categories have effectively zero coverage.** The city does not geocode private residential addresses or mobile service providers, so these read as 95-100% missing:

| Category | rows | % missing geom |
|---|---|---|
| Single Detached House *Historic* | 128,471 | 100.0% |
| Short-term Rental Operator | 45,504 | 100.0% |
| Multiple Dwelling *Historic* | 33,450 | 100.0% |
| Duplex *Historic* | 30,301 | 100.0% |
| Plumber *Historic* | 10,296 | 97.6% |
| Landscape Gardener *Historic* | 14,748 | 97.3% |
| Electrical Contractor *Historic* | 35,400 | 96.9% |
| Painter *Historic* | 7,732 | 95.3% |
| Contractor *Historic* | 89,153 | 91.5% |

**Non-Vancouver licences are 100% missing geom.** ~9% of rows are issued to businesses headquartered outside Vancouver (Burnaby, Surrey, Richmond, etc., per the `city` column). The portal does not geocode out-of-jurisdiction addresses. These are not Vancouver businesses for spatial purposes and should be filtered.

**Year matters at the edges.** 1996-1997 are 60-67% missing (the cliff edge of the dataset, address records are sparse for businesses that pre-existed the digital licence system). 1998-2017 is the cleanest band at 41-46%. 2018+ ticks back up slightly, possibly reflecting the rise of home-based and online businesses.

**Implications for signals.**
- Signals defined over storefront retail (restaurants, specialty coffee, grocery, yoga studios with a leased space) are well-covered. Spatial analyses are sound.
- Signals defined over home-based or mobile service providers (yoga *teachers*, personal trainers, freelance professionals, contractors) will be missing most of their volume in spatial analyses. Aggregate counts by neighborhood will undercount these by 10-50x.
- A composite signal that mixes storefront and home-based versions of the same trade (e.g., a "wellness" signal lumping yoga studios with mobile yoga instructors) silently biases toward the storefront variant.
- The `auto_repair` canonical sits at 30% missing, `fitness_studio` at 41%, `grocery_food_retail` at 17%. The fitness number is a heads-up that the Weekend 1 yoga signal partly reflects "yoga business that bothered to get a storefront licence" rather than "yoga teacher."

This characterization is not a fixable bug; the source data does not contain locations for these rows. The right response is to scope analyses to categories where coverage is high, and to be explicit when a category's coverage caps the conclusions we can draw.
