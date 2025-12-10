"""
Generate a DECODE-format test CSV based on provided sample rows.
Creates `archivos ejemplo/test_data_decode_500.csv` with 500 rows.

Run from repo root:
    python scripts\generate_decode_testdata.py

"""
import csv
import random
import os

random.seed(42)

OUT_PATH = os.path.join("archivos ejemplo", "test_data_decode_500.csv")
HEADER = [
    "SCOUTER INITIALS","MATCH NUMBER","ROBOT","FUTURE ALLIANCE IN QUALY?","TEAM NUMBER",
    "STARTING POSITION","NO SHOW","MOVED?","ARTIFACTS","ARTIFACTS IN PATTERN",
    "OVERFLOW ARTIFACTS","FAILED ARTIFACTS","DEPOT PLACED","AUTO FOUL","PICKUP LOCATION",
    "ARTIFACTS","ARTIFACTS IN PATTERN","OVERFLOW ARTIFACTS","FAILED ARTIFACTS","DEPOT PLACED",
    "FOUL","DIED?","END POSITION","BROKE?","DEFENDED?","TIPPED/FELL OVER?","HP MISTAKE?","OPENED GATE?","YELLOW/RED CARD"
]

# Include your three sample base rows as first match (match 1), add a 4th to make 4-robot match
base_rows = [
    # ML,1,Blue 1,false,7421,Wide Side,false,true,4,2,1,3,0,0,Source,6,3,3,2,0,0,false,Double Park,false,false,false,false,true,None
    {
        "SCOUTER INITIALS":"ML","MATCH NUMBER":1,"ROBOT":"Blue 1","FUTURE ALLIANCE IN QUALY?":"false","TEAM NUMBER":7421,
        "STARTING POSITION":"Wide Side","NO SHOW":"false","MOVED?":"true","ARTIFACTS":4,"ARTIFACTS IN PATTERN":2,
        "OVERFLOW ARTIFACTS":1,"FAILED ARTIFACTS":3,"DEPOT PLACED":0,"AUTO FOUL":0,"PICKUP LOCATION":"Source",
        "ARTIFACTS.2":6,"ARTIFACTS IN PATTERN.2":3,"OVERFLOW ARTIFACTS.2":3,"FAILED ARTIFACTS.2":2,"DEPOT PLACED.2":0,
        "FOUL":0,"DIED?":"false","END POSITION":"Double Park","BROKE?":"false","DEFENDED?":"false","TIPPED/FELL OVER?":"false","HP MISTAKE?":"true","OPENED GATE?":"None","YELLOW/RED CARD":""
    },
    # PA,1,Blue 2,true,3665,Goal Side,false,false,0,0,0,0,0,0,Ground,0,0,0,0,3,1,false,Partially Parked,false,true,false,true,false,Yellow Card
    {
        "SCOUTER INITIALS":"PA","MATCH NUMBER":1,"ROBOT":"Blue 2","FUTURE ALLIANCE IN QUALY?":"true","TEAM NUMBER":3665,
        "STARTING POSITION":"Goal Side","NO SHOW":"false","MOVED?":"false","ARTIFACTS":0,"ARTIFACTS IN PATTERN":0,
        "OVERFLOW ARTIFACTS":0,"FAILED ARTIFACTS":0,"DEPOT PLACED":0,"AUTO FOUL":0,"PICKUP LOCATION":"Ground",
        "ARTIFACTS.2":0,"ARTIFACTS IN PATTERN.2":0,"OVERFLOW ARTIFACTS.2":0,"FAILED ARTIFACTS.2":0,"DEPOT PLACED.2":3,
        "FOUL":1,"DIED?":"false","END POSITION":"Partially Parked","BROKE?":"false","DEFENDED?":"true","TIPPED/FELL OVER?":"false","HP MISTAKE?":"true","OPENED GATE?":"false","YELLOW/RED CARD":"Yellow Card"
    },
    # GM,1,Red 1,true,8989,Wide Side,false,false,0,0,0,0,0,0,Both,3,0,3,5,5,0,false,Fully Parked,true,true,false,false,false,Red Card
    {
        "SCOUTER INITIALS":"GM","MATCH NUMBER":1,"ROBOT":"Red 1","FUTURE ALLIANCE IN QUALY?":"true","TEAM NUMBER":8989,
        "STARTING POSITION":"Wide Side","NO SHOW":"false","MOVED?":"false","ARTIFACTS":0,"ARTIFACTS IN PATTERN":0,
        "OVERFLOW ARTIFACTS":0,"FAILED ARTIFACTS":0,"DEPOT PLACED":0,"AUTO FOUL":0,"PICKUP LOCATION":"Both",
        "ARTIFACTS.2":3,"ARTIFACTS IN PATTERN.2":0,"OVERFLOW ARTIFACTS.2":3,"FAILED ARTIFACTS.2":5,"DEPOT PLACED.2":5,
        "FOUL":0,"DIED?":"false","END POSITION":"Fully Parked","BROKE?":"true","DEFENDED?":"true","TIPPED/FELL OVER?":"false","HP MISTAKE?":"false","OPENED GATE?":"false","YELLOW/RED CARD":"Red Card"
    },
    # Additional sample to make match 1 a 4-robot match
    {
        "SCOUTER INITIALS":"XX","MATCH NUMBER":1,"ROBOT":"Red 2","FUTURE ALLIANCE IN QUALY?":"false","TEAM NUMBER":333,
        "STARTING POSITION":"Center","NO SHOW":"false","MOVED?":"true","ARTIFACTS":2,"ARTIFACTS IN PATTERN":0,
        "OVERFLOW ARTIFACTS":1,"FAILED ARTIFACTS":0,"DEPOT PLACED":1,"AUTO FOUL":0,"PICKUP LOCATION":"Floor",
        "ARTIFACTS.2":3,"ARTIFACTS IN PATTERN.2":1,"OVERFLOW ARTIFACTS.2":0,"FAILED ARTIFACTS.2":0,"DEPOT PLACED.2":0,
        "FOUL":0,"DIED?":"false","END POSITION":"None","BROKE?":"false","DEFENDED?":"false","TIPPED/FELL OVER?":"false","HP MISTAKE?":"false","OPENED GATE?":"false","YELLOW/RED CARD":""
    }
]

