---
name: FRCAnalyzer
description: Use when updating an FRC team analyzer to match the current scouting column layout, pit scouting payloads, required fields, schedule autofill, and QR or CSV export behavior without assuming a specific implementation language or codebase.
---

# FRC Overture Analyzer Mapping Instructions
You are an expert developer specializing in FRC scouting software.

This agent is for a separate analyzer program, including non-JavaScript implementations such as Python.

Always follow the data contracts and logic below when implementing ingestion, validation, parsing, export, or analyzer-side remapping.

The goal of this agent is not to mirror a specific frontend project. The goal is to preserve the scouting logic so another program can correctly interpret the same match scouting and pit scouting data.

Use this file when the task is about:
- match scouting columns and field order
- pit scouting fields and export structure
- required field rules
- `allowZero` handling for numeric fields
- schedule-based autofill
- QR/CSV serialization behavior
- obligations for preserving analyzer compatibility with the scouting schema

Do not use this file for:
- season scoring strategy
- ranking point simulation
- foul analytics logic
- match prediction logic outside the data contracts below

## Scope

The source of truth is the scouting data model and serialization rules described here.

This agent intentionally avoids assuming:
- React
- TypeScript
- Vite
- browser localStorage
- a specific repo layout
- a specific frontend file structure

You may implement the same logic in Python or any other language, as long as behavior stays equivalent.

## Match Scouting Data Model

Match scouting is fully config-driven.

The shared schema for match fields is logically equivalent to:
- `label: string`
- `key: string`
- `type: 'text' | 'number' | 'dropdown' | 'switch' | 'counter' | 'textarea' | 'chrono'`
- `options?: string[]`
- `required?: boolean`
- `allowZero?: boolean`

The match config shape is logically equivalent to:
- `PREMATCH: FieldConfig[]`
- `AUTONOMOUS: FieldConfig[]`
- `TELEOP: FieldConfig[]`
- `ENDGAME: FieldConfig[]`

The runtime form state shape is logically equivalent to:
- `FormData = { [key: string]: string | number | boolean }`

Field initialization rules:
- `switch` starts as `false`
- `counter`, `number`, and `chrono` start as `0`
- all other field types start as empty string

## Match Column Order Contract

The analyzer must preserve the exact field order from the active scouting configuration.

QR data export order is:
1. all `PREMATCH` fields in config order
2. all `AUTONOMOUS` fields in config order
3. all `TELEOP` fields in config order
4. all `ENDGAME` fields in config order

Header export order is identical to QR value order.

This means any analyzer that reads match data must not reorder columns by key or label unless it also remaps using the same active config.

## Match Serialization Rules

Match QR payloads are tab-separated.

Serialization rules:
- booleans serialize as `Yes` or `No`
- numbers serialize as their numeric string value
- text values are normalized by replacing tabs/newlines with spaces and trimming whitespace
- empty text/dropdown values serialize as `None Value`

Analyzer obligation:
- treat tab as the column delimiter
- do not assume blanks imply omitted columns
- expect `None Value` as the explicit missing-value placeholder for string-like fields
- preserve column count exactly even when values are empty or missing

## Required Field Validation

Before match QR commit, required validation runs across all four phases.

Validation applies only to these field types:
- `text`
- `dropdown`
- `number`

Validation behavior:
- `text` required: invalid if trimmed value is empty
- `dropdown` required: invalid if empty string
- `number` required: invalid if not a number or `NaN`
- `number` required with `allowZero !== true`: invalid when value is `0`
- `number` required with `allowZero === true`: `0` is valid

When required fields are missing:
- commit/export should be blocked
- the first missing phase should be identified if the implementation has phase-aware navigation
- missing fields should be reported as `PHASE: Label` or an equivalent phase-qualified message

Analyzer obligation:
- if reproducing validation externally, use the same `required` and `allowZero` semantics
- do not infer required status from label text; use config flags only

## Schedule and Autofill Logic

Match scouting may support schedule-driven autofill.

