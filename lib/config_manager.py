"""Configuration Manager for handling different CSV formats and column mappings.

This module provides centralized configuration management for the Alliance Simulator.
It loads and provides access to all JSON configuration files:
- columns.json: Column mappings for CSV data
- scoring.json: Honor Roll scoring weights and thresholds
- alliance.json: Alliance selector configuration
- game.json: Game point values for match simulation
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union, Any

BASE_DIR = Path(__file__).resolve().parent
CONFIG_DIR = BASE_DIR / "config"

@dataclass 
class ColumnConfig:
    """Configuration for column mappings"""
    headers: List[str] = field(default_factory=list)
    numeric_for_overall: List[str] = field(default_factory=list) 
    stats_columns: List[str] = field(default_factory=list)
    mode_boolean_columns: List[str] = field(default_factory=list)
    autonomous_columns: List[str] = field(default_factory=list)
    teleop_columns: List[str] = field(default_factory=list)
    endgame_columns: List[str] = field(default_factory=list)

@dataclass
class RobotValuationConfig:
    """Configuration for robot valuation weights"""
    phase_weights: List[float] = field(default_factory=lambda: [0.25, 0.35, 0.40])  # Early, Mid, Late season emphasis
    phase_names: List[str] = field(default_factory=lambda: ["Early Season", "Mid Season", "Late Season"])

class ConfigManager:
    """Manages configuration presets and format detection"""

    def __init__(self, config_file: Optional[Union[str, Path]] = None):
        resolved_path = Path(config_file) if config_file is not None else BASE_DIR / "columnsConfig.json"
        if not resolved_path.is_absolute():
            resolved_path = BASE_DIR / resolved_path
        self.config_file = resolved_path
        self.presets = self._load_presets()
    
    def _load_presets(self) -> Dict:
        """Load configuration presets"""
        return {
            "new_standard": {
                "name": "DECODE Standard Format (2026)",
                "description": "FTC DECODE format with Auto/Teleop columns",
                "column_config": ColumnConfig(
                    headers=[
                        "Scouter Name", "Match Number", "Robot Position", "Team Number", "Starting Side (Relative)",
                        "No Show", "Left Launch Line (LEAVE)",
                        "Artifacts Scored (CLASSIFIED) (Auto)", "Artifacts Scored (OVERFLOW) (Auto)",
                        "Artifacts Placed in Depot (Auto)", "Pattern Matches at End of Auto (0-9)",
                        "Auto Strategy", "Died/Stopped Moving in Auto",
                        "Artifacts Scored (CLASSIFIED) (Teleop)", "Artifacts Scored (OVERFLOW) (Teleop)",
                        "Artifacts Placed in Depot (Teleop)", "How many artifacts failed to score?",
                        "Pattern Matches at End of Match (0-9)", "Cycle Focus", "Played Defense",
                        "Was Defended Heavily", "Died/Stopped Moving in Teleop", "Returned to Base",
                        "Climbed On Top of Another Robot", "Tipped/Fell Over", "Broke / Major Failure", "Card"
                    ],
                    numeric_for_overall=[
                        "Artifacts Scored (CLASSIFIED) (Auto)", "Artifacts Scored (OVERFLOW) (Auto)",
                        "Artifacts Placed in Depot (Auto)", "Pattern Matches at End of Auto (0-9)",
                        "Artifacts Scored (CLASSIFIED) (Teleop)", "Artifacts Scored (OVERFLOW) (Teleop)",
                        "Artifacts Placed in Depot (Teleop)", "How many artifacts failed to score?",
                        "Pattern Matches at End of Match (0-9)"
                    ],
                    stats_columns=[
                        "No Show", "Left Launch Line (LEAVE)", "Artifacts Scored (CLASSIFIED) (Auto)",
                        "Artifacts Scored (OVERFLOW) (Auto)", "Artifacts Placed in Depot (Auto)",
                        "Pattern Matches at End of Auto (0-9)", "Auto Strategy", "Died/Stopped Moving in Auto",
                        "Artifacts Scored (CLASSIFIED) (Teleop)", "Artifacts Scored (OVERFLOW) (Teleop)",
                        "Artifacts Placed in Depot (Teleop)", "How many artifacts failed to score?",
                        "Pattern Matches at End of Match (0-9)", "Cycle Focus", "Played Defense",
                        "Was Defended Heavily", "Died/Stopped Moving in Teleop", "Returned to Base",
                        "Climbed On Top of Another Robot", "Tipped/Fell Over", "Broke / Major Failure", "Card"
                    ],
                    mode_boolean_columns=[
                        "No Show", "Left Launch Line (LEAVE)", "Died/Stopped Moving in Auto", "Played Defense",
                        "Was Defended Heavily", "Died/Stopped Moving in Teleop", "Returned to Base",
                        "Climbed On Top of Another Robot", "Tipped/Fell Over", "Broke / Major Failure"
                    ],
                    autonomous_columns=[
                        "Left Launch Line (LEAVE)", "Artifacts Scored (CLASSIFIED) (Auto)",
                        "Artifacts Scored (OVERFLOW) (Auto)", "Artifacts Placed in Depot (Auto)",
                        "Pattern Matches at End of Auto (0-9)", "Auto Strategy", "Died/Stopped Moving in Auto"
                    ],
                    teleop_columns=[
                        "Artifacts Scored (CLASSIFIED) (Teleop)", "Artifacts Scored (OVERFLOW) (Teleop)",
                        "Artifacts Placed in Depot (Teleop)", "How many artifacts failed to score?",
                        "Pattern Matches at End of Match (0-9)", "Cycle Focus", "Played Defense",
                        "Was Defended Heavily", "Died/Stopped Moving in Teleop"
                    ],
                    endgame_columns=[
                        "Returned to Base", "Climbed On Top of Another Robot", "Tipped/Fell Over", "Broke / Major Failure"
                    ]
                ),
                "robot_valuation": RobotValuationConfig()
            },
            "legacy": {
                "name": "Legacy Format",
                "description": "Old format with combined columns",
                "column_config": ColumnConfig(
                    headers=[
                        "Lead Scouter", "Highlights Scouter Name", "Scouter Name", "Match Number",
                        "Future Alliance in Qualy?", "Team Number", "Did something?", "Did Foul?", 
                        "Did auton worked?", "Coral L1 Scored", "Coral L2 Scored", "Coral L3 Scored", 
                        "Coral L4 Scored", "Played Algae?(Disloged NO COUNT)", "Algae Scored in Barge",
                        "Crossed Feild/Played Defense?", "Tipped/Fell Over?", "Died?", 
                        "Was the robot Defended by someone?", "Yellow/Red Card", "Climbed?"
                    ],
                    numeric_for_overall=[
                        "Coral L1 Scored", "Coral L2 Scored", "Coral L3 Scored", "Coral L4 Scored", "Climbed?"
                    ],
                    stats_columns=[
                        "Was the robot Defended by someone?", "Yellow/Red Card", "Climbed?"
                    ],
                    mode_boolean_columns=[],
                    autonomous_columns=[
                        "Did something?", "Did Foul?", "Did auton worked?"
                    ],
                    teleop_columns=[
                        "Coral L1 Scored", "Coral L2 Scored", "Coral L3 Scored", "Coral L4 Scored",
                        "Algae Scored in Barge", "Crossed Feild/Played Defense?"
                    ],
                    endgame_columns=[
                        "Climbed?", "Tipped/Fell Over?", "Died?"
                    ]
                ),
                "robot_valuation": RobotValuationConfig()
            }
        }
    
    def detect_csv_format(self, headers: List[str]) -> str:
        """Detect CSV format based on headers"""
        headers_set = set(headers)
        
        # Check for new format indicators
        new_format_indicators = {
            "Scouter Name", "Left Launch Line (LEAVE)",
            "Artifacts Scored (CLASSIFIED) (Auto)", "Artifacts Scored (CLASSIFIED) (Teleop)",
            "Pattern Matches at End of Auto (0-9)", "Cycle Focus"
        }
        
        if len(new_format_indicators.intersection(headers_set)) >= 3:
            return "new_format"
        
        # Check for legacy format indicators  
        legacy_indicators = {
            "Lead Scouter", "Did something?", "Coral L1 Scored", "Climbed?"
        }
        
        if len(legacy_indicators.intersection(headers_set)) >= 2:
            return "legacy_format"
        
        return "unknown_format"
    
    def get_column_config(self, format_name: str = "new_standard") -> ColumnConfig:
        """Get column configuration for specified format"""
        if format_name in self.presets:
            return self.presets[format_name]["column_config"]
        return self.presets["new_standard"]["column_config"]
    
    def get_robot_valuation_config(self, format_name: str = "new_standard") -> RobotValuationConfig:
        """Get robot valuation configuration"""
        if format_name in self.presets:
            return self.presets[format_name]["robot_valuation"]
        return self.presets["new_standard"]["robot_valuation"]
    
    def get_configuration_presets(self) -> Dict:
        """Get all available presets"""
        return self.presets
    
    def apply_preset(self, preset_name: str) -> bool:
        """Apply a configuration preset"""
        if preset_name not in self.presets:
            return False
        
        # Save current configuration
        try:
            config = {
                "active_preset": preset_name,
                "column_config": self.presets[preset_name]["column_config"].__dict__,
                "robot_valuation": self.presets[preset_name]["robot_valuation"].__dict__
            }
            
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Error applying preset: {e}")
            return False
    
    def update_column_config(self, **kwargs) -> None:
        """Update column configuration with provided values."""
        if "new_standard" in self.presets:
            config = self.presets["new_standard"]["column_config"]
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
    
    def update_robot_valuation_config(self, **kwargs) -> None:
        """Update robot valuation configuration with provided values."""
        if "new_standard" in self.presets:
            config = self.presets["new_standard"]["robot_valuation"]
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
    
    def save_configuration(self) -> bool:
        """Save current configuration to file."""
        try:
            if "new_standard" in self.presets:
                config = {
                    "active_preset": "new_standard",
                    "column_config": self.presets["new_standard"]["column_config"].__dict__,
                    "robot_valuation": self.presets["new_standard"]["robot_valuation"].__dict__
                }
                with open(self.config_file, 'w') as f:
                    json.dump(config, f, indent=2)
                return True
        except Exception as e:
            print(f"Error saving configuration: {e}")
        return False


# ==================== Extended Configuration Classes ==================== #

@dataclass
class ScoringConfig:
    """Configuration for Honor Roll scoring weights and thresholds."""
    honor_roll_weights: Dict[str, float] = field(default_factory=lambda: {
        "match_performance": 0.50,
        "pit_scouting": 0.30,
        "during_event": 0.20
    })
    match_performance_weights: Dict[str, float] = field(default_factory=lambda: {
        "autonomous": 0.20,
        "teleop": 0.60,
        "endgame": 0.20
    })
    pit_scouting_weights: Dict[str, float] = field(default_factory=lambda: {
        "electrical": 0.3333,
        "mechanical": 0.25,
        "driver_station_layout": 0.1667,
        "tools": 0.1667,
        "spare_parts": 0.0833
    })
    during_event_weights: Dict[str, float] = field(default_factory=lambda: {
        "team_organization": 0.50,
        "collaboration": 0.50
    })
    competency_multipliers: Dict[str, int] = field(default_factory=lambda: {
        "competencies": 6,
        "subcompetencies": 3,
        "behavior_reports": 0
    })
    disqualification_thresholds: Dict[str, Any] = field(default_factory=lambda: {
        "min_competencies": 2,
        "min_subcompetencies": 1,
        "min_honor_roll_score": 70.0
    })


@dataclass
class AllianceConfig:
    """Configuration for alliance selection parameters."""
    draft_parameters: Dict[str, Any] = field(default_factory=lambda: {
        "max_alliances": 8,
        "teams_per_alliance": 2,
        "min_teams_per_alliance_for_calc": 2
    })
    scoring_weights: Dict[str, float] = field(default_factory=lambda: {
        "auto": 1.5,
        "teleop": 1.0,
        "endgame": 1.2,
        "defense": 12,
        "consistency": 5,
        "clutch": 8
    })
    pick2_priorities: List[str] = field(default_factory=lambda: [
        "defense_rate",
        "algae_score",
        "death_rate"
    ])
    recommendation_logic: Dict[str, str] = field(default_factory=lambda: {
        "pick1": "captain_sniping",
        "pick2": "disabled"
    })


@dataclass
class GameConfig:
    """Configuration for game point values (FRC 2025 REEFSCAPE)."""
    game_name: str = "REEFSCAPE 2025"
    coral_auto_points: Dict[str, int] = field(default_factory=lambda: {
        "L1": 3, "L2": 4, "L3": 6, "L4": 7
    })
    coral_teleop_points: Dict[str, int] = field(default_factory=lambda: {
        "L1": 2, "L2": 3, "L3": 4, "L4": 5
    })
    algae_points: Dict[str, int] = field(default_factory=lambda: {
        "processor": 6,
        "processor_opponent_bonus": 4,
        "net": 4
    })
    climb_points: Dict[str, int] = field(default_factory=lambda: {
        "none": 0, "park": 2, "shallow": 6, "deep": 12
    })
    ranking_points: Dict[str, Any] = field(default_factory=lambda: {
        "win": 3,
        "tie": 1,
        "loss": 0
    })
    auto_rp_requirements: Dict[str, Any] = field(default_factory=lambda: {
        "all_leave_zone": True,
        "min_coral_auto": 1
    })
    coral_rp_requirements: Dict[str, Any] = field(default_factory=lambda: {
        "min_coral_per_level_no_coop": 7,
        "min_levels_with_coop": 3,
        "min_coral_per_level_with_coop": 7
    })
    cooperation_threshold: int = 2


import threading


class GlobalConfigManager:
    """
    Singleton configuration manager that loads all JSON configuration files.
    Provides a unified API for accessing configuration across the application.
    Thread-safe implementation using a lock.
    """
    
    _instance: Optional['GlobalConfigManager'] = None
    _lock: threading.Lock = threading.Lock()
    
    def __new__(cls) -> 'GlobalConfigManager':
        if cls._instance is None:
            with cls._lock:
                # Double-check locking pattern for thread safety
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._initialized = True
        self._scoring_config: Optional[ScoringConfig] = None
        self._alliance_config: Optional[AllianceConfig] = None
        self._game_config: Optional[GameConfig] = None
        self._columns_config: Optional[Dict] = None
        
        self._load_all_configs()
    
    def _load_all_configs(self) -> None:
        """Load all configuration files."""
        self._scoring_config = self._load_scoring_config()
        self._alliance_config = self._load_alliance_config()
        self._game_config = self._load_game_config()
        self._columns_config = self._load_columns_config()
    
    def _load_json_file(self, filename: str) -> Optional[Dict]:
        """Load a JSON file from the config directory."""
        config_path = CONFIG_DIR / filename
        if not config_path.exists():
            # Fallback to lib directory
            config_path = BASE_DIR / filename
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading {filename}: {e}")
        return None
    
    def _load_scoring_config(self) -> ScoringConfig:
        """Load scoring configuration."""
        data = self._load_json_file("scoring.json")
        if data:
            return ScoringConfig(
                honor_roll_weights=data.get("honor_roll_weights", {}),
                match_performance_weights=data.get("match_performance_weights", {}),
                pit_scouting_weights=data.get("pit_scouting_weights", {}),
                during_event_weights=data.get("during_event_weights", {}),
                competency_multipliers=data.get("competency_multipliers", {}),
                disqualification_thresholds=data.get("disqualification_thresholds", {})
            )
        return ScoringConfig()
    
    def _load_alliance_config(self) -> AllianceConfig:
        """Load alliance configuration."""
        data = self._load_json_file("alliance.json")
        if data:
            return AllianceConfig(
                draft_parameters=data.get("draft_parameters", {}),
                scoring_weights=data.get("scoring_weights", {}),
                pick2_priorities=data.get("pick2_priorities", []),
                recommendation_logic=data.get("recommendation_logic", {})
            )
        return AllianceConfig()
    
    def _load_game_config(self) -> GameConfig:
        """Load game configuration."""
        data = self._load_json_file("game.json")
        if data:
            points = data.get("points", {})
            coral = points.get("coral", {})
            algae = points.get("algae", {})
            climb = points.get("climb", {})
            ranking_points = data.get("ranking_points", {})
            
            return GameConfig(
                game_name=data.get("game_name", "REEFSCAPE 2025"),
                coral_auto_points=coral.get("auto", {}),
                coral_teleop_points=coral.get("teleop", {}),
                algae_points=algae,
                climb_points=climb,
                ranking_points={
                    "win": ranking_points.get("win", 3),
                    "tie": ranking_points.get("tie", 1),
                    "loss": ranking_points.get("loss", 0)
                },
                auto_rp_requirements=ranking_points.get("auto_rp", {}),
                coral_rp_requirements=ranking_points.get("coral_rp", {}),
                cooperation_threshold=ranking_points.get("cooperation_threshold", 2)
            )
        return GameConfig()
    
    def _load_columns_config(self) -> Optional[Dict]:
        """Load columns configuration."""
        return self._load_json_file("columns.json")
    
    # Public API
    def get_scoring_config(self) -> ScoringConfig:
        """Get the scoring configuration."""
        return self._scoring_config or ScoringConfig()
    
    def get_alliance_config(self) -> AllianceConfig:
        """Get the alliance configuration."""
        return self._alliance_config or AllianceConfig()
    
    def get_game_config(self) -> GameConfig:
        """Get the game configuration."""
        return self._game_config or GameConfig()
    
    def get_columns_config(self) -> Optional[Dict]:
        """Get the columns configuration dictionary."""
        return self._columns_config
    
    def reload_all(self) -> None:
        """Reload all configuration files."""
        self._load_all_configs()
    
    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance (useful for testing)."""
        cls._instance = None


def get_global_config() -> GlobalConfigManager:
    """Get the global configuration manager instance."""
    return GlobalConfigManager()