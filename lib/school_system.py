"""
SchoolSystem - Comprehensive Team Scoring System
Implements Honor Roll Score calculation based on weighted performance metrics.

Final HonorRollScore = (MatchPerformanceScore * 0.50) + (PitScoutingScore * 0.30) + (DuringEventScore * 0.20)
"""

import math
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
from enum import Enum


class BehaviorReportType(Enum):
    """Types of behavior reports with associated penalty points"""
    LOW_CONDUCT = 2  # Late to matches, asking for tools
    VERY_LOW_CONDUCT = 5  # Severe infractions, dying in match, not showing GP


@dataclass
class TeamCompetencies:
    """Tracks competencies, subcompetencies, and behavior reports for a team"""
    # Competencies (c)
    team_communication: bool = False
    driving_skills: bool = False
    reliability: bool = False
    no_deaths: bool = False
    pasar_inspeccion_primera: bool = False
    human_player: bool = False
    necessary_drivers_fix: bool = False
    
    # Subcompetencies (sc)
    working_under_pressure: bool = False
    commitment: bool = False
    win_most_games: bool = False
    never_ask_pit_admin: bool = False
    knows_the_rules: bool = False
    
    # Behavior Reports (rp) - list of penalty points
    behavior_reports: List[int] = field(default_factory=list)
    
    def get_competencies_count(self) -> int:
        """Returns count of checked competencies (c)"""
        return sum([
            self.team_communication,
            self.driving_skills,
            self.reliability,
            self.no_deaths,
            self.pasar_inspeccion_primera,
            self.human_player,
            self.necessary_drivers_fix
        ])
    
    def get_subcompetencies_count(self) -> int:
        """Returns count of checked subcompetencies (sc)"""
        return sum([
            self.working_under_pressure,
            self.commitment,
            self.win_most_games,
            self.never_ask_pit_admin,
            self.knows_the_rules
        ])
    
    def get_behavior_reports_points(self) -> int:
        """Returns total penalty points from behavior reports (rp)"""
        return sum(self.behavior_reports)


@dataclass
class TeamScores:
    """Container for all raw scores for a team (0-100 scale)"""
    # Match Performance Components
    autonomous_score: float = 0.0
    teleop_score: float = 0.0
    endgame_score: float = 0.0
    
    # Pit Scouting Components
    electrical_score: float = 0.0
    mechanical_score: float = 0.0
    driver_station_layout_score: float = 0.0
    tools_score: float = 0.0
    spare_parts_score: float = 0.0
    
    # During Event Components
    team_organization_score: float = 0.0
    collaboration_score: float = 0.0
    
    # Competencies
    competencies: TeamCompetencies = field(default_factory=TeamCompetencies)
    
    # Scouting comments from exams
    scouting_comments: List[str] = field(default_factory=list)


@dataclass
class CalculatedScores:
    """Container for all calculated scores"""
    match_performance_score: float = 0.0
    pit_scouting_score: float = 0.0
    during_event_score: float = 0.0
    competencies_score: float = 0.0
    honor_roll_score: float = 0.0
    curved_score: float = 0.0
    final_points: int = 0
    is_disqualified: bool = False
    disqualification_reason: str = ""
    final_feedback: str = ""  # Combined feedback from all exams


