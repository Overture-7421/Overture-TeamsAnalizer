# Foreshadowing (foreshadowing.py)

## Overview

The `foreshadowing.py` module provides match prediction and simulation capabilities. It uses Monte Carlo simulation to predict match outcomes based on team performance statistics.

## Location

```
lib/foreshadowing.py
```

## Key Features

- **Monte Carlo Simulation**: Statistical match outcome prediction
- **Team Performance Extraction**: Convert scouting data to performance profiles
- **Score Breakdown**: Detailed scoring by game element
- **Win Probability**: Calculate alliance win chances
- **RP Prediction**: Ranking point estimations

## Classes

### TeamStatsExtractor

Extracts team performance profiles from scouting data.

```python
from foreshadowing import TeamStatsExtractor
from engine import AnalizadorRobot

analizador = AnalizadorRobot()
analizador.load_csv("scouting_data.csv")

extractor = TeamStatsExtractor(analizador)
performance = extractor.extract_team_performance("7421")
```

#### TeamPerformance Object

```python
performance.team_number   # "7421"
performance.auto_L1       # Auto coral L1 average
performance.auto_L2       # Auto coral L2 average
performance.auto_L3       # Auto coral L3 average
performance.auto_L4       # Auto coral L4 average
performance.teleop_L1     # Teleop coral L1 average
performance.teleop_L2     # Teleop coral L2 average
performance.teleop_L3     # Teleop coral L3 average
performance.teleop_L4     # Teleop coral L4 average
performance.auto_processor    # Auto processor algae
performance.teleop_processor  # Teleop processor algae
performance.teleop_net        # Net algae average
performance.p_leave_auto_zone # Probability of leaving auto zone
performance.p_cooperation     # Probability of cooperation
performance.p_park            # Probability of parking
performance.p_shallow_climb   # Probability of shallow climb
performance.p_deep_climb      # Probability of deep climb

# Calculate expected climb points
climb_pts = performance.expected_climb_points()
```

### MatchSimulator

Simulates match outcomes using Monte Carlo methods.

```python
from foreshadowing import MatchSimulator, TeamStatsExtractor

extractor = TeamStatsExtractor(analizador)
simulator = MatchSimulator()

# Extract performance for each team
red_team1 = extractor.extract_team_performance("7421")
red_team2 = extractor.extract_team_performance("254")
red_team3 = extractor.extract_team_performance("148")

blue_team1 = extractor.extract_team_performance("1114")
blue_team2 = extractor.extract_team_performance("118")
blue_team3 = extractor.extract_team_performance("2056")

# Run simulation
prediction = simulator.simulate_match(
    red_alliance=[red_team1, red_team2, red_team3],
    blue_alliance=[blue_team1, blue_team2, blue_team3],
    num_simulations=5000
)
```

### MatchPrediction

Result object containing prediction data.

```python
prediction.red_score           # Predicted red alliance score
prediction.blue_score          # Predicted blue alliance score
prediction.red_win_probability # Red win probability (0-1)
prediction.blue_win_probability # Blue win probability (0-1)
prediction.tie_probability     # Tie probability (0-1)
prediction.red_rp              # Predicted red ranking points
prediction.blue_rp             # Predicted blue ranking points
prediction.red_breakdown       # Detailed red score breakdown
prediction.blue_breakdown      # Detailed blue score breakdown
```

### Score Breakdown

```python
breakdown = prediction.red_breakdown

# Coral scores by level
breakdown['coral_scores']      # {"L1": 12, "L2": 18, "L3": 24, "L4": 35}
breakdown['auto_coral']        # {"L1": 3, "L2": 4, "L3": 6, "L4": 7}
breakdown['teleop_coral']      # {"L1": 9, "L2": 14, "L3": 18, "L4": 28}

# Algae scores
breakdown['processor_algae']   # {"auto": 6, "teleop": 18}
breakdown['net_algae']         # 12

# Points breakdown
breakdown['coral_points']      # 89
breakdown['algae_points']      # 36
breakdown['climb_points']      # 24

# Climb details
breakdown['climb_scores']      # [("7421", "deep", 12), ("254", "shallow", 6), ...]

# Team metrics
breakdown['teams_left_auto_zone']  # 3
breakdown['cooperation_achieved']   # True/False
```

## Usage Example

```python
from engine import AnalizadorRobot
from foreshadowing import TeamStatsExtractor, MatchSimulator

# Load data
analizador = AnalizadorRobot()
analizador.load_csv("scouting_data.csv")

# Create extractor and simulator
extractor = TeamStatsExtractor(analizador)
simulator = MatchSimulator()

# Define alliances
red_teams = ["7421", "254", "148"]
blue_teams = ["1114", "118", "2056"]

# Extract performances
red_perf = [extractor.extract_team_performance(t) for t in red_teams]
blue_perf = [extractor.extract_team_performance(t) for t in blue_teams]

# Run quick prediction (1000 iterations)
quick_pred = simulator.simulate_match(red_perf, blue_perf, num_simulations=1000)
print(f"Quick: Red {quick_pred.red_score:.1f} - Blue {quick_pred.blue_score:.1f}")

# Run Monte Carlo (5000 iterations for more accuracy)
mc_pred = simulator.simulate_match(red_perf, blue_perf, num_simulations=5000)
print(f"Monte Carlo: Red {mc_pred.red_score:.1f} - Blue {mc_pred.blue_score:.1f}")
print(f"Win Probability: Red {mc_pred.red_win_probability*100:.1f}%")
```

## Integration with Streamlit

The Foreshadowing page in the Streamlit app:

```python
# Alliance selection
red_teams = st.multiselect("Red Alliance", team_options)
blue_teams = st.multiselect("Blue Alliance", team_options)

# Simulation
if st.button("Run Prediction"):
    extractor = TeamStatsExtractor(st.session_state.analizador)
    simulator = MatchSimulator()
    
    red_perf = [extractor.extract_team_performance(t) for t in red_teams]
    blue_perf = [extractor.extract_team_performance(t) for t in blue_teams]
    
    prediction = simulator.simulate_match(red_perf, blue_perf, num_simulations=5000)
    
    # Display results
    st.metric("Red Score", f"{prediction.red_score:.1f}")
    st.metric("Blue Score", f"{prediction.blue_score:.1f}")
    st.metric("Red Win %", f"{prediction.red_win_probability*100:.1f}%")
```

## Simulation Details

### Monte Carlo Method

1. For each simulation iteration:
   - Sample coral counts from distributions based on averages
   - Sample algae placement outcomes
   - Sample climb results from probabilities
   - Calculate total score

2. Aggregate results:
   - Average scores across all iterations
   - Count wins/losses/ties for probability
   - Sum expected RP

### Randomness

The simulator uses random sampling:
- Coral: Poisson distribution around average
- Climb: Bernoulli trial with climb probabilities
- Cooperation: Probability-based

## Dependencies

- `random` - Random number generation
- `statistics` - Statistical calculations
- `dataclasses` - Data structures
