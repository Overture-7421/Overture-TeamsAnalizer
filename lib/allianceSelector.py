from config_manager import get_global_config

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
                 defense_rate=0.0, algae_score=0.0, captain_rank=None, pick1_rank=None,
                 pick2_rank=None, pick1_score=0.0, pick2_score=0.0):
        self.team = int(num)
        self.rank = int(rank)
        self.captain_rank = int(captain_rank) if captain_rank else int(rank)
        self.pick1_rank = int(pick1_rank) if pick1_rank else int(rank)
        self.pick2_rank = int(pick2_rank) if pick2_rank else int(rank)
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
        self.pick1_score = float(pick1_score) if pick1_score else 0.0
        self.pick2_score = float(pick2_score) if pick2_score else 0.0
        
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
            "captain_rank": self.captain_rank,
            "pick1_rank": self.pick1_rank,
            "pick2_rank": self.pick2_rank,
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
            "algae_score": self.algae_score,
            "pick1_score": self.pick1_score,
            "pick2_score": self.pick2_score
        }

class Alliance:
    def __init__(self, number):
        self.allianceNumber = number
        self.captain = None
        self.captainRank = None
        self.pick1 = None
        self.pick1Rec = None
        self.pick2 = None
        self.pick2Rec = None
        self.manual_captain = False

    def as_dict(self):
        return {
            "allianceNumber": self.allianceNumber,
            "captain": self.captain,
            "captainRank": self.captainRank,
            "pick1": self.pick1,
            "pick1Rec": self.pick1Rec,
            "pick2": self.pick2,
            "pick2Rec": self.pick2Rec,
        }

