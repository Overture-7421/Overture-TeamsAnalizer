import copy

# Scoring weights (adjust as needed)
W_AUTO = 1.2
W_TELEOP = 1.0
W_ENDGAME = 1.1
W_DEFENSE = 15

class Team:
    def __init__(self, num, rank, total_epa, auto_epa, teleop_epa, endgame_epa, defense=False, name=None):
        self.team = int(num)
        self.rank = int(rank)
        self.total_epa = float(total_epa)
        self.auto_epa = float(auto_epa)
        self.teleop_epa = float(teleop_epa)
        self.endgame_epa = float(endgame_epa)
        self.defense = bool(defense)
        self.name = name if name else str(num)
        self.score = self.compute_score()

    def compute_score(self):
        return (
            W_AUTO * self.auto_epa +
            W_TELEOP * self.teleop_epa +
            W_ENDGAME * self.endgame_epa +
            (W_DEFENSE if self.defense else 0)
        )

    def as_dict(self):
        return {
            "team": self.team,
            "rank": self.rank,
            "total_epa": self.total_epa,
            "auto_epa": self.auto_epa,
            "teleop_epa": self.teleop_epa,
            "endgame_epa": self.endgame_epa,
            "defense": self.defense,
            "name": self.name,
            "score": self.score
        }

class Alliance:
    def __init__(self, number):
        self.allianceNumber = number
        self.captain = None
        self.captainRank = None
        self.pick1 = None
        self.pick2 = None
        self.pick1Rec = None
        self.pick2Rec = None

    def as_dict(self):
        return {
            "allianceNumber": self.allianceNumber,
            "captain": self.captain,
            "captainRank": self.captainRank,
            "pick1": self.pick1,
            "pick2": self.pick2,
            "pick1Rec": self.pick1Rec,
            "pick2Rec": self.pick2Rec
        }

