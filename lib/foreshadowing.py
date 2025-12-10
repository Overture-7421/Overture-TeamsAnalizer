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

Marco Lopez - Overture 7421
"""

import math
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple
import tkinter as tk
from tkinter import ttk, messagebox


# ============================= CONFIGURACIÓN DE JUEGO ============================= #

@dataclass
class GameConfig:
    """Configuración de puntos del juego DECODE"""
    
    # Puntos por artifacts (Auto y Teleop)
    classified_artifact_points = 3  # CLASSIFIED ARTIFACT
    overflow_artifact_points = 1    # OVERFLOW ARTIFACT
    depot_artifact_points = 1       # DEPOT ARTIFACT (TeleOp only)
    pattern_bonus_points = 2        # PATTERN Bonus per ARTIFACT matching MOTIF
    
    # Puntos de autonomous
    leave_points = 3                # LEAVE in autonomous
    
    # Puntos de endgame
    endgame_points = {
        "none": 0,
        "partially_parked": 5,      # Partially returned to BASE
        "fully_parked": 10,         # Fully returned to BASE
        "double_park": 10           # Additional bonus (both robots fully returned)
    }
    
    # Alliance size
    alliance_size = 2  # DECODE uses 2-robot alliances


# ============================= MODELOS DE DATOS ============================= #

@dataclass
class TeamPerformance:
    """Rendimiento estadístico de un equipo para DECODE"""
    team_number: str
    
    # Artifacts por match (promedio)
    auto_artifacts: float = 0.0
    auto_artifacts_in_pattern: float = 0.0
    auto_overflow_artifacts: float = 0.0
    auto_depot_placed: float = 0.0
    
    teleop_artifacts: float = 0.0
    teleop_artifacts_in_pattern: float = 0.0
    teleop_overflow_artifacts: float = 0.0
    teleop_depot_placed: float = 0.0
    
    # Probabilidades
    p_leave_auto_zone: float = 0.5
    
    # Distribución de endgame
    endgame_distribution: Dict[str, float] = field(default_factory=lambda: {
        "none": 0.3, "partially_parked": 0.3, "fully_parked": 0.3, "double_park": 0.1
    })
    
    def total_artifacts_per_match(self) -> float:
        """Total de artifacts promedio por match"""
        return (self.auto_artifacts + self.auto_overflow_artifacts + 
                self.teleop_artifacts + self.teleop_overflow_artifacts)
    
    def expected_endgame_points(self) -> float:
        """Puntos esperados de endgame"""
        config = GameConfig()
        return sum(prob * config.endgame_points[endgame_type] 
                  for endgame_type, prob in self.endgame_distribution.items())


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
    """Extrae estadísticas de equipos desde el analizador para DECODE"""
    
    def __init__(self, analizador):
        self.analizador = analizador
        self.config = GameConfig()
    
    def extract_team_performance(self, team_number: str) -> TeamPerformance:
        """Extrae el rendimiento estadístico de un equipo para DECODE"""
        team_stats = self._get_team_detailed_stats(team_number)
        
        if not team_stats:
            # Valores por defecto si no hay datos
            return TeamPerformance(
                team_number=team_number,
                p_leave_auto_zone=0.5
            )
        
        # Extraer estadísticas de artifacts
        perf = TeamPerformance(team_number=team_number)
        
        # Autonomous artifacts (try multiple key formats for compatibility)
        perf.auto_artifacts = (team_stats.get('artifacts_auto_avg', 0.0) or 
                               team_stats.get('artifacts__auto__avg', 0.0))
        perf.auto_artifacts_in_pattern = (team_stats.get('artifacts_in_pattern_auto_avg', 0.0) or 
                                          team_stats.get('artifacts_in_pattern__auto__avg', 0.0))
        perf.auto_overflow_artifacts = (team_stats.get('overflow_artifacts_auto_avg', 0.0) or 
                                        team_stats.get('overflow_artifacts__auto__avg', 0.0))
        perf.auto_depot_placed = (team_stats.get('depot_placed_auto_avg', 0.0) or 
                                  team_stats.get('depot_placed__auto__avg', 0.0))
        
        # Teleop artifacts
        perf.teleop_artifacts = (team_stats.get('artifacts_teleop_avg', 0.0) or 
                                 team_stats.get('artifacts__teleop__avg', 0.0))
        perf.teleop_artifacts_in_pattern = (team_stats.get('artifacts_in_pattern_teleop_avg', 0.0) or 
                                            team_stats.get('artifacts_in_pattern__teleop__avg', 0.0))
        perf.teleop_overflow_artifacts = (team_stats.get('overflow_artifacts_teleop_avg', 0.0) or 
                                          team_stats.get('overflow_artifacts__teleop__avg', 0.0))
        perf.teleop_depot_placed = (team_stats.get('depot_placed_teleop_avg', 0.0) or 
                                    team_stats.get('depot_placed__teleop__avg', 0.0))
        
        # Probabilidades basadas en overall performance
        overall_avg = team_stats.get('overall_avg', 0.0)
        # Try multiple key formats for moved rate
        moved_rate = (team_stats.get('moved_rate', 0.0) or 
                      team_stats.get('moved__auto__rate', 0.0) or 0.5)
        perf.p_leave_auto_zone = moved_rate if moved_rate > 0 else (0.85 if overall_avg > 60 else 0.65 if overall_avg > 30 else 0.35)
        
        # Distribución de endgame
        perf.endgame_distribution = self._extract_endgame_distribution(team_stats)
        
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
    
    def _extract_endgame_distribution(self, team_stats: Dict) -> Dict[str, float]:
        """Extrae la distribución de endgame del equipo para DECODE"""
        # Por defecto basado en rendimiento general
        overall_avg = team_stats.get('overall_avg', 0.0)
        
        if overall_avg > 50:  # Equipo fuerte
            return {"none": 0.1, "partially_parked": 0.2, "fully_parked": 0.5, "double_park": 0.2}
        elif overall_avg > 30:  # Equipo medio
            return {"none": 0.2, "partially_parked": 0.3, "fully_parked": 0.4, "double_park": 0.1}
        else:  # Equipo débil
            return {"none": 0.4, "partially_parked": 0.3, "fully_parked": 0.25, "double_park": 0.05}


# ============================= SIMULADOR DE MATCHES ============================= #

class MatchSimulator:
    """Simula matches usando distribuciones estadísticas para DECODE"""
    
    def __init__(self):
        self.config = GameConfig()
    
    def simulate_match(self, red_teams: List[TeamPerformance], 
                      blue_teams: List[TeamPerformance], 
                      num_simulations: int = 1000) -> MatchPrediction:
        """Simula un match completo usando Monte Carlo para DECODE (2-robot alliances)"""
        
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
        """Simula el rendimiento de una alianza para DECODE (2 robots)"""
        result = {
            'auto_artifacts': 0,
            'auto_artifacts_in_pattern': 0,
            'auto_overflow_artifacts': 0,
            'auto_depot_placed': 0,
            'teleop_artifacts': 0,
            'teleop_artifacts_in_pattern': 0,
            'teleop_overflow_artifacts': 0,
            'teleop_depot_placed': 0,
            'endgame_scores': [],
            'artifact_points': 0,
            'endgame_points': 0,
            'auto_points': 0,
            'total_score': 0,
            'teams_left_auto_zone': 0,
            'both_fully_parked': False
        }
        
        fully_parked_count = 0
        
        # Simular cada equipo (2 robots per alliance)
        for team in teams:
            # Auto artifacts (distribución Poisson)
            auto_art = self._poisson_sample(team.auto_artifacts)
            auto_art_pattern = min(auto_art, self._poisson_sample(team.auto_artifacts_in_pattern))
            auto_overflow = self._poisson_sample(team.auto_overflow_artifacts)
            auto_depot = self._poisson_sample(team.auto_depot_placed)
            
            result['auto_artifacts'] += auto_art
            result['auto_artifacts_in_pattern'] += auto_art_pattern
            result['auto_overflow_artifacts'] += auto_overflow
            result['auto_depot_placed'] += auto_depot
            
            # Teleop artifacts
            teleop_art = self._poisson_sample(team.teleop_artifacts)
            teleop_art_pattern = min(teleop_art, self._poisson_sample(team.teleop_artifacts_in_pattern))
            teleop_overflow = self._poisson_sample(team.teleop_overflow_artifacts)
            teleop_depot = self._poisson_sample(team.teleop_depot_placed)
            
            result['teleop_artifacts'] += teleop_art
            result['teleop_artifacts_in_pattern'] += teleop_art_pattern
            result['teleop_overflow_artifacts'] += teleop_overflow
            result['teleop_depot_placed'] += teleop_depot
            
            # Endgame
            endgame_type = self._sample_endgame(team.endgame_distribution)
            endgame_points = self.config.endgame_points[endgame_type]
            result['endgame_scores'].append((team.team_number, endgame_type, endgame_points))
            result['endgame_points'] += endgame_points
            
            if endgame_type in ['fully_parked', 'double_park']:
                fully_parked_count += 1
            
            # Autonomous zone
            if random.random() < team.p_leave_auto_zone:
                result['teams_left_auto_zone'] += 1
                result['auto_points'] += self.config.leave_points
        
        # Check if both robots are fully parked for bonus
        if fully_parked_count >= 2:
            result['both_fully_parked'] = True
            result['endgame_points'] += 10  # Additional bonus
        
        # Calcular puntos de artifacts
        result['artifact_points'] = self._calculate_artifact_points(result)
        
        result['total_score'] = result['artifact_points'] + result['endgame_points'] + result['auto_points']
        
        return result
    
    def _calculate_artifact_points(self, alliance_result: Dict) -> int:
        """Calcula puntos de artifacts para DECODE"""
        points = 0
        
        # Classified artifacts (Auto + Teleop)
        total_classified = alliance_result['auto_artifacts'] + alliance_result['teleop_artifacts']
        points += total_classified * self.config.classified_artifact_points
        
        # Overflow artifacts
        total_overflow = alliance_result['auto_overflow_artifacts'] + alliance_result['teleop_overflow_artifacts']
        points += total_overflow * self.config.overflow_artifact_points
        
        # Depot artifacts (Teleop only)
        points += alliance_result['teleop_depot_placed'] * self.config.depot_artifact_points
        
        # Pattern bonus
        total_pattern = alliance_result['auto_artifacts_in_pattern'] + alliance_result['teleop_artifacts_in_pattern']
        points += total_pattern * self.config.pattern_bonus_points
        
        return points
    
    def _calculate_ranking_points(self, red_result: Dict, blue_result: Dict,
                                red_teams: List[TeamPerformance], 
                                blue_teams: List[TeamPerformance]) -> Tuple[int, int]:
        """Calcula Ranking Points para ambas alianzas en DECODE"""
        red_rp = 0
        blue_rp = 0
        
        # Win/Tie/Loss RP
        if red_result['total_score'] > blue_result['total_score']:
            red_rp += 2  # Win
            blue_rp += 0  # Loss
        elif blue_result['total_score'] > red_result['total_score']:
            blue_rp += 2  # Win
            red_rp += 0  # Loss
        else:
            red_rp += 1  # Tie
            blue_rp += 1  # Tie
        
        return red_rp, blue_rp
    
    def _poisson_sample(self, mean: float) -> int:
        """Muestra de distribución Poisson"""
        if mean <= 0:
            return 0
        return max(0, int(random.gammavariate(mean, 1) + 0.5))
    
    def _sample_endgame(self, distribution: Dict[str, float]) -> str:
        """Muestra tipo de endgame según distribución"""
        rand = random.random()
        cumulative = 0
        
        for endgame_type, prob in distribution.items():
            cumulative += prob
            if rand <= cumulative:
                return endgame_type
        
        return "none"  # Fallback


# ============================= INTERFAZ GRÁFICA ============================= #

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
        for i in range(2):  # DECODE uses 2-robot alliances
            var = tk.StringVar()
            ttk.Label(red_frame, text=f"Equipo {i+1}:").pack(anchor=tk.W)
            combo = ttk.Combobox(red_frame, textvariable=var, values=available_teams, width=15)
            combo.pack(fill=tk.X, pady=2)
            self.red_team_vars.append(var)
        
        # BLUE Alliance  
        blue_frame = ttk.LabelFrame(teams_frame, text="BLUE Alliance", padding=5)
        blue_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=5)
        
        self.blue_team_vars = []
        for i in range(2):  # DECODE uses 2-robot alliances
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
                messagebox.showerror("Error", "Debes seleccionar exactamente 2 equipos por alianza (DECODE)")
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
        output.append("🔮 PREDICCIÓN DE MATCH - DECODE 2025")
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
        """Agrega breakdown detallado de una alianza para DECODE"""
        output.append(f"{title}:")
        output.append(f"  Auto Artifacts:   {breakdown.get('auto_artifacts', 0)} (In Pattern: {breakdown.get('auto_artifacts_in_pattern', 0)})")
        output.append(f"  Auto Overflow:    {breakdown.get('auto_overflow_artifacts', 0)}")
        output.append(f"  Teleop Artifacts: {breakdown.get('teleop_artifacts', 0)} (In Pattern: {breakdown.get('teleop_artifacts_in_pattern', 0)})")
        output.append(f"  Teleop Overflow:  {breakdown.get('teleop_overflow_artifacts', 0)}")
        output.append(f"  Depot Placed:     {breakdown.get('teleop_depot_placed', 0)}")
        
        # Endgame breakdown
        endgame_info = []
        for team, endgame_type, points in breakdown.get('endgame_scores', []):
            endgame_info.append(f"{team}:{endgame_type}({points}pts)")
        output.append(f"  Endgame:          {', '.join(endgame_info)}")
        
        output.append(f"  Puntos Artifacts: {breakdown.get('artifact_points', 0)}")
        output.append(f"  Puntos Auto:      {breakdown.get('auto_points', 0)}")
        output.append(f"  Puntos Endgame:   {breakdown.get('endgame_points', 0)}")
        output.append(f"  TOTAL:            {breakdown.get('total_score', 0)}")
        
        # Flags especiales
        output.append(f"  Auto Zone:        {breakdown.get('teams_left_auto_zone', 0)}/2 equipos salieron")
        output.append(f"  Both Parked:      {'✅ Sí (+10 bonus)' if breakdown.get('both_fully_parked', False) else '❌ No'}")
        output.append("")
    
    def _show_individual_stats(self):
        """Muestra estadísticas individuales de equipos para DECODE"""
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
        stats_window.title("Estadísticas Individuales - DECODE")
        stats_window.geometry("900x600")
        
        # Crear tabla con columnas DECODE
        columns = ['Equipo', 'Auto Art', 'Auto Pattern', 'Auto Overflow',
                  'Tele Art', 'Tele Pattern', 'Tele Overflow', 'Depot',
                  'P_Auto', 'Endgame Exp']
        
        tree = ttk.Treeview(stats_window, columns=columns, show='headings', height=15)
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=85, anchor='center')
        
        # Llenar datos
        for team_number in all_teams:
            perf = self.extractor.extract_team_performance(team_number)
            
            row = [
                team_number,
                f"{perf.auto_artifacts:.2f}",
                f"{perf.auto_artifacts_in_pattern:.2f}",
                f"{perf.auto_overflow_artifacts:.2f}",
                f"{perf.teleop_artifacts:.2f}",
                f"{perf.teleop_artifacts_in_pattern:.2f}",
                f"{perf.teleop_overflow_artifacts:.2f}",
                f"{perf.teleop_depot_placed:.2f}",
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
            
            if len(red_team_numbers) != 2 or len(blue_team_numbers) != 2:
                messagebox.showerror("Error", "Debes seleccionar exactamente 2 equipos por alianza (DECODE)")
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
        red_artifact_total = (prediction.red_breakdown.get('auto_artifacts', 0) + 
                              prediction.red_breakdown.get('teleop_artifacts', 0))
        blue_artifact_total = (prediction.blue_breakdown.get('auto_artifacts', 0) + 
                               prediction.blue_breakdown.get('teleop_artifacts', 0))
        
        if red_artifact_total > blue_artifact_total * 1.2:
            output.append("  🔴 RED tiene ventaja significativa en artifacts")
        elif blue_artifact_total > red_artifact_total * 1.2:
            output.append("  🔵 BLUE tiene ventaja significativa en artifacts")
        
        self.result_text.insert(tk.END, "\n".join(output))
        self.result_text.see(1.0)
    
    def _on_close(self):
        """Cierra la ventana"""
        self.window.destroy()
        self.window = None


# ============================= FUNCIÓN PRINCIPAL ============================= #

def launch_foreshadowing(parent, analizador):
    """Lanza el sistema de Foreshadowing"""
    gui = ForeshadowingGUI(parent, analizador)
    gui.show()


# ============================= TESTING ============================= #

if __name__ == "__main__":
    print("Sistema de Foreshadowing v2.0 - Marco González, Overture 7421")
    print("Sistema completo de predicción para DECODE 2025")
