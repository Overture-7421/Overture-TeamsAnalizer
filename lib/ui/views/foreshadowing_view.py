"""
Foreshadowing View module for predictive simulation layouts.
Provides UI components for match prediction and simulation.
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple

# Lazy Plotly imports for Raspberry Pi optimization
_px = None
_go = None

def _ensure_plotly():
    """Lazy-load Plotly only when needed"""
    global _px, _go
    if _px is None:
        import plotly.express as px_module
        import plotly.graph_objects as go_module
        _px = px_module
        _go = go_module
    return _px, _go


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
            "Select Red Alliance (2 teams)",
            options=[label for label, _ in team_options],
            default=default_red,
            key="foreshadowing_red_multiselect"
        )
    
    with select_cols[1]:
        blue_labels = st.multiselect(
            "Select Blue Alliance (2 teams)",
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
    # Artifact breakdown
    artifact_df = _build_artifact_breakdown_df(breakdown)
    st.markdown("#### Artifact Contribution")
    st.dataframe(artifact_df, use_container_width=True)
    
    # Endgame breakdown
    endgame_df = _build_endgame_summary_df(breakdown)
    st.markdown("#### Endgame Summary")
    st.dataframe(endgame_df, use_container_width=True)
    
    # Endgame return per team
    endgame_team_df = _build_endgame_team_df(breakdown, get_team_display_label)
    st.markdown("#### Endgame Returns")
    st.dataframe(endgame_team_df, use_container_width=True)
    
    # Additional metrics
    st.markdown("#### Additional Metrics")
    st.write(
        f"Auto Leave: {breakdown['teams_left_auto_zone']}/2 | "
        f"Double Park Bonus: {'✅' if breakdown.get('double_park_bonus', 0) else '❌'}"
    )


def _build_artifact_breakdown_df(breakdown: Dict) -> pd.DataFrame:
    """Build artifact breakdown DataFrame."""
    return pd.DataFrame([
        {
            'Phase': 'Auto',
            'Classified': breakdown['auto_artifacts']['classified'],
            'Overflow': breakdown['auto_artifacts']['overflow'],
            'Depot': breakdown['auto_artifacts']['depot'],
            'Pattern Matches': breakdown['auto_artifacts']['pattern']
        },
        {
            'Phase': 'Teleop',
            'Classified': breakdown['teleop_artifacts']['classified'],
            'Overflow': breakdown['teleop_artifacts']['overflow'],
            'Depot': breakdown['teleop_artifacts']['depot'],
            'Failed': breakdown['teleop_artifacts']['failed'],
            'Pattern Matches': breakdown['teleop_artifacts']['pattern']
        }
    ])


def _build_endgame_summary_df(breakdown: Dict) -> pd.DataFrame:
    """Build endgame summary DataFrame."""
    return pd.DataFrame([
        {'Return': 'None', 'Teams': breakdown['endgame_returns']['none']},
        {'Return': 'Partial', 'Teams': breakdown['endgame_returns']['partial']},
        {'Return': 'Full', 'Teams': breakdown['endgame_returns']['full']},
        {'Return': 'Double Park Bonus', 'Teams': 1 if breakdown.get('double_park_bonus', 0) else 0}
    ])


def _build_endgame_team_df(breakdown: Dict, get_team_display_label: callable) -> pd.DataFrame:
    """Build endgame return per-team DataFrame."""
    rows = []
    for team, return_type, points in breakdown['endgame_scores']:
        rows.append({
            'Team': get_team_display_label(team),
            'Return': return_type.capitalize(),
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
            'Auto Classified': round(perf.auto_classified, 2),
            'Auto Overflow': round(perf.auto_overflow, 2),
            'Auto Depot': round(perf.auto_depot, 2),
            'Auto Pattern': round(perf.auto_pattern, 2),
            'Teleop Classified': round(perf.teleop_classified, 2),
            'Teleop Overflow': round(perf.teleop_overflow, 2),
            'Teleop Depot': round(perf.teleop_depot, 2),
            'Teleop Failed': round(perf.teleop_failed, 2),
            'Teleop Pattern': round(perf.teleop_pattern, 2),
            'Auto Leave %': round(perf.p_leave_auto_zone * 100, 1),
            'Expected Endgame': round(perf.expected_endgame_points(), 2)
        })
    st.dataframe(pd.DataFrame(rows), use_container_width=True)


def render_score_comparison_chart(prediction: Any) -> None:
    """Render score comparison bar chart."""
    score_components = [
        {'Alliance': 'Red', 'Component': 'Auto', 'Points': prediction.red_breakdown['auto_points']},
        {'Alliance': 'Red', 'Component': 'Teleop', 'Points': prediction.red_breakdown['teleop_points']},
        {'Alliance': 'Red', 'Component': 'Endgame', 'Points': prediction.red_breakdown['endgame_points']},
        {'Alliance': 'Blue', 'Component': 'Auto', 'Points': prediction.blue_breakdown['auto_points']},
        {'Alliance': 'Blue', 'Component': 'Teleop', 'Points': prediction.blue_breakdown['teleop_points']},
        {'Alliance': 'Blue', 'Component': 'Endgame', 'Points': prediction.blue_breakdown['endgame_points']}
    ]
    
    score_df = pd.DataFrame(score_components)
    px, go = _ensure_plotly()
    fig = px.bar(
        score_df,
        x='Alliance',
        y='Points',
        color='Component',
        barmode='stack',
        color_discrete_map={'Auto': '#60a5fa', 'Teleop': '#34d399', 'Endgame': '#a855f7'}
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
    
    # Teleop artifact comparison
    red_teleop_total = sum(prediction.red_breakdown['teleop_artifacts'].values())
    blue_teleop_total = sum(prediction.blue_breakdown['teleop_artifacts'].values())
    
    if red_teleop_total > blue_teleop_total * 1.2:
        st.write("Red shows a strong teleop artifact advantage. Blue should focus on defense or endgame points.")
    elif blue_teleop_total > red_teleop_total * 1.2:
        st.write("Blue shows a strong teleop artifact advantage. Red should prioritize efficient cycles.")
    else:
        st.write("Teleop artifacts are balanced. Endgame could decide the match.")
    
    st.caption("Foreshadowing simulations use historical averages and random sampling for variability.")
