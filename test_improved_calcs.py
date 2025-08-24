#!/usr/bin/env python3
"""
Test script to verify improved overall and robot valuation calculations
"""

from main import AnalizadorRobot
from config_manager import ConfigManager
import csv
import io

def test_improved_calculations():
    """Test the improved overall and robot valuation calculations"""
    
    print("=== Testing Improved Overall and Robot Valuation Calculations ===")
    
    # Create test data with new format
    test_data = """Scouter Initials,Match Number,Robot,Future Alliance,Team Number,Starting Position,No Show,Moved (Auto),Coral L1 (Auto),Coral L2 (Auto),Coral L3 (Auto),Coral L4 (Auto),Barge Algae (Auto),Processor Algae (Auto),Dislodged Algae (Auto),Foul (Auto),Dislodged Algae (Teleop),Pickup Location,Coral L1 (Teleop),Coral L2 (Teleop),Coral L3 (Teleop),Coral L4 (Teleop),Barge Algae (Teleop),Processor Algae (Teleop),Crossed Field/Defense,Tipped/Fell,Touched Opposing Cage,Died,End Position,Broke,Defended,Coral HP Mistake,Yellow/Red Card
ABC,1,1,false,1234,Center,false,true,2,1,1,0,1,0,false,false,false,Source,3,2,2,1,2,1,true,false,0,false,Deep Climb,false,false,false,false
ABC,2,1,false,1234,Center,false,true,1,2,1,1,0,1,false,false,false,Source,2,3,1,2,1,0,false,false,0,false,Shallow Climb,false,false,false,false
ABC,3,1,false,1234,Center,false,false,0,1,2,1,1,0,false,false,false,Source,4,1,3,1,3,2,true,false,0,false,Parked,false,false,false,false
DEF,1,1,false,5678,Left,false,true,1,0,0,0,0,0,false,false,false,Source,1,1,0,0,1,0,false,false,0,false,None,false,false,false,false
DEF,2,1,false,5678,Left,false,false,0,1,1,0,1,0,false,false,false,Source,2,2,1,1,0,1,true,false,0,false,Deep Climb,false,false,false,false"""
    
    # Create analyzer and load test data
    analyzer = AnalizadorRobot()
    
    # Parse CSV data
    lines = test_data.strip().split('\n')
    analyzer.sheet_data = [line.split(',') for line in lines]
    analyzer._update_column_indices()
    
    print(f"Loaded {len(analyzer.sheet_data)-1} test matches")
    print(f"Headers: {len(analyzer.sheet_data[0])} columns")
    
    # Get team stats
    stats = analyzer.get_detailed_team_stats()
    
    print("\n=== Team Statistics Comparison ===")
    
    for team_stat in stats:
        team = team_stat['team']
        overall_avg = team_stat['overall_avg']
        robot_val = team_stat['RobotValuation']
        
        print(f"\nTeam {team}:")
        print(f"  Overall Average: {overall_avg:.2f}")
        print(f"  Robot Valuation: {robot_val:.2f}")
        
        # Show individual coral/algae stats for comparison
        for key, value in team_stat.items():
            if 'coral' in key.lower() and 'avg' in key:
                print(f"  {key}: {value:.2f}")
            elif 'algae' in key.lower() and 'avg' in key:
                print(f"  {key}: {value:.2f}")
    
    # Test specific calculation details
    print("\n=== Calculation Details ===")
    team_1234_data = analyzer.get_team_data_grouped().get('1234', [])
    if team_1234_data:
        print(f"Team 1234 has {len(team_1234_data)} matches")
        
        # Manual calculation example for first match
        first_match = team_1234_data[0]
        print("First match raw data (relevant columns):")
        
        coral_columns = ['Coral L1 (Auto)', 'Coral L2 (Auto)', 'Coral L3 (Auto)', 'Coral L4 (Auto)',
                        'Coral L1 (Teleop)', 'Coral L2 (Teleop)', 'Coral L3 (Teleop)', 'Coral L4 (Teleop)']
        
        manual_score = 0
        for col in coral_columns:
            idx = analyzer._column_indices.get(col)
            if idx is not None and idx < len(first_match):
                val = float(first_match[idx])
                level = col.split()[1]
                phase = 'Auto' if 'Auto' in col else 'Teleop'
                
                weight = {'L1': 2, 'L2': 3, 'L3': 4, 'L4': 5}[level]
                multiplier = 2.0 if phase == 'Auto' else 1.0
                points = val * weight * multiplier
                manual_score += points
                
                print(f"  {col}: {val} * {weight} * {multiplier} = {points} points")
        
        print(f"Manual calculated score for first match: {manual_score}")
    
    print("\n=== Test completed! ===")
    print("The new calculations should show much higher and more meaningful values.")
    print("Overall averages should be comparable to individual coral/algae stats.")

if __name__ == "__main__":
    test_improved_calculations()
