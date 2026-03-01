"""
Sistema de Foreshadowing
=========================

Predice con precisión:
1. Piezas individuales hechas por cada robot
2. Puntos totales de cada alianza
3. Ranking Points (RP) posibles
4. Probabilidades de victoria

Características:
- Predicción basada en estadísticas reales de cada equipo
- Cálculo preciso de puntos por artefactos y patrón
- Análisis de probabilidades de Autonomous y Cooperation
- Simulación Monte Carlo para resultados más realistas
- Cálculo de Ranking Points según reglas de juego
- JSON-driven configuration for game parameters

Marco Lopez - Overture 7421
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path


# ============================= CONFIGURACIÓN DE JUEGO ============================= #

# Cache for loaded configurations to avoid repeated file reads
_game_config_cache = None
_columns_config_cache = None


def _load_game_config_from_json() -> Optional[Dict]:
    """Load game configuration from JSON file (cached)."""
    global _game_config_cache
    if _game_config_cache is not None:
        return _game_config_cache
    
    config_paths = [
        Path(__file__).parent / "config" / "game.json",
        Path(__file__).parent / "game.json"
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            try:
                import json
                with open(config_path, 'r', encoding='utf-8') as f:
                    _game_config_cache = json.load(f)
                    return _game_config_cache
            except Exception:
                pass
    return None


def _load_columns_config_from_json() -> Optional[Dict]:
    """Load columns configuration from JSON file (cached)."""
    global _columns_config_cache
    if _columns_config_cache is not None:
        return _columns_config_cache
    
    config_paths = [
        Path(__file__).parent / "config" / "columns.json",
        Path(__file__).parent / "columns.json"
    ]

    for config_path in config_paths:
        if config_path.exists():
            try:
                import json
                with open(config_path, 'r', encoding='utf-8') as f:
                    _columns_config_cache = json.load(f)
                    return _columns_config_cache
            except Exception:
                pass
    return None


# Cache for foreshadowing columns
_foreshadowing_columns_cache = None


def _get_foreshadowing_columns() -> Dict[str, str]:
    """Return column mappings for foreshadowing stats (cached)."""
    global _foreshadowing_columns_cache
    if _foreshadowing_columns_cache is not None:
        return _foreshadowing_columns_cache
    
    defaults = {
        "auto_fuel": "FUEL Scored (Active HUB) (Auto)",
        "auto_leave": "Left Launch Line (LEAVE)",
        "auto_tower_l1": "Tower Level 1 - Auto",
        "teleop_fuel": "FUEL Scored (Active HUB) (Teleop)",
        "endgame_tower_climb": "Tower Climb Level"
    }
    data = _load_columns_config_from_json() or {}
    overrides = data.get("foreshadowing_columns", {}) or {}
    merged = defaults.copy()
    merged.update({k: v for k, v in overrides.items() if v})
    _foreshadowing_columns_cache = merged
    return merged


@dataclass
class GameConfig:
    """Configuración de puntos del juego FRC REBUILT 2026.
    
    Supports JSON-driven configuration for easy updates between game seasons.
    Falls back to hardcoded defaults if JSON configuration is not available.
    """

    auto_points: Dict[str, int] = field(default_factory=lambda: {
        "leave": 3,
        "fuel": 1,
        "tower_level1_auto": 15
    })
    teleop_points: Dict[str, int] = field(default_factory=lambda: {
        "fuel": 1
    })
    endgame_points: Dict[str, int] = field(default_factory=lambda: {
        "tower_level1": 10,
        "tower_level2": 20,
        "tower_level3": 30
    })
    ranking_points: Dict[str, int] = field(default_factory=lambda: {
        "win": 3,
        "tie": 1,
        "loss": 0
    })

    @classmethod
    def from_json(cls, config_dict: Optional[Dict] = None) -> 'GameConfig':
        """Create GameConfig from JSON dictionary or load from file."""
        if config_dict is None:
            config_dict = _load_game_config_from_json()

        if config_dict is None:
            return cls()

        points = config_dict.get("points", {})
        auto = points.get("autonomous", {})
        teleop = points.get("teleop", {})
        endgame = points.get("endgame", {})
        ranking_points = config_dict.get("ranking_points", {})

        return cls(
            auto_points={
                "leave": auto.get("leave", 3),
                "fuel": auto.get("fuel", 1),
                "tower_level1_auto": auto.get("tower_level1_auto", 15)
            },
            teleop_points={
                "fuel": teleop.get("fuel", 1)
            },
            endgame_points={
                "tower_level1": endgame.get("tower_level1", 10),
                "tower_level2": endgame.get("tower_level2", 20),
                "tower_level3": endgame.get("tower_level3", 30)
            },
            ranking_points={
                "win": ranking_points.get("win_rp", ranking_points.get("win", 3)),
                "tie": ranking_points.get("tie_rp", ranking_points.get("tie", 1)),
                "loss": ranking_points.get("loss", 0)
            }
        )


# ============================= MODELOS DE DATOS ============================= #

@dataclass
class TeamPerformance:
    """Rendimiento estadístico de un equipo - FRC REBUILT 2026"""
    team_number: str

    # Autonomous (average per match)
    auto_fuel: float = 0.0
    p_auto_tower_l1: float = 0.0  # probability of scoring Tower Level 1 in auto

    # Teleop (average per match)
    teleop_fuel: float = 0.0

    # Probabilities
    p_leave_auto_zone: float = 0.5

    # Endgame tower climb distribution
    climb_distribution: Dict[str, float] = field(default_factory=lambda: {
        "none": 0.5, "level1": 0.3, "level2": 0.15, "level3": 0.05
    })

    def total_fuel_per_match(self) -> float:
        """Total FUEL scored per match"""
        return self.auto_fuel + self.teleop_fuel

    def expected_endgame_points(self) -> float:
        """Expected endgame points from tower climb"""
        config = GameConfig()
        return (
            self.climb_distribution.get("level1", 0.0) * config.endgame_points.get("tower_level1", 0) +
            self.climb_distribution.get("level2", 0.0) * config.endgame_points.get("tower_level2", 0) +
            self.climb_distribution.get("level3", 0.0) * config.endgame_points.get("tower_level3", 0)
        )


@dataclass 
class MatchPrediction:
    """Predicción completa de un match"""
    red_teams: List[TeamPerformance]
    blue_teams: List[TeamPerformance]
    
    # Resultados de simulación
    red_score: float = 0.0
    blue_score: float = 0.0
    red_rp: int = 0
    blue_rp: int = 0
    
    # Breakdown detallado
    red_breakdown: Dict = field(default_factory=dict)
    blue_breakdown: Dict = field(default_factory=dict)
    
    # Probabilidades
    red_win_probability: float = 0.0
    blue_win_probability: float = 0.0
    tie_probability: float = 0.0


# ============================= EXTRACTOR DE ESTADÍSTICAS ============================= #

class TeamStatsExtractor:
    """Extrae estadísticas de equipos desde el analizador"""
    
    def __init__(self, analizador, config: Optional[GameConfig] = None):
        self.analizador = analizador
        self.config = config if config else GameConfig.from_json()
        self.columns_map = _get_foreshadowing_columns()
    
    def extract_team_performance(self, team_number: str) -> TeamPerformance:
        """Extrae el rendimiento estadístico de un equipo"""
        team_rows = self.analizador.get_team_data_grouped().get(str(team_number), [])

        if not team_rows:
            return TeamPerformance(team_number=team_number)

        perf = TeamPerformance(team_number=team_number)
        indices = self.analizador._column_indices

        def _parse_numeric(value: Any) -> Optional[float]:
            if value is None:
                return None
            if isinstance(value, bool):
                return None
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                v = value.strip()
                if not v:
                    return None
                try:
                    return float(v)
                except ValueError:
                    return None
            return None

        def _avg_numeric(col_name: str) -> float:
            col_idx = indices.get(col_name)
            if col_idx is None:
                return 0.0
            values = []
            for row in team_rows:
                if col_idx >= len(row):
                    continue
                val = _parse_numeric(row[col_idx])
                if val is not None:
                    values.append(val)
            return sum(values) / len(values) if values else 0.0

        def _parse_bool(value: Any) -> bool:
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

        def _rate_bool(col_name: str) -> float:
            col_idx = indices.get(col_name)
            if col_idx is None:
                return 0.0
            values = []
            for row in team_rows:
                if col_idx >= len(row):
                    continue
                values.append(1.0 if _parse_bool(row[col_idx]) else 0.0)
            return sum(values) / len(values) if values else 0.0

        perf.auto_fuel = _avg_numeric(self.columns_map.get("auto_fuel", "FUEL Scored (Active HUB) (Auto)"))
        p_tower_l1_col = self.columns_map.get("auto_tower_l1", "Tower Level 1 - Auto")
        perf.p_auto_tower_l1 = _rate_bool(p_tower_l1_col) if p_tower_l1_col else 0.0

        perf.teleop_fuel = _avg_numeric(self.columns_map.get("teleop_fuel", "FUEL Scored (Active HUB) (Teleop)"))

        perf.p_leave_auto_zone = _rate_bool(self.columns_map.get("auto_leave", "Left Launch Line (LEAVE)")) or 0.5
        perf.climb_distribution = self._extract_climb_distribution(team_rows)

        return perf
    
    def _get_team_detailed_stats(self, team_number: str) -> Optional[Dict]:
        """Obtiene estadísticas detalladas del equipo"""
        try:
            all_stats = self.analizador.get_detailed_team_stats()
            for team_stat in all_stats:
                if str(team_stat.get('team', '')) == str(team_number):
                    return team_stat
            return None
        except Exception as e:
            print(f"Error obteniendo estadísticas para equipo {team_number}: {e}")
            return None
    
    def _extract_climb_distribution(self, team_rows: List[List[str]]) -> Dict[str, float]:
        """Extract tower climb level distribution for a team."""
        climb_col = self.columns_map.get("endgame_tower_climb", "Tower Climb Level")
        col_idx = self.analizador._column_indices.get(climb_col)
        if col_idx is None:
            return {"none": 0.5, "level1": 0.3, "level2": 0.15, "level3": 0.05}

        counts = {"none": 0, "level1": 0, "level2": 0, "level3": 0}
        for row in team_rows:
            if col_idx >= len(row):
                continue
            value = str(row[col_idx]).strip().lower()
            if "level 3" in value or "level3" in value:
                counts["level3"] += 1
            elif "level 2" in value or "level2" in value:
                counts["level2"] += 1
            elif "level 1" in value or "level1" in value:
                counts["level1"] += 1
            else:
                counts["none"] += 1

        total = sum(counts.values())
        if total == 0:
            return {"none": 0.5, "level1": 0.3, "level2": 0.15, "level3": 0.05}

        return {k: v / total for k, v in counts.items()}


# ============================= SIMULADOR DE MATCHES ============================= #

class MatchSimulator:
    """Simula matches usando distribuciones estadísticas"""
    
    def __init__(self, config: Optional[GameConfig] = None):
        self.config = config if config else GameConfig.from_json()
    
    def simulate_match(self, red_teams: List[TeamPerformance], 
                      blue_teams: List[TeamPerformance], 
                      num_simulations: int = 1000) -> MatchPrediction:
        """Simula un match completo usando Monte Carlo"""
        
        red_scores = []
        blue_scores = []
        red_rps = []
        blue_rps = []
        
        for _ in range(num_simulations):
            # Simular una instancia del match
            red_result = self._simulate_alliance(red_teams)
            blue_result = self._simulate_alliance(blue_teams)
            
            red_scores.append(red_result['total_score'])
            blue_scores.append(blue_result['total_score'])
            
            # Calcular RPs para esta simulación
            red_rp, blue_rp = self._calculate_ranking_points(
                red_result, blue_result, red_teams, blue_teams
            )
            red_rps.append(red_rp)
            blue_rps.append(blue_rp)
        
        # Calcular promedios y probabilidades
        avg_red_score = sum(red_scores) / num_simulations
        avg_blue_score = sum(blue_scores) / num_simulations
        avg_red_rp = sum(red_rps) / num_simulations
        avg_blue_rp = sum(blue_rps) / num_simulations
        
        # Probabilidades de victoria
        red_wins = sum(1 for r, b in zip(red_scores, blue_scores) if r > b)
        blue_wins = sum(1 for r, b in zip(red_scores, blue_scores) if b > r)
        ties = num_simulations - red_wins - blue_wins
        
        # Breakdown detallado (usando última simulación como ejemplo)
        red_breakdown = self._simulate_alliance(red_teams)
        blue_breakdown = self._simulate_alliance(blue_teams)
        
        return MatchPrediction(
            red_teams=red_teams,
            blue_teams=blue_teams,
            red_score=avg_red_score,
            blue_score=avg_blue_score,
            red_rp=round(avg_red_rp),
            blue_rp=round(avg_blue_rp),
            red_breakdown=red_breakdown,
            blue_breakdown=blue_breakdown,
            red_win_probability=red_wins / num_simulations,
            blue_win_probability=blue_wins / num_simulations,
            tie_probability=ties / num_simulations
        )
    
    def _simulate_alliance(self, teams: List[TeamPerformance]) -> Dict:
        """Simula el rendimiento de una alianza - FRC REBUILT 2026"""
        result = {
            'auto_fuel': 0,
            'auto_tower_l1_count': 0,
            'teleop_fuel': 0,
            'endgame_climbs': {'none': 0, 'level1': 0, 'level2': 0, 'level3': 0},
            'endgame_scores': [],
            'auto_points': 0,
            'teleop_points': 0,
            'endgame_points': 0,
            'total_score': 0,
            'teams_left_auto_zone': 0
        }
        
        # Simulate each team
        for team in teams:
            # Auto FUEL
            result['auto_fuel'] += self._poisson_sample(team.auto_fuel)

            # Auto Tower Level 1 (probability-based)
            if random.random() < team.p_auto_tower_l1:
                result['auto_tower_l1_count'] += 1

            # Teleop FUEL
            result['teleop_fuel'] += self._poisson_sample(team.teleop_fuel)

            # Endgame tower climb
            climb_type = self._sample_climb(team.climb_distribution)
            points = 0
            if climb_type == "level3":
                points = self.config.endgame_points.get("tower_level3", 0)
            elif climb_type == "level2":
                points = self.config.endgame_points.get("tower_level2", 0)
            elif climb_type == "level1":
                points = self.config.endgame_points.get("tower_level1", 0)
            result['endgame_climbs'][climb_type] += 1
            result['endgame_scores'].append((team.team_number, climb_type, points))
            result['endgame_points'] += points
            
            # Autonomous zone leave
            if random.random() < team.p_leave_auto_zone:
                result['teams_left_auto_zone'] += 1

        # Cap auto Tower Level 1 at 2 robots (rule: max 2 in auto)
        result['auto_tower_l1_count'] = min(result['auto_tower_l1_count'], 2)

        result['auto_points'] = self._calculate_auto_points(result)
        result['teleop_points'] = self._calculate_teleop_points(result)
        result['total_score'] = result['auto_points'] + result['teleop_points'] + result['endgame_points']
        
        return result

    def _calculate_auto_points(self, alliance_result: Dict) -> int:
        """Calcula puntos de autonomous - FRC REBUILT 2026"""
        points = 0
        points += alliance_result['teams_left_auto_zone'] * self.config.auto_points.get("leave", 0)
        points += alliance_result['auto_fuel'] * self.config.auto_points.get("fuel", 0)
        points += alliance_result['auto_tower_l1_count'] * self.config.auto_points.get("tower_level1_auto", 0)
        return points

    def _calculate_teleop_points(self, alliance_result: Dict) -> int:
        """Calcula puntos de teleop - FRC REBUILT 2026"""
        points = 0
        points += alliance_result['teleop_fuel'] * self.config.teleop_points.get("fuel", 0)
        return points
    
    def _calculate_ranking_points(self, red_result: Dict, blue_result: Dict,
                                red_teams: List[TeamPerformance], 
                                blue_teams: List[TeamPerformance]) -> Tuple[int, int]:
        """Calcula Ranking Points para ambas alianzas"""
        red_rp = 0
        blue_rp = 0
        
        # Win/Tie/Loss RP
        if red_result['total_score'] > blue_result['total_score']:
            red_rp += self.config.ranking_points.get("win", 2)
            blue_rp += self.config.ranking_points.get("loss", 0)
        elif blue_result['total_score'] > red_result['total_score']:
            blue_rp += self.config.ranking_points.get("win", 2)
            red_rp += self.config.ranking_points.get("loss", 0)
        else:
            red_rp += self.config.ranking_points.get("tie", 1)
            blue_rp += self.config.ranking_points.get("tie", 1)
        
        return red_rp, blue_rp
    
    def _poisson_sample(self, mean: float) -> int:
        """Muestra de distribución Poisson"""
        if mean <= 0:
            return 0
        return max(0, int(random.gammavariate(mean, 1) + 0.5))
    
    def _sample_climb(self, distribution: Dict[str, float]) -> str:
        """Sample tower climb level from distribution."""
        rand = random.random()
        cumulative = 0
        for level, prob in distribution.items():
            cumulative += prob
            if rand <= cumulative:
                return level
        return "none"

    def _sample_return(self, distribution: Dict[str, float]) -> str:
        """Muestra tipo de retorno según distribución"""
        rand = random.random()
        cumulative = 0

        for return_type, prob in distribution.items():
            cumulative += prob
            if rand <= cumulative:
                return return_type

        return "none"  # Fallback


# ============================= INTERFAZ GRÁFICA (DEPRECATED) ============================= #
# Note: The Tkinter GUI is deprecated in favor of the Streamlit UI.
# This code is kept for backwards compatibility but should not be used for new development.

try:
    import tkinter as tk
    from tkinter import ttk, messagebox
    _TKINTER_AVAILABLE = True
except ImportError:
    _TKINTER_AVAILABLE = False


class ForeshadowingGUI:
    """Interfaz gráfica del sistema de Foreshadowing"""
    
    def __init__(self, parent, analizador):
        self.parent = parent
        self.analizador = analizador
        self.extractor = TeamStatsExtractor(analizador)
        self.simulator = MatchSimulator()
        
        self.window = None
        self.red_team_vars = []
        self.blue_team_vars = []
        self.result_text = None
        
    def show(self):
        """Muestra la ventana de Foreshadowing"""
        if self.window is not None:
            self.window.lift()
            return
        
        self.window = tk.Toplevel(self.parent)
        self.window.title("Foreshadowing - Predicción de Matches")
        self.window.geometry("1000x700")
        self.window.protocol("WM_DELETE_WINDOW", self._on_close)
        
        self._create_interface()
    
    def _create_interface(self):
        """Crea la interfaz"""
        # Frame principal con scroll
        canvas = tk.Canvas(self.window)
        scrollbar = ttk.Scrollbar(self.window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Header
        header_frame = ttk.Frame(scrollable_frame)
        header_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(header_frame, text="Sistema de Foreshadowing v2.0", 
                 font=("Arial", 16, "bold")).pack()
        ttk.Label(header_frame, text="Predicción avanzada basada en estadísticas reales",
                 font=("Arial", 10)).pack()
        
        # Selección de equipos
        teams_frame = ttk.LabelFrame(scrollable_frame, text="Selección de Equipos", padding=10)
        teams_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Obtener lista de equipos disponibles
        available_teams = self._get_available_teams()
        
        # RED Alliance
        red_frame = ttk.LabelFrame(teams_frame, text="RED Alliance", padding=5)
        red_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)
        
        self.red_team_vars = []
        for i in range(3):
            var = tk.StringVar()
            ttk.Label(red_frame, text=f"Equipo {i+1}:").pack(anchor=tk.W)
            combo = ttk.Combobox(red_frame, textvariable=var, values=available_teams, width=15)
            combo.pack(fill=tk.X, pady=2)
            self.red_team_vars.append(var)
        
        # BLUE Alliance  
        blue_frame = ttk.LabelFrame(teams_frame, text="BLUE Alliance", padding=5)
        blue_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        self.blue_team_vars = []
        for i in range(3):
            var = tk.StringVar()
            ttk.Label(blue_frame, text=f"Equipo {i+1}:").pack(anchor=tk.W)
            combo = ttk.Combobox(blue_frame, textvariable=var, values=available_teams, width=15)
            combo.pack(fill=tk.X, pady=2)
            self.blue_team_vars.append(var)
        
        # Botones de control
        control_frame = ttk.Frame(scrollable_frame)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(control_frame, text="🔮 Predecir Match", 
                  command=self._predict_match).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="📊 Estadísticas Individuales", 
                  command=self._show_individual_stats).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="🎲 Simulación Monte Carlo", 
                  command=self._run_monte_carlo).pack(side=tk.LEFT, padx=5)
        
        # Área de resultados
        results_frame = ttk.LabelFrame(scrollable_frame, text="Resultados de Predicción", padding=10)
        results_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.result_text = tk.Text(results_frame, height=20, font=("Consolas", 10))
        result_scroll = ttk.Scrollbar(results_frame, orient="vertical", command=self.result_text.yview)
        self.result_text.configure(yscrollcommand=result_scroll.set)
        
        self.result_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        result_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Pack canvas y scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
    
    def _get_available_teams(self) -> List[str]:
        """Obtiene lista de equipos disponibles"""
        try:
            stats = self.analizador.get_detailed_team_stats()
            teams = [str(team_stat.get('team', '')) for team_stat in stats]
            return sorted([t for t in teams if t])
        except:
            return []
    
    def _predict_match(self):
        """Ejecuta predicción de match"""
        try:
            # Obtener equipos seleccionados
            red_team_numbers = [var.get().strip() for var in self.red_team_vars if var.get().strip()]
            blue_team_numbers = [var.get().strip() for var in self.blue_team_vars if var.get().strip()]
            
            if len(red_team_numbers) != 2 or len(blue_team_numbers) != 2:
                messagebox.showerror("Error", "Debes seleccionar exactamente 2 equipos por alianza")
                return
            
            # Extraer estadísticas
            red_teams = [self.extractor.extract_team_performance(team) for team in red_team_numbers]
            blue_teams = [self.extractor.extract_team_performance(team) for team in blue_team_numbers]
            
            # Simular match
            prediction = self.simulator.simulate_match(red_teams, blue_teams)
            
            # Mostrar resultados
            self._display_prediction(prediction)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error en la predicción: {e}")
    
    def _display_prediction(self, prediction: MatchPrediction):
        """Muestra los resultados de la predicción"""
        self.result_text.delete(1.0, tk.END)
        
        output = []
        output.append("=" * 80)
        output.append("🔮 PREDICCIÓN DE MATCH - FTC DECODE 2026")
        output.append("=" * 80)
        output.append("")
        
        # Equipos
        red_teams_str = " + ".join([team.team_number for team in prediction.red_teams])
        blue_teams_str = " + ".join([team.team_number for team in prediction.blue_teams])
        
        output.append(f"🔴 RED Alliance:  {red_teams_str}")
        output.append(f"🔵 BLUE Alliance: {blue_teams_str}")
        output.append("")
        
        # Puntuación predicha
        output.append("📊 PUNTUACIÓN PREDICHA:")
        output.append(f"  🔴 RED:  {prediction.red_score:.1f} puntos")
        output.append(f"  🔵 BLUE: {prediction.blue_score:.1f} puntos")
        output.append("")
        
        # Probabilidades de victoria
        output.append("🎯 PROBABILIDADES:")
        output.append(f"  🔴 RED gana:  {prediction.red_win_probability:.1%}")
        output.append(f"  🔵 BLUE gana: {prediction.blue_win_probability:.1%}")
        output.append(f"  🟡 Empate:    {prediction.tie_probability:.1%}")
        output.append("")
        
        # Ranking Points
        output.append("🏆 RANKING POINTS PREDICHOS:")
        output.append(f"  🔴 RED:  {prediction.red_rp} RP")
        output.append(f"  🔵 BLUE: {prediction.blue_rp} RP")
        output.append("")
        
        # Breakdown detallado
        output.append("🔍 BREAKDOWN DETALLADO:")
        output.append("")
        
        self._add_alliance_breakdown(output, "🔴 RED Alliance", prediction.red_breakdown)
        self._add_alliance_breakdown(output, "🔵 BLUE Alliance", prediction.blue_breakdown)
        
        # Mostrar en el widget de texto
        self.result_text.insert(tk.END, "\n".join(output))
        
        # Scroll al inicio
        self.result_text.see(1.0)
    
    def _add_alliance_breakdown(self, output: List[str], title: str, breakdown: Dict):
        """Agrega breakdown detallado de una alianza"""
        output.append(f"{title}:")
        output.append(
            "  Auto Artifacts: "
            f"Classified:{breakdown['auto_artifacts']['classified']} "
            f"Overflow:{breakdown['auto_artifacts']['overflow']} "
            f"Depot:{breakdown['auto_artifacts']['depot']} "
            f"Pattern:{breakdown['auto_artifacts']['pattern']}"
        )
        output.append(
            "  Teleop Artifacts: "
            f"Classified:{breakdown['teleop_artifacts']['classified']} "
            f"Overflow:{breakdown['teleop_artifacts']['overflow']} "
            f"Depot:{breakdown['teleop_artifacts']['depot']} "
            f"Failed:{breakdown['teleop_artifacts']['failed']} "
            f"Pattern:{breakdown['teleop_artifacts']['pattern']}"
        )

        endgame_info = []
        for team, return_type, points in breakdown['endgame_scores']:
            endgame_info.append(f"{team}:{return_type}({points}pts)")
        output.append(f"  Endgame:     {', '.join(endgame_info)}")

        output.append(f"  Auto Points:   {breakdown['auto_points']}")
        output.append(f"  Teleop Points: {breakdown['teleop_points']}")
        output.append(f"  Endgame Points:{breakdown['endgame_points']}")
        output.append(f"  TOTAL:         {breakdown['total_score']}")

        # Flags especiales
        output.append(f"  Auto Leave:   {breakdown['teams_left_auto_zone']}/2 equipos salieron")
        if breakdown.get('double_park_bonus', 0):
            output.append("  Double Park Bonus: ✅")
        output.append("")
    
    def _show_individual_stats(self):
        """Muestra estadísticas individuales de equipos"""
        # Obtener equipos seleccionados
        all_teams = []
        for var in self.red_team_vars + self.blue_team_vars:
            if var.get().strip():
                all_teams.append(var.get().strip())
        
        if not all_teams:
            messagebox.showwarning("Advertencia", "Selecciona al menos un equipo")
            return
        
        # Crear ventana de estadísticas
        stats_window = tk.Toplevel(self.window)
        stats_window.title("Estadísticas Individuales")
        stats_window.geometry("900x600")
        
        # Crear tabla
        columns = ['Equipo', 'Auto Classified', 'Auto Overflow', 'Auto Depot', 'Auto Pattern',
              'Tele Classified', 'Tele Overflow', 'Tele Depot', 'Tele Failed', 'Tele Pattern',
              'P_Auto', 'Endgame Exp']
        
        tree = ttk.Treeview(stats_window, columns=columns, show='headings', height=15)
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=70, anchor='center')
        
        # Llenar datos
        for team_number in all_teams:
            perf = self.extractor.extract_team_performance(team_number)
            
            row = [
                team_number,
                f"{perf.auto_classified:.2f}",
                f"{perf.auto_overflow:.2f}",
                f"{perf.auto_depot:.2f}",
                f"{perf.auto_pattern:.2f}",
                f"{perf.teleop_classified:.2f}",
                f"{perf.teleop_overflow:.2f}",
                f"{perf.teleop_depot:.2f}",
                f"{perf.teleop_failed:.2f}",
                f"{perf.teleop_pattern:.2f}",
                f"{perf.p_leave_auto_zone:.2f}",
                f"{perf.expected_endgame_points():.2f}"
            ]
            
            tree.insert('', 'end', values=row)
        
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Scrollbar
        scrollbar_stats = ttk.Scrollbar(stats_window, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar_stats.set)
        scrollbar_stats.pack(side=tk.RIGHT, fill=tk.Y)
    
    def _run_monte_carlo(self):
        """Ejecuta simulación Monte Carlo extendida"""
        try:
            # Obtener equipos
            red_team_numbers = [var.get().strip() for var in self.red_team_vars if var.get().strip()]
            blue_team_numbers = [var.get().strip() for var in self.blue_team_vars if var.get().strip()]
            
            if len(red_team_numbers) != 3 or len(blue_team_numbers) != 3:
                messagebox.showerror("Error", "Debes seleccionar exactamente 3 equipos por alianza")
                return
            
            # Ejecutar simulación con más iteraciones
            red_teams = [self.extractor.extract_team_performance(team) for team in red_team_numbers]
            blue_teams = [self.extractor.extract_team_performance(team) for team in blue_team_numbers]
            
            prediction = self.simulator.simulate_match(red_teams, blue_teams, num_simulations=5000)
            
            # Mostrar resultados extendidos
            self._display_monte_carlo_results(prediction)
            
        except Exception as e:
            messagebox.showerror("Error", f"Error en simulación Monte Carlo: {e}")
    
    def _display_monte_carlo_results(self, prediction: MatchPrediction):
        """Muestra resultados de simulación Monte Carlo"""
        self.result_text.delete(1.0, tk.END)
        
        output = []
        output.append("=" * 80)
        output.append("🎲 SIMULACIÓN MONTE CARLO (5000 iteraciones)")
        output.append("=" * 80)
        output.append("")
        
        # Resultado general
        self._display_prediction(prediction)
        
        output.append("\n🎯 ANÁLISIS ESTADÍSTICO:")
        output.append(f"  Confianza en predicción: {'Alta' if abs(prediction.red_win_probability - prediction.blue_win_probability) > 0.3 else 'Media' if abs(prediction.red_win_probability - prediction.blue_win_probability) > 0.1 else 'Baja'}")
        
        # Recomendaciones estratégicas
        output.append("\n💡 RECOMENDACIONES ESTRATÉGICAS:")
        
        if prediction.red_score > prediction.blue_score:
            output.append("  🔴 RED Alliance favorita para ganar")
            output.append("  🔵 BLUE debe enfocarse en Ranking Points")
        else:
            output.append("  🔵 BLUE Alliance favorita para ganar")
            output.append("  🔴 RED debe enfocarse en Ranking Points")
        
        # Factores clave
        red_teleop_total = sum(prediction.red_breakdown['teleop_artifacts'].values())
        blue_teleop_total = sum(prediction.blue_breakdown['teleop_artifacts'].values())
        
        if red_teleop_total > blue_teleop_total * 1.2:
            output.append("  🔴 RED tiene ventaja significativa en teleop de artefactos")
        elif blue_teleop_total > red_teleop_total * 1.2:
            output.append("  🔵 BLUE tiene ventaja significativa en teleop de artefactos")
        
        self.result_text.insert(tk.END, "\n".join(output))
        self.result_text.see(1.0)
    
    def _on_close(self):
        """Cierra la ventana"""
        self.window.destroy()
        self.window = None


# ============================= FUNCIÓN PRINCIPAL ============================= #

def launch_foreshadowing(parent, analizador):
    """
    Lanza el sistema de Foreshadowing (deprecated).
    
    Note: This function is deprecated. Use the Streamlit UI instead.
    """
    if not _TKINTER_AVAILABLE:
        print("Warning: Tkinter is not available. Use the Streamlit UI instead.")
        return None
    gui = ForeshadowingGUI(parent, analizador)
    gui.show()
    return gui


# ============================= TESTING ============================= #

if __name__ == "__main__":
    print("Sistema de Foreshadowing v2.0 - Marco González, Overture 7421")
    print("Sistema completo de predicción para FTC DECODE 2026")
