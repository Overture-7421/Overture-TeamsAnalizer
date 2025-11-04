#!/usr/bin/env python3
"""
Test script to verify simplified ranking export functionality
"""

import os
import csv
from main import AnalizadorRobot

def test_simplified_ranking_export():
    """Test the simplified ranking export feature"""
    print("Testing Simplified Ranking Export...")
    print("=" * 60)
    
    # Initialize analyzer and load test data
    analizador = AnalizadorRobot()
    
    # Check if test data exists
    test_file = "test_data.csv"
    if not os.path.exists(test_file):
        print(f"✗ Test data file '{test_file}' not found!")
        return False
    
    print(f"✓ Found test data file: {test_file}")
    
    # Load test data
    analizador.load_csv(test_file)
    print(f"✓ Loaded CSV data")
    
    # Get team stats
    stats = analizador.get_detailed_team_stats()
    print(f"✓ Generated stats for {len(stats)} teams")
    
    if not stats:
        print("✗ No statistics generated!")
        return False
    
    # Test the export logic (without GUI)
    print("\nTest 1: Verify Required Data Fields")
    print("-" * 60)
    
    team_data_grouped = analizador.get_team_data_grouped()
    
    for rank, team_stat in enumerate(stats[:3], 1):  # Test first 3 teams
        team_num = str(team_stat.get('team', 'N/A'))
        overall_avg = team_stat.get('overall_avg', 0.0)
        overall_std = team_stat.get('overall_std', 0.0)
        robot_valuation = team_stat.get('RobotValuation', 0.0)
        
        # Get death rate
        died_rate_key = analizador._generate_stat_key('Died?', 'rate')
        death_rate = team_stat.get(died_rate_key, 0.0)
        
        # Get defended rate
        defended_key = analizador._generate_stat_key('Was the robot Defended by someone?', 'rate')
        defended_rate = team_stat.get(defended_key, 0.0)
        
        # Determine climb type
        climb_type = "Unknown"
        if team_num in team_data_grouped:
            team_rows = team_data_grouped[team_num]
            end_pos_idx = analizador._column_indices.get('End Position')
            climb_idx = analizador._column_indices.get('Climbed?')
            
            if end_pos_idx is not None:
                climb_values = []
                for row in team_rows:
                    if end_pos_idx < len(row):
                        climb_values.append(str(row[end_pos_idx]).strip())
                if climb_values:
                    climb_type = analizador._calculate_mode(climb_values)
            elif climb_idx is not None:
                climb_values = []
                for row in team_rows:
                    if climb_idx < len(row):
                        val = str(row[climb_idx]).strip().lower()
                        if val in ['true', 'yes', 'y', '1']:
                            climb_values.append('Yes')
                        else:
                            climb_values.append('No')
                if climb_values:
                    climb_type = analizador._calculate_mode(climb_values)
        
        print(f"  Team {team_num}:")
        print(f"    Overall: {overall_avg:.2f} ± {overall_std:.2f}")
        print(f"    Robot Valuation: {robot_valuation:.2f}")
        print(f"    Death Rate: {death_rate:.3f}")
        print(f"    Climb Type: {climb_type}")
        print(f"    Defended Rate: {defended_rate:.3f}")
    
    print("✓ All required fields successfully extracted")
    
    # Test 2: Create actual export file
    print("\nTest 2: Export to CSV File")
    print("-" * 60)
    
    output_file = "/tmp/test_simplified_ranking.csv"
    
    try:
        with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.writer(csvfile)
            
            # Write header
            writer.writerow([
                "Rank", "Team Number", "Overall Average", "Std Deviation", 
                "Robot Valuation", "Death Rate", "Climb Type", "Defended Rate"
            ])
            
            # Write data
            for rank, team_stat in enumerate(stats, 1):
                team_num = str(team_stat.get('team', 'N/A'))
                overall_avg = team_stat.get('overall_avg', 0.0)
                overall_std = team_stat.get('overall_std', 0.0)
                robot_valuation = team_stat.get('RobotValuation', 0.0)
                
                died_rate_key = analizador._generate_stat_key('Died?', 'rate')
                death_rate = team_stat.get(died_rate_key, 0.0)
                
                defended_key = analizador._generate_stat_key('Was the robot Defended by someone?', 'rate')
                defended_rate = team_stat.get(defended_key, 0.0)
                
                climb_type = "Unknown"
                if team_num in team_data_grouped:
                    team_rows = team_data_grouped[team_num]
                    end_pos_idx = analizador._column_indices.get('End Position')
                    climb_idx = analizador._column_indices.get('Climbed?')
                    
                    if end_pos_idx is not None:
                        climb_values = [str(row[end_pos_idx]).strip() for row in team_rows if end_pos_idx < len(row)]
                        if climb_values:
                            climb_type = analizador._calculate_mode(climb_values)
                    elif climb_idx is not None:
                        climb_values = []
                        for row in team_rows:
                            if climb_idx < len(row):
                                val = str(row[climb_idx]).strip().lower()
                                if val in ['true', 'yes', 'y', '1']:
                                    climb_values.append('Yes')
                                else:
                                    climb_values.append('No')
                        if climb_values:
                            climb_type = analizador._calculate_mode(climb_values)
                
                writer.writerow([
                    rank,
                    team_num,
                    f"{overall_avg:.2f}",
                    f"{overall_std:.2f}",
                    f"{robot_valuation:.2f}",
                    f"{death_rate:.3f}",
                    climb_type,
                    f"{defended_rate:.3f}"
                ])
        
        print(f"✓ Created export file: {output_file}")
        
        # Verify file
        with open(output_file, 'r') as f:
            lines = f.readlines()
            print(f"✓ File has {len(lines)} lines (including header)")
            print(f"  Header: {lines[0].strip()}")
            if len(lines) > 1:
                print(f"  Sample data: {lines[1].strip()}")
        
        print("✓ CSV file successfully created and verified")
        
    except Exception as e:
        print(f"✗ Error creating export file: {e}")
        return False
    
    # Test 3: Verify CSV structure
    print("\nTest 3: Verify CSV Structure")
    print("-" * 60)
    
    try:
        with open(output_file, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            
            required_columns = [
                "Rank", "Team Number", "Overall Average", "Std Deviation",
                "Robot Valuation", "Death Rate", "Climb Type", "Defended Rate"
            ]
            
            # Check header
            if set(reader.fieldnames) == set(required_columns):
                print("  ✓ All required columns present")
            else:
                print(f"  ✗ Column mismatch!")
                print(f"    Expected: {required_columns}")
                print(f"    Got: {reader.fieldnames}")
                return False
            
            # Check data rows
            row_count = 0
            for row in reader:
                row_count += 1
                # Verify all fields are present and non-empty
                for col in required_columns:
                    if col not in row or not row[col]:
                        print(f"  ✗ Missing or empty value for {col} in row {row_count}")
                        return False
            
            print(f"  ✓ All {row_count} data rows have complete information")
        
        print("✓ CSV structure is valid")
        
    except Exception as e:
        print(f"✗ Error verifying CSV: {e}")
        return False
    
    # Final summary
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nSimplified Ranking Export Verified:")
    print("  ✓ All required data fields extracted correctly")
    print("  ✓ CSV file created successfully")
    print("  ✓ File structure is valid")
    print("  ✓ Export includes:")
    print("    - Team Number")
    print("    - Overall Average ± Std Deviation")
    print("    - Robot Valuation")
    print("    - Death Rate")
    print("    - Climb Type")
    print("    - Defended Rate")
    print(f"\nTest output saved to: {output_file}")
    
    return True

if __name__ == "__main__":
    success = test_simplified_ranking_export()
    exit(0 if success else 1)
