"""
Streamlit Web Application for Alliance Simulator
Optimized for Raspberry Pi 4 - lazy imports and cached computations
"""

import streamlit as st
import pandas as pd
from pathlib import Path

# Lazy imports - only load heavy modules when needed
_plotly_loaded = False
px = None
go = None

def _ensure_plotly():
    """Lazy-load plotly only when needed for charts."""
    global _plotly_loaded, px, go
    if not _plotly_loaded:
        import plotly.express as _px
        import plotly.graph_objects as _go
        px = _px
        go = _go
        _plotly_loaded = True
    return px, go

# Core imports (lightweight)
import json
import os
import platform
import threading
import queue
import time
import base64
import tempfile
from collections import Counter

# Local imports
from engine import AnalizadorRobot
from allianceSelector import AllianceSelector, Team
from school_system import TeamScoring, BehaviorReportType
from default_robot_image import load_team_image
from foreshadowing import TeamStatsExtractor, MatchSimulator
from exam_integrator import ExamDataIntegrator
from qr_utils import scan_qr_codes, test_camera
from config_manager import get_global_config
from tba_manager import TBAManager
from ftc_scout_manager import FTCScoutManager


APP_DIR = Path(__file__).resolve().parent
ROOT_DIR = APP_DIR.parent

# ── Module-level constants ──────────────────────────────────────────────────
_POST_MATCH_MAX_ENTRIES = 200       # Hard cap for post-match session state list
_POST_MATCH_UPLOAD_MAX_BYTES = 2 * 1024 * 1024  # 2 MB upload guard
_LOCAL_TEAM_NICKNAMES_CACHE = None
_QUALITY_CHASSIS_LABEL = "Quality Chasis/Driver Movement"
_QUALITY_CHASSIS_LABEL_LEGACY = "Quality Chassis Movement"

_AUTON_COMPLEXITY_SCORE = {
    "Did Nothing": 0.0,
    "Only Moved": 1.0,
    "Only Shot": 2.0,
    "Moves Balls in Middle": 3.0,
    "Good": 4.0,
    "Excellent": 5.0,
}

_DEFENSE_SCORE = {
    "None": 0.0,
    "Bad": 1.0,
    "Mid": 2.5,
    "Good": 4.0,
    "BestOfEvent": 5.0,
    "Trobots(PreguntaAntesDePoner)": 0.0,
}

_BULLDOZE_SCORE = {
    "None": 0.0,
    "Bad": 1.0,
    "Mid": 2.5,
    "Good": 4.0,
    "BestOfEvent": 5.0,
}

_CHASSIS_SCORE = {
    "Tank": 0.0,
    "Mecanum": 3.0,
    "Swerve": 12.0,
}

_QUALITY_CHASSIS_SCORE = {
    "None": 0.0,
    "Bad": 1.0,
    "Mid": 2.5,
    "Good": 4.0,
    "BestOfEvent": 5.0,
}


def _load_local_team_nicknames() -> dict:
    """Load team nicknames from the local 2026 MXMO roster file."""
    global _LOCAL_TEAM_NICKNAMES_CACHE
    if _LOCAL_TEAM_NICKNAMES_CACHE is not None:
        return _LOCAL_TEAM_NICKNAMES_CACHE

    lookup = {}
    roster_paths = [ROOT_DIR / "data" / "teams_2026mxmo.json", APP_DIR / "data" / "teams_2026mxmo.json"]
    for roster_path in roster_paths:
        if not roster_path.exists():
            continue
        try:
            with open(roster_path, 'r', encoding='utf-8') as f:
                roster = json.load(f)
            for team in roster:
                team_number = team.get("team_number")
                nickname = team.get("nickname")
                if team_number and nickname:
                    lookup[str(team_number)] = nickname
        except Exception:
            pass
        break

    _LOCAL_TEAM_NICKNAMES_CACHE = lookup
    return lookup


def _get_post_match_data_version() -> int:
    """Return a stable version token for the current post-match data."""
    pm_data = st.session_state.get("post_match_data", [])
    try:
        return hash(json.dumps(pm_data, sort_keys=True, ensure_ascii=False))
    except Exception:
        return len(pm_data)


def _first_non_empty_mode(team_rows: list, *column_names: str) -> str:
    """Return the first non-empty mode value from the provided columns."""
    for column_name in column_names:
        if not column_name:
            continue
        value = get_mode_from_rows(team_rows, column_name)
        if value:
            return value
    return ""


def _first_non_zero_rate(team_stat: dict, *column_names) -> float:
    """Return the first non-zero rate value from the provided stat columns."""
    for column_name in column_names:
        if not column_name:
            continue
        rate_value = get_rate_from_stat(team_stat, column_name)
        if rate_value:
            return float(rate_value)
    return 0.0


def _categorical_score(value: str, score_map: dict[str, float]) -> float:
    """Convert a categorical mode value into a numeric score."""
    return float(score_map.get(str(value).strip(), 0.0)) if value else 0.0


def _safe_team_number(value: object) -> int:
    """Convert team identifiers to an integer for deterministic tie-breaking."""
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return 999999


def _get_quality_chassis_mode(team_rows: list) -> str:
    return _first_non_empty_mode(team_rows, _QUALITY_CHASSIS_LABEL, _QUALITY_CHASSIS_LABEL_LEGACY)


def _get_pick_metrics() -> dict:
    """Return the configured pick metric layout."""
    return {
        "first_pick": [
            {"label": "Contribution Mode", "kind": "contribution_mode"},
            {"label": "Avg Pts Contribution", "kind": "pm_avg"},
            {"label": "Pts Std Contribution", "kind": "pm_std"},
            {"label": "Auto shoot Mode", "kind": "mode", "columns": ["Shoot amount (Auto)"]},
            {"label": "Auto pass mode", "kind": "mode", "columns": ["Pass amount (Auto)"]},
            {"label": "Auto Missed Shoots Mode", "kind": "mode", "columns": ["How much missed shots? (Auto)"]},
            {"label": "Auton Complexity Mode", "kind": "mode", "columns": ["Auton Complexity"]},
            {"label": "Auton Completed Rate", "kind": "rate", "columns": ["Auton Completed?"]},
            {"label": "TeleOp Shoot Mode", "kind": "mode", "columns": ["Shoot amount (Teleop)"]},
            {"label": "TeleOp pass mode", "kind": "mode", "columns": ["Pass amount (Teleop)"]},
            {"label": "TeleOp Missed Shoots Mode", "kind": "mode", "columns": ["How much missed shots? (Teleop)"]},
            {"label": "Died rate", "kind": "rate", "columns": ["Died"]},
            {"label": "Chassis Type Mode", "kind": "mode", "columns": ["Chasis Type"]},
            {"label": "Auto Climb Mode", "kind": "mode", "columns": ["Climb Position (Auto)"]},
            {"label": "TeleOp Climb Mode", "kind": "mode", "columns": ["Climb"]},
            {"label": "Quality Chasis/Driver Movement", "kind": "mode", "columns": [_QUALITY_CHASSIS_LABEL, _QUALITY_CHASSIS_LABEL_LEGACY]},
        ],
        "second_pick": [
            {"label": "Contribution Mode", "kind": "contribution_mode"},
            {"label": "Auto pass mode", "kind": "mode", "columns": ["Pass amount (Auto)"]},
            {"label": "Auto Missed Shoots Mode", "kind": "mode", "columns": ["How much missed shots? (Auto)"]},
            {"label": "Auton Complexity Mode", "kind": "mode", "columns": ["Auton Complexity"]},
            {"label": "Auton Completed Rate", "kind": "rate", "columns": ["Auton Completed?"]},
            {"label": "TeleOp pass mode", "kind": "mode", "columns": ["Pass amount (Teleop)"]},
            {"label": "Defended Mode", "kind": "mode", "columns": ["Defended?"]},
            {"label": "Bulldozing Mode", "kind": "mode", "columns": ["Bulldozing?"]},
            {"label": "Penalties", "kind": "avg", "columns": ["Penalty Counter"]},
            {"label": "Died rate", "kind": "rate", "columns": ["Died"]},
            {"label": "Chassis Type Mode", "kind": "mode", "columns": ["Chasis Type"]},
            {"label": "Quality Chasis/Driver Movement", "kind": "mode", "columns": [_QUALITY_CHASSIS_LABEL, _QUALITY_CHASSIS_LABEL_LEGACY]},
            {"label": "Auto Climb Mode", "kind": "mode", "columns": ["Climb Position (Auto)"]},
            {"label": "TeleOp Climb Mode", "kind": "mode", "columns": ["Climb"]},
        ],
    }


def _score_2nd_pick(team_stat: dict, team_rows: list) -> float:
    """Score teams for 2nd-pick ordering using utility-oriented traits."""
    auto_complexity = _categorical_score(
        _first_non_empty_mode(team_rows, "Auton Complexity"),
        _AUTON_COMPLEXITY_SCORE,
    )
    bulldozing = _categorical_score(
        _first_non_empty_mode(team_rows, "Bulldozing?"),
        _BULLDOZE_SCORE,
    )
    defended = _categorical_score(
        _first_non_empty_mode(team_rows, "Defended?"),
        _DEFENSE_SCORE,
    )
    chassis = _categorical_score(
        _first_non_empty_mode(team_rows, "Chasis Type"),
        _CHASSIS_SCORE,
    )
    quality = _categorical_score(_get_quality_chassis_mode(team_rows), _QUALITY_CHASSIS_SCORE)
    died_penalty = _first_non_zero_rate(team_stat, ("Died",)) * 6.0
    penalties = compute_numeric_average(team_rows, "Penalty Counter")
    penalty_penalty = min(5.0, penalties / 3.0)
    auto_mode = _first_non_empty_mode(team_rows, "Auton Complexity")
    non_trivial_auto_bonus = 14.0 if auto_mode not in {"", "Did Nothing", "Only Moved"} else 0.0
    swerve_bonus = 18.0 if _first_non_empty_mode(team_rows, "Chasis Type") == "Swerve" else 0.0

    return (
        bulldozing * 6.2
        + defended * 7.4
        + chassis * 3.0
        + quality * 3.0
        + auto_complexity * 1.5
        + non_trivial_auto_bonus
        + swerve_bonus
        - died_penalty
        - penalty_penalty
    )


def _score_1st_pick(team_stat: dict, team_rows: list, team_num: object) -> float:
    """Score teams for 1st-pick ordering with strong contribution weighting."""
    points_avg = float(team_stat.get("overall_avg", 0.0))
    contribution_avg = float(get_pm_avg_pts_contribution(team_num))
    died_rate = _first_non_zero_rate(team_stat, ("Died", "Died/Stopped Moving in Teleop"))
    survival_bonus = max(0.0, 1.0 - died_rate) * 14.0
    auton_completed_rate = _first_non_zero_rate(team_stat, ("Auton Completed?",))
    auton_completed_bonus = auton_completed_rate * 12.0
    auton_complexity = _categorical_score(
        _first_non_empty_mode(team_rows, "Auton Complexity"),
        _AUTON_COMPLEXITY_SCORE,
    )
    auton_complexity_bonus = auton_complexity * 4.0
    swerve_bonus = 16.0 if _first_non_empty_mode(team_rows, "Chasis Type") == "Swerve" else 0.0

    return (
        points_avg * 1.15
        + contribution_avg * 1.25
        + survival_bonus
        + auton_completed_bonus
        + auton_complexity_bonus
        + swerve_bonus
    )


