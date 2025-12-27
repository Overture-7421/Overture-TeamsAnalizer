"""
Data Service module for handling data operations.
Extracts data-handling logic from streamlit_app.py for better separation of concerns.
"""

import base64
import pandas as pd
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from collections import Counter
import json

from default_robot_image import load_team_image


def load_csv_data(uploaded_file: Any, analizador: Any, app_dir: Path) -> Tuple[bool, str]:
    """
    Load CSV data into the analyzer.
    
    Args:
        uploaded_file: Streamlit uploaded file object
        analizador: AnalizadorRobot instance
        app_dir: Application directory path
        
    Returns:
        Tuple[bool, str]: (success, message)
    """
    try:
        # Save uploaded file temporarily
        temp_file = app_dir / "temp_upload.csv"
        with temp_file.open("wb") as f:
            f.write(uploaded_file.getbuffer())

        # Load into analyzer
        analizador.load_csv(str(temp_file))
        
        return True, "CSV loaded successfully!"
    except Exception as e:
        return False, f"Error loading CSV: {str(e)}"


def get_team_stats_dataframe(analizador: Any, 
                              toa_manager: Optional[Any] = None) -> Optional[pd.DataFrame]:
    """
    Get team statistics as a pandas DataFrame.
    
    Args:
        analizador: AnalizadorRobot instance
        toa_manager: Optional TOA manager for team names
        
    Returns:
        Optional[pd.DataFrame]: DataFrame with team stats or None
    """
    stats = analizador.get_detailed_team_stats()
    if not stats:
        return None
    
    team_data_grouped = analizador.get_team_data_grouped()
    
    df_data = []
    for team_stat in stats:
        team_num = team_stat.get('team', 'N/A')
        team_name = toa_manager.get_team_nickname(team_num) if toa_manager else team_num
        team_key = str(team_num)
        team_rows = team_data_grouped.get(team_key, [])

        defense_rate = get_rate_from_stat(analizador, team_stat, ("Crossed Field/Defense", "Crossed Feild/Played Defense?")) * 100.0
        death_rate = get_rate_from_stat(analizador, team_stat, ("Died", "Died?")) * 100.0
        pickup_mode = get_mode_from_rows(analizador, team_rows, "Pickup Location")
        climb_mode = get_mode_from_rows(analizador, team_rows, "End Position")
        
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


def compute_numeric_average(analizador: Any, 
                            team_rows: List[List[str]], 
                            column_name: str) -> float:
    """
    Calculate the average numeric value for a given column across a team's matches.
    
    Args:
        analizador: AnalizadorRobot instance
        team_rows: List of row data for the team
        column_name: Name of the column to average
        
    Returns:
        float: Average value
    """
    col_idx = analizador._column_indices.get(column_name)
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


def get_rate_from_stat(analizador: Any, 
                       team_stat: Dict, 
                       column_name: Any) -> float:
    """
    Retrieve a precomputed rate statistic for the requested column.
    
    Args:
        analizador: AnalizadorRobot instance
        team_stat: Team statistics dictionary
        column_name: Column name or tuple of column names to check
        
    Returns:
        float: Rate value (0.0 to 1.0)
    """
    column_candidates = column_name if isinstance(column_name, (list, tuple)) else [column_name]

    for candidate in column_candidates:
        key = analizador._generate_stat_key(candidate, 'rate')
        if key in team_stat:
            return team_stat.get(key, 0.0)

    return 0.0


def get_mode_from_rows(analizador: Any, 
                       team_rows: List[List[str]], 
                       column_name: str) -> str:
    """
    Return the most frequent non-empty value for a given column.
    
    Args:
        analizador: AnalizadorRobot instance
        team_rows: List of row data for the team
        column_name: Name of the column
        
    Returns:
        str: Most frequent value or empty string
    """
    if not team_rows:
        return ""

    col_idx = analizador._column_indices.get(column_name)
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


def get_team_display_label(team_number: Any, toa_manager: Optional[Any] = None) -> str:
    """
    Return formatted team label with nickname when available.
    
    Args:
        team_number: Team number
        toa_manager: Optional TOA manager for team names
        
    Returns:
        str: Formatted team label
    """
    num_str = str(team_number)
    nickname = None
    if toa_manager:
        nickname = toa_manager.get_team_nickname(num_str)
    return f"{num_str} - {nickname}" if nickname else num_str


