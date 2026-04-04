---
name: columns-config-validation
description: "Update lib/config/columns.json and safely propagate scouting schema changes through engine and Streamlit logic. Use when changing columns config and debugging engine.py or streamlit_app.py after schema edits."
argument-hint: "Describe the requested column changes and compatibility expectations"
---

# Columns Config Validation

## When To Use
- You need to add, remove, rename, reorder, or relabel scouting columns.
- You suspect schema updates may break parsing or scoring logic.
- You need schema and logic propagation before UI-specific verification.

## Inputs
- Requested column changes.
- Whether backward compatibility is required.
- Any expected downstream logic impact.

## Procedure
1. Read [project instructions](../../copilot-instructions.md) first.
2. Treat [lib/config/columns.json](../../../lib/config/columns.json) as the authoritative schema.
3. Apply only requested schema changes with minimal, local edits.
4. Regenerate schema-driven fixtures after every columns change:
   - Run [scripts/generate_frc_2026_test_data.py](../../../scripts/generate_frc_2026_test_data.py).
   - Confirm [archivos ejemplo/default_scouting.csv](../../../archivos%20ejemplo/default_scouting.csv) header matches `headers` in [lib/config/columns.json](../../../lib/config/columns.json).
   - Confirm [data/default_scouting.csv](../../../data/default_scouting.csv) is refreshed from the same run.
5. Trace and fix downstream impacts in:
   - [lib/engine.py](../../../lib/engine.py)
   - [lib/streamlit_app.py](../../../lib/streamlit_app.py)
   - Any directly affected helpers in [lib/](../../../lib/)
6. Run the validation checklist in [validation-checklist](./references/validation-checklist.md).
7. If failures appear, patch code and rerun validation until stable.
8. Keep naming and labels backward-compatible unless explicitly asked to break compatibility.
9. After schema and logic are stable, hand off UI checks to [streamlit-postchange-visual-validation](../streamlit-postchange-visual-validation/SKILL.md).

## Output Contract
- Requested change summary.
- Files changed.
- Debug fixes applied.
- Logic validation checklist with pass or fail per section.
- UI validation handoff recommendation.

## Guardrails
- Keep Python changes small and modular.
- Preserve existing lazy-load and caching patterns.
- Do not modify unrelated legacy files.
- If schema changes affect behavior, call out compatibility impact clearly.
