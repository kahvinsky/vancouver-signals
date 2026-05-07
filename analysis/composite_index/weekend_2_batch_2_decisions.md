# Weekend 2, batch 2: methodology decisions

This is the audit trail for the six new signals (contractors, architects_designers, real_estate_brokerages, construction_companies, landscaping, skilled_trades) and the new `coincident` signal class. Every non-trivial methodology call gets recorded here so the framing can be revisited as the corpus grows.

## The new `coincident` signal class

**Decision.** Add `coincident` as a fourth valid `signal_class` value alongside `leading`, `counter`, and `anchor`.

**Context.** Some signals track *existing* affluence rather than its arrival or departure. Landscaping and skilled-trade specialists are demand-driven by people who already own property and pay for servicing. Density of these businesses in a neighborhood does not predict gentrification (leading) and does not lag it (counter); it sits at roughly the same time as observed wealth. The existing three classes did not have a slot for "marker of contemporaneous affluence."

**Alternatives considered.**
- Force these signals into `leading` or `counter`. Rejected because the implied causal claim is wrong.
- Add `wealth` as a class instead. Rejected because the framing is more methodological than topical: many topics have a coincident relationship with the underlying phenomenon, not just wealth.
- Skip the class change and treat landscapers/trades as `leading`. Rejected because their behavior in survival analysis would then be wrongly compared against true leading signals.

**Rationale.** `coincident` captures the temporal relationship cleanly and lets cross-class comparisons (in the survival notebook and any future composite index) treat the four classes as distinct populations. The class is open-ended in topic; future signals like high-end veterinary clinics, art galleries, or luxury car dealerships might also belong here.

**Caveats.** The class names start to crowd; if a fifth class becomes needed, consider a hierarchical scheme. For now four is fine.

## Signal-by-signal canonical mapping decisions

### contractors and construction_companies (partition of one canonical)

**Decision.** One canonical (`general_contractor`) covers the contractor universe; two signals partition it by name.
- `contractors`: `general_contractor` AND name does NOT contain "construction"
- `construction_companies`: `general_contractor` AND name DOES contain "construction"

**Context.** The user's spec called for distinct signals: contractors (renovation) vs construction companies (larger general/civil construction). The licence data does not distinguish business size; `numberofemployees` is in the source CSV but was not loaded into `raw_licences`. Without a size field, only name-based heuristics remain.

**Alternatives considered.**
- Re-load `raw_licences` to include `numberofemployees`, then partition by employee count (e.g., >50 employees → construction company). Rejected for now because (a) it requires a re-run and schema change, (b) employee count is self-reported and may be unreliable, (c) the name heuristic is good enough as a first cut.
- Map all contractor categories to `contractors` only and skip `construction_companies` entirely. Rejected because the user explicitly asked for both signals.
- Define `construction_companies` as a strict-name list (Bird, PCL, EllisDon, Ledcor, etc.) for true anchor-style rarity. Rejected as too brittle and too narrow; misses long tail of mid-sized construction firms.

**Rationale.** "Construction" in name correlates with larger and more institutional contracting firms. The partition keeps the two signals non-overlapping and exhaustive over the canonical. Easy to revisit when employee counts get loaded.

**Caveats.** 4,413 unique businesses end up in `construction_companies`, much denser than the user's anchor-rare framing suggests. The signal is treated as `signal_class='anchor'` per project spec but should probably be re-classified as `coincident` after the user reviews the magnitude. Some renovation contractors do call themselves "Construction" (e.g., "Smith Family Construction Renovations Ltd") and end up in the wrong bucket; the false-positive rate is bounded but non-zero.

### architects_designers

**Decision.** Map four old-vocab `Office *Historic*` subcategories (Architect, Engineer, Interior Design/Decorator, Design Company) plus two new-vocab categories (Architectural and Engineering Services, Design Services) to one canonical, then expose as one signal without a name filter.

**Context.** Architects in Vancouver licence data live mostly under `Office *Historic*` with a subcategory tag. The new-vocab `Architectural and Engineering Services` category is the obvious bucket but has only 2k rows; the bulk of historical architects/designers/engineers are in `Office *Historic*` subcategories totaling ~30k rows. `Design Services` (1.5k) is a broad new-vocab catch-all.