def validate_alliance_selection(red: List[str], blue: List[str]) -> Tuple[bool, str]:
    """
    Validate alliance inputs before running simulations.
    
    Args:
        red: Red alliance team numbers
        blue: Blue alliance team numbers
        
    Returns:
        Tuple[bool, str]: (is_valid, error_message)
    """
    if len(red) != 2 or len(blue) != 2:
        return False, "Select exactly 2 teams for each alliance."

    combined = red + blue
    if len(set(combined)) != len(combined):
        return False, "Each team must be unique across both alliances."

    return True, ""


def export_raw_data_csv(analizador: Any) -> Optional[str]:
    """
    Export raw data as CSV string.
    
    Args:
        analizador: AnalizadorRobot instance
        
    Returns:
        Optional[str]: Base64 encoded CSV or None
    """
    raw_data = analizador.get_raw_data()
    if not raw_data:
        return None
    
    df = pd.DataFrame(raw_data[1:], columns=raw_data[0])
    csv = df.to_csv(index=False)
    return base64.b64encode(csv.encode()).decode()


def export_simplified_ranking(analizador: Any, 
                               toa_manager: Optional[Any] = None) -> Optional[str]:
    """
    Export simplified ranking as CSV string.
    
    Args:
        analizador: AnalizadorRobot instance
        toa_manager: Optional TOA manager for team names
        
    Returns:
        Optional[str]: Base64 encoded CSV or None
    """
    stats = analizador.get_detailed_team_stats()
    if not stats:
        return None
    
    team_data_grouped = analizador.get_team_data_grouped()
    simplified_data = []
    
    for rank, team_stat in enumerate(stats, 1):
        team_num = str(team_stat.get('team', 'N/A'))
        overall_avg = team_stat.get('overall_avg', 0.0)
        overall_std = team_stat.get('overall_std', 0.0)
        robot_valuation = team_stat.get('RobotValuation', 0.0)
        team_rows = team_data_grouped.get(team_num, [])

        death_rate = get_rate_from_stat(analizador, team_stat, ("Died", "Died?"))
        defense_rate = get_rate_from_stat(analizador, team_stat, ("Crossed Field/Defense", "Crossed Feild/Played Defense?"))
        defended_rate = get_rate_from_stat(analizador, team_stat, ("Defended", "Was the robot Defended by someone?"))

        pickup_mode = get_mode_from_rows(analizador, team_rows, "Pickup Location") or "Unknown"
        climb_mode = get_mode_from_rows(analizador, team_rows, "End Position") or "Unknown"

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
    return base64.b64encode(csv.encode()).decode()


