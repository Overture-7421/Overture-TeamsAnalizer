# FRC 2026 REBUILT Scoring Reference

Source documents:
- Official manual URL: https://firstfrc.blob.core.windows.net/frc2026/Manual/2026GameManual.pdf
- Team Update baseline seen during extraction: TU19

Manual sections used:
- Section 6.4.1 HUB Status
- Section 6.5 Scoring
- Section 6.5.3 Point Values (Table 6-4)
- Table 6-5 BONUS RP thresholds

## Core scoring rules

### HUB activity
- FUEL scored in an active HUB is worth points.
- FUEL scored in an inactive HUB is worth zero points.
- During SHIFT windows, one alliance HUB can be inactive based on AUTO result.

### Point values (Table 6-4)

FUEL:
- Active HUB: AUTO `1`, TELEOP `1`
- Inactive HUB: `0`

TOWER:
- LEVEL 1: AUTO `15` (max 2 robots in AUTO), TELEOP `10`
- LEVEL 2: TELEOP `20`
- LEVEL 3: TELEOP `30`

MATCH outcome RP:
- Win: `3 RP`
- Tie: `1 RP`

BONUS RP:
- ENERGIZED RP: active HUB FUEL reaches threshold
- SUPERCHARGED RP: active HUB FUEL reaches threshold
- TRAVERSAL RP: TOWER points reaches threshold

### Regional/District thresholds (Table 6-5)
- ENERGIZED RP: `100`
- SUPERCHARGED RP: `360`
- TRAVERSAL RP: `50`

Note:
- District Championship and Championship thresholds may differ and are announced in Team Updates.
- Validate latest Team Update before finalizing production constants.
