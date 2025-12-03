"""
Streamlit Web Application for Alliance Simulator
Provides a web-based interface for all the core functionality of the desktop application
"""

import streamlit as st
import pandas as pd
import io
import base64
import tempfile
from collections import Counter
from pathlib import Path
from main import AnalizadorRobot
from allianceSelector import AllianceSelector, Team, teams_from_dicts
from school_system import TeamScoring, BehaviorReportType
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import os
from tba_manager import TBAManager
from foreshadowing import TeamStatsExtractor, MatchSimulator
from exam_integrator import ExamDataIntegrator


APP_DIR = Path(__file__).resolve().parent

# Page configuration
st.set_page_config(
    page_title="Alliance Simulator - Overture 7421",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        'About': "Alliance Simulator - Team Overture 7421 | FRC 2025 REEFSCAPE"
    }
)

# Initialize session state
if 'analizador' not in st.session_state:
    st.session_state.analizador = AnalizadorRobot()
if 'alliance_selector' not in st.session_state:
    st.session_state.alliance_selector = None
if 'school_system' not in st.session_state:
    st.session_state.school_system = TeamScoring()
if 'tba_manager' not in st.session_state:
    st.session_state.tba_manager = None
if 'tba_api_key' not in st.session_state:
    st.session_state.tba_api_key = ""
if 'tba_use_api' not in st.session_state:
    st.session_state.tba_use_api = True
if 'tba_event_key' not in st.session_state:
    st.session_state.tba_event_key = ""
if 'events_list' not in st.session_state:
    st.session_state.events_list = []
if 'selected_event_name' not in st.session_state:
    st.session_state.selected_event_name = ""
if 'foreshadowing_prediction' not in st.session_state:
    st.session_state.foreshadowing_prediction = None
if 'foreshadowing_mode' not in st.session_state:
    st.session_state.foreshadowing_mode = None
if 'foreshadowing_last_iterations' not in st.session_state:
    st.session_state.foreshadowing_last_iterations = 0
if 'foreshadowing_error' not in st.session_state:
    st.session_state.foreshadowing_error = ""
if 'foreshadowing_last_inputs' not in st.session_state:
    st.session_state.foreshadowing_last_inputs = {"red": [], "blue": []}
if 'foreshadowing_team_performance' not in st.session_state:
    st.session_state.foreshadowing_team_performance = {"red": [], "blue": []}
if 'foreshadowing_quick_slider' not in st.session_state:
    st.session_state.foreshadowing_quick_slider = 1000
if 'exam_integrator' not in st.session_state:
    st.session_state.exam_integrator = None
if 'scoring_weights' not in st.session_state:
    st.session_state.scoring_weights = {"match": 50, "pit": 30, "event": 20}
if 'selected_team_for_details' not in st.session_state:
    st.session_state.selected_team_for_details = None