**Alternatives considered.**
- Split into separate signals: architects, interior designers, engineers. Rejected because individually each old-vocab subcategory has 5-10k licence rows but collapsed-to-business counts would be small and inconsistent across new vocab.
- Exclude Engineer subcategory (includes mechanical/civil/software engineers). Rejected because the user asked for "architects, interior designers" but engineers are part of the building-design ecosystem and excluding them creates a different gap.
- Tighten with a name filter for "architect"/"design"/"interior". Rejected because most architecture firms register as "Smith Architects Inc" without "design" in name; the category-based filter is more inclusive.

**Rationale.** Treat as one signal capturing the "design economy" broadly. Differential analysis (architect-only vs designer-only) is a future drill-down.

**Caveats.** The signal returns **4,942 unique businesses** — significantly more than "hundreds of architects." This reflects the broader-than-architects scope. The signal is more accurately "architects + interior designers + engineers + design firms." If the user wants strict architect counts, narrow to `Office *Historic*` subcategory='Architect' OR new-vocab name filter for "architect." Document this trade-off; read the signal's neighborhood density as design-economy density, not architect density.

### real_estate_brokerages

**Decision.** Map `Real Estate Dealer *Historic*` (old) + `Real Estate Services` (new) + `Office *Historic*` subcategory `Real Estate Development/Investment`. Exclude `Brokerage Services` (new-vocab generic).

**Context.** Three plausible categories; one ambiguous (`Brokerage Services` could be insurance/freight/real estate).

**Alternatives considered.**
- Include `Brokerage Services`. Rejected because the category is generic and would pollute the signal with non-real-estate brokerages.
- Exclude `Real Estate Development/Investment` subcategory. Rejected because development companies are part of the real-estate-flipping ecosystem and arguably more leading-indicator-y than transactional brokerages.

**Rationale.** Three-category mapping is comprehensive without polluting with the ambiguous fourth.

**Caveats.** 2,786 unique businesses, on the higher end of "hundreds" the user expected. Vancouver's real estate density during the observation window justifies the count. The Development/Investment subcategory may double-count corporate entities that hold both a brokerage and a development licence; not de-duplicated.

### landscaping

**Decision.** Map only the old-vocab `Landscape Gardener *Historic*` to the canonical. Recover post-May-2024 landscapers in the signal SQL via `general_contractor` canonical AND name contains "landscap".

**Context.** No new-vocab landscape category exists. Post-May-2024 landscapers register under `General Contractor` or `Trade Contractor` (verified: 597 "landscap"-named businesses in `General Contractor` since 2024).

**Alternatives considered.**
- Map `General Contractor` to the canonical too. Rejected because `General Contractor` includes 15k+ rows of mostly-not-landscapers; the canonical would be dominated by noise.
- Skip post-2024 recovery and accept the gap. Rejected because the new-vocab gap would create an artificial "death" of the landscaping signal in 2024.
- Use `Building Repair and Maintenance` as a proxy. Rejected because it's broader (includes janitorial, HVAC, electrical maintenance).

**Rationale.** Canonical scoping plus signal-level OR with a name filter on `general_contractor` cleanly handles the schema break.

**Caveats.** The OR pattern in the signal SQL is duplicated in `skilled_trades` (same problem, same solution). If a third signal needs the same pattern, the OR logic should move into the classifier with a more flexible matching API.

### skilled_trades

**Decision.** Combine plumber, electrician, and gas-contractor (HVAC proxy) into one signal. Map per-trade old-vocab categories to a `skilled_trade_specialist` canonical; recover post-May-2024 in signal SQL via `general_contractor` canonical AND name tokens (`plumb`, `electric`, `hvac`, `heating`, `gas fit`, `gas tech`, `gasfit`).

**Context.** The user's spec explicitly asked for the trades to be combined "because individually they're sparse and collectively they tell one story." But the data shows they're not actually sparse individually:
- `Electrical Contractor *Historic*`: 35,400 licence rows
- `Plumber *Historic*` family: ~24,000 rows combined
- `Gas Contractor *Historic*` family: ~6,400 rows

