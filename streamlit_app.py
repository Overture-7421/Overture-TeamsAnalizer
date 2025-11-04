"""
Streamlit Web Application for Alliance Simulator
Provides a web-based interface for all the core functionality of the desktop application
"""

import streamlit as st
import pandas as pd
import io
import base64
import sys
import os

# Avoid tkinter import issues in main.py by making it optional
try:
    from main import AnalizadorRobot
except ImportError as e:
    # If tkinter is not available, mock it for the import
    if 'tkinter' in str(e):
        import types
        sys.modules['tkinter'] = types.ModuleType('tkinter')
        sys.modules['tkinter.ttk'] = types.ModuleType('ttk')
        sys.modules['tkinter'].filedialog = types.ModuleType('filedialog')
        sys.modules['tkinter'].messagebox = types.ModuleType('messagebox')
        sys.modules['tkinter'].simpledialog = types.ModuleType('simpledialog')
        # Also need to mock matplotlib backend
        sys.modules['matplotlib.backends.backend_tkagg'] = types.ModuleType('backend_tkagg')
        sys.modules['matplotlib.backends.backend_tkagg'].FigureCanvasTkAgg = object
        from main import AnalizadorRobot
    else:
        raise

from allianceSelector import AllianceSelector, Team, teams_from_dicts
from school_system import TeamScoring, BehaviorReportType
from firebase_integration import FirebaseManager, FIREBASE_AVAILABLE
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go

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
if 'firebase_manager' not in st.session_state:
    st.session_state.firebase_manager = None
if 'firebase_connected' not in st.session_state:
    st.session_state.firebase_connected = False
if 'team_name_mapping' not in st.session_state:
    st.session_state.team_name_mapping = {}
if 'selected_base' not in st.session_state:
    st.session_state.selected_base = None
if 'available_bases' not in st.session_state:
    st.session_state.available_bases = []

# Enhanced Custom CSS for Dark Theme
st.markdown("""
<style>
    /* Import Google Fonts */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    /* Global Styles */
    * {
        font-family: 'Inter', sans-serif;
    }
    
    /* Main container - Dark background */
    .main {
        background: #000000;
        background-attachment: fixed;
    }
    
    /* Content area - Dark with subtle gradient */
    .block-container {
        padding: 2rem 3rem;
        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a1a 100%);
        border-radius: 20px;
        box-shadow: 0 8px 32px rgba(102, 126, 234, 0.2);
        backdrop-filter: blur(10px);
        margin: 1rem;
        border: 1px solid rgba(102, 126, 234, 0.1);
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
        text-shadow: 2px 2px 4px rgba(102, 126, 234, 0.3);
    }
    
    .sub-header {
        font-size: 1.8rem;
        font-weight: 600;
        color: #667eea;
        margin-top: 2rem;
        margin-bottom: 1rem;
        border-left: 4px solid #667eea;
        padding-left: 1rem;
    }
    
    /* Override Streamlit default text colors */
    h1, h2, h3, h4, h5, h6, p, span, div, label {
        color: #ffffff !important;
    }
    
    /* Metric cards - Dark theme */
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 700;
        color: #667eea !important;
    }
    
    div[data-testid="stMetricLabel"] {
        font-weight: 600;
        color: #cccccc !important;
    }
    
    .metric-card {
        background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        margin: 0.5rem 0;
        border: 1px solid rgba(102, 126, 234, 0.2);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 12px rgba(102, 126, 234, 0.3);
        border-color: rgba(102, 126, 234, 0.4);
    }
    
    /* Buttons */
    .stButton>button {
        width: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        border: none;
        border-radius: 8px;
        padding: 0.6rem 1.2rem;
        font-weight: 600;
        transition: all 0.3s ease;
        box-shadow: 0 4px 6px rgba(102, 126, 234, 0.3);
    }
    
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(102, 126, 234, 0.5);
    }
    
    /* Sidebar - Dark gradient */
    section[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0a0a0a 0%, #1a1a1a 100%);
        border-right: 1px solid rgba(102, 126, 234, 0.2);
    }
    
    section[data-testid="stSidebar"] * {
        color: white !important;
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
        background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%);
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
        border: 1px solid rgba(102, 126, 234, 0.2);
        color: #cccccc !important;
    }
    
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white !important;
        border-color: rgba(102, 126, 234, 0.5);
    }
    
    /* DataFrames - Dark theme */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        background-color: #1a1a1a !important;
    }
    
    .dataframe thead tr th {
        background-color: #2a2a2a !important;
        color: #667eea !important;
        border-color: rgba(102, 126, 234, 0.2) !important;
    }
    
    .dataframe tbody tr {
        background-color: #1a1a1a !important;
        color: #ffffff !important;
    }
    
    .dataframe tbody tr:hover {
        background-color: #2a2a2a !important;
    }
    
    .dataframe td, .dataframe th {
        border-color: rgba(102, 126, 234, 0.1) !important;
    }
    
    /* Info/Warning/Success boxes */
    .stAlert {
        border-radius: 8px;
        border-left: 4px solid;
        background-color: #1a1a1a !important;
        color: #ffffff !important;
    }
    
    /* File uploader */
    .uploadedFile {
        border-radius: 8px;
        border: 2px dashed #667eea;
        background-color: #1a1a1a !important;
    }
    
    /* Input fields */
    .stTextInput>div>div>input,
    .stNumberInput>div>div>input,
    .stSelectbox>div>div>div,
    .stTextArea>div>div>textarea {
        background-color: #2a2a2a !important;
        color: #ffffff !important;
        border-color: rgba(102, 126, 234, 0.3) !important;
    }
    
    /* Plotly charts - Dark background */
    .js-plotly-plot {
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.3);
        background-color: #1a1a1a !important;
    }
    
    /* Team badge */
    .team-badge {
        display: inline-block;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 0.3rem 0.8rem;
        border-radius: 20px;
        font-weight: 600;
        font-size: 0.9rem;
        margin: 0.2rem;
    }
    
    /* Stats card - Dark theme */
    .stats-card {
        background: linear-gradient(135deg, #1a1a1a 0%, #2a2a2a 100%);
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4);
        margin: 1rem 0;
        border-left: 4px solid #667eea;
        border: 1px solid rgba(102, 126, 234, 0.2);
    }
    
    /* Footer */
    .footer {
        text-align: center;
        padding: 2rem;
        color: #999999;
        font-size: 0.9rem;
        margin-top: 3rem;
    }
    
    /* Expander */
    .streamlit-expanderHeader {
        background-color: #1a1a1a !important;
        color: #ffffff !important;
        border: 1px solid rgba(102, 126, 234, 0.2) !important;
    }
    
    .streamlit-expanderContent {
        background-color: #0a0a0a !important;
        border: 1px solid rgba(102, 126, 234, 0.1) !important;
    }
</style>
""", unsafe_allow_html=True)

