# School System (school_system.py)

## Overview

The `school_system.py` module implements the Honor Roll scoring system for evaluating FRC teams. It combines match performance, pit scouting data, and event observations into a comprehensive ranking.

## Location

```
lib/school_system.py
```

## Key Features

- **Multi-component Scoring**: Match performance, pit scouting, during event
- **Competency Tracking**: Required competencies and subcompetencies
- **Curved Scoring**: Apply grade curves to raw scores
- **TierList Export**: Generate TierList-compatible output
- **Feedback Aggregation**: Combine scouting comments

## Classes

### TeamScoring

Main class for the Honor Roll system.

```python
from school_system import TeamScoring

system = TeamScoring()
```

#### Adding Teams

```python
# Add a team
system.add_team("7421")

# Add multiple teams
for team_num in ["7421", "254", "148"]:
    system.add_team(team_num)
```

#### Updating Scores

```python
# Match performance scores
system.update_autonomous_score("7421", 85.0)
system.update_teleop_score("7421", 92.0)
system.update_endgame_score("7421", 78.0)

# Pit scouting scores
system.update_electrical_score("7421", 90.0)
system.update_mechanical_score("7421", 88.0)
system.update_driver_station_score("7421", 95.0)
system.update_tools_score("7421", 70.0)
system.update_spare_parts_score("7421", 65.0)

# During event scores
system.update_organization_score("7421", 82.0)
system.update_collaboration_score("7421", 90.0)
```

#### Competencies

```python
# Update competencies
system.update_competency("7421", "pit_complete", True)
system.update_competency("7421", "match_complete", True)
system.update_competency("7421", "during_complete", True)

# Get competency status
status = system.get_team_competencies_status("7421")
# Returns: {
#     "competencies": {"pit_complete": True, ...},
#     "subcompetencies": {...},
#     "counts": {"competencies": 3, "subcompetencies": 2}
# }
```

#### Configuration

```python
# Set scoring weights (must sum to 1.0)
system.set_scoring_weights(
    match_weight=0.5,
    pit_weight=0.3,
    event_weight=0.2
)

# Set competency multipliers
system.competencies_multiplier = 10
system.subcompetencies_multiplier = 5

# Set minimum requirements
system.min_competencies_count = 3
system.min_subcompetencies_count = 2
system.min_honor_roll_score = 60.0
```

#### Calculating Scores

```python
# Calculate all team scores
system.calculate_all_scores()

# Calculate competencies score for a team
comp_count, subcomp_count, rp = system.calculate_competencies_score("7421")
```

#### Rankings

```python
# Get honor roll ranking
rankings = system.get_honor_roll_ranking()
# Returns: [(team_num, result), ...]

# Get disqualified teams
disqualified = system.get_disqualified_teams()
# Returns: [(team_num, reason), ...]

# Get summary stats
summary = system.get_summary_stats()
# Returns: {
#     "total_teams": 50,
#     "qualified_teams": 45,
#     "disqualified_teams": 5,
#     "avg_score": 72.5
# }
```

#### Team Details

```python
# Get score breakdown
breakdown = system.get_team_score_breakdown("7421")
# Returns: {
#     "match_performance": {"autonomous": 85, "teleop": 92, "endgame": 78, "total": 85},
#     "pit_scouting": {"electrical": 90, "mechanical": 88, ..., "total": 81.6},
#     "during_event": {"organization": 82, "collaboration": 90, "total": 86},
#     "final_feedback": "...",
#     "...": ...
# }
```

### Competency Labels

Get human-readable competency labels:

```python
comp_labels = TeamScoring.get_competency_labels()
# Returns: {"pit_complete": "Pit Scouting Complete", ...}

subcomp_labels = TeamScoring.get_subcompetency_labels()
# Returns: {"autonomous_focus": "Strong Autonomous", ...}
```

### CalculatedScore

Result object for team scores.

```python
result = system.calculated_scores.get("7421")

result.honor_roll_score  # Raw score
result.curved_score      # After curve
result.final_points      # Integer points
result.match_performance_score
result.pit_scouting_score
result.during_event_score
result.final_feedback    # Aggregated feedback
result.qualified         # Meets requirements
```

## Scoring Formula

```
Honor Roll Score = (Match × Match_Weight) + (Pit × Pit_Weight) + (Event × Event_Weight)

Match Score = (Auto + Teleop + Endgame) / 3
Pit Score = (Electrical + Mechanical + DriverStation + Tools + SpareParts) / 5
Event Score = (Organization + Collaboration) / 2

Final Points = Curved_Score + (Competencies × Comp_Multiplier) + (Subcompetencies × Subcomp_Multiplier)
```

## Integration with Exam Data

```python
from exam_integrator import ExamDataIntegrator

integrator = ExamDataIntegrator()
integrator.integrate_programming_exam("programming_results.csv")
integrator.integrate_mechanical_exam("mechanical_results.csv")
integrator.apply_to_scoring_system(system)

system.calculate_all_scores()
```

## TierList Export

The Honor Roll system supports export to TierList format:

```python
rankings = system.get_honor_roll_ranking()
disqualified = system.get_disqualified_teams()

# Teams are distributed to tiers:
# - 1st Pick: Top third of qualified teams
# - 2nd Pick: Middle third
# - 3rd Pick: Bottom third
# - Defense Pick: Teams with defense > 0
# - "-" Tier: Disqualified teams
```

## Behavior Reports

Track team behavior observations:

```python
from school_system import BehaviorReportType

# Add behavior observation
system.add_behavior_report("7421", BehaviorReportType.POSITIVE, "Great sportsmanship")
system.add_behavior_report("7421", BehaviorReportType.NEGATIVE, "Late to matches")

# Get reports
reports = system.get_behavior_reports("7421")
```

## Dependencies

- `dataclasses` - Data structures
- `typing` - Type hints
- `collections` - Counter utilities
