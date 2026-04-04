# Repository Metric Map: Points Avg and Avg Pts Contribution

This map targets Overture Teams Analyzer.

## Points Avg lineage

Primary code points:
- `lib/engine.py` -> `AnalizadorRobot.get_detailed_team_stats`
  - Calculates per-match score and stores aggregate in `team_stats['overall_avg']`
- `lib/streamlit_app.py`
  - Uses `overall_avg` to display `Points Avg` in multiple tables/charts

Important checks:
- Verify active scoring path (`_decode_score_row` path vs fallback coral/algae path)
- Verify denominator for averaging included matches
- Verify current season columns and constants are aligned with manual

## Avg Pts Contribution lineage

Primary code points:
- `lib/streamlit_app.py` -> `get_pm_contribution_points(team_number)`
  - Converts qualitative contribution labels into per-match point estimates
- `lib/streamlit_app.py` -> `get_pm_avg_pts_contribution(team_number)`
  - Mean of contribution point list
- `lib/streamlit_app.py` -> `get_pm_std_pts_contribution(team_number)`
  - Sample std (`n-1`)

Current qualitative map in code:
- Did not score any points -> 0.00
- Scored few points -> 0.05
- Scored ~30% of alliance score -> 0.30
- Scored ~50% of alliance score -> 0.50
- Scored ~75% of alliance score -> 0.75
- Scored almost all alliance score -> 0.90

Special handling in code:
- Dedicated to passing / Dedicated to defend -> excluded from average
- Even split when all alliance contributors share a base-level label

## Configuration touchpoints

- `lib/config/columns.json`
  - `streamlit_config` labels and metric sections
  - `column_configuration` may affect scoring inputs and defaults

## Audit checklist

1. Confirm formula and constants for `overall_avg` match current season manual.
2. Confirm all `Points Avg` UI surfaces read the intended field.
3. Confirm contribution map and exclusion logic are consistent across all usage points.
4. Confirm sort/ranking logic uses updated metrics after any refactor.
