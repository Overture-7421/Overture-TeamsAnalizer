# Validation Checklist

## Schema And Parsing
- Confirm the requested columns exist in schema with expected keys and labels.
- Confirm CSV parsing still maps fields correctly.
- Confirm missing placeholder handling remains consistent.

## Engine Stability
- Confirm core stats computation runs without runtime errors.
- Confirm renamed or removed fields are handled safely.
- Confirm no key metrics silently become empty due to mapping drift.

## Streamlit Stability
- Confirm app startup path still works with current sample data.
- Confirm primary pages render without key or attribute exceptions.
- Confirm tables and charts still receive expected dataframe columns.

## Display Validation
- Team stats: values populate and sorting still behaves as expected.
- Detail stats: per-team breakdown and derived values display correctly.
- Foreshadowing: source fields resolve and cards or tables render correctly.
- Alliance selector: ranking inputs and simulation views use valid fields.

## Final Safety Checks
- Confirm only requested behavior changed.
- Record any known manual follow-up checks for live Streamlit run.