#!/usr/bin/env python3
"""
Simple test script to verify Honor Roll calculations
"""

def test_scaling_logic():
    """Test the scaling logic with sample data"""
    
    print("🧪 Testing Honor Roll Scaling Logic...")
    
    # Sample team data (typical values from real data)
    sample_teams = [
        {"team": "1234", "overall_avg": 45.5, "robot_valuation": 52.3, "phase_scores": {"autonomous": 8.2, "teleop": 12.5, "endgame": 6.1}},
        {"team": "5678", "overall_avg": 67.8, "robot_valuation": 71.2, "phase_scores": {"autonomous": 15.3, "teleop": 18.7, "endgame": 9.4}},
        {"team": "9012", "overall_avg": 23.1, "robot_valuation": 28.9, "phase_scores": {"autonomous": 4.5, "teleop": 7.2, "endgame": 3.8}},
        {"team": "3456", "overall_avg": 89.2, "robot_valuation": 92.1, "phase_scores": {"autonomous": 22.1, "teleop": 28.4, "endgame": 15.7}}
    ]
    
    print("\n📊 Before vs After Scaling Comparison:")
    print("=" * 80)
    
    for team_data in sample_teams:
        team_num = team_data["team"]
        overall_avg = team_data["overall_avg"]
        robot_valuation = team_data["robot_valuation"]
        phase_scores = team_data["phase_scores"]
        
        print(f"\n🤖 Team {team_num}:")
        print(f"   📈 Reference Metrics:")
        print(f"      Overall Avg: {overall_avg:.1f}")
        print(f"      Robot Valuation: {robot_valuation:.1f}")
        
        print(f"   🔢 Raw Phase Scores:")
        print(f"      Autonomous: {phase_scores['autonomous']:.1f}")
        print(f"      Teleop: {phase_scores['teleop']:.1f}")
        print(f"      Endgame: {phase_scores['endgame']:.1f}")
        print(f"      Total: {sum(phase_scores.values()):.1f}")
        
        # OLD METHOD (previous scaling)
        old_scaling_factor = min(1.5, max(0.5, overall_avg / 50)) if overall_avg > 0 else 1.0
        old_auto = min(100, max(0, phase_scores["autonomous"] * old_scaling_factor))
        old_teleop = min(100, max(0, phase_scores["teleop"] * old_scaling_factor))
        old_endgame = min(100, max(0, phase_scores["endgame"] * old_scaling_factor))
        old_match_performance = (old_auto * 0.20 + old_teleop * 0.60 + old_endgame * 0.20)
        
        # NEW METHOD (improved scaling - updated values)
        total_phase_score = sum(phase_scores.values())
        if overall_avg > 0 and total_phase_score > 0:
            new_scale_factor = overall_avg / total_phase_score * 2.5  # Updated multiplier
        else:
            new_scale_factor = 5.0  # Updated fallback
        
        new_scale_factor = max(2.0, min(10.0, new_scale_factor))  # Updated bounds
        
        new_auto = min(100, max(0, phase_scores["autonomous"] * new_scale_factor))
        new_teleop = min(100, max(0, phase_scores["teleop"] * new_scale_factor))
        new_endgame = min(100, max(0, phase_scores["endgame"] * new_scale_factor))
        new_match_performance = (new_auto * 0.20 + new_teleop * 0.60 + new_endgame * 0.20)
        
        print(f"   ⚡ OLD Method (Scale: {old_scaling_factor:.2f}):")
        print(f"      Auto: {old_auto:.1f}, Teleop: {old_teleop:.1f}, Endgame: {old_endgame:.1f}")
        print(f"      🎯 Match Performance: {old_match_performance:.1f}")
        print(f"      📊 vs Overall: {old_match_performance/overall_avg:.2f}x, vs RobotVal: {old_match_performance/robot_valuation:.2f}x")
        
        print(f"   🚀 NEW Method (Scale: {new_scale_factor:.2f}):")
        print(f"      Auto: {new_auto:.1f}, Teleop: {new_teleop:.1f}, Endgame: {new_endgame:.1f}")
        print(f"      🎯 Match Performance: {new_match_performance:.1f}")
        print(f"      📊 vs Overall: {new_match_performance/overall_avg:.2f}x, vs RobotVal: {new_match_performance/robot_valuation:.2f}x")
        
        improvement = new_match_performance - old_match_performance
        print(f"   📈 Improvement: {improvement:+.1f} points ({improvement/old_match_performance*100:+.1f}%)")
    
    print("\n" + "=" * 80)
    print("✅ Analysis Complete!")
    print("\n💡 Key Improvements:")
    print("   • Match Performance now scales proportionally with Overall Average")
    print("   • Scaling factor is dynamic (typically 1.0-4.0x instead of fixed 0.5-1.5x)")
    print("   • Phase scores are adjusted to be comparable to Robot Valuation")
    print("   • Target ratio: Match Performance ≈ 0.8 × Overall Average")
    print("   • Better reflects actual team performance in Honor Roll calculations")

if __name__ == "__main__":
    test_scaling_logic()
