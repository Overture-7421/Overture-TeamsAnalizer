from __future__ import annotations

import csv
import json
import random
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
EXAMPLE_DIR = ROOT / "archivos ejemplo"
SCOUTING_OUTPUTS = [
    DATA_DIR / "default_scouting.csv",
    EXAMPLE_DIR / "default_scouting.csv",
]
POST_MATCH_OUTPUTS = [
    DATA_DIR / "default_post_match_data.json",
    EXAMPLE_DIR / "default_post_match_data.json",
]
ROSTER_FILE = DATA_DIR / "teams_2026mxmo.json"
COLUMNS_FILE = ROOT / "lib" / "config" / "columns.json"

ROBOT_POSITIONS = ["Blue 1", "Blue 2", "Blue 3", "Red 1", "Red 2", "Red 3"]
STARTING_POSITIONS = ["Outpost Side", "Middle", "Depot Side"]

AUTO_SHOOT_OPTIONS = ["None", "Too little (Less than 15)", "Some (15-30)", "Many (30-60)", "Too many (More than 60)"]
TELEOP_SHOOT_OPTIONS = ["None", "Too little (Less than 35)", "Some (35-60)", "Many (60-90)", "Too many (90-130)", "Capitan (More than 130)"]
TELEOP_PASS_OPTIONS = ["None", "Too little (Less than 35)", "Some (35-60)", "Many (60-90)", "Too many (90-130)", "Support (More than 130)"]

AUTO_COMPLEXITY_LEVELS = ["Did Nothing", "Only Moved", "Only Shot", "Moves Balls in Middle", "Good", "Excellent"]
MISS_LEVELS = ["0%(ask before)", "10%", "25%", "50%", "75%", "100%"]
CLIMB_AUTO_LEVELS = ["Didn't Climb", "Failed Climb Attempt", "Side", "Middle"]
CLIMB_LEVELS = ["Didn't Climb", "L1", "L2", "L3", "Failed Climb Attempt"]

DEFENSE_LEVELS = ["None", "Bad", "Mid", "Good", "BestOfEvent"]
QUALITY_LEVELS = ["None", "Bad", "Mid", "Good", "BestOfEvent"]
CHASSIS_LEVELS = ["Tank", "Mecanum", "Swerve"]

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


@dataclass
class TeamProfile:
    offense: int
    auto_skill: int
    defense: int
    quality: int
    reliability: int
    chassis: str


def load_roster() -> List[Dict]:
    with open(ROSTER_FILE, "r", encoding="utf-8") as handle:
        return json.load(handle)


def load_headers() -> List[str]:
    with open(COLUMNS_FILE, "r", encoding="utf-8-sig") as handle:
        config = json.load(handle)
    return list(config["headers"])


def clamp(value: int, low: int, high: int) -> int:
    return max(low, min(high, value))


def option_with_jitter(options: List[str], base_index: int, jitter: int, rng: random.Random) -> str:
    idx = clamp(base_index + rng.randint(-jitter, jitter), 0, len(options) - 1)
    return options[idx]


def build_profiles(teams: List[Dict]) -> Dict[int, TeamProfile]:
    profiles: Dict[int, TeamProfile] = {}
    for i, team in enumerate(teams):
        team_num = int(team["team_number"])
        bucket = i % 6
        if bucket == 0:
            profiles[team_num] = TeamProfile(offense=5, auto_skill=5, defense=2, quality=5, reliability=5, chassis="Swerve")
        elif bucket == 1:
            profiles[team_num] = TeamProfile(offense=4, auto_skill=4, defense=4, quality=4, reliability=4, chassis="Swerve")
        elif bucket == 2:
            profiles[team_num] = TeamProfile(offense=3, auto_skill=3, defense=5, quality=4, reliability=4, chassis="Swerve")
        elif bucket == 3:
            profiles[team_num] = TeamProfile(offense=4, auto_skill=3, defense=3, quality=3, reliability=3, chassis="Mecanum")
        elif bucket == 4:
            profiles[team_num] = TeamProfile(offense=2, auto_skill=2, defense=4, quality=3, reliability=3, chassis="Tank")
        else:
            profiles[team_num] = TeamProfile(offense=1, auto_skill=1, defense=2, quality=2, reliability=2, chassis="Tank")
    return profiles


