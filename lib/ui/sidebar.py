"""
Sidebar module for the Alliance Simulator Streamlit application.
Provides navigation and global filters for the UI.
"""

import streamlit as st
from typing import List, Tuple


def render_sidebar_header() -> None:
    """Render the sidebar header with branding."""
    st.sidebar.markdown("""
    <div style='text-align: center; padding: 1rem 0;'>
        <h1 style='color: white; font-size: 2.5rem; margin: 0;'>🤖</h1>
        <h2 style='color: white; font-weight: 700; margin: 0.5rem 0;'>Alliance Simulator</h2>
        <p style='color: rgba(255,255,255,0.8); font-size: 0.9rem; margin: 0;'>Team Overture 7421</p>
        <p style='color: rgba(255,255,255,0.7); font-size: 0.8rem; margin: 0.2rem 0;'>FRC 2025 REEFSCAPE</p>
    </div>
    """, unsafe_allow_html=True)
    
    st.sidebar.markdown("<hr style='border: 1px solid rgba(255,255,255,0.2); margin: 1rem 0;'>", unsafe_allow_html=True)


def render_navigation() -> str:
    """
    Render the navigation menu and return the selected page.
    
    Returns:
        str: The selected page name
    """
    st.sidebar.markdown("### 📍 Navigation")
    
    page = st.sidebar.radio(
        "Select Page",
        ["📊 Dashboard", "📁 Data Management", "📈 Team Statistics", 
         "🤝 Alliance Selector", "🏆 Honor Roll System", "🔮 Foreshadowing", "⚙️ TBA Settings"],
        label_visibility="collapsed"
    )
    
    return page


def render_global_filters(teams: List[str]) -> dict:
    """
    Render global filter controls.
    
    Args:
        teams: List of available team numbers
        
    Returns:
        dict: Dictionary of filter values
    """
    filters = {}
    
    if teams:
        st.sidebar.markdown("---")
        st.sidebar.markdown("### 🔍 Filters")
        
        # Team filter
        selected_teams = st.sidebar.multiselect(
            "Filter Teams",
            options=teams,
            default=[],
            key="global_team_filter"
        )
        filters['teams'] = selected_teams
        
        # Match range filter
        with st.sidebar.expander("Match Range"):
            min_match = st.number_input("Min Match #", min_value=1, value=1, key="min_match_filter")
            max_match = st.number_input("Max Match #", min_value=1, value=100, key="max_match_filter")
            filters['match_range'] = (min_match, max_match)
    
    return filters


def render_quick_actions() -> Tuple[bool, bool]:
    """
    Render quick action buttons in the sidebar.
    
    Returns:
        Tuple[bool, bool]: (refresh_pressed, export_pressed)
    """
    st.sidebar.markdown("---")
    st.sidebar.markdown("### ⚡ Quick Actions")
    
    refresh_pressed = st.sidebar.button("🔄 Refresh Data", use_container_width=True)
    export_pressed = st.sidebar.button("📥 Export All", use_container_width=True)
    
    return refresh_pressed, export_pressed


def render_sidebar(teams: List[str] = None) -> Tuple[str, dict]:
    """
    Render the complete sidebar.
    
    Args:
        teams: Optional list of team numbers for filters
        
    Returns:
        Tuple[str, dict]: (selected_page, filters)
    """
    render_sidebar_header()
    page = render_navigation()
    
    filters = {}
    if teams:
        filters = render_global_filters(teams)
    
    return page, filters
