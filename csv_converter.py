"""CSV Format Converter for Alliance Simulator

This module provides utilities to convert between different CSV formats,
making it easy to transition from legacy formats to the new standardized format.
"""

import csv
import os
from typing import List, Dict, Any, Optional, Tuple
from config_manager import ConfigManager


class CSVFormatConverter:
    """Handles conversion between different CSV formats"""
    
    def __init__(self, config_manager: Optional[ConfigManager] = None):
        self.config_manager = config_manager or ConfigManager()
    
    def detect_and_convert_file(self, input_file: str, output_file: Optional[str] = None) -> Tuple[str, str]:
        """
        Detect CSV format and convert to new format if needed
        
        Args:
            input_file: Path to input CSV file
            output_file: Path to output CSV file (optional, defaults to input_file_converted.csv)
            
        Returns:
            Tuple of (detected_format, output_file_path)
        """
        if not os.path.exists(input_file):
            raise FileNotFoundError(f"Input file not found: {input_file}")
        
        # Read the input file
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            rows = list(reader)
        
        if not rows:
            raise ValueError("Input file is empty")
        
        headers = rows[0]
        data_rows = rows[1:]
        
        # Detect format
        detected_format = self.config_manager.detect_csv_format(headers)
        
        if detected_format == "new_format":
            print(f"File {input_file} is already in the new format")
            return detected_format, input_file
        
        # Convert to new format
        if output_file is None:
            base_name = os.path.splitext(input_file)[0]
            output_file = f"{base_name}_converted.csv"
        
        converted_rows = self.convert_rows_to_new_format(headers, data_rows)
        
        # Write converted file
        with open(output_file, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(self.config_manager.get_column_config().headers)
            writer.writerows(converted_rows)
        
        print(f"Converted {input_file} from {detected_format} to {output_file}")
        return detected_format, output_file
    
    def convert_rows_to_new_format(self, source_headers: List[str], data_rows: List[List[str]]) -> List[List[str]]:
        """
        Convert data rows from source format to new format
        
        Args:
            source_headers: Headers from source CSV
            data_rows: Data rows from source CSV
            
        Returns:
            Converted data rows in new format
        """
        # Get column mapping
        column_mapping = self.config_manager.create_column_mapping(source_headers)
        target_headers = self.config_manager.get_column_config().headers
        
        # Create reverse mapping for quick lookup
        source_index_map = {header: i for i, header in enumerate(source_headers)}
        
        converted_rows = []
        
        for row in data_rows:
            new_row = [""] * len(target_headers)
            
            # Map data from source to target format
            for source_header, target_header in column_mapping.items():
                if source_header in source_index_map and target_header in target_headers:
                    source_index = source_index_map[source_header]
                    target_index = target_headers.index(target_header)
                    
                    if source_index < len(row):
                        # Apply value transformations if needed
                        value = self._transform_value(source_header, target_header, row[source_index])
                        new_row[target_index] = value
            
            # Apply default values for unmapped columns
            new_row = self._apply_default_values(new_row, target_headers)
            
            converted_rows.append(new_row)
        
        return converted_rows
    
    def _transform_value(self, source_header: str, target_header: str, value: str) -> str:
        """Transform value during conversion if needed"""
        # Standard transformations
        transformations = {
            # Boolean standardization
            ("Did auton worked?", "Moved (Auto)"): self._standardize_boolean,
            ("Did Foul?", "Foul (Auto)"): self._standardize_boolean,
            ("Crossed Feild/Played Defense?", "Crossed Field/Defense"): self._standardize_boolean,
            ("Tipped/Fell Over?", "Tipped/Fell"): self._standardize_boolean,
            ("Died?", "Died"): self._standardize_boolean,
            ("Was the robot Defended by someone?", "Defended"): self._standardize_boolean,
            ("Climbed?", "End Position"): self._transform_climb_to_position,
            # Alliance format standardization
            ("Future Alliance in Qualy?", "Future Alliance"): self._standardize_alliance,
            # Card format standardization
            ("Yellow/Red Card", "Yellow/Red Card"): self._standardize_card,
        }
        
        key = (source_header, target_header)
        if key in transformations:
            return transformations[key](value)
        
        return value
    
    def _standardize_boolean(self, value: str) -> str:
        """Standardize boolean values"""
        value_lower = value.strip().lower()
        if value_lower in ['true', 'yes', 'y', '1', 'si', 'sí']:
            return "True"
        elif value_lower in ['false', 'no', 'n', '0']:
            return "False"
        return value
    
    def _transform_climb_to_position(self, value: str) -> str:
        """Transform climb boolean to end position"""
        value_lower = value.strip().lower()
        if value_lower in ['true', 'yes', 'y', '1', 'si', 'sí']:
            return "Climbed"
        elif value_lower in ['false', 'no', 'n', '0']:
            return "Parked"
        return "Unknown"
    
    def _standardize_alliance(self, value: str) -> str:
        """Standardize alliance format"""
        value_lower = value.strip().lower()
        if 'red' in value_lower:
            return "Red"
        elif 'blue' in value_lower:
            return "Blue"
        return value
    
    def _standardize_card(self, value: str) -> str:
        """Standardize card format"""
        value_lower = value.strip().lower()
        if 'yellow' in value_lower:
            return "Yellow"
        elif 'red' in value_lower:
            return "Red"
        elif 'no' in value_lower or value_lower == '':
            return "None"
        return value
    
    def _apply_default_values(self, row: List[str], headers: List[str]) -> List[str]:
        """Apply default values for unmapped columns"""
        defaults = {
            "Robot": "1",  # Default robot number
            "Starting Position": "Unknown",
            "No Show": "False",
            "Pickup Location": "Unknown",
            "End Position": "Unknown",
            "Broke": "False",
            "Touched Opposing Cage": "False",
            "Coral HP Mistake": "False"
        }
        
        for i, header in enumerate(headers):
            if row[i] == "" and header in defaults:
                row[i] = defaults[header]
        
        return row
    
    def validate_converted_data(self, file_path: str) -> Dict[str, Any]:
        """
        Validate converted CSV data for completeness and accuracy
        
        Args:
            file_path: Path to converted CSV file
            
        Returns:
            Validation report dictionary
        """
        if not os.path.exists(file_path):
            return {"error": f"File not found: {file_path}"}
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                rows = list(reader)
        except Exception as e:
            return {"error": f"Error reading file: {e}"}
        
        if not rows:
            return {"error": "File is empty"}
        
        headers = rows[0]
        data_rows = rows[1:]
        expected_headers = self.config_manager.get_column_config().headers
        
        validation_report = {
            "file_path": file_path,
            "total_rows": len(data_rows),
            "total_columns": len(headers),
            "expected_columns": len(expected_headers),
            "header_match": headers == expected_headers,
            "missing_headers": [h for h in expected_headers if h not in headers],
            "extra_headers": [h for h in headers if h not in expected_headers],
            "empty_rows": 0,
            "incomplete_rows": 0,
            "data_quality": {}
        }
        
        # Check data quality
        for i, row in enumerate(data_rows):
            if not any(cell.strip() for cell in row):
                validation_report["empty_rows"] += 1
            elif len(row) != len(headers):
                validation_report["incomplete_rows"] += 1
        
        # Check key columns
        key_columns = ["Match Number", "Team Number", "Future Alliance"]
        for col in key_columns:
            if col in headers:
                col_index = headers.index(col)
                empty_values = sum(1 for row in data_rows if col_index >= len(row) or not row[col_index].strip())
                validation_report["data_quality"][col] = {
                    "empty_count": empty_values,
                    "completion_rate": (len(data_rows) - empty_values) / len(data_rows) * 100 if data_rows else 0
                }
        
        return validation_report
    
    def generate_conversion_report(self, input_file: str, output_file: str, validation_report: Dict[str, Any]) -> str:
        """Generate a human-readable conversion report"""
        report_lines = [
            "=== CSV Format Conversion Report ===",
            f"Input File: {input_file}",
            f"Output File: {output_file}",
            f"Conversion Time: {validation_report.get('conversion_time', 'N/A')}",
            "",
            "=== Validation Results ===",
            f"Total Rows: {validation_report.get('total_rows', 0)}",
            f"Total Columns: {validation_report.get('total_columns', 0)}",
            f"Expected Columns: {validation_report.get('expected_columns', 0)}",
            f"Header Match: {'✓' if validation_report.get('header_match', False) else '✗'}",
            "",
        ]
        
        if validation_report.get('missing_headers'):
            report_lines.extend([
                "Missing Headers:",
                *[f"  - {header}" for header in validation_report['missing_headers']],
                ""
            ])
        
        if validation_report.get('extra_headers'):
            report_lines.extend([
                "Extra Headers:",
                *[f"  - {header}" for header in validation_report['extra_headers']],
                ""
            ])
        
        if validation_report.get('data_quality'):
            report_lines.extend([
                "Data Quality:",
                *[f"  {col}: {info['completion_rate']:.1f}% complete" 
                  for col, info in validation_report['data_quality'].items()],
                ""
            ])
        
        quality_issues = []
        if validation_report.get('empty_rows', 0) > 0:
            quality_issues.append(f"Empty rows: {validation_report['empty_rows']}")
        if validation_report.get('incomplete_rows', 0) > 0:
            quality_issues.append(f"Incomplete rows: {validation_report['incomplete_rows']}")
        
        if quality_issues:
            report_lines.extend([
                "Quality Issues:",
                *[f"  - {issue}" for issue in quality_issues],
                ""
            ])
        else:
            report_lines.append("✓ No quality issues detected")
        
        return "\n".join(report_lines)


def convert_csv_file(input_file: str, output_file: Optional[str] = None, 
                    config_file: str = "columnsConfig.json") -> str:
    """
    Convenience function to convert a CSV file to the new format
    
    Args:
        input_file: Path to input CSV file
        output_file: Path to output CSV file (optional)
        config_file: Path to configuration file
        
    Returns:
        Path to converted file
    """
    config_manager = ConfigManager(config_file)
    converter = CSVFormatConverter(config_manager)
    
    detected_format, converted_file = converter.detect_and_convert_file(input_file, output_file)
    
    if detected_format != "new_format":
        validation_report = converter.validate_converted_data(converted_file)
        report = converter.generate_conversion_report(input_file, converted_file, validation_report)
        print("\n" + report)
    
    return converted_file


if __name__ == "__main__":
    # Example usage
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python csv_converter.py <input_file> [output_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    try:
        converted_file = convert_csv_file(input_file, output_file)
        print(f"\nConversion completed: {converted_file}")
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)