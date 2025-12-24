# CSV Converter (csv_converter.py)

## Overview

The `csv_converter.py` module handles conversion between different CSV formats used in scouting data. It supports converting legacy formats to the modern format used by the Overture Teams Analyzer.

## Location

```
lib/csv_converter.py
```

## Key Features

- **Format Detection**: Identify legacy vs modern CSV formats
- **Column Mapping**: Map old column names to new ones
- **Data Conversion**: Transform data values as needed
- **Batch Processing**: Convert entire CSV files

## Classes

### CSVFormatConverter

Main converter class for CSV format transformations.

```python
from csv_converter import CSVFormatConverter
from config_manager import ConfigManager

config = ConfigManager()
converter = CSVFormatConverter(config)
```

#### Methods

```python
# Convert entire file
converter.convert_file("legacy_data.csv", "new_format_data.csv")

# Convert rows from legacy format
new_rows = converter.convert_rows_to_new_format(old_headers, old_data_rows)

# Check if conversion is needed
needs_conversion = converter.needs_conversion(headers)

# Get column mapping
mapping = converter.get_column_mapping()
```

## Format Detection

The system detects three format types:

1. **new_format**: Modern format with all expected headers
2. **legacy_format**: Old format that can be converted
3. **unknown_format**: Unrecognized format

```python
from config_manager import ConfigManager

config = ConfigManager()
format_type = config.detect_csv_format(csv_headers)

if format_type == "legacy_format":
    # Convert to new format
    converter = CSVFormatConverter(config)
    new_data = converter.convert_rows_to_new_format(headers, rows)
```

## Column Mapping

Legacy columns are mapped to modern equivalents:

| Legacy Column | New Column |
|---------------|------------|
| "Did something?" | "Moved (Auto)" |
| "Crossed Feild/Played Defense?" | "Crossed Field/Defense" |
| "Died?" | "Died" |
| ... | ... |

## Usage Example

### Automatic Conversion on Load

The engine automatically converts legacy formats:

```python
from engine import AnalizadorRobot

analizador = AnalizadorRobot()

# Load CSV - auto-detects and converts if needed
analizador.load_csv("legacy_scouting_data.csv")
# Output: "Detected legacy format. Converting to new format..."
# Output: "Saved converted file as: legacy_scouting_data_converted.csv"
```

### Manual Conversion

```python
from csv_converter import CSVFormatConverter
from config_manager import ConfigManager
import csv

# Load legacy data
with open("legacy_data.csv", "r") as f:
    reader = csv.reader(f)
    rows = list(reader)

headers = rows[0]
data = rows[1:]

# Convert
config = ConfigManager()
converter = CSVFormatConverter(config)
new_data = converter.convert_rows_to_new_format(headers, data)
new_headers = config.get_column_config().headers

# Save
with open("new_format_data.csv", "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(new_headers)
    writer.writerows(new_data)
```

### Command Line Conversion

From the legacy setup script:

```bash
python lib/setup.py --convert legacy_data.csv new_data.csv
```

## Data Transformations

The converter handles:

1. **Column Reordering**: Align columns to expected order
2. **Missing Columns**: Add empty values for new columns
3. **Value Normalization**: Standardize boolean values (Yes/No → 1/0)
4. **Header Cleanup**: Strip whitespace, fix typos

## Error Handling

```python
try:
    new_data = converter.convert_rows_to_new_format(headers, data)
except ValueError as e:
    print(f"Conversion error: {e}")
    # Handle missing required columns
except Exception as e:
    print(f"Unexpected error: {e}")
```

## Supported Formats

### Legacy Format (Example Headers)

```csv
Scouter Initials,Match Number,Robot,Team,Did something?,Coral L1,Coral L2,Died?,...
```

### Modern Format (Example Headers)

```csv
Scouter Initials,Match Number,Robot,Future Alliance,Team Number,Starting Position,No Show,Moved (Auto),Coral L1 (Auto),Coral L2 (Auto),...
```

## Integration

The converter is used by:

- `engine.py` - Auto-conversion on CSV load
- `setup.py` - Manual conversion utility
- `streamlit_app.py` - File upload handling

## Dependencies

- `csv` - CSV file parsing
- `config_manager` - Configuration access