# Build a pool of team numbers (include sample team numbers and many others)
team_pool = [7421,3665,8989,333,254,111,555,666,222,444,777,888,1234,4321,2000,2001,2002,3001,3002,4001,4002,5001,5002,6100,6200,6300,6400,6500,6600,6700,6800,6900,7001,7002,7100,7200,7300,7400,7500,7600]

# Support four robots per match for DECODE
robots = ["Blue 1","Blue 2","Red 1","Red 2"]

# Helper to format boolean-like values to csv strings
def b(v):
    return "true" if v else "false"

rows = []
# Add base rows first
for r in base_rows:
    # Flatten the duplicate ARTIFACTS fields to match the header
    row = [
        r["SCOUTER INITIALS"], r["MATCH NUMBER"], r["ROBOT"], r["FUTURE ALLIANCE IN QUALY?"], r["TEAM NUMBER"],
        r["STARTING POSITION"], r["NO SHOW"], r["MOVED?"], r["ARTIFACTS"], r["ARTIFACTS IN PATTERN"],
        r["OVERFLOW ARTIFACTS"], r["FAILED ARTIFACTS"], r["DEPOT PLACED"], r["AUTO FOUL"], r["PICKUP LOCATION"],
        r["ARTIFACTS.2"], r["ARTIFACTS IN PATTERN.2"], r["OVERFLOW ARTIFACTS.2"], r["FAILED ARTIFACTS.2"], r["DEPOT PLACED.2"],
        r["FOUL"], r["DIED?"], r["END POSITION"], r["BROKE?"], r["DEFENDED?"], r["TIPPED/FELL OVER?"], r["HP MISTAKE?"], r["OPENED GATE?"], r["YELLOW/RED CARD"]
    ]
    rows.append(row)

# Now generate until we have 500 rows
target = 500
current_match = 2  # start after sample match 1
# We'll produce 4 robots per match for DECODE, ensuring unique team per match
team_pool_len = len(team_pool)
idx = 0
while len(rows) < target:
    teams_this_match = set()
    # For matches except possibly the last, pick up to 4 robots
    num_robots = 4
    # If remaining rows less than 4, adjust final match size
    if (target - len(rows)) < 4:
        num_robots = target - len(rows)
    for r_i in range(num_robots):
        # pick a team not already in this match
        attempts = 0
        while True:
            team = team_pool[(idx + r_i + current_match) % team_pool_len]
            attempts += 1
            if team not in teams_this_match:
                break
            idx += 1
            if attempts > 10:
                # fallback - pick any different team
                for t in team_pool:
                    if t not in teams_this_match:
                        team = t
                        break
                break

        teams_this_match.add(team)

        # derive deterministic-ish values from team and match
        art_auto = (team + current_match) % 5  # 0-4
        art_auto_pat = art_auto if art_auto and ((team + current_match) % 3 == 0) else max(0, art_auto - 1) if art_auto>0 and ((team + current_match) % 3 == 1) else (1 if art_auto>0 and ((team + current_match) % 3 == 2) else 0)
        overflow_auto = (team + current_match) % 2
        failed_auto = 0 if ((team + current_match) % 7) else 1
        depot_auto = 0
        auto_foul = 0

        art_tel = (team * 2 + current_match) % 8
        art_tel_pat = art_tel//3
        overflow_tel = (team + current_match*2) % 3
        failed_tel = 0
        depot_tel = 1 if ((team + current_match) % 10 == 0) else 0

        pickup = "Source" if depot_tel else "Ground"

        foul = 0
        died = "false"
        endpos_choice = (team + current_match) % 12
        if endpos_choice == 0:
            endpos = "Fully Parked"
        elif endpos_choice <= 3:
            endpos = "Partially Parked"
        elif endpos_choice == 11:
            endpos = "Double Park"
        else:
            endpos = "None"

        broke = "false"
        defended = "true" if ((team + current_match) % 11 == 0) else "false"
        tipped = "false"
        hp_mistake = "false"
        opened_gate = "false" if ((team + current_match) % 3 == 0) else "false"
        card = "None"

        scouter = "SG" if (team % 2 == 0) else "AL"
        robot_name = robots[r_i%len(robots)]
        future_alliance = "false"
        start_pos = "Goal Side" if (r_i==0) else "Wide Side"
        no_show = "false"
        moved = b(((team + current_match + r_i) % 5) > 0)

        row = [
            scouter, current_match, robot_name, future_alliance, team,
            start_pos, no_show, moved, art_auto, art_auto_pat, overflow_auto, failed_auto, depot_auto, auto_foul, pickup,
            art_tel, art_tel_pat, overflow_tel, failed_tel, depot_tel, foul, died, endpos, broke, defended, tipped, hp_mistake, opened_gate, card
        ]
        rows.append(row)
    current_match += 1
    idx += 4

# Write CSV
os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
with open(OUT_PATH, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow(HEADER)
    for r in rows:
        w.writerow(r)

print(f"Wrote {len(rows)} rows to {OUT_PATH}")