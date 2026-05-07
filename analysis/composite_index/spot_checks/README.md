# Closure detection spot-checks

Two CSVs sampled from the Weekend 1 signals to manually validate the closure-date heuristic.

- `closed_sample.csv`: 20 businesses where `closure_date` is set. Question: is each one actually closed today (per Google Maps)?
- `open_sample.csv`: 20 businesses where `closure_date` is null. Question: is each one actually still operating today (per Google Maps)?

For each row, fill the `verdict` column with one of:

- `closed` — Google Maps says permanently closed, or the address shows a different business
- `open` — currently operating under the same name and address
- `moved` — same business, different address (still open)
- `renamed` — same address, business under a new name (was a rebrand or sale)
- `unclear` — can't tell from Maps alone

`notes` is freeform.

After filling out, the relevant precision/recall numbers are:

- closed_sample: % verdicts that say `closed` is the precision of our closure-date heuristic
- open_sample: % verdicts that say `open` is the precision of our "still operating" inference

If the closed_sample precision is high (≥80%) and the open_sample precision is also high (≥80%), the heuristic is fit for purpose.

If closed_sample is low: many "closed" flags are really renewals or admin lapses, not closures. The set of statuses we treat as closed (currently `Gone Out of Business`, `Inactive`, `Cancelled`) needs revisiting.

If open_sample is low: many "still operating" rows are actually closed but never got a closed-status licence row. We're under-counting closures, and any signal that compares opening velocity to closure velocity will look healthier than reality.

Stratification: roughly 8 auto repair, 8 yoga, 4 Whole Foods (or whatever falls out of the sampling — Whole Foods has only 3 total rows, none closed, so it's mostly informational).