def generate_tierlist_txt(school_system: Any,
                          analizador: Any,
                          toa_manager: Optional[Any] = None,
                          images_folder: Optional[str] = None) -> str:
    """
    Generate a plain text file in the TierList Maker format.
    
    Args:
        school_system: TeamScoring instance
        analizador: AnalizadorRobot instance
        toa_manager: Optional TOA manager for team names
        images_folder: Optional folder path for team images
        
    Returns:
        str: TierList formatted text
    """
    # Get current configuration values
    current_min_score = school_system.min_honor_roll_score
    current_min_comp = school_system.min_competencies_count
    current_min_subcomp = school_system.min_subcompetencies_count
    
    # Build team stats lookup
    team_stats_lookup = {}
    if analizador:
        all_team_stats = analizador.get_detailed_team_stats()
        for stat in all_team_stats:
            team_num = str(stat.get("team", ""))
            team_stats_lookup[team_num] = stat
    
    # Identify defensive teams
    all_teams_in_system = list(school_system.teams.keys())
    defensive_teams_data = []
    remaining_teams_nums = []

    for team_num in all_teams_in_system:
        stat = team_stats_lookup.get(str(team_num), {})
        defense_rate = stat.get("teleop_crossed_played_defense_rate", stat.get("defense_rate", 0.0))
        
        if defense_rate > 0:
            died_rate = stat.get("died_rate", 1.0)
            result = school_system.calculated_scores.get(str(team_num))
            defensive_teams_data.append({
                'team_num': team_num, 
                'result': result, 
                'defense_rate': defense_rate, 
                'died_rate': died_rate
            })
        else:
            remaining_teams_nums.append(team_num)

    defensive_teams_data.sort(key=lambda x: (x['defense_rate'], -x['died_rate']), reverse=True)
    
    # Get rankings and disqualified teams
    rankings = school_system.get_honor_roll_ranking()
    disqualified = school_system.get_disqualified_teams()
    
    # Filter to remaining teams
    qualified_non_defensive = [
        (team_num, result) for team_num, result in rankings 
        if str(team_num) in remaining_teams_nums
    ]
    disqualified_non_defensive = [
        (team_num, reason) for team_num, reason in disqualified 
        if str(team_num) in remaining_teams_nums
    ]
    
    # Distribute qualified non-defensive teams into tiers
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
    
    # Disqualified teams
    disqualified_teams_list = []
    for team_num, reason in disqualified_non_defensive:
        result = school_system.calculated_scores.get(str(team_num))
        disqualified_teams_list.append((team_num, result, reason))
    
    def get_team_stats_json(team_num, result):
        """Generate stats JSON for a team."""
        calculated = school_system.calculated_scores.get(str(team_num))
        team_scores = school_system.teams.get(str(team_num))
        stat = team_stats_lookup.get(str(team_num), {})
        
        stats_dict = {
            "honor_score": round(calculated.honor_roll_score, 1) if calculated else 0.0,
            "curved_score": round(calculated.curved_score, 1) if calculated else 0.0,
            "final_points": calculated.final_points if calculated else 0,
            "match_performance": round(calculated.match_performance_score, 1) if calculated else 0.0,
            "pit_scouting": round(calculated.pit_scouting_score, 1) if calculated else 0.0,
            "during_event": round(calculated.during_event_score, 1) if calculated else 0.0,
            "overall_avg": round(stat.get("overall_avg", 0.0), 1),
            "robot_valuation": round(stat.get("RobotValuation", 0.0), 1),
            "defense_rate": round(stat.get("teleop_crossed_played_defense_rate", 0.0), 2),
            "died_rate": round(stat.get("died_rate", 0.0), 2),
        }
        
        return json.dumps(stats_dict, ensure_ascii=False)
    
    def generate_team_block(team_num, result, is_defensive=False):
        """Generate tier block for a team."""
        images_folder_path = images_folder if images_folder else "images"
        team_image_base64 = load_team_image(team_num, images_folder=images_folder_path)
        
        stats_json = get_team_stats_json(team_num, result)
        driver_skills = "Defensive" if is_defensive else "Offensive"
        
        team_name = ""
        if toa_manager:
            team_name = toa_manager.get_team_nickname(str(team_num))
        
        title_str = f"{team_num} - {team_name}" if team_name else f"Team {team_num}"
        
        lines = []
        lines.append(f"  Image: {team_image_base64}")
        lines.append(f"    Title: {title_str}")
        lines.append(f"    Text: {stats_json}")
        lines.append(f"    DriverSkills: {driver_skills}")
        lines.append(f"    ImageList:")
        return "\n".join(lines)
    
    # Build output
    output_lines = []
    
    output_lines.append(f"# TierList Export - Configuration Used:")
    output_lines.append(f"# Min Honor Roll Score: {current_min_score}")
    output_lines.append(f"# Min Competencies: {current_min_comp}")
    output_lines.append(f"# Min Subcompetencies: {current_min_subcomp}")
    output_lines.append(f"# Qualified Teams: {len(rankings)}")
    output_lines.append(f"# Disqualified Teams: {len(disqualified)}")
    output_lines.append("")
    
    # Tier blocks
    output_lines.append("Tier: 1st Pick")
    for team_num, result in tier_1:
        output_lines.append(generate_team_block(team_num, result, is_defensive=False))
    output_lines.append("")
    
    output_lines.append("Tier: 2nd Pick")
    for team_num, result in tier_2:
        output_lines.append(generate_team_block(team_num, result, is_defensive=False))
    output_lines.append("")
    
    output_lines.append("Tier: Ojito")
    output_lines.append("")
    
    output_lines.append("Tier: -")
    for team_num, result, reason in disqualified_teams_list:
        output_lines.append(generate_team_block(team_num, result, is_defensive=False))
    output_lines.append("")
    
    output_lines.append("Tier: Defense Pick")
    for team_data in defensive_teams_data:
        output_lines.append(generate_team_block(team_data['team_num'], team_data['result'], is_defensive=True))
    output_lines.append("")
    
    output_lines.append("Tier: Unassigned")
    
    return "\n".join(output_lines)