# Enhanced Custom CSS for better UI
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Global Styles */
    * {
        font-family: 'Inter', sans-serif;
    }
    
    body, .stApp, .main {
        background-color: #000000;
        color: #f5f5f5;
    }
    
    /* Main container */
    .main {
        background: #000000;
        background-attachment: fixed;
    }
    
    /* Content area */
    .block-container {
        padding: 2rem 3rem;
        background: rgba(18, 18, 20, 0.95);
        border-radius: 20px;
        box-shadow: 0 12px 40px rgba(0, 0, 0, 0.6);
        backdrop-filter: blur(16px);
        margin: 1rem;
        color: #f5f5f5;
    }
    
    /* Headers */
    .main-header {
        font-size: 3rem;
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        text-align: center;
        margin-bottom: 2rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.1);
    }
    
    .sub-header {
        font-size: 1.8rem;
        font-weight: 600;
        color: #9f9dfd;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-left: 4px solid #9f9dfd;
        padding-left: 1rem;
    }
    
    /* Metric cards */
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: #c3c2ff;
    }
    
    div[data-testid="stMetricLabel"] {
        font-weight: 600;
        color: #d1d5db;
    }
    
    .metric-card {
        background: linear-gradient(135deg, rgba(50, 50, 70, 0.6) 0%, rgba(30, 30, 45, 0.8) 100%);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 10px 24px rgba(15, 15, 25, 0.7);
        margin: 0.5rem 0;
        border: 1px solid rgba(159, 157, 253, 0.35);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 24px rgba(102, 126, 234, 0.25);
    }
    
    /* Buttons */
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #7f7eff 0%, #a855f7 100%);
        color: #ffffff;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 6px 14px rgba(128, 90, 213, 0.5);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 12px 24px rgba(128, 90, 213, 0.6);
    }
    
    /* Sidebar */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #111118 0%, #1f1b2b 100%);
    }
    
    section[data-testid="stSidebar"] .css-1d391kg {
        color: white;
    }
    
    section[data-testid="stSidebar"] h2 {
        color: white !important;
        font-weight: 700;
    }
    
    section[data-testid="stSidebar"] h3 {
        color: rgba(255, 255, 255, 0.9) !important;
        font-weight: 600;
    }
    
    section[data-testid="stSidebar"] .stRadio label {
        color: white !important;
        font-weight: 500;
    }
    
    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: transparent;
    }
    
    .stTabs [data-baseweb="tab"] {
        background: linear-gradient(135deg, rgba(40, 40, 60, 0.8) 0%, rgba(30, 30, 45, 0.9) 100%);
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        border: 1px solid rgba(159, 157, 253, 0.25);
        color: #e5e7ff;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #7f7eff 0%, #a855f7 100%);
        color: #ffffff !important;
    }
    
    /* DataFrames */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 4px 18px rgba(0, 0, 0, 0.6);
        color: #f5f5f5;
        background: rgba(15, 15, 20, 0.85);
    }
    
    /* Info/Warning/Success boxes */
    .stAlert {
        border-radius: 8px;
        border-left: 4px solid;
        background: rgba(30, 30, 45, 0.9);
        color: #f8fafc;
    }
    
    /* File uploader */
    .uploadedFile {
        border-radius: 8px;
        border: 2px dashed #667eea;
    }
    
    /* Plotly charts */
    .js-plotly-plot {
        border-radius: 12px;
        box-shadow: 0 6px 24px rgba(0, 0, 0, 0.7);
        background: rgba(15, 15, 20, 0.8);
    }
    
    /* Team badge */
    .team-badge {
        display: inline-block;
        background: linear-gradient(135deg, #7f7eff 0%, #a855f7 100%);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
        margin: 0.2rem;
    }
    
    /* Stats card */
    .stats-card {
        background: linear-gradient(135deg, rgba(40, 40, 60, 0.85) 0%, rgba(25, 25, 40, 0.9) 100%);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 12px 32px rgba(10, 10, 20, 0.7);
        margin: 1rem 0;
        border-left: 4px solid #9f9dfd;
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 2rem;
        color: #9ca3af;
        font-size: 0.9rem;
        margin-top: 3rem;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions
def load_csv_data(uploaded_file):
    """Load CSV data into the analyzer"""
    try:
        # Save uploaded file temporarily
        temp_file = APP_DIR / "temp_upload.csv"
        with temp_file.open("wb") as f:
            f.write(uploaded_file.getbuffer())

        # Load into analyzer
        st.session_state.analizador.load_csv(str(temp_file))
        
        return True, "CSV loaded successfully!"
    except Exception as e:
        return False, f"Error loading CSV: {str(e)}"

def get_team_stats_dataframe():
    """Get team statistics as a pandas DataFrame"""
    stats = st.session_state.analizador.get_detailed_team_stats()
    if not stats:
        return None
    
    tba_manager = st.session_state.tba_manager
    team_data_grouped = st.session_state.analizador.get_team_data_grouped()
    
    # Convert to DataFrame with selected columns for simplified view
    df_data = []
    for team_stat in stats:
        team_num = team_stat.get('team', 'N/A')
        team_name = tba_manager.get_team_nickname(team_num) if tba_manager else team_num
        team_key = str(team_num)
        team_rows = team_data_grouped.get(team_key, [])

        defense_rate = get_rate_from_stat(team_stat, ("Crossed Field/Defense", "Crossed Feild/Played Defense?")) * 100.0
        death_rate = get_rate_from_stat(team_stat, ("Died", "Died?")) * 100.0
        pickup_mode = get_mode_from_rows(team_rows, "Pickup Location")
        climb_mode = get_mode_from_rows(team_rows, "End Position")
        df_data.append({
            'Team': f"{team_num} - {team_name}",
            'Overall Avg': round(team_stat.get('overall_avg', 0.0), 2),
            'Overall Std': round(team_stat.get('overall_std', 0.0), 2),
            'Robot Valuation': round(team_stat.get('RobotValuation', 0.0), 2),
            'Defense Rate (%)': round(defense_rate, 2),
            'Died Rate (%)': round(death_rate, 2),
            'Pickup Mode': pickup_mode,
            'Climb Mode': climb_mode,
        })
    
    return pd.DataFrame(df_data)

def create_alliance_selector_teams():
    """Create Team objects for alliance selector from current stats"""
    stats = st.session_state.analizador.get_detailed_team_stats()
    if not stats:
        return []
    
    teams = []
    for rank, stat in enumerate(stats, 1):
        team_num = stat.get('team', 0)
        overall_avg = stat.get('overall_avg', 0)
        robot_val = stat.get('RobotValuation', 0)
        
        # Get phase scores
        phase_scores = st.session_state.analizador.calculate_team_phase_scores(int(team_num))
        death_rate = get_rate_from_stat(stat, ("Died", "Died?"))
        defended_rate = get_rate_from_stat(stat, ("Defended", "Was the robot Defended by someone?"))
        defense_rate = get_rate_from_stat(stat, ("Crossed Field/Defense", "Crossed Feild/Played Defense?"))
        algae_score = stat.get('teleop_algae_avg', 0.0)
        
        team_name = st.session_state.tba_manager.get_team_nickname(team_num) if st.session_state.tba_manager else f"Team {team_num}"

        teams.append(Team(
            num=team_num,
            rank=rank,
            total_epa=overall_avg,
            auto_epa=phase_scores.get('autonomous', 0),
            teleop_epa=phase_scores.get('teleop', 0),
            endgame_epa=phase_scores.get('endgame', 0),
            defense=defense_rate >= 0.4,
            name=team_name,
            robot_valuation=robot_val,
            consistency_score=100 - stat.get('overall_std', 20),
            clutch_factor=75,  # Default value
            death_rate=death_rate,
            defended_rate=defended_rate,
            defense_rate=defense_rate,
            algae_score=algae_score
        ))
    
    return teams

def compute_numeric_average(team_rows, column_name):
    """Calculate the average numeric value for a given column across a team's matches."""
    analyzer = st.session_state.analizador
    col_idx = analyzer._column_indices.get(column_name)
    if col_idx is None:
        return 0.0

    values = []
    for row in team_rows:
        if col_idx < len(row):
            cell = row[col_idx]
            if isinstance(cell, str):
                cell = cell.strip()
                if not cell:
                    continue
            try:
                values.append(float(cell))
            except (ValueError, TypeError):
                continue

    return sum(values) / len(values) if values else 0.0

def get_rate_from_stat(team_stat, column_name):
    """Retrieve a precomputed rate statistic for the requested column."""
    analyzer = st.session_state.analizador
    column_candidates = column_name if isinstance(column_name, (list, tuple)) else [column_name]

    for candidate in column_candidates:
        key = analyzer._generate_stat_key(candidate, 'rate')
        if key in team_stat:
            return team_stat.get(key, 0.0)

    return 0.0


def get_mode_from_rows(team_rows, column_name):
    """Return the most frequent non-empty value for a given column."""
    if not team_rows:
        return ""

    analyzer = st.session_state.analizador
    col_idx = analyzer._column_indices.get(column_name)
    if col_idx is None:
        return ""

    values = []
    for row in team_rows:
        if col_idx >= len(row):
            continue
        value = row[col_idx]
        if isinstance(value, str):
            value = value.strip()
        if value in (None, ""):
            continue
        values.append(str(value))

    if not values:
        return ""

    counts = Counter(values)
    most_common = counts.most_common()
    if not most_common:
        return ""
    max_freq = most_common[0][1]
    top_values = [val for val, freq in most_common if freq == max_freq]
    return top_values[0] if top_values else ""


def get_team_display_label(team_number):
    """Return formatted team label with nickname when available."""
    num_str = str(team_number)
    nickname = None
    if st.session_state.tba_manager:
        nickname = st.session_state.tba_manager.get_team_nickname(num_str)
    return f"{num_str} - {nickname}" if nickname else num_str


def get_foreshadowing_team_options():
    """Build ordered list of selectable teams for foreshadowing."""
    stats = st.session_state.analizador.get_detailed_team_stats()
    if not stats:
        return []

    options = []
    for stat in stats:
        team_num = str(stat.get('team', '')).strip()
        if not team_num:
            continue
        options.append((get_team_display_label(team_num), team_num))
    return options


def validate_alliance_selection(red, blue):
    """Validate alliance inputs before running simulations."""
    if len(red) != 3 or len(blue) != 3:
        return False, "Select exactly 3 teams for each alliance."

    combined = red + blue
    if len(set(combined)) != len(combined):
        return False, "Each team must be unique across both alliances."

    return True, ""


def build_coral_breakdown_df(breakdown):
    levels = ['L1', 'L2', 'L3', 'L4']
    data = {
        'Level': levels,
        'Auto': [breakdown['auto_coral'][lvl] for lvl in levels],
        'Teleop': [breakdown['teleop_coral'][lvl] for lvl in levels],
        'Total': [breakdown['coral_scores'][lvl] for lvl in levels]
    }
    return pd.DataFrame(data)


def build_algae_summary_df(breakdown):
    return pd.DataFrame([
        {'Phase': 'Auto Processor', 'Pieces': breakdown['processor_algae']['auto']},
        {'Phase': 'Teleop Processor', 'Pieces': breakdown['processor_algae']['teleop']},
        {'Phase': 'Teleop Net', 'Pieces': breakdown['net_algae']}
    ])


def build_climb_breakdown_df(breakdown):
    rows = []
    for team, climb_type, points in breakdown['climb_scores']:
        rows.append({
            'Team': get_team_display_label(team),
            'Action': climb_type.capitalize(),
            'Points': points
        })
    return pd.DataFrame(rows)


def build_team_performance_df(team_performances):
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
    return pd.DataFrame(rows)

# Sidebar navigation with enhanced design
st.sidebar.markdown("""
<div style='text-align: center; padding: 1rem 0;'>
    <h1 style='color: white; font-size: 2.5rem; margin: 0;'>🤖</h1>
    <h2 style='color: white; font-weight: 700; margin: 0.5rem 0;'>Alliance Simulator</h2>
    <p style='color: rgba(255,255,255,0.8); font-size: 0.9rem; margin: 0;'>Team Overture 7421</p>
    <p style='color: rgba(255,255,255,0.7); font-size: 0.8rem; margin: 0.2rem 0;'>FRC 2025 REEFSCAPE</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("<hr style='border: 1px solid rgba(255,255,255,0.2); margin: 1rem 0;'>", unsafe_allow_html=True)

st.sidebar.markdown("### 📍 Navigation")

page = st.sidebar.radio(
    "Select Page",
    ["📊 Dashboard", "📁 Data Management", "📈 Team Statistics", 
     "🤝 Alliance Selector", "🏆 Honor Roll System", "🔮 Foreshadowing", "⚙️ TBA Settings"],
    label_visibility="collapsed"
)

# Main content based on selected page
if page == "📊 Dashboard":
    st.markdown("<div class='main-header'>🤖 Alliance Simulator Dashboard</div>", unsafe_allow_html=True)
    
    # Welcome message
    st.markdown(""" 
    <div style='text-align: center; padding: 1rem; background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%); 
                border-radius: 12px; margin-bottom: 2rem;'>
        <p style='color: #4a5568; font-size: 1.1rem; margin: 0;'>
            Welcome to the Alliance Simulator - Your comprehensive FRC scouting and analysis tool
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    # Quick stats with enhanced styling
    st.markdown("<div class='sub-header'>📊 Quick Statistics</div>", unsafe_allow_html=True)
    col1, col2, col3, col4 = st.columns(4)
    
    raw_data = st.session_state.analizador.get_raw_data()
    num_matches = len(raw_data) - 1 if raw_data else 0
    
    team_data = st.session_state.analizador.get_team_data_grouped()
    num_teams = len(team_data)
    
    with col1:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.metric("🎯 Total Matches", num_matches)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.metric("🤖 Total Teams", num_teams)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col3:
        stats = st.session_state.analizador.get_detailed_team_stats()
        avg_overall = sum(s.get('overall_avg', 0) for s in stats) / len(stats) if stats else 0
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.metric("📈 Avg Overall Score", f"{avg_overall:.2f}")
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col4:
        alliances = len(st.session_state.alliance_selector.alliances) if st.session_state.alliance_selector else 0
        st.markdown("<div class='metric-card'>", unsafe_allow_html=True)
        st.metric("🤝 Alliances Configured", alliances)
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Quick overview ranking table with enhanced styling
    if stats:
        st.markdown("<div class='sub-header'>🏆 Top 10 Teams by Overall Performance</div>", unsafe_allow_html=True)

        ranking_rows = []
        for rank, team_stat in enumerate(stats[:10], 1):
            overall_avg = team_stat.get('overall_avg', 0.0)
            overall_std = team_stat.get('overall_std', 0.0)
            team_num = team_stat.get('team', 'N/A')
            team_name = st.session_state.tba_manager.get_team_nickname(team_num) if st.session_state.tba_manager else team_num
            ranking_rows.append({
                'Rank': rank,
                'Team': f"{team_num} - {team_name}",
                'Overall ± Std': f"{overall_avg:.2f} ± {overall_std:.2f}",
                'Robot Valuation': round(team_stat.get('RobotValuation', 0.0), 2)
            })

        ranking_df = pd.DataFrame(ranking_rows)
        st.dataframe(
            ranking_df,
            use_container_width=True,
            height=360
        )
        
        # Additional insights
        st.markdown("<div class='sub-header'>💡 Quick Insights</div>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("<div class='stats-card'>", unsafe_allow_html=True)
            st.markdown("**🥇 Top Team**")
            if stats:
                top_team = stats[0]
                team_num = top_team.get('team', 'N/A')
                team_name = st.session_state.tba_manager.get_team_nickname(team_num) if st.session_state.tba_manager else team_num
                st.markdown(f"<div class='team-badge'>{team_num} - {team_name}</div>", unsafe_allow_html=True)
                st.markdown(f"Overall: **{top_team.get('overall_avg', 0.0):.2f}**")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("<div class='stats-card'>", unsafe_allow_html=True)
            st.markdown("**🎯 Most Consistent**")
            if stats:
                consistent_team = min(stats, key=lambda x: x.get('overall_std', 100))
                team_num = consistent_team.get('team', 'N/A')
                team_name = st.session_state.tba_manager.get_team_nickname(team_num) if st.session_state.tba_manager else team_num
                st.markdown(f"<div class='team-badge'>{team_num} - {team_name}</div>", unsafe_allow_html=True)
                st.markdown(f"Std Dev: **{consistent_team.get('overall_std', 0.0):.2f}**")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col3:
            st.markdown("<div class='stats-card'>", unsafe_allow_html=True)
            st.markdown("**⚙️ Best Robot**")
            if stats:
                best_robot = max(stats, key=lambda x: x.get('RobotValuation', 0))
                team_num = best_robot.get('team', 'N/A')
                team_name = st.session_state.tba_manager.get_team_nickname(team_num) if st.session_state.tba_manager else team_num
                st.markdown(f"<div class='team-badge'>{team_num} - {team_name}</div>", unsafe_allow_html=True)
                st.markdown(f"Valuation: **{best_robot.get('RobotValuation', 0.0):.2f}**")
            st.markdown("</div>", unsafe_allow_html=True)

elif page == "📁 Data Management":
    st.markdown("<div class='main-header'>📁 Data Management</div>", unsafe_allow_html=True)
    
    tab1, tab2, tab3 = st.tabs(["📤 Upload Data", "📋 View Raw Data", "💾 Export Data"])
    
    with tab1:
        st.markdown("### 📁 Upload CSV File (Manual)")
        uploaded_file = st.file_uploader("Choose a CSV file", type=['csv'])
        
        if uploaded_file is not None:
            if st.button("Load CSV"):
                success, message = load_csv_data(uploaded_file)
                if success:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)
        
        st.markdown("---")
        st.markdown("### 📱 Paste QR Data (Manual)")
        qr_data = st.text_area("Paste QR code data here", height=150)
        if st.button("Load QR Data"):
            if qr_data.strip():
                st.session_state.analizador.load_qr_data(qr_data)
                st.success("QR data loaded successfully!")
                st.rerun()
            else:
                st.warning("Please paste QR data first")

    with tab2:
        st.markdown("### 📋 Raw Data View")
        raw_data = st.session_state.analizador.get_raw_data()
        
        if raw_data and len(raw_data) > 1:
            df = pd.DataFrame(raw_data[1:], columns=raw_data[0])
            st.dataframe(df, use_container_width=True, height=400)
            
            st.markdown(f"**Total Records:** {len(raw_data) - 1}")
        else:
            st.info("No data loaded yet. Please upload a CSV file or paste QR data.")
    
    with tab3:
        st.markdown("### 💾 Export Options")
        
        if st.button("Export Raw Data as CSV"):
            raw_data = st.session_state.analizador.get_raw_data()
            if raw_data:
                df = pd.DataFrame(raw_data[1:], columns=raw_data[0])
                csv = df.to_csv(index=False)
                b64 = base64.b64encode(csv.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="raw_data.csv">Download CSV File</a>'
                st.markdown(href, unsafe_allow_html=True)
            else:
                st.warning("No data to export")
        
        if st.button("Export Simplified Ranking"):
            stats = st.session_state.analizador.get_detailed_team_stats()
            if stats:
                # Create simplified ranking data
                simplified_data = []
                team_data_grouped = st.session_state.analizador.get_team_data_grouped()
                
                for rank, team_stat in enumerate(stats, 1):
                    team_num = str(team_stat.get('team', 'N/A'))
                    overall_avg = team_stat.get('overall_avg', 0.0)
                    overall_std = team_stat.get('overall_std', 0.0)
                    robot_valuation = team_stat.get('RobotValuation', 0.0)
                    team_rows = team_data_grouped.get(team_num, [])

                    death_rate = get_rate_from_stat(team_stat, ("Died", "Died?"))
                    defense_rate = get_rate_from_stat(team_stat, ("Crossed Field/Defense", "Crossed Feild/Played Defense?"))
                    defended_rate = get_rate_from_stat(team_stat, ("Defended", "Was the robot Defended by someone?"))

                    pickup_mode = get_mode_from_rows(team_rows, "Pickup Location") or "Unknown"
                    climb_mode = get_mode_from_rows(team_rows, "End Position") or "Unknown"

                    simplified_data.append({
                        'Rank': rank,
                        'Team': team_num,
                        'Overall ± Std': f"{overall_avg:.2f} ± {overall_std:.2f}",
                        'Robot Valuation': f"{robot_valuation:.2f}",
                        'Defense Rate (%)': f"{defense_rate * 100:.3f}",
                        'Died Rate (%)': f"{death_rate * 100:.3f}",
                        'Pickup Mode': pickup_mode,
                        'Climb Mode': climb_mode,
                        'Defended Rate (%)': f"{defended_rate * 100:.3f}"
                    })
                
                df = pd.DataFrame(simplified_data)
                csv = df.to_csv(index=False)
                b64 = base64.b64encode(csv.encode()).decode()
                href = f'<a href="data:file/csv;base64,{b64}" download="simplified_ranking.csv">Download Simplified Ranking</a>'
                st.markdown(href, unsafe_allow_html=True)
                st.success("Simplified ranking ready for download!")
            else:
                st.warning("No statistics available to export")

elif page == "📈 Team Statistics":
    st.markdown("<div class='main-header'>📈 Team Statistics</div>", unsafe_allow_html=True)
    
    stats = st.session_state.analizador.get_detailed_team_stats()
    
    if not stats:
        st.info("No team statistics available. Please load data first.")
    else:
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["Overall Rankings", "Detailed Stats", "Simplified Ranking"])
        
        with tab1:
            st.markdown("### Overall Team Rankings")
            
            team_data_grouped = st.session_state.analizador.get_team_data_grouped()

            auto_coral_columns = [
                ("Coral L1 (Auto)", "Auto Coral L1"),
                ("Coral L2 (Auto)", "Auto Coral L2"),
                ("Coral L3 (Auto)", "Auto Coral L3"),
                ("Coral L4 (Auto)", "Auto Coral L4"),
            ]
            teleop_coral_columns = [
                ("Coral L1 (Teleop)", "Teleop Coral L1"),
                ("Coral L2 (Teleop)", "Teleop Coral L2"),
                ("Coral L3 (Teleop)", "Teleop Coral L3"),
                ("Coral L4 (Teleop)", "Teleop Coral L4"),
            ]
            auto_algae_columns = [
                ("Barge Algae (Auto)", "Auto Barge Algae"),
                ("Processor Algae (Auto)", "Auto Processor Algae"),
                ("Dislodged Algae (Auto)", "Auto Dislodged Algae"),
            ]
            teleop_algae_columns = [
                ("Barge Algae (Teleop)", "Teleop Barge Algae"),
                ("Processor Algae (Teleop)", "Teleop Processor Algae"),
                ("Dislodged Algae (Teleop)", "Teleop Dislodged Algae"),
            ]
            rate_columns = [
                (("Died", "Died?"), "Died Rate (%)"),
                (("No Show",), "No Show Rate (%)"),
                (("Moved (Auto)",), "Auto Mobility Rate (%)"),
                (("Crossed Field/Defense", "Crossed Feild/Played Defense?"), "Defense Rate (%)"),
                (("Defended", "Was the robot Defended by someone?"), "Defended Rate (%)"),
                (("Tipped/Fell",), "Tip/Fall Rate (%)"),
                (("Broke",), "Broke Rate (%)"),
            ]

            base_columns = [
                'Rank', 'Team', 'Matches',
                'Robot Valuation', 'Overall Avg', 'Overall Std',
                'Teleop Coral Score', 'Teleop Algae Score'
            ]
            auto_labels = [label for _, label in auto_coral_columns]
            teleop_labels = [label for _, label in teleop_coral_columns]
            auto_algae_labels = [label for _, label in auto_algae_columns]
            teleop_algae_labels = [label for _, label in teleop_algae_columns]
            rate_labels = [label for _, label in rate_columns]
            columns_order = (
                base_columns
                + auto_labels
                + teleop_labels
                + auto_algae_labels
                + teleop_algae_labels
                + rate_labels
            )

            df_rows = []
            for rank, team_stat in enumerate(stats, 1):
                team_num = team_stat.get('team', 'N/A')
                team_name = st.session_state.tba_manager.get_team_nickname(team_num) if st.session_state.tba_manager else team_num
                row = {
                    'Rank': rank,
                    'Team': f"{team_num} - {team_name}",
                    'Matches': len(team_data_grouped.get(team_num, [])),
                    'Robot Valuation': round(team_stat.get('RobotValuation', 0.0), 2),
                    'Overall Avg': round(team_stat.get('overall_avg', 0.0), 2),
                    'Overall Std': round(team_stat.get('overall_std', 0.0), 2),
                    'Teleop Coral Score': round(team_stat.get('teleop_coral_avg', 0.0), 2),
                    'Teleop Algae Score': round(team_stat.get('teleop_algae_avg', 0.0), 2),
                }

                for source_col, label in auto_coral_columns + teleop_coral_columns + auto_algae_columns + teleop_algae_columns:
                    row[label] = compute_numeric_average(team_data_grouped.get(team_num, []), source_col)

                for source_candidates, label in rate_columns:
                    rate_value = get_rate_from_stat(team_stat, source_candidates) * 100.0
                    row[label] = rate_value

                df_rows.append(row)

            df = pd.DataFrame(df_rows)

            if not df.empty:
                df = df[columns_order]
                float_columns = [col for col in columns_order if col not in ['Rank', 'Team', 'Matches']]
                styled_df = df.style.format({col: "{:.2f}" for col in float_columns})
                st.dataframe(styled_df, use_container_width=True, height=520)

                # Visualization
                st.markdown("### Performance Visualization")
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
                fig.update_layout(
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#f8fafc'),
                    xaxis=dict(color='#d1d5db', gridcolor='rgba(255,255,255,0.05)'),
                    yaxis=dict(color='#d1d5db', gridcolor='rgba(255,255,255,0.05)')
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No ranking data available. Please load scouting data first.")
        
        with tab2:
            st.markdown("### Detailed Team Statistics")
            
            all_teams = [s.get('team', 'N/A') for s in stats]
            if st.session_state.tba_manager:
                team_options = {
                    team: f"{team} - {st.session_state.tba_manager.get_team_nickname(team)}"
                    for team in all_teams
                }
                selected_team_num = st.selectbox(
                    "Select a Team",
                    options=list(team_options.keys()),
                    format_func=lambda x: team_options[x]
                )
            else:
                selected_team_num = st.selectbox("Select a Team", options=all_teams)

            
            if selected_team_num:
                team_stat = next((s for s in stats if s.get('team') == selected_team_num), None)
                
                if team_stat:
                    col1, col2, col3 = st.columns(3)
                    
                    with col1:
                        st.metric("Overall Average", f"{team_stat.get('overall_avg', 0):.2f}")
                        st.metric("Overall Std Dev", f"{team_stat.get('overall_std', 0):.2f}")
                    
                    with col2:
                        st.metric("Robot Valuation", f"{team_stat.get('RobotValuation', 0):.2f}")
                        teleop_coral_avg = team_stat.get('teleop_coral_avg', 0)
                        st.metric("Teleop Coral Avg", f"{teleop_coral_avg:.2f}")
                    
                    with col3:
                        teleop_algae_avg = team_stat.get('teleop_algae_avg', 0)
                        st.metric("Teleop Algae Avg", f"{teleop_algae_avg:.2f}")
                        died_rate = get_rate_from_stat(team_stat, ("Died", "Died?"))
                        st.metric("Death Rate", f"{died_rate * 100:.1f}%")
                    
                    # Complete metrics table
                    st.markdown("### Complete Metric Snapshot")
                    formatted_metrics = {}
                    for key, value in team_stat.items():
                        if isinstance(value, (float, int)):
                            formatted_metrics[key] = round(float(value), 3)
                        else:
                            formatted_metrics[key] = value

                    metrics_df = pd.DataFrame.from_dict(formatted_metrics, orient='index', columns=['Value'])
                    metrics_df.index.name = 'Metric'
                    st.dataframe(metrics_df, use_container_width=True, height=420)

                    # Match performance line chart
                    st.markdown("### Match Performance Trend")
                    match_performance = st.session_state.analizador.get_team_match_performance([selected_team_num])
                    team_performance = match_performance.get(selected_team_num) or match_performance.get(str(selected_team_num))

                    if team_performance:
                        data_points = []
                        first_entry = team_performance[0]
                        if isinstance(first_entry, dict):
                            data_points = [
                                (item.get('match'), item.get('overall'))
                                for item in team_performance
                                if item.get('match') is not None and item.get('overall') is not None
                            ]
                        else:
                            data_points = [
                                (item[0], item[1])
                                for item in team_performance
                                if isinstance(item, (list, tuple)) and len(item) >= 2
                            ]

                        if data_points:
                            matches, overall_scores = zip(*data_points)
                            trend_fig = go.Figure(
                                data=[
                                    go.Scatter(
                                        x=list(matches),
                                        y=list(overall_scores),
                                        mode='lines+markers',
                                        line=dict(color='#a855f7', width=3),
                                        marker=dict(size=8)
                                    )
                                ]
                            )
                            trend_fig.update_layout(
                                title=f'Team {selected_team_num} - Overall Score by Match',
                                xaxis_title='Match Number',
                                yaxis_title='Overall Score',
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)',
                                font=dict(color='#f8fafc'),
                                xaxis=dict(color='#d1d5db', gridcolor='rgba(255,255,255,0.05)'),
                                yaxis=dict(color='#d1d5db', gridcolor='rgba(255,255,255,0.05)')
                            )
                            st.plotly_chart(trend_fig, use_container_width=True)
                        else:
                            st.info("No match performance data available for this team.")
                    else:
                        st.info("No match performance data available for this team.")
        
        with tab3:
            st.markdown("### Simplified Ranking")
            df_simple = get_team_stats_dataframe()
            if df_simple is not None:
                st.dataframe(df_simple, use_container_width=True, height=600)
            else:
                st.info("No data to display.")

elif page == "🤝 Alliance Selector":
    st.markdown("<div class='main-header'>🤝 Alliance Selector</div>", unsafe_allow_html=True)
    
    # Initialize alliance selector if not exists
    if st.button("Initialize/Refresh Alliance Selector"):
        teams = create_alliance_selector_teams()
        if teams:
            st.session_state.alliance_selector = AllianceSelector(teams)
            st.success(f"Alliance selector initialized with {len(teams)} teams!")
            st.rerun()
        else:
            st.warning("No teams available. Please load data first.")
    
    if st.session_state.alliance_selector:
        selector = st.session_state.alliance_selector
        
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown("### Alliance Selections")
            alliance_table_data = selector.get_alliance_table()
            
            # Replace team numbers with names
            if st.session_state.tba_manager:
                for row in alliance_table_data:
                    for col in ['Captain', 'Pick 1', 'Pick 2', 'Recommendation 1', 'Recommendation 2']:
                        if row[col]:
                            num = row[col]
                            name = st.session_state.tba_manager.get_team_nickname(num)
                            row[col] = f"{num} - {name}"

            df_alliances = pd.DataFrame(alliance_table_data)
            st.dataframe(df_alliances, use_container_width=True, height=325)
        
        with col2:
            st.markdown("### Quick Actions")
            
            if st.button("Auto-Optimize All"):
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

                if made_changes:
                    st.success("Auto-optimization filled remaining picks.")
                else:
                    st.info("No auto-optimization needed – all picks already assigned.")
                st.rerun()
            
            if st.button("Reset All Picks"):
                selector.reset_picks()
                st.success("All picks reset!")
                st.rerun()
        
        # Manual alliance configuration
        st.markdown("### Manual Alliance Configuration")
        
        with st.expander("Configure Individual Alliances"):
            alliances = selector.alliances
            
            # Create columns for each alliance
            cols = st.columns(len(alliances))
            
            for i, a in enumerate(alliances):
                with cols[i]:
                    st.markdown(f"**Alliance {a.allianceNumber}**")
                    
                    # Captain selection
                    available_captains = selector.get_available_captains(i)
                    
                    if st.session_state.tba_manager:
                        captain_options = {team.team: f"{team.team} - {team.name}" for team in available_captains}
                        captain_options[0] = "Auto"
                        
                        # Ensure current captain is in the list
                        if a.captain and a.captain not in captain_options:
                            captain_options[a.captain] = f"{a.captain} - {st.session_state.tba_manager.get_team_nickname(a.captain)}"

                        selected_captain = st.selectbox(
                            f"Captain A{a.allianceNumber}",
                            options=list(captain_options.keys()),
                            format_func=lambda x: captain_options.get(x, "Auto"),
                            key=f"captain_{i}",
                            index=list(captain_options.keys()).index(a.captain) if a.captain in captain_options else 0
                        )
                    else:
                        captain_options = [team.team for team in available_captains]
                        captain_options.insert(0, 0) # For "Auto"
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
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))
                    
                    # Pick 1 and Pick 2 selection
                    available_teams = selector.get_available_teams(a.captainRank, 'pick1')
                    
                    if st.session_state.tba_manager:
                        team_options = {team.team: f"{team.team} - {team.name}" for team in available_teams}
                        team_options[0] = "None"
                        
                        # Add current picks if they are not in the available list (e.g. captain of another alliance)
                        for pick in [a.pick1, a.pick2]:
                            if pick and pick not in team_options:
                                team_options[pick] = f"{pick} - {st.session_state.tba_manager.get_team_nickname(pick)}"
                    else:
                        team_options = {team.team: team.team for team in available_teams}
                        team_options[0] = "None"

                    # Pick 1
                    pick1_val = a.pick1 if a.pick1 in team_options else 0
                    selected_pick1 = st.selectbox(f"Pick 1 A{a.allianceNumber}", 
                                                  options=list(team_options.keys()),
                                                  format_func=lambda x: team_options.get(x, "None"),
                                                  key=f"pick1_{i}", index=list(team_options.keys()).index(pick1_val))
                    current_pick1_value = a.pick1 if a.pick1 is not None else 0
                    if selected_pick1 != current_pick1_value:
                        try:
                            selector.set_pick(i, 'pick1', selected_pick1 if selected_pick1 != 0 else None)
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))

                    # Pick 2
                    pick2_val = a.pick2 if a.pick2 in team_options else 0
                    selected_pick2 = st.selectbox(f"Pick 2 A{a.allianceNumber}", 
                                                  options=list(team_options.keys()),
                                                  format_func=lambda x: team_options.get(x, "None"),
                                                  key=f"pick2_{i}", index=list(team_options.keys()).index(pick2_val))
                    current_pick2_value = a.pick2 if a.pick2 is not None else 0
                    if selected_pick2 != current_pick2_value:
                        try:
                            selector.set_pick(i, 'pick2', selected_pick2 if selected_pick2 != 0 else None)
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))
    else:
        st.info("Please initialize the Alliance Selector first.")

