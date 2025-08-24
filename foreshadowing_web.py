"""Foreshadowing (Match Prediction) System - Web Compatible Version

Permite ingresar 3 equipos por alianza (Red / Blue) y predecir puntajes
basados en valores configurables para cada tipo de acción.

Reglas provistas por el usuario:
  - Coral Levels:
       L1: 3 puntos Auto / 2 TeleOp
       L2: 4 puntos Auto / 3 TeleOp
       L3: 6 puntos Auto / 4 TeleOp
       L4: 7 puntos Auto / 5 TeleOp
  - Processor: 6 puntos (Auto y TeleOp) *además el otro equipo gana 4 puntos* (swing opcional)
  - Net: 4 puntos (TeleOp)
  - Climb (endgame): Parked=2, Shallow=6, Deep=12
  - Coopertition Bonus: >=2 ALGAE en cada PROCESSOR => indicador (no RP directo)
  - AUTO RP: todos los robots dejan zona inicial + >=1 CORAL en Auto
  - CORAL RP: >=7 CORAL por nivel (sin coop) ó >=7 en 3 niveles (con coop)
  - Win=3 RP, Tie=1 RP, Loss=0 RP

Este módulo es autónomo y web-compatible.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Callable, Optional
import math, random
import numpy as np


# --------------------------- Data Models ------------------------------------ #

@dataclass
class ScoringConfig:
    coral_auto: Dict[str, int] = field(default_factory=lambda: {"L1": 3, "L2": 4, "L3": 6, "L4": 7})
    coral_teleop: Dict[str, int] = field(default_factory=lambda: {"L1": 2, "L2": 3, "L3": 4, "L4": 5})
    processor_auto: int = 6
    processor_teleop: int = 6
    processor_opponent_gain: int = 4  # Puntos que gana el oponente (swing)
    net_teleop: int = 4
    climb_points: Dict[str, int] = field(default_factory=lambda: {"none": 0, "park": 2, "shallow": 6, "deep": 12})
    enable_processor_swing: bool = True

    def clone(self) -> 'ScoringConfig':
        return ScoringConfig(
            coral_auto=self.coral_auto.copy(),
            coral_teleop=self.coral_teleop.copy(),
            processor_auto=self.processor_auto,
            processor_teleop=self.processor_teleop,
            processor_opponent_gain=self.processor_opponent_gain,
            net_teleop=self.net_teleop,
            climb_points=self.climb_points.copy(),
            enable_processor_swing=self.enable_processor_swing
        )

@dataclass
class TeamPerformance:
    team: str
    auto_L1: float = 0.0
    auto_L2: float = 0.0
    auto_L3: float = 0.0
    auto_L4: float = 0.0
    tele_L1: float = 0.0
    tele_L2: float = 0.0
    tele_L3: float = 0.0
    tele_L4: float = 0.0
    auto_processor: float = 0.0
    tele_processor: float = 0.0
    tele_net: float = 0.0
    climb_dist: Dict[str, float] = field(default_factory=lambda: {"none": 0.0, "park": 0.0, "shallow": 0.0, "deep": 0.0})
    best_climb: str = "none"
    p_auto: float = 0.5
    coop_prob: float = 0.3

    def __post_init__(self):
        # Normalize climb distribution
        total = sum(self.climb_dist.values())
        if total > 0:
            for k in self.climb_dist:
                self.climb_dist[k] /= total
        else:
            self.climb_dist = {"none": 1.0, "park": 0.0, "shallow": 0.0, "deep": 0.0}

@dataclass
class MatchResult:
    red_teams: List[TeamPerformance]
    blue_teams: List[TeamPerformance]
    red_score: float
    blue_score: float
    red_details: Dict
    blue_details: Dict
    config: ScoringConfig


# --------------------------- Core Logic ------------------------------------ #

def compute_team_stats(analizador, team_number: str) -> TeamPerformance:
    """Compute team performance stats from the analizador data"""
    team_data = analizador.get_team_data_grouped().get(team_number, [])
    if not team_data:
        return TeamPerformance(team=team_number)
    
    # Map column names to extract data
    col_indices = analizador._column_indices
    
    def get_avg_for_column(col_name: str) -> float:
        values = []
        col_idx = col_indices.get(col_name)
        if col_idx is not None:
            for row in team_data:
                if col_idx < len(row):
                    try:
                        values.append(float(row[col_idx]))
                    except (ValueError, TypeError):
                        pass
        return sum(values) / len(values) if values else 0.0
    
    # Extract performance data
    perf = TeamPerformance(team=team_number)
    
    # Auto coral levels
    perf.auto_L1 = get_avg_for_column("Coral L1 (Auto)")
    perf.auto_L2 = get_avg_for_column("Coral L2 (Auto)")
    perf.auto_L3 = get_avg_for_column("Coral L3 (Auto)")
    perf.auto_L4 = get_avg_for_column("Coral L4 (Auto)")
    
    # Teleop coral levels
    perf.tele_L1 = get_avg_for_column("Coral L1 (Teleop)")
    perf.tele_L2 = get_avg_for_column("Coral L2 (Teleop)")
    perf.tele_L3 = get_avg_for_column("Coral L3 (Teleop)")
    perf.tele_L4 = get_avg_for_column("Coral L4 (Teleop)")
    
    # Processor
    perf.auto_processor = get_avg_for_column("Processor Algae (Auto)")
    perf.tele_processor = get_avg_for_column("Processor Algae (Teleop)")
    
    # Net (teleop only)
    perf.tele_net = get_avg_for_column("Barge Algae (Teleop)")
    
    # Auto probability (moved in auto)
    moved_auto = get_avg_for_column("Moved (Auto)")
    perf.p_auto = moved_auto if moved_auto > 0 else 0.5
    
    # Climb distribution (simplified)
    end_pos_values = []
    end_pos_idx = col_indices.get("End Position")
    if end_pos_idx is not None:
        for row in team_data:
            if end_pos_idx < len(row):
                val = row[end_pos_idx].strip().lower()
                end_pos_values.append(val)
    
    # Calculate climb distribution
    climb_counts = {"none": 0, "park": 0, "shallow": 0, "deep": 0}
    for val in end_pos_values:
        if "deep" in val or "climb" in val:
            climb_counts["deep"] += 1
        elif "shallow" in val:
            climb_counts["shallow"] += 1
        elif "park" in val:
            climb_counts["park"] += 1
        else:
            climb_counts["none"] += 1
    
    total_climbs = sum(climb_counts.values())
    if total_climbs > 0:
        for k in climb_counts:
            perf.climb_dist[k] = climb_counts[k] / total_climbs
    
    # Best climb
    best_climb_key = max(perf.climb_dist.keys(), key=lambda k: perf.climb_dist[k])
    perf.best_climb = best_climb_key
    
    # Cooperation probability (simplified)
    perf.coop_prob = min(0.8, (perf.auto_processor + perf.tele_processor) / 10.0)
    
    return perf

def simulate_team_performance(team: TeamPerformance, config: ScoringConfig) -> Dict:
    """Simulate a single team's performance in a match"""
    result = {
        "auto_score": 0.0,
        "tele_score": 0.0,
        "climb_score": 0.0,
        "total_score": 0.0,
        "coral_breakdown": {"L1": 0, "L2": 0, "L3": 0, "L4": 0},
        "auto_success": False,
        "climb_result": "none"
    }
    
    # Auto performance
    if random.random() < team.p_auto:
        result["auto_success"] = True
        # Coral scoring in auto
        auto_L1 = max(0, int(np.random.poisson(team.auto_L1)))
        auto_L2 = max(0, int(np.random.poisson(team.auto_L2)))
        auto_L3 = max(0, int(np.random.poisson(team.auto_L3)))
        auto_L4 = max(0, int(np.random.poisson(team.auto_L4)))
        
        result["coral_breakdown"]["L1"] += auto_L1
        result["coral_breakdown"]["L2"] += auto_L2
        result["coral_breakdown"]["L3"] += auto_L3
        result["coral_breakdown"]["L4"] += auto_L4
        
        result["auto_score"] += (auto_L1 * config.coral_auto["L1"] +
                                auto_L2 * config.coral_auto["L2"] +
                                auto_L3 * config.coral_auto["L3"] +
                                auto_L4 * config.coral_auto["L4"])
    
    # Teleop performance
    tele_L1 = max(0, int(np.random.poisson(team.tele_L1)))
    tele_L2 = max(0, int(np.random.poisson(team.tele_L2)))
    tele_L3 = max(0, int(np.random.poisson(team.tele_L3)))
    tele_L4 = max(0, int(np.random.poisson(team.tele_L4)))
    
    result["coral_breakdown"]["L1"] += tele_L1
    result["coral_breakdown"]["L2"] += tele_L2
    result["coral_breakdown"]["L3"] += tele_L3
    result["coral_breakdown"]["L4"] += tele_L4
    
    result["tele_score"] += (tele_L1 * config.coral_teleop["L1"] +
                            tele_L2 * config.coral_teleop["L2"] +
                            tele_L3 * config.coral_teleop["L3"] +
                            tele_L4 * config.coral_teleop["L4"])
    
    # Net scoring
    net_score = max(0, int(np.random.poisson(team.tele_net)))
    result["tele_score"] += net_score * config.net_teleop
    
    # Processor scoring
    auto_processor = max(0, int(np.random.poisson(team.auto_processor)))
    tele_processor = max(0, int(np.random.poisson(team.tele_processor)))
    result["auto_score"] += auto_processor * config.processor_auto
    result["tele_score"] += tele_processor * config.processor_teleop
    
    # Climb performance
    climb_choice = random.choices(
        list(team.climb_dist.keys()),
        weights=list(team.climb_dist.values())
    )[0]
    result["climb_result"] = climb_choice
    result["climb_score"] = config.climb_points.get(climb_choice, 0)
    
    result["total_score"] = result["auto_score"] + result["tele_score"] + result["climb_score"]
    
    return result