# Helper functions
def load_csv_data(uploaded_file):
    """Load CSV data into the analyzer"""
    try:
        # Save uploaded file temporarily
        with open("temp_upload.csv", "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Load into analyzer
        st.session_state.analizador.load_csv("temp_upload.csv")
        
        return True, "CSV loaded successfully!"
    except Exception as e:
        return False, f"Error loading CSV: {str(e)}"

def initialize_firebase(credentials_file):
    """Initialize Firebase connection with uploaded credentials"""
    try:
        # Save credentials temporarily
        credentials_path = "temp_firebase_credentials.json"
        with open(credentials_path, "wb") as f:
            f.write(credentials_file.getbuffer())
        
        # Initialize Firebase
        firebase_manager = FirebaseManager(credentials_path)
        
        if firebase_manager.is_connected():
            st.session_state.firebase_manager = firebase_manager
            st.session_state.firebase_connected = True
            return True, "Firebase connected successfully!"
        else:
            return False, "Failed to connect to Firebase. Check your credentials."
            
    except Exception as e:
        return False, f"Error initializing Firebase: {str(e)}"

def load_firebase_data(collection_name='scouting_data'):
    """Load data from Firebase and convert to CSV format"""
    try:
        if not st.session_state.firebase_connected:
            return False, "Firebase not connected"
        
        firebase_manager = st.session_state.firebase_manager
        data = firebase_manager.get_all_scouting_data(collection_name)
        
        if not data:
            return False, "No data found in Firebase"
        
        # Convert to DataFrame
        df = pd.DataFrame(data)
        
        # Save as temporary CSV
        csv_path = "temp_firebase_data.csv"
        df.to_csv(csv_path, index=False)
        
        # Load into analyzer
        st.session_state.analizador.load_csv(csv_path)
        
        return True, f"Loaded {len(data)} records from Firebase!"
        
    except Exception as e:
        return False, f"Error loading Firebase data: {str(e)}"

def upload_to_firebase(collection_name='scouting_data'):
    """Upload current data to Firebase"""
    try:
        if not st.session_state.firebase_connected:
            return False, "Firebase not connected"
        
        firebase_manager = st.session_state.firebase_manager
        raw_data = st.session_state.analizador.get_raw_data()
        
        if not raw_data or len(raw_data) <= 1:
            return False, "No data to upload"
        
        # Convert to list of dictionaries
        headers = raw_data[0]
        data_rows = raw_data[1:]
        data = [dict(zip(headers, row)) for row in data_rows]
        
        # Upload to Firebase
        success = firebase_manager.upload_scouting_data(data, collection_name)
        
        if success:
            return True, f"Uploaded {len(data)} records to Firebase!"
        else:
            return False, "Failed to upload data to Firebase"
            
    except Exception as e:
        return False, f"Error uploading to Firebase: {str(e)}"

def load_available_bases():
    """Load available Firebase collections (bases)"""
    try:
        if not st.session_state.firebase_connected:
            return False, "Firebase not connected"
        
        firebase_manager = st.session_state.firebase_manager
        collections = firebase_manager.list_collections()
        
        if collections:
            st.session_state.available_bases = collections
            return True, f"Found {len(collections)} bases: {', '.join(collections)}"
        else:
            return False, "No collections found in Firebase"
    except Exception as e:
        return False, f"Error loading bases: {str(e)}"

def load_equipos_frc():
    """Load team name mapping from EquiposFRC base"""
    try:
        if not st.session_state.firebase_connected:
            return False, "Firebase not connected", {}
        
        firebase_manager = st.session_state.firebase_manager
        team_mapping = firebase_manager.get_equipos_frc_mapping()
        
        if team_mapping:
            st.session_state.team_name_mapping = team_mapping
            return True, f"Loaded {len(team_mapping)} team names", team_mapping
        else:
            return False, "No team names found in EquiposFRC", {}
    except Exception as e:
        return False, f"Error loading EquiposFRC: {str(e)}", {}

def load_offseason_allstar():
    """Load match data from OffSeasonAllStar base"""
    try:
        if not st.session_state.firebase_connected:
            return False, "Firebase not connected"
        
        firebase_manager = st.session_state.firebase_manager
        
        # Get expected column headers from the analyzer
        column_headers = st.session_state.analizador.default_column_names
        
        # Load data from OffSeasonAllStar
        rows, metadata = firebase_manager.load_offseason_allstar_data(column_headers)
        
        if "error" in metadata:
            return False, f"Error: {metadata['error']}"
        
        if not rows:
            return False, "No match data found in OffSeasonAllStar"
        
        # Create temporary CSV file
        import csv
        csv_path = "temp_offseason_data.csv"
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(column_headers)
            writer.writerows(rows)
        
        # Load into analyzer
        st.session_state.analizador.load_csv(csv_path)
        
        # Build summary message
        summary = f"Loaded {metadata['matches_loaded']} matches from {metadata['teams_loaded']} teams"
        
        if metadata.get('warnings'):
            summary += f"\n\nWarnings:\n" + "\n".join(f"- {w}" for w in metadata['warnings'])
        
        if metadata.get('missing_fields'):
            summary += f"\n\nDefaulted fields:\n" + "\n".join(
                f"- {field}: {count} instances" 
                for field, count in sorted(metadata['missing_fields'].items(), key=lambda x: -x[1])[:5]
            )
        
        return True, summary
    except Exception as e:
        import traceback
        traceback.print_exc()
        return False, f"Error loading OffSeasonAllStar: {str(e)}"

def get_team_name(team_number):
    """Get team name from mapping, with fallback to team number"""
    team_num_str = str(team_number)
    if team_num_str in st.session_state.team_name_mapping:
        name = st.session_state.team_name_mapping[team_num_str]
        return f"{name} ({team_num_str})"
    return f"Team {team_num_str}"

def get_team_stats_dataframe():
    """Get team statistics as a pandas DataFrame"""
    stats = st.session_state.analizador.get_detailed_team_stats()
    if not stats:
        return None
    
    # Convert to DataFrame with selected columns for simplified view
    df_data = []
    for team_stat in stats:
        team_number = team_stat.get('team', 'N/A')
        df_data.append({
            'Team': get_team_name(team_number),
            'Overall Avg': round(team_stat.get('overall_avg', 0.0), 2),
            'Overall Std': round(team_stat.get('overall_std', 0.0), 2),
            'Robot Valuation': round(team_stat.get('RobotValuation', 0.0), 2),
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
        
        teams.append(Team(
            num=team_num,
            rank=rank,
            total_epa=overall_avg,
            auto_epa=phase_scores.get('autonomous', 0),
            teleop_epa=phase_scores.get('teleop', 0),
            endgame_epa=phase_scores.get('endgame', 0),
            defense=False,  # Can be enhanced
            name=f"Team {team_num}",
            robot_valuation=robot_val,
            consistency_score=100 - stat.get('overall_std', 20),
            clutch_factor=75  # Default value
        ))
    
    return teams

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
     "🤝 Alliance Selector", "🏆 Honor Roll System", "🔮 Foreshadowing"],
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
    
    # Quick overview chart with enhanced styling
    if stats:
        st.markdown("<div class='sub-header'>🏆 Top 10 Teams by Overall Performance</div>", unsafe_allow_html=True)
        
        top_10 = stats[:10]
        teams_list = [str(s.get('team', 'N/A')) for s in top_10]
        overall_list = [s.get('overall_avg', 0) for s in top_10]
        
        fig = px.bar(
            x=teams_list,
            y=overall_list,
            labels={'x': 'Team Number', 'y': 'Overall Average'},
            title="",
            color=overall_list,
            color_continuous_scale='Purples',
            text=overall_list
        )
        fig.update_traces(texttemplate='%{text:.2f}', textposition='outside')
        fig.update_layout(
            showlegend=False,
            plot_bgcolor='#1a1a1a',
            paper_bgcolor='#1a1a1a',
            font=dict(size=12, color='#ffffff'),
            xaxis=dict(showgrid=False, color='#ffffff'),
            yaxis=dict(showgrid=True, gridcolor='rgba(102, 126, 234, 0.2)', color='#ffffff'),
            margin=dict(t=10, b=10, l=10, r=10)
        )
        st.plotly_chart(fig, use_container_width=True)
        
        # Additional insights
        st.markdown("<div class='sub-header'>💡 Quick Insights</div>", unsafe_allow_html=True)
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("<div class='stats-card'>", unsafe_allow_html=True)
            st.markdown("**🥇 Top Team**")
            if stats:
                top_team = stats[0]
                st.markdown(f"<div class='team-badge'>Team {top_team.get('team', 'N/A')}</div>", unsafe_allow_html=True)
                st.markdown(f"Score: **{top_team.get('overall_avg', 0):.2f}**")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("<div class='stats-card'>", unsafe_allow_html=True)
            st.markdown("**🎯 Most Consistent**")
            if stats:
                most_consistent = min(stats, key=lambda x: x.get('overall_std', float('inf')))
                st.markdown(f"<div class='team-badge'>Team {most_consistent.get('team', 'N/A')}</div>", unsafe_allow_html=True)
                st.markdown(f"Std Dev: **{most_consistent.get('overall_std', 0):.2f}**")
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col3:
            st.markdown("<div class='stats-card'>", unsafe_allow_html=True)
            st.markdown("**⚙️ Best Robot**")
            if stats:
                best_robot = max(stats, key=lambda x: x.get('RobotValuation', 0))
                st.markdown(f"<div class='team-badge'>Team {best_robot.get('team', 'N/A')}</div>", unsafe_allow_html=True)
                st.markdown(f"Valuation: **{best_robot.get('RobotValuation', 0):.2f}**")
            st.markdown("</div>", unsafe_allow_html=True)

elif page == "📁 Data Management":
    st.markdown("<div class='main-header'>📁 Data Management</div>", unsafe_allow_html=True)
    
    # Firebase status indicator
    if FIREBASE_AVAILABLE:
        if st.session_state.firebase_connected:
            st.success("🔥 Firebase Connected")
        else:
            st.info("🔥 Firebase Available - Connect to enable cloud features")
    else:
        st.warning("⚠️ Firebase SDK not installed. Install with: pip install firebase-admin google-cloud-firestore")
    
    tab1, tab2, tab3, tab4 = st.tabs(["📤 Upload Data", "🔥 Firebase", "📋 View Raw Data", "💾 Export Data"])
    
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
        st.markdown("### 🔥 Firebase Cloud Database")
        
        if not FIREBASE_AVAILABLE:
            st.error("Firebase SDK not installed. Please install required packages:")
            st.code("pip install firebase-admin google-cloud-firestore", language="bash")
        else:
            col1, col2 = st.columns([2, 1])
            
            with col1:
                st.markdown("#### Firebase Configuration")
                
                if not st.session_state.firebase_connected:
                    st.markdown("""
                    **Setup Instructions:**
                    1. Go to [Firebase Console](https://console.firebase.google.com/)
                    2. Select your project or create a new one
                    3. Go to Project Settings → Service Accounts
                    4. Click "Generate new private key"
                    5. Upload the JSON file below
                    """)
                    
                    credentials_file = st.file_uploader(
                        "Upload Firebase Credentials (JSON)", 
                        type=['json'],
                        key="firebase_credentials"
                    )
                    
                    if credentials_file is not None:
                        if st.button("🔗 Connect to Firebase"):
                            success, message = initialize_firebase(credentials_file)
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                else:
                    st.success("✅ Firebase Connected!")
                    
                    if st.button("🔌 Disconnect"):
                        st.session_state.firebase_connected = False
                        st.session_state.firebase_manager = None
                        st.rerun()
            
            with col2:
                st.markdown("#### Quick Actions")
                
                if st.session_state.firebase_connected:
                    st.markdown("**Status:** Connected ✓")
                    
                    # Display connection info
                    st.markdown("**Operations:**")
                    st.markdown("- Load from cloud")
                    st.markdown("- Upload to cloud")
                    st.markdown("- Sync data")
                else:
                    st.markdown("**Status:** Not Connected")
                    st.markdown("Upload credentials to connect")
            
            if st.session_state.firebase_connected:
                st.markdown("---")
                st.markdown("#### 🗂️ Base Selector & Data Loading")
                
                # Discover available bases
                if st.button("🔍 Discover Available Bases"):
                    with st.spinner("Discovering collections..."):
                        success, message = load_available_bases()
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                
                # Show available bases
                if st.session_state.available_bases:
                    st.markdown("**Available Bases:**")
                    
                    # Default to OffSeasonAllStar if available
                    default_index = 0
                    if "OffSeasonAllStar" in st.session_state.available_bases:
                        default_index = st.session_state.available_bases.index("OffSeasonAllStar")
                    
                    selected_base = st.selectbox(
                        "Select Base to Load",
                        st.session_state.available_bases,
                        index=default_index,
                        key="base_selector"
                    )
                    st.session_state.selected_base = selected_base
                    
                    # Show info about selected base
                    if selected_base == "OffSeasonAllStar":
                        st.info("📊 **OffSeasonAllStar**: Loads match data from team Matches subcollections")
                    elif selected_base == "EquiposFRC":
                        st.info("👥 **EquiposFRC**: Loads team name mapping for enhanced rankings")
                    else:
                        st.info(f"📁 **{selected_base}**: Generic collection")
                    
                    # Load button for selected base
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        if st.button(f"📥 Load {selected_base}", use_container_width=True):
                            with st.spinner(f"Loading {selected_base} data..."):
                                if selected_base == "OffSeasonAllStar":
                                    success, message = load_offseason_allstar()
                                    if success:
                                        st.success(message)
                                        st.rerun()
                                    else:
                                        st.error(message)
                                elif selected_base == "EquiposFRC":
                                    success, message, mapping = load_equipos_frc()
                                    if success:
                                        st.success(message)
                                        # Show a sample of the mapping
                                        if mapping:
                                            sample = dict(list(mapping.items())[:5])
                                            st.write("Sample team names:", sample)
                                    else:
                                        st.error(message)
                                else:
                                    # Generic collection load
                                    success, message = load_firebase_data(selected_base)
                                    if success:
                                        st.success(message)
                                        st.rerun()
                                    else:
                                        st.error(message)
                    
                    with col2:
                        if st.button("🔄 Reload All Bases", use_container_width=True):
                            with st.spinner("Reloading..."):
                                success, message = load_available_bases()
                                if success:
                                    st.success(message)
                                    st.rerun()
                                else:
                                    st.error(message)
                
                # Show current data status
                if st.session_state.team_name_mapping:
                    st.success(f"✓ Team names loaded: {len(st.session_state.team_name_mapping)} teams")
                
                raw_data = st.session_state.analizador.get_raw_data()
                if raw_data and len(raw_data) > 1:
                    st.success(f"✓ Match data loaded: {len(raw_data) - 1} matches")
                
                st.markdown("---")
                st.markdown("#### 📥 Legacy Data Loading")
                st.markdown("*Use this for custom collections or old-format data*")
                
                collection_name_load = st.text_input(
                    "Collection Name",
                    value="scouting_data",
                    key="load_collection"
                )
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    if st.button("📥 Load All Data", use_container_width=True):
                        with st.spinner("Loading data from Firebase..."):
                            success, message = load_firebase_data(collection_name_load)
                            if success:
                                st.success(message)
                                st.rerun()
                            else:
                                st.error(message)
                
                with col2:
                    team_filter = st.number_input("Filter by Team #", min_value=0, value=0, key="team_filter")
                    if team_filter > 0:
                        if st.button("📥 Load Team Data", use_container_width=True):
                            try:
                                firebase_manager = st.session_state.firebase_manager
                                data = firebase_manager.get_scouting_data_by_team(team_filter, collection_name_load)
                                
                                if data:
                                    df = pd.DataFrame(data)
                                    csv_path = "temp_firebase_data.csv"
                                    df.to_csv(csv_path, index=False)
                                    st.session_state.analizador.load_csv(csv_path)
                                    st.success(f"Loaded {len(data)} records for team {team_filter}")
                                    st.rerun()
                                else:
                                    st.warning(f"No data found for team {team_filter}")
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                
                with col3:
                    match_filter = st.number_input("Filter by Match #", min_value=0, value=0, key="match_filter")
                    if match_filter > 0:
                        if st.button("📥 Load Match Data", use_container_width=True):
                            try:
                                firebase_manager = st.session_state.firebase_manager
                                data = firebase_manager.get_scouting_data_by_match(match_filter, collection_name_load)
                                
                                if data:
                                    df = pd.DataFrame(data)
                                    csv_path = "temp_firebase_data.csv"
                                    df.to_csv(csv_path, index=False)
                                    st.session_state.analizador.load_csv(csv_path)
                                    st.success(f"Loaded {len(data)} records for match {match_filter}")
                                    st.rerun()
                                else:
                                    st.warning(f"No data found for match {match_filter}")
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                
                st.markdown("---")
                st.markdown("#### 📤 Upload Data to Firebase")
                
                collection_name_upload = st.text_input(
                    "Collection Name",
                    value="scouting_data",
                    key="upload_collection"
                )
                
                if st.button("📤 Upload Current Data to Firebase"):
                    with st.spinner("Uploading data to Firebase..."):
                        success, message = upload_to_firebase(collection_name_upload)
                        if success:
                            st.success(message)
                        else:
                            st.error(message)
                
                st.markdown("---")
                st.markdown("#### ⚠️ Advanced Operations")
                
                with st.expander("🗑️ Clear Firebase Collection"):
                    st.warning("**Warning:** This will delete all data in the collection!")
                    clear_collection = st.text_input("Type collection name to confirm", key="clear_collection")
                    
                    if st.button("🗑️ Clear Collection"):
                        if clear_collection == collection_name_load:
                            firebase_manager = st.session_state.firebase_manager
                            if firebase_manager.clear_collection(clear_collection):
                                st.success(f"Cleared collection '{clear_collection}'")
                            else:
                                st.error("Failed to clear collection")
                        else:
                            st.error("Collection name doesn't match. Operation cancelled.")
    
    with tab3:
        st.markdown("### 📋 Raw Data View")
        raw_data = st.session_state.analizador.get_raw_data()
        
        if raw_data and len(raw_data) > 1:
            df = pd.DataFrame(raw_data[1:], columns=raw_data[0])
            st.dataframe(df, use_container_width=True, height=400)
            
            st.markdown(f"**Total Records:** {len(raw_data) - 1}")
        else:
            st.info("No data loaded yet. Please upload a CSV file, paste QR data, or load from Firebase.")
    
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
                    
                    died_rate_key = st.session_state.analizador._generate_stat_key('Died?', 'rate')
                    death_rate = team_stat.get(died_rate_key, 0.0)
                    
                    defended_key = st.session_state.analizador._generate_stat_key('Was the robot Defended by someone?', 'rate')
                    defended_rate = team_stat.get(defended_key, 0.0)
                    
                    climb_type = "Unknown"
                    if team_num in team_data_grouped:
                        team_rows = team_data_grouped[team_num]
                        end_pos_idx = st.session_state.analizador._column_indices.get('End Position')
                        if end_pos_idx is not None:
                            climb_values = [str(row[end_pos_idx]).strip() for row in team_rows if end_pos_idx < len(row)]
                            if climb_values:
                                climb_type = st.session_state.analizador._calculate_mode(climb_values)
                    
                    simplified_data.append({
                        'Rank': rank,
                        'Team': get_team_name(team_num),
                        'Overall ± Std': f"{overall_avg:.2f} ± {overall_std:.2f}",
                        'Robot Valuation': f"{robot_valuation:.2f}",
                        'Death Rate': f"{death_rate:.3f}",
                        'Climb Type': climb_type,
                        'Defended Rate': f"{defended_rate:.3f}"
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
            
            # Create a comprehensive DataFrame
            df_data = []
            for rank, team_stat in enumerate(stats, 1):
                team_number = team_stat.get('team', 'N/A')
                df_data.append({
                    'Rank': rank,
                    'Team': get_team_name(team_number),
                    'Overall Avg': round(team_stat.get('overall_avg', 0.0), 2),
                    'Overall Std': round(team_stat.get('overall_std', 0.0), 2),
                    'Robot Valuation': round(team_stat.get('RobotValuation', 0.0), 2),
                })
            
            df = pd.DataFrame(df_data)
            st.dataframe(df, use_container_width=True, height=500)
            
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
                plot_bgcolor='#1a1a1a',
                paper_bgcolor='#1a1a1a',
                font=dict(color='#ffffff'),
                xaxis=dict(gridcolor='rgba(102, 126, 234, 0.2)', color='#ffffff'),
                yaxis=dict(gridcolor='rgba(102, 126, 234, 0.2)', color='#ffffff')
            )
            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            st.markdown("### Detailed Team Statistics")
            
            # Team selector
            team_numbers = [str(s.get('team', '')) for s in stats]
            selected_team = st.selectbox("Select a team to view details", team_numbers)
            
            if selected_team:
                team_stat = next((s for s in stats if str(s.get('team', '')) == selected_team), None)
                
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
                        died_rate = team_stat.get(st.session_state.analizador._generate_stat_key('Died?', 'rate'), 0)
                        st.metric("Death Rate", f"{died_rate:.3f}")
                    
                    # Phase scores visualization
                    phase_scores = st.session_state.analizador.calculate_team_phase_scores(int(selected_team))
                    
                    fig = go.Figure(data=[
                        go.Bar(name='Phase Scores', 
                               x=['Autonomous', 'Teleop', 'Endgame'],
                               y=[phase_scores['autonomous'], phase_scores['teleop'], phase_scores['endgame']],
                               marker=dict(color='#667eea'))
                    ])
                    fig.update_layout(
                        title=f'Team {selected_team} - Phase Performance',
                        plot_bgcolor='#1a1a1a',
                        paper_bgcolor='#1a1a1a',
                        font=dict(color='#ffffff'),
                        xaxis=dict(gridcolor='rgba(102, 126, 234, 0.2)', color='#ffffff'),
                        yaxis=dict(gridcolor='rgba(102, 126, 234, 0.2)', color='#ffffff')
                    )
                    st.plotly_chart(fig, use_container_width=True)
        
        with tab3:
            st.markdown("### Simplified Ranking")
            st.markdown("*Shows: Team Number, Overall ± Std, Robot Valuation, Death Rate, Climb Type, Defended Rate*")
            
            team_data_grouped = st.session_state.analizador.get_team_data_grouped()
            
            simplified_data = []
            for rank, team_stat in enumerate(stats, 1):
                team_num = str(team_stat.get('team', 'N/A'))
                overall_avg = team_stat.get('overall_avg', 0.0)
                overall_std = team_stat.get('overall_std', 0.0)
                robot_valuation = team_stat.get('RobotValuation', 0.0)
                
                died_rate_key = st.session_state.analizador._generate_stat_key('Died?', 'rate')
                death_rate = team_stat.get(died_rate_key, 0.0)
                
                defended_key = st.session_state.analizador._generate_stat_key('Was the robot Defended by someone?', 'rate')
                defended_rate = team_stat.get(defended_key, 0.0)
                
                climb_type = "Unknown"
                if team_num in team_data_grouped:
                    team_rows = team_data_grouped[team_num]
                    end_pos_idx = st.session_state.analizador._column_indices.get('End Position')
                    if end_pos_idx is not None:
                        climb_values = [str(row[end_pos_idx]).strip() for row in team_rows if end_pos_idx < len(row)]
                        if climb_values:
                            climb_type = st.session_state.analizador._calculate_mode(climb_values)
                
                simplified_data.append({
                    'Rank': rank,
                    'Team': get_team_name(team_num),
                    'Overall ± Std': f"{overall_avg:.2f} ± {overall_std:.2f}",
                    'Robot Valuation': f"{robot_valuation:.2f}",
                    'Death Rate': f"{death_rate:.3f}",
                    'Climb Type': climb_type,
                    'Defended Rate': f"{defended_rate:.3f}"
                })
            
            df_simplified = pd.DataFrame(simplified_data)
            st.dataframe(df_simplified, use_container_width=True, height=500)

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
            st.markdown("### Alliance Configuration")
            
            # Display alliance table
            alliance_table = selector.get_alliance_table()
            df_alliances = pd.DataFrame(alliance_table)
            st.dataframe(df_alliances, use_container_width=True)
        
        with col2:
            st.markdown("### Actions")
            
            if st.button("Auto-Optimize All"):
                selector.reset_picks()
                
                # Pick 1 round
                for alliance in selector.alliances:
                    available_teams = selector.get_available_teams(alliance.captainRank, 'pick1')
                    if available_teams:
                        selector.set_pick(alliance.allianceNumber - 1, 'pick1', available_teams[0].team)
                
                # Pick 2 round
                for alliance in reversed(selector.alliances):
                    available_teams = selector.get_available_teams(alliance.captainRank, 'pick2')
                    if available_teams:
                        selector.set_pick(alliance.allianceNumber - 1, 'pick2', available_teams[0].team)
                
                st.success("Alliances auto-optimized!")
                st.rerun()
            
            if st.button("Reset All Picks"):
                selector.reset_picks()
                st.success("All picks reset!")
                st.rerun()
        
        # Manual alliance configuration
        st.markdown("### Manual Alliance Configuration")
        
        with st.expander("Configure Individual Alliances"):
            for idx, alliance in enumerate(selector.alliances):
                st.markdown(f"**Alliance {alliance.allianceNumber}** (Captain: {alliance.captain})")
                
                col1, col2 = st.columns(2)
                
                with col1:
                    available_pick1 = selector.get_available_teams(alliance.captainRank, 'pick1')
                    pick1_options = ["None"] + [f"{t.team} (Score: {t.score:.1f})" for t in available_pick1]
                    current_pick1 = f"{alliance.pick1} (Score: {selector.get_team_score(alliance.pick1):.1f})" if alliance.pick1 else "None"
                    
                    selected_pick1 = st.selectbox(
                        f"Pick 1 for Alliance {alliance.allianceNumber}",
                        pick1_options,
                        index=pick1_options.index(current_pick1) if current_pick1 in pick1_options else 0,
                        key=f"pick1_{idx}"
                    )
                    
                    if st.button(f"Set Pick 1", key=f"set_pick1_{idx}"):
                        if selected_pick1 != "None":
                            team_num = int(selected_pick1.split()[0])
                            try:
                                selector.set_pick(idx, 'pick1', team_num)
                                st.success(f"Pick 1 set for Alliance {alliance.allianceNumber}!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                
                with col2:
                    available_pick2 = selector.get_available_teams(alliance.captainRank, 'pick2')
                    pick2_options = ["None"] + [f"{t.team} (Score: {t.score:.1f})" for t in available_pick2]
                    current_pick2 = f"{alliance.pick2} (Score: {selector.get_team_score(alliance.pick2):.1f})" if alliance.pick2 else "None"
                    
                    selected_pick2 = st.selectbox(
                        f"Pick 2 for Alliance {alliance.allianceNumber}",
                        pick2_options,
                        index=pick2_options.index(current_pick2) if current_pick2 in pick2_options else 0,
                        key=f"pick2_{idx}"
                    )
                    
                    if st.button(f"Set Pick 2", key=f"set_pick2_{idx}"):
                        if selected_pick2 != "None":
                            team_num = int(selected_pick2.split()[0])
                            try:
                                selector.set_pick(idx, 'pick2', team_num)
                                st.success(f"Pick 2 set for Alliance {alliance.allianceNumber}!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
                
                st.markdown("---")
    else:
        st.info("Please initialize the Alliance Selector first.")

elif page == "🏆 Honor Roll System":
    st.markdown("<div class='main-header'>🏆 Honor Roll System</div>", unsafe_allow_html=True)
    
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
    
    # Display rankings
    st.markdown("### Honor Roll Rankings")
    
    if st.session_state.school_system.teams:
        rankings = st.session_state.school_system.get_honor_roll_ranking()
        
        ranking_data = []
        for rank, (team_num, results) in enumerate(rankings, 1):
            c, sc, rp = st.session_state.school_system.calculate_competencies_score(team_num)
            
            ranking_data.append({
                'Rank': rank,
                'Team': team_num,
                'Final Points': results.final_points,
                'Honor Roll Score': round(results.honor_roll_score, 2),
                'Curved Score': round(results.curved_score, 2),
                'Match Perf': round(results.match_performance_score, 2),
                'Competencies': f"{c}/{sc}/{rp}",
                'Status': 'Qualified'
            })
        
        df_rankings = pd.DataFrame(ranking_data)
        st.dataframe(df_rankings, use_container_width=True, height=400)
    else:
        st.info("No teams in Honor Roll System. Please auto-populate from data.")

elif page == "🔮 Foreshadowing":
    st.markdown("<div class='main-header'>🔮 Match Prediction (Foreshadowing)</div>", unsafe_allow_html=True)
    
    st.info("Match prediction functionality coming soon! This will include Monte Carlo simulation for match outcome predictions.")
    
    # Placeholder for future implementation
    st.markdown("""
    ### Planned Features:
    - **Monte Carlo Simulation**: 5000+ iterations for accurate predictions
    - **Win Probability**: Calculate probability of each alliance winning
    - **Score Prediction**: Expected score ranges for each alliance
    - **Ranking Points**: Automatic RP calculation based on FRC 2025 rules
    - **Confidence Intervals**: Statistical confidence metrics
    """)

# Footer - appears on all pages
st.markdown("<hr style='margin-top: 3rem; border: 1px solid #e2e8f0;'>", unsafe_allow_html=True)
st.markdown("""
<div class='footer'>
    <p style='margin: 0.5rem 0;'>
        <strong style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                       -webkit-background-clip: text; -webkit-text-fill-color: transparent;'>
            Alliance Simulator - Web Version
        </strong>
    </p>
    <p style='margin: 0.3rem 0;'>Developed with ❤️ by <strong>Team Overture 7421</strong></p>
    <p style='margin: 0.3rem 0; font-size: 0.85rem;'>
        For FIRST Robotics Competition - REEFSCAPE 2025
    </p>
    <p style='margin: 0.5rem 0; font-size: 0.8rem; color: #a0aec0;'>
        Version 2.0.0 | Enhanced UI Edition
    </p>
</div>
""", unsafe_allow_html=True)
