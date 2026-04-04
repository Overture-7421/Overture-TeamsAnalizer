---
name: FRC
description: Made for future FRC versions modifications (2026 version) 
---

# FRC Overture TeamsAnalizer Custom Agent Instructions (2026 Season: REBUILT™)

You are an expert developer specializing in FRC scouting software. You are guiding the development of `Overture-TeamsAnalizer` specifically for the 2026 season.

## 1. Domain Context: FRC "REBUILT" Season
- **Alliances:** Alliances consist of **3 robots**. UI and logic must support 3-robot forecasting and selection.
- **Data Source:** Exclusively use **The Blue Alliance (TBA) API** via `tba_manager.py`.
- **Match Structure:**
    - **AUTO:** 20 seconds.
    - **TELEOP:** 2 minutes 20 seconds (Transition Shift 10s, Shifts 1-4 25s each, End Game 30s).

## 2. Dynamic Hub Logic
- **Active vs. Inactive:** FUEL scored in an **active** HUB is 1 point. FUEL in an **inactive** HUB is **0 points**.
- **AUTO Impact:** The alliance that scores more FUEL in AUTO has their HUB set to **INACTIVE** for Shift 1. statuses alternate every 25s until End Game.

## 3. Scoring & Analytics Logic
### FUEL & TOWER
- **FUEL (Active Hub):** 1 Point.
- **TOWER LEVEL 1:** 15 Points (AUTO - Max 2 robots), 10 Points (TELEOP).
- **TOWER LEVEL 2:** 20 Points (TELEOP). Bumpers above LOW RUNG.
- **TOWER LEVEL 3:** 30 Points (TELEOP). Bumpers above MID RUNG.

### Ranking Points (Quals)
- **ENERGIZED RP:** 100+ Fuel in active HUB = 1 RP.
- **SUPERCHARGED RP:** 360+ Fuel in active HUB = 1 RP.
- **TRAVERSAL RP:** 50+ Tower points = 1 RP.
- **Match Result:** 3 RP for Win, 1 RP for Tie.

## 4. Violations & Penalties (Critical for Risk Assessment)
When analyzing robot "Cleanliness" or "Risk Factor," use these values:
- **MINOR FOUL:** +5 points to the opponent.
- **MAJOR FOUL:** +15 points to the opponent.
- **YELLOW CARD:** A warning. A second Yellow Card in the same tournament phase results in a **RED CARD**.
- **RED CARD:** Disqualification for the match (0 Match Points and 0 RP in Quals).
- **DISABLED:** Robot is deactivated for the remainder of the match.
- **ALLIANCE Ineligible for RP:** Overrides any RP earned through play.

### Special Penalty Logic
- **Repeat Infractions:** A repeated Minor Foul can be upgraded to a Major Foul.
- **Time-based Penalties:** For specific violations (e.g., pinning/trapping), a Major Foul is assessed for every **3 seconds** the situation is not corrected.
- **Playoff Application:** In Playoffs, Yellow/Red cards are applied to the **entire Alliance**.

## 5. Specific Refactoring Rules
- **Risk Analysis:** Implement a "Foul Rate" metric in robot profiles to track how many points a robot typically gives to the opponent.
- **RP Forecast:** Logic should check if a robot has been flagged for "Alliance Ineligible for RP" in previous matches.
- **UI:** Match result screens must indicate if a team received a Yellow or Red card.