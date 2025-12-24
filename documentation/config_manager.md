# Config Manager (config_manager.py)

## Overview

The `config_manager.py` module handles loading and managing configuration files for the Overture Teams Analyzer. It provides a centralized way to access column configurations, robot valuation settings, and game parameters.

## Location

```
lib/config_manager.py
```

## Key Features

- **Column Configuration**: Manage scouting data column definitions
- **Robot Valuation**: Configure scoring weights and phase names
- **Game Configuration**: Game-specific scoring rules
- **Format Detection**: Auto-detect CSV formats (legacy vs new)

## Classes

### ConfigManager

Main configuration management class.

```python
from config_manager import ConfigManager

# Load default config
config = ConfigManager()

# Load from specific file
config = ConfigManager(config_file="custom_config.json")
```

#### Methods

```python
# Get column configuration
column_config = config.get_column_config()
# Returns: ColumnConfig object

# Get robot valuation config
robot_config = config.get_robot_valuation_config()
# Returns: RobotValuationConfig object

# Get game configuration
game_config = config.get_game_config()
# Returns: GameConfig object

# Detect CSV format
format_type = config.detect_csv_format(headers)
# Returns: "new_format", "legacy_format", or "unknown_format"
```

### ColumnConfig

Stores column configuration settings.

```python
column_config = config.get_column_config()

# Access headers
headers = column_config.headers
# ["Scouter Initials", "Match Number", ...]

# Access column lists
numeric_cols = column_config.numeric_for_overall
stats_cols = column_config.stats_columns
boolean_cols = column_config.mode_boolean_columns
auto_cols = column_config.autonomous_columns
teleop_cols = column_config.teleop_columns
endgame_cols = column_config.endgame_columns
```

### RobotValuationConfig

Stores robot valuation settings.

```python
robot_config = config.get_robot_valuation_config()

# Phase weights
weights = robot_config.phase_weights
# [0.2, 0.3, 0.5]

# Phase names
names = robot_config.phase_names
# ["Q1", "Q2", "Q3"]
```

### GameConfig

Stores game-specific scoring rules.

```python
game_config = config.get_game_config()

# Coral scoring
coral_auto_points = game_config.coral_auto_points
# {"L1": 3, "L2": 4, "L3": 6, "L4": 7}

coral_teleop_points = game_config.coral_teleop_points
# {"L1": 2, "L2": 3, "L3": 4, "L4": 5}

# Algae scoring
algae_points = game_config.algae_points
# {"processor": 6, "net": 4}

# Climb scoring
climb_points = game_config.climb_points
# {"none": 0, "park": 2, "shallow": 6, "deep": 12}
```

## Configuration Files

### columnsConfig.json

Main column configuration file:

```json
{
    "version": "1.0",
    "timestamp": "8.6",
    "headers": [
        "Scouter Initials",
        "Match Number",
        "Robot",
        "Future Alliance",
        "Team Number",
        ...
    ],
    "column_configuration": {
        "numeric_for_overall": [...],
        "stats_columns": [...],
        "mode_boolean_columns": [...],
        "autonomous_columns": [...],
        "teleop_columns": [...],
        "endgame_columns": [...]
    },
    "robot_valuation": {
        "phase_weights": [0.2, 0.3, 0.5],
        "phase_names": ["Q1", "Q2", "Q3"]
    },
    "metadata": {
        "total_columns": 33,
        "description": "Alliance Simulator Column Configuration"
    },
    "system_settings": {
        "scanner_hardware_id": "",
        "headless_mode_enabled": false,
        "default_csv_path": "data/default_scouting.csv",
        "auto_reload_enabled": true,
        "reload_interval_seconds": 5
    }
}
```

### game.json (Optional)

Game-specific scoring rules:

```json
{
    "name": "REEFSCAPE 2025",
    "coral": {
        "auto_points": {"L1": 3, "L2": 4, "L3": 6, "L4": 7},
        "teleop_points": {"L1": 2, "L2": 3, "L3": 4, "L4": 5}
    },
    "algae": {"processor": 6, "net": 4},
    "climb": {"none": 0, "park": 2, "shallow": 6, "deep": 12}
}
```

## Global Access

Get the global configuration instance:

```python
from config_manager import get_global_config

config = get_global_config()
game_config = config.get_game_config()
```

## Format Detection

The ConfigManager can detect CSV formats:

```python
headers = ["Scouter Initials", "Match Number", "Robot", ...]
format_type = config.detect_csv_format(headers)

if format_type == "new_format":
    # Modern format, use as-is
    pass
elif format_type == "legacy_format":
    # Old format, needs conversion
    from csv_converter import CSVFormatConverter
    converter = CSVFormatConverter(config)
    converted_data = converter.convert_rows_to_new_format(headers, data)
else:
    # Unknown format
    print("Warning: Unknown CSV format")
```

## Dependencies

- `json` - JSON file parsing
- `pathlib` - Path manipulation
- `dataclasses` - Data class definitions
