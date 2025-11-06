# Enhanced scoring weights based on comprehensive analysis
W_AUTO = 1.5      # Increased weight for autonomous performance 
W_TELEOP = 1.0    # Base teleop weight
W_ENDGAME = 1.2   # Increased weight for endgame (critical for close matches)
W_DEFENSE = 12    # Slightly reduced but still significant for defensive teams
W_CONSISTENCY = 5 # New weight for consistency bonus
W_CLUTCH = 8      # New weight for high-pressure performance

class Team:
    def __init__(self, num, rank, total_epa, auto_epa, teleop_epa, endgame_epa, defense=False, name=None,
                 robot_valuation=0, consistency_score=0, clutch_factor=0, death_rate=0.0, defended_rate=0.0,
                 defense_rate=0.0, algae_score=0.0):
        self.team = int(num)
        self.rank = int(rank)
        self.total_epa = float(total_epa)
        self.auto_epa = float(auto_epa)
        self.teleop_epa = float(teleop_epa)
        self.endgame_epa = float(endgame_epa)
        self.defense = bool(defense)
        self.name = name if name else str(num)
        
        # Enhanced attributes for better team evaluation
        self.robot_valuation = float(robot_valuation) if robot_valuation else 0
        self.consistency_score = float(consistency_score) if consistency_score else 0
        self.clutch_factor = float(clutch_factor) if clutch_factor else 0
        self.death_rate = float(death_rate) if death_rate else 0.0
        self.defended_rate = float(defended_rate) if defended_rate else 0.0
        self.defense_rate = float(defense_rate) if defense_rate else 0.0
        self.algae_score = float(algae_score) if algae_score else 0.0
        
        self.score = self.compute_score()

    def compute_score(self):
        """Enhanced scoring algorithm that considers multiple factors"""
        base_score = (
            W_AUTO * self.auto_epa +
            W_TELEOP * self.teleop_epa +
            W_ENDGAME * self.endgame_epa
        )
        
        # Defense bonus
        defense_bonus = W_DEFENSE if self.defense else 0
        
        # Consistency bonus (higher is better, penalize inconsistent teams)
        consistency_bonus = (self.consistency_score / 100) * W_CONSISTENCY
        
        # Clutch factor bonus (ability to perform under pressure)
        clutch_bonus = (self.clutch_factor / 100) * W_CLUTCH
        
        # Robot valuation factor (scales with overall robot quality)
        valuation_multiplier = 1.0 + (self.robot_valuation / 1000)  # Small but meaningful boost
        
        total_score = (base_score + defense_bonus + consistency_bonus + clutch_bonus) * valuation_multiplier
        
        return total_score

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
            "score": self.score,
            "robot_valuation": self.robot_valuation,
            "consistency_score": self.consistency_score,
            "clutch_factor": self.clutch_factor,
            "death_rate": self.death_rate,
            "defended_rate": self.defended_rate,
            "defense_rate": self.defense_rate,
            "algae_score": self.algae_score
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
        self.manual_captain = False

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
        # For testing purposes, create reasonable number of alliances
        # In real FRC: 8 alliances for events with 24+ teams, fewer for smaller events
        max_alliances = min(8, max(1, len(teams) // 3))  # At least 3 teams per alliance
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
        selected_picks = set(self.get_selected_picks())

        # Validate existing captains and keep manual selections intact when possible
        used_captains = set()
        for alliance in self.alliances:
            if alliance.captain is None:
                continue
            if alliance.captain in selected_picks:
                alliance.captain = None
                alliance.captainRank = None
                alliance.manual_captain = False
                continue
            used_captains.add(alliance.captain)

        available = [t for t in self.teams if t.team not in selected_picks and t.team not in used_captains]
        available.sort(key=lambda t: t.rank)

        for alliance in self.alliances:
            if alliance.captain is None and available:
                team = available.pop(0)
                alliance.captain = team.team
                alliance.captainRank = team.rank
                alliance.manual_captain = False
            elif alliance.captain is not None:
                # Ensure captain rank stays in sync
                for team in self.teams:
                    if team.team == alliance.captain:
                        alliance.captainRank = team.rank
                        break
            else:
                alliance.captain = None
                alliance.captainRank = None

    def get_available_teams(self, drafting_captain_rank, pick_type):
        selected_picks = self.get_selected_picks()
        
        # Find which alliance is making this pick
        drafting_alliance = None
        for a in self.alliances:
            if a.captainRank == drafting_captain_rank:
                drafting_alliance = a
                break
        
        available = []
        for team in self.teams:
            # Exclude already selected picks
            if team.team in selected_picks:
                continue
            
            # Check if this team is a captain
            is_captain = False
            captain_alliance = None
            for a in self.alliances:
                if a.captain == team.team:
                    is_captain = True
                    captain_alliance = a
                    break
            
            if is_captain:
                if drafting_alliance and captain_alliance:
                    # Captains can be drafted only by higher-ranked alliances (lower alliance number)
                    if drafting_alliance.allianceNumber == captain_alliance.allianceNumber:
                        continue
                    if drafting_alliance.allianceNumber > captain_alliance.allianceNumber:
                        continue
                elif captain_alliance:
                    # If no drafting alliance identified (failsafe), disallow picking own captain
                    continue
            
            # Team is available
            available.append(team)
        
        if pick_type == 'pick2':
            def pick2_key(team):
                # Prioritize defensive specialists and algae scorers with reliable performance
                defense_priority = team.defense_rate if hasattr(team, 'defense_rate') else 0.0
                algae_priority = team.algae_score if hasattr(team, 'algae_score') else 0.0
                reliability_penalty = team.death_rate if hasattr(team, 'death_rate') else 0.0
                return (
                    -defense_priority,
                    -algae_priority,
                    reliability_penalty,
                    -team.score,
                    team.rank
                )

            available.sort(key=pick2_key)
        else:
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
        recommended_pick1 = set()
        recommended_pick2 = set()

        # Pick 1 (1-8)
        for idx, a in enumerate(self.alliances):
            if not a.pick1:
                available = self.get_available_teams(a.captainRank, 'pick1')
                # Filter out already recommended teams
                available = [t for t in available if t.team not in recommended_pick1]
                if available:
                    preferred = None
                    if a.captainRank:
                        for team in available:
                            if team.rank > a.captainRank:
                                preferred = team
                                break
                    chosen = preferred if preferred else available[0]
                    a.pick1Rec = chosen.team
                    recommended_pick1.add(chosen.team)
                else:
                    a.pick1Rec = None
            else:
                a.pick1Rec = None

        # Pick 2 (8-1)
        for idx in reversed(range(len(self.alliances))):
            a = self.alliances[idx]
            if not a.pick2:
                available = self.get_available_teams(a.captainRank, 'pick2')
                # Filter out already recommended teams for both pick types
                available = [t for t in available if t.team not in recommended_pick2 and t.team not in recommended_pick1]
                if available:
                    a.pick2Rec = available[0].team
                    recommended_pick2.add(available[0].team)
                else:
                    a.pick2Rec = None
            else:
                a.pick2Rec = None

    def set_pick(self, alliance_index, pick_type, team_number):
        team_number = int(team_number)
        
        # Get the alliance that is making this pick
        picking_alliance = self.alliances[alliance_index]
        
        # Check if the team is the captain of the SAME alliance (captains cannot pick themselves)
        if team_number == picking_alliance.captain:
            raise ValueError(f"Cannot pick team {team_number} - alliance captains cannot pick themselves.")
        
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

    def set_captain(self, alliance_index, team_number):
        alliance = self.alliances[alliance_index]

        if team_number in (None, 0):
            alliance.captain = None
            alliance.captainRank = None
            alliance.manual_captain = False
            self.update_alliance_captains()
            self.update_recommendations()
            return

        if team_number in self.get_selected_picks():
            raise ValueError(f"Team {team_number} is already selected as a pick and cannot be captain.")

        team = next((t for t in self.teams if t.team == team_number), None)
        if not team:
            raise ValueError(f"Team {team_number} does not exist in the team list.")

        # Remove captain assignment from other alliances if necessary
        for idx, other in enumerate(self.alliances):
            if idx == alliance_index:
                continue
            if other.captain == team_number:
                other.captain = None
                other.captainRank = None
                other.manual_captain = False

        alliance.captain = team.team
        alliance.captainRank = team.rank
        alliance.manual_captain = True
        self.update_alliance_captains()
        self.update_recommendations()

    def get_available_captains(self, alliance_index):
        picks = set(self.get_selected_picks())
        alliance = self.alliances[alliance_index]
        options = []
        for team in self.teams:
            if team.team in picks and team.team != alliance.captain:
                continue
            options.append(team)
        options.sort(key=lambda t: t.rank)
        return options

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
                "Alliance Score": round(alliance_score, 1),
                "Captain Mode": "Manual" if a.manual_captain else "Auto"
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
            name=d.get("name", None),
            robot_valuation=d.get("robot_valuation", 0),
            consistency_score=d.get("consistency_score", 0),
            clutch_factor=d.get("clutch_factor", 0),
            death_rate=d.get("death_rate", 0.0),
            defended_rate=d.get("defended_rate", 0.0),
            defense_rate=d.get("defense_rate", 0.0),
            algae_score=d.get("algae_score", 0.0)
        ))
    return teams
