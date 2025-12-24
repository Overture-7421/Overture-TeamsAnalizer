"""
Simple configuration presets for common use cases
"""

def get_simple_presets():
    """Get simplified configuration presets that are easy to understand and apply"""
    
    return {
        "basic_scouting": {
            "name": "Basic Scouting",
            "description": "Simple configuration for basic robot scouting",
            "headers": [
                "Scouter Initials", "Match Number", "Team Number", "Alliance", 
                "Auto Points", "Teleop Points", "Endgame Points", "Penalties", "Notes"
            ],
            "numeric_columns": ["Auto Points", "Teleop Points", "Endgame Points"],
            "autonomous_columns": ["Auto Points"],
            "teleop_columns": ["Teleop Points"],
            "endgame_columns": ["Endgame Points"],
            "use_case": "Quick setup for basic match tracking"
        },
        
        "2024_deep_water": {
            "name": "2024 Deep Water Game",
            "description": "Full configuration for FIRST Deep Water 2024 season",
            "headers": [
                "Scouter Initials", "Match Number", "Robot", "Future Alliance", "Team Number",
                "Starting Position", "No Show", "Moved (Auto)", "Coral L1 (Auto)", "Coral L2 (Auto)",
                "Coral L3 (Auto)", "Coral L4 (Auto)", "Barge Algae (Auto)", "Processor Algae (Auto)",
                "Dislodged Algae (Auto)", "Foul (Auto)", "Dislodged Algae (Teleop)", "Pickup Location",
                "Coral L1 (Teleop)", "Coral L2 (Teleop)", "Coral L3 (Teleop)", "Coral L4 (Teleop)",
                "Barge Algae (Teleop)", "Processor Algae (Teleop)", "Crossed Field/Defense",
                "Tipped/Fell", "Touched Opposing Cage", "Died", "End Position", "Broke",
                "Defended", "Coral HP Mistake", "Yellow/Red Card"
            ],
            "numeric_columns": [
                "Coral L1 (Auto)", "Coral L2 (Auto)", "Coral L3 (Auto)", "Coral L4 (Auto)",
                "Barge Algae (Auto)", "Processor Algae (Auto)", "Dislodged Algae (Auto)",
                "Coral L1 (Teleop)", "Coral L2 (Teleop)", "Coral L3 (Teleop)", "Coral L4 (Teleop)",
                "Barge Algae (Teleop)", "Processor Algae (Teleop)"
            ],
            "autonomous_columns": [
                "Moved (Auto)", "Coral L1 (Auto)", "Coral L2 (Auto)", "Coral L3 (Auto)",
                "Coral L4 (Auto)", "Barge Algae (Auto)", "Processor Algae (Auto)",
                "Dislodged Algae (Auto)", "Foul (Auto)"
            ],
            "teleop_columns": [
                "Dislodged Algae (Teleop)", "Coral L1 (Teleop)", "Coral L2 (Teleop)",
                "Coral L3 (Teleop)", "Coral L4 (Teleop)", "Barge Algae (Teleop)",
                "Processor Algae (Teleop)", "Crossed Field/Defense", "Defended", "Coral HP Mistake"
            ],
            "endgame_columns": ["Tipped/Fell", "Died"],
            "use_case": "Complete scouting for the 2024 Deep Water season"
        },
        
        "offensive_focused": {
            "name": "Offensive Focused",
            "description": "Configuration focused on offensive capabilities",
            "headers": [
                "Scouter Initials", "Match Number", "Team Number", "Alliance",
                "Auto Scoring", "Teleop Scoring", "Cycle Time", "Accuracy",
                "Preferred Scoring Zone", "Max Pieces", "Consistent Scorer", "Notes"
            ],
            "numeric_columns": ["Auto Scoring", "Teleop Scoring", "Cycle Time", "Max Pieces"],
            "autonomous_columns": ["Auto Scoring"],
            "teleop_columns": ["Teleop Scoring", "Cycle Time", "Accuracy"],
            "endgame_columns": ["Consistent Scorer"],
            "use_case": "Focus on scoring and offensive capabilities"
        },
        
        "defensive_focused": {
            "name": "Defensive Focused", 
            "description": "Configuration focused on defensive capabilities",
            "headers": [
                "Scouter Initials", "Match Number", "Team Number", "Alliance",
                "Played Defense", "Defense Effectiveness", "Blocked Shots", "Disrupted Cycles",
                "Penalties While Defending", "Zone Coverage", "Endgame Defense", "Notes"
            ],
            "numeric_columns": ["Defense Effectiveness", "Blocked Shots", "Disrupted Cycles"],
            "autonomous_columns": [],
            "teleop_columns": ["Played Defense", "Defense Effectiveness", "Blocked Shots", "Disrupted Cycles"],
            "endgame_columns": ["Endgame Defense"],
            "use_case": "Focus on defensive play and disruption"
        }
    }