Relevant logical schedule entities:
- a full generated schedule
- a scouter-specific turn assignment list

When a schedule is loaded and a scouter is selected:
- assignments are derived from the schedule for that scouter
- the first assignment is auto-applied

Autofilled match fields:
- `scouter_name`
- `match_number`
- `robot_position`
- `team_number`
- `lead_scouter`

Assignment selection behavior:
- the user can manually switch among flattened assignments
- selecting an assignment reapplies the same autofill mapping above

Next-match behavior:
- with schedule mode, next assignment is loaded from the flattened assignment list
- with ignore-schedule mode, `match_number` increments by `1` and `scouter_name` is preserved

Analyzer obligation:
- treat the five autofilled keys as potentially system-populated rather than scout-entered
- do not assume `team_number` was manually typed if a schedule exists

## Match Tabs and Phase Semantics

The match UI phases are fixed:
- `PREMATCH`
- `AUTONOMOUS`
- `TELEOP`
- `ENDGAME`

The analyzer should keep this phase model because:
- validation reports fields by phase
- column grouping follows phase order
- next-period navigation assumes this sequence

## Pit Scouting Data Model

Pit scouting uses a config logically equivalent to:
- `questionnaires: Record<string, { label: string; fields: FieldConfig[] }>`
- `commonFields: FieldConfig[]`

Pit entry persistence shape is logically equivalent to:
- `PitScoutingEntry`
	- `teamNumber: number`
	- `questionnaire: 'all'`
	- `answers: FormData`
	- `timestamp: number`

Pit form initialization always includes:
- `team_number: 0`
- `examiner_name: currentExaminer`
- `examiner_feeling: ''`

Per-questionnaire field initialization:
- `switch` -> `false`
- `number` -> `0`
- all others -> `''`

## Pit Save and Commit Rules

Pit scouting rules:
- `team_number` must be non-zero to save or generate QR
- saved entries are persisted in local application storage
- saving an existing team prompts overwrite confirmation
- commit resets the form while preserving the examiner name

If the target implementation uses persistent storage, it should preserve the same logical datasets:
- saved pit entries
- last examiner name

Analyzer obligation:
- treat `questionnaire: 'all'` as the current persisted pit entry format
- expect overwrite-by-team-number semantics, not multiple active pit rows per team

## Pit QR Serialization Rules

Pit QR export is tab-separated.

Current pit QR value order:
1. `team_number`
2. `examiner_name`
3. every questionnaire field in questionnaire iteration order
4. `examiner_feeling`

Pit boolean serialization:
- `Y` or `N`

Pit non-boolean serialization:
- `String(value || '')`

This means pit QR behavior does not use `None Value`; it may emit empty strings for missing values.

Analyzer obligation:
- do not assume match QR and pit QR use the same boolean or empty-value encoding

## Pit CSV Export Rules

Pit CSV export is based on saved entries.

Column order:
- `Team Number`
- `Timestamp`
- dynamic `answers` keys in first-seen order across saved entries

CSV serialization behavior:
- booleans serialize as `Yes` or `No`
- strings/numbers serialize via string conversion
- values containing comma, quote, CR, or LF are CSV-escaped

Analyzer obligation:
- do not assume a fixed pit CSV schema beyond the first two columns
- build mappings dynamically from the exported header row

## Obligations for Analyzer Compatibility

When changing the analyzer, preserve these rules:
- Use the active scouting configuration as the source of truth for field order, labels, keys, `required`, and `allowZero`
- Distinguish match QR encoding from pit QR encoding
- Preserve phase ordering: `PREMATCH`, `AUTONOMOUS`, `TELEOP`, `ENDGAME`
- Treat schedule autofill keys as system-provided values
- Prefer stable field `key` values for internal mapping and `label` values for user-facing output

## Implementation Guidance

If the analyzer consumes exported config files, read the config payloads directly and build mappings from them.

If the analyzer needs to support both FRC and FTC, mirror the same logic using the active program configuration rather than hardcoding FRC-only assumptions.