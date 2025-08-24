"""Foreshadowing (Match Prediction) System

Permite ingresar 3 equipos por alianza (Red / Blue) y predecir puntajes
basados en valores configurables para cada tipo de acción.

Reglas provistas por el usuario:
  - Coral Levels:
       L1: 3 puntos Auto / 2 TeleOp
       L2: 4 puntos Auto / 3 TeleOp
       L3: 6 puntos Auto / 4 TeleOp
       L4: 7 puntos Auto / 5 TeleOp
  - Processor: 6 puntos (Auto y TeleOp) *además el otro equipo gana 4 puntos* (swing opcional)
  - Net: 4 puntos (TeleOp)
  - Climb (endgame): Parked=2, Shallow=6, Deep=12
  - Coopertition Bonus: >=2 ALGAE en cada PROCESSOR => indicador (no RP directo)
  - AUTO RP: todos los robots dejan zona inicial + >=1 CORAL en Auto
  - CORAL RP: >=7 CORAL por nivel (sin coop) ó >=7 en 3 niveles (con coop)
  - Win=3 RP, Tie=1 RP, Loss=0 RP

Este módulo es autónomo pero se integra creando ForeshadowingLauncher.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Callable, Optional
import tkinter as tk
from tkinter import ttk, messagebox
import math, random


# --------------------------- Data Models ------------------------------------ #

@dataclass
class ScoringConfig:
    coral_auto: Dict[str, int] = field(default_factory=lambda: {"L1": 3, "L2": 4, "L3": 6, "L4": 7})
    coral_teleop: Dict[str, int] = field(default_factory=lambda: {"L1": 2, "L2": 3, "L3": 4, "L4": 5})
    processor_auto: int = 6
    processor_teleop: int = 6
    processor_opponent_gain: int = 4  # Puntos que gana el oponente (swing)
    net_teleop: int = 4
    climb_points: Dict[str, int] = field(default_factory=lambda: {"none": 0, "park": 2, "shallow": 6, "deep": 12})
    enable_processor_swing: bool = True

    def clone(self) -> 'ScoringConfig':
        return ScoringConfig(
            coral_auto=self.coral_auto.copy(),
            coral_teleop=self.coral_teleop.copy(),
            processor_auto=self.processor_auto,
            processor_teleop=self.processor_teleop,
            processor_opponent_gain=self.processor_opponent_gain,
            net_teleop=self.net_teleop,
            climb_points=self.climb_points.copy(),
            enable_processor_swing=self.enable_processor_swing
        )


@dataclass
class AlliancePrediction:
    teams: List[str] = field(default_factory=list)  # 3 teams
    auto_coral: Dict[str, int] = field(default_factory=lambda: {"L1": 0, "L2": 0, "L3": 0, "L4": 0})
    teleop_coral: Dict[str, int] = field(default_factory=lambda: {"L1": 0, "L2": 0, "L3": 0, "L4": 0})
    processor_auto: int = 0
    processor_teleop: int = 0
    net_teleop: int = 0
    algae_processor: int = 0  # Para coopertition
    robot_climbs: List[str] = field(default_factory=lambda: ["none", "none", "none"])  # uno por robot
    all_leave_auto: bool = True

    total_points: int = 0
    rp_auto: int = 0
    rp_coral: int = 0
    rp_coop: int = 0  # Indicador solamente
    rp_win_tie: int = 0
    ranking_points_total: int = 0


# --------------------------- Calculator ------------------------------------- #

class ForeshadowingCalculator:
    def __init__(self, config: ScoringConfig):
        self.config = config

    def compute_alliance_points(self, pred: AlliancePrediction, coop_enabled: bool) -> AlliancePrediction:
        points = 0
        for level, cnt in pred.auto_coral.items():
            points += cnt * self.config.coral_auto.get(level, 0)
        for level, cnt in pred.teleop_coral.items():
            points += cnt * self.config.coral_teleop.get(level, 0)
        points += pred.processor_auto * self.config.processor_auto
        points += pred.processor_teleop * self.config.processor_teleop
        points += pred.net_teleop * self.config.net_teleop
        for status in pred.robot_climbs:
            points += self.config.climb_points.get(status.lower(), 0)
        pred.total_points = points

        pred.rp_coop = 1 if pred.algae_processor >= 2 else 0
        auto_total_coral = sum(pred.auto_coral.values())
        pred.rp_auto = 1 if pred.all_leave_auto and auto_total_coral >= 1 else 0

        levels_meeting = [lvl for lvl, cnt in {lvl: pred.auto_coral[lvl] + pred.teleop_coral[lvl] for lvl in pred.auto_coral}.items() if cnt >= 7]
        if coop_enabled:
            pred.rp_coral = 1 if len(levels_meeting) >= 3 else 0
        else:
            pred.rp_coral = 1 if len(levels_meeting) == 4 else 0
        return pred

    def apply_win_tie_rp(self, red: AlliancePrediction, blue: AlliancePrediction):
        if red.total_points > blue.total_points:
            red.rp_win_tie = 3; blue.rp_win_tie = 0
        elif blue.total_points > red.total_points:
            blue.rp_win_tie = 3; red.rp_win_tie = 0
        else:
            red.rp_win_tie = 1; blue.rp_win_tie = 1
        for a in (red, blue):
            a.ranking_points_total = a.rp_auto + a.rp_coral + a.rp_win_tie


# --------------------------- GUI Components --------------------------------- #

class ForeshadowingLauncher:
    def __init__(self, master, on_close: Optional[Callable] = None, analyzer=None):
        """Launcher de Foreshadowing.

        analyzer: instancia de AnalizadorRobot (opcional) para extraer datos históricos
        y generar predicciones automáticas.
        """
        self.master = master
        self.on_close = on_close
        self.analyzer = analyzer
        self.config = ScoringConfig()
        self.calc = ForeshadowingCalculator(self.config)
        self.pred_red = AlliancePrediction()
        self.pred_blue = AlliancePrediction()
        # Cache de estadísticas por equipo para evitar recomputar
        self._team_stats_cache = {}
        self._build_team_entry()
        # Construir modelo estadístico si hay datos
        if self.analyzer:
            self._build_statistical_model()

    # --------------------------- Modelo Estadístico --------------------- #
    def _build_statistical_model(self):
        """Construye parámetros por equipo usando un enfoque Poisson para conteos.
        Parámetros:
          - lambda_{nivel}: media de piezas (L1..L4) por match
          - p_auto: prob. al menos 1 acción auto (usamos auto_success)
          - climb_rate: prob. de intento de climb
        Guardamos en self._team_model[team] = dict(...)
        """
        self._team_model: Dict[str, Dict[str, float]] = {}
        if not self.analyzer or not self.analyzer.sheet_data or len(self.analyzer.sheet_data) < 2:
            return
        # Reusar _compute_team_stats para obtener promedios crudos (ya suavizados)
        team_numbers = set()
        idx = self.analyzer._column_indices
        team_col = idx.get('Team Number')
        if team_col is None:
            return
        for row in self.analyzer.sheet_data[1:]:
            if team_col < len(row):
                team_numbers.add(str(row[team_col]).strip())
        for t in team_numbers:
            stats = self._compute_team_stats(t)
            model_entry = {
                'lambda_L1': max(0.01, stats['L1']-0.2),  # revertir suavizado aproximado
                'lambda_L2': max(0.01, stats['L2']-0.2),
                'lambda_L3': max(0.01, stats['L3']-0.2),
                'lambda_L4': max(0.01, stats['L4']-0.2),
                'p_auto': min(1.0, max(0.0, stats['auto_success'])),
                'climb_rate': min(1.0, max(0.0, stats['climb_rate'])),
                'algae_play': max(0.0, stats['played_algae']),
                'algae_barge': max(0.0, stats['algae_barge'])
            }
            self._team_model[t] = model_entry

    def _sample_climb_category(self, climb_rate: float) -> str:
        """Convierte un climb_rate (prob de algun climb) en distribución simple.
        Modelo heurístico: dividimos climb_rate en probabilidades deep>shallow>park.
        """
        if climb_rate <= 0.05:
            return 'none'
        # Particionamiento
        deep_p = max(0.0, climb_rate - 0.55)
        shallow_p = 0.0
        if climb_rate > 0.25:
            shallow_p = min(0.30, climb_rate - deep_p - 0.10)
        park_p = min(0.15, max(0.0, climb_rate - deep_p - shallow_p))
        none_p = max(0.0, 1.0 - (deep_p + shallow_p + park_p))
        dist = [('deep', deep_p), ('shallow', shallow_p), ('park', park_p), ('none', none_p)]
        r = random.random(); acc = 0.0
        for name, p in dist:
            acc += p
            if r <= acc:
                return name
        return 'none'

    def _statistical_predict_team(self, team: str, auto_factor: float = 0.45) -> Dict:
        """Devuelve predicción esperada para un equipo usando Poisson E[.] sin simulación.
        auto_factor controla fracción media de piezas que caen en auto (multiplicado por p_auto).
        """
        if not hasattr(self, '_team_model') or team not in self._team_model:
            return {
                'team': team, 'exp_L1':0,'exp_L2':0,'exp_L3':0,'exp_L4':0,
                'auto_L1':0,'auto_L2':0,'auto_L3':0,'auto_L4':0,
                'tele_L1':0,'tele_L2':0,'tele_L3':0,'tele_L4':0,
                'climb_dist': {'none':1.0}, 'best_climb':'none', 'coop_prob':0.0
            }
        m = self._team_model[team]
        p_auto = m['p_auto']
        auto_frac = p_auto * auto_factor
        def split(lambda_x):
            auto = lambda_x * auto_frac
            tele = max(0.0, lambda_x - auto)
            return auto, tele
        a1,t1 = split(m['lambda_L1']); a2,t2 = split(m['lambda_L2']); a3,t3 = split(m['lambda_L3']); a4,t4 = split(m['lambda_L4'])
        # Climb distribution (deterministic proportions)
        cr = m['climb_rate']
        deep_p = max(0.0, cr - 0.55)
        shallow_p = max(0.0, min(0.30, cr - deep_p - 0.10))
        park_p = max(0.0, min(0.15, cr - deep_p - shallow_p))
        none_p = max(0.0, 1.0 - (deep_p + shallow_p + park_p))
        climb_dist = {
            'deep': round(deep_p,3),
            'shallow': round(shallow_p,3),
            'park': round(park_p,3),
            'none': round(none_p,3)
        }
        best_climb = max(climb_dist.items(), key=lambda x: x[1])[0]
        # Coop prob ~ normalizada de algae_play & algae_barge
        coop_prob = min(1.0, (m['algae_barge']*0.5 + m['algae_play']*0.3))
        return {
            'team': team,
            'exp_L1': m['lambda_L1'], 'exp_L2': m['lambda_L2'], 'exp_L3': m['lambda_L3'], 'exp_L4': m['lambda_L4'],
            'auto_L1': a1, 'auto_L2': a2, 'auto_L3': a3, 'auto_L4': a4,
            'tele_L1': t1, 'tele_L2': t2, 'tele_L3': t3, 'tele_L4': t4,
            'climb_dist': climb_dist,
            'best_climb': best_climb,
            'coop_prob': coop_prob,
            'p_auto': p_auto
        }

    def statistical_predict_alliance(self, teams: List[str]) -> Dict:
        """Retorna resumen estadístico por equipo y agregado de la alianza."""
        per_team = [self._statistical_predict_team(t) for t in teams]
        agg = {lvl:0.0 for lvl in ['L1','L2','L3','L4']}
        auto_agg = {lvl:0.0 for lvl in ['L1','L2','L3','L4']}
        climb_expected_points = 0.0
        for tpred in per_team:
            for lvl in ['L1','L2','L3','L4']:
                agg[lvl] += tpred[f'exp_{lvl}']
                auto_agg[lvl] += tpred[f'auto_{lvl}']
            # Expected climb points
            for cat, p in tpred['climb_dist'].items():
                climb_expected_points += p * self.config.climb_points.get(cat, 0)
        return {
            'teams': per_team,
            'agg_total': agg,
            'agg_auto': auto_agg,
            'expected_climb_points': climb_expected_points
        }

    def simulate_match_points(self, red_teams: List[str], blue_teams: List[str], simulations: int = 300) -> Dict:
        """Monte Carlo para estimar distribución de puntos de cada alianza."""
        if not hasattr(self, '_team_model'):
            return {'red_mean':0,'blue_mean':0,'red_samples':[], 'blue_samples':[]}
        def sim_alliance(teams):
            total_points_samples = []
            def sample_poisson(lam: float) -> int:
                if lam <= 0: return 0
                L = math.exp(-lam); k = 0; p = 1.0
                while p > L:
                    k += 1
                    p *= random.random()
                return k - 1
            for _ in range(simulations):
                points = 0
                for tm in teams:
                    m = self._team_model.get(tm)
                    if not m:
                        continue
                    for lvl,key in [('L1','lambda_L1'),('L2','lambda_L2'),('L3','lambda_L3'),('L4','lambda_L4')]:
                        lam = m[key]
                        k = sample_poisson(lam)
                        auto_k = int(round(k * m['p_auto'] * 0.45))
                        tele_k = k - auto_k
                        points += auto_k * self.config.coral_auto.get(lvl,0)
                        points += tele_k * self.config.coral_teleop.get(lvl,0)
                    cat = self._sample_climb_category(m['climb_rate'])
                    points += self.config.climb_points.get(cat,0)
                total_points_samples.append(points)
            return total_points_samples
        red_samples = sim_alliance(red_teams)
        blue_samples = sim_alliance(blue_teams)
        return {
            'red_mean': sum(red_samples)/len(red_samples) if red_samples else 0,
            'blue_mean': sum(blue_samples)/len(blue_samples) if blue_samples else 0,
            'red_samples': red_samples,
            'blue_samples': blue_samples
        }

    # --------------------------- Predicción Automática -------------------- #
    def _compute_team_stats(self, team: str):
        """Devuelve dict con promedios por nivel de coral, algae, climb rate, auto success.
        Aplica suavizado (Laplace) para evitar ceros extremos.
        """
        if team in self._team_stats_cache:
            return self._team_stats_cache[team]
        stats = {
            'L1': 0.0, 'L2': 0.0, 'L3': 0.0, 'L4': 0.0,
            'matches': 0,
            'algae_barge': 0.0,
            'played_algae': 0.0,
            'climb_rate': 0.0,
            'auto_success': 0.0
        }
        if not self.analyzer or not self.analyzer.sheet_data or len(self.analyzer.sheet_data) < 2:
            self._team_stats_cache[team] = stats
            return stats
        header = self.analyzer.sheet_data[0]
        idx = self.analyzer._column_indices  # usar mapping interno
        # Column names esperados
        cL1 = idx.get('Coral L1 Scored'); cL2 = idx.get('Coral L2 Scored'); cL3 = idx.get('Coral L3 Scored'); cL4 = idx.get('Coral L4 Scored')
        algae_play_col = idx.get('Played Algae?(Disloged NO COUNT)')
        algae_barge_col = idx.get('Algae Scored in Barge')
        climb_col = idx.get('Climbed?')
        auto_worked_col = idx.get('Did auton worked?')
        team_col = idx.get('Team Number')
        total_matches = 0
        sum_auton_worked = 0
        sum_climb = 0
        sum_algae_play = 0
        sum_algae_barge = 0
        sumL1 = sumL2 = sumL3 = sumL4 = 0.0
        for row in self.analyzer.sheet_data[1:]:
            if team_col is None or team_col >= len(row):
                continue
            if str(row[team_col]).strip() != str(team):
                continue
            total_matches += 1
            def to_float(val):
                try:
                    if isinstance(val, str) and val.strip()=='' : return 0.0
                    return float(val)
                except Exception:
                    if isinstance(val, str) and val.lower() in ['true','yes','y','si','sí','1']:
                        return 1.0
                    if isinstance(val, str) and val.lower() in ['false','no','n','0']:
                        return 0.0
                    return 0.0
            if cL1 is not None and cL1 < len(row): sumL1 += to_float(row[cL1])
            if cL2 is not None and cL2 < len(row): sumL2 += to_float(row[cL2])
            if cL3 is not None and cL3 < len(row): sumL3 += to_float(row[cL3])
            if cL4 is not None and cL4 < len(row): sumL4 += to_float(row[cL4])
            if algae_play_col is not None and algae_play_col < len(row): sum_algae_play += to_float(row[algae_play_col])
            if algae_barge_col is not None and algae_barge_col < len(row): sum_algae_barge += to_float(row[algae_barge_col])
            if climb_col is not None and climb_col < len(row): sum_climb += to_float(row[climb_col])
            if auto_worked_col is not None and auto_worked_col < len(row): sum_auton_worked += to_float(row[auto_worked_col])
        if total_matches > 0:
            stats['L1'] = sumL1 / total_matches
            stats['L2'] = sumL2 / total_matches
            stats['L3'] = sumL3 / total_matches
            stats['L4'] = sumL4 / total_matches
            stats['matches'] = total_matches
            stats['algae_barge'] = sum_algae_barge / total_matches
            stats['played_algae'] = sum_algae_play / total_matches
            stats['climb_rate'] = sum_climb / total_matches
            stats['auto_success'] = sum_auton_worked / total_matches
        # Suavizado simple (Laplace) para piezas coral: añadir 0.2
        for level in ['L1','L2','L3','L4']:
            stats[level] = max(0.0, stats[level]) + 0.2
        self._team_stats_cache[team] = stats
        return stats

    def _predict_alliance(self, pred: AlliancePrediction):
        """Llena pred.* con valores estimados en base a promedios por equipo."""
        if not pred.teams:
            return
        # Agregar promedios
        total_auto_factor = 0.0
        for t in pred.teams:
            ts = self._compute_team_stats(t)
            auto_factor = min(1.0, ts['auto_success']) * 0.45  # fracción esperada de coral que ocurre en auto
            total_auto_factor += auto_factor
            for lvl in ['L1','L2','L3','L4']:
                avg_lvl = ts[lvl]
                auto_contrib = avg_lvl * auto_factor
                pred.auto_coral[lvl] += auto_contrib
                pred.teleop_coral[lvl] += max(0.0, avg_lvl - auto_contrib)
            # Algae -> usar played_algae como proxy para processor autos (cada 3 algae ~1 processor?)
            pred.algae_processor += ts['algae_barge'] * 0.3  # heurística
            pred.processor_auto += ts['played_algae'] * 0.1 * ts['auto_success']
            pred.processor_teleop += ts['played_algae'] * 0.2 * (1 - ts['auto_success'] + 0.5)
            # Climb -> distribuir probabilidad entre shallow/deep
            climb_p = ts['climb_rate']
            if climb_p > 0.6:
                pred.robot_climbs.append('deep')
            elif climb_p > 0.25:
                pred.robot_climbs.append('shallow')
            elif climb_p > 0.1:
                pred.robot_climbs.append('park')
            else:
                pred.robot_climbs.append('none')
        # Mantener sólo 3 climbs (si excede)
        pred.robot_climbs = pred.robot_climbs[:3]
        # Convertir a enteros razonables
        for d in [pred.auto_coral, pred.teleop_coral]:
            for k,v in d.items():
                d[k] = int(round(v,0))
        pred.processor_auto = int(round(pred.processor_auto,0))
        pred.processor_teleop = int(round(pred.processor_teleop,0))
        pred.algae_processor = int(round(pred.algae_processor,0))
        pred.net_teleop = 0  # sin datos directos aún
        # Si no hay climbs asignados (porque lista vacía), rellenar con 'none'
        while len(pred.robot_climbs) < 3:
            pred.robot_climbs.append('none')
        pred.all_leave_auto = True if total_auto_factor/ max(1,len(pred.teams)) > 0.3 else False
        # Limpiar valores extremos
        for lvl in ['L1','L2','L3','L4']:
            if pred.auto_coral[lvl] < 0: pred.auto_coral[lvl] = 0
            if pred.teleop_coral[lvl] < 0: pred.teleop_coral[lvl] = 0

    def _build_team_entry(self):
        self.win = tk.Toplevel(self.master)
        self.win.title("Foreshadowing - Selección de Equipos")
        self.win.grab_set()
        frm = ttk.Frame(self.win, padding=10)
        frm.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frm, text="Equipos RED (3)", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, padx=5, pady=5)
        ttk.Label(frm, text="Equipos BLUE (3)", font=("Segoe UI", 10, "bold")).grid(row=0, column=1, padx=5, pady=5)
        self.red_entries = []; self.blue_entries = []
        for i in range(3):
            e_red = ttk.Entry(frm, width=12); e_blue = ttk.Entry(frm, width=12)
            e_red.grid(row=i+1, column=0, padx=5, pady=2); e_blue.grid(row=i+1, column=1, padx=5, pady=2)
            self.red_entries.append(e_red); self.blue_entries.append(e_blue)
        btn_frame = ttk.Frame(frm); btn_frame.grid(row=5, column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Config Puntajes", command=self._open_config).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Aceptar", command=self._accept_teams).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=self.win.destroy).pack(side=tk.LEFT, padx=5)

    def _open_config(self):
        cfg = tk.Toplevel(self.win); cfg.title("Configurar Puntos"); cfg.grab_set()
        frame = ttk.Frame(cfg, padding=10); frame.pack(fill=tk.BOTH, expand=True)
        ttk.Label(frame, text="Coral Auto", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, pady=4, sticky='w')
        ttk.Label(frame, text="Coral TeleOp", font=("Segoe UI", 9, "bold")).grid(row=0, column=1, pady=4, sticky='w')
        self._cfg_vars = {}; levels = ["L1", "L2", "L3", "L4"]
        for r, lvl in enumerate(levels, start=1):
            var_a = tk.IntVar(value=self.config.coral_auto[lvl]); var_t = tk.IntVar(value=self.config.coral_teleop[lvl])
            ttk.Entry(frame, textvariable=var_a, width=5).grid(row=r, column=0, padx=3, pady=2)
            ttk.Entry(frame, textvariable=var_t, width=5).grid(row=r, column=1, padx=3, pady=2)
            self._cfg_vars[f"auto_{lvl}"] = var_a; self._cfg_vars[f"tele_{lvl}"] = var_t
        row = len(levels) + 2
        ttk.Label(frame, text="Processor A/T").grid(row=row, column=0, sticky='w')
        proc_a = tk.IntVar(value=self.config.processor_auto); proc_t = tk.IntVar(value=self.config.processor_teleop)
        ttk.Entry(frame, textvariable=proc_a, width=5).grid(row=row, column=1)
        ttk.Entry(frame, textvariable=proc_t, width=5).grid(row=row, column=2)
        self._cfg_vars['proc_a'] = proc_a; self._cfg_vars['proc_t'] = proc_t
        row += 1; ttk.Label(frame, text="Net TeleOp").grid(row=row, column=0, sticky='w')
        net_t = tk.IntVar(value=self.config.net_teleop); ttk.Entry(frame, textvariable=net_t, width=5).grid(row=row, column=1)
        self._cfg_vars['net_t'] = net_t
        row += 1; ttk.Label(frame, text="Processor Opp Gain").grid(row=row, column=0, sticky='w')
        proc_gain = tk.IntVar(value=self.config.processor_opponent_gain); ttk.Entry(frame, textvariable=proc_gain, width=5).grid(row=row, column=1)
        self._cfg_vars['proc_gain'] = proc_gain
        row += 1; swing_var = tk.BooleanVar(value=self.config.enable_processor_swing)
        ttk.Checkbutton(frame, text="Activar swing de Processor", variable=swing_var).grid(row=row, column=0, columnspan=2, pady=5, sticky='w')
        self._cfg_vars['swing'] = swing_var
        row += 1; ttk.Label(frame, text="Climb Points", font=("Segoe UI", 9, "bold")).grid(row=row, column=0, sticky='w', pady=(10,4))
        row += 1; climb_vars = {}
        for status in ["park", "shallow", "deep"]:
            ttk.Label(frame, text=status.capitalize()).grid(row=row, column=0, sticky='w')
            cv = tk.IntVar(value=self.config.climb_points[status]); ttk.Entry(frame, textvariable=cv, width=5).grid(row=row, column=1)
            climb_vars[status] = cv; row += 1
        self._cfg_vars['climb'] = climb_vars
        def apply_config():
            for lvl in levels:
                self.config.coral_auto[lvl] = self._cfg_vars[f"auto_{lvl}"].get()
                self.config.coral_teleop[lvl] = self._cfg_vars[f"tele_{lvl}"].get()
            self.config.processor_auto = self._cfg_vars['proc_a'].get()
            self.config.processor_teleop = self._cfg_vars['proc_t'].get()
            self.config.net_teleop = self._cfg_vars['net_t'].get()
            self.config.processor_opponent_gain = self._cfg_vars['proc_gain'].get()
            self.config.enable_processor_swing = self._cfg_vars['swing'].get()
            for k,v in self._cfg_vars['climb'].items():
                self.config.climb_points[k] = v.get()
            messagebox.showinfo("Config", "Puntajes actualizados"); cfg.destroy()
        ttk.Button(frame, text="Guardar", command=apply_config).grid(row=row, column=0, pady=10)
        ttk.Button(frame, text="Cerrar", command=cfg.destroy).grid(row=row, column=1, pady=10)

    def _accept_teams(self):
        reds = [e.get().strip() for e in self.red_entries if e.get().strip()]
        blues = [e.get().strip() for e in self.blue_entries if e.get().strip()]
        if len(reds) != 3 or len(blues) != 3:
            messagebox.showerror("Error", "Debes ingresar exactamente 3 equipos por alianza"); return
        self.pred_red.teams = reds; self.pred_blue.teams = blues
        # Autopredicción basada en datos
        # Reiniciar estructuras
        self.pred_red.auto_coral = {"L1":0,"L2":0,"L3":0,"L4":0}
        self.pred_red.teleop_coral = {"L1":0,"L2":0,"L3":0,"L4":0}
        self.pred_red.processor_auto = 0; self.pred_red.processor_teleop=0; self.pred_red.net_teleop=0; self.pred_red.algae_processor=0; self.pred_red.robot_climbs=[]
        self.pred_blue.auto_coral = {"L1":0,"L2":0,"L3":0,"L4":0}
        self.pred_blue.teleop_coral = {"L1":0,"L2":0,"L3":0,"L4":0}
        self.pred_blue.processor_auto = 0; self.pred_blue.processor_teleop=0; self.pred_blue.net_teleop=0; self.pred_blue.algae_processor=0; self.pred_blue.robot_climbs=[]
        try:
            self._predict_alliance(self.pred_red)
            self._predict_alliance(self.pred_blue)
        except Exception as ex:
            print("Foreshadowing auto prediction error:", ex)
        self.win.destroy(); self._open_prediction_window()

    def _open_prediction_window(self):
            """Ventana principal de predicción (post selección de equipos)."""
            self.pred_win = tk.Toplevel(self.master)
            self.pred_win.title("Foreshadowing - Predicción de Match")
            self.pred_win.grab_set()
            container = ttk.Frame(self.pred_win, padding=8)
            container.pack(fill=tk.BOTH, expand=True)
            top_bar = ttk.Frame(container)
            top_bar.pack(fill=tk.X, pady=4)
            ttk.Button(top_bar, text="Config Puntajes", command=self._open_config).pack(side=tk.LEFT, padx=4)
            ttk.Button(top_bar, text="Recalcular", command=self._recalculate).pack(side=tk.LEFT, padx=4)
            ttk.Button(top_bar, text="Re-predecir", command=self._auto_predict_reset).pack(side=tk.LEFT, padx=4)
            ttk.Button(top_bar, text="Stats Robots", command=self._open_robot_stats).pack(side=tk.LEFT, padx=4)
            ttk.Button(top_bar, text="Cerrar", command=self.pred_win.destroy).pack(side=tk.RIGHT, padx=4)
            ttk.Label(top_bar, text="Predicción generada automáticamente a partir de datos históricos", foreground="blue").pack(side=tk.LEFT, padx=10)
            self.red_frame = self._build_alliance_section(container, "RED", self.pred_red)
            self.blue_frame = self._build_alliance_section(container, "BLUE", self.pred_blue)
            self.result_frame = ttk.LabelFrame(container, text="Resultados")
            self.result_frame.pack(fill=tk.X, pady=8)
            self.lbl_result = ttk.Label(self.result_frame, text="")
            self.lbl_result.pack(anchor='w', padx=6, pady=4)
            self._recalculate()

    def _open_robot_stats(self):
            """Ventana con estadísticas individuales (modelo estadístico) para cada robot en el match.
            Muestra splits Auto / TeleOp por nivel, distribución de climb, prob de coop y auto.
            """
            if not (self.pred_red.teams and self.pred_blue.teams):
                messagebox.showerror("Error", "Primero selecciona equipos (Aceptar en ventana anterior)")
                return
            # Asegurar modelo estadístico
            if not hasattr(self, '_team_model') or not self._team_model:
                try:
                    self._build_statistical_model()
                except Exception as ex:
                    print("Error construyendo modelo estadístico:", ex)
            win = tk.Toplevel(self.pred_win)
            win.title("Stats Individuales de Robots")
            win.grab_set()
            frm = ttk.Frame(win, padding=6)
            frm.pack(fill=tk.BOTH, expand=True)
            cols = [
                'Team',
                'Auto L1','Tele L1','Auto L2','Tele L2','Auto L3','Tele L3','Auto L4','Tele L4',
                'Total Coral','P_auto%','Coop%','Best Climb','Exp Climb Pts',
                'Deep%','Shallow%','Park%','None%'
            ]
            tree = ttk.Treeview(frm, show='headings')
            tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
            for c in cols:
                tree["columns"] = cols
            for c in cols:
                tree.heading(c, text=c)
                tree.column(c, width=80, anchor='center')
            scroll_y = ttk.Scrollbar(frm, orient=tk.VERTICAL, command=tree.yview)
            tree.configure(yscroll=scroll_y.set)
            scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
            teams_all = [('RED', t) for t in self.pred_red.teams] + [('BLUE', t) for t in self.pred_blue.teams]
            # Usar predicción estadística por equipo
            try:
                # Bind method if not already
                if not hasattr(self, '_statistical_predict_team'):
                    self._statistical_predict_team = ForeshadowingLauncher._statistical_predict_team.__get__(self)
            except Exception:
                pass
            # Config climb points for expected value
            climb_pts = self.config.climb_points
            for alliance, team in teams_all:
                pred = self._statistical_predict_team(team)
                auto_vals = [pred.get(f'auto_L{i}',0.0) for i in range(1,5)]
                tele_vals = [pred.get(f'tele_L{i}',0.0) for i in range(1,5)]
                total_coral = sum(auto_vals)+sum(tele_vals)
                climb_dist = pred.get('climb_dist', {})
                exp_climb_pts = 0.0
                for cat, p in climb_dist.items():
                    exp_climb_pts += p * climb_pts.get(cat,0)
                def pct(x): return f"{100*x:.0f}" if isinstance(x,(int,float)) else '0'
                row = [
                    f"{alliance}-{team}",
                    *(f"{v:.2f}" for v in auto_vals),
                    *(f"{v:.2f}" for v in tele_vals),
                    f"{total_coral:.2f}",
                    pct(pred.get('p_auto',0.0)),
                    pct(pred.get('coop_prob',0.0)),
                    pred.get('best_climb','none'),
                    f"{exp_climb_pts:.2f}",
                    pct(climb_dist.get('deep',0.0)),
                    pct(climb_dist.get('shallow',0.0)),
                    pct(climb_dist.get('park',0.0)),
                    pct(climb_dist.get('none',0.0)),
                ]
                tree.insert('', 'end', values=row)
            # Nota / ayuda
            help_lbl = ttk.Label(win, text="Valores basados en medias Poisson y fracción auto = p_auto*0.45. % = porcentaje (aprox).")
            help_lbl.pack(fill=tk.X, padx=6, pady=4)

    def _build_alliance_section(self, parent, name: str, pred: AlliancePrediction):
        lf = ttk.LabelFrame(parent, text=f"Alianza {name}"); lf.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
        ttk.Label(lf, text="Equipos: " + ", ".join(pred.teams)).pack(anchor='w', padx=5, pady=(4,2))
        coral_auto_frame = ttk.LabelFrame(lf, text="Auto Coral"); coral_auto_frame.pack(fill=tk.X, padx=5, pady=3)
        pred._auto_vars = {}
        for idx, lvl in enumerate(["L1", "L2", "L3", "L4"]):
            var = tk.IntVar(value=pred.auto_coral[lvl]); ttk.Label(coral_auto_frame, text=lvl).grid(row=0, column=idx, padx=3)
            sp = ttk.Spinbox(coral_auto_frame, from_=0, to=50, width=4, textvariable=var, command=self._recalculate); sp.grid(row=1, column=idx, padx=3, pady=2)
            pred._auto_vars[lvl] = var
        coral_tel_frame = ttk.LabelFrame(lf, text="TeleOp Coral"); coral_tel_frame.pack(fill=tk.X, padx=5, pady=3)
        pred._tele_vars = {}
        for idx, lvl in enumerate(["L1", "L2", "L3", "L4"]):
            var = tk.IntVar(value=pred.teleop_coral[lvl]); ttk.Label(coral_tel_frame, text=lvl).grid(row=0, column=idx, padx=3)
            sp = ttk.Spinbox(coral_tel_frame, from_=0, to=80, width=4, textvariable=var, command=self._recalculate); sp.grid(row=1, column=idx, padx=3, pady=2)
            pred._tele_vars[lvl] = var
        misc_frame = ttk.Frame(lf); misc_frame.pack(fill=tk.X, padx=5, pady=3)
        pred._proc_auto = tk.IntVar(value=pred.processor_auto); pred._proc_tel = tk.IntVar(value=pred.processor_teleop)
        pred._net_tel = tk.IntVar(value=pred.net_teleop); pred._algae_proc = tk.IntVar(value=pred.algae_processor)
        pred._all_leave = tk.BooleanVar(value=pred.all_leave_auto)
        ttk.Label(misc_frame, text="Proc A").grid(row=0, column=0); ttk.Spinbox(misc_frame, from_=0, to=30, width=4, textvariable=pred._proc_auto, command=self._recalculate).grid(row=1, column=0)
        ttk.Label(misc_frame, text="Proc T").grid(row=0, column=1); ttk.Spinbox(misc_frame, from_=0, to=30, width=4, textvariable=pred._proc_tel, command=self._recalculate).grid(row=1, column=1)
        ttk.Label(misc_frame, text="Net T").grid(row=0, column=2); ttk.Spinbox(misc_frame, from_=0, to=30, width=4, textvariable=pred._net_tel, command=self._recalculate).grid(row=1, column=2)
        ttk.Label(misc_frame, text="Algae Proc").grid(row=0, column=3); ttk.Spinbox(misc_frame, from_=0, to=30, width=4, textvariable=pred._algae_proc, command=self._recalculate).grid(row=1, column=3)
        ttk.Checkbutton(misc_frame, text="All Leave Auto", variable=pred._all_leave, command=self._recalculate).grid(row=2, column=0, columnspan=2, sticky='w', pady=4)
        climb_frame = ttk.LabelFrame(lf, text="Climbs"); climb_frame.pack(fill=tk.X, padx=5, pady=3)
        pred._climb_vars = []; options = ["none", "park", "shallow", "deep"]
        for i in range(3):
            var = tk.StringVar(value=pred.robot_climbs[i]); cb = ttk.Combobox(climb_frame, values=options, textvariable=var, width=8, state='readonly')
            cb.grid(row=0, column=i, padx=4, pady=2); cb.bind('<<ComboboxSelected>>', lambda e: self._recalculate())
            pred._climb_vars.append(var)
        pred._summary_label = ttk.Label(lf, text="Puntos: 0 | RP: 0"); pred._summary_label.pack(anchor='w', padx=6, pady=4)
        return lf

    def _collect_from_widgets(self, pred: AlliancePrediction):
        for lvl, var in pred._auto_vars.items(): pred.auto_coral[lvl] = var.get()
        for lvl, var in pred._tele_vars.items(): pred.teleop_coral[lvl] = var.get()
        pred.processor_auto = pred._proc_auto.get(); pred.processor_teleop = pred._proc_tel.get()
        pred.net_teleop = pred._net_tel.get(); pred.algae_processor = pred._algae_proc.get()
        pred.all_leave_auto = pred._all_leave.get()
        for i, v in enumerate(pred._climb_vars): pred.robot_climbs[i] = v.get()

    def _recalculate(self):
        self._collect_from_widgets(self.pred_red); self._collect_from_widgets(self.pred_blue)
        coop_enabled = (self.pred_red.algae_processor >= 2 and self.pred_blue.algae_processor >= 2)
        self.calc.compute_alliance_points(self.pred_red, coop_enabled); self.calc.compute_alliance_points(self.pred_blue, coop_enabled)
        self.calc.apply_win_tie_rp(self.pred_red, self.pred_blue)
        if self.config.enable_processor_swing:
            blue_swing = (self.pred_red.processor_auto + self.pred_red.processor_teleop) * self.config.processor_opponent_gain
            red_swing = (self.pred_blue.processor_auto + self.pred_blue.processor_teleop) * self.config.processor_opponent_gain
            red_total = self.pred_red.total_points + red_swing; blue_total = self.pred_blue.total_points + blue_swing
        else:
            red_total = self.pred_red.total_points; blue_total = self.pred_blue.total_points
        self.pred_red._summary_label.config(text=f"Puntos: {red_total} | RP(auto/coral/win) {self.pred_red.rp_auto}/{self.pred_red.rp_coral}/{self.pred_red.rp_win_tie} -> Total RP {self.pred_red.ranking_points_total}")
        self.pred_blue._summary_label.config(text=f"Puntos: {blue_total} | RP(auto/coral/win) {self.pred_blue.rp_auto}/{self.pred_blue.rp_coral}/{self.pred_blue.rp_win_tie} -> Total RP {self.pred_blue.ranking_points_total}")
        result_txt = (f"RED {red_total} - {blue_total} BLUE\n" f"Coopertition: {'Sí' if coop_enabled else 'No'}\n" f"(Coral RP: RED {self.pred_red.rp_coral}, BLUE {self.pred_blue.rp_coral}; Auto RP: RED {self.pred_red.rp_auto}, BLUE {self.pred_blue.rp_auto})")
        self.lbl_result.config(text=result_txt)

    # --------------------------- Auto Re-Predict ------------------------- #
    def _auto_predict_reset(self):
        if not self.pred_red.teams or not self.pred_blue.teams:
            return
        # Reset structures
        for pred in (self.pred_red, self.pred_blue):
            pred.auto_coral = {"L1":0,"L2":0,"L3":0,"L4":0}
            pred.teleop_coral = {"L1":0,"L2":0,"L3":0,"L4":0}
            pred.processor_auto = 0; pred.processor_teleop=0; pred.net_teleop=0; pred.algae_processor=0; pred.robot_climbs=[]
        # Rebuild model (in case data changed)
        if self.analyzer:
            self._team_stats_cache.clear()
            self._build_statistical_model()
        self._predict_alliance(self.pred_red)
        self._predict_alliance(self.pred_blue)
        # Volcar a widgets
        for pred in (self.pred_red, self.pred_blue):
            for lvl in ['L1','L2','L3','L4']:
                pred._auto_vars[lvl].set(pred.auto_coral[lvl])
                pred._tele_vars[lvl].set(pred.teleop_coral[lvl])
            pred._proc_auto.set(pred.processor_auto); pred._proc_tel.set(pred.processor_teleop)
            pred._net_tel.set(pred.net_teleop); pred._algae_proc.set(pred.algae_processor)
            # climbs - already predicted list length 3
            for i,var in enumerate(pred._climb_vars):
                var.set(pred.robot_climbs[i])
        self._recalculate()

# --------------------------- API para Streamlit --------------------------- #

def predict_match(analyzer, red_teams: List[str], blue_teams: List[str]) -> Dict:
    """Función de alto nivel para usar en Streamlit. Retorna estructura con predicción por equipo y totales.
    Utiliza el modelo estadístico si es posible.
    """
    launcher = ForeshadowingLauncher(master=tk.Tk(), analyzer=analyzer) if False else None  # no UI
    # Crear instancia "virtual"
    fake = ForeshadowingLauncher.__new__(ForeshadowingLauncher)
    fake.analyzer = analyzer
    fake.config = ScoringConfig()
    fake._team_stats_cache = {}
    fake._build_statistical_model = ForeshadowingLauncher._build_statistical_model.__get__(fake)
    fake._compute_team_stats = ForeshadowingLauncher._compute_team_stats.__get__(fake)
    fake._team_model = {}
    fake._build_statistical_model()
    fake._statistical_predict_team = ForeshadowingLauncher._statistical_predict_team.__get__(fake)
    fake.statistical_predict_alliance = ForeshadowingLauncher.statistical_predict_alliance.__get__(fake)
    fake.simulate_match_points = ForeshadowingLauncher.simulate_match_points.__get__(fake)
    red_stats = fake.statistical_predict_alliance(red_teams)
    blue_stats = fake.statistical_predict_alliance(blue_teams)
    sim = fake.simulate_match_points(red_teams, blue_teams, simulations=200)
    return {
        'red': red_stats,
        'blue': blue_stats,
        'simulation': sim,
        'config': fake.config
    }


# --------------------------- Standalone Run --------------------------------- #

if __name__ == "__main__":
    root = tk.Tk(); root.title("Foreshadowing Standalone")
    ForeshadowingLauncher(root)
    root.mainloop()