elif page == "🏆 Honor Roll System":
    st.markdown("<div class='main-header'>🏆 Honor Roll System</div>", unsafe_allow_html=True)
    
    # Exam Import Section
    with st.expander("📥 Import Exam Data", expanded=False):
        st.markdown("Upload exam CSV files to integrate scores into the Honor Roll System.")
        
        exam_col1, exam_col2 = st.columns(2)
        
        with exam_col1:
            programming_file = st.file_uploader(
                "Upload Programming Exam (.csv)", 
                type=['csv'], 
                key="programming_exam_upload",
                help="CSV file with programming/autonomous exam results"
            )
            mechanical_file = st.file_uploader(
                "Upload Mechanical Exam (.csv)", 
                type=['csv'], 
                key="mechanical_exam_upload",
                help="CSV file with mechanical exam results"
            )
        
        with exam_col2:
            electrical_file = st.file_uploader(
                "Upload Electrical Exam (.csv)", 
                type=['csv'], 
                key="electrical_exam_upload",
                help="CSV file with electrical exam results"
            )
            competencies_file = st.file_uploader(
                "Upload Competencies Exam (.csv)", 
                type=['csv'], 
                key="competencies_exam_upload",
                help="CSV file with competencies/soft skills exam results"
            )
        
        if st.button("🔄 Process Exams", type="primary", use_container_width=True):
            if not any([programming_file, mechanical_file, electrical_file, competencies_file]):
                st.warning("Please upload at least one exam file to process.")
            else:
                try:
                    with st.spinner("Processing exam files..."):
                        integrator = ExamDataIntegrator()
                        results_summary = []
                        
                        # Process Programming Exam
                        if programming_file is not None:
                            with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp:
                                tmp.write(programming_file.getvalue())
                                tmp_path = tmp.name
                            prog_results = integrator.integrate_programming_exam(tmp_path)
                            os.unlink(tmp_path)
                            results_summary.append(f"✅ Programming: {len(prog_results)} teams")
                        
                        # Process Mechanical Exam
                        if mechanical_file is not None:
                            with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp:
                                tmp.write(mechanical_file.getvalue())
                                tmp_path = tmp.name
                            mech_results = integrator.integrate_mechanical_exam(tmp_path)
                            os.unlink(tmp_path)
                            results_summary.append(f"✅ Mechanical: {len(mech_results)} teams")
                        
                        # Process Electrical Exam
                        if electrical_file is not None:
                            with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp:
                                tmp.write(electrical_file.getvalue())
                                tmp_path = tmp.name
                            elec_results = integrator.integrate_electrical_exam(tmp_path)
                            os.unlink(tmp_path)
                            results_summary.append(f"✅ Electrical: {len(elec_results)} teams")
                        
                        # Process Competencies Exam
                        if competencies_file is not None:
                            with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp:
                                tmp.write(competencies_file.getvalue())
                                tmp_path = tmp.name
                            comp_results = integrator.integrate_competencies_exam(tmp_path)
                            os.unlink(tmp_path)
                            results_summary.append(f"✅ Competencies: {len(comp_results)} teams")
                        
                        # Apply to school system
                        integrator.apply_to_scoring_system(st.session_state.school_system)
                        
                        # Calculate all scores
                        st.session_state.school_system.calculate_all_scores()
                        
                        # Store integrator for later reference
                        st.session_state.exam_integrator = integrator
                        
                        # Get statistics
                        stats = integrator.get_exam_statistics()
                        
                        # Display success message
                        st.success("Exam data imported successfully!")
                        
                        # Show results summary
                        for result in results_summary:
                            st.write(result)
                        
                        st.info(f"📊 Total teams in system: {stats['total_teams']} | 💬 Scouting comments: {stats['total_comments']}")
                        
                except Exception as e:
                    st.error(f"Failed to process exam files: {str(e)}")
        
        # Show exam statistics if integrator exists
        if st.session_state.exam_integrator is not None:
            st.markdown("---")
            st.markdown("**📈 Current Exam Statistics:**")
            stats = st.session_state.exam_integrator.get_exam_statistics()
            
            stat_cols = st.columns(4)
            exam_types = ["programming", "mechanical", "electrical", "competencies"]
            for i, exam_type in enumerate(exam_types):
                with stat_cols[i]:
                    s = stats[exam_type]
                    if s['count'] > 0:
                        st.metric(
                            exam_type.title(), 
                            f"{s['count']} teams",
                            f"Avg: {s['avg_score']:.1f}%"
                        )
                    else:
                        st.metric(exam_type.title(), "No data")
    
    # Scoring Settings Section
    with st.expander("⚙️ Scoring Settings", expanded=False):
        st.markdown("**Configure Honor Roll Score Weights**")
        st.markdown("Adjust the weight of each scoring component. Weights must sum to 100%.")
        
        weight_cols = st.columns(3)
        with weight_cols[0]:
            match_weight = st.number_input(
                "Match Performance %", 
                min_value=0, max_value=100, 
                value=st.session_state.scoring_weights["match"],
                step=5,
                help="Weight for autonomous, teleop, and endgame scores"
            )
        with weight_cols[1]:
            pit_weight = st.number_input(
                "Pit Scouting %", 
                min_value=0, max_value=100, 
                value=st.session_state.scoring_weights["pit"],
                step=5,
                help="Weight for electrical, mechanical, and equipment scores"
            )
        with weight_cols[2]:
            event_weight = st.number_input(
                "During Event %", 
                min_value=0, max_value=100, 
                value=st.session_state.scoring_weights["event"],
                step=5,
                help="Weight for organization and collaboration scores"
            )
        
        total_weight = match_weight + pit_weight + event_weight
        
        if total_weight != 100:
            st.warning(f"⚠️ Weights must sum to 100%. Current sum: {total_weight}%")
        else:
            st.success(f"✅ Weights sum to 100%")
        
        if st.button("Apply Scoring Weights", disabled=(total_weight != 100)):
            # Update session state
            st.session_state.scoring_weights = {"match": match_weight, "pit": pit_weight, "event": event_weight}
            
            # Apply to school system
            st.session_state.school_system.set_scoring_weights(
                match_weight / 100.0,
                pit_weight / 100.0,
                event_weight / 100.0
            )
            
            # Recalculate scores
            st.session_state.school_system.calculate_all_scores()
            st.success("Scoring weights updated! Rankings recalculated.")
            st.rerun()
    
    col1, col2 = st.columns([1, 1])
    
    with col1:
        st.markdown("### Configuration")
        
        competencies_mult = st.number_input("Competencies Multiplier", 
                                           value=st.session_state.school_system.competencies_multiplier,
                                           min_value=1, max_value=100)
        subcomp_mult = st.number_input("Subcompetencies Multiplier",
                                       value=st.session_state.school_system.subcompetencies_multiplier,
                                       min_value=1, max_value=100)
        min_comp = st.number_input("Min Competencies Count",
                                   value=st.session_state.school_system.min_competencies_count,
                                   min_value=0, max_value=20)
        min_subcomp = st.number_input("Min Subcompetencies Count",
                                     value=st.session_state.school_system.min_subcompetencies_count,
                                     min_value=0, max_value=20)
        min_score = st.number_input("Min Honor Roll Score",
                                   value=st.session_state.school_system.min_honor_roll_score,
                                   min_value=0.0, max_value=100.0)
        
        if st.button("Apply Configuration"):
            st.session_state.school_system.competencies_multiplier = competencies_mult
            st.session_state.school_system.subcompetencies_multiplier = subcomp_mult
            st.session_state.school_system.min_competencies_count = min_comp
            st.session_state.school_system.min_subcompetencies_count = min_subcomp
            st.session_state.school_system.min_honor_roll_score = min_score
            st.success("Configuration updated!")
    
    with col2:
        st.markdown("### Quick Actions")
        
        if st.button("Auto-populate from Data"):
            stats = st.session_state.analizador.get_detailed_team_stats()
            if stats:
                for stat in stats:
                    team_num = str(stat.get('team', ''))
                    st.session_state.school_system.add_team(team_num)
                    
                    # Add default scores
                    st.session_state.school_system.update_autonomous_score(team_num, 75.0)
                    st.session_state.school_system.update_teleop_score(team_num, 80.0)
                    st.session_state.school_system.update_endgame_score(team_num, 70.0)
                
                st.success(f"Added {len(stats)} teams to Honor Roll System!")
            else:
                st.warning("No team data available")
        
        # Export to TierList button
        if st.session_state.school_system.teams:
            st.markdown("---")
            st.markdown("**📥 Export Options**")
            
            # Generate TierList plain text file with custom format
            def generate_tierlist_txt():
                """
                Generate a plain text file in the TierList Maker format.
                
                Format:
                Tier: [Tier Name]
                  Image: [Base64_String]
                    Title: Team [Team_Number]
                    Text: [JSON_String with stats]
                    DriverSkills: [Value]
                    ImageList:
                
                (blank line between tiers)
                
                Tier Assignment Logic (respects user's dynamic configuration):
                1. Uses min_honor_roll_score from session_state (NOT hardcoded)
                2. Qualified teams are sorted by final_points (includes weight adjustments)
                3. Defense Pick: Qualified teams with defense > 0
                4. 1st/2nd/3rd Pick: Qualified non-defensive teams split into thirds
                5. "-" Tier: ONLY disqualified teams (those below min_honor_roll_score or lacking competencies)
                6. Unassigned: Empty (all qualified teams are assigned to top tiers)
                
                Data Source: Uses real-time data from school_system.calculated_scores
                """
                # Get current configuration values from school_system (reflects UI settings)
                current_min_score = st.session_state.school_system.min_honor_roll_score
                current_min_comp = st.session_state.school_system.min_competencies_count
                current_min_subcomp = st.session_state.school_system.min_subcompetencies_count
                
                # Get rankings and disqualified teams (these respect the current configuration)
                rankings = st.session_state.school_system.get_honor_roll_ranking()
                disqualified = st.session_state.school_system.get_disqualified_teams()
                
                # Build a lookup for team stats from analizador (for defense info and additional stats)
                team_stats_lookup = {}
                if hasattr(st.session_state, 'analizador') and st.session_state.analizador:
                    all_team_stats = st.session_state.analizador.get_detailed_team_stats()
                    for stat in all_team_stats:
                        team_num = str(stat.get("team", ""))
                        team_stats_lookup[team_num] = stat
                
                # Helper to check if team played defense
                def has_played_defense(team_num):
                    stat = team_stats_lookup.get(str(team_num), {})
                    # Check various possible field names for defense
                    defense_val = stat.get("defense_rate", 0) or stat.get("defended", 0) or stat.get("defense_count", 0)
                    return defense_val > 0
                
                # ===============================================================
                # STEP 1: Separate QUALIFIED teams into defensive vs non-defensive
                # rankings already contains ONLY qualified teams, sorted by final_points
                # ===============================================================
                defense_pick_teams = []
                qualified_non_defensive = []
                
                for team_num, result in rankings:
                    if has_played_defense(team_num):
                        defense_pick_teams.append((team_num, result))
                    else:
                        qualified_non_defensive.append((team_num, result))
                
                # ===============================================================
                # STEP 2: Distribute QUALIFIED non-defensive teams into 1st/2nd/3rd Pick
                # These are already sorted by final_points (descending)
                # ===============================================================
                total_qualified_non_def = len(qualified_non_defensive)
                
                if total_qualified_non_def > 0:
                    # Split evenly into thirds for 1st, 2nd, 3rd pick
                    tier_size = max(1, total_qualified_non_def // 3)
                    remainder = total_qualified_non_def % 3
                    
                    # Distribute remainder to higher tiers first
                    tier_1_size = tier_size + (1 if remainder >= 1 else 0)
                    tier_2_size = tier_size + (1 if remainder >= 2 else 0)
                    tier_3_size = total_qualified_non_def - tier_1_size - tier_2_size
                    
                    tier_1 = qualified_non_defensive[:tier_1_size]
                    tier_2 = qualified_non_defensive[tier_1_size:tier_1_size + tier_2_size]
                    tier_3 = qualified_non_defensive[tier_1_size + tier_2_size:]
                else:
                    tier_1, tier_2, tier_3 = [], [], []
                
                # ===============================================================
                # STEP 3: DISQUALIFIED teams go to "-" tier (did not meet threshold)
                # This includes teams below min_honor_roll_score or lacking competencies
                # ===============================================================
                disqualified_teams_list = []
                for team_num, reason in disqualified:
                    result = st.session_state.school_system.calculated_scores.get(str(team_num))
                    disqualified_teams_list.append((team_num, result, reason))
                
                # Default placeholder image (small transparent PNG in base64)
                default_image = "iVBORw0KGgoAAAANSUhEUgAAAJYAAACWCAIAAACzY+a1AAAEn0lEQVR4nO3dwW+TdRzH8d+zPutaVtzqlFaSZcKYRNmmhqFZdsCFiHLAaCAkQjxrsosx+i948mCMi3rVhHhwBPGCkUOnxIQJEgOrJW7iAnNAYWNdsXRtNzObzMLM41PWZzxv/bxOa7/wpPu982uftrRY3T3PGSGru983QFZLCfGUEE8J8ZQQTwnxlBBPCfGUEE8J8ZQQTwnxlBBPCfGUEE8J8ZQQTwnxlBBPCfGUEE8J8ZQQTwnxlBBPCfGUEE8J8ZQQTwnxlBBPCfGUEE8J8ZQQTwnxlBBPCfGUEE8J8ZQQTwnxlBBPCfGUEE8J8ZQQTwnx"
                
                # Helper function to get team stats for the Text JSON field
                # Uses REAL-TIME data from school_system.calculated_scores
                def get_team_stats_json(team_num, result):
                    # Get the calculated scores from school_system (real-time data)
                    calculated = st.session_state.school_system.calculated_scores.get(str(team_num))
                    team_scores = st.session_state.school_system.teams.get(str(team_num))
                    
                    # Get additional stats from analizador if available
                    stat = team_stats_lookup.get(str(team_num), {})
                    overall_avg = stat.get("overall_avg", 0.0)
                    robot_valuation = stat.get("robot_valuation", 0.0)
                    defense_rate = stat.get("defense_rate", 0.0) or stat.get("defended", 0.0) or stat.get("defense_count", 0.0)
                    died_rate = stat.get("died_rate", 0.0)
                    matches_played = stat.get("matches_played", 0)
                    
                    # Build stats dict with real-time calculated data
                    stats_dict = {
                        "honor_score": round(calculated.honor_roll_score, 1) if calculated else (round(result.honor_roll_score, 1) if result else 0.0),
                        "curved_score": round(calculated.curved_score, 1) if calculated else 0.0,
                        "final_points": calculated.final_points if calculated else (result.final_points if result else 0),
                        "match_performance": round(calculated.match_performance_score, 1) if calculated else 0.0,
                        "pit_scouting": round(calculated.pit_scouting_score, 1) if calculated else 0.0,
                        "during_event": round(calculated.during_event_score, 1) if calculated else 0.0,
                        "competencies_score": round(calculated.competencies_score, 1) if calculated else 0.0,
                        "overall_avg": round(overall_avg, 1),
                        "robot_valuation": round(robot_valuation, 1),
                        "defense_rate": round(defense_rate, 2),
                        "died_rate": round(died_rate, 2),
                        "matches_played": matches_played
                    }
                    
                    # Add competencies count if available
                    if team_scores:
                        # Use the TeamCompetencies methods to get counts
                        c_count = team_scores.competencies.get_competencies_count()
                        sc_count = team_scores.competencies.get_subcompetencies_count()
                        stats_dict["competencies"] = c_count
                        stats_dict["subcompetencies"] = sc_count
                    
                    # Add feedback text from calculated scores (real-time)
                    feedback_text = ""
                    if calculated and calculated.final_feedback:
                        feedback_text = calculated.final_feedback
                    elif result and result.final_feedback:
                        feedback_text = result.final_feedback
                    
                    if feedback_text:
                        stats_dict["feedback"] = feedback_text
                    
                    return json.dumps(stats_dict, ensure_ascii=False)
                
                # Helper function to generate team block with DriverSkills based on defense
                def generate_team_block(team_num, result, is_defensive=False):
                    stats_json = get_team_stats_json(team_num, result)
                    driver_skills = "Defensive" if is_defensive else "Offensive"
                    
                    # Get scores for title - prioritize final_points since that's the ranking criteria
                    calculated = st.session_state.school_system.calculated_scores.get(str(team_num))
                    final_pts = calculated.final_points if calculated else (result.final_points if result else 0)
                    honor_score = calculated.honor_roll_score if calculated else (result.honor_roll_score if result else 0.0)
                    
                    lines = []
                    lines.append(f"  Image: {default_image}")
                    lines.append(f"    Title: Team {team_num} | Points: {final_pts} | HR: {honor_score:.1f}")
                    lines.append(f"    Text: {stats_json}")
                    lines.append(f"    DriverSkills: {driver_skills}")
                    lines.append(f"    ImageList:")
                    return "\n".join(lines)
                
                # Build the output
                output_lines = []
                
                # Add export header with configuration info
                output_lines.append(f"# TierList Export - Configuration Used:")
                output_lines.append(f"# Min Honor Roll Score: {current_min_score}")
                output_lines.append(f"# Min Competencies: {current_min_comp}")
                output_lines.append(f"# Min Subcompetencies: {current_min_subcomp}")
                output_lines.append(f"# Qualified Teams: {len(rankings)}")
                output_lines.append(f"# Disqualified Teams: {len(disqualified)}")
                output_lines.append("")
                
                # Tier: 1st Pick (top third of qualified non-defensive teams)
                output_lines.append("Tier: 1st Pick")
                for team_num, result in tier_1:
                    output_lines.append(generate_team_block(team_num, result, is_defensive=False))
                output_lines.append("")  # Blank line between tiers
                
                # Tier: 2nd Pick (middle third of qualified non-defensive teams)
                output_lines.append("Tier: 2nd Pick")
                for team_num, result in tier_2:
                    output_lines.append(generate_team_block(team_num, result, is_defensive=False))
                output_lines.append("")
                
                # Tier: 3rd Pick (lower third of qualified non-defensive teams)
                output_lines.append("Tier: 3rd Pick")
                for team_num, result in tier_3:
                    output_lines.append(generate_team_block(team_num, result, is_defensive=False))
                output_lines.append("")
                
                # Tier: Ojito (empty placeholder - can be used for teams to watch)
                output_lines.append("Tier: Ojito")
                output_lines.append("")
                
                # Tier: - (DISQUALIFIED teams - those below min_honor_roll_score or lacking competencies)
                output_lines.append("Tier: -")
                for team_num, result, reason in disqualified_teams_list:
                    output_lines.append(generate_team_block(team_num, result, is_defensive=False))
                output_lines.append("")
                
                # Tier: Defense Pick (QUALIFIED teams with defense > 0)
                output_lines.append("Tier: Defense Pick")
                for team_num, result in defense_pick_teams:
                    output_lines.append(generate_team_block(team_num, result, is_defensive=True))
                output_lines.append("")
                
                # Tier: Unassigned (empty - all qualified teams are assigned)
                output_lines.append("Tier: Unassigned")
                # No teams here - all qualified teams are distributed to top tiers
                
                return "\n".join(output_lines)
            
            import json
            
            # Get summary stats for display
            summary = st.session_state.school_system.get_summary_stats()
            
            # Show export preview info
            st.info(f"""
            **Export Preview:**
            - Min Honor Roll Score: **{st.session_state.school_system.min_honor_roll_score}**
            - Qualified Teams: **{summary.get('qualified_teams', 0)}**
            - Disqualified Teams: **{summary.get('disqualified_teams', 0)}**
            
            *The export will match the qualified teams shown in the Honor Roll Rankings table.*
            """)
            
            tierlist_txt = generate_tierlist_txt()
            
            # TXT Download (primary export format)
            st.download_button(
                label="📥 Export to TierList Maker (.txt)",
                data=tierlist_txt,
                file_name="tier_list.txt",
                mime="text/plain",
                use_container_width=True
            )
    
    # Team Competency Editor Section
    if st.session_state.school_system.teams:
        with st.expander("✏️ Team Competency Editor", expanded=False):
            st.markdown("Select a team to edit their competencies and subcompetencies.")
            
            team_list = sorted(st.session_state.school_system.teams.keys())
            selected_team_edit = st.selectbox(
                "Select Team to Edit",
                options=team_list,
                key="team_competency_editor_select"
            )
            
            if selected_team_edit:
                comp_status = st.session_state.school_system.get_team_competencies_status(selected_team_edit)
                comp_labels = TeamScoring.get_competency_labels()
                subcomp_labels = TeamScoring.get_subcompetency_labels()
                
                st.markdown("#### Competencies")
                comp_cols = st.columns(2)
                
                for i, (key, label) in enumerate(comp_labels.items()):
                    with comp_cols[i % 2]:
                        current_val = comp_status["competencies"].get(key, False)
                        new_val = st.checkbox(label, value=current_val, key=f"comp_{selected_team_edit}_{key}")
                        if new_val != current_val:
                            st.session_state.school_system.update_competency(selected_team_edit, key, new_val)
                
                st.markdown("#### Subcompetencies")
                subcomp_cols = st.columns(2)
                
                for i, (key, label) in enumerate(subcomp_labels.items()):
                    with subcomp_cols[i % 2]:
                        current_val = comp_status["subcompetencies"].get(key, False)
                        new_val = st.checkbox(label, value=current_val, key=f"subcomp_{selected_team_edit}_{key}")
                        if new_val != current_val:
                            st.session_state.school_system.update_competency(selected_team_edit, key, new_val)
                
                if st.button("💾 Save & Recalculate", key="save_competencies"):
                    st.session_state.school_system.calculate_all_scores()
                    st.success(f"Competencies saved for Team {selected_team_edit}!")
                    st.rerun()
    
    # Display rankings
    st.markdown("### Honor Roll Rankings")
    
    if st.session_state.school_system.teams:
        rankings = st.session_state.school_system.get_honor_roll_ranking()
        
        ranking_data = []
        team_numbers_list = []
        for rank, (team_num, results) in enumerate(rankings, 1):
            team_name = st.session_state.tba_manager.get_team_nickname(team_num) if st.session_state.tba_manager else None
            c, sc, rp = st.session_state.school_system.calculate_competencies_score(team_num)
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
        
        # Team Details Inspector
        st.markdown("### 🔍 Team Details Inspector")
        
        if team_numbers_list:
            selected_detail_team = st.selectbox(
                "Select a team to view detailed breakdown",
                options=team_numbers_list,
                key="team_detail_selector"
            )
            
            if selected_detail_team:
                breakdown = st.session_state.school_system.get_team_score_breakdown(selected_detail_team)
                comp_status = st.session_state.school_system.get_team_competencies_status(selected_detail_team)
                
                detail_col1, detail_col2 = st.columns([1, 1])
                
                with detail_col1:
                    st.markdown("#### 📊 Score Breakdown")
                    
                    # Create radar chart data
                    categories = ['Match Performance', 'Pit Scouting', 'During Event']
                    values = [
                        breakdown['match_performance']['total'],
                        breakdown['pit_scouting']['total'],
                        breakdown['during_event']['total']
                    ]
                    
                    # Create bar chart for score breakdown
                    fig = go.Figure()
                    fig.add_trace(go.Bar(
                        x=categories,
                        y=values,
                        marker_color=['#667eea', '#764ba2', '#f093fb'],
                        text=[f"{v:.1f}" for v in values],
                        textposition='auto'
                    ))
                    fig.update_layout(
                        title=f"Team {selected_detail_team} Score Breakdown",
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
                    st.markdown("#### ✅ Competencies Status")
                    
                    comp_labels = TeamScoring.get_competency_labels()
                    subcomp_labels = TeamScoring.get_subcompetency_labels()
                    
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
                
                # Feedback section
                st.markdown("#### 💬 Scouting Comments & Feedback")
                feedback = breakdown.get('final_feedback', '')
                if feedback:
                    st.text_area(
                        "Aggregated Feedback",
                        value=feedback,
                        height=150,
                        disabled=True,
                        key=f"feedback_{selected_detail_team}"
                    )
                else:
                    st.info("No feedback available for this team.")
    else:
        st.info("No teams in Honor Roll System. Please auto-populate from data.")

elif page == "🔮 Foreshadowing":
    st.markdown("<div class='main-header'>🔮 Match Prediction (Foreshadowing)</div>", unsafe_allow_html=True)

    stats = st.session_state.analizador.get_detailed_team_stats()
    if not stats:
        st.info("Load scouting data to unlock match predictions.")
    else:
        team_options = get_foreshadowing_team_options()
        if not team_options:
            st.warning("No teams available. Upload data or fetch TBA event teams.")
        else:
            label_to_team = {label: team for label, team in team_options}
            default_red = [label for label, _ in team_options[:3]]
            default_blue = [label for label, _ in team_options[3:6]] if len(team_options) >= 6 else [label for label, _ in team_options[:3]]

            with st.form("foreshadowing_form"):
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

                st.session_state.foreshadowing_quick_slider = st.slider(
                    "Iterations (quick simulation)",
                    min_value=200,
                    max_value=5000,
                    value=st.session_state.foreshadowing_quick_slider,
                    step=100
                )

                button_cols = st.columns(2)
                with button_cols[0]:
                    run_quick = st.form_submit_button("Run Quick Prediction")
                with button_cols[1]:
                    run_extended = st.form_submit_button("Run Monte Carlo (5000 iterations)")

            selected_red = [label_to_team[label] for label in red_labels if label in label_to_team]
            selected_blue = [label_to_team[label] for label in blue_labels if label in label_to_team]

            if run_quick or run_extended:
                iterations = 5000 if run_extended else st.session_state.foreshadowing_quick_slider
                valid, message = validate_alliance_selection(selected_red, selected_blue)

                if not valid:
                    st.session_state.foreshadowing_error = message
                    st.session_state.foreshadowing_prediction = None
                else:
                    extractor = TeamStatsExtractor(st.session_state.analizador)
                    simulator = MatchSimulator()

                    try:
                        red_perf = [extractor.extract_team_performance(team) for team in selected_red]
                        blue_perf = [extractor.extract_team_performance(team) for team in selected_blue]
                        prediction = simulator.simulate_match(red_perf, blue_perf, num_simulations=iterations)
                    except Exception as err:
                        st.session_state.foreshadowing_error = f"Prediction failed: {err}"
                        st.session_state.foreshadowing_prediction = None
                    else:
                        st.session_state.foreshadowing_prediction = prediction
                        st.session_state.foreshadowing_mode = "Monte Carlo" if run_extended else "Quick"
                        st.session_state.foreshadowing_last_iterations = iterations
                        st.session_state.foreshadowing_last_inputs = {"red": selected_red, "blue": selected_blue}
                        st.session_state.foreshadowing_team_performance = {"red": red_perf, "blue": blue_perf}
                        st.session_state.foreshadowing_error = ""

            if st.session_state.foreshadowing_error:
                st.error(st.session_state.foreshadowing_error)

            prediction = st.session_state.foreshadowing_prediction
            if prediction:
                st.markdown(
                    f"**Simulation Mode:** {st.session_state.foreshadowing_mode} "
                    f"({st.session_state.foreshadowing_last_iterations} iterations)"
                )

                score_cols = st.columns(3)
                with score_cols[0]:
                    st.metric("Red Predicted Score", f"{prediction.red_score:.1f}")
                with score_cols[1]:
                    st.metric("Blue Predicted Score", f"{prediction.blue_score:.1f}")
                with score_cols[2]:
                    diff = prediction.red_score - prediction.blue_score
                    st.metric("Score Differential", f"{diff:.1f}", delta=f"{diff:+.1f}")

                prob_cols = st.columns(3)
                with prob_cols[0]:
                    st.metric("Red Win %", f"{prediction.red_win_probability*100:.1f}%")
                with prob_cols[1]:
                    st.metric("Blue Win %", f"{prediction.blue_win_probability*100:.1f}%")
                with prob_cols[2]:
                    st.metric("Tie %", f"{prediction.tie_probability*100:.1f}%")

                rp_cols = st.columns(2)
                with rp_cols[0]:
                    st.metric("Red RP", prediction.red_rp)
                with rp_cols[1]:
                    st.metric("Blue RP", prediction.blue_rp)

                st.markdown("### Alliance Rosters")
                roster_cols = st.columns(2)
                with roster_cols[0]:
                    st.markdown("**Red Alliance**")
                    for team in st.session_state.foreshadowing_last_inputs["red"]:
                        st.markdown(f"- {get_team_display_label(team)}")
                with roster_cols[1]:
                    st.markdown("**Blue Alliance**")
                    for team in st.session_state.foreshadowing_last_inputs["blue"]:
                        st.markdown(f"- {get_team_display_label(team)}")

                breakdown_tabs = st.tabs(["🔴 Red Breakdown", "🔵 Blue Breakdown", "📊 Team Profiles"])

                with breakdown_tabs[0]:
                    red_breakdown = prediction.red_breakdown
                    coral_df = build_coral_breakdown_df(red_breakdown)
                    algae_df = build_algae_summary_df(red_breakdown)
                    climb_df = build_climb_breakdown_df(red_breakdown)

                    st.markdown("#### Coral Contribution")
                    st.dataframe(coral_df, use_container_width=True)
                    st.markdown("#### Algae Summary")
                    st.dataframe(algae_df, use_container_width=True)
                    st.markdown("#### Climb Performance")
                    st.dataframe(climb_df, use_container_width=True)

                    st.markdown("#### Additional Metrics")
                    st.write(
                        f"Auto Zone: {red_breakdown['teams_left_auto_zone']}/3 | "
                        f"Cooperation: {'✅' if red_breakdown['cooperation_achieved'] else '❌'}"
                    )

                with breakdown_tabs[1]:
                    blue_breakdown = prediction.blue_breakdown
                    coral_df = build_coral_breakdown_df(blue_breakdown)
                    algae_df = build_algae_summary_df(blue_breakdown)
                    climb_df = build_climb_breakdown_df(blue_breakdown)

                    st.markdown("#### Coral Contribution")
                    st.dataframe(coral_df, use_container_width=True)
                    st.markdown("#### Algae Summary")
                    st.dataframe(algae_df, use_container_width=True)
                    st.markdown("#### Climb Performance")
                    st.dataframe(climb_df, use_container_width=True)

                    st.markdown("#### Additional Metrics")
                    st.write(
                        f"Auto Zone: {blue_breakdown['teams_left_auto_zone']}/3 | "
                        f"Cooperation: {'✅' if blue_breakdown['cooperation_achieved'] else '❌'}"
                    )

                with breakdown_tabs[2]:
                    perf_df = build_team_performance_df(
                        st.session_state.foreshadowing_team_performance["red"] +
                        st.session_state.foreshadowing_team_performance["blue"]
                    )
                    st.dataframe(perf_df, use_container_width=True)

                score_components = [
                    {
                        'Alliance': 'Red',
                        'Component': 'Coral',
                        'Points': prediction.red_breakdown['coral_points']
                    },
                    {
                        'Alliance': 'Red',
                        'Component': 'Algae',
                        'Points': prediction.red_breakdown['algae_points']
                    },
                    {
                        'Alliance': 'Red',
                        'Component': 'Climb',
                        'Points': prediction.red_breakdown['climb_points']
                    },
                    {
                        'Alliance': 'Blue',
                        'Component': 'Coral',
                        'Points': prediction.blue_breakdown['coral_points']
                    },
                    {
                        'Alliance': 'Blue',
                        'Component': 'Algae',
                        'Points': prediction.blue_breakdown['algae_points']
                    },
                    {
                        'Alliance': 'Blue',
                        'Component': 'Climb',
                        'Points': prediction.blue_breakdown['climb_points']
                    }
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

                st.write(
                    f"Confidence level: **{confidence}** | Favorite alliance: **{favorite}**"
                )

                red_coral_total = sum(prediction.red_breakdown['coral_scores'].values())
                blue_coral_total = sum(prediction.blue_breakdown['coral_scores'].values())

                if red_coral_total > blue_coral_total * 1.2:
                    st.write("Red shows a strong coral advantage. Blue should focus on defense or endgame points.")
                elif blue_coral_total > red_coral_total * 1.2:
                    st.write("Blue shows a strong coral advantage. Red should prioritize efficiency in grid cycles.")
                else:
                    st.write("Coral cycles are balanced. Endgame and algae control will likely decide the match.")

                st.caption("Foreshadowing simulations use historical averages and random sampling for variability.")

elif page == "⚙️ TBA Settings":
    st.markdown("<div class='main-header'>⚙️ The Blue Alliance Settings</div>", unsafe_allow_html=True)

    use_api = st.toggle(
        "Use The Blue Alliance API (requires internet)",
        key="tba_use_api"
    )

    if use_api:
        st.markdown("""
        <div class='stats-card'>
        <p>To fetch the latest team names, provide your <strong>The Blue Alliance (TBA) API Key</strong>:</p>
        <ol>
            <li>Visit <a href='https://www.thebluealliance.com/account' target='_blank'>thebluealliance.com/account</a>.</li>
            <li>Log in or create an account.</li>
            <li>In <em>Read API Keys</em>, add a description (e.g., "Overture Alliance App") and click <strong>Add New Key</strong>.</li>
            <li>Copy the generated <code>X-TBA-Auth-Key</code> and paste it below.</li>
        </ol>
        </div>
        """, unsafe_allow_html=True)

        st.session_state.tba_api_key = st.text_input(
            "TBA Auth Key (X-TBA-Auth-Key)",
            value=st.session_state.tba_api_key,
            type="password"
        )
    else:
        st.info(
            "Offline mode active: the app will only use cached JSON files (e.g., `events_YYYY.json`, "
            "`teams_<event>.json`) located next to the application."
        )

    if st.button("Initialize TBA Manager"):
        api_key = st.session_state.tba_api_key.strip() or None
        try:
            st.session_state.tba_manager = TBAManager(
                api_key=api_key,
                use_api=use_api
            )
            st.success("TBA Manager initialized successfully!")
        except ValueError as e:
            st.error(str(e))

    if st.session_state.tba_manager:
        st.session_state.tba_manager.api_key = st.session_state.tba_api_key.strip() or st.session_state.tba_manager.api_key
        try:
            st.session_state.tba_manager.set_api_usage(use_api)
        except ValueError:
            st.warning("API access could not be enabled because no key is configured. Staying in offline mode.")
            st.session_state.tba_use_api = False
            use_api = False

    if st.session_state.tba_manager:
        st.markdown("---")
        st.markdown("### Event Selection")

        year = st.number_input("Select Competition Year", min_value=2000, max_value=2050, value=2024)

        if st.button("Fetch Events for Year"):
            events = st.session_state.tba_manager.get_events_for_year(year)
            if events:
                st.session_state.events_list = sorted(events, key=lambda x: x.get('name', ''))
                st.success(f"Found {len(events)} events for {year}.")
            else:
                st.session_state.events_list = []
                if use_api:
                    st.error("Could not fetch events. Check your API key and internet connection.")
                else:
                    st.warning(f"No cached events found for {int(year)}. Add an `events_{int(year)}.json` file to the app directory or enable API access.")

        if st.session_state.events_list:
            event_options = {event['key']: event['name'] for event in st.session_state.events_list}
            selected_key = st.selectbox(
                "Select Event", 
                options=list(event_options.keys()),
                format_func=lambda x: event_options[x]
            )

            if st.button("Load Teams for Selected Event"):
                with st.spinner(f"Loading teams for {event_options[selected_key]}..."):
                    # First, try to load from a local file
                    if st.session_state.tba_manager.load_teams_from_file(selected_key):
                        st.session_state.tba_event_key = selected_key
                        st.session_state.selected_event_name = event_options[selected_key]
                        st.success(f"Loaded {len(st.session_state.tba_manager.team_names)} teams from local cache for {st.session_state.selected_event_name}.")
                    else:
                        # If not found locally, fetch from API
                        teams_data = st.session_state.tba_manager.get_teams_for_event(selected_key)
                        if teams_data:
                            st.session_state.tba_manager.save_teams_to_file(selected_key, teams_data)
                            st.session_state.tba_manager.load_teams_from_file(selected_key) # Load into memory
                            st.session_state.tba_event_key = selected_key
                            st.session_state.selected_event_name = event_options[selected_key]
                            st.success(f"Fetched and saved {len(teams_data)} teams for {st.session_state.selected_event_name}.")
                        else:
                            if use_api:
                                st.error("Failed to fetch team data from TBA API.")
                            else:
                                st.warning(f"No cached team data available for that event. Place a `teams_{selected_key}.json` file in the app directory or enable API access.")
    
    st.markdown("---")
    st.markdown("### Current Status")
    if st.session_state.tba_manager and st.session_state.tba_event_key:
        st.success(f"TBA Manager is active. Loaded data for event: **{st.session_state.selected_event_name}** (`{st.session_state.tba_event_key}`) with **{len(st.session_state.tba_manager.team_names)}** teams.")
    else:
        st.warning("TBA Manager is not active or no event data is loaded. Team names will not be displayed.")

# Footer - appears on all pages
st.markdown("<hr style='margin-top: 3rem; border: 1px solid #e2e8f0;'>", unsafe_allow_html=True)
st.markdown(
    "<div class='footer'>Developed by Team Overture 7421</div>",
    unsafe_allow_html=True
)