def build_scouting_rows(teams: List[Dict], profiles: Dict[int, TeamProfile], headers: List[str]) -> List[List[str]]:
    rows: List[List[str]] = []
    rng = random.Random(7421)
    match_number = 1

    for team_index, team in enumerate(teams):
        team_num = int(team["team_number"])
        profile = profiles[team_num]

        for round_index in range(3):
            row = {header: "" for header in headers}

            auto_index = clamp(profile.auto_skill - 1, 0, len(AUTO_SHOOT_OPTIONS) - 1)
            teleop_shoot_index = clamp(profile.offense, 0, len(TELEOP_SHOOT_OPTIONS) - 1)
            teleop_pass_index = clamp(profile.offense - 1, 0, len(TELEOP_PASS_OPTIONS) - 1)
            defense_index = clamp(profile.defense - 1, 0, len(DEFENSE_LEVELS) - 1)
            quality_index = clamp(profile.quality - 1, 0, len(QUALITY_LEVELS) - 1)
            auto_complexity_index = clamp(profile.auto_skill, 0, len(AUTO_COMPLEXITY_LEVELS) - 1)

            row["Scouter Name"] = f"AutoScout {team_index % 6 + 1}"
            row["Match Number"] = str(match_number)
            row["Robot Position"] = ROBOT_POSITIONS[(match_number - 1) % len(ROBOT_POSITIONS)]
            row["Team Number"] = str(team_num)
            row["Starting Position"] = STARTING_POSITIONS[(team_index + round_index) % len(STARTING_POSITIONS)]

            row["Shoot amount (Auto)"] = option_with_jitter(AUTO_SHOOT_OPTIONS, auto_index, 1, rng)
            row["Pass amount (Auto)"] = option_with_jitter(AUTO_SHOOT_OPTIONS, max(0, auto_index - 1), 1, rng)
            row["Climb Position (Auto)"] = option_with_jitter(CLIMB_AUTO_LEVELS, 2 if profile.auto_skill >= 3 else 0, 1, rng)
            row["If climbed, Got stuck in Tower? (Auto)"] = "True" if rng.random() < (0.28 - 0.04 * profile.reliability) else "False"
            row["Auton Complexity"] = option_with_jitter(AUTO_COMPLEXITY_LEVELS, auto_complexity_index, 1, rng)
            row["Auton Completed?"] = "True" if rng.random() < (0.40 + 0.10 * profile.auto_skill) else "False"
            row["How much missed shots? (Auto)"] = option_with_jitter(MISS_LEVELS, clamp(5 - profile.reliability, 0, 5), 1, rng)

            row["Shoot amount (Teleop)"] = option_with_jitter(TELEOP_SHOOT_OPTIONS, teleop_shoot_index, 1, rng)
            row["Pass amount (Teleop)"] = option_with_jitter(TELEOP_PASS_OPTIONS, teleop_pass_index, 1, rng)
            row["Penalty Counter"] = str(clamp(7 - profile.reliability + rng.randint(-2, 2), 0, 14))
            row["How much missed shots? (Teleop)"] = option_with_jitter(MISS_LEVELS, clamp(5 - profile.reliability, 0, 5), 1, rng)
            row["Quality Chasis/Driver Movement"] = option_with_jitter(QUALITY_LEVELS, quality_index, 1, rng)
            row["Climb"] = option_with_jitter(CLIMB_LEVELS, clamp(profile.quality, 0, len(CLIMB_LEVELS) - 1), 1, rng)
            row["Jammed over balls?"] = "True" if rng.random() < (0.22 - 0.03 * profile.reliability) else "False"
            row["Bulldozing?"] = option_with_jitter(DEFENSE_LEVELS, defense_index, 1, rng)
            row["Defended?"] = option_with_jitter(DEFENSE_LEVELS, defense_index, 1, rng)
            row["Chasis Type"] = profile.chassis
            row["Died"] = "True" if rng.random() < (0.20 - 0.03 * profile.reliability) else "False"
            row["Comments? (Keep it short, only relevant info)"] = (
                f"{team.get('nickname', team_num)}: offense {profile.offense}/5, defense {profile.defense}/5"
            )

            rows.append([row.get(header, "") for header in headers])
            match_number += 1

    return rows