class AllianceSelector:
    def __init__(self, teams):
        global W_AUTO, W_TELEOP, W_ENDGAME, W_DEFENSE, W_CONSISTENCY, W_CLUTCH
        config = get_global_config().get_alliance_config()
        scoring_weights = config.scoring_weights or {}
        W_AUTO = scoring_weights.get("auto", W_AUTO)
        W_TELEOP = scoring_weights.get("teleop", W_TELEOP)
        W_ENDGAME = scoring_weights.get("endgame", W_ENDGAME)
        W_DEFENSE = scoring_weights.get("defense", W_DEFENSE)
        W_CONSISTENCY = scoring_weights.get("consistency", W_CONSISTENCY)
        W_CLUTCH = scoring_weights.get("clutch", W_CLUTCH)

        self.teams = sorted(teams, key=self._captain_sort_key)
        # FRC: 3 teams per alliance (captain + pick1 + pick2)
        draft_params = config.draft_parameters or {}
        teams_per_alliance = draft_params.get("teams_per_alliance", 3) or 3
        max_alliances_cfg = draft_params.get("max_alliances", 8) or 8
        max_alliances = min(max_alliances_cfg, max(1, len(teams) // teams_per_alliance))
        self.alliances = [Alliance(i+1) for i in range(max_alliances)]
        self.update_alliance_captains()
        self.update_recommendations()

    @staticmethod
    def _captain_sort_key(team):
        return (team.captain_rank, team.team)

    @staticmethod
    def _pick_sort_key(team, pick_type):
        if pick_type == 'pick1':
            return (team.pick1_rank, team.team)
        if pick_type == 'pick2':
            return (team.pick2_rank, team.team)
        return (team.captain_rank, team.team)

    def get_selected_picks(self):
        selected = []
        for a in self.alliances:
            if a.pick1: selected.append(a.pick1)
            if a.pick2: selected.append(a.pick2)
        return selected

    def update_alliance_captains(self):
        while True:
            selected_picks = set(self.get_selected_picks())
            old_captains = [a.captain for a in self.alliances]

            # Step 1: Identify manual captains that are still valid (not picked)
            manual_captains = {}
            for i, alliance in enumerate(self.alliances):
                if alliance.manual_captain and alliance.captain is not None:
                    if alliance.captain in selected_picks:
                        # A manual captain was drafted! It is no longer a captain.
                        alliance.manual_captain = False
                        alliance.captain = None
                        alliance.pick1 = None
                        alliance.pick2 = None
                    else:
                        manual_captains[i] = alliance.captain

            # Step 2: Get all available teams for auto-fill
            # A team is available if it's not a pick and not a manual captain
            available = [
                t for t in self.teams 
                if t.team not in selected_picks and t.team not in manual_captains.values()
            ]
            available.sort(key=self._captain_sort_key)

            # Step 3: Rebuild the 8 captains
            for i, alliance in enumerate(self.alliances):
                old_captain = alliance.captain
                
                if i in manual_captains:
                    new_captain = manual_captains[i]
                else:
                    if available:
                        new_captain = available.pop(0).team
                    else:
                        new_captain = None
                        
                # If the captain for this alliance slot changed, clear its picks 
                # (No pick preservation upon shift/change)
                if old_captain != new_captain:
                    alliance.pick1 = None
                    alliance.pick2 = None
                    
                alliance.captain = new_captain
                
                # Sync rank
                if new_captain is not None:
                    for t in self.teams:
                        if t.team == new_captain:
                            alliance.captainRank = t.captain_rank
                            break
                else:
                    alliance.captainRank = None
                    alliance.manual_captain = False
            
            # Check for stabilization
            new_picks = set(self.get_selected_picks())
            new_captains = [a.captain for a in self.alliances]
            if selected_picks == new_picks and old_captains == new_captains:
                break

    def get_available_teams(self, drafting_captain_rank, pick_type='pick1'):
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
        
        available.sort(key=lambda t: self._pick_sort_key(t, pick_type))
        return available

    def get_team_score(self, team_number):
        for t in self.teams:
            if t.team == team_number:
                return t.score
        return 0

    def update_recommendations(self):
        # For each alliance, recommend the best available picks for pick1 and pick2
        # Each recommendation must be unique.
        recommended = set()

        all_captains = [a.captain for a in self.alliances if a.captain]

        # Pick 1 recommendations (snipe next alliance's captain)
        for idx, a in enumerate(self.alliances):
            if not a.pick1:
                target_captain_team = None
                if idx + 1 < len(all_captains):
                    target_captain_team = all_captains[idx + 1]
                else:
                    selected_teams = set(self.get_selected_picks()) | set(all_captains)
                    next_best_options = [t for t in self.teams if t.team not in selected_teams]
                    next_best_options.sort(key=self._captain_sort_key)
                    if next_best_options:
                        target_captain_team = next_best_options[0].team

                available = self.get_available_teams(a.captainRank, 'pick1')
                available_teams_set = {t.team for t in available}

                if target_captain_team and target_captain_team in available_teams_set and target_captain_team not in recommended:
                    a.pick1Rec = target_captain_team
                    recommended.add(target_captain_team)
                else:
                    fallback = [t for t in available if t.team not in recommended]
                    if fallback:
                        a.pick1Rec = fallback[0].team
                        recommended.add(fallback[0].team)
                    else:
                        a.pick1Rec = None
            else:
                a.pick1Rec = None

        # Pick 2 recommendations (best available team not already recommended/picked)
        for a in self.alliances:
            if not a.pick2:
                available = self.get_available_teams(a.captainRank, 'pick2')
                fallback = [t for t in available if t.team not in recommended]
                if fallback:
                    a.pick2Rec = fallback[0].team
                    recommended.add(fallback[0].team)
                else:
                    a.pick2Rec = None
            else:
                a.pick2Rec = None

    def set_pick(self, alliance_index, pick_type, team_number):
        # Get the alliance that is making this pick
        picking_alliance = self.alliances[alliance_index]

        if pick_type not in ('pick1', 'pick2'):
            raise ValueError("FRC alliances support pick1 and pick2 (3-team alliance).")

        # Allow clearing a pick by passing None or 0
        if team_number in (None, 0):
            setattr(picking_alliance, pick_type, None)
            self.update_alliance_captains()
            self.update_recommendations()
            return

        team_number = int(team_number)
        
        # Check if the team is the captain of the SAME alliance (captains cannot pick themselves)
        if team_number == picking_alliance.captain:
            raise ValueError(f"Cannot pick team {team_number} - alliance captains cannot pick themselves.")
        
        # Check if the team is already selected as a pick by any slot (allow re-selecting same slot)
        selected = self.get_selected_picks()
        current_val = getattr(picking_alliance, pick_type, None)
        if team_number in selected and current_val != team_number:
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
        alliance.captainRank = team.captain_rank
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
        options.sort(key=self._captain_sort_key)
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
        self.teams = sorted(teams, key=self._captain_sort_key)
        # Recalculate number of alliances based on new team count (FRC: 3 teams per alliance)
        max_alliances = min(8, max(1, len(teams) // 3))
        
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
            algae_score=d.get("algae_score", 0.0),
            captain_rank=d.get("captain_rank", d.get("rank", 0)),
            pick1_rank=d.get("pick1_rank", d.get("rank", 0)),
            pick2_rank=d.get("pick2_rank", d.get("rank", 0)),
            pick1_score=d.get("pick1_score", 0.0),
            pick2_score=d.get("pick2_score", 0.0),
        ))
    return teams