def apply_simple_preset(config_manager, preset_name):
    """Apply a simple preset to the configuration manager"""
    presets = get_simple_presets()
    
    if preset_name not in presets:
        raise ValueError(f"Preset '{preset_name}' not found. Available presets: {list(presets.keys())}")
    
    preset = presets[preset_name]
    
    # Update the configuration
    config_manager.update_column_config(
        headers=preset["headers"],
        numeric_for_overall=preset["numeric_columns"],
        stats_columns=[col for col in preset["headers"] if col not in ["Scouter Initials", "Notes"]],
        autonomous_columns=preset["autonomous_columns"],
        teleop_columns=preset["teleop_columns"],
        endgame_columns=preset["endgame_columns"]
    )
    
    print(f"Applied preset: {preset['name']}")
    print(f"Description: {preset['description']}")
    print(f"Use case: {preset['use_case']}")
    print(f"Total columns: {len(preset['headers'])}")

def create_custom_preset(name, description, columns_config, use_case="Custom configuration"):
    """Create a custom preset with the given configuration"""
    return {
        "name": name,
        "description": description,
        "use_case": use_case,
        **columns_config
    }

def get_preset_recommendations(team_type="balanced"):
    """Get preset recommendations based on team characteristics"""
    recommendations = {
        "balanced": ["2024_deep_water", "basic_scouting"],
        "offensive": ["offensive_focused", "2024_deep_water"],
        "defensive": ["defensive_focused", "basic_scouting"],
        "beginner": ["basic_scouting", "offensive_focused"],
        "advanced": ["2024_deep_water", "offensive_focused", "defensive_focused"]
    }
    
    return recommendations.get(team_type, ["basic_scouting"])

def validate_preset(preset):
    """Validate that a preset has all required fields"""
    required_fields = ["name", "description", "headers", "numeric_columns", 
                      "autonomous_columns", "teleop_columns", "endgame_columns"]
    
    for field in required_fields:
        if field not in preset:
            return False, f"Missing required field: {field}"
    
    # Validate that all numeric columns are in headers
    for col in preset["numeric_columns"]:
        if col not in preset["headers"]:
            return False, f"Numeric column '{col}' not found in headers"
    
    # Validate that all phase columns are in headers
    all_phase_columns = (preset["autonomous_columns"] + 
                        preset["teleop_columns"] + 
                        preset["endgame_columns"])
    
    for col in all_phase_columns:
        if col not in preset["headers"]:
            return False, f"Phase column '{col}' not found in headers"
    
    return True, "Preset is valid"

if __name__ == "__main__":
    # Example usage
    presets = get_simple_presets()
    
    print("Available Simple Presets:")
    for key, preset in presets.items():
        print(f"\n{key}:")
        print(f"  Name: {preset['name']}")
        print(f"  Description: {preset['description']}")
        print(f"  Columns: {len(preset['headers'])}")
        print(f"  Use case: {preset['use_case']}")
    
    print("\nRecommendations for offensive team:")
    recommendations = get_preset_recommendations("offensive")
    for rec in recommendations:
        print(f"  - {rec}")