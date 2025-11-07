"""Configuration Manager for handling different CSV formats and column mappings
"""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Union

BASE_DIR = Path(__file__).resolve().parent

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
                "name": "New Standard Format (2025)",
                "description": "Format with separate Auto/Teleop columns",
                "column_config": ColumnConfig(
                    headers=[
                        "Scouter Initials", "Match Number", "Robot", "Future Alliance", "Team Number",
                        "Starting Position", "No Show", "Moved (Auto)", "Coral L1 (Auto)", "Coral L2 (Auto)",
                        "Coral L3 (Auto)", "Coral L4 (Auto)", "Barge Algae (Auto)", "Processor Algae (Auto)",
                        "Dislodged Algae (Auto)", "Foul (Auto)", "Dislodged Algae (Teleop)", "Pickup Location",
                        "Coral L1 (Teleop)", "Coral L2 (Teleop)", "Coral L3 (Teleop)", "Coral L4 (Teleop)",
                        "Barge Algae (Teleop)", "Processor Algae (Teleop)", "Crossed Field/Defense",
                        "Tipped/Fell", "Touched Opposing Cage", "Died", "End Position", "Broke", "Defended",
                        "Coral HP Mistake", "Yellow/Red Card"
                    ],
                    numeric_for_overall=[
                        "Coral L1 (Auto)", "Coral L2 (Auto)", "Coral L3 (Auto)", "Coral L4 (Auto)",
                        "Coral L1 (Teleop)", "Coral L2 (Teleop)", "Coral L3 (Teleop)", "Coral L4 (Teleop)",
                        "Barge Algae (Auto)", "Barge Algae (Teleop)", "Processor Algae (Auto)", "Processor Algae (Teleop)"
                    ],
                    stats_columns=[
                        "Coral L1 (Auto)", "Coral L2 (Auto)", "Coral L3 (Auto)", "Coral L4 (Auto)",
                        "Coral L1 (Teleop)", "Coral L2 (Teleop)", "Coral L3 (Teleop)", "Coral L4 (Teleop)",
                        "Barge Algae (Auto)", "Barge Algae (Teleop)", "Processor Algae (Auto)", "Processor Algae (Teleop)",
                        "End Position", "Crossed Field/Defense", "Died"
                    ],
                    mode_boolean_columns=[
                        "Moved (Auto)", "Foul (Auto)", "Crossed Field/Defense", "Died", "Broke", "Defended"
                    ],
                    autonomous_columns=[
                        "Moved (Auto)", "Coral L1 (Auto)", "Coral L2 (Auto)", "Coral L3 (Auto)", "Coral L4 (Auto)",
                        "Barge Algae (Auto)", "Processor Algae (Auto)", "Foul (Auto)"
                    ],
                    teleop_columns=[
                        "Coral L1 (Teleop)", "Coral L2 (Teleop)", "Coral L3 (Teleop)", "Coral L4 (Teleop)",
                        "Barge Algae (Teleop)", "Processor Algae (Teleop)", "Crossed Field/Defense",
                        "Dislodged Algae (Teleop)", "Defended"
                    ],
                    endgame_columns=[
                        "End Position", "Died", "Broke", "Tipped/Fell"
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
            "Scouter Initials", "Coral L1 (Auto)", "Coral L1 (Teleop)", 
            "End Position", "Starting Position"
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