def simulate_match_points(red_teams: List[TeamPerformance], blue_teams: List[TeamPerformance], 
                         config: ScoringConfig, num_simulations: int = 1000) -> Dict:
    """Simulate multiple matches and return statistics"""
    red_scores = []
    blue_scores = []
    
    for _ in range(num_simulations):
        red_total = 0.0
        blue_total = 0.0
        
        # Simulate red alliance
        for team in red_teams:
            team_result = simulate_team_performance(team, config)
            red_total += team_result["total_score"]
        
        # Simulate blue alliance
        for team in blue_teams:
            team_result = simulate_team_performance(team, config)
            blue_total += team_result["total_score"]
        
        red_scores.append(red_total)
        blue_scores.append(blue_total)
    
    return {
        "red_mean": sum(red_scores) / len(red_scores),
        "blue_mean": sum(blue_scores) / len(blue_scores),
        "red_std": math.sqrt(sum((x - sum(red_scores) / len(red_scores))**2 for x in red_scores) / len(red_scores)),
        "blue_std": math.sqrt(sum((x - sum(blue_scores) / len(blue_scores))**2 for x in blue_scores) / len(blue_scores)),
        "red_samples": red_scores,
        "blue_samples": blue_scores,
        "red_win_prob": sum(1 for r, b in zip(red_scores, blue_scores) if r > b) / len(red_scores),
        "blue_win_prob": sum(1 for r, b in zip(red_scores, blue_scores) if b > r) / len(red_scores),
        "tie_prob": sum(1 for r, b in zip(red_scores, blue_scores) if abs(r - b) < 1) / len(red_scores)
    }

