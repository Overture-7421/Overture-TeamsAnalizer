import csv
import json
import math
from collections import Counter, defaultdict
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from tkinter import simpledialog
from allianceSelector import AllianceSelector, Team, teams_from_dicts
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from school_system import TeamScoring, BehaviorReportType

class AnalizadorRobot:
    def __init__(self, default_column_names=None):
        """
        Inicializa el analizador.

        Args:
            default_column_names (list, optional): Nombres de columna predeterminados.
                                                  Si no se proveen, se esperará que el primer
                                                  archivo CSV o QR defina los encabezados.
        """
        self.default_column_names = default_column_names if default_column_names else [
            "Lead Scouter", "Highlights Scouter Name", "Scouter Name", "Match Number",
            "Future Alliance in Qualy?", "Team Number",
            "Did something?", "Did Foul?", "Did auton worked?",
            "Coral L1 Scored", "Coral L2 Scored", "Coral L3 Scored", "Coral L4 Scored",
            "Played Algae?(Disloged NO COUNT)", "Algae Scored in Barge",
            "Crossed Feild/Played Defense?", "Tipped/Fell Over?",
            "Died?", "Was the robot Defended by someone?", "Yellow/Red Card", "Climbed?"
        ]
        
        # Configuración de columnas por fase del juego
        self._autonomous_columns = []
        self._teleop_columns = []
        self._endgame_columns = []
        
        # sheetData es un List<List<String>> cuya primera fila es siempre el encabezado.
        self.sheet_data = []
        if self.default_column_names:
            self.sheet_data.append(list(self.default_column_names)) # Copia de la lista

        # _columnIndices mapea cada nombre de columna a su índice numérico para acceder rápido.
        self._column_indices = {}
        self._update_column_indices()

        # El usuario puede afinar tres conjuntos de columnas:
        # Numéricas para cálculo global (_selectedNumericColumnsForOverall)
        self._selected_numeric_columns_for_overall = []
        # Para la tabla de estadísticas (_selectedStatsColumns)
        self._selected_stats_columns = []
        # Booleanas cuyo modo (valor más frecuente) se muestre (_modeBooleanColumns)
        self._mode_boolean_columns = []
        
        # Inicializar selecciones de columnas (podría ser más sofisticado)
        self._initialize_selected_columns()

        # --- RobotValuation phase weights and boundaries ---
        self.robot_valuation_phase_weights = [0.2, 0.3, 0.5]  # Default: Q1=0.2, Q2=0.3, Q3=0.5
        self.robot_valuation_phase_names = ["Q1", "Q2", "Q3"]

    def _update_column_indices(self):
        """
        Actualiza el mapeo de nombres de columna a sus índices numéricos.
        Se llama cada vez que el encabezado de sheet_data cambia.
        """
        self._column_indices.clear()
        if not self.sheet_data or not self.sheet_data[0]:
            # Si sheet_data está vacío o no tiene encabezado, no hay nada que mapear.
            # Podríamos usar default_column_names si están disponibles y sheet_data[0] no.
            if self.default_column_names:
                 for i, col_name in enumerate(self.default_column_names):
                    self._column_indices[col_name] = i
            return

        header = self.sheet_data[0]
        for i, col_name in enumerate(header):
            self._column_indices[col_name.strip()] = i
        
        # Auto-detectar columnas por fase del juego si no están configuradas
        if not self._autonomous_columns or not self._teleop_columns or not self._endgame_columns:
            self._auto_detect_game_phase_columns()
        
        # Podríamos reinicializar las columnas seleccionadas aquí si el encabezado cambia.
        # self._initialize_selected_columns() # Descomentar si es necesario

    def _initialize_selected_columns(self):
        """
        Inicializa las listas de columnas seleccionadas con valores predeterminados,
        siguiendo la lógica Dart: overall = corales, stats = todas menos identificadores,
        mode = vacío (usuario elige).
        """
        current_header = self.sheet_data[0] if self.sheet_data else self.default_column_names
        default_overall_columns = [
            'Coral L1 Scored', 'Coral L2 Scored', 'Coral L3 Scored', 'Coral L4 Scored', 'Climbed?'
        ]
        self._selected_numeric_columns_for_overall = [
            col for col in default_overall_columns if col in current_header
        ]
        excluded_from_stats = ["Lead Scouter", "Scouter Name", "Highlights Scouter Name"]
        self._selected_stats_columns = [
            col for col in current_header if col not in excluded_from_stats
        ]
        self._mode_boolean_columns = []  # El usuario elige, por defecto vacío

    def _auto_detect_game_phase_columns(self):
        """
        Auto-detecta columnas por fase del juego basándose en palabras clave en los nombres.
        """
        if not self.sheet_data or not self.sheet_data[0]:
            return
            
        header = self.sheet_data[0]
        
        # Palabras clave para identificar fases del juego
        autonomous_keywords = ['auton', 'auto', 'autonomous', 'did something', 'did foul', 'worked']
        teleop_keywords = ['coral', 'algae', 'barge', 'processor', 'crossed', 'defense', 'defended', 'teleop']
        endgame_keywords = ['climb', 'endgame', 'end game', 'tipped', 'fell over', 'died']
        
        # Limpiar listas actuales si están siendo auto-detectadas
        if not self._autonomous_columns:
            self._autonomous_columns = []
        if not self._teleop_columns:
            self._teleop_columns = []
        if not self._endgame_columns:
            self._endgame_columns = []
            
        for col_name in header:
            col_lower = col_name.lower()
            
            # Verificar autonomous
            if any(keyword in col_lower for keyword in autonomous_keywords):
                if col_name not in self._autonomous_columns:
                    self._autonomous_columns.append(col_name)
            
            # Verificar teleop
            elif any(keyword in col_lower for keyword in teleop_keywords):
                if col_name not in self._teleop_columns:
                    self._teleop_columns.append(col_name)
            
            # Verificar endgame
            elif any(keyword in col_lower for keyword in endgame_keywords):
                if col_name not in self._endgame_columns:
                    self._endgame_columns.append(col_name)

    def set_autonomous_columns(self, column_names_list):
        """Configura manualmente las columnas de autonomous"""
        self._autonomous_columns = column_names_list.copy()
        
    def set_teleop_columns(self, column_names_list):
        """Configura manualmente las columnas de teleop"""
        self._teleop_columns = column_names_list.copy()
        
    def set_endgame_columns(self, column_names_list):
        """Configura manualmente las columnas de endgame"""
        self._endgame_columns = column_names_list.copy()
        
    def get_autonomous_columns(self):
        """Obtiene la lista de columnas de autonomous"""
        return self._autonomous_columns.copy()
        
    def get_teleop_columns(self):
        """Obtiene la lista de columnas de teleop"""
        return self._teleop_columns.copy()
        
    def get_endgame_columns(self):
        """Obtiene la lista de columnas de endgame"""
        return self._endgame_columns.copy()

    def calculate_team_phase_scores(self, team_number):
        """
        Calcula los puntajes de autonomous, teleop y endgame para un equipo específico.
        Retorna un diccionario con los puntajes promedio de cada fase.
        """
        team_data = self.get_team_data_grouped().get(str(team_number), [])
        if not team_data:
            return {"autonomous": 0, "teleop": 0, "endgame": 0}
            
        # Calcular promedios para cada fase
        phase_scores = {"autonomous": 0, "teleop": 0, "endgame": 0}
        
        # Autonomous
        if self._autonomous_columns:
            auto_values = []
            for row in team_data:
                for col_name in self._autonomous_columns:
                    if col_name in self._column_indices:
                        col_idx = self._column_indices[col_name]
                        if col_idx < len(row):
                            try:
                                # Convertir booleanos y strings a números
                                val = row[col_idx]
                                if isinstance(val, str):
                                    if val.lower() in ['true', 'yes', 'y', '1', 'si', 'sí']:
                                        auto_values.append(100)
                                    elif val.lower() in ['false', 'no', 'n', '0']:
                                        auto_values.append(0)
                                    else:
                                        auto_values.append(float(val))
                                elif isinstance(val, bool):
                                    auto_values.append(100 if val else 0)
                                else:
                                    auto_values.append(float(val))
                            except (ValueError, TypeError):
                                pass
            phase_scores["autonomous"] = sum(auto_values) / len(auto_values) if auto_values else 0
            
        # Teleop
        if self._teleop_columns:
            teleop_values = []
            for row in team_data:
                for col_name in self._teleop_columns:
                    if col_name in self._column_indices:
                        col_idx = self._column_indices[col_name]
                        if col_idx < len(row):
                            try:
                                val = row[col_idx]
                                if isinstance(val, str):
                                    if val.lower() in ['true', 'yes', 'y', '1', 'si', 'sí']:
                                        teleop_values.append(100)
                                    elif val.lower() in ['false', 'no', 'n', '0']:
                                        teleop_values.append(0)
                                    else:
                                        teleop_values.append(float(val))
                                elif isinstance(val, bool):
                                    teleop_values.append(100 if val else 0)
                                else:
                                    teleop_values.append(float(val))
                            except (ValueError, TypeError):
                                pass
            phase_scores["teleop"] = sum(teleop_values) / len(teleop_values) if teleop_values else 0
            
        # Endgame
        if self._endgame_columns:
            endgame_values = []
            for row in team_data:
                for col_name in self._endgame_columns:
                    if col_name in self._column_indices:
                        col_idx = self._column_indices[col_name]
                        if col_idx < len(row):
                            try:
                                val = row[col_idx]
                                if isinstance(val, str):
                                    if val.lower() in ['true', 'yes', 'y', '1', 'si', 'sí']:
                                        endgame_values.append(100)
                                    elif val.lower() in ['false', 'no', 'n', '0']:
                                        endgame_values.append(0)
                                    else:
                                        endgame_values.append(float(val))
                                elif isinstance(val, bool):
                                    endgame_values.append(100 if val else 0)
                                else:
                                    endgame_values.append(float(val))
                            except (ValueError, TypeError):
                                pass
            phase_scores["endgame"] = sum(endgame_values) / len(endgame_values) if endgame_values else 0
            
        return phase_scores

    def _find_potential_numeric_columns(self, header, sample_data_row=None):
        """
        Intenta adivinar qué columnas son numéricas basándose en una fila de datos de muestra.
        Similar a _findPotentialNumericColumns en Dart.
        """
        potential_columns = []
        if not sample_data_row: # Si no hay datos, no podemos adivinar
            return potential_columns

        excluded_keywords = [
            'Team Number', 'Match Number', 'Scouter', 'Name', 'Defense?', 'Did ', 'Was ', 'Played ', 'Card', 'Climbed', 'Tipped', 'Died'
        ]

        for idx, col_name in enumerate(header):
            # Evitar columnas que claramente no son para promedios numéricos generales
            if any(keyword.lower() in col_name.lower() for keyword in excluded_keywords):
                continue
            
            if idx < len(sample_data_row):
                try:
                    float(sample_data_row[idx])
                    potential_columns.append(col_name)
                except (ValueError, TypeError):
                    pass # No es un número
        return potential_columns

    def _find_potential_boolean_columns(self, header, sample_data_row=None):
        """
        Intenta adivinar qué columnas son booleanas basándose en nombres y, opcionalmente, datos.
        Similar a _findPotentialBooleanColumns en Dart.
        """
        potential_columns = []
        # Palabras clave que suelen indicar columnas booleanas o categóricas simples
        boolean_keywords = ['?', 'did', 'was', 'played', 'climbed', 'card', 'tipped', 'foul', 'worked', 'something', 'defended']
        # Columnas que NO deberían ser booleanas (más bien numéricas o de identificación)
        excluded_from_boolean = [
            'Team Number', 'Match Number', 'Scouter', 'Name', 'Coral L', 'Algae Scored'
        ]
        
        # Obtener columnas identificadas como numéricas para excluirlas de las booleanas
        numeric_cols = []
        if self.sheet_data and len(self.sheet_data) > 1:
            numeric_cols = self._find_potential_numeric_columns(header, self.sheet_data[1])
        elif sample_data_row:
             numeric_cols = self._find_potential_numeric_columns(header, sample_data_row)


        for col_name in header:
            col_name_lower = col_name.lower()
            
            # Excluir si está en la lista de exclusión explícita
            if any(ex_keyword.lower() in col_name_lower for ex_keyword in excluded_from_boolean):
                continue
            
            # Excluir si ya fue identificada como numérica
            if col_name in numeric_cols:
                continue

            # Heurística basada en palabras clave
            if any(keyword.lower() in col_name_lower for keyword in boolean_keywords):
                potential_columns.append(col_name)
            # Podríamos añadir más heurísticas si es necesario, como comprobar valores (true/false, yes/no)
            # en una fila de muestra si sample_data_row está disponible.

        return list(set(potential_columns)) # Eliminar duplicados

    def update_header(self, new_header_str):
        """
        Actualiza los nombres de las columnas del encabezado.
        Args:
            new_header_str (str): Una cadena con los nombres de columna separados por comas.
        """
        new_header = [name.strip() for name in new_header_str.split(',')]
        if not self.sheet_data:
            self.sheet_data.append(new_header)
        else:
            self.sheet_data[0] = new_header
        self._update_column_indices()
        self._initialize_selected_columns() # Re-inicializar selecciones con nuevo encabezado
        print(f"Encabezado actualizado a: {self.sheet_data[0]}")

    def load_csv(self, file_path):
        """
        Carga datos desde un archivo CSV.
        Usa FilePicker para seleccionar un .csv, lee su contenido (bytes o ruta),
        lo parte por líneas y comas y lo añade a sheetData.

        Args:
            file_path (str): La ruta al archivo CSV.
        """
        try:
            with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
                reader = csv.reader(csvfile)
                csv_rows = [row for row in reader if any(field.strip() for field in row)] # Ignorar filas vacías

            if not csv_rows:
                print("Archivo CSV está vacío o no contiene datos.")
                return

            # Si sheet_data está vacío o solo tiene el encabezado por defecto (y no datos reales)
            if not self.sheet_data or (len(self.sheet_data) == 1 and not any(self.sheet_data[0])): 
                self.sheet_data = csv_rows
                print(f"Datos CSV cargados. {len(self.sheet_data)} filas (incluyendo encabezado).")
            else:
                # Si ya hay datos, comparar encabezados
                current_header = self.sheet_data[0]
                csv_header = csv_rows[0]
                if current_header == csv_header:
                    self.sheet_data.extend(csv_rows[1:]) # Añadir solo datos
                    print(f"Datos CSV añadidos. Total {len(self.sheet_data)} filas.")
                else:
                    # Opción 1: Reemplazar todo si los encabezados no coinciden (más simple)
                    # print("Advertencia: Encabezado del CSV no coincide con el existente. Reemplazando todos los datos.")
                    # self.sheet_data = csv_rows
                    # Opción 2: Solo añadir datos, manteniendo el encabezado original (como en el código Dart)
                    print("Advertencia: Encabezado del CSV no coincide con el existente. Añadiendo solo filas de datos.")
                    self.sheet_data.extend(csv_rows[1:])
            
            self._update_column_indices()
            self._initialize_selected_columns() # Asegurarse que las selecciones se actualizan
        except FileNotFoundError:
            print(f"Error: Archivo no encontrado en {file_path}")
        except Exception as e:
            print(f"Error al cargar CSV: {e}")

    def load_qr_data(self, qr_string_data):
        """
        Procesa datos desde un string de QR codes.
        Maneja diferentes formatos: texto simple, CSV, o datos separados por tabuladores.
        Añade los datos como nuevas filas en la tabla raw data.

        Args:
            qr_string_data (str): String con los datos del QR, puede contener múltiples líneas.
        """
        if not qr_string_data.strip():
            print("Datos de QR vacíos.")
            return

        print(f"Procesando datos QR: {qr_string_data}")

        # Asegurar que tenemos un encabezado
        if not self.sheet_data or not self.sheet_data[0]:
            if self.default_column_names:
                self.sheet_data = [list(self.default_column_names)]
                print(f"Inicializando con encabezado por defecto: {len(self.default_column_names)} columnas")
            else:
                print("Error: No hay un encabezado definido para los datos QR.")
                return

        current_headers = self.sheet_data[0]
        num_columns = len(current_headers)

        # Procesar cada línea del QR
        lines = qr_string_data.strip().split('\n')
        new_rows_added = 0

        for line in lines:
            if not line.strip():
                continue

            # Intentar diferentes métodos de parsing
            row_data = None

            # Método 1: Datos separados por tabuladores
            if '\t' in line:
                row_data = [field.strip() for field in line.split('\t')]
                print(f"Parseado como datos tabulados: {len(row_data)} campos")

            # Método 2: Datos separados por comas (CSV)
            elif ',' in line and line.count(',') >= 2:
                row_data = [field.strip() for field in line.split(',')]
                print(f"Parseado como CSV: {len(row_data)} campos")

            # Método 3: Datos separados por punto y coma
            elif ';' in line:
                row_data = [field.strip() for field in line.split(';')]
                print(f"Parseado como datos separados por ';': {len(row_data)} campos")

            # Método 4: Texto simple - crear una fila con el texto en la primera columna
            else:
                row_data = [line.strip()]
                # Rellenar el resto de columnas con valores vacíos
                while len(row_data) < num_columns:
                    row_data.append("")
                print(f"Parseado como texto simple en {num_columns} columnas")

            # Ajustar el número de campos para que coincida con el encabezado
            if row_data:
                # Si hay menos campos, rellenar con vacíos
                while len(row_data) < num_columns:
                    row_data.append("")
                
                # Si hay más campos, truncar
                if len(row_data) > num_columns:
                    row_data = row_data[:num_columns]
                    print(f"Truncando a {num_columns} campos para coincidir con el encabezado")

                # Añadir la fila a los datos
                self.sheet_data.append(row_data)
                new_rows_added += 1
                print(f"Fila añadida: {row_data}")

        print(f"Datos de QR procesados. {new_rows_added} filas añadidas. Total: {len(self.sheet_data)} filas.")
        
        # Actualizar índices después de añadir datos
        self._update_column_indices()
        # y el encabezado no cambió. Si el encabezado PUDIERA cambiar con QR, entonces sí.

    # --- Funciones de Cálculo Estadístico ---
    def _average(self, values):
        """Calcula el promedio de una lista de números."""
        if not values: return 0.0
        return sum(values) / len(values)

    def _standard_deviation(self, values):
        """Calcula la desviación estándar de una lista de números."""
        if not values or len(values) < 1: return 0.0 # Devuelve 0 si no hay suficientes datos
        n = len(values)
        mean = self._average(values)
        sum_sq_diff = sum((x - mean) ** 2 for x in values)
        # Para desviación estándar poblacional, dividir entre n.
        # Para desviación estándar muestral, dividir entre n-1.
        # El código Dart divide entre n (poblacional).
        if n == 0: return 0.0 # Evitar división por cero
        return math.sqrt(sum_sq_diff / n)


    def _calculate_mode(self, values):
        """Calcula la moda de una lista de strings."""
        if not values: return 'N/A'
        non_empty_values = [v for v in values if str(v).strip()]
        if not non_empty_values: return 'N/A'
        
        counts = Counter(non_empty_values)
        max_freq = counts.most_common(1)[0][1]
        modes = [val for val, freq in counts.items() if freq == max_freq]
        # Si hay múltiples modas, Dart devuelve la primera encontrada por groupListsBy.
        # Counter.most_common devuelve una lista, así que podemos tomar la primera.
        # Python_version <=3.7 Counter no preserva el orden de inserción. Python 3.7+ sí.
        # Para ser consistente con el groupListsBy de Dart que toma el primero, podemos simplemente retornar modes[0]
        # o si el orden no importa tanto, unirlos.
        return modes[0] # Devuelve una de las modas si hay varias.

    def _rate_from_strs(self, str_vals):
        true_like = {'true', 'yes', 'y', '1', 'si', 'sí', 'verdadero'}
        false_like = {'false', 'no', 'n', '0', 'falso'}
        bools = []
        for s in str_vals:
            lv = s.lower()
            if lv in true_like:
                bools.append(1.0)
            elif lv in false_like:
                bools.append(0.0)
        return self._average(bools) if bools else 0.0

    def get_raw_data(self):
        """Devuelve los datos crudos (sheet_data)."""
        return self.sheet_data

    def get_team_data_grouped(self):
        # Agrupa filas por número de equipo, igual que en Dart
        if len(self.sheet_data) < 2:
            return {}
        team_number_col_name = "Team Number"
        if team_number_col_name not in self._column_indices:
            if "Team" in self._column_indices:
                team_number_col_name = "Team"
            else:
                return {}
        team_col_idx = self._column_indices[team_number_col_name]
        team_rows_map = defaultdict(list)
        for row in self.sheet_data[1:]:
            if team_col_idx < len(row):
                team_number = row[team_col_idx].strip()
                if team_number:
                    team_rows_map[team_number].append(row)
        return dict(team_rows_map)

    def _generate_stat_key(self, col_name, stat_type):
        # Lógica idéntica a Dart para las claves
        if col_name in ['teleop_coral', 'teleop_algae']:
            return f'{col_name}_{stat_type}'
        base = col_name.replace('?', '') \
                       .replace('(Disloged NO COUNT)', '') \
                       .replace('(Disloged DOES NOT COUNT)', '') \
                       .replace('/', '_') \
                       .replace(' ', '_') \
                       .lower()
        specific_renames = {
            'End Position': 'climb',
            'Climbed?': 'climb',
            'Did something?': 'auto_did_something',
            'Did Foul?': 'auto_did_foul',
            'Did auton worked?': 'auto_worked',
            'Barge Algae Scored': 'teleop_barge_algae',
            'Algae Scored in Barge': 'teleop_barge_algae',
            'Processor Algae Scored': 'teleop_processor_algae',
            'Played Algae?(Disloged NO COUNT)': 'teleop_played_algae',
            'Played Algae?(Disloged DOES NOT COUNT)': 'teleop_played_algae',
            'Crossed Feild/Played Defense?': 'teleop_crossed_played_defense',
            'Was the robot Defended by alguien?': 'defended_by_other'
        }
        if col_name in specific_renames:
            base = specific_renames[col_name]
        return f'{base}_{stat_type}'

    def get_detailed_team_stats(self):
        # Procesa estadísticas exactamente como el Dart
        if len(self.sheet_data) < 2:
            return []
        team_data_grouped = self.get_team_data_grouped()
        if not team_data_grouped:
            return []
        detailed_stats_list = []
        coral_algae_groups = {
            'teleop_coral': [
                'Coral L1 Scored', 'Coral L2 Scored',
                'Coral L3 Scored', 'Coral L4 Scored'
            ],
            'teleop_algae': [
                'Algae Scored in Barge'
            ]
        }
        for team_number, rows in team_data_grouped.items():
            team_stats = {'team': team_number}
            # Coral y algae: avg y std
            for group_name, columns in coral_algae_groups.items():
                group_values = []
                for col_name in columns:
                    col_idx = self._column_indices.get(col_name)
                    if col_idx is None:
                        continue
                    for row in rows:
                        if col_idx < len(row):
                            try:
                                group_values.append(float(row[col_idx]))
                            except Exception:
                                pass
                avg_key = self._generate_stat_key(group_name, 'avg')
                std_key = self._generate_stat_key(group_name, 'std')
                team_stats[avg_key] = self._average(group_values) if group_values else 0.0
                team_stats[std_key] = self._standard_deviation(group_values) if group_values else 0.0
            # Individual coral/algae columns
            individual_numeric_columns = []
            for columns in coral_algae_groups.values():
                individual_numeric_columns.extend(columns)
            individual_numeric_columns = list(set(individual_numeric_columns))
            for col_name in individual_numeric_columns:
                col_idx = self._column_indices.get(col_name)
                if col_idx is None:
                    continue
                values = []
                for row in rows:
                    if col_idx < len(row):
                        try:
                            values.append(float(row[col_idx]))
                        except Exception:
                            pass
                avg_key = self._generate_stat_key(col_name, 'avg')
                std_key = self._generate_stat_key(col_name, 'std')
                team_stats[avg_key] = self._average(values) if values else 0.0
                team_stats[std_key] = self._standard_deviation(values) if values else 0.0
            # Defensa (rate)
            defense_col = 'Crossed Feild/Played Defense?'
            defense_idx = self._column_indices.get(defense_col)
            defense_values = []
            if defense_idx is not None:
                for row in rows:
                    if defense_idx < len(row):
                        v = row[defense_idx].strip().lower()
                        if v in ['true', 'yes', 'y', '1']:
                            defense_values.append(1.0)
                        elif v in ['false', 'no', 'n', '0']:
                            defense_values.append(0.0)
                defense_key = self._generate_stat_key(defense_col, 'rate')
                team_stats[defense_key] = self._average(defense_values) if defense_values else 0.0
            # Overall avg y std (solo columnas seleccionadas)
            overall_values = []
            for col_name in self._selected_numeric_columns_for_overall:
                col_idx = self._column_indices.get(col_name)
                if col_idx is None:
                    continue
                for row in rows:
                    if col_idx < len(row):
                        try:
                            overall_values.append(float(row[col_idx]))
                        except Exception:
                            pass
            team_stats['overall_avg'] = self._average(overall_values) if overall_values else 0.0
            team_stats['overall_std'] = self._standard_deviation(overall_values) if overall_values else 0.0
            # Booleanas: rate y mode si corresponde
            for col_name in self._selected_stats_columns:
                if col_name in individual_numeric_columns or col_name in ['Team Number', 'Match Number']:
                    continue
                col_idx = self._column_indices.get(col_name)
                if col_idx is None:
                    continue
                str_vals = [row[col_idx] for row in rows if col_idx < len(row)]
                # Rate
                rate_key = self._generate_stat_key(col_name, 'rate')
                team_stats[rate_key] = self._rate_from_strs(str_vals)
                # Mode solo si está seleccionada
                if col_name in self._mode_boolean_columns:
                    mode_key = self._generate_stat_key(col_name, 'mode')
                    team_stats[mode_key] = self._calculate_mode(str_vals)
            # --- RobotValuation ---
            team_stats['RobotValuation'] = self._robot_valuation(rows)
            detailed_stats_list.append(team_stats)
        detailed_stats_list.sort(key=lambda x: (x.get('overall_avg', 0.0), -x.get('overall_std', float('inf'))), reverse=True)
        return detailed_stats_list

    def get_defensive_robot_ranking(self):
        # Ranking defensivo igual que Dart
        all_team_stats = self.get_detailed_team_stats()
        if not all_team_stats:
            return []
        defense_col_name = "Crossed Feild/Played Defense?"
        defense_rate_key = self._generate_stat_key(defense_col_name, 'rate')
        died_col_name = "Died?"
        moved_col_name = "Did something?"
        died_rate_key = self._generate_stat_key(died_col_name, 'rate')
        moved_rate_key = self._generate_stat_key(moved_col_name, 'rate')
        defensive_ranking = []
        for stats in all_team_stats:
            current_defense_rate = stats.get(defense_rate_key, 0.0)
            if current_defense_rate > 0:
                rank_entry = {
                    'team': stats['team'],
                    'defense_rate': current_defense_rate,
                    'overall_avg': stats.get('overall_avg', 0.0),
                    'died_rate': stats.get(died_rate_key, 0.0),
                    'moved_rate': stats.get(moved_rate_key, 0.0)
                }
                defensive_ranking.append(rank_entry)
        defensive_ranking.sort(key=lambda x: x['defense_rate'], reverse=True)
        return defensive_ranking

    # --- Funciones para configurar columnas seleccionadas por el usuario ---
    def set_selected_numeric_columns_for_overall(self, column_names_list):
        """Establece las columnas numéricas para el cálculo del promedio general."""
        self._selected_numeric_columns_for_overall = [
            name for name in column_names_list if name in self._column_indices
        ]
        print(f"Columnas para promedio general: {self._selected_numeric_columns_for_overall}")

    def set_selected_stats_columns(self, column_names_list):
        """Establece las columnas que se mostrarán/calcularán en la tabla de estadísticas detalladas."""
        self._selected_stats_columns = [
            name for name in column_names_list if name in self._column_indices
        ]
        print(f"Columnas para tabla de estadísticas: {self._selected_stats_columns}")

    def set_mode_boolean_columns(self, column_names_list):
        """Establece las columnas booleanas para las cuales se calculará el modo."""
        self._mode_boolean_columns = [
            name for name in column_names_list if name in self._column_indices
        ]
        print(f"Columnas para cálculo de modo: {self._mode_boolean_columns}")

    def get_current_headers(self):
        """Devuelve los encabezados de columna actuales."""
        return list(self.sheet_data[0]) if self.sheet_data and self.sheet_data[0] else list(self.default_column_names)

    def set_robot_valuation_phase_weights(self, weights):
        """Set user-defined weights for Q1, Q2, Q3 phases. Expects a list of 3 floats summing to 1.0."""
        if len(weights) != 3 or not all(isinstance(w, (float, int)) for w in weights):
            raise ValueError("Weights must be a list of 3 numbers.")
        total = sum(weights)
        if not (0.99 < total < 1.01):
            raise ValueError("Weights must sum to 1.0")
        self.robot_valuation_phase_weights = [float(w) for w in weights]

    def get_robot_valuation_phase_weights(self):
        return list(self.robot_valuation_phase_weights)

    def _split_rows_into_phases(self, rows):
        """Split rows into 3 phases (Q1, Q2, Q3) as evenly as possible."""
        n = len(rows)
        if n == 0:
            return [[], [], []]
        # Split indices
        q1_end = n // 3
        q2_end = 2 * n // 3
        q1 = rows[:q1_end]
        q2 = rows[q1_end:q2_end]
        q3 = rows[q2_end:]
        return [q1, q2, q3]

    def _robot_valuation(self, rows):
        """Calculate RobotValuation as weighted avg of selected numeric columns, split by phases."""
        if not rows or not self._selected_numeric_columns_for_overall:
            return 0.0
        phases = self._split_rows_into_phases(rows)
        phase_weights = self.robot_valuation_phase_weights
        phase_avgs = []
        for phase_rows in phases:
            vals = []
            for col_name in self._selected_numeric_columns_for_overall:
                col_idx = self._column_indices.get(col_name)
                if col_idx is None:
                    continue
                for row in phase_rows:
                    if col_idx < len(row):
                        try:
                            vals.append(float(row[col_idx]))
                        except Exception:
                            pass
            phase_avgs.append(self._average(vals) if vals else 0.0)
        # Weighted sum
        return sum(w * v for w, v in zip(phase_weights, phase_avgs))

    def get_team_match_performance(self, team_numbers=None):
        """
        Returns a dict: {team_number: [(match_number, overall_for_that_match), ...]}
        Only includes teams in team_numbers (if provided), else all.
        """
        if len(self.sheet_data) < 2:
            return {}
        team_col = self._column_indices.get("Team Number")
        match_col = self._column_indices.get("Match Number")
        if team_col is None or match_col is None:
            return {}
        # Build per-team, per-match
        perf = {}
        for row in self.sheet_data[1:]:
            if team_col >= len(row) or match_col >= len(row):
                continue
            team = row[team_col].strip()
            match = row[match_col].strip()
            if not team or not match:
                continue
            try:
                match_num = int(match)
            except Exception:
                continue
            # Compute "overall" for this row
            vals = []
            for col_name in self._selected_numeric_columns_for_overall:
                idx = self._column_indices.get(col_name)
                if idx is not None and idx < len(row):
                    try:
                        vals.append(float(row[idx]))
                    except Exception:
                        pass
            overall = sum(vals) / len(vals) if vals else 0.0
            if team_numbers is not None and team not in team_numbers:
                continue
            perf.setdefault(team, []).append((match_num, overall))
        # Sort matches by match number
        for team in perf:
            perf[team].sort(key=lambda x: x[0])
        return perf

    def export_columns_config(self, file_path):
        """
        Exporta la configuración actual de columnas a un archivo JSON.
        
        Args:
            file_path (str): Ruta donde guardar el archivo JSON
        """
        config = {
            "version": "1.0",
            "timestamp": f"{tk.TkVersion}",
            "headers": self.get_current_headers(),
            "column_configuration": {
                "numeric_for_overall": self._selected_numeric_columns_for_overall,
                "stats_columns": self._selected_stats_columns,
                "mode_boolean_columns": self._mode_boolean_columns,
                "autonomous_columns": self._autonomous_columns,
                "teleop_columns": self._teleop_columns,
                "endgame_columns": self._endgame_columns
            },
            "robot_valuation": {
                "phase_weights": self.robot_valuation_phase_weights,
                "phase_names": self.robot_valuation_phase_names
            },
            "metadata": {
                "total_columns": len(self.get_current_headers()),
                "description": "Alliance Simulator Column Configuration"
            }
        }
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=4, ensure_ascii=False)
            print(f"Configuración exportada exitosamente a: {file_path}")
            return True
        except Exception as e:
            print(f"Error al exportar configuración: {e}")
            return False

    def import_columns_config(self, file_path):
        """
        Importa la configuración de columnas desde un archivo JSON.
        
        Args:
            file_path (str): Ruta del archivo JSON a importar
            
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            # Validar estructura básica
            if "column_configuration" not in config:
                return False, "Archivo JSON no contiene configuración de columnas válida"
            
            col_config = config["column_configuration"]
            current_headers = self.get_current_headers()
            
            # Validar que las columnas en el archivo existen en los datos actuales
            missing_columns = []
            
            # Validar columnas numéricas para overall
            if "numeric_for_overall" in col_config:
                numeric_cols = col_config["numeric_for_overall"]
                missing = [col for col in numeric_cols if col not in current_headers]
                if missing:
                    missing_columns.extend(missing)
                else:
                    self._selected_numeric_columns_for_overall = numeric_cols
            
            # Validar columnas de estadísticas
            if "stats_columns" in col_config:
                stats_cols = col_config["stats_columns"]
                missing = [col for col in stats_cols if col not in current_headers]
                if missing:
                    missing_columns.extend(missing)
                else:
                    self._selected_stats_columns = stats_cols
            
            # Validar columnas booleanas de modo
            if "mode_boolean_columns" in col_config:
                mode_cols = col_config["mode_boolean_columns"]
                missing = [col for col in mode_cols if col not in current_headers]
                if missing:
                    missing_columns.extend(missing)
                else:
                    self._mode_boolean_columns = mode_cols
            
            # Validar columnas de autonomous
            if "autonomous_columns" in col_config:
                auto_cols = col_config["autonomous_columns"]
                missing = [col for col in auto_cols if col not in current_headers]
                if missing:
                    missing_columns.extend(missing)
                else:
                    self._autonomous_columns = auto_cols
            
            # Validar columnas de teleop
            if "teleop_columns" in col_config:
                teleop_cols = col_config["teleop_columns"]
                missing = [col for col in teleop_cols if col not in current_headers]
                if missing:
                    missing_columns.extend(missing)
                else:
                    self._teleop_columns = teleop_cols
            
            # Validar columnas de endgame
            if "endgame_columns" in col_config:
                endgame_cols = col_config["endgame_columns"]
                missing = [col for col in endgame_cols if col not in current_headers]
                if missing:
                    missing_columns.extend(missing)
                else:
                    self._endgame_columns = endgame_cols
            
            # Importar configuración de RobotValuation si existe
            if "robot_valuation" in config:
                robot_val = config["robot_valuation"]
                if "phase_weights" in robot_val and len(robot_val["phase_weights"]) == 3:
                    weights = robot_val["phase_weights"]
                    if abs(sum(weights) - 1.0) < 0.01:  # Verificar que sumen ~1.0
                        self.robot_valuation_phase_weights = weights
            
            if missing_columns:
                missing_unique = list(set(missing_columns))
                return False, f"Las siguientes columnas no existen en los datos actuales: {', '.join(missing_unique)}"
            
            print(f"Configuración importada exitosamente desde: {file_path}")
            return True, "Configuración importada exitosamente"
            
        except FileNotFoundError:
            return False, "Archivo no encontrado"
        except json.JSONDecodeError:
            return False, "Error al decodificar JSON - archivo corrupto o formato inválido"
        except Exception as e:
            return False, f"Error al importar configuración: {str(e)}"

    def get_columns_config_summary(self):
        """
        Retorna un resumen de la configuración actual de columnas.
        
        Returns:
            dict: Resumen de la configuración
        """
        return {
            "total_headers": len(self.get_current_headers()),
            "numeric_for_overall_count": len(self._selected_numeric_columns_for_overall),
            "stats_columns_count": len(self._selected_stats_columns),
            "mode_boolean_count": len(self._mode_boolean_columns),
            "autonomous_columns_count": len(self._autonomous_columns),
            "teleop_columns_count": len(self._teleop_columns),
            "endgame_columns_count": len(self._endgame_columns),
            "robot_valuation_weights": self.robot_valuation_phase_weights,
            "game_phases_configured": {
                "autonomous": self._autonomous_columns,
                "teleop": self._teleop_columns,
                "endgame": self._endgame_columns
            }
        }

# GUI Application
class AnalizadorGUI:
    def __init__(self, root, analizador):
        self.root = root
        self.analizador = analizador
        self.root.title("Alliance Simulator Analyzer")
        # Initialize SchoolSystem
        self.school_system = TeamScoring()
        self.create_widgets()

    def create_widgets(self):
        # Layout container
        frame = ttk.Frame(self.root, padding=8)
        frame.pack(fill=tk.BOTH, expand=True)

        # Top buttons
        btn_frame = ttk.Frame(frame)
        btn_frame.pack(side=tk.TOP, fill=tk.X, pady=5)
        buttons = [
            ("Load CSV", self.load_csv),
            ("Real-Time QR Scanner", self.scan_and_load_qr),
            ("Test Camera", self.test_camera),
            ("Paste QR Data", self.load_qr),
            ("Update Header", self.update_header),
            ("Configure Columns", self.configure_columns),
            ("Game Phase Config", self.show_phase_config),
            ("RobotValuation Weights", self.configure_robot_valuation_weights),
            ("Plot Team Performance", self.open_team_performance_plot),
            ("SchoolSystem", self.open_school_system),
            ("Foreshadowing", self.open_foreshadowing),
        ]
        for text, cmd in buttons:
            ttk.Button(btn_frame, text=text, command=cmd).pack(side=tk.LEFT, padx=4, pady=2)
        ttk.Button(btn_frame, text="About", command=self.show_about).pack(side=tk.RIGHT, padx=4, pady=2)

        # Status bar
        self.status_var = tk.StringVar()
        status_bar = ttk.Label(frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Notebook
        self.notebook = ttk.Notebook(frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        # Raw Data Tab
        self.raw_frame = ttk.Frame(self.notebook)
        raw_controls = ttk.Frame(self.raw_frame)
        raw_controls.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        raw_btns = [
            ("Edit Selected Row", self.edit_raw_data_row),
            ("Delete Selected Row", self.delete_raw_data_row),
            ("Add New Row", self.add_raw_data_row),
            ("Save Changes", self.save_raw_data_changes),
        ]
        for txt, cmd in raw_btns[:-1]:
            ttk.Button(raw_controls, text=txt, command=cmd).pack(side=tk.LEFT, padx=2)
        ttk.Button(raw_controls, text=raw_btns[-1][0], command=raw_btns[-1][1]).pack(side=tk.RIGHT, padx=2)
        self.tree_raw = ttk.Treeview(self.raw_frame, show='headings')
        self.tree_raw.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        self.tree_raw.bind("<Double-1>", self.on_raw_data_double_click)
        scrollbar_raw_y = ttk.Scrollbar(self.raw_frame, orient=tk.VERTICAL, command=self.tree_raw.yview)
        scrollbar_raw_x = ttk.Scrollbar(self.raw_frame, orient=tk.HORIZONTAL, command=self.tree_raw.xview)
        self.tree_raw.configure(yscroll=scrollbar_raw_y.set, xscroll=scrollbar_raw_x.set)
        scrollbar_raw_y.pack(side=tk.LEFT, fill=tk.Y)
        scrollbar_raw_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.notebook.add(self.raw_frame, text="Raw Data")

        # Team Stats Tab
        self.stats_frame = ttk.Frame(self.notebook)
        self.tree_stats = ttk.Treeview(self.stats_frame, show='headings')
        self.tree_stats.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scrollbar_stats_y = ttk.Scrollbar(self.stats_frame, orient=tk.VERTICAL, command=self.tree_stats.yview)
        scrollbar_stats_x = ttk.Scrollbar(self.stats_frame, orient=tk.HORIZONTAL, command=self.tree_stats.xview)
        self.tree_stats.configure(yscroll=scrollbar_stats_y.set, xscroll=scrollbar_stats_x.set)
        scrollbar_stats_y.pack(side=tk.LEFT, fill=tk.Y)
        scrollbar_stats_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.notebook.add(self.stats_frame, text="Team Stats")

        # Defensive Ranking Tab
        self.def_frame = ttk.Frame(self.notebook)
        self.tree_def = ttk.Treeview(self.def_frame, show='headings')
        self.tree_def.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scrollbar_def_y = ttk.Scrollbar(self.def_frame, orient=tk.VERTICAL, command=self.tree_def.yview)
        scrollbar_def_x = ttk.Scrollbar(self.def_frame, orient=tk.HORIZONTAL, command=self.tree_def.xview)
        self.tree_def.configure(yscroll=scrollbar_def_y.set, xscroll=scrollbar_def_x.set)
        scrollbar_def_y.pack(side=tk.LEFT, fill=tk.Y)
        scrollbar_def_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.notebook.add(self.def_frame, text="Defensive Ranking")

        # Alliance Selector Tab
        self.alliance_frame = ttk.Frame(self.notebook)
        # --- Add a canvas for horizontal scrolling of the entire alliance tab ---
        self.alliance_canvas = tk.Canvas(self.alliance_frame)
        self.alliance_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.alliance_inner_frame = ttk.Frame(self.alliance_canvas)
        self.alliance_inner_frame_id = self.alliance_canvas.create_window((0, 0), window=self.alliance_inner_frame, anchor="nw")
        # Horizontal and vertical scrollbars for the canvas
        scrollbar_alliance_y = ttk.Scrollbar(self.alliance_frame, orient=tk.VERTICAL, command=self.alliance_canvas.yview)
        scrollbar_alliance_x = ttk.Scrollbar(self.alliance_frame, orient=tk.HORIZONTAL, command=self.alliance_canvas.xview)
        self.alliance_canvas.configure(yscrollcommand=scrollbar_alliance_y.set, xscrollcommand=scrollbar_alliance_x.set)
        scrollbar_alliance_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_alliance_x.pack(side=tk.BOTTOM, fill=tk.X)
        # Treeview inside the scrollable frame
        self.tree_alliance = ttk.Treeview(self.alliance_inner_frame, show='headings')
        self.tree_alliance.pack(fill=tk.BOTH, expand=True, side=tk.TOP)
        self.notebook.add(self.alliance_frame, text="Alliance Selector")
        # Bind resizing
        def _on_frame_configure(event):
            self.alliance_canvas.configure(scrollregion=self.alliance_canvas.bbox("all"))
        self.alliance_inner_frame.bind("<Configure>", _on_frame_configure)
        # Mousewheel horizontal scroll
        def _on_mousewheel(event):
            if event.state & 0x1:  # Shift is held
                self.alliance_canvas.xview_scroll(int(-1*(event.delta/120)), "units")
        self.alliance_canvas.bind_all("<MouseWheel>", _on_mousewheel)

        # Honor Roll System Tab
        self.honor_roll_frame = ttk.Frame(self.notebook)
        
        # Honor Roll controls
        honor_controls = ttk.Frame(self.honor_roll_frame)
        honor_controls.pack(side=tk.TOP, fill=tk.X, padx=5, pady=5)
        ttk.Button(honor_controls, text="Auto-populate from Team Data", command=self.auto_populate_school_system).pack(side=tk.LEFT, padx=2)
        ttk.Button(honor_controls, text="Manual Team Entry", command=self.manual_team_entry).pack(side=tk.LEFT, padx=2)
        ttk.Button(honor_controls, text="Edit Team Scores", command=self.edit_team_scores).pack(side=tk.LEFT, padx=2)
        ttk.Button(honor_controls, text="Export Honor Roll", command=self.export_honor_roll).pack(side=tk.RIGHT, padx=2)
        
        self.tree_honor_roll = ttk.Treeview(self.honor_roll_frame, show='headings')
        self.tree_honor_roll.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        
        scrollbar_honor_y = ttk.Scrollbar(self.honor_roll_frame, orient=tk.VERTICAL, command=self.tree_honor_roll.yview)
        scrollbar_honor_x = ttk.Scrollbar(self.honor_roll_frame, orient=tk.HORIZONTAL, command=self.tree_honor_roll.xview)
        self.tree_honor_roll.configure(yscroll=scrollbar_honor_y.set, xscroll=scrollbar_honor_x.set)
        scrollbar_honor_y.pack(side=tk.RIGHT, fill=tk.Y)
        scrollbar_honor_x.pack(side=tk.BOTTOM, fill=tk.X)
        self.notebook.add(self.honor_roll_frame, text="Honor Roll System")

        # For dropdowns in the alliance selector
        self.alliance_selector = None
        self.alliance_pick_vars = []  # List of (pick1_var, pick2_var) for each alliance

        # Mejorar resize de columnas
        for tree in [self.tree_raw, self.tree_stats, self.tree_def, self.tree_alliance, self.tree_honor_roll]:
            tree["displaycolumns"] = "#all"
            tree.tag_configure('highlight', background='#f0f0ff')

        self.refresh_all()

    def show_about(self):
        messagebox.showinfo(
            "About",
            "Alliance Simulator Analyzer\n\n"
            "Developed with Tkinter.\n"
            "Features:\n"
            "- CSV/QR data import\n"
            "- Interactive column configuration\n"
            "- Stats and defensive ranking\n"
            "- 3 significant digits for numbers\n"
            "- Combined avg±std columns\n"
        )

    def load_csv(self):
        path = filedialog.askopenfilename(filetypes=[("CSV Files","*.csv")])
        if path:
            self.analizador.load_csv(path)
            self.status_var.set(f"Loaded CSV: {os.path.basename(path)}")
            self.refresh_all()

    def scan_and_load_qr(self):
        """Handles the QR scanning process with real-time updates to the table."""
        try:
            # Test if required libraries are available
            import cv2
            import pyzbar
            print("OpenCV and pyzbar libraries are available.")
        except ImportError as e:
            messagebox.showerror(
                "Missing Dependencies", 
                f"Required libraries not found: {e}\n\n"
                "Please install:\n"
                "- pip install opencv-python\n"
                "- pip install pyzbar\n\n"
                "On some systems, you may also need to install ZBar library separately."
            )
            return
        
        try:
            # Import the scanner function
            from qr_scanner import scan_qr_codes
            print("QR scanner module imported successfully.")
        except ImportError as e:
            messagebox.showerror("Import Error", f"Failed to import QR scanner: {e}")
            return

        # Confirm with user before starting camera
        response = messagebox.askyesno(
            "Start Real-Time QR Scanner", 
            "This will open your camera for QR code scanning with REAL-TIME updates.\n\n"
            "• The Raw Data table will update immediately when QR codes are detected\n"
            "• The main application will remain open and visible\n"
            "• You can watch the table update in real-time!\n\n"
            "Make sure your camera is not being used by another application.\n\n"
            "Press 'q' in the scanner window to stop scanning.\n\n"
            "Continue with real-time scanning?"
        )
        
        if not response:
            return

        # Define the real-time update callback
        def real_time_update_callback(qr_data):
            """
            This function is called immediately when a QR code is detected.
            It updates the Raw Data table in real-time.
            """
            try:
                print(f"Processing QR data in real-time: {qr_data}")
                
                # Load the QR data immediately into the analyzer
                self.analizador.load_qr_data(qr_data)
                
                # Update the GUI immediately
                self.refresh_raw_data_only()
                
                # Update status bar
                total_rows = len(self.analizador.sheet_data) - 1  # -1 for header
                self.status_var.set(f"Real-time update: New QR data added! Total rows: {total_rows}")
                
                # Force GUI update
                self.root.update_idletasks()
                
                print(f"✓ Real-time table update completed. Total rows: {total_rows}")
                
            except Exception as e:
                print(f"Error in real-time update callback: {e}")
                self.status_var.set(f"Error in real-time update: {e}")

        self.status_var.set("Real-time QR scanner starting... Data will update immediately when detected!")
        self.root.update()  # Update the UI
        
        try:
            print("Starting real-time QR scanner...")
            # Pass the callback to enable real-time updates
            scanned_data = scan_qr_codes(update_callback=real_time_update_callback)
            print(f"QR scanner finished. Total codes processed: {len(scanned_data)}")
            
            # Final refresh after scanning is complete
            self.refresh_all()
            
            if scanned_data:
                total_rows = len(self.analizador.sheet_data) - 1
                self.status_var.set(f"Real-time scanning completed! {len(scanned_data)} codes processed. Total rows: {total_rows}")
                messagebox.showinfo("Real-Time Scanning Complete", 
                                  f"¡Escaneo en tiempo real completado!\n\n"
                                  f"• {len(scanned_data)} códigos QR procesados\n"
                                  f"• Datos actualizados en tiempo real en Raw Data\n"
                                  f"• Total de filas: {total_rows}")
            else:
                self.status_var.set("Real-time scanning ended - no new codes detected.")
                messagebox.showinfo("Scanning Complete", "Escaneo terminado.\n\n"
                                  "No se detectaron códigos QR nuevos.\n\n"
                                  "Asegúrese de que:\n"
                                  "• Los códigos QR sean claros y legibles\n"
                                  "• Haya buena iluminación\n"
                                  "• La cámara esté enfocada correctamente")
        except Exception as e:
            print(f"Error during real-time QR scanning: {e}")
            messagebox.showerror("QR Scanner Error", f"Error durante el escaneo en tiempo real:\n\n{e}")
            self.status_var.set("Real-time QR scanning failed.")

    def load_qr(self):
        data = simpledialog.askstring("QR Data", "Enter QR data (tab-separated):")
        if data:
            self.analizador.load_qr_data(data)
            self.status_var.set("QR data loaded.")
            self.refresh_all()

    def update_header(self):
        header = simpledialog.askstring("Update Header", "Enter comma-separated column names:")
        if header:
            self.analizador.update_header(header)
            self.status_var.set("Header updated.")
            self.refresh_all()

    def configure_columns(self):
        # Ventana interactiva con checkboxes para selección intuitiva
        cfg = tk.Toplevel(self.root)
        cfg.title("Configure Columns")
        cfg.transient(self.root)
        cfg.grab_set()
        cfg.geometry("800x600")
        
        headers = self.analizador.get_current_headers()

        # Frame principal con scroll
        main_frame = tk.Frame(cfg)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Frame para botones de Import/Export en la parte superior
        import_export_frame = tk.Frame(main_frame)
        import_export_frame.pack(fill=tk.X, pady=(0, 10))

        tk.Label(import_export_frame, text="Gestión de Configuraciones:", 
                font=("Arial", 12, "bold")).pack(anchor=tk.W)
        
        buttons_frame = tk.Frame(import_export_frame)
        buttons_frame.pack(fill=tk.X, pady=5)

        def export_config():
            file_path = filedialog.asksaveasfilename(
                title="Exportar Configuración de Columnas",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            if file_path:
                if self.analizador.export_columns_config(file_path):
                    messagebox.showinfo("Éxito", f"Configuración exportada exitosamente a:\n{file_path}")
                else:
                    messagebox.showerror("Error", "Error al exportar la configuración")

        def import_config():
            file_path = filedialog.askopenfilename(
                title="Importar Configuración de Columnas",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            if file_path:
                success, message = self.analizador.import_columns_config(file_path)
                if success:
                    messagebox.showinfo("Éxito", message)
                    # Actualizar las variables de checkboxes con la nueva configuración
                    for h in headers:
                        var_nums[h].set(h in self.analizador._selected_numeric_columns_for_overall)
                        var_stats[h].set(h in self.analizador._selected_stats_columns)
                        var_modes[h].set(h in self.analizador._mode_boolean_columns)
                        # Actualizar variables de fases del juego
                        var_auto[h].set(h in self.analizador.get_autonomous_columns())
                        var_teleop[h].set(h in self.analizador.get_teleop_columns())
                        var_endgame[h].set(h in self.analizador.get_endgame_columns())
                else:
                    messagebox.showerror("Error", message)

        tk.Button(buttons_frame, text="📤 Exportar Configuración", command=export_config, 
                 bg="#4CAF50", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        tk.Button(buttons_frame, text="📥 Importar Configuración", command=import_config,
                 bg="#2196F3", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT)

        # Separador
        separator = tk.Frame(main_frame, height=2, bg="gray")
        separator.pack(fill=tk.X, pady=10)

        # Variables para checkboxes
        var_nums = {h: tk.BooleanVar(value=h in self.analizador._selected_numeric_columns_for_overall) for h in headers}
        var_stats = {h: tk.BooleanVar(value=h in self.analizador._selected_stats_columns) for h in headers}
        var_modes = {h: tk.BooleanVar(value=h in self.analizador._mode_boolean_columns) for h in headers}
        
        # Variables para fases del juego
        var_auto = {h: tk.BooleanVar(value=h in self.analizador.get_autonomous_columns()) for h in headers}
        var_teleop = {h: tk.BooleanVar(value=h in self.analizador.get_teleop_columns()) for h in headers}
        var_endgame = {h: tk.BooleanVar(value=h in self.analizador.get_endgame_columns()) for h in headers}

        # Frame con scroll para los checkboxes
        canvas = tk.Canvas(main_frame)
        scrollbar = tk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)

        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        frm = ttk.Frame(scrollable_frame)
        frm.pack(padx=10, pady=10)

        # Add a title and headers
        ttk.Label(frm, text="Select columns for each category:", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=6, pady=(0,8))
        
        # Headers para columnas generales
        ttk.Label(frm, text="Numeric for overall", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, padx=5, pady=5)
        ttk.Label(frm, text="Stats columns", font=("Segoe UI", 9, "bold")).grid(row=1, column=1, padx=5, pady=5)
        ttk.Label(frm, text="Mode boolean", font=("Segoe UI", 9, "bold")).grid(row=1, column=2, padx=5, pady=5)
        
        # Headers para fases del juego
        tk.Label(frm, text="Autonomous", font=("Segoe UI", 9, "bold"), fg="blue").grid(row=1, column=3, padx=5, pady=5)
        tk.Label(frm, text="Teleop", font=("Segoe UI", 9, "bold"), fg="green").grid(row=1, column=4, padx=5, pady=5)
        tk.Label(frm, text="Endgame", font=("Segoe UI", 9, "bold"), fg="red").grid(row=1, column=5, padx=5, pady=5)

        # Crear columnas de checkboxes
        for i, h in enumerate(headers):
            ttk.Checkbutton(frm, text=h, variable=var_nums[h]).grid(row=i+2, column=0, sticky='w')
            ttk.Checkbutton(frm, text=h, variable=var_stats[h]).grid(row=i+2, column=1, sticky='w')
            ttk.Checkbutton(frm, text=h, variable=var_modes[h]).grid(row=i+2, column=2, sticky='w')
            # Checkboxes para fases del juego
            ttk.Checkbutton(frm, text=h, variable=var_auto[h]).grid(row=i+2, column=3, sticky='w')
            ttk.Checkbutton(frm, text=h, variable=var_teleop[h]).grid(row=i+2, column=4, sticky='w')
            ttk.Checkbutton(frm, text=h, variable=var_endgame[h]).grid(row=i+2, column=5, sticky='w')

        def apply_cfg():
            sel_nums  = [h for h in headers if var_nums[h].get()]
            sel_stats = [h for h in headers if var_stats[h].get()]
            sel_modes = [h for h in headers if var_modes[h].get()]
            
            # Aplicar configuración de fases del juego
            sel_auto = [h for h in headers if var_auto[h].get()]
            sel_teleop = [h for h in headers if var_teleop[h].get()]
            sel_endgame = [h for h in headers if var_endgame[h].get()]
            
            self.analizador.set_selected_numeric_columns_for_overall(sel_nums)
            self.analizador.set_selected_stats_columns(sel_stats)
            self.analizador.set_mode_boolean_columns(sel_modes)
            
            # Configurar fases del juego
            self.analizador.set_autonomous_columns(sel_auto)
            self.analizador.set_teleop_columns(sel_teleop)
            self.analizador.set_endgame_columns(sel_endgame)
            
            cfg.destroy()
            self.refresh_all()

        # Botones en la parte inferior
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Apply", command=apply_cfg).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=cfg.destroy).pack(side=tk.RIGHT, padx=5)

        # Configurar el canvas y scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        # Bind mousewheel to canvas
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        canvas.bind("<MouseWheel>", _on_mousewheel)
        
        cfg.wait_window()

    def configure_robot_valuation_weights(self):
        # Dialog for user to set Q1, Q2, Q3 weights
        cfg = tk.Toplevel(self.root)
        cfg.title("Configure RobotValuation Weights")
        cfg.transient(self.root)
        cfg.grab_set()
        ttk.Label(cfg, text="Set weights for Q1, Q2, Q3 phases (must sum to 1.0):").pack(padx=10, pady=(10, 0))
        weights = self.analizador.get_robot_valuation_phase_weights()
        vars = [tk.DoubleVar(value=w) for w in weights]
        frm = ttk.Frame(cfg)
        frm.pack(padx=10, pady=10)
        for i, name in enumerate(self.analizador.robot_valuation_phase_names):
            ttk.Label(frm, text=f"{name} weight:").grid(row=i, column=0, sticky='e', padx=5, pady=3)
            ttk.Entry(frm, textvariable=vars[i], width=8).grid(row=i, column=1, padx=5, pady=3)
        msg_var = tk.StringVar()
        ttk.Label(cfg, textvariable=msg_var, foreground="red").pack()
        def apply():
            try:
                vals = [v.get() for v in vars]
                total = sum(vals)
                if not (0.99 < total < 1.01):
                    msg_var.set("Weights must sum to 1.0")
                    return
                self.analizador.set_robot_valuation_phase_weights(vals)
                cfg.destroy()
                self.refresh_all()
            except Exception as e:
                msg_var.set(str(e))
        ttk.Button(cfg, text="Apply", command=apply).pack(pady=(0,10))
        ttk.Button(cfg, text="Close", command=cfg.destroy).pack()
        cfg.wait_window()

    def show_phase_config(self):
        """Show current game phase column configuration"""
        cfg = tk.Toplevel(self.root)
        cfg.title("Game Phase Column Configuration")
        cfg.transient(self.root)
        cfg.grab_set()
        cfg.geometry("600x500")
        
        main_frame = tk.Frame(cfg)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Title
        ttk.Label(main_frame, text="Current Game Phase Column Configuration", 
                 font=("Arial", 12, "bold")).pack(pady=(0, 10))
        
        # Create notebook for different phases
        phase_notebook = ttk.Notebook(main_frame)
        phase_notebook.pack(fill=tk.BOTH, expand=True)
        
        # Autonomous tab
        auto_frame = ttk.Frame(phase_notebook)
        phase_notebook.add(auto_frame, text="Autonomous")
        
        ttk.Label(auto_frame, text="Autonomous Columns:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=5)
        auto_columns = self.analizador.get_autonomous_columns()
        if auto_columns:
            for col in auto_columns:
                ttk.Label(auto_frame, text=f"• {col}").pack(anchor=tk.W, padx=20)
        else:
            ttk.Label(auto_frame, text="No autonomous columns configured", 
                     foreground="gray").pack(anchor=tk.W, padx=20)
        
        # Teleop tab
        teleop_frame = ttk.Frame(phase_notebook)
        phase_notebook.add(teleop_frame, text="Teleop")
        
        ttk.Label(teleop_frame, text="Teleop Columns:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=5)
        teleop_columns = self.analizador.get_teleop_columns()
        if teleop_columns:
            for col in teleop_columns:
                ttk.Label(teleop_frame, text=f"• {col}").pack(anchor=tk.W, padx=20)
        else:
            ttk.Label(teleop_frame, text="No teleop columns configured", 
                     foreground="gray").pack(anchor=tk.W, padx=20)
        
        # Endgame tab
        endgame_frame = ttk.Frame(phase_notebook)
        phase_notebook.add(endgame_frame, text="Endgame")
        
        ttk.Label(endgame_frame, text="Endgame Columns:", font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=5)
        endgame_columns = self.analizador.get_endgame_columns()
        if endgame_columns:
            for col in endgame_columns:
                ttk.Label(endgame_frame, text=f"• {col}").pack(anchor=tk.W, padx=20)
        else:
            ttk.Label(endgame_frame, text="No endgame columns configured", 
                     foreground="gray").pack(anchor=tk.W, padx=20)
        
        # Summary tab
        summary_frame = ttk.Frame(phase_notebook)
        phase_notebook.add(summary_frame, text="Summary")
        
        ttk.Label(summary_frame, text="Configuration Summary:", 
                 font=("Arial", 10, "bold")).pack(anchor=tk.W, pady=5)
        
        summary = self.analizador.get_columns_config_summary()
        summary_text = f"""
        Total Headers: {summary['total_headers']}
        
        Game Phase Columns:
        • Autonomous: {summary['autonomous_columns_count']} columns
        • Teleop: {summary['teleop_columns_count']} columns  
        • Endgame: {summary['endgame_columns_count']} columns
        
        Other Columns:
        • Numeric for Overall: {summary['numeric_for_overall_count']} columns
        • Stats Columns: {summary['stats_columns_count']} columns
        • Mode Boolean: {summary['mode_boolean_count']} columns
        """
        
        ttk.Label(summary_frame, text=summary_text, justify=tk.LEFT).pack(anchor=tk.W, padx=20)
        
        # Buttons
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=(10, 0))
        
        ttk.Button(button_frame, text="Configure Columns", 
                  command=lambda: [cfg.destroy(), self.configure_columns()]).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Auto-detect Phases", 
                  command=lambda: [self.analizador._auto_detect_game_phase_columns(), 
                                   cfg.destroy(), self.show_phase_config()]).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=cfg.destroy).pack(side=tk.RIGHT, padx=5)

    def refresh_table(self, tree, columns, rows):
        tree.delete(*tree.get_children())
        tree["columns"] = columns
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=120, anchor=tk.W)
        for row in rows:
            if len(row) < len(columns):
                row = list(row) + [''] * (len(columns) - len(row))
            elif len(row) > len(columns):
                row = row[:len(columns)]
            formatted_row = []
            for i, val in enumerate(row):
                col = columns[i]
                if col.lower() == "team number" or col.lower() == "team":
                    formatted_row.append(val)
                elif isinstance(val, (float, int)):
                    formatted_row.append(f"{val:.3g}")
                elif isinstance(val, str):
                    try:
                        fval = float(val)
                        formatted_row.append(f"{fval:.3g}")
                    except Exception:
                        formatted_row.append(val)
                else:
                    formatted_row.append(val)
            tree.insert("", tk.END, values=formatted_row)

    def refresh_all(self):
        # Update column indices in case data structure changed
        self.analizador._update_column_indices()
        
        # Raw Data
        raw = self.analizador.get_raw_data()
        if raw:
            headers = raw[0]
            data = raw[1:]
            self.refresh_table(self.tree_raw, headers, data)
        # Team Stats
        stats = self.analizador.get_detailed_team_stats()
        if stats:
            # --- Build columns: Team, RobotValuation, Overall (avg±std), ...rest ---
            stat_keys = list(stats[0].keys())
            columns = []
            avgstd_map = {}
            skip_keys = set()
            # Always put 'team' first, then 'RobotValuation', then 'overall_avg'+'overall_std' as one column
            if 'team' in stat_keys:
                columns.append('team')
            if 'RobotValuation' in stat_keys:
                columns.append('RobotValuation')
            if 'overall_avg' in stat_keys and 'overall_std' in stat_keys:
                columns.append('overall (avg±std)')
                avgstd_map['overall (avg±std)'] = ('overall_avg', 'overall_std')
                skip_keys.add('overall_avg')
                skip_keys.add('overall_std')
            # Now add the rest, skipping those already added
            for k in stat_keys:
                if k in columns or k in skip_keys:
                    continue
                if k.endswith('_avg') and k.replace('_avg', '_std') in stat_keys and not k.startswith('overall'):
                    base = k[:-4]
                    col_label = f"{base} (avg±std)"
                    columns.append(col_label)
                    avgstd_map[col_label] = (f"{base}_avg", f"{base}_std")
                    skip_keys.add(k)
                    skip_keys.add(f"{base}_std")
                elif k not in skip_keys and not k.endswith('_std'):
                    columns.append(k)
            rows = []
            for s in stats:
                row = []
                for col in columns:
                    if col in avgstd_map:
                        avg_key, std_key = avgstd_map[col]
                        avg = s.get(avg_key, 0.0)
                        std = s.get(std_key, 0.0)
                        avg_fmt = f"{avg:.3g}"
                        std_fmt = f"{std:.3g}"
                        row.append(f"{avg_fmt} ± {std_fmt}")
                    else:
                        val = s.get(col)
                        if col.lower() == "team number" or col.lower() == "team":
                            row.append(val)
                        elif isinstance(val, (float, int)):
                            row.append(f"{val:.3g}")
                        elif isinstance(val, str):
                            try:
                                fval = float(val)
                                row.append(f"{fval:.3g}")
                            except Exception:
                                row.append(val)
                        else:
                            row.append(val)
                rows.append(row)
            self.refresh_table(self.tree_stats, columns, rows)
        # Defensive Ranking
        ranking = self.analizador.get_defensive_robot_ranking()
        if ranking:
            columns = list(ranking[0].keys())
            rows = []
            for r in ranking:
                row = []
                for i, col in enumerate(columns):
                    val = r.get(col)
                    if col.lower() == "team number" or col.lower() == "team":
                        row.append(val)
                    elif isinstance(val, (float, int)):
                        row.append(f"{val:.3g}")
                    elif isinstance(val, str):
                        try:
                            fval = float(val)
                            row.append(f"{fval:.3g}")
                        except Exception:
                            row.append(val)
                    else:
                        row.append(val)
                rows.append(row)
            self.refresh_table(self.tree_def, columns, rows)
        self.refresh_alliance_selector_tab()
        self.refresh_honor_roll_tab()
        self.status_var.set("BELIEVE")

    def refresh_raw_data_only(self):
        """
        Actualiza solo la tabla Raw Data sin recalcular estadísticas.
        Optimizada para actualizaciones en tiempo real durante el escaneo QR.
        """
        # Update column indices in case data structure changed
        self.analizador._update_column_indices()
        
        # Raw Data only
        raw = self.analizador.get_raw_data()
        if raw:
            headers = raw[0]
            data = raw[1:]
            self.refresh_table(self.tree_raw, headers, data)
            print(f"Raw data table refreshed with {len(data)} rows")

    def refresh_alliance_selector_tab(self):
        stats = self.analizador.get_detailed_team_stats()
        if not stats:
            self.tree_alliance.delete(*self.tree_alliance.get_children())
            self.tree_alliance["columns"] = ["Alliance #", "Captain", "Pick 1", "Recommendation 1", "Pick 2", "Recommendation 2", "Alliance Score"]
            # Remove previous controls if any
            if hasattr(self, 'alliance_selector_controls') and self.alliance_selector_controls:
                self.alliance_selector_controls.destroy()
                self.alliance_selector_controls = None
            return

        team_dicts = []
        for idx, s in enumerate(stats):
            team_dicts.append({
                "num": s.get("team"),
                "rank": idx + 1,
                "total_epa": s.get("overall_avg", 0),
                "auto_epa": s.get("teleop_coral_avg", 0),
                "teleop_epa": s.get("teleop_algae_avg", 0),
                "endgame_epa": 0,
                "defense": s.get("teleop_crossed_played_defense_rate", 0) > 0.5,
                "name": s.get("team")
            })
        teams = teams_from_dicts(team_dicts)

        if not hasattr(self, 'alliance_selector') or self.alliance_selector is None or len(self.alliance_selector.teams) != len(teams):
            self.alliance_selector = AllianceSelector(teams)
        selector = self.alliance_selector

        table = selector.get_alliance_table()
        columns = ["Alliance #", "Captain", "Pick 1", "Recommendation 1", "Pick 2", "Recommendation 2", "Alliance Score"]
        self.tree_alliance.delete(*self.tree_alliance.get_children())
        self.tree_alliance["columns"] = columns
        for col in columns:
            self.tree_alliance.heading(col, text=col)
            self.tree_alliance.column(col, width=120, anchor=tk.W)

        for row in table:
            values = [
                row["Alliance #"],
                row["Captain"],
                row["Pick 1"],
                row["Recommendation 1"],
                row["Pick 2"],
                row["Recommendation 2"],
                row["Alliance Score"]
            ]
            self.tree_alliance.insert("", tk.END, values=values)

        # --- Add Comboboxes for interactive pick selection ---
        # Remove previous controls if any
        if hasattr(self, 'alliance_selector_controls') and self.alliance_selector_controls:
            self.alliance_selector_controls.destroy()
        self.alliance_selector_controls = ttk.Frame(self.alliance_frame)
        self.alliance_selector_controls.pack(fill=tk.X, padx=4, pady=4)

        ttk.Label(self.alliance_selector_controls, text="Alliance #").grid(row=0, column=0)
        ttk.Label(self.alliance_selector_controls, text="Pick 1").grid(row=0, column=1)
        ttk.Label(self.alliance_selector_controls, text="Pick 2").grid(row=0, column=2)

        self._alliance_selector_combos = []
        for idx, a in enumerate(selector.alliances):
            ttk.Label(self.alliance_selector_controls, text=str(a.allianceNumber)).grid(row=idx+1, column=0, sticky='w')

            # Pick 1 Combobox
            pick1_var = tk.StringVar(value=str(a.pick1) if a.pick1 else "")
            available_pick1 = selector.get_available_teams(a.captainRank, 'pick1')
            pick1_options = [("", "No selection")] + [(str(t.team), f"{t.team} (Score: {t.score:.1f})") for t in available_pick1]
            pick1_combo = ttk.Combobox(self.alliance_selector_controls, textvariable=pick1_var,
                                       values=[label for _, label in pick1_options], state="readonly", width=18)
            # Set current value
            if a.pick1:
                for val, label in pick1_options:
                    if val == str(a.pick1):
                        pick1_combo.set(label)
                        break
            else:
                pick1_combo.set(pick1_options[0][1])
            def on_pick1(event, idx=idx, pick1_var=pick1_var, pick1_options=pick1_options):
                selected_label = pick1_var.get()
                selected_team = ""
                for val, label in pick1_options:
                    if label == selected_label:
                        selected_team = val
                        break
                if selected_team == "":
                    selector.alliances[idx].pick1 = None
                else:
                    try:
                        selector.set_pick(idx, 'pick1', selected_team)
                    except Exception as e:
                        messagebox.showerror("Alliance Selector", str(e))
                        selector.alliances[idx].pick1 = None
                selector.update_alliance_captains()
                selector.update_recommendations()
                self.refresh_alliance_selector_tab()
            pick1_combo.bind("<<ComboboxSelected>>", on_pick1)
            pick1_combo.grid(row=idx+1, column=1, sticky='w')
            self._alliance_selector_combos.append(pick1_combo)

            # Pick 2 Combobox
            pick2_var = tk.StringVar(value=str(a.pick2) if a.pick2 else "")
            available_pick2 = selector.get_available_teams(a.captainRank, 'pick2')
            pick2_options = [("", "No selection")] + [(str(t.team), f"{t.team} (Score: {t.score:.1f})") for t in available_pick2]
            pick2_combo = ttk.Combobox(self.alliance_selector_controls, textvariable=pick2_var,
                                       values=[label for _, label in pick2_options], state="readonly", width=18)
            if a.pick2:
                for val, label in pick2_options:
                    if val == str(a.pick2):
                        pick2_combo.set(label)
                        break
            else:
                pick2_combo.set(pick2_options[0][1])
            def on_pick2(event, idx=idx, pick2_var=pick2_var, pick2_options=pick2_options):
                selected_label = pick2_var.get()
                selected_team = ""
                for val, label in pick2_options:
                    if label == selected_label:
                        selected_team = val
                        break
                if selected_team == "":
                    selector.alliances[idx].pick2 = None
                else:
                    try:
                        selector.set_pick(idx, 'pick2', selected_team)
                    except Exception as e:
                        messagebox.showerror("Alliance Selector", str(e))
                        selector.alliances[idx].pick2 = None
                selector.update_alliance_captains()
                selector.update_recommendations()
                self.refresh_alliance_selector_tab()
            pick2_combo.bind("<<ComboboxSelected>>", on_pick2)
            pick2_combo.grid(row=idx+1, column=2, sticky='w')
            self._alliance_selector_combos.append(pick2_combo)

    def open_alliance_selector(self):
        # Use current team stats to build teams for alliance selection
        stats = self.analizador.get_detailed_team_stats()
        if not stats:
            messagebox.showinfo("Alliance Selector", "No team stats available.")
            return
        # Convert stats to Team objects
        team_dicts = []
        for s in stats:
            team_dicts.append({
                "num": s.get("team"),
                "rank": 1,  # You may want to use actual rank if available
                "total_epa": s.get("overall_avg", 0),
                "auto_epa": s.get("teleop_coral_avg", 0),
                "teleop_epa": s.get("teleop_algae_avg", 0),
                "endgame_epa": 0,  # If you have endgame EPA, use it
                "defense": s.get("teleop_crossed_played_defense_rate", 0) > 0.5,
                "name": s.get("team")
            })
        teams = teams_from_dicts(team_dicts)
        selector = AllianceSelector(teams)
        # Show a simple dialog with alliance recommendations
        table = selector.get_alliance_table()
        msg = ""
        for row in table:
            msg += f"Alliance {row['Alliance #']}: Captain {row['Captain']}, Pick1 {row['Pick 1']} (Rec: {row['Recommendation 1']}), Pick2 {row['Pick 2']} (Rec: {row['Recommendation 2']}), Score: {row['Alliance Score']}\n"
        messagebox.showinfo("Alliance Recommendations", msg)

    def open_team_performance_plot(self):
        # Open a window to select teams and plot their match-by-match overall
        win = tk.Toplevel(self.root)
        win.title("Plot Team Performance")
        win.transient(self.root)
        win.grab_set()
        ttk.Label(win, text="Select teams to plot:").pack(padx=10, pady=(10, 0))
        # Get all teams
        team_data = self.analizador.get_team_data_grouped()
        team_list = sorted(team_data.keys(), key=lambda x: int(x) if x.isdigit() else x)
        vars = {team: tk.BooleanVar(value=False) for team in team_list}
        frm = ttk.Frame(win)
        frm.pack(padx=10, pady=10)
        for i, team in enumerate(team_list):
            ttk.Checkbutton(frm, text=team, variable=vars[team]).grid(row=i//5, column=i%5, sticky='w', padx=4, pady=2)
        msg_var = tk.StringVar()
        ttk.Label(win, textvariable=msg_var, foreground="red").pack()
        def plot_selected():
            selected = [team for team in team_list if vars[team].get()]
            if not selected:
                msg_var.set("Select at least one team.")
                return
            perf = self.analizador.get_team_match_performance(selected)
            if not perf:
                msg_var.set("No data to plot.")
                return
            fig, ax = plt.subplots(figsize=(7,4))
            for team in selected:
                data = perf.get(team, [])
                if not data:
                    continue
                xs, ys = zip(*data)
                ax.plot(xs, ys, marker='o', label=f"Team {team}")
            ax.set_xlabel("Match Number")
            ax.set_ylabel("Overall (per match)")
            ax.set_title("Team Performance Over Matches")
            ax.legend()
            # Embed in Tk window
            plot_win = tk.Toplevel(win)
            plot_win.title("Team Performance Plot")
            canvas = FigureCanvasTkAgg(fig, master=plot_win)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            plt.close(fig)
        ttk.Button(win, text="Plot", command=plot_selected).pack(pady=(0,10))
        ttk.Button(win, text="Close", command=win.destroy).pack()
        win.wait_window()

    def test_camera(self):
        """Test camera access without starting the full QR scanner."""
        try:
            import cv2
        except ImportError:
            messagebox.showerror("Missing Dependencies", 
                               "OpenCV not found. Please install: pip install opencv-python")
            return
        
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                messagebox.showerror("Camera Error", 
                                   "Could not open camera. Please check:\n"
                                   "- Camera is connected\n"
                                   "- Camera is not being used by another application\n"
                                   "- Camera permissions are granted")
                return
            
            cap.release()
            messagebox.showinfo("Camera Test", "Camera test successful! Your camera is working properly.")
            self.status_var.set("Camera test passed.")
        except Exception as e:
            messagebox.showerror("Camera Test Failed", f"Camera test failed: {e}")
            self.status_var.set("Camera test failed.")

    def open_foreshadowing(self):
        def _launch():
            try:
                from foreshadowing import ForeshadowingLauncher
            except ImportError as e:
                messagebox.showerror("Foreshadowing", f"No se pudo importar módulo: {e}")
                return
            ForeshadowingLauncher(self.root, analyzer=self.analizador)
        _launch()

    def edit_raw_data_row(self):
        """Edit the selected row in the raw data table."""
        selection = self.tree_raw.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a row to edit.")
            return
        
        item = selection[0]
        current_values = self.tree_raw.item(item, 'values')
        headers = self.analizador.get_current_headers()
        
        if not current_values or not headers:
            messagebox.showerror("Error", "No data available to edit.")
            return
        
        # Create edit dialog
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Edit Row")
        edit_window.transient(self.root)
        edit_window.grab_set()
        
        # Create form fields
        entries = {}
        for i, (header, value) in enumerate(zip(headers, current_values)):
            ttk.Label(edit_window, text=f"{header}:").grid(row=i, column=0, sticky='e', padx=5, pady=2)
            entry = ttk.Entry(edit_window, width=30)
            entry.insert(0, str(value))
            entry.grid(row=i, column=1, padx=5, pady=2)
            entries[header] = entry
        
        # Buttons
        def save_changes():
            new_values = [entries[header].get() for header in headers]
            # Update treeview
            self.tree_raw.item(item, values=new_values)
            # Update analyzer data
            row_index = int(item) + 1  # +1 because item IDs start from 0, but data rows start from 1 (after header)
            if row_index < len(self.analizador.sheet_data):
                self.analizador.sheet_data[row_index] = new_values
                self.status_var.set("Row updated. Click 'Save Changes' to persist modifications.")
            edit_window.destroy()
        
        btn_frame = ttk.Frame(edit_window)
        btn_frame.grid(row=len(headers), column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Save", command=save_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=edit_window.destroy).pack(side=tk.LEFT, padx=5)

    def delete_raw_data_row(self):
        """Delete the selected row from the raw data table."""
        selection = self.tree_raw.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a row to delete.")
            return
        
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected row?"):
            item = selection[0]
            row_index = int(item) + 1  # +1 because item IDs start from 0, but data rows start from 1
            
            # Remove from analyzer data
            if row_index < len(self.analizador.sheet_data):
                del self.analizador.sheet_data[row_index]
            
            # Remove from treeview
            self.tree_raw.delete(item)
            self.status_var.set("Row deleted. Click 'Save Changes' to persist modifications.")

    def add_raw_data_row(self):
        """Add a new row to the raw data table."""
        headers = self.analizador.get_current_headers()
        if not headers:
            messagebox.showerror("Error", "No headers defined. Please load data or update headers first.")
            return
        
        # Create add dialog
        add_window = tk.Toplevel(self.root)
        add_window.title("Add New Row")
        add_window.transient(self.root)
        add_window.grab_set()
        
        # Create form fields
        entries = {}
        for i, header in enumerate(headers):
            ttk.Label(add_window, text=f"{header}:").grid(row=i, column=0, sticky='e', padx=5, pady=2)
            entry = ttk.Entry(add_window, width=30)
            entry.grid(row=i, column=1, padx=5, pady=2)
            entries[header] = entry
        
        # Buttons
        def save_new_row():
            new_values = [entries[header].get() for header in headers]
            # Add to analyzer data
            self.analizador.sheet_data.append(new_values)
            # Add to treeview
            self.tree_raw.insert("", tk.END, values=new_values)
            self.status_var.set("Row added. Click 'Save Changes' to persist modifications.")
            add_window.destroy()
        
        btn_frame = ttk.Frame(add_window)
        btn_frame.grid(row=len(headers), column=0, columnspan=2, pady=10)
        ttk.Button(btn_frame, text="Add", command=save_new_row).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=add_window.destroy).pack(side=tk.LEFT, padx=5)

    def save_raw_data_changes(self):
        """Save the current raw data to a CSV file."""
        if not self.analizador.sheet_data:
            messagebox.showwarning("No Data", "No data to save.")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="Save Raw Data"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    writer.writerows(self.analizador.sheet_data)
                messagebox.showinfo("Success", f"Data saved to {file_path}")
                self.status_var.set(f"Data saved to {os.path.basename(file_path)}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save file: {e}")

    def on_raw_data_double_click(self, event):
        """Handle double-click on raw data table to edit row."""
        self.edit_raw_data_row()

    def open_school_system(self):
        """Open SchoolSystem Honor Roll configuration window"""
        school_window = tk.Toplevel(self.root)
        school_window.title("SchoolSystem - Honor Roll Configuration")
        school_window.geometry("800x600")
        school_window.transient(self.root)
        
        # Create notebook for different configuration sections
        school_notebook = ttk.Notebook(school_window)
        school_notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Team Management Tab
        team_mgmt_frame = ttk.Frame(school_notebook)
        school_notebook.add(team_mgmt_frame, text="Team Management")
        
        # Team list
        ttk.Label(team_mgmt_frame, text="Teams in SchoolSystem:").pack(anchor=tk.W, padx=5, pady=5)
        
        team_listbox = tk.Listbox(team_mgmt_frame, height=8)
        team_listbox.pack(fill=tk.X, padx=5, pady=5)
        
        # Populate team list
        for team_num in self.school_system.teams.keys():
            team_listbox.insert(tk.END, f"Team {team_num}")
        
        # Team management buttons
        team_btn_frame = ttk.Frame(team_mgmt_frame)
        team_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        def add_team():
            team_num = simpledialog.askstring("Add Team", "Enter team number:")
            if team_num:
                self.school_system.add_team(team_num)
                team_listbox.insert(tk.END, f"Team {team_num}")
                self.refresh_honor_roll_tab()
        
        def remove_team():
            selection = team_listbox.curselection()
            if selection:
                team_text = team_listbox.get(selection[0])
                team_num = team_text.replace("Team ", "")
                if team_num in self.school_system.teams:
                    del self.school_system.teams[team_num]
                    del self.school_system.calculated_scores[team_num]
                team_listbox.delete(selection[0])
                self.refresh_honor_roll_tab()
        
        ttk.Button(team_btn_frame, text="Add Team", command=add_team).pack(side=tk.LEFT, padx=2)
        ttk.Button(team_btn_frame, text="Remove Selected", command=remove_team).pack(side=tk.LEFT, padx=2)
        ttk.Button(team_btn_frame, text="Auto-populate from Raw Data", command=self.auto_populate_school_system).pack(side=tk.LEFT, padx=2)
        
        # Quick Configuration Tab
        quick_config_frame = ttk.Frame(school_notebook)
        school_notebook.add(quick_config_frame, text="Quick Configuration")
        
        ttk.Label(quick_config_frame, text="SchoolSystem Configuration", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Configuration options
        config_frame = ttk.LabelFrame(quick_config_frame, text="Multipliers and Thresholds")
        config_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Multipliers
        mult_frame = ttk.Frame(config_frame)
        mult_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(mult_frame, text="Competencies Multiplier:").grid(row=0, column=0, sticky=tk.W, padx=5)
        comp_mult_var = tk.IntVar(value=self.school_system.competencies_multiplier)
        ttk.Entry(mult_frame, textvariable=comp_mult_var, width=10).grid(row=0, column=1, padx=5)
        
        ttk.Label(mult_frame, text="Subcompetencies Multiplier:").grid(row=1, column=0, sticky=tk.W, padx=5)
        subcomp_mult_var = tk.IntVar(value=self.school_system.subcompetencies_multiplier)
        ttk.Entry(mult_frame, textvariable=subcomp_mult_var, width=10).grid(row=1, column=1, padx=5)
        
        # Thresholds
        thresh_frame = ttk.Frame(config_frame)
        thresh_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(thresh_frame, text="Min Competencies:").grid(row=0, column=0, sticky=tk.W, padx=5)
        min_comp_var = tk.IntVar(value=self.school_system.min_competencies_count)
        ttk.Entry(thresh_frame, textvariable=min_comp_var, width=10).grid(row=0, column=1, padx=5)
        
        ttk.Label(thresh_frame, text="Min Subcompetencies:").grid(row=1, column=0, sticky=tk.W, padx=5)
        min_subcomp_var = tk.IntVar(value=self.school_system.min_subcompetencies_count)
        ttk.Entry(thresh_frame, textvariable=min_subcomp_var, width=10).grid(row=1, column=1, padx=5)
        
        ttk.Label(thresh_frame, text="Min Honor Roll Score:").grid(row=2, column=0, sticky=tk.W, padx=5)
        min_score_var = tk.DoubleVar(value=self.school_system.min_honor_roll_score)
        ttk.Entry(thresh_frame, textvariable=min_score_var, width=10).grid(row=2, column=1, padx=5)
        
        def apply_config():
            self.school_system.competencies_multiplier = comp_mult_var.get()
            self.school_system.subcompetencies_multiplier = subcomp_mult_var.get()
            self.school_system.min_competencies_count = min_comp_var.get()
            self.school_system.min_subcompetencies_count = min_subcomp_var.get()
            self.school_system.min_honor_roll_score = min_score_var.get()
            self.refresh_honor_roll_tab()
            messagebox.showinfo("Configuration", "Settings updated successfully!")
        
        ttk.Button(config_frame, text="Apply Settings", command=apply_config).pack(pady=10)
        
        # Results Preview Tab
        results_frame = ttk.Frame(school_notebook)
        school_notebook.add(results_frame, text="Results Preview")
        
        # Results tree
        results_tree = ttk.Treeview(results_frame, show='headings')
        results_tree.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Populate results
        def refresh_results():
            rankings = self.school_system.get_honor_roll_ranking()
            
            columns = ["Rank", "Team", "Final Points", "Honor Roll Score", "Curved Score", "C/SC/RP", "Status"]
            results_tree["columns"] = columns
            
            for col in columns:
                results_tree.heading(col, text=col)
                results_tree.column(col, width=100)
            
            results_tree.delete(*results_tree.get_children())
            
            for rank, (team_num, results) in enumerate(rankings, 1):
                c, sc, rp = self.school_system.calculate_competencies_score(team_num)
                status = "Qualified"
                
                results_tree.insert("", tk.END, values=[
                    rank, team_num, results.final_points,
                    f"{results.honor_roll_score:.1f}", f"{results.curved_score:.1f}",
                    f"{c}/{sc}/{rp}", status
                ])
            
            # Add disqualified teams
            disqualified = self.school_system.get_disqualified_teams()
            for team_num, reason in disqualified:
                c, sc, rp = self.school_system.calculate_competencies_score(team_num)
                results_tree.insert("", tk.END, values=[
                    "DQ", team_num, "0", "0.0", "0.0", f"{c}/{sc}/{rp}", reason[:30]
                ])
        
        ttk.Button(results_frame, text="Refresh Results", command=refresh_results).pack(pady=5)
        refresh_results()

    def auto_populate_school_system(self):
        """Auto-populate SchoolSystem with teams from raw data using calculated phase scores"""
        team_data = self.analizador.get_team_data_grouped()
        if not team_data:
            messagebox.showwarning("No Data", "No team data available. Please load some data first.")
            return
        
        teams_added = 0
        teams_with_calculated_scores = 0
        
        for team_number in team_data.keys():
            self.school_system.add_team(team_number)
            
            # Calculate real scores from game phases
            phase_scores = self.analizador.calculate_team_phase_scores(int(team_number))
            
            if any(score > 0 for score in phase_scores.values()):
                # Use calculated scores from actual data
                self.school_system.update_autonomous_score(team_number, phase_scores["autonomous"])
                self.school_system.update_teleop_score(team_number, phase_scores["teleop"])
                self.school_system.update_endgame_score(team_number, phase_scores["endgame"])
                teams_with_calculated_scores += 1
            else:
                # Use default values if no data available
                self.school_system.update_autonomous_score(team_number, 75.0)
                self.school_system.update_teleop_score(team_number, 80.0)
                self.school_system.update_endgame_score(team_number, 70.0)
            
            # Set default pit scouting scores (these need manual input or separate data source)
            self.school_system.update_electrical_score(team_number, 85.0)
            self.school_system.update_mechanical_score(team_number, 80.0)
            self.school_system.update_driver_station_layout_score(team_number, 75.0)
            self.school_system.update_tools_score(team_number, 70.0)
            self.school_system.update_spare_parts_score(team_number, 65.0)
            self.school_system.update_team_organization_score(team_number, 80.0)
            self.school_system.update_collaboration_score(team_number, 85.0)
            
            # Try to infer some competencies from performance data
            team_stats = self.analizador.get_detailed_team_stats()
            if str(team_number) in team_stats:
                stats = team_stats[str(team_number)]
                
                # Infer reliability based on match consistency
                if "died_rate" in stats and stats["died_rate"] < 0.1:  # Less than 10% death rate
                    self.school_system.update_competency(team_number, "no_deaths", True)
                    self.school_system.update_competency(team_number, "reliability", True)
                
                # Infer driving skills based on teleop performance
                if phase_scores["teleop"] > 75:
                    self.school_system.update_competency(team_number, "driving_skills", True)
                
                # Infer autonomous competency
                if phase_scores["autonomous"] > 75:
                    self.school_system.update_competency(team_number, "pasar_inspeccion_primera", True)
            
            # Set some default competencies
            self.school_system.update_competency(team_number, "team_communication", True)
            self.school_system.update_competency(team_number, "working_under_pressure", True)
            
            teams_added += 1
        
        self.refresh_honor_roll_tab()
        
        message = f"Added {teams_added} teams to SchoolSystem.\n"
        message += f"{teams_with_calculated_scores} teams have calculated phase scores from actual data.\n"
        message += f"{teams_added - teams_with_calculated_scores} teams use default values.\n\n"
        message += "Note: Pit scouting scores still use default values and may need manual adjustment."
        
        messagebox.showinfo("Auto-populate Complete", message)

    def manual_team_entry(self):
        """Open manual team entry dialog"""
        team_num = simpledialog.askstring("Manual Entry", "Enter team number:")
        if not team_num:
            return
        
        self.school_system.add_team(team_num)
        self.edit_team_scores_for_team(team_num)

    def edit_team_scores(self):
        """Open team selection for score editing"""
        if not self.school_system.teams:
            messagebox.showwarning("No Teams", "No teams in SchoolSystem. Please add teams first.")
            return
        
        # Create team selection dialog
        selection_window = tk.Toplevel(self.root)
        selection_window.title("Select Team to Edit")
        selection_window.geometry("300x400")
        selection_window.transient(self.root)
        
        ttk.Label(selection_window, text="Select a team to edit:").pack(pady=10)
        
        team_listbox = tk.Listbox(selection_window)
        team_listbox.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        for team_num in sorted(self.school_system.teams.keys()):
            team_listbox.insert(tk.END, team_num)
        
        def edit_selected():
            selection = team_listbox.curselection()
            if selection:
                team_num = team_listbox.get(selection[0])
                selection_window.destroy()
                self.edit_team_scores_for_team(team_num)
        
        ttk.Button(selection_window, text="Edit Selected Team", command=edit_selected).pack(pady=10)

    def edit_team_scores_for_team(self, team_number):
        """Open detailed score editing window for a specific team"""
        edit_window = tk.Toplevel(self.root)
        edit_window.title(f"Edit Scores - Team {team_number}")
        edit_window.geometry("600x700")
        edit_window.transient(self.root)
        
        # Create scrollable frame
        canvas = tk.Canvas(edit_window)
        scrollbar = ttk.Scrollbar(edit_window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Get current scores
        current_scores = self.school_system.teams[team_number]
        
        # Variables for all scores
        score_vars = {}
        
        # Match Performance Section
        match_frame = ttk.LabelFrame(scrollable_frame, text="Match Performance (50%)")
        match_frame.pack(fill=tk.X, padx=10, pady=5)
        
        score_vars['autonomous'] = tk.DoubleVar(value=current_scores.autonomous_score)
        score_vars['teleop'] = tk.DoubleVar(value=current_scores.teleop_score)
        score_vars['endgame'] = tk.DoubleVar(value=current_scores.endgame_score)
        
        ttk.Label(match_frame, text="Autonomous Score (20%):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(match_frame, textvariable=score_vars['autonomous'], width=10).grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(match_frame, text="Teleop Score (60%):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(match_frame, textvariable=score_vars['teleop'], width=10).grid(row=1, column=1, padx=5, pady=2)
        
        ttk.Label(match_frame, text="Endgame Score (20%):").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(match_frame, textvariable=score_vars['endgame'], width=10).grid(row=2, column=1, padx=5, pady=2)
        
        # Pit Scouting Section
        pit_frame = ttk.LabelFrame(scrollable_frame, text="Pit Scouting (30%)")
        pit_frame.pack(fill=tk.X, padx=10, pady=5)
        
        score_vars['electrical'] = tk.DoubleVar(value=current_scores.electrical_score)
        score_vars['mechanical'] = tk.DoubleVar(value=current_scores.mechanical_score)
        score_vars['driver_station'] = tk.DoubleVar(value=current_scores.driver_station_layout_score)
        score_vars['tools'] = tk.DoubleVar(value=current_scores.tools_score)
        score_vars['spare_parts'] = tk.DoubleVar(value=current_scores.spare_parts_score)
        
        pit_scores = [
            ("Electrical (33.33%):", 'electrical'),
            ("Mechanical (25%):", 'mechanical'),
            ("Driver Station Layout (16.67%):", 'driver_station'),
            ("Tools (16.67%):", 'tools'),
            ("Spare Parts (8.33%):", 'spare_parts')
        ]
        
        for i, (label, var_key) in enumerate(pit_scores):
            ttk.Label(pit_frame, text=label).grid(row=i, column=0, sticky=tk.W, padx=5, pady=2)
            ttk.Entry(pit_frame, textvariable=score_vars[var_key], width=10).grid(row=i, column=1, padx=5, pady=2)
        
        # During Event Section
        event_frame = ttk.LabelFrame(scrollable_frame, text="During Event (20%)")
        event_frame.pack(fill=tk.X, padx=10, pady=5)
        
        score_vars['organization'] = tk.DoubleVar(value=current_scores.team_organization_score)
        score_vars['collaboration'] = tk.DoubleVar(value=current_scores.collaboration_score)
        
        ttk.Label(event_frame, text="Team Organization (50%):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(event_frame, textvariable=score_vars['organization'], width=10).grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(event_frame, text="Collaboration (50%):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        ttk.Entry(event_frame, textvariable=score_vars['collaboration'], width=10).grid(row=1, column=1, padx=5, pady=2)
        
        # Competencies Section
        comp_frame = ttk.LabelFrame(scrollable_frame, text="Competencies & Subcompetencies")
        comp_frame.pack(fill=tk.X, padx=10, pady=5)
        
        competencies = current_scores.competencies
        comp_vars = {}
        
        # Competencies
        comp_items = [
            ("Team Communication", 'team_communication'),
            ("Driving Skills", 'driving_skills'),
            ("Reliability", 'reliability'),
            ("No Deaths", 'no_deaths'),
            ("Pasar Inspección Primera", 'pasar_inspeccion_primera'),
            ("Human Player", 'human_player'),
            ("Necessary Drivers Fix", 'necessary_drivers_fix')
        ]
        
        ttk.Label(comp_frame, text="Competencies:", font=("Arial", 10, "bold")).grid(row=0, column=0, columnspan=2, pady=5)
        
        for i, (label, attr) in enumerate(comp_items, 1):
            comp_vars[attr] = tk.BooleanVar(value=getattr(competencies, attr))
            ttk.Checkbutton(comp_frame, text=label, variable=comp_vars[attr]).grid(row=i, column=0, sticky=tk.W, padx=5, pady=1)
        
        # Subcompetencies
        subcomp_items = [
            ("Working Under Pressure", 'working_under_pressure'),
            ("Commitment", 'commitment'),
            ("Win Most Games", 'win_most_games'),
            ("Never Ask Pit Admin", 'never_ask_pit_admin'),
            ("Knows the Rules", 'knows_the_rules')
        ]
        
        ttk.Label(comp_frame, text="Subcompetencies:", font=("Arial", 10, "bold")).grid(row=0, column=2, columnspan=2, pady=5)
        
        for i, (label, attr) in enumerate(subcomp_items, 1):
            comp_vars[attr] = tk.BooleanVar(value=getattr(competencies, attr))
            ttk.Checkbutton(comp_frame, text=label, variable=comp_vars[attr]).grid(row=i, column=2, sticky=tk.W, padx=5, pady=1)
        
        # Behavior Reports Section
        behavior_frame = ttk.LabelFrame(scrollable_frame, text="Behavior Reports")
        behavior_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(behavior_frame, text=f"Current penalty points: {competencies.get_behavior_reports_points()}").pack(pady=5)
        
        def add_low_conduct():
            self.school_system.add_behavior_report(team_number, BehaviorReportType.LOW_CONDUCT)
            refresh_behavior_display()
        
        def add_very_low_conduct():
            self.school_system.add_behavior_report(team_number, BehaviorReportType.VERY_LOW_CONDUCT)
            refresh_behavior_display()
        
        def clear_reports():
            self.school_system.teams[team_number].competencies.behavior_reports.clear()
            refresh_behavior_display()
        
        def refresh_behavior_display():
            current_points = self.school_system.teams[team_number].competencies.get_behavior_reports_points()
            ttk.Label(behavior_frame, text=f"Current penalty points: {current_points}").pack(pady=5)
        
        behavior_btn_frame = ttk.Frame(behavior_frame)
        behavior_btn_frame.pack(pady=5)
        
        ttk.Button(behavior_btn_frame, text="Add Low Conduct (+2)", command=add_low_conduct).pack(side=tk.LEFT, padx=2)
        ttk.Button(behavior_btn_frame, text="Add Very Low Conduct (+5)", command=add_very_low_conduct).pack(side=tk.LEFT, padx=2)
        ttk.Button(behavior_btn_frame, text="Clear All Reports", command=clear_reports).pack(side=tk.LEFT, padx=2)
        
        # Save button
        def save_scores():
            # Update all scores
            self.school_system.update_autonomous_score(team_number, score_vars['autonomous'].get())
            self.school_system.update_teleop_score(team_number, score_vars['teleop'].get())
            self.school_system.update_endgame_score(team_number, score_vars['endgame'].get())
            self.school_system.update_electrical_score(team_number, score_vars['electrical'].get())
            self.school_system.update_mechanical_score(team_number, score_vars['mechanical'].get())
            self.school_system.update_driver_station_layout_score(team_number, score_vars['driver_station'].get())
            self.school_system.update_tools_score(team_number, score_vars['tools'].get())
            self.school_system.update_spare_parts_score(team_number, score_vars['spare_parts'].get())
            self.school_system.update_team_organization_score(team_number, score_vars['organization'].get())
            self.school_system.update_collaboration_score(team_number, score_vars['collaboration'].get())
            
            # Update competencies
            for attr, var in comp_vars.items():
                self.school_system.update_competency(team_number, attr, var.get())
            
            self.refresh_honor_roll_tab()
            messagebox.showinfo("Saved", f"Scores updated for Team {team_number}")
            edit_window.destroy()
        
        ttk.Button(scrollable_frame, text="Save All Changes", command=save_scores).pack(pady=20)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

    def refresh_honor_roll_tab(self):
        """Refresh the Honor Roll System tab"""
        if not hasattr(self, 'tree_honor_roll'):
            return
        
        rankings = self.school_system.get_honor_roll_ranking()
        disqualified = self.school_system.get_disqualified_teams()
        
        columns = ["Rank", "Team", "Final Points", "Honor Roll", "Curved", "Match Perf", "Pit Scout", "During Event", "C/SC/RP", "Status"]
        self.tree_honor_roll["columns"] = columns
        
        for col in columns:
            self.tree_honor_roll.heading(col, text=col)
            if col in ["Team", "Status"]:
                self.tree_honor_roll.column(col, width=80)
            else:
                self.tree_honor_roll.column(col, width=90)
        
        self.tree_honor_roll.delete(*self.tree_honor_roll.get_children())
        
        # Add qualified teams
        for rank, (team_num, results) in enumerate(rankings, 1):
            c, sc, rp = self.school_system.calculate_competencies_score(team_num)
            
            self.tree_honor_roll.insert("", tk.END, values=[
                rank,
                team_num,
                results.final_points,
                f"{results.honor_roll_score:.1f}",
                f"{results.curved_score:.1f}",
                f"{results.match_performance_score:.1f}",
                f"{results.pit_scouting_score:.1f}",
                f"{results.during_event_score:.1f}",
                f"{c}/{sc}/{rp}",
                "Qualified"
            ])
        
        # Add disqualified teams
        for team_num, reason in disqualified:
            calculated = self.school_system.calculated_scores.get(team_num)
            c, sc, rp = self.school_system.calculate_competencies_score(team_num)
            
            if calculated:
                self.tree_honor_roll.insert("", tk.END, values=[
                    "DQ",
                    team_num,
                    "0",
                    f"{calculated.honor_roll_score:.1f}",
                    "0.0",
                    f"{calculated.match_performance_score:.1f}",
                    f"{calculated.pit_scouting_score:.1f}",
                    f"{calculated.during_event_score:.1f}",
                    f"{c}/{sc}/{rp}",
                    reason[:20] + "..." if len(reason) > 20 else reason
                ])

    def export_honor_roll(self):
        """Export Honor Roll results to CSV"""
        if not self.school_system.teams:
            messagebox.showwarning("No Data", "No teams in SchoolSystem to export.")
            return
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV Files", "*.csv"), ("All Files", "*.*")],
            title="Export Honor Roll Results"
        )
        
        if file_path:
            try:
                rankings = self.school_system.get_honor_roll_ranking()
                disqualified = self.school_system.get_disqualified_teams()
                
                with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                    writer = csv.writer(csvfile)
                    
                    # Write header
                    writer.writerow([
                        "Rank", "Team", "Final Points", "Honor Roll Score", "Curved Score",
                        "Match Performance", "Pit Scouting", "During Event",
                        "Competencies", "Subcompetencies", "Behavior Reports", "Status", "Notes"
                    ])
                    
                    # Write qualified teams
                    for rank, (team_num, results) in enumerate(rankings, 1):
                        c, sc, rp = self.school_system.calculate_competencies_score(team_num)
                        
                        writer.writerow([
                            rank, team_num, results.final_points,
                            f"{results.honor_roll_score:.2f}", f"{results.curved_score:.2f}",
                            f"{results.match_performance_score:.2f}",
                            f"{results.pit_scouting_score:.2f}",
                            f"{results.during_event_score:.2f}",
                            c, sc, rp, "Qualified", ""
                        ])
                    
                    # Write disqualified teams
                    for team_num, reason in disqualified:
                        calculated = self.school_system.calculated_scores.get(team_num)
                        c, sc, rp = self.school_system.calculate_competencies_score(team_num)
                        
                        if calculated:
                            writer.writerow([
                                "DQ", team_num, 0,
                                f"{calculated.honor_roll_score:.2f}", "0.00",
                                f"{calculated.match_performance_score:.2f}",
                                f"{calculated.pit_scouting_score:.2f}",
                                f"{calculated.during_event_score:.2f}",
                                c, sc, rp, "Disqualified", reason
                            ])
                
                # Export summary statistics
                stats = self.school_system.get_summary_stats()
                summary_path = file_path.replace('.csv', '_summary.txt')
                
                with open(summary_path, 'w', encoding='utf-8') as summary_file:
                    summary_file.write("SchoolSystem Honor Roll Summary\n")
                    summary_file.write("=" * 40 + "\n\n")
                    summary_file.write(f"Total Teams: {stats['total_teams']}\n")
                    summary_file.write(f"Qualified Teams: {stats['qualified_teams']}\n")
                    summary_file.write(f"Disqualified Teams: {stats['disqualified_teams']}\n")
                    summary_file.write(f"Average Honor Roll Score: {stats['avg_honor_roll_score']:.2f}\n")
                    summary_file.write(f"Average Final Points: {stats['avg_final_points']:.2f}\n\n")
                    
                    summary_file.write("Configuration:\n")
                    summary_file.write(f"  Competencies Multiplier: {self.school_system.competencies_multiplier}\n")
                    summary_file.write(f"  Subcompetencies Multiplier: {self.school_system.subcompetencies_multiplier}\n")
                    summary_file.write(f"  Min Competencies: {self.school_system.min_competencies_count}\n")
                    summary_file.write(f"  Min Subcompetencies: {self.school_system.min_subcompetencies_count}\n")
                    summary_file.write(f"  Min Honor Roll Score: {self.school_system.min_honor_roll_score}\n")
                
                messagebox.showinfo("Export Complete", 
                                  f"Honor Roll results exported to:\n{file_path}\n\n"
                                  f"Summary exported to:\n{summary_path}")
                self.status_var.set(f"Honor Roll exported to {os.path.basename(file_path)}")
                
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export Honor Roll: {e}")

    def test_camera(self):
        """Test camera access without starting the full QR scanner."""
        try:
            import cv2
        except ImportError:
            messagebox.showerror("Missing Dependencies", 
                               "OpenCV not found. Please install: pip install opencv-python")
            return
        
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                messagebox.showerror("Camera Error", 
                                   "Could not open camera. Please check:\n"
                                   "- Camera is connected\n"
                                   "- Camera is not being used by another application\n"
                                   "- Camera permissions are granted")
                return
            
            cap.release()
            messagebox.showinfo("Camera Test", "Camera test successful! Your camera is working properly.")
            self.status_var.set("Camera test passed.")
        except Exception as e:
            messagebox.showerror("Camera Test Failed", f"Camera test failed: {e}")
            self.status_var.set("Camera test failed.")

# Replace CLI example with GUI launch
if __name__ == "__main__":
    root = tk.Tk()
    analizador = AnalizadorRobot()
    app = AnalizadorGUI(root, analizador)
    root.mainloop()