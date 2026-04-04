---
name: frc-avg-points-logic-check
description: Validate and fix FRC scoring metric logic for Points Avg and Avg Pts Contribution, grounded in the current season game manual. Use this skill whenever the user mentions average points, overall_avg, points contribution, post-match contribution labels, scoring mismatch, alliance ranking anomalies, or asks to align scoring code with the FRC game manual (especially REBUILT 2026).
---

# FRC Avg Points Logic Check

Audit and correct scoring logic for two high-impact metrics:
- `Points Avg` (usually backed by `overall_avg`)
- `Avg Pts Contribution` (from post-match qualitative contribution labels)

This skill is repository-aware for Overture Teams Analyzer and season-aware for FRC manual updates.

## Scope

Use this workflow when the task involves any of:
- Wrong `Points Avg` values in dashboards, ranking tables, or detail views
- Wrong `Avg Pts Contribution` values in post-match views
- Mismatch between code scoring and official FRC manual scoring
- Rebuild of scoring logic after season transition or Team Updates

## Step 1: Resolve season context first

1. Detect the target season year from user context or data files.
2. Prefer user-provided manual artifact (PDF) when available.
3. If missing, query web using: `frc <year> game manual`.
4. Use the first official result from FIRST resources (typically `firstinspires.org` or `firstfrc.blob.core.windows.net`).
5. Extract the scoring table and RP threshold table before touching formulas.

Why: metric logic must track season-specific game rules. Do not patch formulas without manual grounding.

## Step 2: Build a scoring matrix from the manual

Create a compact matrix with:
- Action
- AUTO points
- TELEOP points
- Constraints (caps, timing, eligibility)
- RP thresholds

For FRC 2026 REBUILT, use `references/frc-2026-rebuilt-scoring.md` as baseline.

## Step 3: Audit repository mapping for both metrics

Read `references/repo-metrics-map.md` and validate these paths in code:
- `lib/engine.py` for `overall_avg` computation path
- `lib/streamlit_app.py` for `Points Avg` presentation
- `lib/streamlit_app.py` for `get_pm_contribution_points` and `get_pm_avg_pts_contribution`
- `lib/config/columns.json` for column selection and streamlit config labels

## Step 4: Validate Points Avg logic with explicit invariants

Check these invariants:
1. Per-match score uses the current-season scoring matrix (not stale constants).
2. AUTO and TELEOP values are not double-counted.
3. Inactive-HUB or zero-point states are represented as zero, not omitted unless explicitly intended.
4. Exclusions from averaging are intentional and documented.
5. Denominator of average matches included match scores.
6. Any fallback scoring path is season-consistent with current config schema.

If invariant fails, propose exact patch and test case.

## Step 5: Validate Avg Pts Contribution logic with explicit invariants

For contribution label mapping:
1. Label-to-percentage map matches intended rubric.
2. `Dedicated to passing` and `Dedicated to defend` are excluded from average denominator.
3. Even split rule is applied only when all alliance members share base-level labels.
4. Alliance points source is correct by alliance side and slot index.
5. Contribution average is arithmetic mean of included per-match contributions.
6. Contribution std uses sample standard deviation (`n-1`) and returns `0.0` when fewer than 2 values.

## Step 6: Produce output in this format

## Manual Scoring Matrix
- List extracted rules with source references.

## Findings (highest severity first)
- File and symbol
- Current behavior
- Expected behavior
- Impact on rankings/selection

## Proposed Fixes
- Minimal patch per finding
- Why this fix aligns with manual and repository design

## Verification
- At least 2 concrete examples with expected numeric outputs
- Confirm both `Points Avg` and `Avg Pts Contribution`

## Repo-specific notes for this project

- `Points Avg` is shown in several tables/charts and often proxies `overall_avg`.
- `Avg Pts Contribution` derives from post-match qualitative labels and alliance score context.
- Any changes should preserve existing naming and table labels unless the user asks to rename.
- When modifying scoring, also update project documentation and changelog entries if applicable.

## Common failure patterns

- Season constants left from old game while UI labels were updated
- Percent contribution map changed in one function but not another
- Exclusion labels removed from one path and kept in another
- Ranking sorts still using stale fields after scoring refactor

## Example trigger prompts

- "My Points Avg is too low compared to match videos, check scoring logic against 2026 manual."
- "Avg Pts Contribution is wrong for teams marked Dedicated to defend, can you audit it?"
- "Please align overall_avg and contribution columns with current FRC game manual thresholds."
