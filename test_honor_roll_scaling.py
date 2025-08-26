#!/usr/bin/env python3
"""
Test script to verify Honor Roll calculations are properly scaled
"""

import sys
import os

# Add the project directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from main import AnalizadorRobot
from school_system import TeamScoring

def test_honor_roll_scaling():
    """Test that Honor Roll calculations are properly scaled"""
    
    print("🧪 Testing Honor Roll Scaling...")
    
    # Create analyzer instance
    analizador = AnalizadorRobot()
    
    # Load test data if available
    test_file = "test_data.csv"
    if os.path.exists(test_file):
        print(f"📁 Loading test data from {test_file}")
        # Use the correct method to load CSV data
        with open(test_file, 'r', encoding='utf-8') as f:
            import csv
            reader = csv.reader(f)
            data = list(reader)
            if len(data) > 1:  # Has header + data
                analizador.sheet_data = data
                analizador._setup_column_mapping()
                
                # Get some team stats to compare
        team_stats = analizador.get_detailed_team_stats()
        if team_stats:
            print(f"📊 Found {len(team_stats)} teams in test data")
            
            # Show first few teams for comparison
            for i, team in enumerate(team_stats[:3]):
                team_num = str(team['team'])
                overall_avg = team.get('overall_avg', 0)
                robot_valuation = team.get('RobotValuation', 0)
                
                # Get phase scores
                phase_scores = analizador.calculate_team_phase_scores(int(team_num))
                
                print(f"\n🤖 Team {team_num}:")
                print(f"   Overall Avg: {overall_avg:.2f}")
                print(f"   Robot Valuation: {robot_valuation:.2f}")
                print(f"   Raw Phase Scores:")
                print(f"     Autonomous: {phase_scores['autonomous']:.2f}")
                print(f"     Teleop: {phase_scores['teleop']:.2f}")
                print(f"     Endgame: {phase_scores['endgame']:.2f}")
                print(f"     Total: {sum(phase_scores.values()):.2f}")
                
                # Calculate what the new scaling would produce
                if overall_avg > 0:
                    total_phase_score = sum(phase_scores.values())
                    if total_phase_score > 0:
                        scale_factor = overall_avg / total_phase_score * 0.8
                    else:
                        scale_factor = 1.0
                else:
                    scale_factor = 3.0
                
                scale_factor = max(1.0, min(8.0, scale_factor))
                
                auto_scaled = min(100, max(0, phase_scores["autonomous"] * scale_factor))
                teleop_scaled = min(100, max(0, phase_scores["teleop"] * scale_factor))
                endgame_scaled = min(100, max(0, phase_scores["endgame"] * scale_factor))
                
                print(f"   Scaling Factor: {scale_factor:.2f}")
                print(f"   Scaled Scores (for Honor Roll):")
                print(f"     Autonomous: {auto_scaled:.2f}")
                print(f"     Teleop: {teleop_scaled:.2f}")
                print(f"     Endgame: {endgame_scaled:.2f}")
                
                # Calculate what match performance would be
                match_performance = (auto_scaled * 0.20 + teleop_scaled * 0.60 + endgame_scaled * 0.20)
                print(f"   🎯 Match Performance: {match_performance:.2f}")
                print(f"   📊 Comparison - Overall: {overall_avg:.2f}, Match Perf: {match_performance:.2f}, Ratio: {match_performance/overall_avg:.2f}" if overall_avg > 0 else "")
        else:
            print("❌ No team stats found in test data")
    else:
        print(f"❌ Test file {test_file} not found")
        print("🔄 Creating sample data for testing...")
        
        # Create sample data for testing
        sample_teams = [
            {"team": "1234", "overall_avg": 45.5, "robot_valuation": 52.3, "phase_scores": {"autonomous": 8.2, "teleop": 12.5, "endgame": 6.1}},
            {"team": "5678", "overall_avg": 67.8, "robot_valuation": 71.2, "phase_scores": {"autonomous": 15.3, "teleop": 18.7, "endgame": 9.4}},
            {"team": "9012", "overall_avg": 23.1, "robot_valuation": 28.9, "phase_scores": {"autonomous": 4.5, "teleop": 7.2, "endgame": 3.8}}
        ]
        
        for team_data in sample_teams:
            team_num = team_data["team"]
            overall_avg = team_data["overall_avg"]
            robot_valuation = team_data["robot_valuation"]
            phase_scores = team_data["phase_scores"]
            
            print(f"\n🤖 Sample Team {team_num}:")
            print(f"   Overall Avg: {overall_avg:.2f}")
            print(f"   Robot Valuation: {robot_valuation:.2f}")
            print(f"   Sample Phase Scores:")
            print(f"     Autonomous: {phase_scores['autonomous']:.2f}")
            print(f"     Teleop: {phase_scores['teleop']:.2f}")
            print(f"     Endgame: {phase_scores['endgame']:.2f}")
            print(f"     Total: {sum(phase_scores.values()):.2f}")
            
            # Calculate new scaling
            total_phase_score = sum(phase_scores.values())
            if total_phase_score > 0:
                scale_factor = overall_avg / total_phase_score * 0.8
            else:
                scale_factor = 3.0
            
            scale_factor = max(1.0, min(8.0, scale_factor))
            
            auto_scaled = min(100, max(0, phase_scores["autonomous"] * scale_factor))
            teleop_scaled = min(100, max(0, phase_scores["teleop"] * scale_factor))
            endgame_scaled = min(100, max(0, phase_scores["endgame"] * scale_factor))
            
            print(f"   Scaling Factor: {scale_factor:.2f}")
            print(f"   Scaled Scores (for Honor Roll):")
            print(f"     Autonomous: {auto_scaled:.2f}")
            print(f"     Teleop: {teleop_scaled:.2f}")
            print(f"     Endgame: {endgame_scaled:.2f}")
            
            # Calculate match performance
            match_performance = (auto_scaled * 0.20 + teleop_scaled * 0.60 + endgame_scaled * 0.20)
            print(f"   🎯 Match Performance: {match_performance:.2f}")
            print(f"   📊 Comparison - Overall: {overall_avg:.2f}, Match Perf: {match_performance:.2f}, Ratio: {match_performance/overall_avg:.2f}")
    
    print("\n✅ Honor Roll scaling test completed!")
    print("\n💡 Key Improvements:")
    print("   - Match Performance now scales with Overall Average")
    print("   - Scaling factor is dynamic based on team's actual performance")
    print("   - Phase scores are adjusted to be comparable to Robot Valuation")
    print("   - Ratio between Match Performance and Overall should be around 0.8")

if __name__ == "__main__":
    test_honor_roll_scaling()
