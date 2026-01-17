"""
Streamlit Web Application for Alliance Simulator
Provides a web-based interface for all the core functionality of the desktop application
"""

import streamlit as st
import pandas as pd
import io
import base64
import tempfile
import json
from collections import Counter
from pathlib import Path
from engine import AnalizadorRobot
from allianceSelector import AllianceSelector, Team, teams_from_dicts
from school_system import TeamScoring, BehaviorReportType
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
import os
import threading
import queue
from toa_manager import TOAManager
from default_robot_image import load_team_image
from foreshadowing import TeamStatsExtractor, MatchSimulator
from exam_integrator import ExamDataIntegrator
from qr_utils import scan_qr_codes, test_camera


APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent


def load_app_config():
    """Load application configuration from JSON file.
    
    Returns:
        dict: Configuration dictionary loaded from JSON or default values.
    """
    config_paths = [
        ROOT_DIR / "config" / "config.json",
        APP_DIR / "config" / "config.json",
    ]
    
    config = None
    for config_path in config_paths:
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    break
            except json.JSONDecodeError as e:
                st.warning(f"Failed to parse config from {config_path}: {e}. Using defaults.")
            except IOError as e:
                st.warning(f"Failed to read config from {config_path}: {e}. Using defaults.")
    
    if config is None:
        # Return default config if file not found or failed to load
        config = {
            "app": {
                "title": "Alliance Simulator - Overture 7421",
                "icon": "🤖",
                "subtitle": "FTC DECODE 2026",
                "team_name": "Team Overture 7421"
            },
            "scoring_weights": {
                "match_performance": 50,
                "pit_scouting": 30,
                "during_event": 20
            },
            "game": {
                "name": "DECODE 2026",
                "autonomous": {
                    "leave": 3,
                    "artifact": 3,
                    "overflow": 1,
                    "depot": 1,
                    "pattern_match": 2
                },
                "teleop": {
                    "artifact": 3,
                    "overflow": 1,
                    "depot": 1,
                    "pattern_match": 2
                },
                "endgame": {
                    "park_partial": 5,
                    "park_full": 10,
                    "double_park_bonus": 10
                }
            },
            "metrics": {
                "game_phases": ["autonomous", "teleop", "endgame"],
                "endgame_states": ["park_partial", "park_full"],
                "match_items": ["artifact", "overflow", "depot", "pattern_match"]
            }
        }
    
    # Validate scoring weights sum to 100
    scoring_weights = config.get("scoring_weights", {})
    weights_sum = sum([
        scoring_weights.get("match_performance", 50),
        scoring_weights.get("pit_scouting", 30),
        scoring_weights.get("during_event", 20)
    ])
    if weights_sum != 100:
        st.warning(f"Scoring weights in config sum to {weights_sum}, not 100. Using defaults.")
        config["scoring_weights"] = {
            "match_performance": 50,
            "pit_scouting": 30,
            "during_event": 20
        }
    
    return config


# Load configuration
APP_CONFIG = load_app_config()

# Page configuration - uses values from APP_CONFIG
app_config = APP_CONFIG.get("app", {})
st.set_page_config(
    page_title=app_config.get("title", "Alliance Simulator - Overture 7421"),
    page_icon=app_config.get("icon", "🤖"),
    layout=app_config.get("layout", "wide"),
    initial_sidebar_state=app_config.get("initial_sidebar_state", "expanded"),
    menu_items={
        'About': f"{app_config.get('title', 'Alliance Simulator')} | {app_config.get('subtitle', 'FRC 2025')}"
    }
)

# Initialize session state
if 'analizador' not in st.session_state:
    st.session_state.analizador = AnalizadorRobot()
if 'auto_decode_reset_done' not in st.session_state:
    st.session_state.auto_decode_reset_done = False
if not st.session_state.auto_decode_reset_done:
    try:
        raw_data = st.session_state.analizador.get_raw_data()
        if raw_data and raw_data[0]:
            header = raw_data[0]
            has_frc_columns = any("Coral" in col or "Algae" in col for col in header)
            decode_header = st.session_state.analizador.config_manager.get_column_config().headers
            has_decode_columns = any("Artifacts Scored" in col for col in decode_header)
            if has_frc_columns and has_decode_columns:
                st.session_state.analizador.set_raw_data([decode_header])
                st.session_state.auto_decode_reset_done = True
    except Exception:
        st.session_state.auto_decode_reset_done = True
if 'alliance_selector' not in st.session_state:
    st.session_state.alliance_selector = None
if 'school_system' not in st.session_state:
    st.session_state.school_system = TeamScoring()
if 'toa_manager' not in st.session_state:
    st.session_state.toa_manager = None
if 'toa_api_key' not in st.session_state:
    st.session_state.toa_api_key = ""
if 'toa_application_origin' not in st.session_state:
    st.session_state.toa_application_origin = ""
if 'toa_use_api' not in st.session_state:
    st.session_state.toa_use_api = True
if 'toa_event_key' not in st.session_state:
    st.session_state.toa_event_key = ""
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
    # Initialize scoring weights from config
    config_weights = APP_CONFIG.get("scoring_weights", {})
    st.session_state.scoring_weights = {
        "match": config_weights.get("match_performance", 50),
        "pit": config_weights.get("pit_scouting", 30),
        "event": config_weights.get("during_event", 20)
    }
if 'selected_team_for_details' not in st.session_state:
    st.session_state.selected_team_for_details = None
if 'app_config' not in st.session_state:
    st.session_state.app_config = APP_CONFIG

# QR Scanner state (used in Data Management -> QR Code Scanner)
if 'qr_scanner_queue' not in st.session_state:
    st.session_state.qr_scanner_queue = queue.Queue()
if 'qr_scanner_thread' not in st.session_state:
    st.session_state.qr_scanner_thread = None
if 'qr_scanner_running' not in st.session_state:
    st.session_state.qr_scanner_running = False
if 'qr_scanner_selected_camera' not in st.session_state:
    st.session_state.qr_scanner_selected_camera = 0
if 'qr_available_cameras' not in st.session_state:
    st.session_state.qr_available_cameras = []
if 'qr_scanned_codes' not in st.session_state:
    st.session_state.qr_scanned_codes = []
if 'qr_scanner_status' not in st.session_state:
    st.session_state.qr_scanner_status = ""