def _build_pick_rankings_dataframe(stats: list[dict], title: str) -> pd.DataFrame | None:
    """Build a pick-specific ranking table from the current team stats."""
    if not stats:
        return None

    team_data_grouped = st.session_state.analizador.get_team_data_grouped()
    metrics_by_pick = _get_pick_metrics()
    metric_defs = metrics_by_pick.get(title, [])
    if not metric_defs:
        return None

    scored_rows = []
    for team_stat in stats:
        team_num = team_stat.get("team", "N/A")
        team_num_int = _safe_team_number(team_num)
        team_key = str(team_num)
        team_rows = team_data_grouped.get(team_key, [])
        if title == "first_pick":
            score = _score_1st_pick(team_stat, team_rows, team_num)
        else:
            score = _score_2nd_pick(team_stat, team_rows)
        scored_rows.append((score, team_num_int, team_stat, team_rows))

    if title in {"first_pick", "second_pick"}:
        scored_rows.sort(key=lambda item: (-item[0], item[1]))

    output_rows = []
    for rank, (_, _, team_stat, team_rows) in enumerate(scored_rows, 1):
        team_num = team_stat.get("team", "N/A")
        row = {
            "Rank": rank,
            "Team Number": get_team_display_label(team_num),
        }

        for metric in metric_defs:
            label = metric.get("label")
            kind = metric.get("kind")
            columns = metric.get("columns") or []
            if not label or not kind:
                continue

            if kind == "contribution_mode":
                row[label] = get_pm_contribution_mode(team_num)
            elif kind == "pm_avg":
                row[label] = round(get_pm_avg_pts_contribution(team_num), 2)
            elif kind == "pm_std":
                row[label] = round(get_pm_std_pts_contribution(team_num), 2)
            elif kind == "mode":
                row[label] = _first_non_empty_mode(team_rows, *columns)
            elif kind == "rate":
                rate_value = _first_non_zero_rate(team_stat, *columns) * 100.0
                row[label] = round(rate_value, 2)
            elif kind == "avg":
                row[label] = round(compute_numeric_average(team_rows, columns[0]), 2) if columns else 0.0
            else:
                row[label] = ""

        output_rows.append(row)

    return pd.DataFrame(output_rows)


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
                "subtitle": "FRC REBUILT 2026",
                "team_name": "Team Overture 7421"
            },
            "scoring_weights": {
                "match_performance": 50,
                "pit_scouting": 30,
                "during_event": 20
            },
            "game": {
                "name": "REBUILT 2026",
                "autonomous": {
                    "leave": 3,
                    "fuel": 1,
                    "tower_level1_auto": 15
                },
                "teleop": {
                    "fuel": 1
                },
                "endgame": {
                    "tower_level1": 10,
                    "tower_level2": 20,
                    "tower_level3": 30
                }
            },
            "metrics": {
                "game_phases": ["autonomous", "teleop", "endgame"],
                "endgame_states": ["tower_level1", "tower_level2", "tower_level3"],
                "match_items": ["fuel", "tower_level1_auto"]
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


# Load configuration (cached to avoid repeated disk reads)
@st.cache_data(ttl=300)
def _cached_load_app_config():
    return load_app_config()

APP_CONFIG = _cached_load_app_config()

# Page configuration - uses values from APP_CONFIG
app_config = APP_CONFIG.get("app", {})
st.set_page_config(
    page_title=app_config.get("title", "Alliance Simulator - Overture 7421"),
    page_icon=app_config.get("icon", "🤖"),
    layout=app_config.get("layout", "wide"),
    initial_sidebar_state=app_config.get("initial_sidebar_state", "expanded"),
    menu_items={
        'About': f"{app_config.get('title', 'Alliance Simulator')} | {app_config.get('subtitle', 'FRC REBUILT 2026')}"
    }
)


def _init_session_state():
    """Initialize all session state variables in one pass for efficiency."""
    global_config = get_global_config()
    
    # Define defaults for simple values
    defaults = {
        'auto_decode_reset_done': False,
        'alliance_selector': None,
        'foreshadowing_prediction': None,
        'foreshadowing_mode': None,
        'foreshadowing_last_iterations': 0,
        'foreshadowing_error': "",
        'foreshadowing_last_inputs': {"red": [], "blue": []},
        'foreshadowing_team_performance': {"red": [], "blue": []},
        'foreshadowing_quick_slider': 1000,
        'exam_integrator': None,
        'selected_team_for_details': None,
        'app_config': APP_CONFIG,
        # QR Scanner state
        'qr_scanner_thread': None,
        'qr_scanner_stop_event': None,
        'qr_scanner_running': False,
        'qr_scanner_selected_camera': 0,
        'qr_available_cameras': [],
        'qr_scanned_codes': [],
        'qr_scanner_status': "",
        'qr_scanner_debounce_seconds': 2.0,
        'qr_last_scan_ts': 0.0,
        'qr_idle_seconds': 5.0,
        'qr_last_scan_preview': "",
        'raw_data_last_edit_ts': 0.0,
        'raw_data_last_saved_hash': "",
        'post_match_data': [],
        # TBA Manager state
        'tba_manager': None,
        'tba_api_key': "",
        'tba_year': 2026,
        'tba_event_key': "",
        'tba_events_list': [],
        'tba_selected_event_name': "",
        # FTC Scout Manager state
        'ftc_manager': None,
        'ftc_season': 2025,
        'ftc_events_list': [],
        'ftc_selected_event_code': "",
        'ftc_selected_event_name': "",
        'ftc_teams_list': [],
        # System Hub update state
        '_hub_update_checked': False,
        '_hub_update_available': False,
        '_hub_latest_sha': "",
        '_hub_current_sha': "",
        # Computation result caches (keyed by engine._data_version)
        '_cached_team_stats_df': None,
        '_cached_team_stats_df_version': -1,
        '_cached_alliance_teams': None,
        '_cached_alliance_teams_version': -1,
    }
    
    # Set defaults only if not already in session state
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value
    
    # Queue needs special handling (not hashable)
    if 'qr_scanner_queue' not in st.session_state:
        st.session_state.qr_scanner_queue = queue.Queue()
    
    # Initialize analizador
    if 'analizador' not in st.session_state:
        st.session_state.analizador = AnalizadorRobot()

    if not st.session_state.post_match_data:
        default_pm_path = ROOT_DIR / "data" / "default_post_match_data.json"
        if default_pm_path.exists():
            try:
                with open(default_pm_path, 'r', encoding='utf-8') as f:
                    loaded_pm = json.load(f)
                if isinstance(loaded_pm, list):
                    st.session_state.post_match_data = loaded_pm[-_POST_MATCH_MAX_ENTRIES:]
            except Exception:
                pass
    
    # Auto-detect and reset old FTC data if current config is FRC
    if not st.session_state.auto_decode_reset_done:
        try:
            raw_data = st.session_state.analizador.get_raw_data()
            if raw_data and raw_data[0]:
                header = raw_data[0]
                has_old_columns = any("FUEL Scored" in col or "Tower Climb Level" in col or "Left Launch Line" in col for col in header)
                current_header = st.session_state.analizador.config_manager.get_column_config().headers
                has_new_columns = any("HP Scored" in col for col in current_header)
                if has_old_columns and has_new_columns:
                    st.session_state.analizador.set_raw_data([current_header])
                    st.session_state.auto_decode_reset_done = True
        except Exception:
            st.session_state.auto_decode_reset_done = True
    
    # Initialize school_system with config values
    if 'school_system' not in st.session_state:
        scoring_cfg = global_config.get_scoring_config()
        honor_weights = scoring_cfg.honor_roll_weights or {}
        st.session_state.school_system = TeamScoring(
            match_weight=honor_weights.get("match_performance", 0.50),
            pit_weight=honor_weights.get("pit_scouting", 0.30),
            event_weight=honor_weights.get("during_event", 0.20)
        )
        st.session_state.school_system.competencies_multiplier = scoring_cfg.competency_multipliers.get("competencies", 6)
        st.session_state.school_system.subcompetencies_multiplier = scoring_cfg.competency_multipliers.get("subcompetencies", 3)
        st.session_state.school_system.behavior_reports_multiplier = scoring_cfg.competency_multipliers.get("behavior_reports", 0)
        st.session_state.school_system.min_competencies_count = scoring_cfg.disqualification_thresholds.get("min_competencies", 2)
        st.session_state.school_system.min_subcompetencies_count = scoring_cfg.disqualification_thresholds.get("min_subcompetencies", 1)
        st.session_state.school_system.min_honor_roll_score = scoring_cfg.disqualification_thresholds.get("min_honor_roll_score", 70.0)
    
    # Initialize scoring_weights
    if 'scoring_weights' not in st.session_state:
        scoring_cfg = global_config.get_scoring_config()
        honor_weights = scoring_cfg.honor_roll_weights or {}
        st.session_state.scoring_weights = {
            "match": int(round(honor_weights.get("match_performance", 0.50) * 100)),
            "pit": int(round(honor_weights.get("pit_scouting", 0.30) * 100)),
            "event": int(round(honor_weights.get("during_event", 0.20) * 100))
        }


# Run session state initialization
_init_session_state()
global_config = get_global_config()

# CSS must be injected on every rerun since Streamlit re-renders the entire page
# Minified CSS for better Pi 4 performance
st.markdown("""<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
*{font-family:'Inter',sans-serif}
body,.stApp,.main{background-color:#000;color:#f5f5f5}
.main{background:#000;background-attachment:fixed}
.block-container{padding:2rem 3rem;background:rgba(18,18,20,0.95);border-radius:20px;box-shadow:0 12px 40px rgba(0,0,0,0.6);backdrop-filter:blur(16px);margin:1rem;color:#f5f5f5}
.main-header{font-size:3rem;font-weight:700;background:linear-gradient(135deg,#667eea 0%,#764ba2 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;text-align:center;margin-bottom:2rem}
.sub-header{font-size:1.8rem;font-weight:600;color:#9f9dfd;margin-top:2rem;margin-bottom:1rem;border-left:4px solid #9f9dfd;padding-left:1rem}
div[data-testid="stMetricValue"]{font-size:2rem;font-weight:700;color:#c3c2ff}
div[data-testid="stMetricLabel"]{font-weight:600;color:#d1d5db}
.metric-card{background:linear-gradient(135deg,rgba(50,50,70,0.6) 0%,rgba(30,30,45,0.8) 100%);padding:1.5rem;border-radius:12px;box-shadow:0 10px 24px rgba(15,15,25,0.7);margin:0.5rem 0;border:1px solid rgba(159,157,253,0.35);transition:transform 0.2s,box-shadow 0.2s}
.metric-card:hover{transform:translateY(-2px);box-shadow:0 12px 24px rgba(102,126,234,0.25)}
.stButton>button{width:100%;background:linear-gradient(135deg,#7f7eff 0%,#a855f7 100%);color:#fff;border:none;border-radius:8px;padding:0.6rem 1.2rem;font-weight:600;transition:all 0.3s ease;box-shadow:0 6px 14px rgba(128,90,213,0.5)}
.stButton>button:hover{transform:translateY(-2px);box-shadow:0 12px 24px rgba(128,90,213,0.6)}
section[data-testid="stSidebar"]{background:linear-gradient(180deg,#111118 0%,#1f1b2b 100%)}
section[data-testid="stSidebar"] h2{color:white !important;font-weight:700}
section[data-testid="stSidebar"] h3{color:rgba(255,255,255,0.9) !important;font-weight:600}
section[data-testid="stSidebar"] .stRadio label{color:white !important;font-weight:500}
.stTabs [data-baseweb="tab-list"]{gap:8px;background-color:transparent}
.stTabs [data-baseweb="tab"]{background:linear-gradient(135deg,rgba(40,40,60,0.8) 0%,rgba(30,30,45,0.9) 100%);border-radius:8px;padding:0.5rem 1rem;font-weight:600;border:1px solid rgba(159,157,253,0.25);color:#e5e7ff}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,#7f7eff 0%,#a855f7 100%);color:#fff !important}
.dataframe{border-radius:8px;overflow:hidden;box-shadow:0 4px 18px rgba(0,0,0,0.6);color:#f5f5f5;background:rgba(15,15,20,0.85)}
.stAlert{border-radius:8px;border-left:4px solid;background:rgba(30,30,45,0.9);color:#f8fafc}
.uploadedFile{border-radius:8px;border:2px dashed #667eea}
.js-plotly-plot{border-radius:12px;box-shadow:0 6px 24px rgba(0,0,0,0.7);background:rgba(15,15,20,0.8)}
.team-badge{display:inline-block;background:linear-gradient(135deg,#7f7eff 0%,#a855f7 100%);color:white;padding:0.3rem 0.8rem;border-radius:20px;font-weight:600;font-size:0.9rem;margin:0.2rem}
.stats-card{background:linear-gradient(135deg,rgba(40,40,60,0.85) 0%,rgba(25,25,40,0.9) 100%);padding:1.5rem;border-radius:12px;box-shadow:0 12px 32px rgba(10,10,20,0.7);margin:1rem 0;border-left:4px solid #9f9dfd}
.footer{text-align:center;padding:2rem;color:#9ca3af;font-size:0.9rem;margin-top:3rem}
</style>""", unsafe_allow_html=True)

# Streamlit configuration defaults (can be overridden in config/columns.json)
DEFAULT_STREAMLIT_CONFIG = {
    "overall_rankings": {
        "average_columns": [
            {"column": "HP Scored (Auto)", "label": "Auto HP Scored"},
            {"column": "HP Scored (Teleop)", "label": "Teleop HP Scored"}
        ],
        "rate_columns": [
            {"columns": ["Is HP True to your team?"], "label": "HP True Rate (%)"},
            {"columns": ["If climbed, Got stuck in Tower? (Auto)"], "label": "Auto Stuck Rate (%)"},
            {"columns": ["Jammed over balls?"], "label": "Jammed Rate (%)"},
            {"columns": ["Died"], "label": "Died Rate (%)"},
            {"columns": ["Do you want it on our alliance?"], "label": "Alliance Preference Rate (%)"}
        ]
    },
    "simplified_ranking": {
        "rate_columns": [
            {"columns": ["Died"], "label": "Died Rate (%)"},
            {"columns": ["Jammed over balls?"], "label": "Jammed Rate (%)"}
        ],
        "mode_columns": [
            {"column": "Auton Quality", "label": "Auton Quality"},
            {"column": "Driver Quality", "label": "Driver Quality"},
            {"column": "Climb", "label": "Climb Mode"}
        ]
    },
    "detailed_stats": {
        "compare_metrics": [
            {"type": "points_avg", "label": "Points Avg"},
            {"type": "robot_valuation", "label": "Robot Valuation"},
            {"type": "avg", "column": "HP Scored (Auto)", "label": "Auto HP Scored Avg"},
            {"type": "avg", "column": "HP Scored (Teleop)", "label": "Teleop HP Scored Avg"},
            {"type": "rate", "columns": ["Died"], "label": "Died Rate", "format": "percent"}
        ],
        "radar_categories": [
            {"type": "points_avg", "label": "Points Avg"},
            {"type": "robot_valuation", "label": "Robot Valuation"},
            {"type": "avg", "column": "HP Scored (Auto)", "label": "Auto HP Scored"},
            {"type": "avg", "column": "HP Scored (Teleop)", "label": "Teleop HP Scored"},
            {"type": "consistency", "label": "Consistency"}
        ],
        "bar_metrics": [
            {"type": "points_avg", "label": "Points Avg"},
            {"type": "robot_valuation", "label": "Robot Valuation"},
            {"type": "avg", "column": "HP Scored (Auto)", "label": "Auto HP Scored"},
            {"type": "avg", "column": "HP Scored (Teleop)", "label": "Teleop HP Scored"}
        ],
        "comparison_table": [
            {"type": "points_avg", "label": "Points Avg"},
            {"type": "points_std", "label": "Points Std"},
            {"type": "robot_valuation", "label": "Robot Valuation"},
            {"type": "avg", "column": "HP Scored (Auto)", "label": "Auto HP Scored Avg"},
            {"type": "avg", "column": "HP Scored (Teleop)", "label": "Teleop HP Scored Avg"}
        ]
    },
    "match_trend": {
        "auto": {
            "hp_scored": "HP Scored (Auto)"
        },
        "teleop": {
            "hp_scored": "HP Scored (Teleop)"
        },
        "endgame": {
            "tower_climb": "Climb"
        }
    }
}

def _merge_dicts(base: dict, override: dict) -> dict:
    """Shallow-deep merge dictionaries for nested config sections."""
    merged = dict(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _merge_dicts(merged.get(key, {}), value)
        else:
            merged[key] = value
    return merged

def get_streamlit_config() -> dict:
    """Return streamlit_config from config/columns.json, merged with defaults."""
    analyzer = st.session_state.analizador if 'analizador' in st.session_state else None
    if analyzer and hasattr(analyzer, 'config_manager'):
        overrides = analyzer.config_manager.get_streamlit_config()
    else:
        overrides = {}
    return _merge_dicts(DEFAULT_STREAMLIT_CONFIG, overrides)

def _metric_value(team_stat: dict, team_rows: list, metric: dict) -> float:
    metric_type = metric.get("type")
    if metric_type in ("overall_avg", "points_avg"):
        return float(team_stat.get('overall_avg', 0.0))
    if metric_type in ("overall_std", "points_std"):
        return float(team_stat.get('overall_std', 0.0))
    if metric_type == "robot_valuation":
        return float(team_stat.get('RobotValuation', 0.0))
    if metric_type == "avg":
        column = metric.get("column")
        return float(compute_numeric_average(team_rows, column)) if column else 0.0
    if metric_type == "rate":
        columns = metric.get("columns") or []
        return float(get_rate_from_stat(team_stat, tuple(columns)) * 100.0) if columns else 0.0
    if metric_type == "consistency":
        overall_avg = float(team_stat.get('overall_avg', 0.0))
        overall_std = float(team_stat.get('overall_std', 0.0))
        if overall_avg <= 0:
            return 50.0
        consistency = (1 - (overall_std / (overall_avg + 0.01))) * 100
        return float(max(0.0, min(100.0, consistency)))
    return 0.0

def _format_metric_value(metric: dict, value: float) -> str:
    fmt = metric.get("format")
    if fmt == "percent":
        return f"{value:.1f}%"
    return f"{value:.2f}"

def _safe_autorefresh(interval_ms: int, key: str) -> None:
    """Trigger periodic reruns using streamlit-autorefresh."""
    try:
        import importlib
        module = importlib.import_module("streamlit_autorefresh")
        st_autorefresh = getattr(module, "st_autorefresh", None)
        if st_autorefresh:
            st_autorefresh(interval=interval_ms, key=key)
    except Exception:
        st.warning(
            "⚠️ **Auto-refresh unavailable** — scanned codes won't appear automatically. "
            "Install with: `pip install streamlit-autorefresh`, then restart the app."
        )

# Helper functions
def load_csv_data(uploaded_file):
    """Load CSV data into the analyzer with basic validation.
    
    Limits: maximum 50 MB file size to prevent memory exhaustion.
    """
    try:
        # Validate file size (limit to 50 MB to prevent memory issues)
        MAX_CSV_BYTES = 50 * 1024 * 1024  # 50 MB
        file_bytes = uploaded_file.getvalue()
        if len(file_bytes) > MAX_CSV_BYTES:
            return False, f"File too large ({len(file_bytes) // (1024*1024)} MB). Maximum allowed size is 50 MB."

        # Parse directly from bytes — no temp-file round-trip needed
        st.session_state.analizador.load_csv_from_bytes(file_bytes)
        
        return True, "CSV loaded successfully!"
    except Exception as e:
        return False, f"Error loading CSV: {str(e)}"

def get_team_stats_dataframe():
    """Get team statistics as a pandas DataFrame (cached by data version)."""
    version = st.session_state.analizador._data_version
    pm_version = _get_post_match_data_version()
    cache_version = (version, pm_version)
    if (st.session_state._cached_team_stats_df is not None
            and st.session_state._cached_team_stats_df_version == cache_version):
        return st.session_state._cached_team_stats_df

    stats = st.session_state.analizador.get_detailed_team_stats()
    if not stats:
        return None
    
    team_data_grouped = st.session_state.analizador.get_team_data_grouped()

    # Convert to DataFrame with selected columns for simplified view
    df_data = []
    for team_stat in stats:
        team_num = team_stat.get('team', 'N/A')
        team_key = str(team_num)
        team_rows = team_data_grouped.get(team_key, [])
        points_avg = round(float(team_stat.get('overall_avg', 0.0)), 2)

        row = {
            '_team_num_sort': _safe_team_number(team_num),
            'Team Number': get_team_display_label(team_num),
            'Points Avg': points_avg,
            'Contribution Mode': get_pm_contribution_mode(team_num),
            'Avg Pts Contribution': round(get_pm_avg_pts_contribution(team_num), 2),
            'Pts Std Contribution': round(get_pm_std_pts_contribution(team_num), 2),
            'Auto Shoot Mode': get_mode_from_rows(team_rows, 'Shoot amount (Auto)'),
            'Auto Pass Mode': get_mode_from_rows(team_rows, 'Pass amount (Auto)'),
            'Auto Missed Shoots Mode': get_mode_from_rows(team_rows, 'How much missed shots? (Auto)'),
            'Auton Complexity Mode': get_mode_from_rows(team_rows, 'Auton Complexity'),
            'Auton Completed Rate': round(get_rate_from_stat(team_stat, ('Auton Completed?',)) * 100.0, 2),
            'TeleOp Shoot Mode': get_mode_from_rows(team_rows, 'Shoot amount (Teleop)'),
            'TeleOp Pass Mode': get_mode_from_rows(team_rows, 'Pass amount (Teleop)'),
            'TeleOp Missed Shoots Mode': get_mode_from_rows(team_rows, 'How much missed shots? (Teleop)'),
            'Defended Mode': get_mode_from_rows(team_rows, 'Defended?'),
            'Bulldozing Mode': get_mode_from_rows(team_rows, 'Bulldozing?'),
            'Penalties': round(compute_numeric_average(team_rows, 'Penalty Counter'), 2),
            'Died rate': round(get_rate_from_stat(team_stat, ('Died',)) * 100.0, 2),
            'Chassis Type Mode': get_mode_from_rows(team_rows, 'Chasis Type'),
            'Auto Climb Mode': get_mode_from_rows(team_rows, 'Climb Position (Auto)'),
            'TeleOp Climb Mode': get_mode_from_rows(team_rows, 'Climb'),
            'Quality Chasis/Driver Movement': _get_quality_chassis_mode(team_rows),
        }

        df_data.append(row)

    result = pd.DataFrame(df_data)
    if not result.empty and 'Points Avg' in result.columns:
        result = result.sort_values(by=['Points Avg', '_team_num_sort'], ascending=[False, True]).reset_index(drop=True)
        result = result.drop(columns=['_team_num_sort'])
        result.insert(0, 'Rank', result.index + 1)
    st.session_state._cached_team_stats_df = result
    st.session_state._cached_team_stats_df_version = cache_version
    return result

def create_alliance_selector_teams():
    """Create Team objects for alliance selector from current stats (cached by data version)."""
    version = st.session_state.analizador._data_version
    if (st.session_state._cached_alliance_teams is not None
            and st.session_state._cached_alliance_teams_version == version):
        return st.session_state._cached_alliance_teams

    stats = st.session_state.analizador.get_detailed_team_stats()
    if not stats:
        return []

    team_data_grouped = st.session_state.analizador.get_team_data_grouped()
    team_entries = []
    for stat in stats:
        team_num = stat.get('team', 0)
        team_key = str(team_num)
        team_rows = team_data_grouped.get(team_key, [])
        team_entries.append({
            'stat': stat,
            'team_num': team_num,
            'team_num_int': _safe_team_number(team_num),
            'points_avg': float(stat.get('overall_avg', 0.0)),
            'pick1_score': _score_1st_pick(stat, team_rows, team_num),
            'pick2_score': _score_2nd_pick(stat, team_rows),
        })

    captain_sorted = sorted(team_entries, key=lambda item: (-item['points_avg'], item['team_num_int']))
    pick1_sorted = sorted(team_entries, key=lambda item: (-item['pick1_score'], item['team_num_int']))
    pick2_sorted = sorted(team_entries, key=lambda item: (-item['pick2_score'], item['team_num_int']))

    captain_rank_by_team = {str(item['team_num']): idx for idx, item in enumerate(captain_sorted, 1)}
    pick1_rank_by_team = {str(item['team_num']): idx for idx, item in enumerate(pick1_sorted, 1)}
    pick2_rank_by_team = {str(item['team_num']): idx for idx, item in enumerate(pick2_sorted, 1)}
    
    teams = []
    for stat in stats:
        team_num = stat.get('team', 0)
        team_key = str(team_num)
        overall_avg = stat.get('overall_avg', 0)
        robot_val = stat.get('RobotValuation', 0)
        team_rows = team_data_grouped.get(team_key, [])
        
        # Get phase scores
        phase_scores = st.session_state.analizador.calculate_team_phase_scores(int(team_num))
        death_rate = get_rate_from_stat(stat, ("Died", "Died/Stopped Moving in Teleop"))
        defended_rate = get_rate_from_stat(stat, ("Defended?", "Was Defended Heavily"))
        defense_rate = max(
            get_rate_from_stat(stat, ("Defended?", "Played Defense")),
            get_rate_from_stat(stat, ("Bulldozing?", "Was Defended Heavily")),
        )
        
        team_name = get_team_display_label(team_num)

        teams.append(Team(
            num=team_num,
            rank=captain_rank_by_team.get(team_key, 0),
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
            ,
            captain_rank=captain_rank_by_team.get(team_key),
            pick1_rank=pick1_rank_by_team.get(team_key),
            pick2_rank=pick2_rank_by_team.get(team_key),
            pick1_score=_score_1st_pick(stat, team_rows, team_num),
            pick2_score=_score_2nd_pick(stat, team_rows),
        ))

    st.session_state._cached_alliance_teams = teams
    st.session_state._cached_alliance_teams_version = version
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
    """Return formatted team label with TBA nickname when available."""
    num_str = str(team_number)
    tba = st.session_state.get('tba_manager')
    nickname = None
    if tba:
        nickname = tba.get_team_nickname(num_str)
    if not nickname:
        nickname = _load_local_team_nicknames().get(num_str)
    if nickname and nickname != num_str:
        return f"{num_str} - {nickname}"
    return num_str


def get_pm_contribution_mode(team_number) -> str:
    """Return the mode contribution label for a given team from post-match data.

    Looks up ``st.session_state.post_match_data`` and aggregates every
    contribution entry whose ``team_numbers`` slot matches *team_number*.
    Returns the most frequent label, or an empty string when no data exist.
    """
    pm_data = st.session_state.get("post_match_data", [])
    if not pm_data:
        return ""
    try:
        target = int(team_number)
    except (TypeError, ValueError):
        return ""
    if target == 0:
        return ""
    contribs = []
    for entry in pm_data:
        team_nums = entry.get("team_numbers", [])
        for slot_idx, contrib in enumerate(entry.get("contributions", [])):
            slot_team = team_nums[slot_idx] if slot_idx < len(team_nums) else None
            if slot_team is not None and int(slot_team) == target:
                contribs.append(contrib)
    if not contribs:
        return ""
    return Counter(contribs).most_common(1)[0][0]


def get_pm_contribution_points(team_number) -> list:
    """Return the per-match points contributions used for post-match stats."""
    pm_data = st.session_state.get("post_match_data", [])
    if not pm_data:
        return []
    try:
        target = int(team_number)
    except (TypeError, ValueError):
        return []
    if target == 0:
        return []

    even_split = frozenset({
        "Did not score any points",
        "Scored few points",
        "Scored ~30% of alliance score",
    })
    pct_map = {
        "Did not score any points":         0.00,
        "Scored few points":                0.05,
        "Scored ~30% of alliance score":    0.30,
        "Scored ~50% of alliance score":    0.50,
        "Scored ~75% of alliance score":    0.75,
        "Scored almost all alliance score": 0.90,
    }

    pts_list = []
    for entry in pm_data:
        team_nums = entry.get("team_numbers", [])
        num_teams = entry.get("num_teams", 6)
        half = num_teams // 2
        all_contribs = entry.get("contributions", [])

        for slot_idx, contrib in enumerate(all_contribs):
            slot_team = team_nums[slot_idx] if slot_idx < len(team_nums) else None
            if slot_team is None:
                continue
            try:
                if int(slot_team) != target:
                    continue
            except (TypeError, ValueError):
                continue

            is_red = slot_idx < half
            alliance_pts = entry["red_points"] if is_red else entry["blue_points"]
            alliance_contribs = [
                all_contribs[i]
                for i in (range(half) if is_red else range(half, num_teams))
                if i < len(all_contribs)
            ]

            if contrib in ("Dedicated to passing", "Dedicated to defend"):
                continue
            elif contrib in even_split and alliance_contribs and all(c == contrib for c in alliance_contribs):
                pts_list.append(alliance_pts / len(alliance_contribs))
            else:
                pct = pct_map.get(contrib)
                if pct is not None:
                    pts_list.append(alliance_pts * pct)

    return pts_list


def get_pm_avg_pts_contribution(team_number) -> float:
    """Return the average individual points contribution for a team from post-match data.

    Applies the same rules as the Qualitative Metrics tab:
    - 'Dedicated to passing' / 'Dedicated to defend' → match excluded from average
    - 'Did not score any points' → 0 pts
    - 'Scored few points' → 5% of alliance pts
    - 'Scored ~30% of alliance score' → 30% of alliance pts
    - 'Scored ~50% of alliance score' → 50% of alliance pts
    - 'Scored ~75% of alliance score' → 75% of alliance pts
    - 'Scored almost all alliance score' → 90% of alliance pts
    - If ALL alliance members share the same base-level label
      ('Did not score any points', 'Scored few points', or
      'Scored ~30% of alliance score') → alliance_pts / num_alliance_teams
    """
    pts_list = get_pm_contribution_points(team_number)
    return sum(pts_list) / len(pts_list) if pts_list else 0.0


def get_pm_std_pts_contribution(team_number) -> float:
    """Return the sample standard deviation of per-match contribution points."""
    pts_list = get_pm_contribution_points(team_number)
    if len(pts_list) < 2:
        return 0.0
    mean = sum(pts_list) / len(pts_list)
    return ((sum((value - mean) ** 2 for value in pts_list)) / (len(pts_list) - 1)) ** 0.5


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
    data = [
        {
            'Phase': 'Auto',
            'FUEL': breakdown.get('auto_fuel', 0),
            'Tower L1': breakdown.get('auto_tower_l1_count', 0),
            'Leave': breakdown.get('teams_left_auto_zone', 0)
        },
        {
            'Phase': 'Teleop',
            'FUEL': breakdown.get('teleop_fuel', 0),
            'Tower L1': breakdown.get('endgame_climbs', {}).get('level1', 0),
            'Tower L2': breakdown.get('endgame_climbs', {}).get('level2', 0),
            'Tower L3': breakdown.get('endgame_climbs', {}).get('level3', 0)
        }
    ]
    return pd.DataFrame(data)


def build_algae_summary_df(breakdown):
    climbs = breakdown.get('endgame_climbs', {})
    return pd.DataFrame([
        {'Climb Level': 'Did Not Climb', 'Teams': climbs.get('none', 0)},
        {'Climb Level': 'Level 1 (10 pts)', 'Teams': climbs.get('level1', 0)},
        {'Climb Level': 'Level 2 (20 pts)', 'Teams': climbs.get('level2', 0)},
        {'Climb Level': 'Level 3 (30 pts)', 'Teams': climbs.get('level3', 0)},
    ])


def build_climb_breakdown_df(breakdown):
    rows = []
    for team, climb_type, points in breakdown.get('endgame_scores', []):
        rows.append({
            'Team': get_team_display_label(team),
            'Climb Level': climb_type.replace('level', 'Level ').replace('none', 'Did Not Climb').capitalize(),
            'Points': points
        })
    return pd.DataFrame(rows)


def build_team_performance_df(team_performances):
    rows = []
    for perf in team_performances:
        rows.append({
            'Team': get_team_display_label(perf.team_number),
            'Auto FUEL': round(perf.auto_fuel, 2),
            'Auto Tower L1 %': round(getattr(perf, 'p_auto_tower_l1', 0) * 100, 1),
            'Teleop FUEL': round(perf.teleop_fuel, 2),
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
    <p style='color: rgba(255,255,255,0.7); font-size: 0.8rem; margin: 0.2rem 0;'>{game_config.get('name', 'FRC REBUILT 2026')}</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("<hr style='border: 1px solid rgba(255,255,255,0.2); margin: 1rem 0;'>", unsafe_allow_html=True)

st.sidebar.markdown("### 📍 Navigation")

page = st.sidebar.radio(
    "Select Page",
    ["📁 Data Management", "📈 Team Statistics", 
     "🤝 Alliance Selector", "🏆 Honor Roll System", "🔮 Foreshadowing",
     "📊 Post-Match", "🛠️ System Hub"],
    label_visibility="collapsed"
)

st.sidebar.markdown("---")
if st.sidebar.button("🔄 Reload Configurations"):
    global_config.reload_all()
    st.session_state.analizador.reload_configuration_from_file()
    scoring_cfg = global_config.get_scoring_config()
    honor_weights = scoring_cfg.honor_roll_weights or {}
    st.session_state.scoring_weights = {
        "match": int(round(honor_weights.get("match_performance", 0.50) * 100)),
        "pit": int(round(honor_weights.get("pit_scouting", 0.30) * 100)),
        "event": int(round(honor_weights.get("during_event", 0.20) * 100))
    }
    st.session_state.school_system.set_scoring_weights(
        honor_weights.get("match_performance", 0.50),
        honor_weights.get("pit_scouting", 0.30),
        honor_weights.get("during_event", 0.20)
    )
    st.session_state.school_system.competencies_multiplier = scoring_cfg.competency_multipliers.get("competencies", 6)
    st.session_state.school_system.subcompetencies_multiplier = scoring_cfg.competency_multipliers.get("subcompetencies", 3)
    st.session_state.school_system.behavior_reports_multiplier = scoring_cfg.competency_multipliers.get("behavior_reports", 0)
    st.session_state.school_system.min_competencies_count = scoring_cfg.disqualification_thresholds.get("min_competencies", 2)
    st.session_state.school_system.min_subcompetencies_count = scoring_cfg.disqualification_thresholds.get("min_subcompetencies", 1)
    st.session_state.school_system.min_honor_roll_score = scoring_cfg.disqualification_thresholds.get("min_honor_roll_score", 70.0)
    st.session_state.alliance_selector = None
    st.sidebar.success("Configurations reloaded.")
    st.rerun()

# ── TBA Manager sidebar ─────────────────────────────────────────────────────
st.sidebar.markdown("---")
with st.sidebar.expander("🔵 The Blue Alliance", expanded=False):
    st.markdown("**TBA Team Name Lookup**")
    tba_use_api = st.toggle(
        "Use TBA API",
        value=bool(st.session_state.tba_api_key),
        key="tba_use_api_toggle"
    )
    if tba_use_api:
        st.session_state.tba_api_key = st.text_input(
            "TBA Auth Key",
            value=st.session_state.tba_api_key,
            type="password",
            placeholder="Paste your X-TBA-Auth-Key",
            help="Get your key at thebluealliance.com/account → Read API Keys"
        )
        st.session_state.tba_year = int(st.number_input(
            "Year",
            min_value=1992,
            max_value=2099,
            value=int(st.session_state.tba_year),
            step=1,
        ))
        if st.button("🔌 Connect & Fetch Events", key="tba_connect_btn"):
            api_key = st.session_state.tba_api_key.strip()
            if not api_key:
                st.error("Please enter a TBA API key first.")
            else:
                try:
                    mgr = TBAManager(api_key=api_key, use_api=True)
                    events = mgr.get_events_for_year(st.session_state.tba_year)
                    if events:
                        st.session_state.tba_manager = mgr
                        st.session_state.tba_events_list = sorted(
                            events, key=lambda e: e.get("name", "")
                        )
                        st.success(f"Connected! {len(events)} events loaded.")
                    else:
                        st.warning("No events returned. Check key/year.")
                except ValueError as e:
                    st.error(str(e))

        if st.session_state.tba_events_list:
            event_options = {
                ev["key"]: ev.get("name", ev["key"])
                for ev in st.session_state.tba_events_list
            }
            sel_key = st.selectbox(
                "Select Event",
                options=list(event_options.keys()),
                format_func=lambda k: event_options[k],
                key="tba_event_selectbox",
            )
            if st.button("📥 Load Teams for Event", key="tba_load_teams_btn"):
                mgr = st.session_state.tba_manager
                if mgr:
                    with st.spinner("Loading teams…"):
                        teams = mgr.get_teams_for_event(sel_key)
                    if teams:
                        st.session_state.tba_event_key = sel_key
                        st.session_state.tba_selected_event_name = event_options[sel_key]
                        st.success(f"Loaded {len(teams)} teams.")
                    else:
                        st.warning("No teams found for that event.")

        if st.session_state.tba_manager and st.session_state.tba_event_key:
            st.caption(
                f"✅ Active event: **{st.session_state.tba_selected_event_name}**"
            )
        elif st.session_state.tba_manager:
            st.caption("Manager connected – select and load an event.")
    else:
        # Offline mode: try to load from cached files
        if st.session_state.tba_event_key:
            st.caption(f"Offline – cached event: {st.session_state.tba_event_key}")
        if st.button("🗑️ Clear TBA Manager", key="tba_clear_btn"):
            st.session_state.tba_manager = None
            st.session_state.tba_events_list = []
            st.session_state.tba_event_key = ""
            st.session_state.tba_selected_event_name = ""
            st.rerun()

# ── FTC Scout sidebar ────────────────────────────────────────────────────────
st.sidebar.markdown("---")
with st.sidebar.expander("🟠 FTC Scout", expanded=False):
    st.markdown("**FTC Team & Event Lookup**")
    st.markdown(
        "<small>Powered by [ftcscout.org](https://ftcscout.org)</small>",
        unsafe_allow_html=True,
    )

    # Season selector
    st.session_state.ftc_season = int(st.number_input(
        "FTC Season",
        min_value=2019,
        max_value=2099,
        value=int(st.session_state.ftc_season),
        step=1,
        key="ftc_season_input",
        help="Enter the start year of the FTC season (e.g. 2025 for 2025-26)"
    ))

    # Optional search filters
    with st.expander("🔍 Event Search Filters", expanded=False):
        ftc_search_text = st.text_input("Search text", key="ftc_search_text", placeholder="Event name…")
        ftc_region = st.text_input("Region", key="ftc_region", placeholder="e.g. USTX")
        ftc_limit = st.number_input("Max results", min_value=1, max_value=500, value=50, step=10, key="ftc_limit")

    if st.button("🔌 Fetch Events", key="ftc_fetch_events_btn"):
        if st.session_state.ftc_manager is None:
            st.session_state.ftc_manager = FTCScoutManager()
        mgr_ftc = st.session_state.ftc_manager
        with st.spinner("Fetching FTC events…"):
            events_ftc = mgr_ftc.search_events(
                st.session_state.ftc_season,
                search_text=st.session_state.get("ftc_search_text", "") or None,
                region=st.session_state.get("ftc_region", "") or None,
                limit=int(st.session_state.get("ftc_limit", 50)),
                force_refresh=True,
            )
        if events_ftc:
            st.session_state.ftc_events_list = events_ftc
            st.success(f"Found {len(events_ftc)} events.")
        else:
            st.warning("No events returned. Check season or filters.")

    if st.session_state.ftc_events_list:
        ftc_event_options = {
            ev.get("code", ""): ev.get("name", ev.get("code", ""))
            for ev in st.session_state.ftc_events_list
            if ev.get("code")
        }
        ftc_sel_code = st.selectbox(
            "Select Event",
            options=list(ftc_event_options.keys()),
            format_func=lambda k: ftc_event_options.get(k, k),
            key="ftc_event_selectbox",
        )
        if st.button("📥 Load Teams for Event", key="ftc_load_teams_btn"):
            if st.session_state.ftc_manager is None:
                st.session_state.ftc_manager = FTCScoutManager()
            mgr_ftc2 = st.session_state.ftc_manager
            with st.spinner("Loading FTC teams…"):
                teams_ftc = mgr_ftc2.get_teams_for_event(
                    st.session_state.ftc_season, ftc_sel_code, force_refresh=True
                )
            if teams_ftc:
                st.session_state.ftc_teams_list = teams_ftc
                st.session_state.ftc_selected_event_code = ftc_sel_code
                st.session_state.ftc_selected_event_name = ftc_event_options.get(ftc_sel_code, ftc_sel_code)
                st.success(f"Loaded {len(teams_ftc)} team participations.")
            else:
                st.warning("No teams found for that event.")

    if st.session_state.ftc_selected_event_code:
        st.caption(f"✅ Active: **{st.session_state.ftc_selected_event_name}** "
                   f"({len(st.session_state.ftc_teams_list)} teams)")

    if st.button("🗑️ Clear FTC Scout", key="ftc_clear_btn"):
        st.session_state.ftc_manager = None
        st.session_state.ftc_events_list = []
        st.session_state.ftc_selected_event_code = ""
        st.session_state.ftc_selected_event_name = ""
        st.session_state.ftc_teams_list = []
        st.rerun()

# Main content based on selected page
if page == "📁 Data Management":
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
        # ── Dependency check ────────────────────────────────────────────────
        deps_ok = True
        deps_error = None
        try:
            import importlib
            importlib.import_module("cv2")
            importlib.import_module("pyzbar")
            importlib.import_module("numpy")
        except Exception as _e:
            deps_ok = False
            deps_error = str(_e)

        if not deps_ok:
            st.error(
                "⚠️ **QR scanner dependencies missing.**  "
                "Install with: `pip install opencv-python pyzbar numpy`"
            )
            if deps_error:
                st.caption(f"Error detail: {deps_error}")
        else:
            # ── Queue drain helper ───────────────────────────────────────────
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
                            st.session_state.qr_last_scan_ts = time.time()
                            st.session_state.qr_last_scan_preview = (
                                payload[:80] + ("…" if len(payload) > 80 else "")
                            )
                    elif kind == "DONE":
                        st.session_state.qr_scanner_running = False
                        st.session_state.qr_scanner_stop_event = None
                        st.session_state.qr_scanner_status = "stopped"
                        st.session_state.qr_last_scan_ts = 0.0
                    elif kind == "ERROR":
                        st.session_state.qr_scanner_running = False
                        st.session_state.qr_scanner_stop_event = None
                        st.session_state.qr_scanner_status = f"error:{payload}"

                t = st.session_state.qr_scanner_thread
                if st.session_state.qr_scanner_running and t and not t.is_alive():
                    st.session_state.qr_scanner_running = False
                    st.session_state.qr_scanner_stop_event = None
                    if not st.session_state.qr_scanner_status:
                        st.session_state.qr_scanner_status = "stopped"
                return drained, auto_updated

            _, _auto_updated = _drain_qr_queue()
            if _auto_updated:
                st.rerun()

            # ── Status banner ────────────────────────────────────────────────
            _is_running = st.session_state.qr_scanner_running
            _raw_status = st.session_state.qr_scanner_status or ""
            _is_error = _raw_status.startswith("error:")

            if _is_running:
                if platform.system() == "Darwin":
                    st.success("🟢 **Scanner is running** — on macOS the preview window is disabled for stability.")
                else:
                    st.success("🟢 **Scanner is running** — point your QR code at the camera window.")
            elif _is_error:
                st.error(f"🔴 **Scanner error:** {_raw_status.removeprefix('error:')}")
            else:
                st.info("⚪ **Scanner idle** — configure settings below and press ▶ Start.")

            st.markdown("---")

            # ── Section 1: Camera setup ──────────────────────────────────────
            with st.expander("🎥 Camera Setup", expanded=not _is_running):
                cfg_col1, cfg_col2 = st.columns([1, 1])
                with cfg_col1:
                    max_probe = st.number_input(
                        "Max index to probe",
                        min_value=0, max_value=20, value=4, step=1,
                        help="Checks indices 0 … N and lists those that open successfully.",
                        key="qr_max_probe"
                    )
                    if st.button("🔎 Detect Cameras", key="qr_detect_btn"):
                        available = []
                        with st.spinner("Probing cameras…"):
                            for idx in range(int(max_probe) + 1):
                                try:
                                    if test_camera(idx):
                                        available.append(idx)
                                except Exception:
                                    pass
                        st.session_state.qr_available_cameras = available
                        if available:
                            st.session_state.qr_scanner_selected_camera = int(available[0])
                            st.session_state.qr_scanner_status = ""
                            st.success(f"Found cameras: {available}")
                        else:
                            st.warning("No cameras detected. Try a higher max index or enter one manually.")

                with cfg_col2:
                    if st.session_state.qr_available_cameras:
                        _sel = st.selectbox(
                            "Camera",
                            options=st.session_state.qr_available_cameras,
                            index=(
                                st.session_state.qr_available_cameras.index(
                                    st.session_state.qr_scanner_selected_camera
                                )
                                if st.session_state.qr_scanner_selected_camera
                                in st.session_state.qr_available_cameras
                                else 0
                            ),
                            key="qr_cam_select"
                        )
                        st.session_state.qr_scanner_selected_camera = int(_sel)
                    else:
                        st.session_state.qr_scanner_selected_camera = int(
                            st.number_input(
                                "Camera index (manual)",
                                min_value=0, max_value=20,
                                value=int(st.session_state.qr_scanner_selected_camera),
                                step=1,
                                key="qr_cam_manual"
                            )
                        )
                    if st.button("🔬 Test Camera", key="qr_test_btn"):
                        with st.spinner("Testing…"):
                            ok = test_camera(int(st.session_state.qr_scanner_selected_camera))
                        if ok:
                            st.success("✅ Camera OK")
                        else:
                            st.error("❌ Camera not available")

                adv_col1, adv_col2 = st.columns(2)
                with adv_col1:
                    st.session_state.qr_scanner_debounce_seconds = float(
                        st.number_input(
                            "Debounce (s)",
                            min_value=0.0, max_value=10.0,
                            value=float(st.session_state.qr_scanner_debounce_seconds),
                            step=0.5,
                            help="Prevents repeated reads while the same code stays in view.",
                            key="qr_debounce"
                        )
                    )
                with adv_col2:
                    st.session_state.qr_idle_seconds = float(
                        st.number_input(
                            "Auto-update idle (s)",
                            min_value=1.0, max_value=30.0,
                            value=float(st.session_state.qr_idle_seconds),
                            step=1.0,
                            help="Auto-refreshes the page after this many idle seconds.",
                            key="qr_idle"
                        )
                    )

            # ── Section 2: Controls ──────────────────────────────────────────
            ctrl_col1, ctrl_col2, ctrl_col3 = st.columns([2, 2, 2])
            with ctrl_col1:
                if st.button(
                    "▶️ Start Scanner",
                    disabled=_is_running,
                    use_container_width=True,
                    type="primary",
                    key="qr_start_btn"
                ):
                    q = st.session_state.qr_scanner_queue
                    while True:
                        try:
                            q.get_nowait()
                        except queue.Empty:
                            break
                    camera_index = int(st.session_state.qr_scanner_selected_camera)
                    debounce = float(st.session_state.qr_scanner_debounce_seconds)
                    stop_event = threading.Event()
                    st.session_state.qr_scanner_stop_event = stop_event

                    def _worker(out_queue: "queue.Queue", cam_idx: int, deb: float, stop_evt: threading.Event):
                        try:
                            scanned = scan_qr_codes(
                                update_callback=lambda data: out_queue.put(("SCAN", data)),
                                camera_index=cam_idx,
                                debounce_seconds=deb,
                                show_window=(platform.system() != "Darwin"),
                                stop_event=stop_evt,
                            )
                            out_queue.put(("DONE", scanned))
                        except Exception as _ex:
                            out_queue.put(("ERROR", str(_ex)))

                    st.session_state.qr_scanner_running = True
                    st.session_state.qr_scanner_status = ""
                    st.session_state.qr_last_scan_ts = time.time()
                    _t = threading.Thread(
                        target=_worker,
                        args=(st.session_state.qr_scanner_queue, camera_index, debounce, stop_event),
                        daemon=True,
                    )
                    st.session_state.qr_scanner_thread = _t
                    _t.start()
                    st.rerun()

            with ctrl_col2:
                if st.button(
                    "⏹️ Stop Scanner",
                    disabled=not _is_running,
                    use_container_width=True,
                    key="qr_stop_btn"
                ):
                    stop_evt = st.session_state.qr_scanner_stop_event
                    if stop_evt and hasattr(stop_evt, "set"):
                        stop_evt.set()
                        st.session_state.qr_scanner_status = "Stopping scanner..."
                    else:
                        st.session_state.qr_scanner_status = "Scanner stop requested."
                    st.rerun()

            with ctrl_col3:
                if st.button(
                    "🔄 Refresh",
                    use_container_width=True,
                    key="qr_refresh_btn",
                    help="Pull any newly scanned codes from the background thread."
                ):
                    added, _ = _drain_qr_queue()
                    st.session_state.qr_scanner_status = (
                        f"Refreshed — {added} new code(s) added." if added else "No new codes."
                    )
                    st.rerun()

            # ── Section 3: Results ───────────────────────────────────────────
            st.markdown("---")
            res_col1, res_col2 = st.columns([3, 1])
            with res_col1:
                n_codes = len(st.session_state.qr_scanned_codes)
                st.metric("QR Codes Scanned", n_codes)
                if st.session_state.qr_last_scan_preview:
                    st.caption(f"Last: `{st.session_state.qr_last_scan_preview}`")
            with res_col2:
                if st.button(
                    "🗑️ Clear List",
                    use_container_width=True,
                    key="qr_clear_btn",
                    help="Remove all scanned codes from the session."
                ):
                    st.session_state.qr_scanned_codes = []
                    st.session_state.qr_scanner_status = ""
                    st.rerun()

            if st.session_state.qr_scanned_codes:
                with st.expander(f"📋 Scanned codes ({n_codes})", expanded=False):
                    st.dataframe(
                        pd.DataFrame({"QR Data": st.session_state.qr_scanned_codes}),
                        use_container_width=True,
                        hide_index=True,
                    )
            else:
                st.caption("No QR codes scanned yet.")

            # ── Auto-refresh while running ───────────────────────────────────
            if _is_running:
                last_scan = st.session_state.qr_last_scan_ts
                if last_scan and (time.time() - last_scan) >= st.session_state.qr_idle_seconds:
                    st.session_state.qr_scanner_status = ""
                _safe_autorefresh(interval_ms=1000, key="qr_scanner_autorefresh")

            st.markdown("---")

            st.markdown("### 🖥️ Headless Mode (Linux)")
            st.markdown("""
            For headless deployments with barcode/QR scanners acting as HID devices:

            1. Configure scanner hardware ID in `config/columns.json`
            2. Run the HID interceptor: `python lib/headless_interceptor.py`
            3. Or use systemd services: `sudo scripts/install_services.sh --enable-hid`

            The interceptor captures scanner input and writes to `data/default_scouting.csv`.
            """)

    with tab3:
        st.markdown("### ✏️ Edit Raw Data")
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
            st.caption("Modify cells below and click Save Changes to update the dataset.")
            edited_df = st.data_editor(
                df,
                use_container_width=True,
                height=420,
                num_rows="dynamic",
                key="raw_data_editor"
            )

            save_cols = st.columns([1, 3])
            with save_cols[0]:
                if st.button("💾 Save Changes"):
                    cleaned_df = edited_df.fillna("")
                    rows = cleaned_df.values.tolist()
                    new_sheet = [raw_data[0]] + [[str(cell) for cell in row] for row in rows]
                    st.session_state.analizador.set_raw_data(new_sheet)
                    st.session_state.raw_data_last_edit_ts = 0.0
                    st.session_state.raw_data_last_saved_hash = cleaned_df.to_csv(index=False)
                    st.success("Raw data saved. Stats updated.")
                    st.rerun()

            # Auto-save changes after idle
            cleaned_df = edited_df.fillna("")
            current_hash = cleaned_df.to_csv(index=False)
            if current_hash != st.session_state.raw_data_last_saved_hash:
                st.session_state.raw_data_last_edit_ts = time.time()
                st.session_state.raw_data_last_saved_hash = current_hash

            if st.session_state.raw_data_last_edit_ts:
                if time.time() - st.session_state.raw_data_last_edit_ts >= 2.0:
                    rows = cleaned_df.values.tolist()
                    new_sheet = [raw_data[0]] + [[str(cell) for cell in row] for row in rows]
                    st.session_state.analizador.set_raw_data(new_sheet)
                    st.session_state.raw_data_last_edit_ts = 0.0
                    st.success("Raw data auto-saved. Stats updated.")
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
                df = get_team_stats_dataframe()
                if df is None:
                    st.warning("No statistics available to export")
                    st.stop()
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
    team_data_grouped = st.session_state.analizador.get_team_data_grouped()
    
    if not stats:
        st.info("No team statistics available. Please load data first.")
    else:
        # Create tabs for different views
        tab1, tab2, tab3, tab4, tab5 = st.tabs([
            "📊 Points Rankings",
            "🔍 Detailed Stats",
            "📋 Simplified Ranking",
            "🥇 1st Pick",
            "🥈 2nd Pick",
        ])
        
        with tab1:
            st.markdown("### Team Points Rankings")

            team_stats_df = get_team_stats_dataframe()

            if team_stats_df is not None and not team_stats_df.empty:
                st.dataframe(team_stats_df, use_container_width=True, height=520, hide_index=True)

                # Visualization
                st.markdown("### Performance Visualization")
                chart_df = pd.DataFrame([
                    {
                        'Rank': rank,
                        'Team': get_team_display_label(team_stat.get('team', 'N/A')),
                        'Points Avg': round(team_stat.get('overall_avg', 0.0), 2),
                        'Robot Valuation': round(team_stat.get('RobotValuation', 0.0), 2),
                        'Points Std': round(team_stat.get('overall_std', 0.0), 2),
                    }
                    for rank, team_stat in enumerate(stats, 1)
                ])
                px, go = _ensure_plotly()
                fig = px.scatter(
                    chart_df,
                    x='Points Avg',
                    y='Robot Valuation',
                    size='Points Std',
                    hover_data=['Team', 'Rank'],
                    title='Points Average vs Robot Valuation (size = std deviation)',
                    labels={'Points Avg': 'Points Average', 'Robot Valuation': 'Robot Valuation'}
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
            streamlit_cfg = get_streamlit_config()
            details_cfg = streamlit_cfg.get("detailed_stats", {})
            
            # Add compare mode toggle
            compare_mode = st.checkbox("🔀 Compare Multiple Teams", key="compare_mode_toggle")
            
            if compare_mode:
                # Multi-team comparison mode
                st.markdown("#### Multi-Team Comparison")
                
                selected_teams = st.multiselect(
                    "Select Teams to Compare (2 or more)",
                    options=all_teams,
                    default=all_teams[:2] if len(all_teams) >= 2 else [],
                    format_func=lambda x: get_team_display_label(x)
                )
                
                if len(selected_teams) >= 2:
                    # Get stats for selected teams
                    selected_stats = [s for s in stats if s.get('team') in selected_teams]

                    streamlit_cfg = get_streamlit_config()
                    details_cfg = streamlit_cfg.get("detailed_stats", {})
                    compare_metrics = details_cfg.get("compare_metrics", [])
                    radar_metrics = details_cfg.get("radar_categories", [])
                    bar_metrics = details_cfg.get("bar_metrics", [])
                    table_metrics = details_cfg.get("comparison_table", [])

                    # Side-by-side metrics display using columns
                    st.markdown("#### Key Metrics Comparison")
                    cols = st.columns(len(selected_teams))

                    for idx, team_num in enumerate(selected_teams):
                        team_stat = next((s for s in stats if s.get('team') == team_num), None)
                        if team_stat:
                            with cols[idx]:
                                team_name = get_team_display_label(team_num)
                                team_rows = team_data_grouped.get(team_num, [])
                                st.markdown(f"**{team_name}**")
                                for metric in compare_metrics:
                                    label = metric.get("label") or metric.get("column") or metric.get("type")
                                    if not label:
                                        continue
                                    value = _metric_value(team_stat, team_rows, metric)
                                    st.metric(label, _format_metric_value(metric, value))
                                avg_contrib = get_pm_avg_pts_contribution(team_num)
                                st.metric("Avg Pts Contribution", f"{avg_contrib:.2f}")

                    if radar_metrics:
                        st.markdown("#### Performance Radar Chart")
                        px, go = _ensure_plotly()
                        categories = [m.get("label") or m.get("column") or m.get("type") for m in radar_metrics]
                        max_values = []
                        for metric in radar_metrics:
                            metric_values = []
                            for s in selected_stats:
                                team_num = s.get('team', 'N/A')
                                metric_values.append(_metric_value(s, team_data_grouped.get(team_num, []), metric))
                            max_val = max(metric_values) if metric_values else 1
                            max_values.append(max_val if max_val > 0 else 1)

                        radar_fig = go.Figure()
                        colors = px.colors.qualitative.Set2
                        for idx, team_stat in enumerate(selected_stats):
                            team_num = team_stat.get('team', 'N/A')
                            team_rows = team_data_grouped.get(team_num, [])
                            raw_values = [_metric_value(team_stat, team_rows, m) for m in radar_metrics]
                            values = [
                                (raw_values[i] / max_values[i]) * 100 if max_values[i] > 0 else 0
                                for i in range(len(raw_values))
                            ]
                            radar_fig.add_trace(go.Scatterpolar(
                                r=values + [values[0]] if values else [0],
                                theta=categories + [categories[0]] if categories else [],
                                fill='toself',
                                name=get_team_display_label(team_num),
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

                    if bar_metrics:
                        st.markdown("#### Side-by-Side Bar Comparison")
                        bar_data = []
                        for team_stat in selected_stats:
                            team_num = team_stat.get('team', 'N/A')
                            team_rows = team_data_grouped.get(team_num, [])
                            for metric in bar_metrics:
                                label = metric.get("label") or metric.get("column") or metric.get("type")
                                if not label:
                                    continue
                                value = _metric_value(team_stat, team_rows, metric)
                                bar_data.append({
                                    'Team': get_team_display_label(team_num),
                                    'Metric': label,
                                    'Value': value
                                })

                        if bar_data:
                            bar_df = pd.DataFrame(bar_data)
                            px, go = _ensure_plotly()
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

                    if table_metrics:
                        st.markdown("#### Detailed Comparison Table")
                        table_rows = {}
                        for metric in table_metrics:
                            label = metric.get("label") or metric.get("column") or metric.get("type")
                            if not label:
                                continue
                            table_rows[label] = {}
                            for team_num in selected_teams:
                                team_stat = next((s for s in stats if s.get('team') == team_num), None)
                                if not team_stat:
                                    continue
                                team_rows = team_data_grouped.get(team_num, [])
                                table_rows[label][team_num] = _metric_value(team_stat, team_rows, metric)
                        table_rows["Avg Pts Contribution"] = {
                            team_num: round(get_pm_avg_pts_contribution(team_num), 2)
                            for team_num in selected_teams
                        }
                        if table_rows:
                            comparison_table = pd.DataFrame(table_rows).T
                            comparison_table.columns = [get_team_display_label(c) for c in comparison_table.columns]
                            st.dataframe(comparison_table, use_container_width=True)
                    
                elif len(selected_teams) == 1:
                    st.info("Please select at least 2 teams to compare.")
                else:
                    st.info("Select teams to compare from the dropdown above.")
            
            else:
                # Single team selection mode (original behavior)
                selected_team_num = st.selectbox("Select a Team", options=all_teams, format_func=lambda x: get_team_display_label(x))

                
                if selected_team_num:
                    team_stat = next((s for s in stats if s.get('team') == selected_team_num), None)
                    
                    if team_stat:
                        team_rows = st.session_state.analizador.get_team_data_grouped().get(str(selected_team_num), [])
                        metrics = details_cfg.get("compare_metrics", [])
                        cols = st.columns(3)
                        for idx, metric in enumerate(metrics):
                            label = metric.get("label") or metric.get("column") or metric.get("type")
                            if not label:
                                continue
                            value = _metric_value(team_stat, team_rows, metric)
                            with cols[idx % 3]:
                                st.metric(label, _format_metric_value(metric, value))
                        
                        # Complete metrics table
                        st.markdown("### Complete Metric Snapshot")
                        formatted_metrics = {}
                        for key, value in team_stat.items():
                            if isinstance(value, (float, int)):
                                formatted_metrics[key] = round(float(value), 3)
                            else:
                                formatted_metrics[key] = value
                        formatted_metrics['Avg Pts Contribution'] = round(get_pm_avg_pts_contribution(selected_team_num), 2)

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

                            streamlit_cfg = get_streamlit_config()
                            match_cfg = streamlit_cfg.get("match_trend", {})
                            auto_cols = match_cfg.get("auto", {}) or {}
                            teleop_cols = match_cfg.get("teleop", {}) or {}
                            endgame_cols = match_cfg.get("endgame", {}) or {}

                            leave_col = auto_cols.get("leave", "")
                            auto_hp_col = auto_cols.get("hp_scored", auto_cols.get("fuel", "HP Scored (Auto)"))
                            auto_tower_l1_col = auto_cols.get("tower_l1", "")

                            teleop_hp_col = teleop_cols.get("hp_scored", teleop_cols.get("fuel", "HP Scored (Teleop)"))

                            tower_climb_col = endgame_cols.get("tower_climb", "Climb")

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

                        def _normalize_tower_climb(value: str) -> str:
                            v = (value or "").strip().lower()
                            if v == "l3" or "level 3" in v or "level3" in v:
                                return "level3"
                            if v == "l2" or "level 2" in v or "level2" in v:
                                return "level2"
                            if v == "l1" or "level 1" in v or "level1" in v:
                                return "level1"
                            return "none"

                        def _row_match_points(row) -> float:
                            points = 0.0

                            # Autonomous scoring
                            leave = _parse_bool(_get_value(row, leave_col))
                            if leave:
                                points += float(auto_points.get("leave", 0))

                            auto_hp = _get_num(row, auto_hp_col)
                            points += auto_hp * float(auto_points.get("fuel", 0))

                            auto_tower_l1 = _parse_bool(_get_value(row, auto_tower_l1_col))
                            if auto_tower_l1:
                                points += float(auto_points.get("tower_level1_auto", 0))

                            # Teleop scoring
                            teleop_hp = _get_num(row, teleop_hp_col)
                            points += teleop_hp * float(teleop_points.get("fuel", 0))

                            # Endgame scoring (tower climb level)
                            climb_val = _get_text(row, tower_climb_col)
                            climb_key = _normalize_tower_climb(climb_val)
                            if climb_key == "level3":
                                points += float(endgame_points.get("tower_level3", 0))
                            elif climb_key == "level2":
                                points += float(endgame_points.get("tower_level2", 0))
                            elif climb_key == "level1":
                                points += float(endgame_points.get("tower_level1", 0))

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
                            px, go = _ensure_plotly()
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

        with tab4:
            st.markdown("### 1st Pick Rankings")
            st.caption("This view follows the normal ranking order and displays the pick metrics requested for the first alliance selection slot.")

            first_pick_df = _build_pick_rankings_dataframe(stats, "first_pick")
            if first_pick_df is not None and not first_pick_df.empty:
                st.dataframe(first_pick_df, use_container_width=True, height=600, hide_index=True)
            else:
                st.info("No 1st pick ranking data available.")

        with tab5:
            st.markdown("### 2nd Pick Rankings")
            st.caption("This view sorts teams by a custom utility score that emphasizes defense, bulldozing, autonomous breadth, chassis, and driver movement.")

            second_pick_df = _build_pick_rankings_dataframe(stats, "second_pick")
            if second_pick_df is not None and not second_pick_df.empty:
                st.dataframe(second_pick_df, use_container_width=True, height=600, hide_index=True)
            else:
                st.info("No 2nd pick ranking data available.")

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

                # Pick 2 round (highest seeds first)
                for alliance in selector.alliances:
                    if not alliance.captain or alliance.pick2:
                        continue
                    available_teams2 = selector.get_available_teams(alliance.captainRank, 'pick2')
                    if available_teams2:
                        selector.set_pick(alliance.allianceNumber - 1, 'pick2', available_teams2[0].team)
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
                    
                    captain_options = {team.team: get_team_display_label(team.team) for team in available_captains}
                    captain_options[0] = "Auto"

                    # Ensure current captain is in the list
                    if a.captain and a.captain not in captain_options:
                        captain_options[a.captain] = get_team_display_label(a.captain)

                    selected_captain = st.selectbox(
                            f"Captain A{a.allianceNumber}",
                            options=list(captain_options.keys()),
                            format_func=lambda x: captain_options.get(x, "Auto"),
                            key=f"captain_{i}",
                            index=list(captain_options.keys()).index(a.captain) if a.captain in captain_options else 0
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
                    
                    team_options = {str(team.team): get_team_display_label(team.team) for team in available_teams}
                    if a.pick1 and str(a.pick1) not in team_options:
                        team_options[str(a.pick1)] = get_team_display_label(a.pick1)
                    team_options["0"] = "None"

                    # Pick 1
                    options_list = list(team_options.keys())
                    pick1_val = str(a.pick1) if a.pick1 is not None and str(a.pick1) in team_options else "0"
                    selected_pick1 = st.selectbox(
                        f"Pick 1 A{a.allianceNumber}",
                        options=options_list,
                        format_func=lambda x: team_options.get(x, "None"),
                        key=f"pick1_{i}",
                        index=options_list.index(pick1_val)
                    )
                    current_pick1_value = str(a.pick1) if a.pick1 is not None else "0"
                    if selected_pick1 != current_pick1_value:
                        try:
                            selected_val = int(selected_pick1) if selected_pick1 != "0" else None
                            selector.set_pick(i, 'pick1', selected_val)
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))

                    # Pick 2 — build available teams excluding already-selected picks
                    available_teams2 = selector.get_available_teams(a.captainRank, 'pick2')
                    team_options2 = {str(team.team): get_team_display_label(team.team) for team in available_teams2}
                    if a.pick2 and str(a.pick2) not in team_options2:
                        team_options2[str(a.pick2)] = get_team_display_label(a.pick2)
                    team_options2["0"] = "None"

                    options_list2 = list(team_options2.keys())
                    pick2_val = str(a.pick2) if a.pick2 is not None and str(a.pick2) in team_options2 else "0"
                    selected_pick2 = st.selectbox(
                        f"Pick 2 A{a.allianceNumber}",
                        options=options_list2,
                        format_func=lambda x: team_options2.get(x, "None"),
                        key=f"pick2_{i}",
                        index=options_list2.index(pick2_val)
                    )
                    current_pick2_value = str(a.pick2) if a.pick2 is not None else "0"
                    if selected_pick2 != current_pick2_value:
                        try:
                            selected_val2 = int(selected_pick2) if selected_pick2 != "0" else None
                            selector.set_pick(i, 'pick2', selected_val2)
                            st.rerun()
                        except ValueError as e:
                            st.error(str(e))
    else:
        st.info("Please initialize the Alliance Selector first.")

elif page == "🏆 Honor Roll System":
    st.markdown("<div class='main-header'>🏆 Honor Roll System</div>", unsafe_allow_html=True)
    
    # Exam Import Section
    with st.expander("📥 Import Exam Data", expanded=False):
        st.markdown("Upload the unified pit-scouting CSV to integrate scores into the Honor Roll System.")

        unified_file = st.file_uploader(
            "Upload Pit Scouting CSV (.csv)",
            type=['csv'],
            key="unified_exam_upload",
            help="Single CSV with all exam sections (mech_*, prog_*, elec_*, comp_*)"
        )

        if st.button("🔄 Process Exams", type="primary", use_container_width=True):
            if unified_file is None:
                st.warning("Please upload a pit-scouting CSV file to process.")
            else:
                try:
                    with st.spinner("Processing exam file..."):
                        integrator = ExamDataIntegrator()

                        with tempfile.NamedTemporaryFile(mode='wb', suffix='.csv', delete=False) as tmp:
                            tmp.write(unified_file.getvalue())
                            tmp_path = tmp.name

                        all_results = integrator.integrate_unified_exam(tmp_path)
                        os.unlink(tmp_path)

                        # Apply to school system
                        integrator.apply_to_scoring_system(st.session_state.school_system)

                        # Calculate all scores
                        st.session_state.school_system.calculate_all_scores()

                        # Store integrator for later reference
                        st.session_state.exam_integrator = integrator

                        # Get statistics
                        stats = integrator.get_exam_statistics()

                        st.success("Exam data imported successfully!")
                        for section, res in all_results.items():
                            st.write(f"✅ {section.title()}: {len(res)} teams")

                        st.info(f"📊 Total teams in system: {stats['total_teams']} | 💬 Scouting comments: {stats['total_comments']}")

                except Exception as e:
                    st.error(f"Failed to process exam file: {str(e)}")

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
                    # FRC 3-robot alliances: split into two pick tiers (pick1 and pick2).
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
                    
                    # Format title with team number
                    team_name = ""
                    title_str = get_team_display_label(team_num)
                    
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
            c, sc, rp = st.session_state.school_system.calculate_competencies_score(team_num)
            team_numbers_list.append(team_num)
            ranking_data.append({
                "Rank": rank,
                "Team": get_team_display_label(team_num),
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
                format_func=lambda x: get_team_display_label(x),
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
                        title=f"{get_team_display_label(selected_detail_team)} Score Breakdown",
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

                    st.markdown("#### Scoring Contribution")
                    st.dataframe(coral_df, use_container_width=True)
                    st.markdown("#### Tower Climb Summary")
                    st.dataframe(algae_df, use_container_width=True)
                    st.markdown("#### Endgame Breakdown")
                    st.dataframe(climb_df, use_container_width=True)

                    st.markdown("#### Additional Metrics")
                    st.write(
                        f"Auto Leave: {red_breakdown.get('teams_left_auto_zone', 0)}/3"
                    )

                with breakdown_tabs[1]:
                    blue_breakdown = prediction.blue_breakdown
                    coral_df = build_coral_breakdown_df(blue_breakdown)
                    algae_df = build_algae_summary_df(blue_breakdown)
                    climb_df = build_climb_breakdown_df(blue_breakdown)

                    st.markdown("#### Scoring Contribution")
                    st.dataframe(coral_df, use_container_width=True)
                    st.markdown("#### Tower Climb Summary")
                    st.dataframe(algae_df, use_container_width=True)
                    st.markdown("#### Endgame Breakdown")
                    st.dataframe(climb_df, use_container_width=True)

                    st.markdown("#### Additional Metrics")
                    st.write(
                        f"Auto Leave: {blue_breakdown.get('teams_left_auto_zone', 0)}/3"
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

                red_teleop_fuel = prediction.red_breakdown.get('teleop_fuel', 0)
                blue_teleop_fuel = prediction.blue_breakdown.get('teleop_fuel', 0)

                if red_teleop_fuel > blue_teleop_fuel * 1.2:
                    st.write("Red shows a strong teleop FUEL advantage. Blue should focus on defense or tower climbing.")
                elif blue_teleop_fuel > red_teleop_fuel * 1.2:
                    st.write("Blue shows a strong teleop FUEL advantage. Red should prioritize efficient fuel cycles.")
                else:
                    st.write("Teleop FUEL is balanced. Tower climbing and endgame could decide the match.")

                st.caption("Foreshadowing simulations use historical averages and random sampling for variability.")

elif page == "📊 Post-Match":
    st.markdown("<div class='main-header'>📊 Post-Match Analysis</div>", unsafe_allow_html=True)

    CONTRIBUTION_OPTIONS = [
        "Did not score any points",
        "Dedicated to passing",
        "Dedicated to defend",
        "Scored few points",
        "Scored ~30% of alliance score",
        "Scored ~50% of alliance score",
        "Scored ~75% of alliance score",
        "Scored almost all alliance score",
    ]

    # Contribution level numeric weights for mode display
    _CONTRIB_WEIGHTS = {opt: i for i, opt in enumerate(CONTRIBUTION_OPTIONS)}

    def _contribution_mode(values: list) -> str:
        """Return the most frequently occurring contribution level."""
        if not values:
            return "—"
        counts = Counter(values)
        return counts.most_common(1)[0][0]

    tab_entry, tab_metrics = st.tabs(["📝 Match Entry", "📈 Qualitative Metrics"])

    with tab_entry:
        # ── Top toolbar: Save / Upload ──────────────────────────────────────
        toolbar_col1, toolbar_col2, toolbar_col3 = st.columns([2, 2, 2])
        with toolbar_col1:
            # Download as JSON
            if st.session_state.post_match_data:
                json_bytes = json.dumps(st.session_state.post_match_data, indent=2).encode("utf-8")
                st.download_button(
                    "💾 Save as JSON",
                    data=json_bytes,
                    file_name="post_match_data.json",
                    mime="application/json",
                    use_container_width=True,
                    key="pm_download_json",
                )
            else:
                st.button("💾 Save as JSON", disabled=True, use_container_width=True, key="pm_download_json_dis")

        with toolbar_col2:
            # Download as CSV
            if st.session_state.post_match_data:
                csv_rows = []
                for e in st.session_state.post_match_data:
                    team_nums = e.get("team_numbers", [])
                    for i, c in enumerate(e.get("contributions", [])):
                        alliance = "Red" if i < e.get("num_teams", 6) // 2 else "Blue"
                        csv_rows.append({
                            "match_number": e["match_number"],
                            "red_points": e["red_points"],
                            "blue_points": e["blue_points"],
                            "team_number": team_nums[i] if i < len(team_nums) else "",
                            "team_slot": i + 1,
                            "alliance": alliance,
                            "contribution": c,
                        })
                csv_bytes = pd.DataFrame(csv_rows).to_csv(index=False).encode("utf-8")
                st.download_button(
                    "📄 Save as CSV",
                    data=csv_bytes,
                    file_name="post_match_data.csv",
                    mime="text/csv",
                    use_container_width=True,
                    key="pm_download_csv",
                )
            else:
                st.button("📄 Save as CSV", disabled=True, use_container_width=True, key="pm_download_csv_dis")

        with toolbar_col3:
            # Upload previously saved JSON
            pm_upload = st.file_uploader(
                "📂 Load JSON",
                type=["json"],
                key="pm_upload_file",
                label_visibility="collapsed",
                help="Upload a previously saved post_match_data.json file"
            )
            if pm_upload is not None:
                upload_id = f"{pm_upload.name}_{pm_upload.size}"
                if st.session_state.get("_pm_upload_processed_id") != upload_id:
                    try:
                        raw_bytes = pm_upload.read()
                        if len(raw_bytes) > _POST_MATCH_UPLOAD_MAX_BYTES:
                            st.error("File too large (max 2 MB).")
                        else:
                            loaded_data = json.loads(raw_bytes.decode("utf-8"))
                            if isinstance(loaded_data, list):
                                st.session_state.post_match_data = loaded_data[-_POST_MATCH_MAX_ENTRIES:]
                                st.session_state._pm_upload_processed_id = upload_id
                                st.success(f"Loaded {len(loaded_data)} matches.")
                                st.rerun()
                            else:
                                st.error("Invalid format: expected a JSON array.")
                    except Exception as _ex:
                        st.error(f"Error loading file: {_ex}")

        st.markdown("---")
        st.markdown("### Record Post-Match Data")

        with st.form("post_match_form", clear_on_submit=True):
            pm_col1, pm_col2 = st.columns(2)
            with pm_col1:
                pm_match_number = st.number_input("Match Number", min_value=1, value=1, step=1)
                pm_red_points = st.number_input("Red Alliance Points", min_value=0, value=0, step=1, key="pm_red_points")
            with pm_col2:
                pm_blue_points = st.number_input("Blue Alliance Points", min_value=0, value=0, step=1, key="pm_blue_points")
                pm_num_teams = st.number_input(
                    "Number of Teams That Participated",
                    min_value=1, max_value=6, value=6, step=1,
                    help="Total teams in this match (usually 6: 3 red + 3 blue)"
                )

            st.markdown("#### Team Contribution Breakdown")
            st.caption("For each participating team, enter the team number and select their contribution.")
            contributions = []
            team_numbers = []
            contrib_cols = st.columns(min(int(pm_num_teams), 3))
            for t_idx in range(int(pm_num_teams)):
                col = contrib_cols[t_idx % 3]
                alliance_label = "🔴 Red" if t_idx < int(pm_num_teams) // 2 else "🔵 Blue"
                with col:
                    t_num = st.number_input(
                        f"Team # ({alliance_label})",
                        min_value=1, max_value=99999,
                        value=None,
                        placeholder="Team number",
                        step=1,
                        key=f"pm_team_num_{t_idx}"
                    )
                    team_numbers.append(int(t_num) if t_num else 0)
                    contrib = st.selectbox(
                        "Contribution",
                        options=CONTRIBUTION_OPTIONS,
                        key=f"pm_contrib_{t_idx}"
                    )
                    contributions.append(contrib)

            submitted = st.form_submit_button("✅ Save Match Entry", type="primary", use_container_width=True)
            if submitted:
                entry = {
                    "match_number": int(pm_match_number),
                    "red_points": int(pm_red_points),
                    "blue_points": int(pm_blue_points),
                    "num_teams": int(pm_num_teams),
                    "team_numbers": team_numbers,
                    "contributions": list(contributions),
                }
                existing = [e for e in st.session_state.post_match_data if e["match_number"] != entry["match_number"]]
                existing.append(entry)
                existing_sorted = sorted(existing, key=lambda x: x["match_number"])
                # Cap to max entries to prevent unbounded memory growth
                st.session_state.post_match_data = existing_sorted[-_POST_MATCH_MAX_ENTRIES:]
                st.success(f"Match {int(pm_match_number)} saved!")

        if st.session_state.post_match_data:
            st.markdown("---")
            st.markdown("### Recorded Matches")

            # Per-team row view (like Team Statistics)
            per_team_rows = []
            for e in st.session_state.post_match_data:
                team_nums = e.get("team_numbers", [])
                for i, contrib in enumerate(e.get("contributions", [])):
                    alliance = "🔴 Red" if i < e.get("num_teams", 6) // 2 else "🔵 Blue"
                    team_display = (
                        get_team_display_label(team_nums[i])
                        if i < len(team_nums)
                        else f"Slot {i + 1}"
                    )
                    per_team_rows.append({
                        "Team": team_display,
                        "Match": e["match_number"],
                        "Alliance": alliance,
                        "Red Pts": e["red_points"],
                        "Blue Pts": e["blue_points"],
                        "Contribution": contrib,
                    })

            pm_display_df = pd.DataFrame(per_team_rows)
            st.dataframe(pm_display_df, use_container_width=True, hide_index=True)
            if st.button("🗑️ Clear All Post-Match Data", type="secondary"):
                st.session_state.post_match_data = []
                st.rerun()

    with tab_metrics:
        pm_data = st.session_state.post_match_data
        if not pm_data:
            st.info(
                "No post-match data yet. Record matches in the **Match Entry** tab, "
                "or upload a previously saved JSON file."
            )
        else:
            # ── Build per-team lookup: team_id → contributions and alliance points ──
            team_contrib_map: dict = {}
            team_pts_map: dict = {}
            team_contrib_pts_map: dict = {}

            # Contributions that trigger an even 3-way split when ALL alliance members share it
            _EVEN_SPLIT_CONTRIBS = frozenset({
                "Did not score any points",
                "Scored few points",
                "Scored ~30% of alliance score",
            })
            # Individual percentage of alliance points awarded per contribution label
            _CONTRIB_PCT = {
                "Did not score any points":         0.00,
                "Scored few points":                0.05,
                "Scored ~30% of alliance score":    0.30,
                "Scored ~50% of alliance score":    0.50,
                "Scored ~75% of alliance score":    0.75,
                "Scored almost all alliance score": 0.90,
            }

            for entry in pm_data:
                team_nums = entry.get("team_numbers", [])
                num_teams_entry = entry.get("num_teams", 6)
                half = num_teams_entry // 2
                all_contribs = entry.get("contributions", [])

                red_contribs  = [all_contribs[i] for i in range(half)             if i < len(all_contribs)]
                blue_contribs = [all_contribs[i] for i in range(half, num_teams_entry) if i < len(all_contribs)]

                for slot_idx, contrib in enumerate(all_contribs):
                    team_id = (
                        team_nums[slot_idx]
                        if slot_idx < len(team_nums)
                        else f"Slot {slot_idx + 1}"
                    )
                    is_red = slot_idx < half
                    alliance_pts = entry["red_points"] if is_red else entry["blue_points"]
                    alliance_contribs = red_contribs if is_red else blue_contribs

                    team_contrib_map.setdefault(team_id, []).append(contrib)
                    team_pts_map.setdefault(team_id, []).append(alliance_pts)

                    # Individual average points contribution calculation
                    if contrib in ("Dedicated to passing", "Dedicated to defend"):
                        ind_pts = None  # exclude match from average
                    elif (
                        contrib in _EVEN_SPLIT_CONTRIBS
                        and len(alliance_contribs) > 0
                        and all(c == contrib for c in alliance_contribs)
                    ):
                        ind_pts = alliance_pts / len(alliance_contribs)
                    else:
                        pct = _CONTRIB_PCT.get(contrib)
                        ind_pts = alliance_pts * pct if pct is not None else None

                    if ind_pts is not None:
                        team_contrib_pts_map.setdefault(team_id, []).append(ind_pts)

            # ── Qualitative Stats table ──────────────────────────────────────────
            st.markdown("#### 📊 Qualitative Stats")

            def _pts_std(values: list) -> float:
                """Calculate sample standard deviation using Bessel's correction (n-1 denominator).
                Returns 0.0 for fewer than 2 values."""
                if len(values) < 2:
                    return 0.0
                n = len(values)
                mean = sum(values) / n
                return (sum((v - mean) ** 2 for v in values) / (n - 1)) ** 0.5

            qual_rows = []
            for team_id, contribs in sorted(
                team_contrib_map.items(),
                key=lambda x: (0, int(x[0])) if str(x[0]).isdigit() else (1, str(x[0]))
            ):
                mode_val = _contribution_mode(contribs)
                pts = team_pts_map.get(team_id, [])
                avg_pts = sum(pts) / len(pts) if pts else 0.0
                std_pts = _pts_std(pts)
                contrib_pts_list = team_contrib_pts_map.get(team_id, [])
                avg_contrib_pts = sum(contrib_pts_list) / len(contrib_pts_list) if contrib_pts_list else 0.0
                qual_rows.append({
                    "Team": get_team_display_label(team_id),
                    "Matches": len(contribs),
                    "Contribution Mode": mode_val,
                    "Avg Pts Contribution": round(avg_contrib_pts, 2),
                    "Pts Avg": round(avg_pts, 2),
                    "Pts Std": round(std_pts, 2),
                    "Weight": _CONTRIB_WEIGHTS.get(mode_val, 0),
                })
            qual_df = pd.DataFrame(qual_rows)
            qual_display = (
                qual_df
                .sort_values(by="Weight", ascending=False)
                .drop(columns=["Weight"])
                .reset_index(drop=True)
            )
            st.dataframe(qual_display, use_container_width=True, hide_index=True)

            st.markdown("---")

            # ── Per-team contribution distribution (like Detailed Stats) ─────────
            st.markdown("#### Contribution Distribution")
            all_team_ids = sorted(
                team_contrib_map.keys(),
                key=lambda x: (0, int(x)) if str(x).isdigit() else (1, str(x))
            )
            team_labels = [get_team_display_label(t) for t in all_team_ids]
            selected_label = st.selectbox(
                "Select a Team",
                options=team_labels,
                key="pm_team_contrib_selector",
            )
            if selected_label:
                sel_idx = team_labels.index(selected_label)
                sel_team_id = all_team_ids[sel_idx]
                sel_contribs = team_contrib_map[sel_team_id]
                sel_counts = Counter(sel_contribs)
                sel_df = pd.DataFrame(
                    [
                        {
                            "Contribution": k,
                            "Count": v,
                            "Percentage": f"{v / len(sel_contribs) * 100:.1f}%",
                        }
                        for k, v in sorted(
                            sel_counts.items(),
                            key=lambda x: _CONTRIB_WEIGHTS.get(x[0], 0),
                        )
                    ]
                )
                st.dataframe(sel_df, use_container_width=True, hide_index=True)

                px, go = _ensure_plotly()
                if px:
                    fig_bar = px.bar(
                        sel_df,
                        x="Contribution",
                        y="Count",
                        title=f"Contribution Distribution — {selected_label}",
                        color="Count",
                        color_continuous_scale="Purples",
                    )
                    fig_bar.update_layout(
                        plot_bgcolor='rgba(0,0,0,0)',
                        paper_bgcolor='rgba(0,0,0,0)',
                        font=dict(color='#f8fafc'),
                        xaxis=dict(color='#d1d5db', tickangle=-30),
                        yaxis=dict(color='#d1d5db', gridcolor='rgba(255,255,255,0.05)'),
                        showlegend=False,
                    )
                    st.plotly_chart(fig_bar, use_container_width=True)

            st.markdown("---")

            # ── Alliance points trend across matches ─────────────────────────────
            total_matches = len(pm_data)
            px, go = _ensure_plotly()
            if go and total_matches > 1:
                match_nums = [e["match_number"] for e in pm_data]
                red_pts = [e["red_points"] for e in pm_data]
                blue_pts = [e["blue_points"] for e in pm_data]
                fig_line = go.Figure()
                fig_line.add_trace(go.Scatter(
                    x=match_nums, y=red_pts,
                    mode='lines+markers', name='Red Alliance',
                    line=dict(color='#ef4444', width=2), marker=dict(size=7)
                ))
                fig_line.add_trace(go.Scatter(
                    x=match_nums, y=blue_pts,
                    mode='lines+markers', name='Blue Alliance',
                    line=dict(color='#3b82f6', width=2), marker=dict(size=7)
                ))
                fig_line.update_layout(
                    title='Alliance Points by Match',
                    xaxis_title='Match Number',
                    yaxis_title='Points',
                    plot_bgcolor='rgba(0,0,0,0)',
                    paper_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#f8fafc'),
                    xaxis=dict(color='#d1d5db', gridcolor='rgba(255,255,255,0.05)'),
                    yaxis=dict(color='#d1d5db', gridcolor='rgba(255,255,255,0.05)', rangemode='tozero'),
                    legend=dict(font=dict(color='#f8fafc')),
                )
                st.plotly_chart(fig_line, use_container_width=True)


# ─────────────────────────────────────────────────────────────────────────────
# System Hub  (Linux scripts / services visual panel)
# ─────────────────────────────────────────────────────────────────────────────
elif page == "🛠️ System Hub":
    import re as _re
    import shutil
    import subprocess
    import time as _time
    from pathlib import Path as _Path

    st.markdown("<div class='main-header'>🛠️ System Hub</div>", unsafe_allow_html=True)
    st.markdown("Visual control panel for Overture Linux services and scripts.")

    _SCRIPTS_DIR = _Path(__file__).resolve().parent.parent / "scripts"
    _DATA_DIR = _Path(__file__).resolve().parent.parent / "data"
    _BACKUP_DIR = _Path(__file__).resolve().parent.parent / "backups"
    _DEFAULT_CSV = _DATA_DIR / "default_scouting.csv"

    _APP_SERVICE  = "overture-app.service"
    _HID_SERVICE  = "overture-hid.service"

    _SYSTEMCTL = shutil.which("systemctl")
    _JOURNALCTL = shutil.which("journalctl")
    _HAS_SYSTEMD = _SYSTEMCTL is not None

    def _run(*args, timeout: int = 5) -> tuple[int, str]:
        """Run a command safely, returning (returncode, stdout+stderr)."""
        try:
            result = subprocess.run(
                list(args), capture_output=True, text=True,
                timeout=timeout, check=False
            )
            return result.returncode, (result.stdout + result.stderr).strip()
        except Exception as exc:
            return -1, str(exc)

    def _service_active(service: str) -> bool:
        if not _HAS_SYSTEMD:
            return False
        rc, _ = _run(_SYSTEMCTL, "is-active", "--quiet", service)
        return rc == 0

    def _service_enabled(service: str) -> bool:
        if not _HAS_SYSTEMD:
            return False
        rc, _ = _run(_SYSTEMCTL, "is-enabled", "--quiet", service)
        return rc == 0

    def _process_running(pattern: str) -> bool:
        rc, _ = _run("pgrep", "-f", pattern)
        return rc == 0

    def _status_badge(active: bool) -> str:
        return "🟢 Running" if active else "🔴 Stopped"

    # ── Tab layout ─────────────────────────────────────────────────────────
    hub_tab1, hub_tab2, hub_tab3, hub_tab4, hub_tab5 = st.tabs([
        "⚙️ Services", "💾 Data", "📡 HID Scanner", "📋 Logs", "🔄 Updates"
    ])

    # ─── Tab 1: Service Status & Control ──────────────────────────────────
    with hub_tab1:
        st.markdown("### Service Status & Control")

        if not _HAS_SYSTEMD:
            st.warning(
                "⚠️ `systemctl` not found — service control requires a Linux system "
                "with systemd. Service status is based on running processes only."
            )

        st.markdown("#### Systemd Services")
        col_a, col_b = st.columns(2)

        with col_a:
            app_active = _service_active(_APP_SERVICE)
            app_enabled = _service_enabled(_APP_SERVICE)
            st.markdown(f"**Web App** (`{_APP_SERVICE}`)")
            st.markdown(_status_badge(app_active))
            if app_enabled:
                st.caption("Auto-start: enabled")
            else:
                st.caption("Auto-start: disabled / not installed")

            btn_col1, btn_col2, btn_col3 = st.columns(3)
            with btn_col1:
                if st.button("▶ Start", key="app_start", use_container_width=True):
                    if _HAS_SYSTEMD:
                        rc, out = _run("sudo", _SYSTEMCTL, "start", _APP_SERVICE)
                        st.toast(f"start: {out or 'ok'}" if rc == 0 else f"Error: {out}")
                    else:
                        st.warning("systemctl not available.")
            with btn_col2:
                if st.button("⏹ Stop", key="app_stop", use_container_width=True):
                    if _HAS_SYSTEMD:
                        rc, out = _run("sudo", _SYSTEMCTL, "stop", _APP_SERVICE)
                        st.toast(f"stop: {out or 'ok'}" if rc == 0 else f"Error: {out}")
                    else:
                        st.warning("systemctl not available.")
            with btn_col3:
                if st.button("🔄 Restart", key="app_restart", use_container_width=True):
                    if _HAS_SYSTEMD:
                        rc, out = _run("sudo", _SYSTEMCTL, "restart", _APP_SERVICE)
                        st.toast(f"restart: {out or 'ok'}" if rc == 0 else f"Error: {out}")
                    else:
                        st.warning("systemctl not available.")

        with col_b:
            hid_active = _service_active(_HID_SERVICE)
            hid_enabled = _service_enabled(_HID_SERVICE)
            st.markdown(f"**HID Scanner** (`{_HID_SERVICE}`)")
            st.markdown(_status_badge(hid_active))
            if hid_enabled:
                st.caption("Auto-start: enabled")
            else:
                st.caption("Auto-start: disabled / not installed")

            btn_col4, btn_col5, btn_col6 = st.columns(3)
            with btn_col4:
                if st.button("▶ Start", key="hid_start_svc", use_container_width=True):
                    if _HAS_SYSTEMD:
                        rc, out = _run("sudo", _SYSTEMCTL, "start", _HID_SERVICE)
                        st.toast(f"start: {out or 'ok'}" if rc == 0 else f"Error: {out}")
                    else:
                        st.warning("systemctl not available.")
            with btn_col5:
                if st.button("⏹ Stop", key="hid_stop_svc", use_container_width=True):
                    if _HAS_SYSTEMD:
                        rc, out = _run("sudo", _SYSTEMCTL, "stop", _HID_SERVICE)
                        st.toast(f"stop: {out or 'ok'}" if rc == 0 else f"Error: {out}")
                    else:
                        st.warning("systemctl not available.")
            with btn_col6:
                if st.button("🔄 Restart", key="hid_restart_svc", use_container_width=True):
                    if _HAS_SYSTEMD:
                        rc, out = _run("sudo", _SYSTEMCTL, "restart", _HID_SERVICE)
                        st.toast(f"restart: {out or 'ok'}" if rc == 0 else f"Error: {out}")
                    else:
                        st.warning("systemctl not available.")

        st.markdown("---")
        st.markdown("#### Running Processes")
        proc_col1, proc_col2 = st.columns(2)
        with proc_col1:
            streamlit_running = _process_running(r"streamlit.*streamlit_app\.py")
            st.markdown(f"**Streamlit web process**  \n{_status_badge(streamlit_running)}")
        with proc_col2:
            hid_proc_running = _process_running("headless_interceptor.py")
            st.markdown(f"**HID capture process**  \n{_status_badge(hid_proc_running)}")

        st.markdown("---")
        st.markdown("#### Auto-start Management")
        en_col1, en_col2 = st.columns(2)
        with en_col1:
            if st.button("✅ Enable Web App auto-start", use_container_width=True, key="app_enable"):
                if _HAS_SYSTEMD:
                    rc, out = _run("sudo", _SYSTEMCTL, "enable", _APP_SERVICE)
                    st.toast("Enabled" if rc == 0 else f"Error: {out}")
                else:
                    st.warning("systemctl not available.")
            if st.button("❌ Disable Web App auto-start", use_container_width=True, key="app_disable"):
                if _HAS_SYSTEMD:
                    rc, out = _run("sudo", _SYSTEMCTL, "disable", _APP_SERVICE)
                    st.toast("Disabled" if rc == 0 else f"Error: {out}")
                else:
                    st.warning("systemctl not available.")
        with en_col2:
            if st.button("✅ Enable HID auto-start", use_container_width=True, key="hid_enable"):
                if _HAS_SYSTEMD:
                    rc, out = _run("sudo", _SYSTEMCTL, "enable", _HID_SERVICE)
                    st.toast("Enabled" if rc == 0 else f"Error: {out}")
                else:
                    st.warning("systemctl not available.")
            if st.button("❌ Disable HID auto-start", use_container_width=True, key="hid_disable"):
                if _HAS_SYSTEMD:
                    rc, out = _run("sudo", _SYSTEMCTL, "disable", _HID_SERVICE)
                    st.toast("Disabled" if rc == 0 else f"Error: {out}")
                else:
                    st.warning("systemctl not available.")

        if st.button("🔃 Refresh Status", key="refresh_status", use_container_width=False):
            st.rerun()

    # ─── Tab 2: Data Management ─────────────────────────────────────────────
    with hub_tab2:
        st.markdown("### Data Management")

        # Current data stats
        if _DEFAULT_CSV.exists():
            try:
                lines = sum(1 for _ in open(_DEFAULT_CSV, encoding='utf-8')) - 1
            except Exception:
                lines = 0
            st.success(f"✅ Scouting CSV: **{max(0, lines)} records**  \n`{_DEFAULT_CSV}`")
        else:
            st.info(f"ℹ️ No scouting data file at `{_DEFAULT_CSV}`")
            lines = 0

        st.markdown("---")
        st.markdown("#### Backup")
        backup_name_input = st.text_input(
            "Backup name (optional)", placeholder="e.g. match_day_1",
            key="backup_name_input"
        )
        if st.button("💾 Create Backup", use_container_width=False, key="do_backup"):
            if not _DEFAULT_CSV.exists() or lines <= 0:
                st.warning("No scouting data to backup.")
            else:
                _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
                ts = _time.strftime("%Y%m%d_%H%M%S")
                safe_name = "".join(c for c in backup_name_input.strip() if c.isalnum() or c in "_-")
                fname = f"{safe_name}_{ts}.csv" if safe_name else f"scouting_backup_{ts}.csv"
                dest = _BACKUP_DIR / fname
                shutil.copy2(_DEFAULT_CSV, dest)
                st.success(f"Backup created: `{dest.name}`")

        st.markdown("---")
        st.markdown("#### Available Backups")
        if _BACKUP_DIR.exists():
            backup_files = sorted(_BACKUP_DIR.glob("*.csv"), reverse=True)
            if backup_files:
                rows_bk = []
                for bf in backup_files:
                    try:
                        n = sum(1 for _ in open(bf, encoding='utf-8')) - 1
                    except Exception:
                        n = 0
                    rows_bk.append({"File": bf.name, "Records": max(0, n), "Size": f"{bf.stat().st_size // 1024} KB"})
                st.dataframe(rows_bk, use_container_width=True)

                restore_choice = st.selectbox(
                    "Select backup to restore",
                    options=[bf.name for bf in backup_files],
                    key="restore_choice"
                )
                if st.button("♻️ Restore selected backup", use_container_width=False, key="do_restore"):
                    src = _BACKUP_DIR / restore_choice
                    if src.exists():
                        _DATA_DIR.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(src, _DEFAULT_CSV)
                        st.success(f"Restored `{restore_choice}` → `{_DEFAULT_CSV.name}`")
                        if 'analizador' in st.session_state:
                            st.session_state.analizador.reload_csv()
                        st.rerun()
                    else:
                        st.error("Backup file not found.")
            else:
                st.info("No backup files found.")
        else:
            st.info("Backup directory does not exist yet.")

        st.markdown("---")
        st.markdown("#### Clear Scouting Data")
        st.warning("⚠️ This removes all scouting records. A backup will be created automatically.")
        if st.button("🗑️ Clear All Data", type="primary", key="clear_data_btn"):
            st.session_state["_hub_clear_confirm"] = True

        if st.session_state.get("_hub_clear_confirm"):
            st.error("**Are you sure?** This cannot be undone (a backup is created first).")
            conf_col1, conf_col2 = st.columns(2)
            with conf_col1:
                if st.button("✅ Yes, clear data", key="clear_confirm_yes"):
                    if _DEFAULT_CSV.exists() and lines > 0:
                        _BACKUP_DIR.mkdir(parents=True, exist_ok=True)
                        ts2 = _time.strftime("%Y%m%d_%H%M%S")
                        shutil.copy2(_DEFAULT_CSV, _BACKUP_DIR / f"pre_clear_{ts2}.csv")
                    if _DEFAULT_CSV.exists():
                        # Keep header row only
                        with open(_DEFAULT_CSV, encoding='utf-8') as fh:
                            header = fh.readline()
                        with open(_DEFAULT_CSV, 'w', encoding='utf-8') as fh:
                            fh.write(header)
                    if 'analizador' in st.session_state:
                        st.session_state.analizador.reload_csv()
                    st.session_state["_hub_clear_confirm"] = False
                    st.success("Data cleared. Header preserved, backup created.")
                    st.rerun()
            with conf_col2:
                if st.button("❌ Cancel", key="clear_confirm_no"):
                    st.session_state["_hub_clear_confirm"] = False
                    st.rerun()

    # ─── Tab 3: HID Scanner ──────────────────────────────────────────────────
    with hub_tab3:
        st.markdown("### HID Scanner")

        hid_col1, hid_col2 = st.columns(2)
        with hid_col1:
            hid_running = _process_running("headless_interceptor.py")
            st.markdown(f"**Interceptor process:** {_status_badge(hid_running)}")

        st.markdown("---")
        st.markdown("#### Available HID Devices")
        if st.button("🔍 List HID Devices", key="hid_list_btn", use_container_width=False):
            venv_python = _Path(__file__).resolve().parent.parent / ".venv" / "bin" / "python"
            python_cmd = str(venv_python) if venv_python.exists() else "python3"
            interceptor = _Path(__file__).resolve().parent / "headless_interceptor.py"
            if interceptor.exists():
                rc, out = _run(python_cmd, str(interceptor), "--list", timeout=10)
                if out:
                    st.code(out, language="text")
                else:
                    st.info("No output from interceptor list command.")
            else:
                st.error(f"Interceptor script not found: {interceptor}")

        st.markdown("---")
        st.markdown("#### Start / Stop Interceptor")

        hid_start_col, hid_stop_col = st.columns(2)
        with hid_start_col:
            if st.button("▶ Start HID Interceptor", key="hid_start_proc", use_container_width=True):
                if _HAS_SYSTEMD and hid_enabled:
                    rc, out = _run("sudo", _SYSTEMCTL, "start", _HID_SERVICE)
                    st.toast("Started via systemd" if rc == 0 else f"Error: {out}")
                else:
                    venv_python2 = _Path(__file__).resolve().parent.parent / ".venv" / "bin" / "python"
                    python_cmd2 = str(venv_python2) if venv_python2.exists() else "python3"
                    interceptor2 = _Path(__file__).resolve().parent / "headless_interceptor.py"
                    cfg = _Path(__file__).resolve().parent / "config" / "columns.json"
                    if interceptor2.exists():
                        _hid_log = _Path(__file__).resolve().parent.parent / "data" / "hid_interceptor.log"
                        _hid_log.parent.mkdir(parents=True, exist_ok=True)
                        _hid_log_fh = open(_hid_log, "a", encoding="utf-8")
                        subprocess.Popen(
                            [python_cmd2, str(interceptor2),
                             "--config", str(cfg), "--output", str(_DEFAULT_CSV)],
                            stdout=_hid_log_fh, stderr=_hid_log_fh,
                            start_new_session=True
                        )
                        st.toast(f"HID interceptor started. Logs: {_hid_log.name}")
                    else:
                        st.error("Interceptor script not found.")
        with hid_stop_col:
            if st.button("⏹ Stop HID Interceptor", key="hid_stop_proc", use_container_width=True):
                if _HAS_SYSTEMD and hid_enabled:
                    rc, out = _run("sudo", _SYSTEMCTL, "stop", _HID_SERVICE)
                    st.toast("Stopped via systemd" if rc == 0 else f"Error: {out}")
                else:
                    rc, out = _run("pkill", "-f", "headless_interceptor.py")
                    st.toast("Stopped" if rc == 0 else "Process not running or pkill failed.")

    # ─── Tab 4: Logs ────────────────────────────────────────────────────────
    with hub_tab4:
        st.markdown("### Service Logs")

        log_service_choice = st.selectbox(
            "Select service",
            options=["Web App (overture-app)", "HID Scanner (overture-hid)"],
            key="log_service_choice"
        )
        log_lines = st.slider("Lines to show", min_value=20, max_value=500, value=60, step=20, key="log_lines_slider")

        if st.button("📋 Fetch Logs", key="fetch_logs_btn", use_container_width=False):
            if not _JOURNALCTL:
                st.warning("`journalctl` not available on this system.")
            else:
                service_unit = _APP_SERVICE if "Web App" in log_service_choice else _HID_SERVICE
                rc, out = _run(
                    _JOURNALCTL, "-u", service_unit,
                    "--no-pager", f"-n{log_lines}", "--output=short",
                    timeout=10
                )
                if out.strip():
                    st.code(out, language="text")
                else:
                    st.info(f"No log output for `{service_unit}`. "
                            "The service may not be installed or has no recent entries.")

        st.markdown("---")
        st.markdown("#### Script Reference")
        ctl_script = _SCRIPTS_DIR / "overture-ctl.sh"
        if ctl_script.exists():
            st.code(f"# Run from project root:\nbash scripts/overture-ctl.sh help", language="bash")
            with st.expander("📄 View overture-ctl.sh help output"):
                rc_h, out_h = _run("bash", str(ctl_script), "help", timeout=5)
                # Strip ANSI colour codes for clean display
                out_clean = _re.sub(r'\x1b\[[0-9;]*m', '', out_h)
                st.code(out_clean, language="text")
        else:
            st.info(f"Script not found: `{ctl_script}`")

    # ─── Tab 5: Updates ──────────────────────────────────────────────────────
    with hub_tab5:
        st.markdown("### 🔄 Application Updates")
        st.markdown(
            "Check whether a newer version is available on the `main` branch "
            "and apply it with a single button."
        )

        _HUB_PROJECT_ROOT = _Path(__file__).resolve().parent.parent
        _GIT_CMD = shutil.which("git")
        _UPDATE_BRANCH = "main"

        def _current_sha() -> str:
            """Return the short SHA of the current HEAD commit."""
            if not _GIT_CMD:
                return ""
            rc, out = _run(_GIT_CMD, "-C", str(_HUB_PROJECT_ROOT), "rev-parse", "--short", "HEAD")
            return out.strip() if rc == 0 else ""

        def _remote_sha(branch: str = _UPDATE_BRANCH) -> str:
            """Fetch remote refs and return the short SHA of the remote HEAD.

            Returns empty string if fetch or rev-parse fails (e.g. offline).
            """
            if not _GIT_CMD:
                return ""
            # Refresh remote refs; ignore failure (offline / no remote)
            rc_fetch, fetch_out = _run(
                _GIT_CMD, "-C", str(_HUB_PROJECT_ROOT),
                "fetch", "--quiet", "origin", branch, timeout=20,
            )
            if rc_fetch != 0:
                print(f"[Update] git fetch failed: {fetch_out}")
                # Fall back to whatever remote ref we have cached locally
            rc, out = _run(_GIT_CMD, "-C", str(_HUB_PROJECT_ROOT),
                           "rev-parse", "--short", f"origin/{branch}")
            return out.strip() if rc == 0 else ""

        # ── One-time check per session ─────────────────────────────────────
        if not st.session_state._hub_update_checked:
            with st.spinner("Checking for updates…"):
                cur = _current_sha()
                rem = _remote_sha()
            st.session_state._hub_current_sha = cur
            st.session_state._hub_latest_sha = rem
            st.session_state._hub_update_available = bool(rem and cur and rem != cur)
            st.session_state._hub_update_checked = True

        cur_sha = st.session_state._hub_current_sha
        rem_sha = st.session_state._hub_latest_sha
        update_available = st.session_state._hub_update_available

        # Status display
        info_col1, info_col2 = st.columns(2)
        with info_col1:
            st.metric("Current version", cur_sha or "unknown")
        with info_col2:
            st.metric("Latest on main", rem_sha or "unknown")

        if not _GIT_CMD:
            st.warning("`git` not found – update management requires git to be installed.")
        elif update_available:
            st.warning(
                f"⬆️ **A new version is available** (`{rem_sha}`).  "
                "Update to get the latest features and fixes."
            )
            if st.button("⬇️ Update Now (git pull)", key="hub_update_now_btn", type="primary"):
                with st.spinner("Downloading update…"):
                    rc_pull, out_pull = _run(
                        _GIT_CMD, "-C", str(_HUB_PROJECT_ROOT),
                        "pull", "--ff-only", "origin", _UPDATE_BRANCH,
                        timeout=120,
                    )
                if rc_pull == 0:
                    st.success(
                        "✅ Update applied successfully! "
                        "Restart the app for changes to take effect."
                    )
                    # Refresh state
                    st.session_state._hub_current_sha = _current_sha()
                    st.session_state._hub_update_available = False
                    st.rerun()
                else:
                    st.error(f"Update failed:\n```\n{out_pull}\n```")
        else:
            st.success("✅ You are running the latest version.")

        st.markdown("---")
        st.markdown("#### Manual Controls")
        upd_col1, upd_col2 = st.columns(2)
        with upd_col1:
            if st.button("🔃 Re-check for updates", key="hub_recheck_btn"):
                # Reset the one-time flag so the check runs again
                st.session_state._hub_update_checked = False
                st.rerun()
        with upd_col2:
            if st.button("📋 Show recent commits", key="hub_log_btn"):
                if _GIT_CMD:
                    rc_log, out_log = _run(
                        _GIT_CMD, "-C", str(_HUB_PROJECT_ROOT),
                        "log", "--oneline", "-10", f"origin/{_UPDATE_BRANCH}",
                        timeout=15,
                    )
                    st.code(out_log, language="text")
                else:
                    st.warning("`git` not found.")


# Footer - appears on all pages
st.markdown("<hr style='margin-top: 3rem; border: 1px solid #e2e8f0;'>", unsafe_allow_html=True)
st.markdown(
    "<div class='footer'>Developed by Team Overture 7421</div>",
    unsafe_allow_html=True
)