def predict_match(analizador, red_team_numbers: List[str], blue_team_numbers: List[str], 
                 config: Optional[ScoringConfig] = None) -> Dict:
    """Main prediction function"""
    if config is None:
        config = ScoringConfig()
    
    # Get team performances
    red_teams = [compute_team_stats(analizador, team) for team in red_team_numbers]
    blue_teams = [compute_team_stats(analizador, team) for team in blue_team_numbers]
    
    # Calculate expected values
    red_stats = {
        "teams": [],
        "agg_total": {"L1": 0, "L2": 0, "L3": 0, "L4": 0},
        "agg_auto": {"L1": 0, "L2": 0, "L3": 0, "L4": 0},
        "expected_climb_points": 0.0
    }
    
    blue_stats = {
        "teams": [],
        "agg_total": {"L1": 0, "L2": 0, "L3": 0, "L4": 0},
        "agg_auto": {"L1": 0, "L2": 0, "L3": 0, "L4": 0},
        "expected_climb_points": 0.0
    }
    
    # Process red teams
    for team in red_teams:
        team_dict = {
            "team": team.team,
            "auto_L1": team.auto_L1,
            "auto_L2": team.auto_L2,
            "auto_L3": team.auto_L3,
            "auto_L4": team.auto_L4,
            "tele_L1": team.tele_L1,
            "tele_L2": team.tele_L2,
            "tele_L3": team.tele_L3,
            "tele_L4": team.tele_L4,
            "climb_dist": team.climb_dist,
            "best_climb": team.best_climb,
            "p_auto": team.p_auto,
            "coop_prob": team.coop_prob
        }
        red_stats["teams"].append(team_dict)
        
        # Aggregate stats
        red_stats["agg_total"]["L1"] += team.auto_L1 + team.tele_L1
        red_stats["agg_total"]["L2"] += team.auto_L2 + team.tele_L2
        red_stats["agg_total"]["L3"] += team.auto_L3 + team.tele_L3
        red_stats["agg_total"]["L4"] += team.auto_L4 + team.tele_L4
        
        red_stats["agg_auto"]["L1"] += team.auto_L1
        red_stats["agg_auto"]["L2"] += team.auto_L2
        red_stats["agg_auto"]["L3"] += team.auto_L3
        red_stats["agg_auto"]["L4"] += team.auto_L4
        
        # Expected climb points
        for climb_type, prob in team.climb_dist.items():
            red_stats["expected_climb_points"] += prob * config.climb_points.get(climb_type, 0)
    
    # Process blue teams (similar to red)
    for team in blue_teams:
        team_dict = {
            "team": team.team,
            "auto_L1": team.auto_L1,
            "auto_L2": team.auto_L2,
            "auto_L3": team.auto_L3,
            "auto_L4": team.auto_L4,
            "tele_L1": team.tele_L1,
            "tele_L2": team.tele_L2,
            "tele_L3": team.tele_L3,
            "tele_L4": team.tele_L4,
            "climb_dist": team.climb_dist,
            "best_climb": team.best_climb,
            "p_auto": team.p_auto,
            "coop_prob": team.coop_prob
        }
        blue_stats["teams"].append(team_dict)
        
        # Aggregate stats
        blue_stats["agg_total"]["L1"] += team.auto_L1 + team.tele_L1
        blue_stats["agg_total"]["L2"] += team.auto_L2 + team.tele_L2
        blue_stats["agg_total"]["L3"] += team.auto_L3 + team.tele_L3
        blue_stats["agg_total"]["L4"] += team.auto_L4 + team.tele_L4
        
        blue_stats["agg_auto"]["L1"] += team.auto_L1
        blue_stats["agg_auto"]["L2"] += team.auto_L2
        blue_stats["agg_auto"]["L3"] += team.auto_L3
        blue_stats["agg_auto"]["L4"] += team.auto_L4
        
        # Expected climb points
        for climb_type, prob in team.climb_dist.items():
            blue_stats["expected_climb_points"] += prob * config.climb_points.get(climb_type, 0)
    
    # Run simulation
    simulation_results = simulate_match_points(red_teams, blue_teams, config)
    
    return {
        "red": red_stats,
        "blue": blue_stats,
        "simulation": simulation_results,
        "config": config
    }


