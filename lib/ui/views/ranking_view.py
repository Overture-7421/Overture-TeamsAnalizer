"""
Ranking View module for Honor Roll visualization.
Provides UI components for displaying team rankings and Honor Roll data.
"""

import streamlit as st
import pandas as pd
from typing import Dict, List, Any, Optional

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


def render_honor_roll_table(rankings: List[tuple], 
                            school_system: Any,
                            toa_manager: Optional[Any] = None) -> None:
    """
    Render the Honor Roll rankings table.
    
    Args:
        rankings: List of (team_num, results) tuples from school_system.get_honor_roll_ranking()
        school_system: TeamScoring instance
        toa_manager: Optional TOA manager for team names
    """
    ranking_data = []
    team_numbers_list = []
    
    for rank, (team_num, results) in enumerate(rankings, 1):
        team_name = toa_manager.get_team_nickname(team_num) if toa_manager else None
        c, sc, rp = school_system.calculate_competencies_score(team_num)
        team_numbers_list.append(team_num)
        
        ranking_data.append({
            "Rank": rank,
            "Team": f"{team_num} - {team_name}" if team_name else team_num,
            "Final Points": results.final_points,
            "Honor Roll": round(results.honor_roll_score, 1),
            "Curved Score": round(results.curved_score, 1),
            "C/SC/RP": f"{c}/{sc}/{rp}",
            "Feedback": results.final_feedback[:50] + "..." if len(results.final_feedback) > 50 else results.final_feedback,
            "Status": "Qualified"
        })
    
    df_rankings = pd.DataFrame(ranking_data)
    st.dataframe(df_rankings, use_container_width=True, height=400)
    
    return team_numbers_list


def render_team_score_breakdown(team_number: str, 
                                school_system: Any) -> None:
    """
    Render detailed score breakdown for a specific team.
    
    Args:
        team_number: Team number to display
        school_system: TeamScoring instance
    """
    breakdown = school_system.get_team_score_breakdown(team_number)
    
    if not breakdown:
        st.warning(f"No data available for team {team_number}")
        return
    
    detail_col1, detail_col2 = st.columns([1, 1])
    
    with detail_col1:
        st.markdown("#### 📊 Score Breakdown")
        
        # Create bar chart for score breakdown
        categories = ['Match Performance', 'Pit Scouting', 'During Event']
        values = [
            breakdown['match_performance']['total'],
            breakdown['pit_scouting']['total'],
            breakdown['during_event']['total']
        ]
        
        px, go = _ensure_plotly()
        fig = go.Figure()
        fig.add_trace(go.Bar(
            x=categories,
            y=values,
            marker_color=['#667eea', '#764ba2', '#f093fb'],
            text=[f"{v:.1f}" for v in values],
            textposition='auto'
        ))
        fig.update_layout(
            title=f"Team {team_number} Score Breakdown",
            yaxis_title="Score",
            height=300,
            template="plotly_dark"
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Detailed sub-scores
        st.markdown("**Match Performance Details:**")
        mp = breakdown['match_performance']
        st.write(f"• Autonomous: {mp['autonomous']:.1f}")
        st.write(f"• Teleop: {mp['teleop']:.1f}")
        st.write(f"• Endgame: {mp['endgame']:.1f}")
        
        st.markdown("**Pit Scouting Details:**")
        ps = breakdown['pit_scouting']
        st.write(f"• Electrical: {ps['electrical']:.1f}")
        st.write(f"• Mechanical: {ps['mechanical']:.1f}")
        st.write(f"• Driver Station: {ps['driver_station']:.1f}")
        st.write(f"• Tools: {ps['tools']:.1f}")
        st.write(f"• Spare Parts: {ps['spare_parts']:.1f}")
    
    with detail_col2:
        render_competencies_status(team_number, school_system)


def render_competencies_status(team_number: str, school_system: Any) -> None:
    """
    Render competencies and subcompetencies status for a team.
    
    Args:
        team_number: Team number
        school_system: TeamScoring instance
    """
    from school_system import TeamScoring
    
    comp_status = school_system.get_team_competencies_status(team_number)
    comp_labels = TeamScoring.get_competency_labels()
    subcomp_labels = TeamScoring.get_subcompetency_labels()
    
    st.markdown("#### ✅ Competencies Status")
    
    st.markdown("**Competencies:**")
    for key, label in comp_labels.items():
        status = comp_status["competencies"].get(key, False)
        icon = "🟢" if status else "🔴"
        st.write(f"{icon} {label}")
    
    st.markdown("**Subcompetencies:**")
    for key, label in subcomp_labels.items():
        status = comp_status["subcompetencies"].get(key, False)
        icon = "🟢" if status else "🔴"
        st.write(f"{icon} {label}")
    
    st.markdown("**Summary:**")
    counts = comp_status["counts"]
    st.metric("Competencies Met", f"{counts['competencies']}/7")
    st.metric("Subcompetencies Met", f"{counts['subcompetencies']}/5")


def render_ranking_visualization(stats: List[Dict[str, Any]], 
                                 toa_manager: Optional[Any] = None) -> None:
    """
    Render ranking visualization charts.
    
    Args:
        stats: List of team statistics
        toa_manager: Optional TOA manager for team names
    """
    if not stats:
        st.info("No statistics available for visualization.")
        return
    
    # Create DataFrame for visualization
    df_data = []
    for rank, team_stat in enumerate(stats[:20], 1):
        team_num = team_stat.get('team', 'N/A')
        team_name = toa_manager.get_team_nickname(team_num) if toa_manager else team_num
        df_data.append({
            'Rank': rank,
            'Team': f"{team_num} - {team_name}",
            'Overall Avg': round(team_stat.get('overall_avg', 0.0), 2),
            'Overall Std': round(team_stat.get('overall_std', 0.0), 2),
            'Robot Valuation': round(team_stat.get('RobotValuation', 0.0), 2)
        })
    
    df = pd.DataFrame(df_data)
    
    # Scatter plot
    st.markdown("### Performance Visualization")
    px, go = _ensure_plotly()
    fig = px.scatter(
        df,
        x='Overall Avg',
        y='Robot Valuation',
        size='Overall Std',
        hover_data=['Team', 'Rank'],
        title='Overall Average vs Robot Valuation (size = std deviation)',
        labels={'Overall Avg': 'Overall Average', 'Robot Valuation': 'Robot Valuation'}
    )
    fig.update_layout(
        plot_bgcolor='rgba(0,0,0,0)',
        paper_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#f8fafc'),
        xaxis=dict(color='#d1d5db', gridcolor='rgba(255,255,255,0.05)'),
        yaxis=dict(color='#d1d5db', gridcolor='rgba(255,255,255,0.05)')
    )
    st.plotly_chart(fig, use_container_width=True)
