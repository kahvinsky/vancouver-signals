# Yoga closure spot-check

**Question.** Yoga's 23.4% closure rate (vs specialty coffee's 53.8%) is roughly half. Is yoga genuinely more durable, or does the closure heuristic systematically under-count yoga closures because yoga teachers operate as personal-services-style licences and tend to lapse rather than file explicit cancellations?

The general-purpose `closed_sample.csv` / `open_sample.csv` test the closure heuristic across all signals. This pair tests it against yoga *specifically* so we can isolate whether the yoga vs coffee survival gap is real or an artifact.

## Files

- `yoga_open_sample.csv` — 20 yoga businesses where the heuristic says still operating (closure_date is null). Includes `last_observed_licence_date` (the most recent issue_date for that business across any licence row, not just yoga-related ones). If a business hasn't had any licence activity in years, it's probably gone even though the heuristic says open.
- `yoga_closed_sample.csv` — 20 yoga businesses where the heuristic says closed (closure_date is not null).

## How to verify

For each row, check Google Maps for the business at the listed address. Fill `verdict`:

- `still_open` — currently operating at the same address under the same name (or a continuation: same yoga studio, slight rename)
- `closed` — Maps shows permanently closed, address is now a different business, or the business has no current web presence and no Maps listing
- `moved` — same business, different address (still operating yoga)
- `renamed` — same address, business is now under a clearly different name (not a yoga studio anymore, or a different yoga studio)
- `unclear` — can't determine from Maps + a quick web search alone

Use the `notes` column for anything worth recording (e.g., "Maps shows permanently closed since 2022 but our heuristic still says open — confirms under-counting").

## What the result tells us

- **If yoga_open_sample has many `closed` verdicts** (say >25%): the heuristic under-counts yoga closures, and the 81% pooled 5-year survival rate is inflated. The yoga vs coffee survival gap may shrink or disappear once we improve closure detection.
- **If yoga_open_sample is mostly `still_open`** (say >80%): yoga really is durable, and the survival gap with coffee reflects genuine business-model differences, not a measurement artifact.
- **If yoga_closed_sample is mostly `closed`**: precision is good (when we say closed, they really are).
- **If yoga_closed_sample has many `still_open`**: false-positive closures, and the closure-status set used in `signals/_common.py` (`Gone Out of Business`, `Inactive`, `Cancelled`) is too aggressive for yoga.

The interesting asymmetry to watch for: heavy false-negatives on the open sample (many "open" yoga businesses that are actually closed) combined with clean true-positives on the closed sample (the explicit closures we do detect are real). That pattern would suggest yoga teachers tend to fade out without filing closure paperwork.

## Method context

`last_observed_licence_date` is the diagnostic to lean on. A yoga business with `closure_date IS NULL` but `last_observed_licence_date` more than ~3 years ago is highly suspicious — either we missed a closure or the business stopped renewing despite still operating informally. For each row in the open sample, the rule of thumb:

- `last_observed_licence_date` within the last 18 months → almost certainly still operating
- 18-36 months ago → could go either way; check Maps
- 36+ months ago → likely closed even though heuristic says open