class TeamScoring:
    """
    Main class for implementing the SchoolSystem Honor Roll scoring.
    Manages multiple teams and calculates comprehensive scores.
    """
    
    def __init__(self, match_weight: float = 0.50, pit_weight: float = 0.30, event_weight: float = 0.20):
        """
        Initialize the scoring system with configurable weights.
        
        Args:
            match_weight: Weight for Match Performance Score (default 0.50 = 50%)
            pit_weight: Weight for Pit Scouting Score (default 0.30 = 30%)
            event_weight: Weight for During Event Score (default 0.20 = 20%)
        """
        self.teams: Dict[str, TeamScores] = {}
        self.calculated_scores: Dict[str, CalculatedScores] = {}
        
        # Configurable scoring weights (must sum to 1.0)
        self.match_performance_weight = match_weight
        self.pit_scouting_weight = pit_weight
        self.during_event_weight = event_weight
        
        # Configurable multipliers for final points calculation
        self.competencies_multiplier = 6
        self.subcompetencies_multiplier = 3
        self.behavior_reports_multiplier = 0  # Currently 0 as per specs
        
        # Disqualification thresholds
        self.min_competencies_count = 2
        self.min_subcompetencies_count = 1
        self.min_honor_roll_score = 70.0
    
    def set_scoring_weights(self, match_weight: float, pit_weight: float, event_weight: float) -> bool:
        """
        Set custom scoring weights. Validates that they sum to 1.0 (100%).
        
        Args:
            match_weight: Weight for Match Performance Score (0.0 to 1.0)
            pit_weight: Weight for Pit Scouting Score (0.0 to 1.0)
            event_weight: Weight for During Event Score (0.0 to 1.0)
            
        Returns:
            True if weights are valid and set, False otherwise
        """
        total = match_weight + pit_weight + event_weight
        if abs(total - 1.0) > 0.001:  # Allow small floating point tolerance
            return False
        
        self.match_performance_weight = match_weight
        self.pit_scouting_weight = pit_weight
        self.during_event_weight = event_weight
        return True
    
    def get_scoring_weights(self) -> Tuple[float, float, float]:
        """
        Get current scoring weights.
        
        Returns:
            Tuple of (match_weight, pit_weight, event_weight)
        """
        return (self.match_performance_weight, self.pit_scouting_weight, self.during_event_weight)
    
    def validate_weights(self, match_weight: float, pit_weight: float, event_weight: float) -> Tuple[bool, str]:
        """
        Validate if the provided weights sum to 100%.
        
        Returns:
            Tuple of (is_valid, message)
        """
        total = match_weight + pit_weight + event_weight
        if abs(total - 1.0) > 0.001:
            return False, f"Weights must sum to 100%. Current sum: {total * 100:.1f}%"
        return True, "Weights are valid"
    
    def add_team(self, team_number: str) -> None:
        """Add a new team to the system"""
        if team_number not in self.teams:
            self.teams[team_number] = TeamScores()
            self.calculated_scores[team_number] = CalculatedScores()
    
    def update_autonomous_score(self, team_number: str, score: float) -> None:
        """Update autonomous score (0-100)"""
        self.add_team(team_number)
        self.teams[team_number].autonomous_score = max(0, min(100, score))
    
    def update_teleop_score(self, team_number: str, score: float) -> None:
        """Update teleop score (0-100)"""
        self.add_team(team_number)
        self.teams[team_number].teleop_score = max(0, min(100, score))
    
    def update_endgame_score(self, team_number: str, score: float) -> None:
        """Update endgame score (0-100)"""
        self.add_team(team_number)
        self.teams[team_number].endgame_score = max(0, min(100, score))
    
    def update_electrical_score(self, team_number: str, score: float) -> None:
        """Update electrical score (0-100)"""
        self.add_team(team_number)
        self.teams[team_number].electrical_score = max(0, min(100, score))
    
    def update_mechanical_score(self, team_number: str, score: float) -> None:
        """Update mechanical score (0-100)"""
        self.add_team(team_number)
        self.teams[team_number].mechanical_score = max(0, min(100, score))
    
    def update_driver_station_layout_score(self, team_number: str, score: float) -> None:
        """Update driver station layout score (0-100)"""
        self.add_team(team_number)
        self.teams[team_number].driver_station_layout_score = max(0, min(100, score))
    
    def update_tools_score(self, team_number: str, score: float) -> None:
        """Update tools score (0-100)"""
        self.add_team(team_number)
        self.teams[team_number].tools_score = max(0, min(100, score))
    
    def update_spare_parts_score(self, team_number: str, score: float) -> None:
        """Update spare parts score (0-100)"""
        self.add_team(team_number)
        self.teams[team_number].spare_parts_score = max(0, min(100, score))
    
    def update_team_organization_score(self, team_number: str, score: float) -> None:
        """Update team organization score (0-100)"""
        self.add_team(team_number)
        self.teams[team_number].team_organization_score = max(0, min(100, score))
    
    def update_collaboration_score(self, team_number: str, score: float) -> None:
        """Update collaboration score (0-100)"""
        self.add_team(team_number)
        self.teams[team_number].collaboration_score = max(0, min(100, score))
    
    def update_competency(self, team_number: str, competency_name: str, value: bool) -> None:
        """Update a specific competency"""
        self.add_team(team_number)
        competencies = self.teams[team_number].competencies
        if hasattr(competencies, competency_name):
            setattr(competencies, competency_name, value)
        else:
            raise ValueError(f"Unknown competency: {competency_name}")
    
    def add_behavior_report(self, team_number: str, report_type: BehaviorReportType) -> None:
        """Add a behavior report"""
        self.add_team(team_number)
        self.teams[team_number].competencies.behavior_reports.append(report_type.value)
    
    def calculate_match_performance_score(self, team_number: str) -> float:
        """
        Calculate Match Performance Score (50% of total)
        Internal weights: Autonomous (20%), Teleop (60%), Endgame (20%)
        """
        if team_number not in self.teams:
            return 0.0
        
        scores = self.teams[team_number]
        match_performance = (
            scores.autonomous_score * 0.20 +
            scores.teleop_score * 0.60 +
            scores.endgame_score * 0.20
        )
        return match_performance
    
    def calculate_pit_scouting_score(self, team_number: str) -> float:
        """
        Calculate Pit Scouting Score (30% of total)
        Internal weights based on contribution to 30% total
        """
        if team_number not in self.teams:
            return 0.0
        
        scores = self.teams[team_number]
        pit_scouting = (
            scores.electrical_score * (10/30) +
            scores.mechanical_score * (7.5/30) +
            scores.driver_station_layout_score * (5/30) +
            scores.tools_score * (5/30) +
            scores.spare_parts_score * (2.5/30)
        )
        return pit_scouting
    
    def calculate_during_event_score(self, team_number: str) -> float:
        """
        Calculate During Event Score (20% of total)
        Simple average of team organization and collaboration
        """
        if team_number not in self.teams:
            return 0.0
        
        scores = self.teams[team_number]
        during_event = (
            scores.team_organization_score * 0.5 +
            scores.collaboration_score * 0.5
        )
        return during_event
    
    def calculate_competencies_score(self, team_number: str) -> Tuple[int, int, int]:
        """
        Calculate competencies metrics
        Returns: (c_count, sc_count, rp_points)
        """
        if team_number not in self.teams:
            return 0, 0, 0
        
        competencies = self.teams[team_number].competencies
        c_count = competencies.get_competencies_count()
        sc_count = competencies.get_subcompetencies_count()
        rp_points = competencies.get_behavior_reports_points()
        
        return c_count, sc_count, rp_points
    
    def calculate_honor_roll_score(self, team_number: str) -> float:
        """
        Calculate the main Honor Roll Score using configurable weights.
        HonorRollScore = (MatchPerformanceScore * match_weight) + (PitScoutingScore * pit_weight) + (DuringEventScore * event_weight)
        """
        match_performance = self.calculate_match_performance_score(team_number)
        pit_scouting = self.calculate_pit_scouting_score(team_number)
        during_event = self.calculate_during_event_score(team_number)
        
        honor_roll = (
            match_performance * self.match_performance_weight +
            pit_scouting * self.pit_scouting_weight +
            during_event * self.during_event_weight
        )
        return honor_roll
    
    def check_disqualification(self, team_number: str) -> Tuple[bool, str]:
        """
        Check if team should be disqualified
        Returns: (is_disqualified, reason)
        """
        c_count, sc_count, rp_points = self.calculate_competencies_score(team_number)
        honor_roll_score = self.calculate_honor_roll_score(team_number)
        
        # Performance DQ Rule
        if c_count < self.min_competencies_count:
            return True, f"Insufficient competencies: {c_count} < {self.min_competencies_count}"
        if sc_count < self.min_subcompetencies_count:
            return True, f"Insufficient subcompetencies: {sc_count} < {self.min_subcompetencies_count}"
        
        # Score DQ Rule
        if honor_roll_score < self.min_honor_roll_score:
            return True, f"Honor Roll Score too low: {honor_roll_score:.1f} < {self.min_honor_roll_score}"
        
        return False, ""
    
    def calculate_all_scores(self) -> None:
        """Calculate all scores for all teams"""
        for team_number in self.teams.keys():
            calculated = self.calculated_scores[team_number]
            
            # Calculate component scores
            calculated.match_performance_score = self.calculate_match_performance_score(team_number)
            calculated.pit_scouting_score = self.calculate_pit_scouting_score(team_number)
            calculated.during_event_score = self.calculate_during_event_score(team_number)
            calculated.honor_roll_score = self.calculate_honor_roll_score(team_number)
            
            # Check disqualification
            is_dq, reason = self.check_disqualification(team_number)
            calculated.is_disqualified = is_dq
            calculated.disqualification_reason = reason
            
            # Concatenate scouting comments into final feedback
            team_scores = self.teams[team_number]
            if team_scores.scouting_comments:
                calculated.final_feedback = " | ".join(team_scores.scouting_comments)
    
    def apply_grading_curve_and_final_points(self) -> None:
        """Apply grading curve and calculate final ranking points"""
        # First, calculate all base scores
        self.calculate_all_scores()
        
        # Find qualified teams and their top score
        qualified_teams = [
            team_num for team_num in self.teams.keys()
            if not self.calculated_scores[team_num].is_disqualified
        ]
        
        if not qualified_teams:
            return
        
        # Find the anchor score (highest among qualified teams)
        top_score = max(
            self.calculated_scores[team_num].honor_roll_score
            for team_num in qualified_teams
        )
        
        if top_score == 0:
            top_score = 1  # Avoid division by zero
        
        # Calculate curved scores and final points for all teams
        for team_number in self.teams.keys():
            calculated = self.calculated_scores[team_number]
            
            if calculated.is_disqualified:
                calculated.curved_score = 0.0
                calculated.final_points = 0
            else:
                # Calculate curved score
                calculated.curved_score = (calculated.honor_roll_score / top_score) * 100
                
                # Get competencies counts
                c_count, sc_count, rp_points = self.calculate_competencies_score(team_number)
                
                # Calculate final points
                final_points = (
                    round(calculated.curved_score) +
                    (c_count * self.competencies_multiplier) +
                    (sc_count * self.subcompetencies_multiplier) +
                    (rp_points * self.behavior_reports_multiplier)
                )
                calculated.final_points = final_points
    
    def get_team_results(self, team_number: str) -> Optional[CalculatedScores]:
        """Get complete results for a team"""
        if team_number not in self.calculated_scores:
            return None
        return self.calculated_scores[team_number]
    
    def get_team_score_breakdown(self, team_number: str) -> Dict:
        """
        Get detailed score breakdown for a team including all component scores.
        Useful for visualizations like radar charts.
        
        Returns:
            Dict with all score components and metadata
        """
        if team_number not in self.teams:
            return {}
        
        team_scores = self.teams[team_number]
        calculated = self.calculated_scores.get(team_number)
        
        return {
            "team_number": team_number,
            "match_performance": {
                "autonomous": team_scores.autonomous_score,
                "teleop": team_scores.teleop_score,
                "endgame": team_scores.endgame_score,
                "total": calculated.match_performance_score if calculated else 0
            },
            "pit_scouting": {
                "electrical": team_scores.electrical_score,
                "mechanical": team_scores.mechanical_score,
                "driver_station": team_scores.driver_station_layout_score,
                "tools": team_scores.tools_score,
                "spare_parts": team_scores.spare_parts_score,
                "total": calculated.pit_scouting_score if calculated else 0
            },
            "during_event": {
                "organization": team_scores.team_organization_score,
                "collaboration": team_scores.collaboration_score,
                "total": calculated.during_event_score if calculated else 0
            },
            "honor_roll_score": calculated.honor_roll_score if calculated else 0,
            "curved_score": calculated.curved_score if calculated else 0,
            "final_points": calculated.final_points if calculated else 0,
            "scouting_comments": team_scores.scouting_comments,
            "final_feedback": calculated.final_feedback if calculated else ""
        }
    
    def get_team_competencies_status(self, team_number: str) -> Dict:
        """
        Get the status of all competencies and subcompetencies for a team.
        
        Returns:
            Dict with competency names as keys and bool status as values
        """
        if team_number not in self.teams:
            return {}
        
        comp = self.teams[team_number].competencies
        
        return {
            "competencies": {
                "team_communication": comp.team_communication,
                "driving_skills": comp.driving_skills,
                "reliability": comp.reliability,
                "no_deaths": comp.no_deaths,
                "pasar_inspeccion_primera": comp.pasar_inspeccion_primera,
                "human_player": comp.human_player,
                "necessary_drivers_fix": comp.necessary_drivers_fix
            },
            "subcompetencies": {
                "working_under_pressure": comp.working_under_pressure,
                "commitment": comp.commitment,
                "win_most_games": comp.win_most_games,
                "never_ask_pit_admin": comp.never_ask_pit_admin,
                "knows_the_rules": comp.knows_the_rules
            },
            "behavior_reports": comp.behavior_reports,
            "counts": {
                "competencies": comp.get_competencies_count(),
                "subcompetencies": comp.get_subcompetencies_count(),
                "behavior_penalty": comp.get_behavior_reports_points()
            }
        }
    
    @staticmethod
    def get_competency_labels() -> Dict[str, str]:
        """Get human-readable labels for all competencies"""
        return {
            "team_communication": "Team Communication",
            "driving_skills": "Driving Skills",
            "reliability": "Reliability",
            "no_deaths": "No Deaths (Robot Reliability)",
            "pasar_inspeccion_primera": "Passed Inspection First Try",
            "human_player": "Human Player Skills",
            "necessary_drivers_fix": "Drivers Can Fix Issues"
        }
    
    @staticmethod
    def get_subcompetency_labels() -> Dict[str, str]:
        """Get human-readable labels for all subcompetencies"""
        return {
            "working_under_pressure": "Works Under Pressure",
            "commitment": "Team Commitment",
            "win_most_games": "Wins Most Games",
            "never_ask_pit_admin": "Self-Sufficient (No Pit Admin)",
            "knows_the_rules": "Knows Game Rules"
        }

    def get_honor_roll_ranking(self) -> List[Tuple[str, CalculatedScores]]:
        """
        Get final honor roll ranking sorted by final points (descending)
        Only includes qualified teams
        """
        self.apply_grading_curve_and_final_points()
        
        qualified_teams = [
            (team_num, self.calculated_scores[team_num])
            for team_num in self.teams.keys()
            if not self.calculated_scores[team_num].is_disqualified
        ]
        
        # Sort by final points (descending)
        qualified_teams.sort(key=lambda x: x[1].final_points, reverse=True)
        return qualified_teams
    
    def get_disqualified_teams(self) -> List[Tuple[str, str]]:
        """Get list of disqualified teams with reasons"""
        self.calculate_all_scores()
        
        return [
            (team_num, self.calculated_scores[team_num].disqualification_reason)
            for team_num in self.teams.keys()
            if self.calculated_scores[team_num].is_disqualified
        ]
    
    def get_summary_stats(self) -> Dict:
        """Get summary statistics for the honor roll system"""
        self.apply_grading_curve_and_final_points()
        
        total_teams = len(self.teams)
        qualified_teams = sum(
            1 for team_num in self.teams.keys()
            if not self.calculated_scores[team_num].is_disqualified
        )
        disqualified_teams = total_teams - qualified_teams
        
        if qualified_teams > 0:
            avg_honor_roll = sum(
                self.calculated_scores[team_num].honor_roll_score
                for team_num in self.teams.keys()
                if not self.calculated_scores[team_num].is_disqualified
            ) / qualified_teams
            
            avg_final_points = sum(
                self.calculated_scores[team_num].final_points
                for team_num in self.teams.keys()
                if not self.calculated_scores[team_num].is_disqualified
            ) / qualified_teams
        else:
            avg_honor_roll = 0
            avg_final_points = 0
        
        return {
            "total_teams": total_teams,
            "qualified_teams": qualified_teams,
            "disqualified_teams": disqualified_teams,
            "avg_honor_roll_score": avg_honor_roll,
            "avg_final_points": avg_final_points
        }


