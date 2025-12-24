# Alliance Selector (allianceSelector.py)

## Overview

The `allianceSelector.py` module provides tools for building and optimizing FRC alliance selections. It helps teams make strategic decisions during alliance selection ceremonies.

## Location

```
lib/allianceSelector.py
```

## Key Features

- **Team Rankings**: Organize teams by performance metrics
- **Alliance Building**: Configure 8 alliances with captain and 2 picks
- **Recommendations**: Suggest optimal picks based on statistics
- **Snake Draft Support**: Handles pick order reversal

## Classes

### Team

Data class representing a team's statistics.

```python
from allianceSelector import Team

team = Team(
    num=7421,
    rank=1,
    total_epa=45.5,
    auto_epa=12.3,
    teleop_epa=28.5,
    endgame_epa=4.7,
    defense=True,
    name="Team Overture",
    robot_valuation=85.2,
    consistency_score=92.0,
    clutch_factor=75,
    death_rate=0.05,
    defended_rate=0.15,
    defense_rate=0.40,
    algae_score=8.5
)
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `num` | `int` | Team number |
| `rank` | `int` | Overall ranking |
| `total_epa` | `float` | Total EPA score |
| `auto_epa` | `float` | Autonomous EPA |
| `teleop_epa` | `float` | Teleop EPA |
| `endgame_epa` | `float` | Endgame EPA |
| `defense` | `bool` | Plays defense |
| `name` | `str` | Team name/nickname |
| `robot_valuation` | `float` | Robot valuation score |
| `consistency_score` | `float` | Consistency rating |
| `clutch_factor` | `float` | Clutch performance |
| `death_rate` | `float` | Robot failure rate |
| `defended_rate` | `float` | How often defended |
| `defense_rate` | `float` | Defense play rate |
| `algae_score` | `float` | Algae scoring average |

### Alliance

Represents a single alliance with captain and picks.

```python
from allianceSelector import Alliance

alliance = Alliance(allianceNumber=1)
alliance.captain = 7421
alliance.captainRank = 1
alliance.pick1 = 254
alliance.pick2 = 148
```

#### Attributes

| Attribute | Type | Description |
|-----------|------|-------------|
| `allianceNumber` | `int` | Alliance number (1-8) |
| `captain` | `int` | Captain team number |
| `captainRank` | `int` | Captain's rank |
| `pick1` | `int` | First pick team number |
| `pick2` | `int` | Second pick team number |

### AllianceSelector

Main class for managing alliance selections.

```python
from allianceSelector import AllianceSelector, teams_from_dicts

# Create from team data
teams = teams_from_dicts([
    {"team": 7421, "total_epa": 45.5, ...},
    {"team": 254, "total_epa": 48.2, ...},
    ...
])

selector = AllianceSelector(teams)
```

#### Methods

```python
# Get available teams for pick
available = selector.get_available_teams(captain_rank=1, pick_type='pick1')

# Get available captains for alliance
captains = selector.get_available_captains(alliance_index=0)

# Set captain for alliance
selector.set_captain(alliance_index=0, team_number=7421)

# Set pick for alliance
selector.set_pick(alliance_index=0, pick_type='pick1', team_number=254)

# Reset all picks
selector.reset_picks()

# Get alliance table for display
table = selector.get_alliance_table()
# Returns: [{"Alliance": 1, "Captain": 7421, "Pick 1": 254, ...}]
```

## Helper Functions

### teams_from_dicts()

Convert dictionary data to Team objects.

```python
from allianceSelector import teams_from_dicts

team_dicts = [
    {"team": 7421, "overall_avg": 45.5, "RobotValuation": 85.2, ...},
    {"team": 254, "overall_avg": 48.2, "RobotValuation": 90.1, ...},
]

teams = teams_from_dicts(team_dicts)
```

## Usage Example

```python
from engine import AnalizadorRobot
from allianceSelector import AllianceSelector, Team

# Load data
analizador = AnalizadorRobot()
analizador.load_csv("scouting_data.csv")

# Get team statistics
stats = analizador.get_detailed_team_stats()

# Create Team objects
teams = []
for rank, stat in enumerate(stats, 1):
    teams.append(Team(
        num=stat['team'],
        rank=rank,
        total_epa=stat.get('overall_avg', 0),
        auto_epa=...,
        teleop_epa=...,
        endgame_epa=...,
        defense=stat.get('defense_rate', 0) >= 0.4,
        name=f"Team {stat['team']}",
        robot_valuation=stat.get('RobotValuation', 0),
        consistency_score=100 - stat.get('overall_std', 20),
        clutch_factor=75,
        death_rate=stat.get('died_rate', 0),
        defended_rate=stat.get('defended_rate', 0),
        defense_rate=stat.get('defense_rate', 0),
        algae_score=stat.get('teleop_algae_avg', 0)
    ))

# Create selector
selector = AllianceSelector(teams)

# Configure alliances
selector.set_captain(0, 7421)  # Alliance 1 captain
selector.set_pick(0, 'pick1', 254)  # Alliance 1 first pick
selector.set_pick(0, 'pick2', 148)  # Alliance 1 second pick

# Get recommendations
available = selector.get_available_teams(captain_rank=2, pick_type='pick1')
print(f"Recommended for Alliance 2: {[t.num for t in available[:3]]}")
```

## Integration with Streamlit

In the Streamlit app:

```python
# Initialize in session state
if 'alliance_selector' not in st.session_state:
    st.session_state.alliance_selector = None

# Create from current data
teams = create_alliance_selector_teams()  # Helper function
st.session_state.alliance_selector = AllianceSelector(teams)

# Use in interface
selector = st.session_state.alliance_selector
for alliance in selector.alliances:
    st.write(f"Alliance {alliance.allianceNumber}: "
             f"Captain {alliance.captain}, "
             f"Picks: {alliance.pick1}, {alliance.pick2}")
```

## Alliance Strategy

The selector considers:
1. **Overall Performance**: Total EPA and robot valuation
2. **Phase Scores**: Auto, teleop, and endgame contributions
3. **Reliability**: Death rate and consistency
4. **Defense Capability**: Defense rate for strategic picks
5. **Synergy**: Complementary strengths across alliance

## Dependencies

- Python dataclasses
- typing module