So the combination decision is not driven by sparsity but by:
1. **The wealth-signal framing.** Plumbers, electricians, and HVAC specialists collectively serve the "people who own property and pay for servicing" market. Splitting them would obscure that single story.
2. **Post-2024 recovery is awkward when split.** Each trade's new-vocab home is `Trade Contractor` / `General Contractor`; cleanly extracting just plumbers vs just electricians from a name filter requires per-trade name lists with overlap and edge cases. Combined signal sidesteps that.
3. **HVAC has no dedicated category** in either vocabulary; it's only identifiable via name within the broader Gas Contractor / Trade Contractor buckets. The combined skilled_trades signal absorbs HVAC naturally; a stand-alone HVAC signal would essentially have no canonical.

**Alternatives considered.**
- Three separate signals (plumbers, electricians, HVAC). Rejected for the reasons above.
- Skip HVAC entirely as untrackable. Rejected because the user explicitly asked for it.
- Include painters and roofers in the skilled_trades signal. Rejected because user spec was specifically plumber/electrician/HVAC, and painter/roofer have different economics (lower licence fee, less specialized).

**Rationale.** Combined signal matches the user's framing, sidesteps the post-2024 vocabulary collapse, and lets HVAC ride along.

**Caveats.** The signal is the largest of the new batch (8,585 businesses). The combined-trade framing means we can't independently track plumber vs electrician vs HVAC trends. If a future analysis wants per-trade breakdown, restrict to old-vocab categories only and accept the post-2024 cliff.

## The address-of-work problem

**Decision.** Document the address-of-work caveat explicitly in every contractor/trade/landscaping signal docstring AND in this document. Do not attempt to resolve it.

**Context.** Vancouver business licences register the *business address* (where the licence is held, often a home or small office), not the *work address* (where the business actually performs services). For storefront retailers (cafes, grocery, yoga studios) these are the same. For contractors, plumbers, electricians, landscapers, and most service trades, they diverge sharply.

**The data tells us**:
- `Contractor *Historic*` has 8.5% lat/lon coverage (91.5% of rows have no usable address)
- `Electrical Contractor *Historic*`: 3.1% coverage
- `Plumber *Historic*`: 2.4%
- `Landscape Gardener *Historic*`: 2.7%
- `Painter *Historic*`: 4.7%
- `Trade Contractor`: 7.0%
- Compare to storefront categories: Restaurant 96%, Health and Beauty 95%, Limited Service Food 94%

Even when address fields are populated, they're typically the operator's home address. The trade is mobile.

**Implication.** Spatial analysis (neighborhood density, neighborhood survival curves) on contractors / trades / landscaping signals does NOT measure where work is happening. It measures where the operators *live and register*. Two valid framings:

1. **Where do trade specialists live?** A neighborhood with many plumber registrations may have many plumbers as residents. Useful for some questions (housing affordability for skilled tradespeople, immigrant-trade clustering).
2. **Where is renovation work happening?** Not answerable from this data. Would need building-permit data, not business-licence data.

For composite-index work that combines signals across categories, this means contractors/trades/landscaping are temporal-only signals: aggregate counts over time work, neighborhood density does not.

**Alternatives considered.**
- Filter signals to only registered office addresses (not home addresses). Rejected because there's no clean field distinguishing the two.
- Geocode work addresses from a separate building-permit dataset. Rejected as out of scope for Weekend 2; a future signal class.
- Drop these signals from spatial analysis entirely. Documented but not enforced; analyses that use them spatially must do so consciously and noted.

**Rationale.** Document the caveat prominently so analysts don't accidentally make the wrong claim. Don't attempt a fix because no fix is clean.

**Caveats.** This is a known limitation, not a bug. The architects_designers and real_estate_brokerages signals have the milder version (54% and 74% coverage) because architects and brokers more often have real offices.

## Where n is too low to be confident

**Decision threshold.** Treat any signal with fewer than 30 unique businesses (after dropping left-censored) as "low confidence" — surface results but mark them as fragile, especially for cohort survival and neighborhood-level analysis.

**Signals currently under that threshold.**
- `wine_bars`: 24 businesses post-left-censor (already documented in `signals/leading/wine_bars.py` docstring as a recall floor)
- `whole_foods_openings`: 3 businesses
- `pilates_studios`: 55 (above threshold but small enough to flag for neighborhood-level claims)

