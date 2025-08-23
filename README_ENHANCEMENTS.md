# Alliance Simulator - Enhanced CSV Format Compatibility

## Overview

The Alliance Simulator has been enhanced with comprehensive CSV format compatibility and simplified configuration management. The system now supports automatic detection and conversion between legacy and modern CSV formats, making it easier to transition to the standardized format while maintaining backward compatibility.

## Key Features

### 🔄 CSV Format Compatibility

#### Supported Formats
- **Legacy Format**: Original format with columns like `Lead Scouter`, `Coral L1 Scored`, etc.
- **New Standard Format**: Modernized format with columns like `Scouter Initials`, `Coral L1 (Auto)`, `Coral L1 (Teleop)`, etc.

#### Automatic Conversion
The system automatically detects the CSV format and converts legacy data to the new standard format:

```python
from csv_converter import convert_csv_file

# Convert a legacy CSV file to new format
converted_file = convert_csv_file('legacy_data.csv', 'converted_data.csv')
```

#### Column Mapping Examples
| Legacy Format | New Format |
|---------------|------------|
| `Lead Scouter` | `Scouter Initials` |
| `Future Alliance in Qualy?` | `Future Alliance` |
| `Coral L1 Scored` | `Coral L1 (Teleop)` |
| `Coral L2 Scored` | `Coral L2 (Teleop)` |
| `Coral L3 Scored` | `Coral L3 (Teleop)` |
| `Coral L4 Scored` | `Coral L4 (Teleop)` |
| `Algae Scored in Barge` | `Barge Algae (Teleop)` |
| `Crossed Feild/Played Defense?` | `Crossed Field/Defense` |
| `Did auton worked?` | `Moved (Auto)` |
| `Did Foul?` | `Foul (Auto)` |

### ⚙️ Simplified Configuration System

#### Configuration Manager
The new `ConfigManager` class provides centralized configuration management:

```python
from config_manager import ConfigManager

# Load configuration
config = ConfigManager('columnsConfig.json')

# Get column configuration
column_config = config.get_column_config()
print(f"Available headers: {column_config.headers}")

# Apply configuration presets
config.apply_preset('2024_game_preset')
```

#### Configuration Presets
- **2024 Game Configuration**: Optimized for FIRST Deep Water 2024 game
- **Basic Configuration**: Simple setup for general scouting

#### Game Phase Configuration
The system automatically categorizes columns by game phase:
- **Autonomous**: 9 columns including `Moved (Auto)`, `Coral L1-L4 (Auto)`, etc.
- **Teleop**: 10 columns including `Coral L1-L4 (Teleop)`, `Crossed Field/Defense`, etc.
- **Endgame**: 2 columns including `Tipped/Fell`, `Died`

### 🌐 Web Interface Enhancements

#### New Pages
1. **CSV Conversion**: Upload and convert CSV files with real-time validation
2. **System Configuration**: Manage configuration presets and view current settings
3. **Enhanced Data Loading**: Automatic format detection during upload

#### Web-Compatible Modules
- `main_web.py`: Web-compatible analyzer without tkinter dependencies
- `foreshadowing_web.py`: Web-compatible prediction system
- Enhanced Streamlit app with new functionality

### 🔮 Enhanced Foreshadowing System

#### Improved Features
- **Export Functionality**: Save prediction results to JSON format
- **Detailed Statistics**: Individual team breakdowns and alliance aggregates
- **Confidence Intervals**: Statistical analysis of prediction reliability
- **Enhanced UI**: Better visualization of prediction results

#### Usage Example
```python
from foreshadowing_web import predict_match, export_prediction_results

# Run prediction
result = predict_match(analyzer, ['1234', '5678', '9012'], ['3456', '7890', '2468'])

# Export results
export_prediction_results(result, 'match_prediction.json')

# Get summary
summary = create_prediction_summary(result)
print(summary)
```

## Installation and Setup

### Requirements
```bash
pip install streamlit pandas numpy matplotlib
```

### Running the Web Application
```bash
streamlit run streamlit_app.py
```

### Running the Desktop Application
```bash
python main.py
```

## Usage Guide

### Converting CSV Files

#### Using the Web Interface
1. Navigate to "🔄 Conversión de CSV"
2. Upload your CSV file
3. The system will automatically detect the format
4. Download the converted file if conversion is needed

#### Using Python
```python
from csv_converter import CSVFormatConverter, convert_csv_file

# Simple conversion
converted_file = convert_csv_file('input.csv', 'output.csv')

# Advanced conversion with validation
converter = CSVFormatConverter()
detected_format, output_file = converter.detect_and_convert_file('input.csv')
validation_report = converter.validate_converted_data(output_file)
```

