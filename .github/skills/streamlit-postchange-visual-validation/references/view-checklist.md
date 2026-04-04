# View Checklist

## Global App Health
- App page opens and remains responsive.
- No blocking console errors during initial render.
- Main navigation loads expected sections.

## Team Stats
- Team list or table appears.
- At least one numeric metric is visible.
- Sorting or filtering interaction updates view without errors.

## Detail Stats
- Team selection control is visible.
- Comparison metrics render (table, cards, or charts).
- Switching team updates displayed values.

## Foreshadowing
- Foreshadowing section opens without exceptions.
- Auto and teleop related indicators are present.
- Data values are not entirely empty for known populated teams.

## Alliance Selector
- Alliance selector view loads.
- Team ranking input or selector is interactive.
- Simulation or recommendation output renders after interaction.

## Evidence To Capture
- URL and page state tested.
- List of actions performed in each view.
- Console error messages when failures occur.
- Short pass or fail summary by view.

## Failure Classification
- Render failure: view does not load or crashes.
- Data mapping failure: view loads but key values are wrong or empty.
- Interaction failure: controls present but actions do not update results.