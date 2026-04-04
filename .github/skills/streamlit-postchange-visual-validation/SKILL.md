---
name: streamlit-postchange-visual-validation
description: "Run post-change visual verification for Streamlit views after schema or logic edits. Use when validating Team Stats, Detail Stats, Foreshadowing, and Alliance Selector rendering with Chrome DevTools MCP and Playwright MCP."
argument-hint: "Describe what changed and which views must be verified"
---

# Streamlit Post-Change Visual Validation

## Outcome
- Validate that Streamlit UI views still render correctly after code, schema, or scoring changes.
- Provide a clear pass or fail report with evidence and next actions.

## Scope
- This skill is for visual and interaction validation only.
- Keep schema edits and logic propagation in [columns-config-validation](../columns-config-validation/SKILL.md).

## Required Inputs
- What changed (for example: columns, labels, scoring, data parsing, ranking logic).
- Which views must be checked.
- Any specific team or match examples to validate.

## Tooling
- Chrome DevTools MCP: use for browser state inspection, DOM checks, console checks, and quick script evaluation.
- Playwright MCP: use for reliable navigation, clicking, filtering, and repeatable view-level checks.

## Preferred Tool Calls
- Chrome DevTools MCP:
   - open_browser_page
   - mcp_io_github_chr_evaluate_script
   - mcp_io_github_chr_get_console_message (when console message IDs are available)
- Playwright MCP:
   - mcp_microsoft_pla_browser_run_code
   - mcp_microsoft_pla_browser_console_messages

## Procedure
1. Read [project instructions](../../copilot-instructions.md) first.
2. Ensure app is available at a reachable URL, usually local Streamlit.
3. Open the app and run an initial health check:
   - Page loads without blank-state crash.
   - No obvious blocking errors in console using mcp_microsoft_pla_browser_console_messages.
4. Run the view checklist from [view-checklist](./references/view-checklist.md):
   - Team Stats
   - Detail Stats
   - Foreshadowing
   - Alliance Selector
5. For each view, capture evidence:
   - Confirm expected table or chart elements are present.
   - Confirm key fields render with non-empty values where expected.
   - Confirm interactive controls respond correctly.
6. Branching logic:
   - If a view fails to load, record the failing step and blocking error.
   - If values look wrong but view renders, classify as data mapping issue.
   - If interactions fail, classify as UI flow or state sync issue.
7. Report final status with pass or fail per view and concrete reproduction steps.

## Quality Criteria
- No fatal runtime errors while opening target views.
- All required views render at least one valid dataset.
- Expected controls can be used without breaking page state.
- Findings are tied to concrete view names and reproducible steps.

## Output Contract
- Change context summary.
- Environment and URL tested.
- Pass or fail matrix for each required view.
- Console or runtime errors observed.
- Screens or snapshots captured (if available).
- Clear next action list:
  - No issues found, or
  - Suggested fix owner and target module.

## Guardrails
- Preserve project patterns and avoid unrelated edits.
- Do not redefine schema or scoring in this skill.
- Keep checks focused, deterministic, and reproducible.