if 'qr_scanner_debounce_seconds' not in st.session_state:
    st.session_state.qr_scanner_debounce_seconds = 2.0

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
    
    toa_manager = st.session_state.toa_manager
    team_data_grouped = st.session_state.analizador.get_team_data_grouped()
    
    # Convert to DataFrame with selected columns for simplified view
    df_data = []
    for team_stat in stats:
        team_num = team_stat.get('team', 'N/A')
        team_name = toa_manager.get_team_nickname(team_num) if toa_manager else team_num
        team_key = str(team_num)
        team_rows = team_data_grouped.get(team_key, [])

        defense_rate = get_rate_from_stat(team_stat, ("Played Defense",)) * 100.0
        death_rate = get_rate_from_stat(team_stat, ("Died/Stopped Moving in Teleop",)) * 100.0
        cycle_focus_mode = get_mode_from_rows(team_rows, "Cycle Focus")
        climb_mode = get_mode_from_rows(team_rows, "Climbed On Top of Another Robot")
        df_data.append({
            'Team': f"{team_num} - {team_name}",
            'Overall Avg': round(team_stat.get('overall_avg', 0.0), 2),
            'Overall Std': round(team_stat.get('overall_std', 0.0), 2),
            'Robot Valuation': round(team_stat.get('RobotValuation', 0.0), 2),
            'Defense Rate (%)': round(defense_rate, 2),
            'Died Rate (%)': round(death_rate, 2),
            'Cycle Focus': cycle_focus_mode,
            'Climb On Top Mode': climb_mode,
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
        death_rate = get_rate_from_stat(stat, ("Died/Stopped Moving in Teleop",))
        defended_rate = get_rate_from_stat(stat, ("Was Defended Heavily",))
        defense_rate = get_rate_from_stat(stat, ("Played Defense",))
        
        team_name = st.session_state.toa_manager.get_team_nickname(team_num) if st.session_state.toa_manager else f"Team {team_num}"

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
            algae_score=0.0
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
    if st.session_state.toa_manager:
        nickname = st.session_state.toa_manager.get_team_nickname(num_str)
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
    if len(red) != 2 or len(blue) != 2:
        return False, "Select exactly 2 teams for each alliance."

    combined = red + blue
    if len(set(combined)) != len(combined):
        return False, "Each team must be unique across both alliances."

    return True, ""


def build_coral_breakdown_df(breakdown):
    data = [
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
    ]
    return pd.DataFrame(data)


def build_algae_summary_df(breakdown):
    return pd.DataFrame([
        {'Return': 'None', 'Teams': breakdown['endgame_returns']['none']},
        {'Return': 'Partial', 'Teams': breakdown['endgame_returns']['partial']},
        {'Return': 'Full', 'Teams': breakdown['endgame_returns']['full']},
        {'Return': 'Double Park Bonus', 'Teams': 1 if breakdown.get('double_park_bonus', 0) else 0}
    ])


def build_climb_breakdown_df(breakdown):
    rows = []
    for team, return_type, points in breakdown['endgame_scores']:
        rows.append({
            'Team': get_team_display_label(team),
            'Return': return_type.capitalize(),
            'Points': points
        })
    return pd.DataFrame(rows)


def build_team_performance_df(team_performances):
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
    return pd.DataFrame(rows)

# Sidebar navigation with enhanced design - uses config values
sidebar_config = APP_CONFIG.get("app", {})
game_config = APP_CONFIG.get("game", {})
st.sidebar.markdown(f"""
<div style='text-align: center; padding: 1rem 0;'>
    <h1 style='color: white; font-size: 2.5rem; margin: 0;'>{sidebar_config.get('icon', '🤖')}</h1>
    <h2 style='color: white; font-weight: 700; margin: 0.5rem 0;'>Alliance Simulator</h2>
    <p style='color: rgba(255,255,255,0.8); font-size: 0.9rem; margin: 0;'>{sidebar_config.get('team_name', 'Team Overture 7421')}</p>
    <p style='color: rgba(255,255,255,0.7); font-size: 0.8rem; margin: 0.2rem 0;'>{game_config.get('name', 'FTC DECODE 2026')}</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("<hr style='border: 1px solid rgba(255,255,255,0.2); margin: 1rem 0;'>", unsafe_allow_html=True)

st.sidebar.markdown("### 📍 Navigation")

page = st.sidebar.radio(
    "Select Page",
    ["📊 Dashboard", "📁 Data Management", "📈 Team Statistics", 
     "🤝 Alliance Selector", "🏆 Honor Roll System", "🔮 Foreshadowing", "⚙️ TOA Settings"],
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
            team_name = st.session_state.toa_manager.get_team_nickname(team_num) if st.session_state.toa_manager else team_num
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
                team_name = st.session_state.toa_manager.get_team_nickname(team_num) if st.session_state.toa_manager else team_num
                st.markdown(f"<div class='team-badge'>{team_num} - {team_name}</div>", unsafe_allow_html=True)
                st.markdown(f"Overall: **{top_team.get('overall_avg', 0.0):.2f}**")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("<div class='stats-card'>", unsafe_allow_html=True)
            st.markdown("**🎯 Most Consistent**")
            if stats:
                consistent_team = min(stats, key=lambda x: x.get('overall_std', 100))
                team_num = consistent_team.get('team', 'N/A')
                team_name = st.session_state.toa_manager.get_team_nickname(team_num) if st.session_state.toa_manager else team_num
                st.markdown(f"<div class='team-badge'>{team_num} - {team_name}</div>", unsafe_allow_html=True)
                st.markdown(f"Std Dev: **{consistent_team.get('overall_std', 0.0):.2f}**")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col3:
            st.markdown("<div class='stats-card'>", unsafe_allow_html=True)
            st.markdown("**⚙️ Best Robot**")
            if stats:
                best_robot = max(stats, key=lambda x: x.get('RobotValuation', 0))
                team_num = best_robot.get('team', 'N/A')
                team_name = st.session_state.toa_manager.get_team_nickname(team_num) if st.session_state.toa_manager else team_num
                st.markdown(f"<div class='team-badge'>{team_num} - {team_name}</div>", unsafe_allow_html=True)
                st.markdown(f"Valuation: **{best_robot.get('RobotValuation', 0.0):.2f}**")
            st.markdown("</div>", unsafe_allow_html=True)

elif page == "📁 Data Management":
    st.markdown("<div class='main-header'>📁 Data Management</div>", unsafe_allow_html=True)
    
    tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload Data", "📷 QR Scanner", "📋 View Raw Data", "💾 Export Data"])
    
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
        
        st.markdown("---")
        st.markdown("### 📂 Default Scouting CSV")
        default_csv_path = st.session_state.analizador.get_default_csv_path()
        
        if default_csv_path.exists():
            st.success(f"✅ Default CSV found: `{default_csv_path}`")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("🔄 Reload Default CSV"):
                    if st.session_state.analizador.reload_csv():
                        st.success("Default CSV reloaded successfully!")
                        st.rerun()
                    else:
                        st.error("Failed to reload CSV")
            with col2:
                # Hot reload toggle
                if 'hot_reload_enabled' not in st.session_state:
                    st.session_state.hot_reload_enabled = False
                
                if st.button("🔥 Toggle Hot Reload"):
                    st.session_state.hot_reload_enabled = not st.session_state.hot_reload_enabled
                    if st.session_state.hot_reload_enabled:
                        st.session_state.analizador.start_hot_reload(interval_seconds=5.0)
                        st.info("Hot reload enabled - checking for changes every 5 seconds")
                    else:
                        st.session_state.analizador.stop_hot_reload()
                        st.info("Hot reload disabled")
        else:
            st.info(f"ℹ️ Place a CSV file at `{default_csv_path}` for auto-loading on startup")
    
    with tab2:
        st.markdown("### 📷 QR Code Scanner")
        st.markdown("""
        Use your webcam to scan QR codes containing scouting data.
        
        **Requirements:**
        - `opencv-python` and `pyzbar` must be installed
        - Webcam access required
        """)

        # Validate dependencies (opencv-python, pyzbar, numpy)
        deps_ok = True
        deps_error = None
        try:
            # This will raise a helpful ImportError if opencv isn't installed.
            _ = test_camera(0)
        except ImportError as e:
            deps_ok = False
            deps_error = str(e)

        if not deps_ok:
            st.warning(
                "⚠️ QR scanner dependencies not installed or not available. "
                "Install with: `pip install opencv-python pyzbar numpy`"
            )
            if deps_error:
                st.caption(deps_error)
        else:
            st.info(
                "Scanning opens a separate OpenCV window on the same machine running Streamlit. "
                "To stop scanning, focus that window and press 'q'."
            )

            # Drain queue items from the scanner thread into session_state.
            def _drain_qr_queue() -> tuple[int, bool]:
                drained = 0
                auto_updated = False
                q = st.session_state.qr_scanner_queue
                while True:
                    try:
                        kind, payload = q.get_nowait()
                    except queue.Empty:
                        break

                    if kind == "SCAN":
                        if payload and payload not in st.session_state.qr_scanned_codes:
                            st.session_state.qr_scanned_codes.append(payload)
                            drained += 1
                            st.session_state.analizador.load_qr_data(payload)
                            auto_updated = True
                    elif kind == "DONE":
                        st.session_state.qr_scanner_running = False
                        st.session_state.qr_scanner_status = "Scanner stopped."
                    elif kind == "ERROR":
                        st.session_state.qr_scanner_running = False
                        st.session_state.qr_scanner_status = f"Scanner error: {payload}"

                t = st.session_state.qr_scanner_thread
                if st.session_state.qr_scanner_running and t and not t.is_alive():
                    st.session_state.qr_scanner_running = False
                    if not st.session_state.qr_scanner_status:
                        st.session_state.qr_scanner_status = "Scanner stopped."

                return drained, auto_updated

            _, auto_updated = _drain_qr_queue()
            if auto_updated:
                st.rerun()

            st.markdown("#### 🎥 Camera Selection")
            cam_cols = st.columns([1, 1])
            with cam_cols[0]:
                max_probe = st.number_input(
                    "Max camera index to probe",
                    min_value=0,
                    max_value=20,
                    value=4,
                    step=1,
                    help="Checks camera indices 0..N and lists the ones that open successfully."
                )
                if st.button("Detect available cameras"):
                    available = []
                    for idx in range(int(max_probe) + 1):
                        try:
                            if test_camera(idx):
                                available.append(idx)
                        except Exception:
                            pass
                    st.session_state.qr_available_cameras = available
                    if available:
                        st.session_state.qr_scanner_selected_camera = int(available[0])
                        st.session_state.qr_scanner_status = f"Detected cameras: {available}"
                    else:
                        st.session_state.qr_scanner_status = (
                            "No cameras detected. Try a different max index or enter one manually."
                        )

            with cam_cols[1]:
                if st.session_state.qr_available_cameras:
                    selected = st.selectbox(
                        "Camera index",
                        options=st.session_state.qr_available_cameras,
                        index=st.session_state.qr_available_cameras.index(st.session_state.qr_scanner_selected_camera)
                        if st.session_state.qr_scanner_selected_camera in st.session_state.qr_available_cameras
                        else 0
                    )
                    st.session_state.qr_scanner_selected_camera = int(selected)
                else:
                    st.session_state.qr_scanner_selected_camera = int(
                        st.number_input(
                            "Camera index",
                            min_value=0,
                            max_value=20,
                            value=int(st.session_state.qr_scanner_selected_camera),
                            step=1,
                            help="If detection doesn't find your camera, try 0, 1, 2..."
                        )
                    )

            st.session_state.qr_scanner_debounce_seconds = float(
                st.number_input(
                    "Debounce seconds",
                    min_value=0.0,
                    max_value=10.0,
                    value=float(st.session_state.qr_scanner_debounce_seconds),
                    step=0.5,
                    help="Prevents repeated reads of the same QR code while it stays in view."
                )
            )

            action_cols = st.columns(2)
            with action_cols[0]:
                if st.button("🔍 Test Selected Camera"):
                    with st.spinner("Testing camera..."):
                        if test_camera(int(st.session_state.qr_scanner_selected_camera)):
                            st.success("✅ Camera test successful!")
                        else:
                            st.error("❌ Camera not available. Please check your webcam.")

            with action_cols[1]:
                status = st.session_state.qr_scanner_status or (
                    "Running" if st.session_state.qr_scanner_running else "Idle"
                )
                st.write(f"Status: {status}")

            st.markdown("---")
            st.markdown("#### 🔍 Scanning")
            start_disabled = bool(st.session_state.qr_scanner_running)
            if st.button("Start QR Scanner (opens new window)", disabled=start_disabled):
                # Clear any old queue messages
                q = st.session_state.qr_scanner_queue
                while True:
                    try:
                        q.get_nowait()
                    except queue.Empty:
                        break

                camera_index = int(st.session_state.qr_scanner_selected_camera)
                debounce = float(st.session_state.qr_scanner_debounce_seconds)

                def _worker(out_queue: "queue.Queue", cam_idx: int, debounce_seconds: float):
                    try:
                        scanned = scan_qr_codes(
                            update_callback=lambda data: out_queue.put(("SCAN", data)),
                            camera_index=cam_idx,
                            debounce_seconds=debounce_seconds,
                            show_window=True,
                        )
                        out_queue.put(("DONE", scanned))
                    except Exception as e:
                        out_queue.put(("ERROR", str(e)))

                st.session_state.qr_scanner_running = True
                st.session_state.qr_scanner_status = f"Starting scanner on camera {camera_index}..."
                t = threading.Thread(
                    target=_worker,
                    args=(st.session_state.qr_scanner_queue, camera_index, debounce),
                    daemon=True,
                )
                st.session_state.qr_scanner_thread = t
                t.start()

            refresh_cols = st.columns(2)
            with refresh_cols[0]:
                if st.button("Update scanned list"):
                    added, auto_updated = _drain_qr_queue()
                    status = f"Updated. Added {added} new code(s)."
                    if auto_updated:
                        status += " QR data loaded into raw data."
                    st.session_state.qr_scanner_status = status
            with refresh_cols[1]:
                if st.button("Clear scanned list"):
                    st.session_state.qr_scanned_codes = []
                    st.session_state.qr_scanner_status = "Cleared scanned list."

            st.markdown("---")
            st.markdown("#### 📋 Results")
            st.metric("Scanned QR codes", len(st.session_state.qr_scanned_codes))
            if st.session_state.qr_scanned_codes:
                st.dataframe(pd.DataFrame({"QR Data": st.session_state.qr_scanned_codes}))
            else:
                st.caption("No QR codes scanned yet.")

            st.markdown("---")
            st.markdown("### 🖥️ Headless Mode (Linux)")
            st.markdown("""
            For headless deployments with barcode/QR scanners acting as HID devices:

            1. Configure scanner hardware ID in `columnsConfig.json`
            2. Run the HID interceptor: `python lib/headless_interceptor.py`
            3. Or use systemd services: `sudo scripts/install_services.sh --enable-hid`

            The interceptor captures scanner input and writes to `data/default_scouting.csv`.
            """)

    with tab3:
        st.markdown("### 📋 Raw Data View")
        raw_data = st.session_state.analizador.get_raw_data()
        
        if raw_data and len(raw_data) > 1:
            header = raw_data[0]
            target_len = len(header)
            normalized_rows = []
            for row in raw_data[1:]:
                if len(row) < target_len:
                    row = list(row) + [""] * (target_len - len(row))
                elif len(row) > target_len:
                    row = list(row)[:target_len]
                normalized_rows.append(row)
            df = pd.DataFrame(normalized_rows, columns=header)
            st.dataframe(df, use_container_width=True, height=400)
            
            st.markdown(f"**Total Records:** {len(raw_data) - 1}")

            st.markdown("---")
            st.markdown("### ✏️ Edit Raw Data")
            st.caption("Modify cells below and click Save Changes to update the dataset.")
            with st.form("raw_data_edit_form"):
                edited_df = st.data_editor(
                    df,
                    use_container_width=True,
                    height=420,
                    num_rows="dynamic",
                    key="raw_data_editor"
                )
                save_changes = st.form_submit_button("Save Changes")

            if save_changes:
                cleaned_df = edited_df.fillna("")
                rows = cleaned_df.values.tolist()
                new_sheet = [raw_data[0]] + [[str(cell) for cell in row] for row in rows]
                st.session_state.analizador.set_raw_data(new_sheet)
                st.success("Raw data updated. Stats will refresh automatically.")
                st.rerun()
        else:
            st.info("No data loaded yet. Please upload a CSV file or paste QR data.")
    
    with tab4:
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

            auto_decode_columns = [
                ("Artifacts Scored (CLASSIFIED) (Auto)", "Auto Classified"),
                ("Artifacts Scored (OVERFLOW) (Auto)", "Auto Overflow"),
                ("Artifacts Placed in Depot (Auto)", "Auto Depot"),
                ("Pattern Matches at End of Auto (0-9)", "Auto Pattern Matches"),
            ]
            teleop_decode_columns = [
                ("Artifacts Scored (CLASSIFIED) (Teleop)", "Teleop Classified"),
                ("Artifacts Scored (OVERFLOW) (Teleop)", "Teleop Overflow"),
                ("Artifacts Placed in Depot (Teleop)", "Teleop Depot"),
                ("How many artifacts failed to score?", "Teleop Failed"),
                ("Pattern Matches at End of Match (0-9)", "Teleop Pattern Matches"),
            ]
            rate_columns = [
                (("No Show",), "No Show Rate (%)"),
                (("Left Launch Line (LEAVE)",), "Leave Rate (%)"),
                (("Played Defense",), "Played Defense Rate (%)"),
                (("Was Defended Heavily",), "Defended Heavily Rate (%)"),
                (("Died/Stopped Moving in Auto",), "Auto Died Rate (%)"),
                (("Died/Stopped Moving in Teleop",), "Teleop Died Rate (%)"),
                (("Returned to Base",), "Returned to Base Rate (%)"),
                (("Climbed On Top of Another Robot",), "Climb On Top Rate (%)"),
                (("Tipped/Fell Over",), "Tip/Fall Rate (%)"),
                (("Broke / Major Failure",), "Broke Rate (%)"),
            ]

            base_columns = [
                'Rank', 'Team', 'Matches',
                'Robot Valuation', 'Overall Avg', 'Overall Std'
            ]
            auto_labels = [label for _, label in auto_decode_columns]
            teleop_labels = [label for _, label in teleop_decode_columns]
            rate_labels = [label for _, label in rate_columns]
            columns_order = (
                base_columns
                + auto_labels
                + teleop_labels
                + rate_labels
            )

            df_rows = []
            for rank, team_stat in enumerate(stats, 1):
                team_num = team_stat.get('team', 'N/A')
                team_name = st.session_state.toa_manager.get_team_nickname(team_num) if st.session_state.toa_manager else team_num
                row = {
                    'Rank': rank,
                    'Team': f"{team_num} - {team_name}",
                    'Matches': len(team_data_grouped.get(team_num, [])),
                    'Robot Valuation': round(team_stat.get('RobotValuation', 0.0), 2),
                    'Overall Avg': round(team_stat.get('overall_avg', 0.0), 2),
                    'Overall Std': round(team_stat.get('overall_std', 0.0), 2),
                }

                for source_col, label in auto_decode_columns + teleop_decode_columns:
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
            
            # Add compare mode toggle
            compare_mode = st.checkbox("🔀 Compare Multiple Teams", key="compare_mode_toggle")
            
            if compare_mode:
                # Multi-team comparison mode
                st.markdown("#### Multi-Team Comparison")
                
                if st.session_state.toa_manager:
                    team_options = {
                        team: f"{team} - {st.session_state.toa_manager.get_team_nickname(team)}"
                        for team in all_teams
                    }
                    selected_teams = st.multiselect(
                        "Select Teams to Compare (2 or more)",
                        options=list(team_options.keys()),
                        format_func=lambda x: team_options[x],
                        default=list(team_options.keys())[:2] if len(team_options) >= 2 else []
                    )
                else:
                    selected_teams = st.multiselect(
                        "Select Teams to Compare (2 or more)",
                        options=all_teams,
                        default=all_teams[:2] if len(all_teams) >= 2 else []
                    )
                
                if len(selected_teams) >= 2:
                    # Get stats for selected teams
                    selected_stats = [s for s in stats if s.get('team') in selected_teams]
                    
                    # Side-by-side metrics display using columns
                    st.markdown("#### Key Metrics Comparison")
                    cols = st.columns(len(selected_teams))
                    
                    for idx, team_num in enumerate(selected_teams):
                        team_stat = next((s for s in stats if s.get('team') == team_num), None)
                        if team_stat:
                            with cols[idx]:
                                team_name = team_num
                                if st.session_state.toa_manager:
                                    team_name = f"{team_num} - {st.session_state.toa_manager.get_team_nickname(team_num)}"
                                team_rows = team_data_grouped.get(team_num, [])
                                auto_classified_avg = compute_numeric_average(team_rows, "Artifacts Scored (CLASSIFIED) (Auto)")
                                teleop_classified_avg = compute_numeric_average(team_rows, "Artifacts Scored (CLASSIFIED) (Teleop)")
                                st.markdown(f"**{team_name}**")
                                st.metric("Overall Avg", f"{team_stat.get('overall_avg', 0):.2f}")
                                st.metric("Robot Valuation", f"{team_stat.get('RobotValuation', 0):.2f}")
                                st.metric("Auto Classified Avg", f"{auto_classified_avg:.2f}")
                                st.metric("Teleop Classified Avg", f"{teleop_classified_avg:.2f}")
                                died_rate = get_rate_from_stat(team_stat, ("Died/Stopped Moving in Teleop",))
                                st.metric("Teleop Died Rate", f"{died_rate * 100:.1f}%")
                    
                    # Radar chart comparison
                    st.markdown("#### Performance Radar Chart")
                    
                    # Prepare radar data
                    categories = ['Overall Avg', 'Robot Valuation', 'Auto Classified', 'Teleop Classified', 'Consistency']
                    
                    radar_fig = go.Figure()
                    
                    # Normalize values for radar chart - safely handle zero maximum values
                    max_overall_val = max((s.get('overall_avg', 0) for s in selected_stats), default=0)
                    max_overall = max_overall_val if max_overall_val > 0 else 1
                    max_robot_val_raw = max((s.get('RobotValuation', 0) for s in selected_stats), default=0)
                    max_robot_val = max_robot_val_raw if max_robot_val_raw > 0 else 1
                    auto_classified_vals = [
                        compute_numeric_average(team_data_grouped.get(s.get('team', ''), []), "Artifacts Scored (CLASSIFIED) (Auto)")
                        for s in selected_stats
                    ]
                    teleop_classified_vals = [
                        compute_numeric_average(team_data_grouped.get(s.get('team', ''), []), "Artifacts Scored (CLASSIFIED) (Teleop)")
                        for s in selected_stats
                    ]
                    max_auto_classified = max(auto_classified_vals) if auto_classified_vals else 1
                    max_auto_classified = max_auto_classified if max_auto_classified > 0 else 1
                    max_teleop_classified = max(teleop_classified_vals) if teleop_classified_vals else 1
                    max_teleop_classified = max_teleop_classified if max_teleop_classified > 0 else 1
                    
                    # Use chart colors from config if available
                    ui_config = APP_CONFIG.get("ui", {})
                    chart_colors = ui_config.get("chart_colors", {})
                    colors = px.colors.qualitative.Set2
                    
                    for idx, team_stat in enumerate(selected_stats):
                        team_num = team_stat.get('team', 'N/A')
                        team_rows = team_data_grouped.get(team_num, [])
                        auto_classified_avg = compute_numeric_average(team_rows, "Artifacts Scored (CLASSIFIED) (Auto)")
                        teleop_classified_avg = compute_numeric_average(team_rows, "Artifacts Scored (CLASSIFIED) (Teleop)")
                        
                        # Calculate consistency (inverse of std dev relative to avg)
                        overall_avg = team_stat.get('overall_avg', 0)
                        overall_std = team_stat.get('overall_std', 0)
                        consistency = (1 - (overall_std / (overall_avg + 0.01))) * 100 if overall_avg > 0 else 50
                        consistency = max(0, min(100, consistency))
                        
                        values = [
                            (team_stat.get('overall_avg', 0) / max_overall) * 100 if max_overall > 0 else 0,
                            (team_stat.get('RobotValuation', 0) / max_robot_val) * 100 if max_robot_val > 0 else 0,
                            (auto_classified_avg / max_auto_classified) * 100 if max_auto_classified > 0 else 0,
                            (teleop_classified_avg / max_teleop_classified) * 100 if max_teleop_classified > 0 else 0,
                            consistency
                        ]
                        
                        radar_fig.add_trace(go.Scatterpolar(
                            r=values + [values[0]],  # Close the polygon
                            theta=categories + [categories[0]],
                            fill='toself',
                            name=f"Team {team_num}",
                            line=dict(color=colors[idx % len(colors)])
                        ))
                    
                    radar_fig.update_layout(
                        polar=dict(
                            radialaxis=dict(visible=True, range=[0, 100]),
                            bgcolor='rgba(0,0,0,0)'
                        ),
                        showlegend=True,
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#f8fafc'),
                        title="Team Performance Comparison"
                    )
                    st.plotly_chart(radar_fig, use_container_width=True)
                    
                    # Bar chart comparison
                    st.markdown("#### Side-by-Side Bar Comparison")
                    
                    comparison_metrics = ['overall_avg', 'RobotValuation', 'auto_classified_avg', 'teleop_classified_avg']
                    metric_labels = ['Overall Avg', 'Robot Valuation', 'Auto Classified', 'Teleop Classified']
                    
                    bar_data = []
                    for team_stat in selected_stats:
                        team_num = team_stat.get('team', 'N/A')
                        team_rows = team_data_grouped.get(team_num, [])
                        auto_classified_avg = compute_numeric_average(team_rows, "Artifacts Scored (CLASSIFIED) (Auto)")
                        teleop_classified_avg = compute_numeric_average(team_rows, "Artifacts Scored (CLASSIFIED) (Teleop)")
                        for metric, label in zip(comparison_metrics, metric_labels):
                            if metric == 'auto_classified_avg':
                                value = auto_classified_avg
                            elif metric == 'teleop_classified_avg':
                                value = teleop_classified_avg
                            else:
                                value = team_stat.get(metric, 0)
                            bar_data.append({
                                'Team': f"Team {team_num}",
                                'Metric': label,
                                'Value': value
                            })
                    
                    bar_df = pd.DataFrame(bar_data)
                    bar_fig = px.bar(
                        bar_df,
                        x='Metric',
                        y='Value',
                        color='Team',
                        barmode='group',
                        title='Metrics Comparison'
                    )
                    bar_fig.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#f8fafc'),
                        xaxis=dict(color='#d1d5db'),
                        yaxis=dict(color='#d1d5db')
                    )
                    st.plotly_chart(bar_fig, use_container_width=True)
                    
                    # Comparison table
                    st.markdown("#### Detailed Comparison Table")
                    comparison_df = pd.DataFrame(selected_stats)
                    comparison_df = comparison_df.set_index('team')
                    key_columns = ['overall_avg', 'overall_std', 'RobotValuation']
                    available_columns = [col for col in key_columns if col in comparison_df.columns]
                    if available_columns:
                        base_table = comparison_df[available_columns].T
                        extra_rows = {}
                        for team_num in selected_teams:
                            team_rows = team_data_grouped.get(team_num, [])
                            extra_rows.setdefault('auto_classified_avg', {})[team_num] = compute_numeric_average(
                                team_rows, "Artifacts Scored (CLASSIFIED) (Auto)"
                            )
                            extra_rows.setdefault('teleop_classified_avg', {})[team_num] = compute_numeric_average(
                                team_rows, "Artifacts Scored (CLASSIFIED) (Teleop)"
                            )
                        extra_df = pd.DataFrame(extra_rows)
                        extra_df = extra_df.T
                        extra_df.index = ['Auto Classified Avg', 'Teleop Classified Avg']
                        comparison_table = pd.concat([base_table, extra_df], axis=0)
                        st.dataframe(comparison_table, use_container_width=True)
                    
                elif len(selected_teams) == 1:
                    st.info("Please select at least 2 teams to compare.")
                else:
                    st.info("Select teams to compare from the dropdown above.")
            
            else:
                # Single team selection mode (original behavior)
                if st.session_state.toa_manager:
                    team_options = {
                        team: f"{team} - {st.session_state.toa_manager.get_team_nickname(team)}"
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
                        team_rows = st.session_state.analizador.get_team_data_grouped().get(str(selected_team_num), [])
                        col1, col2, col3 = st.columns(3)
                        
                        with col1:
                            st.metric("Overall Average", f"{team_stat.get('overall_avg', 0):.2f}")
                            st.metric("Overall Std Dev", f"{team_stat.get('overall_std', 0):.2f}")
                        
                        with col2:
                            st.metric("Robot Valuation", f"{team_stat.get('RobotValuation', 0):.2f}")
                            auto_classified_avg = compute_numeric_average(team_rows, "Artifacts Scored (CLASSIFIED) (Auto)")
                            st.metric("Auto Classified Avg", f"{auto_classified_avg:.2f}")
                        
                        with col3:
                            teleop_classified_avg = compute_numeric_average(team_rows, "Artifacts Scored (CLASSIFIED) (Teleop)")
                            st.metric("Teleop Classified Avg", f"{teleop_classified_avg:.2f}")
                            died_rate = get_rate_from_stat(team_stat, ("Died/Stopped Moving in Teleop",))
                            st.metric("Teleop Died Rate", f"{died_rate * 100:.1f}%")
                        
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

                        analyzer = st.session_state.analizador
                        team_rows = analyzer.get_team_data_grouped().get(str(selected_team_num), [])
                        match_idx = analyzer._column_indices.get('Match Number')

                        def _parse_numeric(value):
                            if value is None:
                                return None
                            # Avoid accidental scaling: booleans are not valid numeric match metrics here.
                            # (`bool` is a subclass of `int`, so this must come before the (int, float) check.)
                            if isinstance(value, bool):
                                return None
                            if isinstance(value, (int, float)):
                                return float(value)
                            if isinstance(value, str):
                                v = value.strip().lower()
                                try:
                                    return float(v)
                                except ValueError:
                                    return None
                            try:
                                return float(value)
                            except (TypeError, ValueError):
                                return None

                        def _parse_bool(value):
                            if value is None:
                                return False
                            if isinstance(value, bool):
                                return value
                            if isinstance(value, (int, float)):
                                return float(value) != 0.0
                            if isinstance(value, str):
                                v = value.strip().lower()
                                return v in {"1", "true", "t", "yes", "y", "si", "sí", "x"}
                            return False

                        if match_idx is None:
                            st.warning("Match Number column not found; cannot build trend chart.")
                        elif not team_rows:
                            st.info("No match performance data available for this team.")
                        else:
                            from collections import defaultdict

                            # Compute DECODE match points based on current config.
                            game_cfg = APP_CONFIG.get("game", {})
                            auto_points = game_cfg.get("autonomous", {}) or {}
                            teleop_points = game_cfg.get("teleop", {}) or {}
                            endgame_points = game_cfg.get("endgame", {}) or {}

                            def _get_value(row, col_name):
                                col_idx = analyzer._column_indices.get(col_name)
                                if col_idx is None or col_idx >= len(row):
                                    return None
                                return row[col_idx]

                            def _get_num(row, col_name, default=0.0):
                                parsed = _parse_numeric(_get_value(row, col_name))
                                return default if parsed is None else float(parsed)

                        def _get_text(row, col_name):
                            v = _get_value(row, col_name)
                            if v is None:
                                return ""
                            return str(v).strip().lower()

                        def _normalize_returned(value: str) -> str:
                            v = (value or "").strip().lower()
                            if not v:
                                return "none"
                            if "fully" in v:
                                return "full"
                            if "partial" in v:
                                return "partial"
                            return "none"

                        def _row_match_points(row) -> float:
                            points = 0.0

                            # Autonomous scoring
                            leave = _parse_bool(_get_value(row, "Left Launch Line (LEAVE)"))
                            if leave:
                                points += float(auto_points.get("leave", 0))

                            auto_classified = _get_num(row, "Artifacts Scored (CLASSIFIED) (Auto)")
                            auto_overflow = _get_num(row, "Artifacts Scored (OVERFLOW) (Auto)")
                            auto_depot = _get_num(row, "Artifacts Placed in Depot (Auto)")
                            auto_pattern = _get_num(row, "Pattern Matches at End of Auto (0-9)")
                            points += auto_classified * float(auto_points.get("artifact", 0))
                            points += auto_overflow * float(auto_points.get("overflow", 0))
                            points += auto_depot * float(auto_points.get("depot", 0))
                            points += auto_pattern * float(auto_points.get("pattern_match", 0))

                            # Teleop scoring
                            teleop_classified = _get_num(row, "Artifacts Scored (CLASSIFIED) (Teleop)")
                            teleop_overflow = _get_num(row, "Artifacts Scored (OVERFLOW) (Teleop)")
                            teleop_depot = _get_num(row, "Artifacts Placed in Depot (Teleop)")
                            teleop_pattern = _get_num(row, "Pattern Matches at End of Match (0-9)")
                            points += teleop_classified * float(teleop_points.get("artifact", 0))
                            points += teleop_overflow * float(teleop_points.get("overflow", 0))
                            points += teleop_depot * float(teleop_points.get("depot", 0))
                            points += teleop_pattern * float(teleop_points.get("pattern_match", 0))

                            # Endgame scoring (per-robot)
                            returned_val = _get_text(row, "Returned to Base")
                            return_key = _normalize_returned(returned_val)
                            if return_key == "partial":
                                points += float(endgame_points.get("park_partial", 0))
                            elif return_key == "full":
                                points += float(endgame_points.get("park_full", 0))

                            return points

                        values_by_match = defaultdict(list)
                        for row in team_rows:
                            if match_idx >= len(row):
                                continue
                            match_value = _parse_numeric(row[match_idx])
                            if match_value is None:
                                continue
                            match_number = int(match_value)

                            points = _row_match_points(row)
                            values_by_match[match_number].append(points)

                        data_points = []
                        for m in sorted(values_by_match.keys()):
                            vals = values_by_match[m]
                            if not vals:
                                continue
                            data_points.append((m, sum(vals) / len(vals)))

                        if not data_points:
                            st.info("No match performance data available for this team.")
                        else:
                            matches, overall_avgs = zip(*data_points)
                            trend_fig = go.Figure(
                                data=[
                                    go.Scatter(
                                        x=list(matches),
                                        y=list(overall_avgs),
                                        mode='lines+markers',
                                        line=dict(color='#a855f7', width=3),
                                        marker=dict(size=8)
                                    )
                                ]
                            )
                            trend_fig.update_layout(
                                title=f'Team {selected_team_num} - Match Points by Match',
                                xaxis_title='Match Number',
                                yaxis_title='Match Points',
                                plot_bgcolor='rgba(0,0,0,0)',
                                paper_bgcolor='rgba(0,0,0,0)',
                                font=dict(color='#f8fafc'),
                                xaxis=dict(color='#d1d5db', gridcolor='rgba(255,255,255,0.05)'),
                                yaxis=dict(
                                    color='#d1d5db',
                                    gridcolor='rgba(255,255,255,0.05)',
                                    rangemode='tozero',
                                    tickformat='.2f'
                                )
                            )
                            st.plotly_chart(trend_fig, use_container_width=True)
        
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
            if st.session_state.toa_manager:
                for row in alliance_table_data:
                    for col in ['Captain', 'Pick 1', 'Recommendation 1']:
                        if row[col]:
                            num = row[col]
                            name = st.session_state.toa_manager.get_team_nickname(num)
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
                    
                    if st.session_state.toa_manager:
                        captain_options = {team.team: f"{team.team} - {team.name}" for team in available_captains}
                        captain_options[0] = "Auto"
                        
                        # Ensure current captain is in the list
                        if a.captain and a.captain not in captain_options:
                            captain_options[a.captain] = f"{a.captain} - {st.session_state.toa_manager.get_team_nickname(a.captain)}"

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
                    
                    if st.session_state.toa_manager:
                        team_options = {team.team: f"{team.team} - {team.name}" for team in available_teams}
                        team_options[0] = "None"
                        
                        # Add current picks if they are not in the available list (e.g. captain of another alliance)
                        if a.pick1 and a.pick1 not in team_options:
                            team_options[a.pick1] = f"{a.pick1} - {st.session_state.toa_manager.get_team_nickname(a.pick1)}"
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
                    
                    # Calculate scores based on actual performance
                    overall_avg = stat.get('overall_avg', 0.0)
                    robot_valuation = stat.get('RobotValuation', 0.0)
                    
                    # Auto: Fraction of overall (0.8), capped at 100
                    auto_score = min(100.0, overall_avg * 0.8)
                    
                    # Teleop: Overall average, capped at 100
                    teleop_score = min(100.0, overall_avg)
                    
                    # Endgame: Robot valuation * 0.9, capped at 100
                    endgame_score = min(100.0, robot_valuation * 0.9)
                    
                    st.session_state.school_system.update_autonomous_score(team_num, auto_score)
                    st.session_state.school_system.update_teleop_score(team_num, teleop_score)
                    st.session_state.school_system.update_endgame_score(team_num, endgame_score)
                
                st.success(f"Added {len(stats)} teams to Honor Roll System!")
            else:
                st.warning("No team data available")
        
        # Export to TierList button
        if st.session_state.school_system.teams:
            st.markdown("---")
            st.markdown("**📥 Export Options**")
            
            # Generate TierList plain text file with custom format
            def generate_tierlist_txt(images_folder=None):
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
                2. Defense Pick: ANY team with defense_rate > 0, sorted by defense_rate (desc) then died_rate (asc)
                3. Qualified teams (non-defensive) are sorted by final_points (includes weight adjustments)
                4. 1st/2nd Pick: Qualified non-defensive teams split into halves
                5. "-" Tier: ONLY disqualified teams (those below min_honor_roll_score or lacking competencies)
                6. Unassigned: Empty (all qualified teams are assigned to top tiers)
                
                Data Source: Uses real-time data from school_system.calculated_scores
                """
                # Get current configuration values from school_system (reflects UI settings)
                current_min_score = st.session_state.school_system.min_honor_roll_score
                current_min_comp = st.session_state.school_system.min_competencies_count
                current_min_subcomp = st.session_state.school_system.min_subcompetencies_count
                
                # Build a lookup for team stats from analizador (for defense info and additional stats)
                team_stats_lookup = {}
                if hasattr(st.session_state, 'analizador') and st.session_state.analizador:
                    all_team_stats = st.session_state.analizador.get_detailed_team_stats()
                    for stat in all_team_stats:
                        team_num = str(stat.get("team", ""))
                        team_stats_lookup[team_num] = stat
                
                # ===============================================================
                # STEP 1: Identify Defensive Teams (ANY team with defense > 0)
                # ===============================================================
                all_teams_in_system = list(st.session_state.school_system.teams.keys())
                defensive_teams_data = []
                remaining_teams_nums = []

                for team_num in all_teams_in_system:
                    stat = team_stats_lookup.get(str(team_num), {})
                    # Use a more robust check for defense rate across possible keys
                    defense_rate = stat.get("teleop_crossed_played_defense_rate", stat.get("defense_rate", 0.0))
                    
                    if defense_rate > 0:
                        died_rate = stat.get("died_rate", 1.0) # Default to 1.0 (bad) if not found
                        result = st.session_state.school_system.calculated_scores.get(str(team_num))
                        defensive_teams_data.append({'team_num': team_num, 'result': result, 'defense_rate': defense_rate, 'died_rate': died_rate})
                    else:
                        remaining_teams_nums.append(team_num)

                # Sort the defensive teams by the new criteria: defense_rate (desc), died_rate (asc)
                defensive_teams_data.sort(key=lambda x: (x['defense_rate'], -x['died_rate']), reverse=True)
                
                # ===============================================================
                # STEP 2: Process Remaining Teams (Qualified vs Disqualified)
                # ===============================================================
                # Get rankings and disqualified teams (these respect the current configuration)
                rankings = st.session_state.school_system.get_honor_roll_ranking()
                disqualified = st.session_state.school_system.get_disqualified_teams()
                
                # Filter rankings and disqualified lists to only include teams from `remaining_teams_nums`
                qualified_non_defensive = [(team_num, result) for team_num, result in rankings if str(team_num) in remaining_teams_nums]
                disqualified_non_defensive = [(team_num, reason) for team_num, reason in disqualified if str(team_num) in remaining_teams_nums]
                
                # ===============================================================
                # STEP 3: Distribute QUALIFIED non-defensive teams into 1st/2nd Pick
                # These are already sorted by final_points (descending) from get_honor_roll_ranking
                # ===============================================================
                total_qualified_non_def = len(qualified_non_defensive)
                
                if total_qualified_non_def > 0:
                    # FTC 2-robot alliances: only one pick, so split into two tiers.
                    tier_size = max(1, total_qualified_non_def // 2)
                    remainder = total_qualified_non_def % 2

                    tier_1_size = tier_size + (1 if remainder >= 1 else 0)
                    tier_1 = qualified_non_defensive[:tier_1_size]
                    tier_2 = qualified_non_defensive[tier_1_size:]
                else:
                    tier_1, tier_2 = [], []
                
                # ===============================================================
                # STEP 4: DISQUALIFIED teams go to "-" tier (did not meet threshold)
                # ===============================================================
                disqualified_teams_list = []
                for team_num, reason in disqualified_non_defensive:
                    result = st.session_state.school_system.calculated_scores.get(str(team_num))
                    disqualified_teams_list.append((team_num, result, reason))
                
                # Helper function to get team stats for the Text JSON field
                # Uses REAL-TIME data from school_system.calculated_scores
                def get_team_stats_json(team_num, result):
                    # Get the calculated scores from school_system (real-time data)
                    calculated = st.session_state.school_system.calculated_scores.get(str(team_num))
                    team_scores = st.session_state.school_system.teams.get(str(team_num))
                    
                    # Get additional stats from analizador if available
                    stat = team_stats_lookup.get(str(team_num), {})
                    overall_avg = stat.get("overall_avg", 0.0)
                    
                    # Correct data retrieval for key stats
                    robot_valuation = stat.get("RobotValuation", 0.0)
                    # Try multiple keys for defense rate to be safe
                    defense_rate = stat.get("teleop_crossed_field_defense_rate", 0.0) or \
                                   stat.get("teleop_crossed_played_defense_rate", 0.0) or \
                                   stat.get("defense_rate", 0.0)
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
                        "overall_avg": round(overall_avg, 1),
                        "robot_valuation": round(robot_valuation, 1),
                        "defense_rate": round(defense_rate, 2),
                        "died_rate": round(died_rate, 2),
                        "matches_played": matches_played
                    }
                    
                    # Add descriptive competency lists instead of counts
                    if team_scores:
                        # Get labels
                        comp_labels = TeamScoring.get_competency_labels()
                        subcomp_labels = TeamScoring.get_subcompetency_labels()
                        
                        met_competencies = []
                        for key, label in comp_labels.items():
                            if getattr(team_scores.competencies, key, False):
                                met_competencies.append(label)
                                
                        met_subcompetencies = []
                        for key, label in subcomp_labels.items():
                            if getattr(team_scores.competencies, key, False):
                                met_subcompetencies.append(label)
                                
                        stats_dict["met_competencies"] = met_competencies
                        stats_dict["met_subcompetencies"] = met_subcompetencies
                    
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
                    # Define the path to the folder where team images might be stored
                    # Use provided images_folder or default to 'images'
                    images_folder_path = images_folder if images_folder else "images"
                    
                    # Call the function to get a dynamic image
                    team_image_base64 = load_team_image(team_num, images_folder=images_folder_path)
                    
                    stats_json = get_team_stats_json(team_num, result)
                    driver_skills = "Defensive" if is_defensive else "Offensive"
                    
                    # Get team name if available
                    team_name = ""
                    if st.session_state.toa_manager:
                        team_name = st.session_state.toa_manager.get_team_nickname(str(team_num))
                    
                    # Format title with number and name
                    if team_name:
                        title_str = f"{team_num} - {team_name}"
                    else:
                        title_str = f"Team {team_num}"
                    
                    lines = []
                    lines.append(f"  Image: {team_image_base64}")
                    lines.append(f"    Title: {title_str}")
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
                for team_data in defensive_teams_data:
                    output_lines.append(generate_team_block(team_data['team_num'], team_data['result'], is_defensive=True))
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
            
            # NEW: Add a text input for the image folder path
            image_folder_path = st.text_input(
                "Local Image Folder Path (Optional)",
                help="Paste the absolute path to the folder containing team images (e.g., C:/Users/YourUser/Documents/FRC/TeamImages). If left empty, default images will be generated."
            )
            
            tierlist_txt = generate_tierlist_txt(images_folder=image_folder_path)
            
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
            team_name = st.session_state.toa_manager.get_team_nickname(team_num) if st.session_state.toa_manager else None
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
            default_red = [label for label, _ in team_options[:2]]
            default_blue = [label for label, _ in team_options[2:4]] if len(team_options) >= 4 else [label for label, _ in team_options[:2]]

            with st.form("foreshadowing_form"):
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

                    st.markdown("#### Artifact Contribution")
                    st.dataframe(coral_df, use_container_width=True)
                    st.markdown("#### Endgame Summary")
                    st.dataframe(algae_df, use_container_width=True)
                    st.markdown("#### Endgame Returns")
                    st.dataframe(climb_df, use_container_width=True)

                    st.markdown("#### Additional Metrics")
                    st.write(
                        f"Auto Leave: {red_breakdown['teams_left_auto_zone']}/2 | "
                        f"Double Park Bonus: {'✅' if red_breakdown.get('double_park_bonus', 0) else '❌'}"
                    )

                with breakdown_tabs[1]:
                    blue_breakdown = prediction.blue_breakdown
                    coral_df = build_coral_breakdown_df(blue_breakdown)
                    algae_df = build_algae_summary_df(blue_breakdown)
                    climb_df = build_climb_breakdown_df(blue_breakdown)

                    st.markdown("#### Artifact Contribution")
                    st.dataframe(coral_df, use_container_width=True)
                    st.markdown("#### Endgame Summary")
                    st.dataframe(algae_df, use_container_width=True)
                    st.markdown("#### Endgame Returns")
                    st.dataframe(climb_df, use_container_width=True)

                    st.markdown("#### Additional Metrics")
                    st.write(
                        f"Auto Leave: {blue_breakdown['teams_left_auto_zone']}/2 | "
                        f"Double Park Bonus: {'✅' if blue_breakdown.get('double_park_bonus', 0) else '❌'}"
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
                        'Component': 'Auto',
                        'Points': prediction.red_breakdown['auto_points']
                    },
                    {
                        'Alliance': 'Red',
                        'Component': 'Teleop',
                        'Points': prediction.red_breakdown['teleop_points']
                    },
                    {
                        'Alliance': 'Red',
                        'Component': 'Endgame',
                        'Points': prediction.red_breakdown['endgame_points']
                    },
                    {
                        'Alliance': 'Blue',
                        'Component': 'Auto',
                        'Points': prediction.blue_breakdown['auto_points']
                    },
                    {
                        'Alliance': 'Blue',
                        'Component': 'Teleop',
                        'Points': prediction.blue_breakdown['teleop_points']
                    },
                    {
                        'Alliance': 'Blue',
                        'Component': 'Endgame',
                        'Points': prediction.blue_breakdown['endgame_points']
                    }
                ]
                score_df = pd.DataFrame(score_components)
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

                red_teleop_total = sum(prediction.red_breakdown['teleop_artifacts'].values())
                blue_teleop_total = sum(prediction.blue_breakdown['teleop_artifacts'].values())

                if red_teleop_total > blue_teleop_total * 1.2:
                    st.write("Red shows a strong teleop artifact advantage. Blue should focus on defense or endgame points.")
                elif blue_teleop_total > red_teleop_total * 1.2:
                    st.write("Blue shows a strong teleop artifact advantage. Red should prioritize efficient cycles.")
                else:
                    st.write("Teleop artifacts are balanced. Endgame could decide the match.")

                st.caption("Foreshadowing simulations use historical averages and random sampling for variability.")

elif page == "⚙️ TOA Settings":
    st.markdown("<div class='main-header'>⚙️ The Orange Alliance Settings</div>", unsafe_allow_html=True)

    use_api = st.toggle(
        "Use The Orange Alliance API (requires internet)",
        key="toa_use_api"
    )

    if use_api:
        st.markdown("""
        <div class='stats-card'>
        <p>To fetch the latest FTC event/team data, provide your <strong>The Orange Alliance (TOA) credentials</strong>:</p>
        <ul>
            <li><code>X-TOA-Key</code> (API key)</li>
            <li><code>X-Application-Origin</code> (any identifier for your app)</li>
        </ul>
        </div>
        """, unsafe_allow_html=True)

        st.session_state.toa_api_key = st.text_input(
            "TOA Key (X-TOA-Key)",
            value=st.session_state.toa_api_key,
            type="password"
        )
        st.session_state.toa_application_origin = st.text_input(
            "Application Origin (X-Application-Origin)",
            value=st.session_state.toa_application_origin,
            placeholder="Overture_Analizador_FTC"
        )
    else:
        st.info(
            "Offline mode active: the app will only use cached JSON files (e.g., `toa_events_<season_key>.json`, "
            "`teams_<event_key>.json`) located next to the application."
        )

    if st.button("Initialize TOA Manager"):
        api_key = st.session_state.toa_api_key.strip() or None
        application_origin = st.session_state.toa_application_origin.strip() or None
        try:
            st.session_state.toa_manager = TOAManager(
                api_key=api_key,
                application_origin=application_origin,
                use_api=use_api
            )
            st.success("TOA Manager initialized successfully!")
        except ValueError as e:
            st.error(str(e))

    if st.session_state.toa_manager:
        st.session_state.toa_manager.api_key = st.session_state.toa_api_key.strip() or st.session_state.toa_manager.api_key
        if st.session_state.toa_application_origin.strip():
            st.session_state.toa_manager.application_origin = st.session_state.toa_application_origin.strip()
        try:
            st.session_state.toa_manager.set_api_usage(use_api)
        except ValueError:
            st.warning("API access could not be enabled because no key is configured. Staying in offline mode.")
            st.session_state.toa_use_api = False
            use_api = False

    if st.session_state.toa_manager:
        st.markdown("---")
        st.markdown("### Event Selection")

        season_key = st.number_input(
            "Select TOA Season Key (example: 2425)",
            min_value=0,
            max_value=9999,
            value=2425
        )

        if st.button("Fetch Events for Season"):
            events = st.session_state.toa_manager.get_events_by_season(season_key)
            if events:
                st.session_state.events_list = sorted(events, key=lambda x: x.get('name', ''))
                st.success(f"Found {len(events)} events for season {int(season_key)}.")
            else:
                st.session_state.events_list = []
                if use_api:
                    last_error = getattr(st.session_state.toa_manager, "last_error", None)
                    if isinstance(last_error, dict):
                        status = last_error.get("status")
                        message = last_error.get("message")
                        err_type = last_error.get("type")
                        preview = last_error.get("preview")

                        details = []
                        if status is not None:
                            details.append(f"HTTP {status}")
                        if message:
                            details.append(str(message))
                        if err_type == "non_json" and preview:
                            details.append(f"Non-JSON response preview: {preview}")

                        suffix = " - ".join(details)
                        st.error(
                            "Could not fetch events. Check your API key/internet."
                            + (f" ({suffix})" if suffix else "")
                        )
                    else:
                        st.error("Could not fetch events. Check your API key and internet connection.")
                else:
                    st.warning(
                        f"No cached events found for {int(season_key)}. Add a `toa_events_{int(season_key)}.json` file "
                        "to the app directory or enable API access."
                    )

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
                    loaded = st.session_state.toa_manager.load_teams_from_file(selected_key)
                    if loaded:
                        st.session_state.toa_event_key = selected_key
                        st.session_state.selected_event_name = event_options[selected_key]
                        st.success(f"Loaded {len(loaded)} teams from local cache for {st.session_state.selected_event_name}.")
                    else:
                        # If not found locally, fetch from API
                        teams_data = st.session_state.toa_manager.get_teams_for_event(selected_key)
                        if teams_data:
                            st.session_state.toa_manager.save_teams_to_file(selected_key, teams_data)
                            loaded = st.session_state.toa_manager.load_teams_from_file(selected_key)  # Load into memory
                            st.session_state.toa_event_key = selected_key
                            st.session_state.selected_event_name = event_options[selected_key]
                            st.success(f"Fetched and saved {len(teams_data)} teams for {st.session_state.selected_event_name}.")
                        else:
                            if use_api:
                                st.error("Failed to fetch team data from TOA API.")
                            else:
                                st.warning(
                                    f"No cached team data available for that event. Place a `teams_{selected_key}.json` "
                                    "file in the app directory or enable API access."
                                )

    st.markdown("---")
    st.markdown("### Current Status")
    if st.session_state.toa_manager and st.session_state.toa_event_key:
        st.success(
            f"TOA Manager is active. Loaded data for event: **{st.session_state.selected_event_name}** "
            f"(`{st.session_state.toa_event_key}`)"
        )
    else:
        st.warning("TOA Manager is not active or no event data is loaded. Team names will not be displayed.")

# Footer - appears on all pages
st.markdown("<hr style='margin-top: 3rem; border: 1px solid #e2e8f0;'>", unsafe_allow_html=True)
st.markdown(
    "<div class='footer'>Developed by Team Overture 7421</div>",
    unsafe_allow_html=True
)
