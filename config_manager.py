"""Configuration Manager for Alliance Simulator

This module provides centralized configuration management, making it easier to:
- Load and save column configurations
- Convert between CSV formats
- Manage system settings
- Simplify user configuration experience
"""

import json
import os
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


@dataclass
class ColumnConfiguration:
    """Configuration for column mappings and settings"""
    headers: List[str]
    numeric_for_overall: List[str] = field(default_factory=list)
    stats_columns: List[str] = field(default_factory=list)
    mode_boolean_columns: List[str] = field(default_factory=list)
    autonomous_columns: List[str] = field(default_factory=list)
    teleop_columns: List[str] = field(default_factory=list)
    endgame_columns: List[str] = field(default_factory=list)


@dataclass
class RobotValuationConfig:
    """Configuration for robot valuation system"""
    phase_weights: List[float] = field(default_factory=lambda: [0.2, 0.3, 0.5])
    phase_names: List[str] = field(default_factory=lambda: ["Q1", "Q2", "Q3"])


class ConfigManager:
    """Centralized configuration management for the Alliance Simulator"""
    
    def __init__(self, config_file: str = "columnsConfig.json"):
        self.config_file = config_file
        self.column_config = None
        self.robot_valuation_config = None
        self._load_configuration()
    
    def _load_configuration(self):
        """Load configuration from file or create default"""
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                self._parse_config_data(config_data)
            else:
                self._create_default_configuration()
        except Exception as e:
            print(f"Error loading configuration: {e}")
            self._create_default_configuration()
    
    def _parse_config_data(self, config_data: Dict[str, Any]):
        """Parse configuration data from JSON"""
        # Load column configuration
        self.column_config = ColumnConfiguration(
            headers=config_data.get("headers", []),
            numeric_for_overall=config_data.get("column_configuration", {}).get("numeric_for_overall", []),
            stats_columns=config_data.get("column_configuration", {}).get("stats_columns", []),
            mode_boolean_columns=config_data.get("column_configuration", {}).get("mode_boolean_columns", []),
            autonomous_columns=config_data.get("column_configuration", {}).get("autonomous_columns", []),
            teleop_columns=config_data.get("column_configuration", {}).get("teleop_columns", []),
            endgame_columns=config_data.get("column_configuration", {}).get("endgame_columns", [])
        )
        
        # Load robot valuation configuration
        robot_val_data = config_data.get("robot_valuation", {})
        self.robot_valuation_config = RobotValuationConfig(
            phase_weights=robot_val_data.get("phase_weights", [0.2, 0.3, 0.5]),
            phase_names=robot_val_data.get("phase_names", ["Q1", "Q2", "Q3"])
        )
    
    def _create_default_configuration(self):
        """Create default configuration"""
        # Default headers for the new format
        default_headers = [
            "Scouter Initials", "Match Number", "Robot", "Future Alliance", "Team Number",
            "Starting Position", "No Show", "Moved (Auto)", "Coral L1 (Auto)", "Coral L2 (Auto)",
            "Coral L3 (Auto)", "Coral L4 (Auto)", "Barge Algae (Auto)", "Processor Algae (Auto)",
            "Dislodged Algae (Auto)", "Foul (Auto)", "Dislodged Algae (Teleop)", "Pickup Location",
            "Coral L1 (Teleop)", "Coral L2 (Teleop)", "Coral L3 (Teleop)", "Coral L4 (Teleop)",
            "Barge Algae (Teleop)", "Processor Algae (Teleop)", "Crossed Field/Defense",
            "Tipped/Fell", "Touched Opposing Cage", "Died", "End Position", "Broke",
            "Defended", "Coral HP Mistake", "Yellow/Red Card"
        ]
        
        self.column_config = ColumnConfiguration(
            headers=default_headers,
            numeric_for_overall=[
                "Coral L1 (Auto)", "Coral L2 (Auto)", "Coral L3 (Auto)", "Coral L4 (Auto)",
                "Barge Algae (Auto)", "Processor Algae (Auto)", "Dislodged Algae (Auto)",
                "Coral L1 (Teleop)", "Coral L2 (Teleop)", "Coral L3 (Teleop)", "Coral L4 (Teleop)",
                "Barge Algae (Teleop)", "Processor Algae (Teleop)"
            ],
            stats_columns=[col for col in default_headers if col not in ["Scouter Initials", "Robot"]],
            mode_boolean_columns=[
                "No Show", "Moved (Auto)", "Foul (Auto)", "Dislodged Algae (Teleop)",
                "Crossed Field/Defense", "Tipped/Fell", "Touched Opposing Cage", "Died",
                "Broke", "Defended", "Coral HP Mistake"
            ],
            autonomous_columns=[
                "Moved (Auto)", "Coral L1 (Auto)", "Coral L2 (Auto)", "Coral L3 (Auto)",
                "Coral L4 (Auto)", "Barge Algae (Auto)", "Processor Algae (Auto)",
                "Dislodged Algae (Auto)", "Foul (Auto)"
            ],
            teleop_columns=[
                "Dislodged Algae (Teleop)", "Coral L1 (Teleop)", "Coral L2 (Teleop)",
                "Coral L3 (Teleop)", "Coral L4 (Teleop)", "Barge Algae (Teleop)",
                "Processor Algae (Teleop)", "Crossed Field/Defense", "Defended", "Coral HP Mistake"
            ],
            endgame_columns=["Tipped/Fell", "Died"]
        )
        
        self.robot_valuation_config = RobotValuationConfig()
    
    def save_configuration(self):
        """Save current configuration to file"""
        config_data = {
            "version": "1.0",
            "timestamp": "auto-generated",
            "headers": self.column_config.headers,
            "column_configuration": {
                "numeric_for_overall": self.column_config.numeric_for_overall,
                "stats_columns": self.column_config.stats_columns,
                "mode_boolean_columns": self.column_config.mode_boolean_columns,
                "autonomous_columns": self.column_config.autonomous_columns,
                "teleop_columns": self.column_config.teleop_columns,
                "endgame_columns": self.column_config.endgame_columns
            },
            "robot_valuation": {
                "phase_weights": self.robot_valuation_config.phase_weights,
                "phase_names": self.robot_valuation_config.phase_names
            },
            "metadata": {
                "total_columns": len(self.column_config.headers),
                "description": "Alliance Simulator Column Configuration"
            }
        }
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4, ensure_ascii=False)
            print(f"Configuration saved to {self.config_file}")
        except Exception as e:
            print(f"Error saving configuration: {e}")
    
    def get_column_config(self) -> ColumnConfiguration:
        """Get current column configuration"""
        return self.column_config
    
    def get_robot_valuation_config(self) -> RobotValuationConfig:
        """Get current robot valuation configuration"""
        return self.robot_valuation_config
    
    def update_column_config(self, **kwargs):
        """Update column configuration with provided arguments"""
        for key, value in kwargs.items():
            if hasattr(self.column_config, key):
                setattr(self.column_config, key, value)
    
    def update_robot_valuation_config(self, **kwargs):
        """Update robot valuation configuration with provided arguments"""
        for key, value in kwargs.items():
            if hasattr(self.robot_valuation_config, key):
                setattr(self.robot_valuation_config, key, value)
    
    def detect_csv_format(self, csv_headers: List[str]) -> str:
        """Detect CSV format based on headers"""
        current_headers = set(self.column_config.headers)
        input_headers = set(csv_headers)
        
        # Calculate similarity
        intersection = current_headers.intersection(input_headers)
        similarity = len(intersection) / len(current_headers.union(input_headers))
        
        if similarity > 0.8:
            return "new_format"
        elif "Lead Scouter" in input_headers or "Scouter Name" in input_headers:
            return "legacy_format"
        else:
            return "unknown_format"
    
    def create_column_mapping(self, source_headers: List[str]) -> Dict[str, str]:
        """Create mapping between different CSV formats"""
        # Legacy to new format mapping
        legacy_mapping = {
            "Lead Scouter": "Scouter Initials",
            "Match Number": "Match Number",
            "Team Number": "Team Number",
            "Future Alliance in Qualy?": "Future Alliance",
            "Coral L1 Scored": "Coral L1 (Teleop)",
            "Coral L2 Scored": "Coral L2 (Teleop)",
            "Coral L3 Scored": "Coral L3 (Teleop)",
            "Coral L4 Scored": "Coral L4 (Teleop)",
            "Algae Scored in Barge": "Barge Algae (Teleop)",
            "Crossed Feild/Played Defense?": "Crossed Field/Defense",
            "Tipped/Fell Over?": "Tipped/Fell",
            "Died?": "Died",
            "Was the robot Defended by someone?": "Defended",
            "Yellow/Red Card": "Yellow/Red Card",
            "Did Foul?": "Foul (Auto)",
            "Did auton worked?": "Moved (Auto)",
            "Climbed?": "End Position"
        }
        
        mapping = {}
        for source_header in source_headers:
            if source_header in legacy_mapping:
                mapping[source_header] = legacy_mapping[source_header]
            elif source_header in self.column_config.headers:
                mapping[source_header] = source_header
        
        return mapping
    
    def get_configuration_presets(self) -> Dict[str, Dict]:
        """Get predefined configuration presets for common scenarios"""
        return {
            "2024_game_preset": {
                "name": "2024 Game Configuration",
                "description": "Optimized for FIRST Deep Water 2024 game",
                "column_config": self.column_config.__dict__,
                "robot_valuation": self.robot_valuation_config.__dict__
            },
            "basic_preset": {
                "name": "Basic Configuration",
                "description": "Simple configuration for general scouting",
                "column_config": {
                    "numeric_for_overall": ["Coral L1 (Teleop)", "Coral L2 (Teleop)", "Barge Algae (Teleop)"],
                    "stats_columns": self.column_config.headers,
                    "autonomous_columns": ["Moved (Auto)", "Coral L1 (Auto)"],
                    "teleop_columns": ["Coral L1 (Teleop)", "Coral L2 (Teleop)", "Barge Algae (Teleop)"],
                    "endgame_columns": ["Tipped/Fell"]
                },
                "robot_valuation": {"phase_weights": [0.3, 0.4, 0.3]}
            }
        }
    
    def apply_preset(self, preset_name: str):
        """Apply a configuration preset"""
        presets = self.get_configuration_presets()
        if preset_name in presets:
            preset = presets[preset_name]
            if "column_config" in preset:
                for key, value in preset["column_config"].items():
                    if hasattr(self.column_config, key):
                        setattr(self.column_config, key, value)
            if "robot_valuation" in preset:
                for key, value in preset["robot_valuation"].items():
                    if hasattr(self.robot_valuation_config, key):
                        setattr(self.robot_valuation_config, key, value)
            print(f"Applied preset: {preset['name']}")