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
- Cálculo preciso de puntos por nivel de coral
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

def _load_game_config_from_json() -> Optional[Dict]:
    """Load game configuration from JSON file."""
    config_paths = [
        Path(__file__).parent / "config" / "game.json",
        Path(__file__).parent / "game.json"
    ]
    
    for config_path in config_paths:
        if config_path.exists():
            try:
                import json
                with open(config_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
    return None


@dataclass
class GameConfig:
    """Configuración de puntos del juego REEFSCAPE 2025.
    
    Supports JSON-driven configuration for easy updates between game seasons.
    Falls back to hardcoded defaults if JSON configuration is not available.
    """
    
    # Puntos por nivel de coral
    coral_auto_points: Dict[str, int] = field(default_factory=lambda: {"L1": 3, "L2": 4, "L3": 6, "L4": 7})
    coral_teleop_points: Dict[str, int] = field(default_factory=lambda: {"L1": 2, "L2": 3, "L3": 4, "L4": 5})
    
    # Puntos por algae
    processor_points: int = 6  # Auto y Teleop
    processor_opponent_bonus: int = 4  # Puntos extra para el oponente
    net_points: int = 4  # Solo Teleop
    
    # Puntos de endgame
    climb_points: Dict[str, int] = field(default_factory=lambda: {"none": 0, "park": 2, "shallow": 6, "deep": 12})
    
    # Requisitos para Ranking Points
    auto_rp_requirements: Dict[str, Any] = field(default_factory=lambda: {
        "all_leave_zone": True,
        "min_coral_auto": 1
    })
    
    coral_rp_requirements: Dict[str, Any] = field(default_factory=lambda: {
        "min_coral_per_level_no_coop": 7,
        "min_levels_with_coop": 3,
        "min_coral_per_level_with_coop": 7
    })
    
    cooperation_threshold: int = 2  # Algae mínimas en cada processor para coop
    
    @classmethod
    def from_json(cls, config_dict: Optional[Dict] = None) -> 'GameConfig':
        """Create GameConfig from JSON dictionary or load from file."""
        if config_dict is None:
            config_dict = _load_game_config_from_json()
        
        if config_dict is None:
            return cls()
        
        points = config_dict.get("points", {})
        coral = points.get("coral", {})
        algae = points.get("algae", {})
        climb = points.get("climb", {})
        ranking_points = config_dict.get("ranking_points", {})
        
        return cls(
            coral_auto_points=coral.get("auto", {"L1": 3, "L2": 4, "L3": 6, "L4": 7}),
            coral_teleop_points=coral.get("teleop", {"L1": 2, "L2": 3, "L3": 4, "L4": 5}),
            processor_points=algae.get("processor", 6),
            processor_opponent_bonus=algae.get("processor_opponent_bonus", 4),
            net_points=algae.get("net", 4),
            climb_points=climb if climb else {"none": 0, "park": 2, "shallow": 6, "deep": 12},
            auto_rp_requirements=ranking_points.get("auto_rp", {
                "all_leave_zone": True,
                "min_coral_auto": 1
            }),
            coral_rp_requirements=ranking_points.get("coral_rp", {
                "min_coral_per_level_no_coop": 7,
                "min_levels_with_coop": 3,
                "min_coral_per_level_with_coop": 7
            }),
            cooperation_threshold=ranking_points.get("cooperation_threshold", 2)
        )


# ============================= MODELOS DE DATOS ============================= #

@dataclass
class TeamPerformance:
    """Rendimiento estadístico de un equipo"""
    team_number: str
    
    # Coral por nivel (promedio por match)
    auto_L1: float = 0.0
    auto_L2: float = 0.0
    auto_L3: float = 0.0
    auto_L4: float = 0.0
    teleop_L1: float = 0.0
    teleop_L2: float = 0.0
    teleop_L3: float = 0.0
    teleop_L4: float = 0.0
    
    # Algae (promedio por match)
    auto_processor: float = 0.0
    teleop_processor: float = 0.0
    teleop_net: float = 0.0
    
    # Probabilidades
    p_leave_auto_zone: float = 0.5
    p_cooperation: float = 0.3
    
    # Distribución de climb
    climb_distribution: Dict[str, float] = field(default_factory=lambda: {
        "none": 0.4, "park": 0.3, "shallow": 0.2, "deep": 0.1
    })
    
    def total_coral_per_match(self) -> float:
        """Total de corales promedio por match"""
        return (self.auto_L1 + self.auto_L2 + self.auto_L3 + self.auto_L4 + 
                self.teleop_L1 + self.teleop_L2 + self.teleop_L3 + self.teleop_L4)
    
    def expected_climb_points(self) -> float:
        """Puntos esperados de climb"""
        config = GameConfig()
        return sum(prob * config.climb_points[climb_type] 
                  for climb_type, prob in self.climb_distribution.items())


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
    
    def extract_team_performance(self, team_number: str) -> TeamPerformance:
        """Extrae el rendimiento estadístico de un equipo"""
        team_stats = self._get_team_detailed_stats(team_number)
        
        if not team_stats:
            # Valores por defecto si no hay datos
            return TeamPerformance(
                team_number=team_number,
                p_leave_auto_zone=0.5,
                p_cooperation=0.3
            )
        
        # Extraer estadísticas de coral
        perf = TeamPerformance(team_number=team_number)
        
        # El analizador no separa auto/teleop en las estadísticas detalladas actualmente
        # Usamos las estadísticas disponibles y las distribuimos proporcionalmente
        
        # Coral totales (combinadas)
        total_L1 = team_stats.get('coral_l1__avg', 0.0)
        total_L2 = team_stats.get('coral_l2__avg', 0.0) 
        total_L3 = team_stats.get('coral_l3__avg', 0.0)
        total_L4 = team_stats.get('coral_l4__avg', 0.0)
        
        # Distribuir 30% auto, 70% teleop basado en observaciones típicas
        auto_ratio = 0.3
        teleop_ratio = 0.7
        
        perf.auto_L1 = total_L1 * auto_ratio
        perf.auto_L2 = total_L2 * auto_ratio
        perf.auto_L3 = total_L3 * auto_ratio
        perf.auto_L4 = total_L4 * auto_ratio
        
        perf.teleop_L1 = total_L1 * teleop_ratio
        perf.teleop_L2 = total_L2 * teleop_ratio
        perf.teleop_L3 = total_L3 * teleop_ratio
        perf.teleop_L4 = total_L4 * teleop_ratio
        
        # Algae (usar las estadísticas teleop disponibles como base)
        perf.auto_processor = team_stats.get('teleop_processor_algae_avg', 0.0) * 0.25  # Menos en auto
        perf.teleop_processor = team_stats.get('teleop_processor_algae_avg', 0.0)
        perf.teleop_net = team_stats.get('teleop_barge_algae_avg', 0.0)
        
        # Probabilidades basadas en overall performance
        overall_avg = team_stats.get('overall_avg', 0.0)
        if overall_avg > 60:
            perf.p_leave_auto_zone = 0.85
        elif overall_avg > 30:
            perf.p_leave_auto_zone = 0.65
        else:
            perf.p_leave_auto_zone = 0.35
        
        # Cooperation basada en processor performance
        perf.p_cooperation = min(0.8, max(0.1, perf.teleop_processor / 3.0))
        
        # Distribución de climb
        perf.climb_distribution = self._extract_climb_distribution(team_stats)
        
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
    
    def _extract_climb_distribution(self, team_stats: Dict) -> Dict[str, float]:
        """Extrae la distribución de climb del equipo"""
        # Por defecto basado en rendimiento general
        overall_avg = team_stats.get('overall_avg', 0.0)
        
        if overall_avg > 50:  # Equipo fuerte
            return {"none": 0.1, "park": 0.2, "shallow": 0.4, "deep": 0.3}
        elif overall_avg > 30:  # Equipo medio
            return {"none": 0.2, "park": 0.3, "shallow": 0.4, "deep": 0.1}
        else:  # Equipo débil
            return {"none": 0.5, "park": 0.3, "shallow": 0.15, "deep": 0.05}


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
        """Simula el rendimiento de una alianza"""
        result = {
            'coral_scores': {'L1': 0, 'L2': 0, 'L3': 0, 'L4': 0},
            'auto_coral': {'L1': 0, 'L2': 0, 'L3': 0, 'L4': 0},
            'teleop_coral': {'L1': 0, 'L2': 0, 'L3': 0, 'L4': 0},
            'processor_algae': {'auto': 0, 'teleop': 0},
            'net_algae': 0,
            'climb_scores': [],
            'coral_points': 0,
            'algae_points': 0,
            'climb_points': 0,
            'total_score': 0,
            'teams_left_auto_zone': 0,
            'cooperation_achieved': False
        }
        
        # Simular cada equipo
        for team in teams:
            # Coral Auto (distribución Poisson)
            auto_coral = {
                'L1': self._poisson_sample(team.auto_L1),
                'L2': self._poisson_sample(team.auto_L2),
                'L3': self._poisson_sample(team.auto_L3),
                'L4': self._poisson_sample(team.auto_L4)
            }
            
            # Coral Teleop
            teleop_coral = {
                'L1': self._poisson_sample(team.teleop_L1),
                'L2': self._poisson_sample(team.teleop_L2),
                'L3': self._poisson_sample(team.teleop_L3),
                'L4': self._poisson_sample(team.teleop_L4)
            }
            
            # Acumular coral
            for level in ['L1', 'L2', 'L3', 'L4']:
                result['auto_coral'][level] += auto_coral[level]
                result['teleop_coral'][level] += teleop_coral[level]
                result['coral_scores'][level] += auto_coral[level] + teleop_coral[level]
            
            # Algae
            result['processor_algae']['auto'] += self._poisson_sample(team.auto_processor)
            result['processor_algae']['teleop'] += self._poisson_sample(team.teleop_processor)
            result['net_algae'] += self._poisson_sample(team.teleop_net)
            
            # Climb
            climb_type = self._sample_climb(team.climb_distribution)
            climb_points = self.config.climb_points[climb_type]
            result['climb_scores'].append((team.team_number, climb_type, climb_points))
            result['climb_points'] += climb_points
            
            # Autonomous zone
            if random.random() < team.p_leave_auto_zone:
                result['teams_left_auto_zone'] += 1
        
        # Calcular puntos
        result['coral_points'] = self._calculate_coral_points(result)
        result['algae_points'] = self._calculate_algae_points(result)
        
        # Cooperation
        total_processor = result['processor_algae']['auto'] + result['processor_algae']['teleop']
        result['cooperation_achieved'] = total_processor >= self.config.cooperation_threshold * 2  # 2 processors
        
        result['total_score'] = result['coral_points'] + result['algae_points'] + result['climb_points']
        
        return result
    
    def _calculate_coral_points(self, alliance_result: Dict) -> int:
        """Calcula puntos de coral"""
        points = 0
        
        # Auto coral
        for level, count in alliance_result['auto_coral'].items():
            points += count * self.config.coral_auto_points[level]
        
        # Teleop coral
        for level, count in alliance_result['teleop_coral'].items():
            points += count * self.config.coral_teleop_points[level]
        
        return points
    
    def _calculate_algae_points(self, alliance_result: Dict) -> int:
        """Calcula puntos de algae"""
        points = 0
        
        # Processor algae
        total_processor = alliance_result['processor_algae']['auto'] + alliance_result['processor_algae']['teleop']
        points += total_processor * self.config.processor_points
        
        # Net algae
        points += alliance_result['net_algae'] * self.config.net_points
        
        return points
    
    def _calculate_ranking_points(self, red_result: Dict, blue_result: Dict,
                                red_teams: List[TeamPerformance], 
                                blue_teams: List[TeamPerformance]) -> Tuple[int, int]:
        """Calcula Ranking Points para ambas alianzas"""
        red_rp = 0
        blue_rp = 0
        
        # Win/Tie/Loss RP
        if red_result['total_score'] > blue_result['total_score']:
            red_rp += 3  # Win
            blue_rp += 0  # Loss
        elif blue_result['total_score'] > red_result['total_score']:
            blue_rp += 3  # Win
            red_rp += 0  # Loss
        else:
            red_rp += 1  # Tie
            blue_rp += 1  # Tie
        
        # Auto RP
        if (red_result['teams_left_auto_zone'] >= 3 and 
            sum(red_result['auto_coral'].values()) >= 1):
            red_rp += 1
        
        if (blue_result['teams_left_auto_zone'] >= 3 and 
            sum(blue_result['auto_coral'].values()) >= 1):
            blue_rp += 1
        
        # Coral RP
        if self._check_coral_rp(red_result):
            red_rp += 1
        
        if self._check_coral_rp(blue_result):
            blue_rp += 1
        
        return red_rp, blue_rp
    
    def _check_coral_rp(self, alliance_result: Dict) -> bool:
        """Verifica si se cumple el requisito de Coral RP"""
        coral_counts = alliance_result['coral_scores']
        cooperation = alliance_result['cooperation_achieved']
        
        if cooperation:
            # Con cooperación: al menos 7 corales en 3 niveles
            levels_with_7_plus = sum(1 for count in coral_counts.values() if count >= 7)
            return levels_with_7_plus >= 3
        else:
            # Sin cooperación: al menos 7 corales en cada nivel
            return all(count >= 7 for count in coral_counts.values())
    
    def _poisson_sample(self, mean: float) -> int:
        """Muestra de distribución Poisson"""
        if mean <= 0:
            return 0
        return max(0, int(random.gammavariate(mean, 1) + 0.5))
    
    def _sample_climb(self, distribution: Dict[str, float]) -> str:
        """Muestra tipo de climb según distribución"""
        rand = random.random()
        cumulative = 0
        
        for climb_type, prob in distribution.items():
            cumulative += prob
            if rand <= cumulative:
                return climb_type
        
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
            
            if len(red_team_numbers) != 3 or len(blue_team_numbers) != 3:
                messagebox.showerror("Error", "Debes seleccionar exactamente 3 equipos por alianza")
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
        output.append("🔮 PREDICCIÓN DE MATCH - REEFSCAPE 2025")
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
        output.append(f"  Coral Auto:   L1:{breakdown['auto_coral']['L1']} L2:{breakdown['auto_coral']['L2']} L3:{breakdown['auto_coral']['L3']} L4:{breakdown['auto_coral']['L4']}")
        output.append(f"  Coral Teleop: L1:{breakdown['teleop_coral']['L1']} L2:{breakdown['teleop_coral']['L2']} L3:{breakdown['teleop_coral']['L3']} L4:{breakdown['teleop_coral']['L4']}")
        output.append(f"  Processor:    Auto:{breakdown['processor_algae']['auto']} Teleop:{breakdown['processor_algae']['teleop']}")
        output.append(f"  Net Algae:    {breakdown['net_algae']}")
        
        # Climb breakdown
        climb_info = []
        for team, climb_type, points in breakdown['climb_scores']:
            climb_info.append(f"{team}:{climb_type}({points}pts)")
        output.append(f"  Climb:        {', '.join(climb_info)}")
        
        output.append(f"  Puntos Coral: {breakdown['coral_points']}")
        output.append(f"  Puntos Algae: {breakdown['algae_points']}")
        output.append(f"  Puntos Climb: {breakdown['climb_points']}")
        output.append(f"  TOTAL:        {breakdown['total_score']}")
        
        # Flags especiales
        output.append(f"  Auto Zone:    {breakdown['teams_left_auto_zone']}/3 equipos salieron")
        output.append(f"  Cooperation:  {'✅ Sí' if breakdown['cooperation_achieved'] else '❌ No'}")
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
        columns = ['Equipo', 'Auto L1', 'Auto L2', 'Auto L3', 'Auto L4',
                  'Tele L1', 'Tele L2', 'Tele L3', 'Tele L4',
                  'Proc Auto', 'Proc Tele', 'Net', 'P_Auto', 'Climb Exp']
        
        tree = ttk.Treeview(stats_window, columns=columns, show='headings', height=15)
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=70, anchor='center')
        
        # Llenar datos
        for team_number in all_teams:
            perf = self.extractor.extract_team_performance(team_number)
            
            row = [
                team_number,
                f"{perf.auto_L1:.2f}",
                f"{perf.auto_L2:.2f}",
                f"{perf.auto_L3:.2f}",
                f"{perf.auto_L4:.2f}",
                f"{perf.teleop_L1:.2f}",
                f"{perf.teleop_L2:.2f}",
                f"{perf.teleop_L3:.2f}",
                f"{perf.teleop_L4:.2f}",
                f"{perf.auto_processor:.2f}",
                f"{perf.teleop_processor:.2f}",
                f"{perf.teleop_net:.2f}",
                f"{perf.p_leave_auto_zone:.2f}",
                f"{perf.expected_climb_points():.2f}"
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
        red_coral_total = sum(prediction.red_breakdown['coral_scores'].values())
        blue_coral_total = sum(prediction.blue_breakdown['coral_scores'].values())
        
        if red_coral_total > blue_coral_total * 1.2:
            output.append("  🔴 RED tiene ventaja significativa en coral")
        elif blue_coral_total > red_coral_total * 1.2:
            output.append("  🔵 BLUE tiene ventaja significativa en coral")
        
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
    print("Sistema completo de predicción para REEFSCAPE 2025")