def contribution_from_profile(profile: TeamProfile) -> str:
    if profile.defense >= 5 and profile.offense <= 2:
        return "Dedicated to defend"
    if profile.offense >= 5:
        return "Scored almost all alliance score"
    if profile.offense == 4:
        return "Scored ~75% of alliance score"
    if profile.offense == 3:
        return "Scored ~50% of alliance score"
    if profile.offense == 2:
        return "Scored ~30% of alliance score"
    return "Scored few points"


def contribution_points(label: str) -> int:
    if label == "Scored almost all alliance score":
        return 88
    if label == "Scored ~75% of alliance score":
        return 72
    if label == "Scored ~50% of alliance score":
        return 48
    if label == "Scored ~30% of alliance score":
        return 32
    if label == "Scored few points":
        return 12
    return 0


def build_post_match_entries(teams: List[Dict], profiles: Dict[int, TeamProfile]) -> List[Dict]:
    rng = random.Random(2026)
    team_numbers = [int(team["team_number"]) for team in teams]
    rng.shuffle(team_numbers)

    entries: List[Dict] = []
    if len(team_numbers) < 6:
        return entries

    match_number = 1
    for offset in range(0, len(team_numbers) - (len(team_numbers) % 6), 6):
        slots = team_numbers[offset:offset + 6]
        contributions: List[str] = []

        red_points = 0
        blue_points = 0

        for slot_index, team_num in enumerate(slots):
            profile = profiles[team_num]
            label = contribution_from_profile(profile)
            if profile.defense >= 4 and rng.random() < 0.35:
                label = "Dedicated to defend"
            elif profile.offense <= 2 and rng.random() < 0.25:
                label = "Dedicated to passing"

            contributions.append(label)
            points = contribution_points(label) + rng.randint(-8, 8)
            points = max(0, points)

            if slot_index < 3:
                red_points += points
            else:
                blue_points += points

        red_points = max(red_points, 35)
        blue_points = max(blue_points, 35)

        entries.append({
            "match_number": match_number,
            "red_points": red_points,
            "blue_points": blue_points,
            "num_teams": 6,
            "team_numbers": slots,
            "contributions": contributions,
        })
        match_number += 1

    return entries


def main() -> None:
    teams = load_roster()
    profiles = build_profiles(teams)
    headers = load_headers()

    scouting_rows = build_scouting_rows(teams, profiles, headers)
    post_match_entries = build_post_match_entries(teams, profiles)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for scouting_output in SCOUTING_OUTPUTS:
        scouting_output.parent.mkdir(parents=True, exist_ok=True)
        with open(scouting_output, "w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(headers)
            writer.writerows(scouting_rows)
        print(f"Wrote {len(scouting_rows)} scouting rows to {scouting_output}")

    for post_match_output in POST_MATCH_OUTPUTS:
        post_match_output.parent.mkdir(parents=True, exist_ok=True)
        with open(post_match_output, "w", encoding="utf-8") as handle:
            json.dump(post_match_entries, handle, indent=2, ensure_ascii=False)
        print(f"Wrote {len(post_match_entries)} post-match entries to {post_match_output}")


if __name__ == "__main__":
    main()