# --------------------------- Export Functions ------------------------------------ #

def export_prediction_results(prediction_result: Dict, filename: str = "prediction_results.json"):
    """Export prediction results to JSON file"""
    import json
    
    # Convert non-serializable objects
    export_data = {
        "red_teams": prediction_result["red"],
        "blue_teams": prediction_result["blue"],
        "simulation": {
            k: v for k, v in prediction_result["simulation"].items() 
            if k not in ["red_samples", "blue_samples"]  # Skip large arrays
        },
        "config": {
            "coral_auto": prediction_result["config"].coral_auto,
            "coral_teleop": prediction_result["config"].coral_teleop,
            "processor_auto": prediction_result["config"].processor_auto,
            "processor_teleop": prediction_result["config"].processor_teleop,
            "climb_points": prediction_result["config"].climb_points,
            "enable_processor_swing": prediction_result["config"].enable_processor_swing
        }
    }
    
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(export_data, f, indent=2, ensure_ascii=False)
    
    print(f"Prediction results exported to {filename}")


def create_prediction_summary(prediction_result: Dict) -> str:
    """Create a text summary of prediction results"""
    red = prediction_result["red"]
    blue = prediction_result["blue"]
    sim = prediction_result["simulation"]
    
    summary_lines = [
        "=== MATCH PREDICTION SUMMARY ===",
        "",
        f"Red Alliance Expected Score: {sim['red_mean']:.1f} ± {sim['red_std']:.1f}",
        f"Blue Alliance Expected Score: {sim['blue_mean']:.1f} ± {sim['blue_std']:.1f}",
        f"Score Difference (Red - Blue): {sim['red_mean'] - sim['blue_mean']:.1f}",
        "",
        f"Win Probabilities:",
        f"  Red: {sim['red_win_prob']:.1%}",
        f"  Blue: {sim['blue_win_prob']:.1%}",
        f"  Tie: {sim['tie_prob']:.1%}",
        "",
        "=== TEAM BREAKDOWN ===",
        "",
        "RED ALLIANCE:",
    ]
    
    for team in red["teams"]:
        summary_lines.extend([
            f"  Team {team['team']}:",
            f"    Auto Coral: L1={team['auto_L1']:.1f}, L2={team['auto_L2']:.1f}, L3={team['auto_L3']:.1f}, L4={team['auto_L4']:.1f}",
            f"    Teleop Coral: L1={team['tele_L1']:.1f}, L2={team['tele_L2']:.1f}, L3={team['tele_L3']:.1f}, L4={team['tele_L4']:.1f}",
            f"    Best Climb: {team['best_climb']} (p_auto: {team['p_auto']:.2f})",
            ""
        ])
    
    summary_lines.extend([
        "BLUE ALLIANCE:",
    ])
    
    for team in blue["teams"]:
        summary_lines.extend([
            f"  Team {team['team']}:",
            f"    Auto Coral: L1={team['auto_L1']:.1f}, L2={team['auto_L2']:.1f}, L3={team['auto_L3']:.1f}, L4={team['auto_L4']:.1f}",
            f"    Teleop Coral: L1={team['tele_L1']:.1f}, L2={team['tele_L2']:.1f}, L3={team['tele_L3']:.1f}, L4={team['tele_L4']:.1f}",
            f"    Best Climb: {team['best_climb']} (p_auto: {team['p_auto']:.2f})",
            ""
        ])
    
    return "\n".join(summary_lines)