**Rationale for the 30 threshold.** Below 30, year-over-year cohort sizes drop to 0-3 routinely, and survival curves become per-business noise rather than population statistics. Above 30, even sparse cohorts have enough statistical mass for the curves to be visually interpretable. 30 is a heuristic, not a sharp boundary.

**Caveats.** Wine_bars in particular needs either a manual curation pass to lift recall or an explicit downgrade to "indicator only, do not include in survival comparisons."

## Validation: signal counts table (all 13 signals)

Computed after taxonomy + classifier + bridge-pass + geocode end-to-end. Total counts include left-censored.

| signal | class | total | % left-censored | % with closure |
|---|---|---|---|---|
| yoga_studios | leading | 154 | 0.0% | 23.4% |
| specialty_coffee | leading | 1,352 | 4.4% | 53.8% |
| wine_bars | leading | 25 | 4.0% | 60.0% |
| pilates_studios | leading | 55 | 0.0% | 25.5% |
| contractors | leading | 7,501 | 7.7% | 10.5% |
| architects_designers | leading | 4,942 | 14.7% | 22.2% |
| real_estate_brokerages | leading | 2,786 | 14.0% | 26.5% |
| auto_repair | counter | 1,739 | 28.2% | 29.6% |
| print_shops | counter | 640 | 30.0% | 28.9% |
| whole_foods_openings | anchor | 3 | 0.0% | 0.0% |
| construction_companies | anchor | 4,413 | 13.9% | 12.1% |
| landscaping | coincident | 2,040 | 18.7% | 19.4% |
| skilled_trades | coincident | 8,585 | 19.3% | 18.5% |

### Eyeball check

Vancouver scale expectations vs observed:
- **Thousands of contractors** expected → 7,501 ✓ matches
- **Hundreds of architects** expected → 4,942 (signal includes designers and engineers; pure-architect count would be smaller). Surfaced above as a scoping decision worth user review.
- **Hundreds of real estate brokerages** expected → 2,786, on the higher end. Plausible given Vancouver's real estate intensity over 25 years.
- **Construction companies** as anchor-rare → 4,413, much denser than anchor framing suggests. Documented above.
- **Landscapers** → 2,040, plausible for a city of Vancouver's residential density and 25-year window.
- **Skilled trades** → 8,585, large but matches the combined plumb+electric+gas+HVAC scope.

### Closure-rate observations

- The new contractor/construction/architect/real-estate signals have low closure rates (10-26%). Plausible because:
  1. These businesses tend to renew durably (real-estate brokerages especially)
  2. The closure heuristic systematically under-counts businesses that lapse rather than file explicit closures (the same problem flagged for yoga in the spot-check work)
- `wine_bars` 60% closure is the highest — small sample fragility plus genuine industry churn.
- `whole_foods_openings` 0% closure is correct (all 3 stores still open).

### Bias caveat to remember

The closure-rate column is the heuristic's read, not the truth. The yoga spot-check (`analysis/composite_index/spot_checks/yoga_open_sample.csv` etc.) is the calibration mechanism. Until that's verified, take all closure rates as upper bounds on "still operating" and lower bounds on "actually closed."

## Open questions for next session

1. **Yoga spot-check results.** When the yoga verification CSVs come back, recompute the closure-rate calibration and apply any correction to the survival comparisons (especially the yoga vs specialty coffee gap).
2. **Architects scope.** Decide whether `architects_designers` should be split into pure-architects vs design-economy-broad, or whether the broad framing is the intended one.
3. **Construction companies signal_class.** Currently `anchor`; consider re-classifying as `coincident` given the magnitude (4,413 not anchor-rare).
4. **Wine bars curation.** Decide whether to invest in a manual INCLUDE list to lift recall, or accept the high-precision floor with prominent documentation.
5. **Address-of-work resolution.** Building-permit data could partially resolve the contractor/trade spatial-analysis gap; out of scope for now but flagged as a future-signal candidate.
6. **`numberofemployees` field.** Currently dropped from `raw_licences`. Adding it back enables size-based partitioning for contractors/construction (instead of name-based), and might enable a separate "small business" signal class.
