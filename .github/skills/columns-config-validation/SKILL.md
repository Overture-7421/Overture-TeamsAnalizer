---
name: columns-config-validation
description: "Update lib/config/columns.json and safely propagate scouting schema changes through engine and Streamlit views. Use when changing columns config, debugging engine.py or streamlit_app.py after schema edits, and validating Team Stats, Detail Stats, Foreshadowing, or Alliance Selector displays."
argument-hint: "Describe the requested column changes and compatibility expectations"
---

# Columns Config Validation

## When To Use
- You need to add, remove, rename, reorder, or relabel scouting columns.
- You suspect schema updates may break parsing, scoring, or UI rendering.
- You want a full validation pass after column changes.

## Inputs
- Requested column changes.
- Whether backward compatibility is required.
- Any expected display changes in stats or scouting views.

## Procedure
1. Read [project instructions](../../copilot-instructions.md) first.
2. Treat [lib/config/columns.json](../../../lib/config/columns.json) as the authoritative schema.
3. Apply only requested schema changes with minimal, local edits.
4. Trace and fix downstream impacts in:
   - [lib/engine.py](../../../lib/engine.py)
   - [lib/streamlit_app.py](../../../lib/streamlit_app.py)
   - Any directly affected helpers in [lib/](../../../lib/)
5. Run the validation checklist in [validation-checklist](./references/validation-checklist.md).
6. If failures appear, patch code and rerun validation until stable.
7. Keep naming and labels backward-compatible unless explicitly asked to break compatibility.

## Output Contract
- Requested change summary.
- Files changed.
- Debug fixes applied.
- Validation checklist with pass or fail per section.
- Residual risks and manual Streamlit checks.

## Guardrails
- Keep Python changes small and modular.
- Preserve existing lazy-load and caching patterns.
- Do not modify unrelated legacy files.
- If schema changes affect behavior, call out compatibility impact clearly.