### Configuration Management

#### Loading Configuration
```python
from config_manager import ConfigManager

config = ConfigManager()
column_config = config.get_column_config()
```

#### Applying Presets
```python
# Apply 2024 game configuration
config.apply_preset('2024_game_preset')

# Save current configuration
config.save_configuration()
```

### Data Analysis

#### Loading Data
```python
from main_web import AnalizadorRobotWeb

analyzer = AnalizadorRobotWeb()
analyzer.load_csv('data.csv')  # Automatic format detection and conversion
```

#### Getting Team Statistics
```python
# Get detailed team statistics
team_stats = analyzer.get_detailed_team_stats()

# Get team data grouped by team number
team_data = analyzer.get_team_data_grouped()
```

## New Standard CSV Format

The new standard format includes 33 columns designed for comprehensive robot scouting:

### Core Information
- `Scouter Initials`: Scout identifier
- `Match Number`: Match identifier
- `Robot`: Robot position (1, 2, or 3)
- `Future Alliance`: Red or Blue
- `Team Number`: Team identifier
- `Starting Position`: Robot starting position

### Autonomous Phase
- `No Show`: Robot didn't show up
- `Moved (Auto)`: Robot moved in autonomous
- `Coral L1-L4 (Auto)`: Coral pieces scored in each level
- `Barge Algae (Auto)`: Algae scored in barge
- `Processor Algae (Auto)`: Algae scored in processor
- `Dislodged Algae (Auto)`: Algae dislodged
- `Foul (Auto)`: Fouls committed

### Teleop Phase
- `Dislodged Algae (Teleop)`: Algae dislodged in teleop
- `Pickup Location`: Where robot picks up game pieces
- `Coral L1-L4 (Teleop)`: Coral pieces scored in each level
- `Barge Algae (Teleop)`: Algae scored in barge
- `Processor Algae (Teleop)`: Algae scored in processor
- `Crossed Field/Defense`: Defense activities
- `Defended`: Robot was defended
- `Coral HP Mistake`: Human player mistakes

### Endgame
- `Tipped/Fell`: Robot tipped or fell
- `Touched Opposing Cage`: Interaction with opposing cage
- `Died`: Robot stopped working
- `End Position`: Final robot position
- `Broke`: Robot broke during match

### Penalties
- `Yellow/Red Card`: Penalty cards received

## File Structure

```
├── config_manager.py          # Configuration management
├── csv_converter.py           # CSV format conversion
├── main_web.py               # Web-compatible analyzer
├── foreshadowing_web.py      # Web-compatible predictions
├── main.py                   # Desktop application
├── streamlit_app.py          # Web application
├── columnsConfig.json        # Default configuration
└── README_ENHANCEMENTS.md    # This file
```

## Validation and Quality Assurance

### Conversion Validation
The system validates converted data and provides detailed reports:
- Total rows and columns
- Data completeness percentage
- Quality issues identification
- Missing or incomplete data detection

### Example Validation Report
```
=== CSV Format Conversion Report ===
Input File: test_data.csv
Output File: test_data_converted.csv

=== Validation Results ===
Total Rows: 90
Total Columns: 33
Expected Columns: 33
Header Match: ✓

Data Quality:
  Match Number: 100.0% complete
  Team Number: 100.0% complete
  Future Alliance: 100.0% complete

✓ No quality issues detected
```

## Benefits of the Enhanced System

1. **Seamless Migration**: Automatic conversion from legacy formats
2. **User-Friendly**: Simplified configuration with presets
3. **Robust Validation**: Comprehensive data quality checks
4. **Web Accessibility**: Full functionality through web interface
5. **Backward Compatibility**: Support for existing data and workflows
6. **Enhanced Analytics**: Improved prediction and analysis capabilities

## Support and Troubleshooting

### Common Issues

#### Format Detection Problems
If the system cannot detect your CSV format:
1. Ensure the CSV has proper headers
2. Check for encoding issues (UTF-8 recommended)
3. Verify column names match expected patterns

#### Conversion Issues
If conversion fails:
1. Check the validation report for specific issues
2. Ensure required columns are present
3. Verify data types are correct

#### Configuration Problems
If configuration doesn't load:
1. Check that `columnsConfig.json` exists
2. Verify JSON syntax is valid
3. Ensure all required fields are present

### Getting Help
For additional support or questions about the enhanced features, refer to the main project documentation or create an issue in the repository.