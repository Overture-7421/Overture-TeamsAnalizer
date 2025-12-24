# Engine (engine.py)

## Overview

The `engine.py` module contains the `AnalizadorRobot` class, which is the core data processing and analysis engine for the Overture Teams Analyzer. It handles data loading, statistical calculations, and team analysis without any GUI dependencies.

## Location

```
lib/engine.py
```

## Key Features

- **CSV Data Loading**: Load and parse scouting data from CSV files
- **QR Data Processing**: Parse QR code formatted data
- **Auto-loading**: Automatically load `data/default_scouting.csv` on startup
- **Hot Reload**: Monitor CSV files for changes and reload automatically
- **Team Statistics**: Calculate comprehensive team statistics
- **Robot Valuation**: Compute weighted performance scores

## Class: AnalizadorRobot

### Constructor

```python
def __init__(
    self, 
    default_column_names: Optional[List[str]] = None, 
    config_file: str = "columnsConfig.json",
    config_manager: Optional[ConfigManager] = None,
    auto_load_default: bool = True
)
```

#### Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `default_column_names` | `List[str]` | Custom column headers (optional) |
| `config_file` | `str` | Path to configuration file |
| `config_manager` | `ConfigManager` | Pre-configured ConfigManager instance |
| `auto_load_default` | `bool` | Auto-load `data/default_scouting.csv` if exists |

### Key Methods

#### Data Loading

```python
# Load CSV file
analizador.load_csv("/path/to/scouting_data.csv")

# Load QR code data
analizador.load_qr_data("tab\tseparated\tdata\nwith\tmultiple\trows")

# Get raw data
raw_data = analizador.get_raw_data()
```

#### Auto-loading and Hot Reload

```python
# Get default CSV path
default_path = analizador.get_default_csv_path()
# Returns: Path("data/default_scouting.csv")

# Manually reload CSV from disk
analizador.reload_csv()

# Check if file was modified
has_updates = analizador.check_for_updates()

# Start hot-reload monitoring
analizador.start_hot_reload(interval_seconds=5.0, callback=on_change)

# Stop hot-reload
analizador.stop_hot_reload()
```

#### Statistics

```python
# Get detailed team statistics
stats = analizador.get_detailed_team_stats()
# Returns list of dicts with overall_avg, overall_std, RobotValuation, etc.

# Get team data grouped by team number
team_data = analizador.get_team_data_grouped()
# Returns: {"7421": [[row1], [row2], ...], "254": [...]}

# Calculate phase scores for a team
phase_scores = analizador.calculate_team_phase_scores(7421)
# Returns: {"autonomous": 15.5, "teleop": 42.3, "endgame": 8.0}
```

## Default CSV Auto-Loading

When `auto_load_default=True` (default), the engine will:

1. Check if `data/default_scouting.csv` exists
2. If found, automatically load it on initialization
3. Track the file's modification time for hot-reload

This is especially useful for headless servers where the HID interceptor writes data to the default CSV file.

## Hot Reload Feature

The hot-reload feature allows the engine to automatically detect when the CSV file changes and reload it. This is critical for headless scouting setups where:

1. The HID interceptor appends new scans to the CSV
2. The web interface needs to show updated data without manual refresh

### Usage Example

```python
from engine import AnalizadorRobot

# Create analyzer with auto-load
analizador = AnalizadorRobot()

# Define callback for when data changes
def on_data_change():
    print("Data updated! Refreshing statistics...")
    stats = analizador.get_detailed_team_stats()
    print(f"Now tracking {len(stats)} teams")

# Start hot-reload with 5-second interval
analizador.start_hot_reload(
    interval_seconds=5.0,
    callback=on_data_change
)

# ... application runs ...

# Cleanup
analizador.stop_hot_reload()
```

## Configuration

The engine uses `columnsConfig.json` for column configuration:

```json
{
    "headers": ["Scouter Initials", "Match Number", ...],
    "column_configuration": {
        "numeric_for_overall": [...],
        "autonomous_columns": [...],
        "teleop_columns": [...],
        "endgame_columns": [...]
    },
    "system_settings": {
        "default_csv_path": "data/default_scouting.csv",
        "auto_reload_enabled": true,
        "reload_interval_seconds": 5
    }
}
```

## Thread Safety

The hot-reload feature uses a daemon thread that runs in the background. Key points:

- The monitoring thread is a daemon thread (won't block program exit)
- Exception handling prevents silent thread death
- Use `stop_hot_reload()` for graceful shutdown

## Dependencies

- `csv` - CSV file parsing
- `json` - Configuration file loading
- `threading` - Hot-reload background monitoring
- `config_manager` - Configuration management
- `csv_converter` - Format conversion utilities
