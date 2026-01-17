"""
Headless Engine for Alliance Simulator
Provides the AnalizadorRobot class without any GUI dependencies.
This module acts as a backend service that manages data processing,
QR decoding, and statistical calculations.
"""

import csv
import json
import math
import os
import threading
import time
from collections import Counter, defaultdict
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from pathlib import Path

from config_manager import ConfigManager
from csv_converter import CSVFormatConverter

# Base directory for resolving relative paths
BASE_DIR = Path(__file__).resolve().parent
ROOT_DIR = BASE_DIR.parent
DATA_DIR = ROOT_DIR / "data"
DEFAULT_CSV_PATH = DATA_DIR / "default_scouting.csv"


class AnalizadorRobot:
    """
    Headless data analysis engine for FRC scouting data.
    Manages data processing, statistics calculation, and team analysis
    without any GUI dependencies.
    """
    
    def __init__(self, default_column_names: Optional[List[str]] = None, 
                 config_file: str = "columnsConfig.json",
                 config_manager: Optional[ConfigManager] = None,
                 auto_load_default: bool = True):
        """
        Initialize the analyzer.

        Args:
            default_column_names: Default column names (optional, loaded from config if not provided)
            config_file: Column configuration file path
            config_manager: Optional pre-configured ConfigManager instance for dependency injection
            auto_load_default: If True, automatically load data/default_scouting.csv if it exists
        """
        # Initialize configuration manager (support dependency injection)
        if config_manager is not None:
            self.config_manager = config_manager
        else:
            self.config_manager = ConfigManager(config_file)
        
        self.csv_converter = CSVFormatConverter(self.config_manager)
        
        # Load column configuration
        column_config = self.config_manager.get_column_config()
        robot_config = self.config_manager.get_robot_valuation_config()
        
        self.default_column_names = default_column_names if default_column_names else column_config.headers
        
        # Game phase column configuration
        self._autonomous_columns: List[str] = column_config.autonomous_columns.copy()
        self._teleop_columns: List[str] = column_config.teleop_columns.copy()
        self._endgame_columns: List[str] = column_config.endgame_columns.copy()
        
        # Sheet data: List[List[str]] where first row is always the header
        self.sheet_data: List[List[str]] = []
        if self.default_column_names:
            self.sheet_data.append(list(self.default_column_names))

        # Column indices map for quick access
        self._column_indices: Dict[str, int] = {}
        self._update_column_indices()

        # User-configurable column selections
        self._selected_numeric_columns_for_overall: List[str] = column_config.numeric_for_overall.copy()
        self._selected_stats_columns: List[str] = column_config.stats_columns.copy()
        self._mode_boolean_columns: List[str] = column_config.mode_boolean_columns.copy()
        
        # Initialize column selections
        self._initialize_selected_columns()

        # Robot valuation phase weights and names
        self.robot_valuation_phase_weights: List[float] = robot_config.phase_weights.copy()
        self.robot_valuation_phase_names: List[str] = robot_config.phase_names.copy()
        
        # Hot-reload configuration
        self._csv_file_path: Optional[Path] = None
        self._csv_last_modified: float = 0.0
        self._reload_thread: Optional[threading.Thread] = None
        self._reload_stop_event = threading.Event()
        self._reload_callback: Optional[Callable[[], None]] = None
        
        # Auto-load default scouting CSV if it exists
        if auto_load_default:
            self._try_load_default_csv()

    def _update_column_indices(self) -> None:
        """Update the column name to index mapping."""
        self._column_indices.clear()
        if not self.sheet_data or not self.sheet_data[0]:
            if self.default_column_names:
                for i, col_name in enumerate(self.default_column_names):
                    self._column_indices[col_name] = i
            return

        header = self.sheet_data[0]
        for i, col_name in enumerate(header):
            self._column_indices[col_name.strip()] = i
        
        # Auto-detect game phase columns if not configured
        if not self._autonomous_columns or not self._teleop_columns or not self._endgame_columns:
            self._auto_detect_game_phase_columns()

    def _initialize_selected_columns(self) -> None:
        """Initialize selected column lists with defaults from configuration."""
        if hasattr(self, 'config_manager'):
            column_config = self.config_manager.get_column_config()
            
            current_header = self.sheet_data[0] if self.sheet_data else self.default_column_names
            
            # Filter columns that exist in current header
            self._selected_numeric_columns_for_overall = [
                col for col in column_config.numeric_for_overall if col in current_header
            ]
            self._selected_stats_columns = [
                col for col in column_config.stats_columns if col in current_header
            ]
            self._mode_boolean_columns = [
                col for col in column_config.mode_boolean_columns if col in current_header
            ]
        else:
            # Fallback to legacy behavior
            current_header = self.sheet_data[0] if self.sheet_data else self.default_column_names
            default_overall_columns = [
                'Coral L1 (Auto)', 'Coral L2 (Auto)', 'Coral L3 (Auto)', 'Coral L4 (Auto)', 
                'Coral L1 (Teleop)', 'Coral L2 (Teleop)', 'Coral L3 (Teleop)', 'Coral L4 (Teleop)',
                'Barge Algae (Auto)', 'Barge Algae (Teleop)', 'Processor Algae (Auto)', 'Processor Algae (Teleop)'
            ]
            self._selected_numeric_columns_for_overall = [
                col for col in default_overall_columns if col in current_header
            ]
            excluded_from_stats = ["Scouter Initials", "Robot"]
            self._selected_stats_columns = [
                col for col in current_header if col not in excluded_from_stats
            ]
            self._mode_boolean_columns = []

    def _auto_detect_game_phase_columns(self) -> None:
        """Auto-detect game phase columns based on keywords in names."""
        if not self.sheet_data or not self.sheet_data[0]:
            return
            
        header = self.sheet_data[0]
        
        # Keywords for identifying game phases
        autonomous_keywords = [
            'auton', 'auto', 'autonomous', 'leave', 'launch line', 'pattern matches at end of auto',
            'auto strategy', 'died/stopped moving in auto'
        ]
        teleop_keywords = [
            'teleop', 'artifact', 'overflow', 'depot', 'failed to score', 'pattern matches at end of match',
            'cycle focus', 'played defense', 'defended heavily', 'died/stopped moving in teleop'
        ]
        endgame_keywords = [
            'endgame', 'end game', 'returned to base', 'climbed on top', 'tipped', 'fell over', 'broke'
        ]
        
        if not self._autonomous_columns:
            self._autonomous_columns = []
        if not self._teleop_columns:
            self._teleop_columns = []
        if not self._endgame_columns:
            self._endgame_columns = []
            
        for col_name in header:
            col_lower = col_name.lower()
            
            if any(keyword in col_lower for keyword in autonomous_keywords):
                if col_name not in self._autonomous_columns:
                    self._autonomous_columns.append(col_name)
            elif any(keyword in col_lower for keyword in teleop_keywords):
                if col_name not in self._teleop_columns:
                    self._teleop_columns.append(col_name)
            elif any(keyword in col_lower for keyword in endgame_keywords):
                if col_name not in self._endgame_columns:
                    self._endgame_columns.append(col_name)

    # Default CSV auto-loading and hot-reload methods
    def _try_load_default_csv(self) -> bool:
        """
        Try to load the default scouting CSV file if it exists.
        
        Returns:
            True if the file was loaded successfully, False otherwise
        """
        if DEFAULT_CSV_PATH.exists():
            try:
                print(f"Auto-loading default scouting data from: {DEFAULT_CSV_PATH}")
                self.load_csv(str(DEFAULT_CSV_PATH))
                self._csv_file_path = DEFAULT_CSV_PATH
                self._csv_last_modified = DEFAULT_CSV_PATH.stat().st_mtime
                print(f"Successfully loaded {len(self.sheet_data) - 1} records from default CSV")
                return True
            except Exception as e:
                print(f"Warning: Could not auto-load default CSV: {e}")
        return False

    def get_default_csv_path(self) -> Path:
        """Get the path to the default scouting CSV file."""
        return DEFAULT_CSV_PATH

    def reload_csv(self) -> bool:
        """
        Reload the currently loaded CSV file from disk.
        Useful when the file has been modified externally (e.g., by the HID interceptor).
        
        Returns:
            True if the file was reloaded successfully, False otherwise
        """
        if not self._csv_file_path or not self._csv_file_path.exists():
            return False
        
        try:
            # Clear existing data but keep the header
            if self.default_column_names:
                self.sheet_data = [list(self.default_column_names)]
            else:
                self.sheet_data = []
            
            # Reload the file
            self.load_csv(str(self._csv_file_path))
            self._csv_last_modified = self._csv_file_path.stat().st_mtime
            return True
        except Exception as e:
            print(f"Error reloading CSV: {e}")
            return False

    def check_for_updates(self) -> bool:
        """
        Check if the currently loaded CSV file has been modified.
        
        Returns:
            True if the file has been modified since last load, False otherwise
        """
        if not self._csv_file_path or not self._csv_file_path.exists():
            return False
        
        current_mtime = self._csv_file_path.stat().st_mtime
        return current_mtime > self._csv_last_modified

    def start_hot_reload(self, interval_seconds: float = 5.0, 
                         callback: Optional[Callable[[], None]] = None) -> None:
        """
        Start a background thread that monitors the CSV file for changes.
        When changes are detected, the file is automatically reloaded.
        
        Args:
            interval_seconds: How often to check for changes (default: 5 seconds)
            callback: Optional function to call after successful reload
        """
        if self._reload_thread and self._reload_thread.is_alive():
            print("Hot reload is already running")
            return
        
        self._reload_callback = callback
        self._reload_stop_event.clear()
        
        def _monitor_loop():
            while not self._reload_stop_event.is_set():
                try:
                    if self.check_for_updates():
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] CSV file changed, reloading...")
                        if self.reload_csv():
                            print(f"Reloaded {len(self.sheet_data) - 1} records")
                            if self._reload_callback:
                                try:
                                    self._reload_callback()
                                except Exception as e:
                                    print(f"Error in reload callback: {e}")
                except Exception as e:
                    print(f"Error in hot-reload monitor: {e}")
                self._reload_stop_event.wait(interval_seconds)
        
        self._reload_thread = threading.Thread(target=_monitor_loop, daemon=True)
        self._reload_thread.start()
        print(f"Hot reload started (checking every {interval_seconds} seconds)")

    def stop_hot_reload(self) -> None:
        """Stop the background hot-reload monitoring thread."""
        self._reload_stop_event.set()
        if self._reload_thread:
            self._reload_thread.join(timeout=2.0)
            self._reload_thread = None
        print("Hot reload stopped")

    def set_csv_file_path(self, file_path: str) -> None:
        """
        Set the CSV file path for hot-reload monitoring.
        
        Args:
            file_path: Path to the CSV file to monitor
        """
        path = Path(file_path)
        if path.exists():
            self._csv_file_path = path
            self._csv_last_modified = path.stat().st_mtime

    # Game phase column setters and getters
    def set_autonomous_columns(self, column_names_list: List[str]) -> None:
        """Manually configure autonomous columns."""
        self._autonomous_columns = column_names_list.copy()
        
    def set_teleop_columns(self, column_names_list: List[str]) -> None:
        """Manually configure teleop columns."""
        self._teleop_columns = column_names_list.copy()
        
    def set_endgame_columns(self, column_names_list: List[str]) -> None:
        """Manually configure endgame columns."""
        self._endgame_columns = column_names_list.copy()
        
    def get_autonomous_columns(self) -> List[str]:
        """Get the list of autonomous columns."""
        return self._autonomous_columns.copy()
        
    def get_teleop_columns(self) -> List[str]:
        """Get the list of teleop columns."""
        return self._teleop_columns.copy()
        
    def get_endgame_columns(self) -> List[str]:
        """Get the list of endgame columns."""
        return self._endgame_columns.copy()

    def calculate_team_phase_scores(self, team_number: int) -> Dict[str, float]:
        """
        Calculate autonomous, teleop, and endgame scores for a specific team.
        Returns a dict with average scores for each phase.
        """
        team_data = self.get_team_data_grouped().get(str(team_number), [])
        if not team_data:
            return {"autonomous": 0, "teleop": 0, "endgame": 0}

        # FTC DECODE scoring path (only enabled when the sheet contains DECODE-style columns).
        if self._has_decode_columns():
            phase_totals = {"autonomous": 0.0, "teleop": 0.0, "endgame": 0.0}
            # Endgame bonus is alliance-level (+10 if both robots fully returned), so compute
            # from the entire sheet (not just this team).
            all_rows = self.sheet_data[1:] if len(self.sheet_data) > 1 else []
            endgame_bonus_by_row = self._decode_endgame_bonus_by_row_id(all_rows)
            for row in team_data:
                score = self._decode_score_row(row, endgame_bonus=endgame_bonus_by_row.get(id(row), 0.0))
                phase_totals["autonomous"] += score["autonomous"]
                phase_totals["teleop"] += score["teleop"]
                phase_totals["endgame"] += score["endgame"] + score["endgame_bonus"]

            match_count = len(team_data)
            return {
                "autonomous": phase_totals["autonomous"] / match_count if match_count else 0.0,
                "teleop": phase_totals["teleop"] / match_count if match_count else 0.0,
                "endgame": phase_totals["endgame"] / match_count if match_count else 0.0,
            }
            
        phase_scores = {"autonomous": 0.0, "teleop": 0.0, "endgame": 0.0}
        
        def parse_value(val: Any) -> Optional[float]:
            """Parse a value to float, handling booleans and strings."""
            if isinstance(val, str):
                val_lower = val.lower()
                if val_lower in ['true', 'yes', 'y', '1', 'si', 'sí']:
                    return 100.0
                elif val_lower in ['false', 'no', 'n', '0']:
                    return 0.0
                else:
                    try:
                        return float(val)
                    except ValueError:
                        return None
            elif isinstance(val, bool):
                return 100.0 if val else 0.0
            else:
                try:
                    return float(val)
                except (ValueError, TypeError):
                    return None

        def calculate_phase_score(columns: List[str]) -> float:
            """Calculate average score for a set of columns."""
            values = []
            for row in team_data:
                for col_name in columns:
                    if col_name in self._column_indices:
                        col_idx = self._column_indices[col_name]
                        if col_idx < len(row):
                            parsed = parse_value(row[col_idx])
                            if parsed is not None:
                                values.append(parsed)
            return sum(values) / len(values) if values else 0.0
        
        if self._autonomous_columns:
            phase_scores["autonomous"] = calculate_phase_score(self._autonomous_columns)
        if self._teleop_columns:
            phase_scores["teleop"] = calculate_phase_score(self._teleop_columns)
        if self._endgame_columns:
            phase_scores["endgame"] = calculate_phase_score(self._endgame_columns)
            
        return phase_scores

    # --- FTC DECODE scoring helpers ---
    def _has_decode_columns(self) -> bool:
        """Return True if the current header looks like FTC DECODE scouting schema.

        This is intentionally heuristic so the engine can support both the legacy FRC
        REEFSCAPE schema and the FTC DECODE schema without hard coupling to one JSON.
        """
        if not self.sheet_data or not self.sheet_data[0]:
            return False

        header_lower = [str(h).strip().lower() for h in self.sheet_data[0]]
        # Require at least one of these DECODE-specific concepts.
        decode_markers = (
            "artifact",
            "classified",
            "overflow",
            "depot",
            "pattern",
            "fully returned",
            "partially returned",
        )
        return any(any(marker in h for marker in decode_markers) for h in header_lower)

    def _decode_find_column(self, *, keywords: List[str]) -> Optional[str]:
        """Find the first column whose name contains all keywords (case-insensitive)."""
        if not self.sheet_data or not self.sheet_data[0]:
            return None
        keywords_lower = [k.strip().lower() for k in keywords if k and str(k).strip()]
        if not keywords_lower:
            return None
        for col in self.sheet_data[0]:
            name = str(col).strip()
            name_lower = name.lower()
            if all(k in name_lower for k in keywords_lower):
                return name
        return None

    def _decode_get_cell(self, row: List[str], col_name: Optional[str]) -> Any:
        if not col_name:
            return None
        idx = self._column_indices.get(col_name)
        if idx is None or idx >= len(row):
            return None
        return row[idx]

    def _decode_parse_float(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return float(value)
        s = str(value).strip()
        if not s:
            return None
        s_lower = s.lower()
        if s_lower in {"true", "yes", "y", "1", "si", "sí"}:
            return 1.0
        if s_lower in {"false", "no", "n", "0"}:
            return 0.0
        try:
            return float(s)
        except ValueError:
            return None

    def _decode_parse_bool(self, value: Any) -> bool:
        parsed = self._decode_parse_float(value)
        if parsed is not None:
            return parsed > 0
        s = str(value).strip().lower() if value is not None else ""
        return s in {"true", "yes", "y", "si", "sí", "x"}

    def _decode_get_count(self, row: List[str], *, primary: List[str], fallback: List[List[str]] = []) -> float:
        """Get a numeric count from the first available column.

        `primary` is an exact name candidate list.
        `fallback` is a list of keyword lists used for fuzzy matching.
        """
        for name in primary:
            if name in self._column_indices:
                val = self._decode_parse_float(self._decode_get_cell(row, name))
                return val or 0.0
        for kw in fallback:
            col = self._decode_find_column(keywords=kw)
            if col and col in self._column_indices:
                val = self._decode_parse_float(self._decode_get_cell(row, col))
                return val or 0.0
        return 0.0

    def _decode_get_endgame_status(self, row: List[str]) -> Dict[str, Any]:
        """Return endgame points and whether the robot is fully returned."""
        # Common DECODE field: end position dropdown.
        end_pos_col = None
        for exact in ("endPosition", "End Position", "End Position (Endgame)"):
            if exact in self._column_indices:
                end_pos_col = exact
                break
        if end_pos_col is None:
            end_pos_col = self._decode_find_column(keywords=["end", "position"]) or self._decode_find_column(keywords=["endgame", "position"])

        end_pos_val = str(self._decode_get_cell(row, end_pos_col) or "").strip().lower()

        partially = "partial" in end_pos_val
        fully = "full" in end_pos_val

        # Alternate schemas may have explicit booleans.
        if not (partially or fully):
            partially = self._decode_parse_bool(self._decode_get_cell(row, self._decode_find_column(keywords=["partial", "returned"]) ))
            fully = self._decode_parse_bool(self._decode_get_cell(row, self._decode_find_column(keywords=["full", "returned"]) ))

        points = 10.0 if fully else (5.0 if partially else 0.0)
        return {"points": points, "fully_returned": bool(fully)}

    def _decode_match_group_key(self, row: List[str]) -> Optional[str]:
        """Build a (match, alliance) grouping key if possible."""
        match_col = None
        for exact in ("Match Number", "matchNumber", "match_number"):
            if exact in self._column_indices:
                match_col = exact
                break
        if match_col is None:
            match_col = self._decode_find_column(keywords=["match", "number"])

        alliance_col = None
        for exact in ("Alliance", "Alliance Color", "Future Alliance"):
            if exact in self._column_indices:
                alliance_col = exact
                break
        if alliance_col is None:
            alliance_col = self._decode_find_column(keywords=["alliance"])

        if not match_col or not alliance_col:
            return None

        match_raw = str(self._decode_get_cell(row, match_col) or "").strip()
        alliance_raw = str(self._decode_get_cell(row, alliance_col) or "").strip().lower()
        if not match_raw or not alliance_raw:
            return None
        return f"{match_raw}|{alliance_raw}"

    def _decode_endgame_bonus_by_row_id(self, rows: List[List[str]]) -> Dict[int, float]:
        """Compute +10 DECODE bonus when 2 robots are fully returned.

        The bonus is split across the two robots (+5 each) when we can identify
        (match, alliance) groups.
        """
        by_group: Dict[str, List[List[str]]] = defaultdict(list)
        for row in rows:
            key = self._decode_match_group_key(row)
            if key:
                by_group[key].append(row)

        bonus_by_row_id: Dict[int, float] = {}
        for group_rows in by_group.values():
            fully_flags = [self._decode_get_endgame_status(r)["fully_returned"] for r in group_rows]
            if fully_flags.count(True) >= 2:
                # Exactly two robots in FTC alliances; if we have more (bad data), still cap at 2.
                bonus_split = 10.0 / 2.0
                applied = 0
                for r, is_full in zip(group_rows, fully_flags):
                    if is_full and applied < 2:
                        bonus_by_row_id[id(r)] = bonus_split
                        applied += 1
        return bonus_by_row_id

    def _decode_score_row(self, row: List[str], *, endgame_bonus: float = 0.0) -> Dict[str, float]:
        """Compute DECODE points for a single robot/match row."""
        # Autonomous
        auto_leave = 1.0 if self._decode_parse_bool(self._decode_get_cell(row, self._decode_find_column(keywords=["auto", "leave"]) )
                                                    or self._decode_get_cell(row, self._decode_find_column(keywords=["auto", "moved"]) )) else 0.0
        auto_artifacts = self._decode_get_count(
            row,
            primary=["artifactsAuto", "Artifacts (Auto)", "Classified (Auto)", "Artifacts Auto", "Classified Auto"],
            fallback=[["auto", "artifact"], ["auto", "classified"]],
        )
        auto_overflow = self._decode_get_count(
            row,
            primary=["overflowAuto", "Overflow (Auto)", "Overflow Auto"],
            fallback=[["auto", "overflow"]],
        )
        auto_depot = self._decode_get_count(
            row,
            primary=["depotAuto", "Depot (Auto)", "Depot Auto"],
            fallback=[["auto", "depot"]],
        )
        auto_pattern = self._decode_get_count(
            row,
            primary=["patternAuto", "Pattern (Auto)", "Pattern Match (Auto)", "Pattern Auto"],
            fallback=[["auto", "pattern"]],
        )
        autonomous = 3.0 * auto_leave + 3.0 * auto_artifacts + 1.0 * auto_overflow + 1.0 * auto_depot + 2.0 * auto_pattern

        # TeleOp
        teleop_artifacts = self._decode_get_count(
            row,
            primary=["artifactsTeleop", "Artifacts (Teleop)", "Classified (Teleop)", "Artifacts Teleop", "Classified Teleop"],
            fallback=[["teleop", "artifact"], ["teleop", "classified"], ["tele", "artifact"], ["tele", "classified"]],
        )
        teleop_overflow = self._decode_get_count(
            row,
            primary=["overflowTeleop", "Overflow (Teleop)", "Overflow Teleop"],
            fallback=[["teleop", "overflow"], ["tele", "overflow"]],
        )
        teleop_depot = self._decode_get_count(
            row,
            primary=["depotTeleop", "Depot (Teleop)", "Depot Teleop"],
            fallback=[["teleop", "depot"], ["tele", "depot"]],
        )
        teleop_pattern = self._decode_get_count(
            row,
            primary=["patternTeleop", "Pattern (Teleop)", "Pattern Match (Teleop)", "Pattern Teleop"],
            fallback=[["teleop", "pattern"], ["tele", "pattern"]],
        )
        teleop = 3.0 * teleop_artifacts + 1.0 * teleop_overflow + 1.0 * teleop_depot + 2.0 * teleop_pattern

        # Endgame
        endgame_status = self._decode_get_endgame_status(row)
        endgame = float(endgame_status["points"])

        total = autonomous + teleop + endgame + float(endgame_bonus or 0.0)
        return {
            "autonomous": autonomous,
            "teleop": teleop,
            "endgame": endgame,
            "endgame_bonus": float(endgame_bonus or 0.0),
            "total": total,
        }

    def _find_potential_numeric_columns(self, header: List[str], 
                                         sample_data_row: Optional[List[str]] = None) -> List[str]:
        """Guess which columns are numeric based on sample data."""
        potential_columns = []
        if not sample_data_row:
            return potential_columns

        excluded_keywords = [
            'Team Number', 'Match Number', 'Scouter', 'Name', 'Defense?', 
            'Did ', 'Was ', 'Played ', 'Card', 'Climbed', 'Tipped', 'Died'
        ]

        for idx, col_name in enumerate(header):
            if any(keyword.lower() in col_name.lower() for keyword in excluded_keywords):
                continue
            
            if idx < len(sample_data_row):
                try:
                    float(sample_data_row[idx])
                    potential_columns.append(col_name)
                except (ValueError, TypeError):
                    pass
        return potential_columns

    def _find_potential_boolean_columns(self, header: List[str], 
                                         sample_data_row: Optional[List[str]] = None) -> List[str]:
        """Guess which columns are boolean based on column names."""
        potential_columns = []
        boolean_keywords = ['?', 'did', 'was', 'played', 'climbed', 'card', 'tipped', 'foul', 'worked', 'something', 'defended']
        excluded_from_boolean = ['Team Number', 'Match Number', 'Scouter', 'Name', 'Coral L', 'Algae Scored']
        
        numeric_cols = []
        if self.sheet_data and len(self.sheet_data) > 1:
            numeric_cols = self._find_potential_numeric_columns(header, self.sheet_data[1])
        elif sample_data_row:
            numeric_cols = self._find_potential_numeric_columns(header, sample_data_row)

        for col_name in header:
            col_name_lower = col_name.lower()
            
            if any(ex_keyword.lower() in col_name_lower for ex_keyword in excluded_from_boolean):
                continue
            
            if col_name in numeric_cols:
                continue

            if any(keyword.lower() in col_name_lower for keyword in boolean_keywords):
                potential_columns.append(col_name)

        return list(set(potential_columns))

    def update_header(self, new_header_str: str) -> None:
        """Update column header names from a comma-separated string."""
        new_header = [name.strip() for name in new_header_str.split(',')]
        if not self.sheet_data:
            self.sheet_data.append(new_header)
        else:
            self.sheet_data[0] = new_header
        self._update_column_indices()
        self._initialize_selected_columns()
        print(f"Header updated to: {self.sheet_data[0]}")

    def load_csv(self, file_path: str) -> None:
        """
        Load a CSV file, auto-detecting format and converting if necessary.
        
        Args:
            file_path: Path to the CSV file
        """
        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                csv_rows = [row for row in reader if any(field.strip() for field in row)]

            if not csv_rows:
                print("CSV file is empty or contains no data.")
                return

            csv_headers = csv_rows[0]
            
            # Detect CSV format
            detected_format = self.config_manager.detect_csv_format(csv_headers)
            
            if detected_format == "legacy_format":
                print("Detected legacy format. Converting to new format...")
                
                converted_rows = self.csv_converter.convert_rows_to_new_format(csv_headers, csv_rows[1:])
                csv_rows = [self.config_manager.get_column_config().headers] + converted_rows
                
                print(f"Successfully converted {len(converted_rows)} data rows to new format.")
                
                # Optionally save converted file
                converted_file_path = file_path.replace('.csv', '_converted.csv')
                with open(converted_file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerows(csv_rows)
                print(f"Saved converted file as: {converted_file_path}")
                
            elif detected_format == "unknown_format":
                print("Warning: Unknown CSV format detected. Loading as-is, but some features may not work correctly.")
            else:
                print("CSV file is already in the correct format.")

            # Handle data loading
            if not self.sheet_data or (len(self.sheet_data) == 1 and not any(self.sheet_data[0])): 
                self.sheet_data = csv_rows
                print(f"CSV data loaded. {len(self.sheet_data)} rows (including header).")
            else:
                current_header = self.sheet_data[0]
                csv_header = csv_rows[0]
                if current_header == csv_header:
                    self.sheet_data.extend(csv_rows[1:])
                    print(f"CSV data appended. Total {len(self.sheet_data)} rows.")
                else:
                    expected_header = self.config_manager.get_column_config().headers
                    if csv_header == expected_header:
                        self.sheet_data = csv_rows
                        print("CSV header matches config. Replaced existing data and headers.")
                    else:
                        print("Warning: CSV header doesn't match existing data. Appending data rows only.")
                        target_len = len(current_header)
                        for row in csv_rows[1:]:
                            if len(row) < target_len:
                                row = row + [""] * (target_len - len(row))
                            elif len(row) > target_len:
                                row = row[:target_len]
                            self.sheet_data.append(row)
            
            self._update_column_indices()
            self._initialize_selected_columns()
        except FileNotFoundError:
            print(f"Error: File not found at {file_path}")
        except Exception as e:
            print(f"Error loading CSV: {e}")

    def load_qr_data(self, qr_string_data: str) -> None:
        """
        Process data from QR code strings.
        Handles different formats: plain text, CSV, or tab-separated.
        Adds data as new rows to the raw data table.
        """
        if not qr_string_data.strip():
            print("QR data is empty.")
            return

        print(f"Processing QR data: {qr_string_data}")

        # Ensure we have a header
        if not self.sheet_data or not self.sheet_data[0]:
            if self.default_column_names:
                self.sheet_data = [list(self.default_column_names)]
                print(f"Initialized with default header: {len(self.default_column_names)} columns")
            else:
                print("Error: No header defined for QR data.")
                return

        current_headers = self.sheet_data[0]
        num_columns = len(current_headers)

        lines = qr_string_data.strip().split('\n')
        new_rows_added = 0

        for line in lines:
            if not line.strip():
                continue

            row_data = None

            # Method 1: Tab-separated
            if '\t' in line:
                row_data = [field.strip() for field in line.split('\t')]
            # Method 2: CSV
            elif ',' in line and line.count(',') >= 2:
                row_data = [field.strip() for field in line.split(',')]
            # Method 3: Semicolon-separated
            elif ';' in line:
                row_data = [field.strip() for field in line.split(';')]
            # Method 4: Plain text
            else:
                row_data = [line.strip()]
                while len(row_data) < num_columns:
                    row_data.append("")

            if row_data:
                # Pad with empty strings if needed
                while len(row_data) < num_columns:
                    row_data.append("")
                
                # Truncate if too many fields
                if len(row_data) > num_columns:
                    row_data = row_data[:num_columns]

                self.sheet_data.append(row_data)
                new_rows_added += 1
                print(f"Row added: {row_data}")

        print(f"QR data processed. {new_rows_added} rows added. Total: {len(self.sheet_data)} rows.")
        self._update_column_indices()
        self._initialize_selected_columns()

    # --- Statistical Calculation Functions ---
    def _average(self, values: List[float]) -> float:
        """Calculate the average of a list of numbers."""
        if not values:
            return 0.0
        return sum(values) / len(values)

    def _standard_deviation(self, values: List[float]) -> float:
        """Calculate the standard deviation of a list of numbers."""
        if not values or len(values) < 1:
            return 0.0
        n = len(values)
        mean = self._average(values)
        sum_sq_diff = sum((x - mean) ** 2 for x in values)
        if n == 0:
            return 0.0
        return math.sqrt(sum_sq_diff / n)

    def _calculate_mode(self, values: List[str]) -> str:
        """Calculate the mode of a list of strings."""
        if not values:
            return 'N/A'
        non_empty_values = [v for v in values if str(v).strip()]
        if not non_empty_values:
            return 'N/A'
        
        counts = Counter(non_empty_values)
        max_freq = counts.most_common(1)[0][1]
        modes = [val for val, freq in counts.items() if freq == max_freq]
        return modes[0]

    def _rate_from_strs(self, str_vals: List[str]) -> float:
        """Calculate rate from boolean string values."""
        true_like = {'true', 'yes', 'y', '1', 'si', 'sí', 'verdadero'}
        false_like = {'false', 'no', 'n', '0', 'falso'}
        bools = []
        for s in str_vals:
            lv = s.lower()
            if lv in true_like:
                bools.append(1.0)
            elif lv in false_like:
                bools.append(0.0)
        return self._average(bools) if bools else 0.0

    def get_raw_data(self) -> List[List[str]]:
        """Return the raw sheet data."""
        return self.sheet_data

    def set_raw_data(self, sheet_data: List[List[str]]) -> None:
        """Replace the raw sheet data and refresh column mappings."""
        if not sheet_data:
            return
        self.sheet_data = sheet_data
        self._update_column_indices()
        self._initialize_selected_columns()

    def get_team_data_grouped(self) -> Dict[str, List[List[str]]]:
        """Group rows by team number."""
        if len(self.sheet_data) < 2:
            return {}
        team_number_col_name = "Team Number"
        if team_number_col_name not in self._column_indices:
            if "Team" in self._column_indices:
                team_number_col_name = "Team"
            else:
                return {}
        team_col_idx = self._column_indices[team_number_col_name]
        team_rows_map: Dict[str, List[List[str]]] = defaultdict(list)
        for row in self.sheet_data[1:]:
            if team_col_idx < len(row):
                team_number = row[team_col_idx].strip()
                if team_number:
                    team_rows_map[team_number].append(row)
        return dict(team_rows_map)

    def _generate_stat_key(self, col_name: str, stat_type: str) -> str:
        """Generate a standardized key for statistics."""
        if col_name in ['teleop_coral', 'teleop_algae']:
            return f'{col_name}_{stat_type}'
        base = col_name.replace('?', '') \
                       .replace('(Disloged NO COUNT)', '') \
                       .replace('(Disloged DOES NOT COUNT)', '') \
                       .replace('(Auto)', '') \
                       .replace('(Teleop)', '') \
                       .replace('/', '_') \
                       .replace(' ', '_') \
                       .lower()
        specific_renames = {
            'End Position': 'climb',
            'Climbed?': 'climb',
            'Did something?': 'auto_did_something',
            'Did Foul?': 'auto_did_foul',
            'Did auton worked?': 'auto_worked',
            'Moved (Auto)': 'auto_worked',
            'Barge Algae Scored': 'teleop_barge_algae',
            'Barge Algae (Teleop)': 'teleop_barge_algae',
            'Algae Scored in Barge': 'teleop_barge_algae',
            'Processor Algae Scored': 'teleop_processor_algae',
            'Processor Algae (Teleop)': 'teleop_processor_algae',
            'Played Algae?(Disloged NO COUNT)': 'teleop_played_algae',
            'Played Algae?(Disloged DOES NOT COUNT)': 'teleop_played_algae',
            'Crossed Feild/Played Defense?': 'teleop_crossed_played_defense',
            'Crossed Field/Defense': 'teleop_crossed_played_defense',
            'Was the robot Defended by alguien?': 'defended_by_other'
        }
        if col_name in specific_renames:
            base = specific_renames[col_name]
        return f'{base}_{stat_type}'

    def get_detailed_team_stats(self) -> List[Dict[str, Any]]:
        """Process and return detailed statistics for all teams."""
        if len(self.sheet_data) < 2:
            return []
        team_data_grouped = self.get_team_data_grouped()
        if not team_data_grouped:
            return []
        detailed_stats_list = []
        
        # Coral/algae column groups supporting both formats
        coral_algae_groups = {
            'teleop_coral': [
                'Coral L1 (Teleop)', 'Coral L2 (Teleop)',
                'Coral L3 (Teleop)', 'Coral L4 (Teleop)',
                'Coral L1 Scored', 'Coral L2 Scored',
                'Coral L3 Scored', 'Coral L4 Scored'
            ],
            'teleop_algae': [
                'Barge Algae (Teleop)', 'Processor Algae (Teleop)',
                'Algae Scored in Barge'
            ]
        }
        
        for team_number, rows in team_data_grouped.items():
            team_stats: Dict[str, Any] = {'team': team_number}
            
            # Process coral and algae groups
            for group_name, columns in coral_algae_groups.items():
                group_values = []
                for col_name in columns:
                    col_idx = self._column_indices.get(col_name)
                    if col_idx is None:
                        continue
                    for row in rows:
                        if col_idx < len(row):
                            try:
                                group_values.append(float(row[col_idx]))
                            except Exception:
                                pass
                avg_key = self._generate_stat_key(group_name, 'avg')
                std_key = self._generate_stat_key(group_name, 'std')
                team_stats[avg_key] = self._average(group_values) if group_values else 0.0
                team_stats[std_key] = self._standard_deviation(group_values) if group_values else 0.0
            
            # Individual numeric columns
            individual_numeric_columns = []
            for columns in coral_algae_groups.values():
                individual_numeric_columns.extend(columns)
            individual_numeric_columns = list(set(individual_numeric_columns))
            
            for col_name in individual_numeric_columns:
                col_idx = self._column_indices.get(col_name)
                if col_idx is None:
                    continue
                values = []
                for row in rows:
                    if col_idx < len(row):
                        try:
                            values.append(float(row[col_idx]))
                        except Exception:
                            pass
                avg_key = self._generate_stat_key(col_name, 'avg')
                std_key = self._generate_stat_key(col_name, 'std')
                team_stats[avg_key] = self._average(values) if values else 0.0
                team_stats[std_key] = self._standard_deviation(values) if values else 0.0
            
            # Defense rate
            defense_col = 'Crossed Field/Defense'
            defense_idx = self._column_indices.get(defense_col)
            if defense_idx is None:
                defense_col = 'Crossed Feild/Played Defense?'
                defense_idx = self._column_indices.get(defense_col)
            
            defense_values = []
            if defense_idx is not None:
                for row in rows:
                    if defense_idx < len(row):
                        v = row[defense_idx].strip().lower()
                        if v in ['true', 'yes', 'y', '1']:
                            defense_values.append(1.0)
                        elif v in ['false', 'no', 'n', '0']:
                            defense_values.append(0.0)
                defense_key = self._generate_stat_key(defense_col, 'rate')
                team_stats[defense_key] = self._average(defense_values) if defense_values else 0.0
            
            # Enhanced overall calculation
            overall_values = []
            coral_values = []
            algae_values = []

            decode_bonus_by_row_id: Dict[int, float] = {}
            if self._has_decode_columns():
                decode_bonus_by_row_id = self._decode_endgame_bonus_by_row_id(self.sheet_data[1:])

            for row in rows:
                match_score = 0.0

                if self._has_decode_columns():
                    match_score = self._decode_score_row(
                        row,
                        endgame_bonus=decode_bonus_by_row_id.get(id(row), 0.0),
                    )["total"]
                    if match_score > 0:
                        overall_values.append(match_score)
                    continue
                
                # Coral scoring with level-based weights
                coral_weights = {'L1': 2, 'L2': 3, 'L3': 4, 'L4': 5}
                for level, weight in coral_weights.items():
                    # Auto coral
                    auto_col = f'Coral {level} (Auto)'
                    auto_idx = self._column_indices.get(auto_col)
                    if auto_idx is not None and auto_idx < len(row):
                        try:
                            auto_val = float(row[auto_idx])
                            match_score += auto_val * weight * 2
                            coral_values.append(auto_val * weight * 2)
                        except Exception:
                            pass
                    
                    # Teleop coral
                    teleop_col = f'Coral {level} (Teleop)'
                    teleop_idx = self._column_indices.get(teleop_col)
                    if teleop_idx is not None and teleop_idx < len(row):
                        try:
                            teleop_val = float(row[teleop_idx])
                            match_score += teleop_val * weight
                            coral_values.append(teleop_val * weight)
                        except Exception:
                            pass
                    
                    # Legacy format fallback
                    legacy_col = f'Coral {level} Scored'
                    legacy_idx = self._column_indices.get(legacy_col)
                    if legacy_idx is not None and legacy_idx < len(row) and auto_idx is None and teleop_idx is None:
                        try:
                            legacy_val = float(row[legacy_idx])
                            match_score += legacy_val * weight * 1.5
                            coral_values.append(legacy_val * weight * 1.5)
                        except Exception:
                            pass
                
                # Algae scoring
                algae_configs = [
                    ('Barge Algae (Auto)', 3 * 1.5),
                    ('Barge Algae (Teleop)', 3),
                    ('Processor Algae (Auto)', 6 * 1.5),
                    ('Processor Algae (Teleop)', 6),
                    ('Algae Scored in Barge', 3)
                ]
                
                for col_name, points in algae_configs:
                    col_idx = self._column_indices.get(col_name)
                    if col_idx is not None and col_idx < len(row):
                        try:
                            val = float(row[col_idx])
                            match_score += val * points
                            algae_values.append(val * points)
                        except Exception:
                            pass
                
                # Endgame scoring
                end_pos_idx = self._column_indices.get('End Position')
                climb_idx = self._column_indices.get('Climbed?')
                
                if end_pos_idx is not None and end_pos_idx < len(row):
                    end_pos = str(row[end_pos_idx]).strip().lower()
                    if 'deep' in end_pos:
                        match_score += 12
                    elif 'shallow' in end_pos:
                        match_score += 6
                    elif 'park' in end_pos:
                        match_score += 2
                elif climb_idx is not None and climb_idx < len(row):
                    try:
                        climb_val = float(row[climb_idx])
                        if climb_val > 0:
                            match_score += 8
                    except Exception:
                        pass
                
                if match_score > 0:
                    overall_values.append(match_score)
            
            team_stats['overall_avg'] = self._average(overall_values) if overall_values else 0.0
            team_stats['overall_std'] = self._standard_deviation(overall_values) if overall_values else 0.0
            
            # Boolean columns: rate and mode
            for col_name in self._selected_stats_columns:
                if col_name in individual_numeric_columns or col_name in ['Team Number', 'Match Number']:
                    continue
                col_idx = self._column_indices.get(col_name)
                if col_idx is None:
                    continue
                str_vals = [row[col_idx] for row in rows if col_idx < len(row)]
                rate_key = self._generate_stat_key(col_name, 'rate')
                team_stats[rate_key] = self._rate_from_strs(str_vals)
                if col_name in self._mode_boolean_columns:
                    mode_key = self._generate_stat_key(col_name, 'mode')
                    team_stats[mode_key] = self._calculate_mode(str_vals)
            
            # Robot valuation
            team_stats['RobotValuation'] = self._robot_valuation(rows)
            detailed_stats_list.append(team_stats)
        
        detailed_stats_list.sort(key=lambda x: (x.get('overall_avg', 0.0), -x.get('overall_std', float('inf'))), reverse=True)
        return detailed_stats_list

    def get_defensive_robot_ranking(self) -> List[Dict[str, Any]]:
        """Get defensive robot ranking."""
        all_team_stats = self.get_detailed_team_stats()
        if not all_team_stats:
            return []
        defense_col_name = "Crossed Feild/Played Defense?"
        defense_rate_key = self._generate_stat_key(defense_col_name, 'rate')
        died_col_name = "Died?"
        moved_col_name = "Did something?"
        died_rate_key = self._generate_stat_key(died_col_name, 'rate')
        moved_rate_key = self._generate_stat_key(moved_col_name, 'rate')
        defensive_ranking = []
        for stats in all_team_stats:
            current_defense_rate = stats.get(defense_rate_key, 0.0)
            if current_defense_rate > 0:
                rank_entry = {
                    'team': stats['team'],
                    'defense_rate': current_defense_rate,
                    'overall_avg': stats.get('overall_avg', 0.0),
                    'died_rate': stats.get(died_rate_key, 0.0),
                    'moved_rate': stats.get(moved_rate_key, 0.0)
                }
                defensive_ranking.append(rank_entry)
        defensive_ranking.sort(key=lambda x: x['defense_rate'], reverse=True)
        return defensive_ranking

    # --- Column configuration setters ---
    def set_selected_numeric_columns_for_overall(self, column_names_list: List[str]) -> None:
        """Set numeric columns for overall calculation."""
        self._selected_numeric_columns_for_overall = [
            name for name in column_names_list if name in self._column_indices
        ]
        print(f"Columns for overall average: {self._selected_numeric_columns_for_overall}")

    def set_selected_stats_columns(self, column_names_list: List[str]) -> None:
        """Set columns for stats table."""
        self._selected_stats_columns = [
            name for name in column_names_list if name in self._column_indices
        ]
        print(f"Columns for stats table: {self._selected_stats_columns}")

    def set_mode_boolean_columns(self, column_names_list: List[str]) -> None:
        """Set boolean columns for mode calculation."""
        self._mode_boolean_columns = [
            name for name in column_names_list if name in self._column_indices
        ]
        print(f"Columns for mode calculation: {self._mode_boolean_columns}")

    def get_current_headers(self) -> List[str]:
        """Return current column headers."""
        return list(self.sheet_data[0]) if self.sheet_data and self.sheet_data[0] else list(self.default_column_names)

    def set_robot_valuation_phase_weights(self, weights: List[float]) -> None:
        """Set weights for Q1, Q2, Q3 phases. Must be 3 floats summing to 1.0."""
        if len(weights) != 3 or not all(isinstance(w, (float, int)) for w in weights):
            raise ValueError("Weights must be a list of 3 numbers.")
        total = sum(weights)
        if not (0.99 < total < 1.01):
            raise ValueError("Weights must sum to 1.0")
        self.robot_valuation_phase_weights = [float(w) for w in weights]

    def save_configuration(self) -> None:
        """Save current configuration to file."""
        if hasattr(self, 'config_manager'):
            self.config_manager.update_column_config(
                numeric_for_overall=self._selected_numeric_columns_for_overall,
                stats_columns=self._selected_stats_columns,
                mode_boolean_columns=self._mode_boolean_columns,
                autonomous_columns=self._autonomous_columns,
                teleop_columns=self._teleop_columns,
                endgame_columns=self._endgame_columns
            )
            self.config_manager.update_robot_valuation_config(
                phase_weights=self.robot_valuation_phase_weights,
                phase_names=self.robot_valuation_phase_names
            )
            self.config_manager.save_configuration()
            print("Configuration saved successfully.")
        else:
            print("Warning: No configuration manager available.")

    def get_available_presets(self) -> Dict:
        """Get available configuration presets."""
        if hasattr(self, 'config_manager'):
            return self.config_manager.get_configuration_presets()
        return {}

    def apply_configuration_preset(self, preset_name: str) -> None:
        """Apply a configuration preset."""
        if hasattr(self, 'config_manager'):
            self.config_manager.apply_preset(preset_name)
            column_config = self.config_manager.get_column_config()
            robot_config = self.config_manager.get_robot_valuation_config()
            
            self._selected_numeric_columns_for_overall = column_config.numeric_for_overall.copy()
            self._selected_stats_columns = column_config.stats_columns.copy()
            self._mode_boolean_columns = column_config.mode_boolean_columns.copy()
            self._autonomous_columns = column_config.autonomous_columns.copy()
            self._teleop_columns = column_config.teleop_columns.copy()
            self._endgame_columns = column_config.endgame_columns.copy()
            self.robot_valuation_phase_weights = robot_config.phase_weights.copy()
            self.robot_valuation_phase_names = robot_config.phase_names.copy()
            
            print(f"Applied configuration preset: {preset_name}")
        else:
            print("Warning: No configuration manager available.")

    def get_robot_valuation_phase_weights(self) -> List[float]:
        """Get current robot valuation phase weights."""
        return list(self.robot_valuation_phase_weights)

    def _split_rows_into_phases(self, rows: List[List[str]]) -> List[List[List[str]]]:
        """Split rows into 3 phases (Q1, Q2, Q3) as evenly as possible."""
        n = len(rows)
        if n == 0:
            return [[], [], []]
        q1_end = n // 3
        q2_end = 2 * n // 3
        q1 = rows[:q1_end]
        q2 = rows[q1_end:q2_end]
        q3 = rows[q2_end:]
        return [q1, q2, q3]

    def _robot_valuation(self, rows: List[List[str]]) -> float:
        """Calculate RobotValuation using enhanced weighted scoring across phases."""
        if not rows:
            return 0.0

        decode_bonus_by_row_id: Dict[int, float] = {}
        if self._has_decode_columns() and len(self.sheet_data) > 1:
            decode_bonus_by_row_id = self._decode_endgame_bonus_by_row_id(self.sheet_data[1:])
        
        phases = self._split_rows_into_phases(rows)
        phase_weights = self.robot_valuation_phase_weights
        phase_scores = []
        
        for phase_rows in phases:
            phase_total = 0.0
            match_count = len(phase_rows)
            
            if match_count == 0:
                phase_scores.append(0.0)
                continue
            
            for row in phase_rows:
                match_score = 0.0

                if self._has_decode_columns():
                    match_score = self._decode_score_row(
                        row,
                        endgame_bonus=decode_bonus_by_row_id.get(id(row), 0.0),
                    )["total"]
                    phase_total += match_score
                    continue
                
                # Coral scoring with level-based weights
                coral_weights = {'L1': 2, 'L2': 3, 'L3': 4, 'L4': 5}
                for level, weight in coral_weights.items():
                    # Auto coral
                    auto_col = f'Coral {level} (Auto)'
                    auto_idx = self._column_indices.get(auto_col)
                    if auto_idx is not None and auto_idx < len(row):
                        try:
                            auto_val = float(row[auto_idx])
                            match_score += auto_val * weight * 2.0
                        except Exception:
                            pass
                    
                    # Teleop coral
                    teleop_col = f'Coral {level} (Teleop)'
                    teleop_idx = self._column_indices.get(teleop_col)
                    if teleop_idx is not None and teleop_idx < len(row):
                        try:
                            teleop_val = float(row[teleop_idx])
                            match_score += teleop_val * weight
                        except Exception:
                            pass
                    
                    # Legacy format fallback
                    legacy_col = f'Coral {level} Scored'
                    legacy_idx = self._column_indices.get(legacy_col)
                    if legacy_idx is not None and legacy_idx < len(row) and auto_idx is None and teleop_idx is None:
                        try:
                            legacy_val = float(row[legacy_idx])
                            match_score += legacy_val * weight * 1.5
                        except Exception:
                            pass
                
                # Algae scoring
                algae_configs = [
                    ('Barge Algae (Auto)', 4.5),
                    ('Barge Algae (Teleop)', 3),
                    ('Processor Algae (Auto)', 9),
                    ('Processor Algae (Teleop)', 6),
                    ('Algae Scored in Barge', 3)
                ]
                
                for col_name, points in algae_configs:
                    col_idx = self._column_indices.get(col_name)
                    if col_idx is not None and col_idx < len(row):
                        try:
                            val = float(row[col_idx])
                            match_score += val * points
                        except Exception:
                            pass
                
                # Endgame scoring
                end_pos_idx = self._column_indices.get('End Position')
                climb_idx = self._column_indices.get('Climbed?')
                
                if end_pos_idx is not None and end_pos_idx < len(row):
                    end_pos = str(row[end_pos_idx]).strip().lower()
                    if 'deep' in end_pos:
                        match_score += 12
                    elif 'shallow' in end_pos:
                        match_score += 6
                    elif 'park' in end_pos:
                        match_score += 2
                elif climb_idx is not None and climb_idx < len(row):
                    try:
                        climb_val = float(row[climb_idx])
                        if climb_val > 0:
                            match_score += 8
                    except Exception:
                        pass
                
                # Defense/activity bonus
                defense_idx = self._column_indices.get('Crossed Field/Defense')
                if defense_idx is None:
                    defense_idx = self._column_indices.get('Crossed Feild/Played Defense?')
                
                if defense_idx is not None and defense_idx < len(row):
                    defense_val = str(row[defense_idx]).strip().lower()
                    if defense_val in ['true', 'yes', 'y', '1']:
                        match_score += 5
                
                # Auto movement bonus
                auto_moved_idx = self._column_indices.get('Moved (Auto)')
                if auto_moved_idx is None:
                    auto_moved_idx = self._column_indices.get('Did something?')
                
                if auto_moved_idx is not None and auto_moved_idx < len(row):
                    moved_val = str(row[auto_moved_idx]).strip().lower()
                    if moved_val in ['true', 'yes', 'y', '1']:
                        match_score += 3
                
                phase_total += match_score
            
            phase_avg = phase_total / match_count if match_count > 0 else 0.0
            phase_scores.append(phase_avg)
        
        final_score = sum(w * s for w, s in zip(phase_weights, phase_scores))
        return final_score

    def get_team_match_performance(self, team_numbers: Optional[List[str]] = None) -> Dict[str, List[tuple]]:
        """
        Returns a dict: {team_number: [(match_number, overall_for_that_match), ...]}
        """
        if len(self.sheet_data) < 2:
            return {}
        team_col = self._column_indices.get("Team Number")
        match_col = self._column_indices.get("Match Number")
        if team_col is None or match_col is None:
            return {}
        
        perf: Dict[str, List[tuple]] = {}
        decode_bonus_by_row_id: Dict[int, float] = {}
        if self._has_decode_columns() and len(self.sheet_data) > 1:
            decode_bonus_by_row_id = self._decode_endgame_bonus_by_row_id(self.sheet_data[1:])
        for row in self.sheet_data[1:]:
            if team_col >= len(row) or match_col >= len(row):
                continue
            team = row[team_col].strip()
            match = row[match_col].strip()
            if not team or not match:
                continue
            try:
                match_num = int(match)
            except Exception:
                continue
            
            if self._has_decode_columns():
                overall = self._decode_score_row(
                    row,
                    endgame_bonus=decode_bonus_by_row_id.get(id(row), 0.0),
                )["total"]
            else:
                vals = []
                for col_name in self._selected_numeric_columns_for_overall:
                    idx = self._column_indices.get(col_name)
                    if idx is not None and idx < len(row):
                        try:
                            vals.append(float(row[idx]))
                        except Exception:
                            pass
                overall = sum(vals) / len(vals) if vals else 0.0
            if team_numbers is not None and team not in team_numbers:
                continue
            perf.setdefault(team, []).append((match_num, overall))
        
        for team in perf:
            perf[team].sort(key=lambda x: x[0])
        return perf

    def export_columns_config(self, file_path: str) -> bool:
        """Export current column configuration to a JSON file."""
        config = {
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "headers": self.get_current_headers(),
            "column_configuration": {
                "numeric_for_overall": self._selected_numeric_columns_for_overall,
                "stats_columns": self._selected_stats_columns,
                "mode_boolean_columns": self._mode_boolean_columns,
                "autonomous_columns": self._autonomous_columns,
                "teleop_columns": self._teleop_columns,
                "endgame_columns": self._endgame_columns
            },
            "robot_valuation": {
                "phase_weights": self.robot_valuation_phase_weights,
                "phase_names": self.robot_valuation_phase_names
            },
            "metadata": {
                "total_columns": len(self.get_current_headers()),
                "description": "Alliance Simulator Column Configuration"
            }
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            print(f"Configuration exported successfully to: {file_path}")
            return True
        except Exception as e:
            print(f"Error exporting configuration: {e}")
            return False

    def import_columns_config(self, file_path: str) -> tuple:
        """
        Import column configuration from a JSON file.
        Returns: (success: bool, message: str)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if "column_configuration" not in config:
                return False, "JSON file does not contain valid column configuration"
            
            col_config = config["column_configuration"]
            current_headers = self.get_current_headers()
            
            missing_columns = []
            
            # Validate and apply column configurations
            config_mappings = [
                ("numeric_for_overall", "_selected_numeric_columns_for_overall"),
                ("stats_columns", "_selected_stats_columns"),
                ("mode_boolean_columns", "_mode_boolean_columns"),
                ("autonomous_columns", "_autonomous_columns"),
                ("teleop_columns", "_teleop_columns"),
                ("endgame_columns", "_endgame_columns")
            ]
            
            for config_key, attr_name in config_mappings:
                if config_key in col_config:
                    cols = col_config[config_key]
                    missing = [col for col in cols if col not in current_headers]
                    if missing:
                        missing_columns.extend(missing)
                    else:
                        setattr(self, attr_name, cols)
            
            # Import robot valuation config if present
            if "robot_valuation" in config:
                rv_config = config["robot_valuation"]
                if "phase_weights" in rv_config:
                    weights = rv_config["phase_weights"]
                    if len(weights) == 3 and 0.99 < sum(weights) < 1.01:
                        self.robot_valuation_phase_weights = weights
                if "phase_names" in rv_config:
                    self.robot_valuation_phase_names = rv_config["phase_names"]
            
            if missing_columns:
                return True, f"Configuration imported with warnings. Missing columns: {list(set(missing_columns))}"
            
            return True, "Configuration imported successfully"
            
        except FileNotFoundError:
            return False, f"File not found: {file_path}"
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON format: {e}"
        except Exception as e:
            return False, f"Error importing configuration: {e}"

    def get_config_summary(self) -> Dict[str, Any]:
        """Return a summary of the current configuration."""
        return {
            "total_headers": len(self.get_current_headers()),
            "numeric_for_overall_count": len(self._selected_numeric_columns_for_overall),
            "stats_columns_count": len(self._selected_stats_columns),
            "mode_boolean_count": len(self._mode_boolean_columns),
            "autonomous_columns_count": len(self._autonomous_columns),
            "teleop_columns_count": len(self._teleop_columns),
            "endgame_columns_count": len(self._endgame_columns),
            "robot_valuation_weights": self.robot_valuation_phase_weights,
            "game_phases_configured": {
                "autonomous": self._autonomous_columns,
                "teleop": self._teleop_columns,
                "endgame": self._endgame_columns
            }
        }
