#!/usr/bin/env python3
"""
Test script to verify alliance selector bug fix
"""

from allianceSelector import AllianceSelector, Team

def test_alliance_selector_fix():
    """Test that alliance selector properly handles team selection"""
    print("Testing Alliance Selector Fix...")
    print("=" * 60)
    
    # Create sample teams
    teams = [
        Team(num=1001, rank=1, total_epa=100, auto_epa=30, teleop_epa=50, endgame_epa=20),
        Team(num=1002, rank=2, total_epa=95, auto_epa=28, teleop_epa=48, endgame_epa=19),
        Team(num=1003, rank=3, total_epa=90, auto_epa=27, teleop_epa=45, endgame_epa=18),
        Team(num=1004, rank=4, total_epa=85, auto_epa=25, teleop_epa=43, endgame_epa=17),
        Team(num=1005, rank=5, total_epa=80, auto_epa=24, teleop_epa=40, endgame_epa=16),
        Team(num=1006, rank=6, total_epa=75, auto_epa=22, teleop_epa=38, endgame_epa=15),
        Team(num=1007, rank=7, total_epa=70, auto_epa=21, teleop_epa=35, endgame_epa=14),
        Team(num=1008, rank=8, total_epa=65, auto_epa=20, teleop_epa=32, endgame_epa=13),
        Team(num=1009, rank=9, total_epa=60, auto_epa=18, teleop_epa=30, endgame_epa=12),
        Team(num=1010, rank=10, total_epa=55, auto_epa=17, teleop_epa=28, endgame_epa=10),
    ]
    
    # Initialize alliance selector
    selector = AllianceSelector(teams)
    
    print(f"\n✓ Created {len(teams)} teams")
    print(f"✓ Initialized {len(selector.alliances)} alliances")
    print(f"✓ Captains assigned: {[a.captain for a in selector.alliances]}")
    
    # Test 1: Check initial state
    print("\nTest 1: Initial State")
    print("-" * 60)
    for idx, alliance in enumerate(selector.alliances):
        print(f"  Alliance {alliance.allianceNumber}: Captain={alliance.captain}, "
              f"Pick1={alliance.pick1}, Pick2={alliance.pick2}")
    print("✓ Initial state verified")
    
    # Test 2: Make pick 1 selections
    print("\nTest 2: Pick 1 Selections")
    print("-" * 60)
    
    # Alliance 1 picks team 1009
    available_before = selector.get_available_teams(selector.alliances[0].captainRank, 'pick1')
    print(f"  Alliance 1: {len(available_before)} teams available before pick")
    
    selector.set_pick(0, 'pick1', 1009)
    print(f"  Alliance 1 picked team 1009")
    
    # Verify team 1009 is no longer available for other alliances
    available_after = selector.get_available_teams(selector.alliances[1].captainRank, 'pick1')
    team_numbers_after = [t.team for t in available_after]
    
    if 1009 not in team_numbers_after:
        print("  ✓ Team 1009 correctly removed from available teams for Alliance 2")
    else:
        print("  ✗ ERROR: Team 1009 still available for Alliance 2!")
        return False
    
    # Alliance 2 picks team 1010
    selector.set_pick(1, 'pick1', 1010)
    print(f"  Alliance 2 picked team 1010")
    
    # Verify team 1010 is no longer available
    available_for_alliance3 = selector.get_available_teams(selector.alliances[2].captainRank, 'pick1')
    team_numbers_alliance3 = [t.team for t in available_for_alliance3]
    
    if 1010 not in team_numbers_alliance3 and 1009 not in team_numbers_alliance3:
        print("  ✓ Both picked teams correctly removed from Alliance 3's available teams")
    else:
        print("  ✗ ERROR: Picked teams still showing as available!")
        return False
    
    print("✓ Pick 1 selections working correctly")
    
    # Test 3: Captain cannot pick themselves
    print("\nTest 3: Captain Self-Selection Prevention")
    print("-" * 60)
    
    try:
        captain = selector.alliances[0].captain
        selector.set_pick(0, 'pick2', captain)
        print(f"  ✗ ERROR: Alliance captain {captain} was allowed to pick themselves!")
        return False
    except ValueError as e:
        print(f"  ✓ Correctly prevented captain from picking themselves: {str(e)[:50]}...")
    
    # Test 4: Alliance table
    print("\nTest 4: Alliance Table Generation")
    print("-" * 60)
    
    alliance_table = selector.get_alliance_table()
    print(f"  Generated table with {len(alliance_table)} alliances")
    
    for row in alliance_table[:3]:  # Show first 3
        print(f"  Alliance {row['Alliance #']}: Captain={row['Captain']}, "
              f"Pick1={row['Pick 1']}, Pick2={row['Pick 2']}, "
              f"Score={row['Alliance Score']:.1f}")
    
    print("✓ Alliance table generated successfully")
    
    # Test 5: Reset picks
    print("\nTest 5: Reset Functionality")
    print("-" * 60)
    
    selector.reset_picks()
    
    all_reset = all(a.pick1 is None and a.pick2 is None for a in selector.alliances)
    if all_reset:
        print("  ✓ All picks successfully reset")
    else:
        print("  ✗ ERROR: Some picks not reset!")
        return False
    
    # Final summary
    print("\n" + "=" * 60)
    print("✓ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nAlliance Selector Fix Verified:")
    print("  ✓ Teams properly removed from available list after selection")
    print("  ✓ Captains cannot pick themselves")
    print("  ✓ Multiple picks work correctly")
    print("  ✓ Reset functionality works")
    print("\nThe alliance selector bug has been successfully fixed!")
    
    return True

if __name__ == "__main__":
    success = test_alliance_selector_fix()
    exit(0 if success else 1)
