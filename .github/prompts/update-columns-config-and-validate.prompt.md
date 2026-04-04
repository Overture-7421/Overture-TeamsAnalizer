---
description: "Change scouting columns config and verify engine plus Streamlit logic stay stable"
name: "Update Columns Config And Validate"
argument-hint: "Describe the exact column changes to apply"
agent: "agent"
---

Related skill: `columns-config-validation`. Load and follow [skill instructions](../skills/columns-config-validation/SKILL.md).
Follow-up skill for UI checks: [streamlit-postchange-visual-validation](../skills/streamlit-postchange-visual-validation/SKILL.md).

Read [project instructions](../copilot-instructions.md) first and follow them strictly.

Use the prompt arguments as the requested column changes.

Goal: apply column configuration changes safely and debug logic breakage; run visual verification as a dedicated follow-up workflow.

Required workflow:
1. Treat [lib/config/columns.json](../../lib/config/columns.json) as the authoritative schema file.
2. Implement only the requested column changes (add/remove/rename/reorder/label updates) with minimal, localized edits.
3. Debug and fix any breakage caused by schema changes, especially in [lib/engine.py](../../lib/engine.py) and [lib/streamlit_app.py](../../lib/streamlit_app.py).
4. Verify the app does not collapse after changes:
   - Data loading and parsing still work.
   - Stats computation still runs.
   - No obvious runtime errors from updated columns.
5. Keep backward compatibility unless the requested schema change explicitly breaks it.
6. Hand off visual verification to [streamlit-postchange-visual-validation](../skills/streamlit-postchange-visual-validation/SKILL.md).

Output format:
- Summary of requested column changes applied.
- Files changed.
- Debug fixes made (if any).
- Validation checklist with pass/fail for:
  - Engine logic
  - Streamlit app stability
- Visual verification handoff status.
- Remaining risks or manual checks to run in Streamlit.

Constraints:
- Keep changes small and modular.
- Do not edit unrelated legacy files unless required.
- Prefer existing project patterns and labels.