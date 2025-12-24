"""
Foreshadowing View module for predictive simulation layouts.
Provides UI components for match prediction and simulation.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, List, Any, Optional, Tuple


def render_alliance_selectors(team_options: List[Tuple[str, str]], 
                               default_red: List[str],
                               default_blue: List[str]) -> Tuple[List[str], List[str]]:
    """
    Render alliance team selection controls.
    
    Args:
        team_options: List of (label, team_number) tuples
        default_red: Default red alliance teams
        default_blue: Default blue alliance teams
        
    Returns:
        Tuple[List[str], List[str]]: Selected (red_teams, blue_teams)
    """
    st.markdown("### Configure Alliances")
    select_cols = st.columns(2)
    
    with select_cols[0]:
        red_labels = st.multiselect(
            "Select Red Alliance (3 teams)",
            options=[label for label, _ in team_options],
            default=default_red,
            key="foreshadowing_red_multiselect"
        )
    
    with select_cols[1]:
        blue_labels = st.multiselect(
            "Select Blue Alliance (3 teams)",
            options=[label for label, _ in team_options],
            default=default_blue,
            key="foreshadowing_blue_multiselect"
        )
    
    return red_labels, blue_labels


def render_simulation_controls(current_iterations: int) -> Tuple[int, bool, bool]:
    """
    Render simulation control buttons and settings.
    
    Args:
        current_iterations: Current iteration count
        
    Returns:
        Tuple[int, bool, bool]: (iterations, run_quick, run_extended)
    """
    iterations = st.slider(
        "Iterations (quick simulation)",
        min_value=200,
        max_value=5000,
        value=current_iterations,
        step=100
    )
    
    button_cols = st.columns(2)
    with button_cols[0]:
        run_quick = st.button("Run Quick Prediction", use_container_width=True)
    with button_cols[1]:
        run_extended = st.button("Run Monte Carlo (5000 iterations)", use_container_width=True)
    
    return iterations, run_quick, run_extended


def render_prediction_results(prediction: Any, 
                               red_teams: List[str], 
                               blue_teams: List[str],
                               mode: str,
                               iterations: int,
                               get_team_display_label: callable) -> None:
    """
    Render prediction results.
    
    Args:
        prediction: MatchPrediction result
        red_teams: Red alliance team numbers
        blue_teams: Blue alliance team numbers
        mode: Simulation mode ("Quick" or "Monte Carlo")
        iterations: Number of iterations used
        get_team_display_label: Function to get team display labels
    """
    st.markdown(f"**Simulation Mode:** {mode} ({iterations} iterations)")
    
    # Score metrics
    score_cols = st.columns(3)
    with score_cols[0]:
        st.metric("Red Predicted Score", f"{prediction.red_score:.1f}")
    with score_cols[1]:
        st.metric("Blue Predicted Score", f"{prediction.blue_score:.1f}")
    with score_cols[2]:
        diff = prediction.red_score - prediction.blue_score
        st.metric("Score Differential", f"{diff:.1f}", delta=f"{diff:+.1f}")
    
    # Probability metrics
    prob_cols = st.columns(3)
    with prob_cols[0]:
        st.metric("Red Win %", f"{prediction.red_win_probability*100:.1f}%")
    with prob_cols[1]:
        st.metric("Blue Win %", f"{prediction.blue_win_probability*100:.1f}%")
    with prob_cols[2]:
        st.metric("Tie %", f"{prediction.tie_probability*100:.1f}%")
    
    # RP metrics
    rp_cols = st.columns(2)
    with rp_cols[0]:
        st.metric("Red RP", prediction.red_rp)
    with rp_cols[1]:
        st.metric("Blue RP", prediction.blue_rp)
    
    # Alliance rosters
    st.markdown("### Alliance Rosters")
    roster_cols = st.columns(2)
    with roster_cols[0]:
        st.markdown("**Red Alliance**")
        for team in red_teams:
            st.markdown(f"- {get_team_display_label(team)}")
    with roster_cols[1]:
        st.markdown("**Blue Alliance**")
        for team in blue_teams:
            st.markdown(f"- {get_team_display_label(team)}")


def render_breakdown_tabs(prediction: Any, 
                          red_performance: List[Any],
                          blue_performance: List[Any],
                          get_team_display_label: callable) -> None:
    """
    Render detailed breakdown tabs.
    
    Args:
        prediction: MatchPrediction result
        red_performance: Red team performances
        blue_performance: Blue team performances
        get_team_display_label: Function to get team display labels
    """
    breakdown_tabs = st.tabs(["🔴 Red Breakdown", "🔵 Blue Breakdown", "📊 Team Profiles"])
    
    with breakdown_tabs[0]:
        _render_alliance_breakdown(prediction.red_breakdown, get_team_display_label)
    
    with breakdown_tabs[1]:
        _render_alliance_breakdown(prediction.blue_breakdown, get_team_display_label)
    
    with breakdown_tabs[2]:
        _render_team_profiles(red_performance + blue_performance, get_team_display_label)


def _render_alliance_breakdown(breakdown: Dict, get_team_display_label: callable) -> None:
    """Render breakdown for a single alliance."""
    # Coral breakdown
    coral_df = _build_coral_breakdown_df(breakdown)
    st.markdown("#### Coral Contribution")
    st.dataframe(coral_df, use_container_width=True)
    
    # Algae breakdown
    algae_df = _build_algae_summary_df(breakdown)
    st.markdown("#### Algae Summary")
    st.dataframe(algae_df, use_container_width=True)
    
    # Climb breakdown
    climb_df = _build_climb_breakdown_df(breakdown, get_team_display_label)
    st.markdown("#### Climb Performance")
    st.dataframe(climb_df, use_container_width=True)
    
    # Additional metrics
    st.markdown("#### Additional Metrics")
    st.write(
        f"Auto Zone: {breakdown['teams_left_auto_zone']}/3 | "
        f"Cooperation: {'✅' if breakdown['cooperation_achieved'] else '❌'}"
    )


def _build_coral_breakdown_df(breakdown: Dict) -> pd.DataFrame:
    """Build coral breakdown DataFrame."""
    levels = ['L1', 'L2', 'L3', 'L4']
    data = {
        'Level': levels,
        'Auto': [breakdown['auto_coral'][lvl] for lvl in levels],
        'Teleop': [breakdown['teleop_coral'][lvl] for lvl in levels],
        'Total': [breakdown['coral_scores'][lvl] for lvl in levels]
    }
    return pd.DataFrame(data)


def _build_algae_summary_df(breakdown: Dict) -> pd.DataFrame:
    """Build algae summary DataFrame."""
    return pd.DataFrame([
        {'Phase': 'Auto Processor', 'Pieces': breakdown['processor_algae']['auto']},
        {'Phase': 'Teleop Processor', 'Pieces': breakdown['processor_algae']['teleop']},
        {'Phase': 'Teleop Net', 'Pieces': breakdown['net_algae']}
    ])


def _build_climb_breakdown_df(breakdown: Dict, get_team_display_label: callable) -> pd.DataFrame:
    """Build climb breakdown DataFrame."""
    rows = []
    for team, climb_type, points in breakdown['climb_scores']:
        rows.append({
            'Team': get_team_display_label(team),
            'Action': climb_type.capitalize(),
            'Points': points
        })
    return pd.DataFrame(rows)


def _render_team_profiles(team_performances: List[Any], 
                          get_team_display_label: callable) -> None:
    """Render team performance profiles."""
    rows = []
    for perf in team_performances:
        rows.append({
            'Team': get_team_display_label(perf.team_number),
            'Auto L1': round(perf.auto_L1, 2),
            'Auto L2': round(perf.auto_L2, 2),
            'Auto L3': round(perf.auto_L3, 2),
            'Auto L4': round(perf.auto_L4, 2),
            'Teleop L1': round(perf.teleop_L1, 2),
            'Teleop L2': round(perf.teleop_L2, 2),
            'Teleop L3': round(perf.teleop_L3, 2),
            'Teleop L4': round(perf.teleop_L4, 2),
            'Processor Auto': round(perf.auto_processor, 2),
            'Processor Teleop': round(perf.teleop_processor, 2),
            'Net Algae': round(perf.teleop_net, 2),
            'Auto Leave %': round(perf.p_leave_auto_zone * 100, 1),
            'Cooperation %': round(perf.p_cooperation * 100, 1),
            'Expected Climb': round(perf.expected_climb_points(), 2)
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)


def render_score_comparison_chart(prediction: Any) -> None:
    """Render score comparison bar chart."""
    score_components = [
        {'Alliance': 'Red', 'Component': 'Coral', 'Points': prediction.red_breakdown['coral_points']},
        {'Alliance': 'Red', 'Component': 'Algae', 'Points': prediction.red_breakdown['algae_points']},
        {'Alliance': 'Red', 'Component': 'Climb', 'Points': prediction.red_breakdown['climb_points']},
        {'Alliance': 'Blue', 'Component': 'Coral', 'Points': prediction.blue_breakdown['coral_points']},
        {'Alliance': 'Blue', 'Component': 'Algae', 'Points': prediction.blue_breakdown['algae_points']},
        {'Alliance': 'Blue', 'Component': 'Climb', 'Points': prediction.blue_breakdown['climb_points']}
    ]
    
    score_df = pd.DataFrame(score_components)
    fig = px.bar(
        score_df,
        x='Alliance',
        y='Points',
        color='Component',
        barmode='stack',
        color_discrete_map={'Coral': '#ef4444', 'Algae': '#22d3ee', 'Climb': '#a855f7'}
    )
    fig.update_layout(
        title="Score Breakdown",
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#f5f5f5')
    )
    st.plotly_chart(fig, use_container_width=True)


def render_strategic_notes(prediction: Any) -> None:
    """Render strategic notes and recommendations."""
    st.markdown("### Strategic Notes")
    
    diff_probability = abs(prediction.red_win_probability - prediction.blue_win_probability)
    if diff_probability > 0.3:
        confidence = "High"
    elif diff_probability > 0.1:
        confidence = "Medium"
    else:
        confidence = "Low"
    
    if prediction.red_score > prediction.blue_score:
        favorite = "Red"
    elif prediction.blue_score > prediction.red_score:
        favorite = "Blue"
    else:
        favorite = "Even"
    
    st.write(f"Confidence level: **{confidence}** | Favorite alliance: **{favorite}**")
    
    # Coral comparison
    red_coral_total = sum(prediction.red_breakdown['coral_scores'].values())
    blue_coral_total = sum(prediction.blue_breakdown['coral_scores'].values())
    
    if red_coral_total > blue_coral_total * 1.2:
        st.write("Red shows a strong coral advantage. Blue should focus on defense or endgame points.")
    elif blue_coral_total > red_coral_total * 1.2:
        st.write("Blue shows a strong coral advantage. Red should prioritize efficiency in grid cycles.")
    else:
        st.write("Coral cycles are balanced. Endgame and algae control will likely decide the match.")
    
    st.caption("Foreshadowing simulations use historical averages and random sampling for variability.")
