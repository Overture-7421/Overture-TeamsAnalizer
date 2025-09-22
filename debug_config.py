#!/usr/bin/env python3
"""
Debug configuration loading
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from main import AnalizadorRobot
import json

def debug_config():
    print("🔍 Debugging configuration loading...")
    
    # Load config directly
    with open('columnsConfig.json', 'r', encoding='utf-8') as f:
        config = json.load(f)
    
    print(f"📋 Config headers: {len(config['headers'])}")
    print(f"📊 Numeric columns in config: {config['column_configuration']['numeric_for_overall']}")
    
    # Initialize analyzer
    analyzer = AnalizadorRobot()
    
    print(f"📊 Analyzer numeric columns: {analyzer._selected_numeric_columns_for_overall}")
    print(f"📊 Analyzer stats columns: {analyzer._selected_stats_columns}")
    
    # Load test data
    with open('test_artifacts_format.csv', 'r', encoding='utf-8') as f:
        content = f.read()
    
    lines = content.strip().split('\n')
    csv_data = [line.split(',') for line in lines]
    
    analyzer.sheet_data = csv_data
    analyzer._update_column_indices()
    
    # Check if numeric columns are in the data
    print(f"\n🔍 Checking numeric columns presence in data:")
    for col in analyzer._selected_numeric_columns_for_overall:
        in_data = col in analyzer._column_indices
        print(f"  {col}: {'✅' if in_data else '❌'}")
    
    # Try manually calculating stats for a column
    if 'ARTIFACTS(AUTO)' in analyzer._column_indices:
        col_idx = analyzer._column_indices['ARTIFACTS(AUTO)']
        team_7421_data = analyzer.get_team_data_grouped().get('7421', [])
        values = []
        for row in team_7421_data:
            if col_idx < len(row):
                try:
                    val = float(row[col_idx])
                    values.append(val)
                except ValueError:
                    values.append(0.0)
        
        avg = sum(values) / len(values) if values else 0
        print(f"\n🔢 Manual calculation for ARTIFACTS(AUTO):")
        print(f"  Values: {values}")
        print(f"  Average: {avg}")

if __name__ == "__main__":
    debug_config()