class ForshadowingSystem:
    """
    Separate predictive analysis system for match and ranking prediction
    """
    
    @staticmethod
    def match_forshadow(rivals_performance_score: float) -> Dict:
        """
        Predict match outcomes based on rival performance scores
        """
        # Basic prediction logic - can be enhanced with more sophisticated algorithms
        win_probability = max(0, min(1, (rivals_performance_score - 50) / 50))
        
        return {
            "win_probability": win_probability,
            "predicted_outcome": "WIN" if win_probability > 0.5 else "LOSS",
            "confidence": abs(win_probability - 0.5) * 2
        }
    
    @staticmethod
    def ranking_forshadow(
        alliance_performance_score: float,
        alliance_ranking_points: int,
        alliance_selector_output: Dict,
        sidenote_pt1: str = "",
        sidenote_pt2: str = ""
    ) -> Dict:
        """
        Predict event rankings based on alliance performance and selection data
        """
        # Combine various factors for ranking prediction
        base_prediction = alliance_performance_score * 0.6 + alliance_ranking_points * 0.4
        
        # Adjust based on alliance selector recommendations
        selector_bonus = 0
        if "recommended" in str(alliance_selector_output).lower():
            selector_bonus = 10
        
        final_prediction = base_prediction + selector_bonus
        
        return {
            "predicted_ranking": max(1, round(8 - (final_prediction / 20))),  # Rough ranking estimate
            "performance_factor": alliance_performance_score,
            "ranking_points_factor": alliance_ranking_points,
            "selector_factor": selector_bonus,
            "notes": f"{sidenote_pt1} | {sidenote_pt2}".strip(" |"),
            "confidence_level": min(100, final_prediction)
        }