class AllianceSelector:
    def __init__(self, teams):
        self.teams = sorted(teams, key=lambda t: t.rank)
        # Official FIRST competitions always have exactly 8 alliances
        # However, if there are fewer than 8 teams, we adjust accordingly
        max_alliances = min(8, len(teams))
        self.alliances = [Alliance(i+1) for i in range(max_alliances)]
        self.update_alliance_captains()
        self.update_recommendations()

    def get_selected_picks(self):
        selected = []
        for a in self.alliances:
            if a.pick1: selected.append(a.pick1)
            if a.pick2: selected.append(a.pick2)
        return selected

    def update_alliance_captains(self):
        selected_picks = self.get_selected_picks()
        available = [t for t in self.teams if t.team not in selected_picks]
        available.sort(key=lambda t: t.rank)
        for i, a in enumerate(self.alliances):
            if i < len(available):
                a.captain = available[i].team
                a.captainRank = available[i].rank
            else:
                a.captain = None
                a.captainRank = None

    def get_available_teams(self, drafting_captain_rank, pick_type):
        selected = self.get_selected_picks()
        captains = [a.captain for a in self.alliances if a.captain]
        
        # For both pick1 and pick2, exclude:
        # 1. Already selected picks
        # 2. Current alliance captains (captains can never be picked)
        available = [t for t in self.teams if t.team not in selected and t.team not in captains]
        
        # Sort by score descending, then by rank ascending for tie-breaker
        available.sort(key=lambda t: (-t.score, t.rank))
        return available

    def get_team_score(self, team_number):
        for t in self.teams:
            if t.team == team_number:
                return t.score
        return 0

    def update_recommendations(self):
        # For each alliance, recommend the best available pick for pick1 and pick2
        # Each recommendation must be unique (no team recommended to multiple alliances for the same pick)
        # We simulate the draft order: pick1 (1-8), pick2 (8-1)
        # We use a copy of the current picks to simulate the draft
        picks_sim = {a.allianceNumber: {'pick1': a.pick1, 'pick2': a.pick2} for a in self.alliances}
        recommended_pick1 = set()
        recommended_pick2 = set()

        # Pick 1 (1-8)
        for idx, a in enumerate(self.alliances):
            if not a.pick1:
                available = [t for t in self.get_available_teams(a.captainRank, 'pick1') if t.team not in recommended_pick1]
                if available:
                    a.pick1Rec = available[0].team
                    recommended_pick1.add(available[0].team)
                else:
                    a.pick1Rec = None
            else:
                a.pick1Rec = None

        # Pick 2 (8-1)
        for idx in reversed(range(len(self.alliances))):
            a = self.alliances[idx]
            if not a.pick2:
                available = [t for t in self.get_available_teams(a.captainRank, 'pick2') if t.team not in recommended_pick2 and t.team not in recommended_pick1]
                if available:
                    a.pick2Rec = available[0].team
                    recommended_pick2.add(available[0].team)
                else:
                    a.pick2Rec = None
            else:
                a.pick2Rec = None

    def set_pick(self, alliance_index, pick_type, team_number):
        team_number = int(team_number)
        
        # Check if the team is already a captain (captains cannot be picked)
        captains = [a.captain for a in self.alliances if a.captain]
        if team_number in captains:
            raise ValueError(f"Cannot pick team {team_number} - it is already an alliance captain.")
        
        # Check if the team is already selected as a pick
        selected = self.get_selected_picks()
        if team_number in selected:
            raise ValueError(f"Team {team_number} is already selected as a pick.")
        
        # Verify the team exists in our team list
        team_exists = any(t.team == team_number for t in self.teams)
        if not team_exists:
            raise ValueError(f"Team {team_number} does not exist in the team list.")
        
        setattr(self.alliances[alliance_index], pick_type, team_number)
        self.update_alliance_captains()
        self.update_recommendations()

    def reset_picks(self):
        for a in self.alliances:
            a.pick1 = None
            a.pick2 = None
        self.update_alliance_captains()
        self.update_recommendations()

    def get_alliance_table(self):
        table = []
        for a in self.alliances:
            alliance_score = 0
            if a.captain: alliance_score += self.get_team_score(a.captain)
            if a.pick1: alliance_score += self.get_team_score(a.pick1)
            if a.pick2: alliance_score += self.get_team_score(a.pick2)
            table.append({
                "Alliance #": a.allianceNumber,
                "Captain": a.captain,
                "Pick 1": a.pick1,
                "Recommendation 1": a.pick1Rec,
                "Pick 2": a.pick2,
                "Recommendation 2": a.pick2Rec,
                "Alliance Score": round(alliance_score, 1)
            })
        return table

    def get_selector_info(self):
        """
        Retorna información útil sobre el estado actual del selector
        """
        captains = [a.captain for a in self.alliances if a.captain]
        selected_picks = self.get_selected_picks()
        total_selected = len(captains) + len(selected_picks)
        available_for_picks = len(self.teams) - len(captains)
        
        return {
            "total_teams": len(self.teams),
            "total_alliances": len(self.alliances),
            "active_alliances": len(captains),
            "captains": captains,
            "selected_picks": selected_picks,
            "total_selected": total_selected,
            "available_for_picks": available_for_picks,
            "can_make_picks": available_for_picks > 0
        }

    def update_teams(self, teams):
        self.teams = sorted(teams, key=lambda t: t.rank)
        # Recalculate number of alliances based on new team count
        max_alliances = min(8, max(1, len(teams) // 2))
        
        # If we need to adjust the number of alliances
        if len(self.alliances) != max_alliances:
            self.alliances = [Alliance(i+1) for i in range(max_alliances)]
        
        self.reset_picks()

def teams_from_dicts(team_dicts):
    teams = []
    for d in team_dicts:
        teams.append(Team(
            num=d.get("num", d.get("team", 0)),
            rank=d.get("rank", 0),
            total_epa=d.get("total_epa", 0),
            auto_epa=d.get("auto_epa", 0),
            teleop_epa=d.get("teleop_epa", 0),
            endgame_epa=d.get("endgame_epa", 0),
            defense=d.get("defense", False),
            name=d.get("name", None)
        ))
    return teams
