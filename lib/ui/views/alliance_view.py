"""
Alliance View module for the drafting interface.
Provides UI components for alliance selection and management.
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional


def render_alliance_table(selector: Any, tba_manager: Optional[Any] = None) -> None:
    """
    Render the alliance selections table.
    
    Args:
        selector: AllianceSelector instance
        tba_manager: Optional TBA manager for team names
    """
    alliance_table_data = selector.get_alliance_table()
    
    # Replace team numbers with names if TBA manager available
    if tba_manager:
        for row in alliance_table_data:
            for col in ['Captain', 'Pick 1', 'Pick 2', 'Recommendation 1', 'Recommendation 2']:
                if row[col]:
                    num = row[col]
                    name = tba_manager.get_team_nickname(num)
                    row[col] = f"{num} - {name}"
    
    df_alliances = pd.DataFrame(alliance_table_data)
    st.dataframe(df_alliances, use_container_width=True, height=325)


def render_quick_actions(selector: Any) -> tuple:
    """
    Render quick action buttons for alliance selector.
    
    Args:
        selector: AllianceSelector instance
        
    Returns:
        tuple: (auto_optimize_pressed, reset_pressed)
    """
    st.markdown("### Quick Actions")
    
    auto_optimize = st.button("Auto-Optimize All", use_container_width=True)
    reset = st.button("Reset All Picks", use_container_width=True)
    
    return auto_optimize, reset


def render_alliance_configuration(selector: Any, 
                                   tba_manager: Optional[Any] = None) -> bool:
    """
    Render manual alliance configuration interface.
    
    Args:
        selector: AllianceSelector instance
        tba_manager: Optional TBA manager for team names
        
    Returns:
        bool: True if any changes were made
    """
    changes_made = False
    alliances = selector.alliances
    
    with st.expander("Configure Individual Alliances"):
        cols = st.columns(len(alliances))
        
        for i, a in enumerate(alliances):
            with cols[i]:
                st.markdown(f"**Alliance {a.allianceNumber}**")
                
                # Captain selection
                available_captains = selector.get_available_captains(i)
                
                if tba_manager:
                    captain_options = {team.team: f"{team.team} - {team.name}" for team in available_captains}
                    captain_options[0] = "Auto"
                    
                    if a.captain and a.captain not in captain_options:
                        captain_options[a.captain] = f"{a.captain} - {tba_manager.get_team_nickname(a.captain)}"
                    
                    selected_captain = st.selectbox(
                        f"Captain A{a.allianceNumber}",
                        options=list(captain_options.keys()),
                        format_func=lambda x: captain_options.get(x, "Auto"),
                        key=f"captain_{i}",
                        index=list(captain_options.keys()).index(a.captain) if a.captain in captain_options else 0
                    )
                else:
                    captain_options = [team.team for team in available_captains]
                    captain_options.insert(0, 0)
                    selected_captain = st.selectbox(
                        f"Captain A{a.allianceNumber}",
                        options=captain_options,
                        key=f"captain_{i}",
                        index=captain_options.index(a.captain) if a.captain in captain_options else 0
                    )
                
                current_captain_value = a.captain if a.captain is not None else 0
                if selected_captain != current_captain_value:
                    try:
                        selector.set_captain(i, selected_captain if selected_captain != 0 else None)
                        changes_made = True
                    except ValueError as e:
                        st.error(str(e))
                
                # Pick selections
                available_teams = selector.get_available_teams(a.captainRank, 'pick1')
                
                if tba_manager:
                    team_options = {team.team: f"{team.team} - {team.name}" for team in available_teams}
                    team_options[0] = "None"
                    
                    for pick in [a.pick1, a.pick2]:
                        if pick and pick not in team_options:
                            team_options[pick] = f"{pick} - {tba_manager.get_team_nickname(pick)}"
                else:
                    team_options = {team.team: team.team for team in available_teams}
                    team_options[0] = "None"
                
                # Pick 1
                pick1_val = a.pick1 if a.pick1 in team_options else 0
                selected_pick1 = st.selectbox(
                    f"Pick 1 A{a.allianceNumber}",
                    options=list(team_options.keys()),
                    format_func=lambda x: team_options.get(x, "None"),
                    key=f"pick1_{i}",
                    index=list(team_options.keys()).index(pick1_val)
                )
                
                current_pick1_value = a.pick1 if a.pick1 is not None else 0
                if selected_pick1 != current_pick1_value:
                    try:
                        selector.set_pick(i, 'pick1', selected_pick1 if selected_pick1 != 0 else None)
                        changes_made = True
                    except ValueError as e:
                        st.error(str(e))
                
                # Pick 2
                pick2_val = a.pick2 if a.pick2 in team_options else 0
                selected_pick2 = st.selectbox(
                    f"Pick 2 A{a.allianceNumber}",
                    options=list(team_options.keys()),
                    format_func=lambda x: team_options.get(x, "None"),
                    key=f"pick2_{i}",
                    index=list(team_options.keys()).index(pick2_val)
                )
                
                current_pick2_value = a.pick2 if a.pick2 is not None else 0
                if selected_pick2 != current_pick2_value:
                    try:
                        selector.set_pick(i, 'pick2', selected_pick2 if selected_pick2 != 0 else None)
                        changes_made = True
                    except ValueError as e:
                        st.error(str(e))
    
    return changes_made


def auto_optimize_alliances(selector: Any) -> bool:
    """
    Automatically optimize alliance selections.
    
    Args:
        selector: AllianceSelector instance
        
    Returns:
        bool: True if changes were made
    """
    made_changes = False
    
    # Pick 1 round (highest seeds first)
    for alliance in selector.alliances:
        if not alliance.captain or alliance.pick1:
            continue
        available_teams = selector.get_available_teams(alliance.captainRank, 'pick1')
        if available_teams:
            selector.set_pick(alliance.allianceNumber - 1, 'pick1', available_teams[0].team)
            made_changes = True
    
    # Pick 2 round (snake order)
    for alliance in reversed(selector.alliances):
        if not alliance.captain or alliance.pick2:
            continue
        available_teams = selector.get_available_teams(alliance.captainRank, 'pick2')
        if available_teams:
            selector.set_pick(alliance.allianceNumber - 1, 'pick2', available_teams[0].team)
            made_changes = True
    
    return made_changes