if __name__ == "__main__":
    # Example usage and testing
    print("SchoolSystem - Honor Roll Scoring System")
    print("=" * 50)
    
    # Create scoring system
    scoring = TeamScoring()
    
    # Add some example teams
    teams_data = [
        ("1234", 85, 90, 75, 80, 85, 70, 75, 80, 90, 85),
        ("5678", 70, 80, 85, 90, 75, 85, 80, 75, 80, 90),
        ("9012", 95, 85, 80, 75, 90, 80, 85, 90, 85, 75)
    ]
    
    for team_num, auto, teleop, end, elec, mech, ds, tools, parts, org, collab in teams_data:
        scoring.update_autonomous_score(team_num, auto)
        scoring.update_teleop_score(team_num, teleop)
        scoring.update_endgame_score(team_num, end)
        scoring.update_electrical_score(team_num, elec)
        scoring.update_mechanical_score(team_num, mech)
        scoring.update_driver_station_layout_score(team_num, ds)
        scoring.update_tools_score(team_num, tools)
        scoring.update_spare_parts_score(team_num, parts)
        scoring.update_team_organization_score(team_num, org)
        scoring.update_collaboration_score(team_num, collab)
        
        # Add some competencies
        scoring.update_competency(team_num, "team_communication", True)
        scoring.update_competency(team_num, "driving_skills", True)
        scoring.update_competency(team_num, "reliability", True)
        scoring.update_competency(team_num, "working_under_pressure", True)
        scoring.update_competency(team_num, "commitment", True)
    
    # Get final rankings
    rankings = scoring.get_honor_roll_ranking()
    
    print("\nHonor Roll Rankings:")
    print("-" * 80)
    print(f"{'Rank':<5} {'Team':<8} {'Final Points':<12} {'Honor Roll':<12} {'Curved':<10} {'C/SC/RP'}")
    print("-" * 80)
    
    for rank, (team_num, results) in enumerate(rankings, 1):
        c, sc, rp = scoring.calculate_competencies_score(team_num)
        print(f"{rank:<5} {team_num:<8} {results.final_points:<12} "
              f"{results.honor_roll_score:<12.1f} {results.curved_score:<10.1f} "
              f"{c}/{sc}/{rp}")
    
    # Show disqualified teams
    disqualified = scoring.get_disqualified_teams()
    if disqualified:
        print(f"\nDisqualified Teams:")
        for team_num, reason in disqualified:
            print(f"  {team_num}: {reason}")
    
    # Show summary
    stats = scoring.get_summary_stats()
    print(f"\nSummary Statistics:")
    print(f"  Total Teams: {stats['total_teams']}")
    print(f"  Qualified: {stats['qualified_teams']}")
    print(f"  Disqualified: {stats['disqualified_teams']}")
    print(f"  Avg Honor Roll Score: {stats['avg_honor_roll_score']:.1f}")
    print(f"  Avg Final Points: {stats['avg_final_points']:.1f}")
