import csv
import json
import math
import base64
from collections import Counter, defaultdict
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from tkinter import simpledialog
from allianceSelector import AllianceSelector, Team, teams_from_dicts
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from school_system import TeamScoring, BehaviorReportType
from config_manager import ConfigManager
from csv_converter import CSVFormatConverter
from default_robot_image import load_team_image

class AnalizadorRobot:
    def __init__(self, default_column_names=None, config_file="columnsConfig.json"):
        """
        Inicializa el analizador.

        Args:
            default_column_names (list, optional): Nombres de columna predeterminados.
                                                  Si no se proveen, se cargarán desde la configuración.
            config_file (str): Archivo de configuración de columnas.
        """
        # Initialize configuration manager
        self.config_manager = ConfigManager(config_file)
        self.csv_converter = CSVFormatConverter(self.config_manager)
        
        # Load column configuration
        column_config = self.config_manager.get_column_config()
        robot_config = self.config_manager.get_robot_valuation_config()
        
        self.default_column_names = default_column_names if default_column_names else column_config.headers
        
        # Configuración de columnas por fase del juego
        self._autonomous_columns = column_config.autonomous_columns.copy()
        self._teleop_columns = column_config.teleop_columns.copy()
        self._endgame_columns = column_config.endgame_columns.copy()
        
        # sheetData es un List<List<String>> cuya primera fila es siempre el encabezado.
        self.sheet_data = []
        if self.default_column_names:
            self.sheet_data.append(list(self.default_column_names)) # Copia de la lista

        # _columnIndices mapea cada nombre de columna a su índice numérico para acceder rápido.
        self._column_indices = {}
        self._update_column_indices()

        # El usuario puede afinar tres conjuntos de columnas:
        # Numéricas para cálculo global (_selectedNumericColumnsForOverall)
        self._selected_numeric_columns_for_overall = column_config.numeric_for_overall.copy()
        # Para la tabla de estadísticas (_selectedStatsColumns)
        self._selected_stats_columns = column_config.stats_columns.copy()
        # Booleanas cuyo modo (valor más frecuente) se muestre (_modeBooleanColumns)
        self._mode_boolean_columns = column_config.mode_boolean_columns.copy()
        
        # Inicializar selecciones de columnas (podría ser más sofisticado)
        self._initialize_selected_columns()

        # --- RobotValuation phase weights and boundaries ---
        self.robot_valuation_phase_weights = robot_config.phase_weights.copy()
        self.robot_valuation_phase_names = robot_config.phase_names.copy()

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
        usando la configuración cargada del ConfigManager.
        """
        # Use configuration from ConfigManager if available
        if hasattr(self, 'config_manager'):
            column_config = self.config_manager.get_column_config()
            
            current_header = self.sheet_data[0] if self.sheet_data else self.default_column_names
            
            # Filter columns that exist in current header
            self._selected_numeric_columns_for_overall = [
                col for col in column_config.numeric_for_overall if col in current_header
            ]
            self._selected_stats_columns = [
                col for col in column_config.stats_columns if col in current_header
            ]
            self._mode_boolean_columns = [
                col for col in column_config.mode_boolean_columns if col in current_header
            ]
        else:
            # Fallback to legacy behavior
            current_header = self.sheet_data[0] if self.sheet_data else self.default_column_names
            default_overall_columns = [
                'Coral L1 (Auto)', 'Coral L2 (Auto)', 'Coral L3 (Auto)', 'Coral L4 (Auto)', 
                'Coral L1 (Teleop)', 'Coral L2 (Teleop)', 'Coral L3 (Teleop)', 'Coral L4 (Teleop)',
                'Barge Algae (Auto)', 'Barge Algae (Teleop)', 'Processor Algae (Auto)', 'Processor Algae (Teleop)'
            ]
            self._selected_numeric_columns_for_overall = [
                col for col in default_overall_columns if col in current_header
            ]
            excluded_from_stats = ["Scouter Initials", "Robot"]
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
        Carga un archivo CSV, detectando automáticamente el formato y convirtiéndolo si es necesario.
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

            csv_headers = csv_rows[0]
            
            # Detect CSV format
            detected_format = self.config_manager.detect_csv_format(csv_headers)
            
            if detected_format == "legacy_format":
                print(f"Detected legacy format. Converting to new format...")
                
                # Convert to new format
                converted_rows = self.csv_converter.convert_rows_to_new_format(csv_headers, csv_rows[1:])
                csv_rows = [self.config_manager.get_column_config().headers] + converted_rows
                
                print(f"Successfully converted {len(converted_rows)} data rows to new format.")
                
                # Optionally save converted file
                converted_file_path = file_path.replace('.csv', '_converted.csv')
                with open(converted_file_path, 'w', newline='', encoding='utf-8') as f:
                    writer = csv.writer(f)
                    writer.writerows(csv_rows)
                print(f"Saved converted file as: {converted_file_path}")
                
            elif detected_format == "unknown_format":
                print("Warning: Unknown CSV format detected. Loading as-is, but some features may not work correctly.")
            else:
                print("CSV file is already in the correct format.")

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
                       .replace('(Auto)', '') \
                       .replace('(Teleop)', '') \
                       .replace('/', '_') \
                       .replace(' ', '_') \
                       .lower()
        specific_renames = {
            'End Position': 'climb',
            'Climbed?': 'climb',
            'Did something?': 'auto_did_something',
            'Did Foul?': 'auto_did_foul',
            'Did auton worked?': 'auto_worked',
            'Moved (Auto)': 'auto_worked',
            'Barge Algae Scored': 'teleop_barge_algae',
            'Barge Algae (Teleop)': 'teleop_barge_algae',
            'Algae Scored in Barge': 'teleop_barge_algae',
            'Processor Algae Scored': 'teleop_processor_algae',
            'Processor Algae (Teleop)': 'teleop_processor_algae',
            'Played Algae?(Disloged NO COUNT)': 'teleop_played_algae',
            'Played Algae?(Disloged DOES NOT COUNT)': 'teleop_played_algae',
            'Crossed Feild/Played Defense?': 'teleop_crossed_played_defense',
            'Crossed Field/Defense': 'teleop_crossed_played_defense',
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
        # Updated coral_algae_groups to support both new and legacy formats
        coral_algae_groups = {
            'teleop_coral': [
                # New format columns
                'Coral L1 (Teleop)', 'Coral L2 (Teleop)',
                'Coral L3 (Teleop)', 'Coral L4 (Teleop)',
                # Legacy format columns for backward compatibility
                'Coral L1 Scored', 'Coral L2 Scored',
                'Coral L3 Scored', 'Coral L4 Scored'
            ],
            'teleop_algae': [
                # New format columns
                'Barge Algae (Teleop)', 'Processor Algae (Teleop)',
                # Legacy format columns for backward compatibility
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
            # Defensa (rate) - handle both new and legacy column names
            defense_col = 'Crossed Field/Defense'  # Try new format first
            defense_idx = self._column_indices.get(defense_col)
            if defense_idx is None:
                defense_col = 'Crossed Feild/Played Defense?'  # Fall back to legacy format
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
            # Enhanced Overall calculation with proper weighting
            overall_values = []
            coral_values = []
            algae_values = []
            
            # Calculate per-match performance across all matches for this team
            for row in rows:
                match_score = 0.0
                
                # Coral scoring with level-based weights (L1=2, L2=3, L3=4, L4=5 for teleop; double for auto)
                coral_weights = {'L1': 2, 'L2': 3, 'L3': 4, 'L4': 5}
                for level, weight in coral_weights.items():
                    # Auto coral (higher value)
                    auto_col = f'Coral {level} (Auto)'
                    auto_idx = self._column_indices.get(auto_col)
                    if auto_idx is not None and auto_idx < len(row):
                        try:
                            auto_val = float(row[auto_idx])
                            match_score += auto_val * weight * 2  # Double points for auto
                            coral_values.append(auto_val * weight * 2)
                        except Exception:
                            pass
                    
                    # Teleop coral
                    teleop_col = f'Coral {level} (Teleop)'
                    teleop_idx = self._column_indices.get(teleop_col)
                    if teleop_idx is not None and teleop_idx < len(row):
                        try:
                            teleop_val = float(row[teleop_idx])
                            match_score += teleop_val * weight
                            coral_values.append(teleop_val * weight)
                        except Exception:
                            pass
                    
                    # Legacy format fallback
                    legacy_col = f'Coral {level} Scored'
                    legacy_idx = self._column_indices.get(legacy_col)
                    if legacy_idx is not None and legacy_idx < len(row) and auto_idx is None and teleop_idx is None:
                        try:
                            legacy_val = float(row[legacy_idx])
                            match_score += legacy_val * weight * 1.5  # Moderate weight for combined
                            coral_values.append(legacy_val * weight * 1.5)
                        except Exception:
                            pass
                
                # Algae scoring (Barge=3 points, Processor=6 points)
                algae_configs = [
                    ('Barge Algae (Auto)', 3 * 1.5),  # Auto bonus
                    ('Barge Algae (Teleop)', 3),
                    ('Processor Algae (Auto)', 6 * 1.5),  # Auto bonus  
                    ('Processor Algae (Teleop)', 6),
                    ('Algae Scored in Barge', 3)  # Legacy
                ]
                
                for col_name, points in algae_configs:
                    col_idx = self._column_indices.get(col_name)
                    if col_idx is not None and col_idx < len(row):
                        try:
                            val = float(row[col_idx])
                            match_score += val * points
                            algae_values.append(val * points)
                        except Exception:
                            pass
                
                # Add endgame scoring (climb bonus)
                end_pos_idx = self._column_indices.get('End Position')
                climb_idx = self._column_indices.get('Climbed?')  # Legacy
                
                if end_pos_idx is not None and end_pos_idx < len(row):
                    end_pos = str(row[end_pos_idx]).strip().lower()
                    if 'deep' in end_pos:
                        match_score += 12
                    elif 'shallow' in end_pos:
                        match_score += 6
                    elif 'park' in end_pos:
                        match_score += 2
                elif climb_idx is not None and climb_idx < len(row):
                    try:
                        climb_val = float(row[climb_idx])
                        if climb_val > 0:
                            match_score += 8  # Estimated climb points for legacy
                    except Exception:
                        pass
                
                if match_score > 0:
                    overall_values.append(match_score)
            
            # Set overall stats
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

    def save_configuration(self):
        """Save current configuration to file"""
        if hasattr(self, 'config_manager'):
            # Update configuration with current selections
            self.config_manager.update_column_config(
                numeric_for_overall=self._selected_numeric_columns_for_overall,
                stats_columns=self._selected_stats_columns,
                mode_boolean_columns=self._mode_boolean_columns,
                autonomous_columns=self._autonomous_columns,
                teleop_columns=self._teleop_columns,
                endgame_columns=self._endgame_columns
            )
            self.config_manager.update_robot_valuation_config(
                phase_weights=self.robot_valuation_phase_weights,
                phase_names=self.robot_valuation_phase_names
            )
            self.config_manager.save_configuration()
            print("Configuration saved successfully.")
        else:
            print("Warning: No configuration manager available.")

    def get_available_presets(self):
        """Get available configuration presets"""
        if hasattr(self, 'config_manager'):
            return self.config_manager.get_configuration_presets()
        return {}

    def apply_configuration_preset(self, preset_name):
        """Apply a configuration preset"""
        if hasattr(self, 'config_manager'):
            self.config_manager.apply_preset(preset_name)
            # Reload configuration
            column_config = self.config_manager.get_column_config()
            robot_config = self.config_manager.get_robot_valuation_config()
            
            # Update local variables
            self._selected_numeric_columns_for_overall = column_config.numeric_for_overall.copy()
            self._selected_stats_columns = column_config.stats_columns.copy()
            self._mode_boolean_columns = column_config.mode_boolean_columns.copy()
            self._autonomous_columns = column_config.autonomous_columns.copy()
            self._teleop_columns = column_config.teleop_columns.copy()
            self._endgame_columns = column_config.endgame_columns.copy()
            self.robot_valuation_phase_weights = robot_config.phase_weights.copy()
            self.robot_valuation_phase_names = robot_config.phase_names.copy()
            
            print(f"Applied configuration preset: {preset_name}")
        else:
            print("Warning: No configuration manager available.")

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
        """Calculate RobotValuation using enhanced weighted scoring across phases."""
        if not rows:
            return 0.0
        
        phases = self._split_rows_into_phases(rows)
        phase_weights = self.robot_valuation_phase_weights
        phase_scores = []
        
        for phase_rows in phases:
            phase_total = 0.0
            match_count = len(phase_rows)
            
            if match_count == 0:
                phase_scores.append(0.0)
                continue
            
            # Calculate enhanced score for this phase
            for row in phase_rows:
                match_score = 0.0
                
                # Coral scoring with level-based weights
                coral_weights = {'L1': 2, 'L2': 3, 'L3': 4, 'L4': 5}
                for level, weight in coral_weights.items():
                    # Auto coral (higher multiplier)
                    auto_col = f'Coral {level} (Auto)'
                    auto_idx = self._column_indices.get(auto_col)
                    if auto_idx is not None and auto_idx < len(row):
                        try:
                            auto_val = float(row[auto_idx])
                            match_score += auto_val * weight * 2.0
                        except Exception:
                            pass
                    
                    # Teleop coral
                    teleop_col = f'Coral {level} (Teleop)'
                    teleop_idx = self._column_indices.get(teleop_col)
                    if teleop_idx is not None and teleop_idx < len(row):
                        try:
                            teleop_val = float(row[teleop_idx])
                            match_score += teleop_val * weight
                        except Exception:
                            pass
                    
                    # Legacy format fallback
                    legacy_col = f'Coral {level} Scored'
                    legacy_idx = self._column_indices.get(legacy_col)
                    if legacy_idx is not None and legacy_idx < len(row) and auto_idx is None and teleop_idx is None:
                        try:
                            legacy_val = float(row[legacy_idx])
                            match_score += legacy_val * weight * 1.5
                        except Exception:
                            pass
                
                # Algae scoring
                algae_configs = [
                    ('Barge Algae (Auto)', 4.5),  # 3 points * 1.5 auto multiplier
                    ('Barge Algae (Teleop)', 3),
                    ('Processor Algae (Auto)', 9),  # 6 points * 1.5 auto multiplier
                    ('Processor Algae (Teleop)', 6),
                    ('Algae Scored in Barge', 3)  # Legacy
                ]
                
                for col_name, points in algae_configs:
                    col_idx = self._column_indices.get(col_name)
                    if col_idx is not None and col_idx < len(row):
                        try:
                            val = float(row[col_idx])
                            match_score += val * points
                        except Exception:
                            pass
                
                # Endgame scoring
                end_pos_idx = self._column_indices.get('End Position')
                climb_idx = self._column_indices.get('Climbed?')  # Legacy
                
                if end_pos_idx is not None and end_pos_idx < len(row):
                    end_pos = str(row[end_pos_idx]).strip().lower()
                    if 'deep' in end_pos:
                        match_score += 12
                    elif 'shallow' in end_pos:
                        match_score += 6
                    elif 'park' in end_pos:
                        match_score += 2
                elif climb_idx is not None and climb_idx < len(row):
                    try:
                        climb_val = float(row[climb_idx])
                        if climb_val > 0:
                            match_score += 8  # Estimated points for legacy
                    except Exception:
                        pass
                
                # Defense/activity bonus
                defense_idx = self._column_indices.get('Crossed Field/Defense')
                if defense_idx is None:
                    defense_idx = self._column_indices.get('Crossed Feild/Played Defense?')
                
                if defense_idx is not None and defense_idx < len(row):
                    defense_val = str(row[defense_idx]).strip().lower()
                    if defense_val in ['true', 'yes', 'y', '1']:
                        match_score += 5  # Defense bonus
                
                # Auto movement bonus
                auto_moved_idx = self._column_indices.get('Moved (Auto)')
                if auto_moved_idx is None:
                    auto_moved_idx = self._column_indices.get('Did something?')
                
                if auto_moved_idx is not None and auto_moved_idx < len(row):
                    moved_val = str(row[auto_moved_idx]).strip().lower()
                    if moved_val in ['true', 'yes', 'y', '1']:
                        match_score += 3  # Auto activity bonus
                
                phase_total += match_score
            
            # Average for this phase
            phase_avg = phase_total / match_count if match_count > 0 else 0.0
            phase_scores.append(phase_avg)
        
        # Weighted sum across phases
        final_score = sum(w * s for w, s in zip(phase_weights, phase_scores))
        return final_score

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
        self.modified_rows = set()  # Track which rows have been manually modified
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
            ("Camera Settings", self.configure_camera),
            ("Paste QR Data", self.load_qr),
            ("System Configuration", self.open_system_configuration),
            ("Plot Team Performance", self.open_team_performance_plot),
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
        ttk.Button(honor_controls, text="Export to Tier List", command=self.export_tier_list).pack(side=tk.RIGHT, padx=2)
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
        Preserva las filas que han sido modificadas manualmente.
        """
        # Update column indices in case data structure changed
        self.analizador._update_column_indices()
        
        # Raw Data only
        raw = self.analizador.get_raw_data()
        if raw:
            headers = raw[0]
            data = raw[1:]
            
            # Store current modified data from sheet_data to preserve user edits
            modified_data = {}
            for row_index in self.modified_rows:
                if 0 < row_index < len(self.analizador.sheet_data):
                    modified_data[row_index - 1] = self.analizador.sheet_data[row_index]  # -1 because tree index
            
            # Clear and rebuild tree
            self.tree_raw.delete(*self.tree_raw.get_children())
            self.tree_raw["columns"] = headers
            for header in headers:
                self.tree_raw.heading(header, text=header)
                self.tree_raw.column(header, width=100)
            
            # Add data, preserving manually modified rows
            for i, row_data in enumerate(data):
                # If this row was manually modified, use the modified version from sheet_data
                if i in modified_data:
                    self.tree_raw.insert("", "end", values=modified_data[i])
                else:
                    self.tree_raw.insert("", "end", values=row_data)
            
            print(f"Raw data table refreshed with {len(data)} rows (preserved {len(self.modified_rows)} modified rows)")
        else:
            # No data available, clear the tree
            self.tree_raw.delete(*self.tree_raw.get_children())
            self.tree_raw["columns"] = []

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
            # Use enhanced team stats with proper phase scoring and robot valuation
            team_num = s.get("team")
            
            # Calculate enhanced phase scores using the same logic as team stats
            phase_scores = self.analizador.calculate_team_phase_scores(int(team_num))
            
            # Get robot valuation for better ranking assessment
            robot_valuation = s.get("robot_valuation", 0)
            
            # Enhanced EPA calculation with weighted scoring
            auto_epa = phase_scores["autonomous"] * 2.0  # Auto gets 2x multiplier
            teleop_epa = phase_scores["teleop"] * 1.0
            endgame_epa = phase_scores["endgame"] * 1.1  # Endgame gets 1.1x multiplier
            
            # Calculate total EPA with proper weighting
            total_epa = (auto_epa * 0.3) + (teleop_epa * 0.5) + (endgame_epa * 0.2)
            
            # Enhanced defense detection using multiple indicators
            defense_rate = s.get("teleop_crossed_played_defense_rate", 0)
            died_rate = s.get("died_rate", 0)
            consistency = s.get("overall_std", float('inf'))
            
            # A team is defensive if they play defense regularly OR have low death/high consistency
            is_defensive = (defense_rate > 0.3) or (died_rate < 0.1 and consistency < 15)
            
            # Calculate enhanced team metrics
            consistency_score = max(0, min(100, 100 - (consistency * 2)))  # Convert std to 0-100 scale
            clutch_factor = min(100, max(0, (robot_valuation * 0.8) + (50 - consistency)))  # Combination of skill and consistency
            
            team_dicts.append({
                "num": team_num,
                "rank": idx + 1,
                "total_epa": total_epa,
                "auto_epa": auto_epa,
                "teleop_epa": teleop_epa,
                "endgame_epa": endgame_epa,
                "defense": is_defensive,
                "name": team_num,
                "robot_valuation": robot_valuation,
                "overall_avg": s.get("overall_avg", 0),
                "phase_scores": phase_scores,
                "consistency_score": consistency_score,
                "clutch_factor": clutch_factor
            })
        teams = teams_from_dicts(team_dicts)

        if not hasattr(self, 'alliance_selector') or self.alliance_selector is None or len(self.alliance_selector.teams) != len(teams):
            self.alliance_selector = AllianceSelector(teams)
        else:
            # Update existing selector with new team data
            self.alliance_selector.update_teams(teams)
        selector = self.alliance_selector

        # Update alliance table
        self.update_alliance_table()
        
        # Create controls only if they don't exist
        self.create_alliance_selector_controls()

    def update_alliance_table(self):
        """Update only the alliance table without recreating controls"""
        if not hasattr(self, 'alliance_selector') or self.alliance_selector is None:
            return
            
        self.update_alliance_combobox_options()  # Update combobox options first
        
        selector = self.alliance_selector
        table = selector.get_alliance_table()
        columns = ["Alliance #", "Captain", "Pick 1", "Recommendation 1", "Pick 2", "Recommendation 2", "Alliance Score", "Combined EPA", "Strategy Notes"]
        self.tree_alliance.delete(*self.tree_alliance.get_children())
        self.tree_alliance["columns"] = columns
        for col in columns:
            self.tree_alliance.heading(col, text=col)
            if col in ["Strategy Notes"]:
                self.tree_alliance.column(col, width=200, anchor=tk.W)
            elif col in ["Combined EPA"]:
                self.tree_alliance.column(col, width=100, anchor=tk.W)
            else:
                self.tree_alliance.column(col, width=120, anchor=tk.W)

        # Get team_dicts for strategic insights
        stats = self.analizador.get_detailed_team_stats()
        team_dicts = []
        for idx, s in enumerate(stats):
            team_num = s.get("team")
            phase_scores = self.analizador.calculate_team_phase_scores(int(team_num))
            robot_valuation = s.get("robot_valuation", 0)
            auto_epa = phase_scores["autonomous"] * 2.0
            teleop_epa = phase_scores["teleop"] * 1.0
            endgame_epa = phase_scores["endgame"] * 1.1
            total_epa = (auto_epa * 0.3) + (teleop_epa * 0.5) + (endgame_epa * 0.2)
            defense_rate = s.get("teleop_crossed_played_defense_rate", 0)
            died_rate = s.get("died_rate", 0)
            consistency = s.get("overall_std", float('inf'))
            is_defensive = (defense_rate > 0.3) or (died_rate < 0.1 and consistency < 15)
            
            team_dicts.append({
                "num": team_num,
                "total_epa": total_epa,
                "auto_epa": auto_epa,
                "defense": is_defensive,
                "robot_valuation": robot_valuation
            })

        # Enhanced alliance table with strategic insights
        for row in table:
            alliance_num = row["Alliance #"]
            captain = row["Captain"]
            pick1 = row["Pick 1"]
            pick2 = row["Pick 2"]
            alliance_score = row["Alliance Score"]
            
            # Calculate combined EPA and strategic notes
            combined_epa = 0
            strategy_notes = []
            
            for team_num in [captain, pick1, pick2]:
                if team_num:
                    team_data = next((t for t in team_dicts if t["num"] == team_num), None)
                    if team_data:
                        combined_epa += team_data["total_epa"]
                        if team_data["defense"]:
                            strategy_notes.append(f"{team_num}:DEF")
                        if team_data["robot_valuation"] > 85:
                            strategy_notes.append(f"{team_num}:ELITE")
                        if team_data["auto_epa"] > 50:
                            strategy_notes.append(f"{team_num}:AUTO")
            
            strategy_text = ", ".join(strategy_notes) if strategy_notes else "Standard"
            
            self.tree_alliance.insert("", "end", values=[
                alliance_num, captain, pick1, row["Recommendation 1"], pick2, row["Recommendation 2"], 
                f"{alliance_score:.1f}", f"{combined_epa:.1f}", strategy_text
            ])

    def update_alliance_combobox_options(self):
        """Update the available options in alliance selector comboboxes"""
        if not hasattr(self, 'alliance_selector') or not self.alliance_selector:
            return
        if not hasattr(self, '_alliance_selector_combos') or not self._alliance_selector_combos:
            return
            
        selector = self.alliance_selector
        combo_index = 0
        
        for idx, alliance in enumerate(selector.alliances):
            # Update Pick 1 combobox
            if combo_index < len(self._alliance_selector_combos):
                pick1_combo = self._alliance_selector_combos[combo_index]
                available_pick1 = selector.get_available_teams(alliance.captainRank, 'pick1')
                pick1_options = [("", "No selection")] + [(str(t.team), f"{t.team} (Score: {t.score:.1f})") for t in available_pick1]
                pick1_combo['values'] = [label for _, label in pick1_options]
                
                # Preserve current selection if it's still valid
                current_value = pick1_combo.get()
                if alliance.pick1:
                    for val, label in pick1_options:
                        if val == str(alliance.pick1):
                            pick1_combo.set(label)
                            break
                else:
                    pick1_combo.set(pick1_options[0][1] if pick1_options else "No selection")
                
                combo_index += 1
            
            # Update Pick 2 combobox
            if combo_index < len(self._alliance_selector_combos):
                pick2_combo = self._alliance_selector_combos[combo_index]
                available_pick2 = selector.get_available_teams(alliance.captainRank, 'pick2')
                pick2_options = [("", "No selection")] + [(str(t.team), f"{t.team} (Score: {t.score:.1f})") for t in available_pick2]
                pick2_combo['values'] = [label for _, label in pick2_options]
                
                # Preserve current selection if it's still valid
                if alliance.pick2:
                    for val, label in pick2_options:
                        if val == str(alliance.pick2):
                            pick2_combo.set(label)
                            break
                else:
                    pick2_combo.set(pick2_options[0][1] if pick2_options else "No selection")
                
                combo_index += 1

    def create_alliance_selector_controls(self):
        """Create alliance selector controls only if they don't exist"""
        if hasattr(self, 'alliance_selector_controls') and self.alliance_selector_controls:
            return  # Controls already exist, don't recreate them
        
        selector = self.alliance_selector
        
        # --- Add Comboboxes for interactive pick selection ---
        # Remove previous controls if any
        if hasattr(self, 'alliance_selector_controls') and self.alliance_selector_controls:
            self.alliance_selector_controls.destroy()
        self.alliance_selector_controls = ttk.Frame(self.alliance_frame)
        self.alliance_selector_controls.pack(fill=tk.X, padx=4, pady=4)

        # Enhanced alliance selection controls with optimization
        optimization_frame = ttk.LabelFrame(self.alliance_selector_controls, text="Alliance Optimization")
        optimization_frame.grid(row=0, column=3, columnspan=2, padx=10, pady=5, sticky='ew')
        
        ttk.Button(optimization_frame, text="Auto-Optimize All", 
                  command=self.auto_optimize_alliances).pack(side=tk.LEFT, padx=2)
        ttk.Button(optimization_frame, text="Balance Strategies", 
                  command=self.balance_alliance_strategies).pack(side=tk.LEFT, padx=2)
        ttk.Button(optimization_frame, text="Reset Picks", 
                  command=lambda: [selector.reset_picks(), self.refresh_alliance_selector_tab()]).pack(side=tk.LEFT, padx=2)

        # Alliance selector grid
        ttk.Label(self.alliance_selector_controls, text="Alliance #").grid(row=1, column=0)
        ttk.Label(self.alliance_selector_controls, text="Pick 1").grid(row=1, column=1)
        ttk.Label(self.alliance_selector_controls, text="Pick 2").grid(row=1, column=2)

        self._alliance_selector_combos = []
        for idx, a in enumerate(selector.alliances):
            ttk.Label(self.alliance_selector_controls, text=str(a.allianceNumber)).grid(row=idx+2, column=0, sticky='w')

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
            def on_pick1(event, idx=idx, pick1_var=pick1_var):
                selected_label = pick1_var.get()
                selected_team = ""
                
                # Get current available teams dynamically
                current_available = selector.get_available_teams(selector.alliances[idx].captainRank, 'pick1')
                current_options = [("", "No selection")] + [(str(t.team), f"{t.team} (Score: {t.score:.1f})") for t in current_available]
                
                for val, label in current_options:
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
                self.update_alliance_table()
            pick1_combo.bind("<<ComboboxSelected>>", on_pick1)
            pick1_combo.grid(row=idx+2, column=1, sticky='w')
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
            def on_pick2(event, idx=idx, pick2_var=pick2_var):
                selected_label = pick2_var.get()
                selected_team = ""
                
                # Get current available teams dynamically
                current_available = selector.get_available_teams(selector.alliances[idx].captainRank, 'pick2')
                current_options = [("", "No selection")] + [(str(t.team), f"{t.team} (Score: {t.score:.1f})") for t in current_available]
                
                for val, label in current_options:
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
                self.update_alliance_table()
            pick2_combo.bind("<<ComboboxSelected>>", on_pick2)
            pick2_combo.grid(row=idx+2, column=2, sticky='w')
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

    def configure_camera(self):
        """Configure camera settings and selection."""
        try:
            import cv2
        except ImportError:
            messagebox.showerror("Missing Dependencies", 
                               "OpenCV not found. Please install: pip install opencv-python")
            return

        camera_win = tk.Toplevel(self.root)
        camera_win.title("Camera Configuration")
        camera_win.transient(self.root)
        camera_win.grab_set()
        camera_win.geometry("400x300")
        
        main_frame = ttk.Frame(camera_win, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(main_frame, text="Camera Configuration", 
                 font=("Arial", 12, "bold")).pack(pady=(0, 10))
        
        # Camera selection
        camera_frame = ttk.LabelFrame(main_frame, text="Camera Selection")
        camera_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(camera_frame, text="Select Camera:").pack(anchor=tk.W, padx=5, pady=2)
        
        camera_var = tk.IntVar(value=0)
        camera_combo = ttk.Combobox(camera_frame, textvariable=camera_var, state="readonly")
        camera_combo.pack(fill=tk.X, padx=5, pady=2)
        
        # Detect available cameras
        available_cameras = []
        for i in range(5):  # Check first 5 camera indices
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    available_cameras.append(f"Camera {i}")
                    cap.release()
            except:
                pass
        
        if not available_cameras:
            available_cameras = ["No cameras detected"]
        
        camera_combo['values'] = available_cameras
        camera_combo.current(0)
        
        # Camera settings
        settings_frame = ttk.LabelFrame(main_frame, text="Camera Settings")
        settings_frame.pack(fill=tk.X, pady=5)
        
        # Resolution
        ttk.Label(settings_frame, text="Resolution:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        resolution_var = tk.StringVar(value="640x480")
        resolution_combo = ttk.Combobox(settings_frame, textvariable=resolution_var, 
                                       values=["320x240", "640x480", "800x600", "1024x768", "1280x720", "1920x1080"],
                                       state="readonly")
        resolution_combo.grid(row=0, column=1, padx=5, pady=2, sticky=tk.W)
        resolution_combo.current(1)
        
        # Test camera function
        def test_selected_camera():
            try:
                camera_index = camera_combo.current()
                if camera_index < 0 or "No cameras" in camera_combo.get():
                    messagebox.showerror("Error", "No camera selected or available")
                    return
                
                cap = cv2.VideoCapture(camera_index)
                if not cap.isOpened():
                    messagebox.showerror("Camera Error", f"Could not open Camera {camera_index}")
                    return
                
                # Set resolution
                resolution = resolution_var.get().split('x')
                width, height = int(resolution[0]), int(resolution[1])
                cap.set(cv2.CAP_PROP_FRAME_WIDTH, width)
                cap.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
                
                # Test capture
                ret, frame = cap.read()
                cap.release()
                
                if ret:
                    messagebox.showinfo("Camera Test", 
                                      f"Camera {camera_index} test successful!\n"
                                      f"Resolution: {width}x{height}")
                else:
                    messagebox.showerror("Camera Test", "Failed to capture frame from camera")
                    
            except Exception as e:
                messagebox.showerror("Camera Test Failed", f"Error: {e}")
        
        # Buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Test Camera", command=test_selected_camera).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save Settings", 
                  command=lambda: self._save_camera_settings(camera_var.get(), resolution_var.get(), camera_win)).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Close", command=camera_win.destroy).pack(side=tk.RIGHT, padx=5)
        
        # Instructions
        instructions = """
Instructions:
1. Select your preferred camera from the dropdown
2. Choose the desired resolution
3. Test the camera to ensure it works
4. Save settings to apply for QR scanning
        """
        ttk.Label(main_frame, text=instructions, justify=tk.LEFT, foreground="gray").pack(pady=5)
    
    def _save_camera_settings(self, camera_index, resolution, window):
        """Save camera settings to configuration."""
        try:
            # Store camera settings (you can expand this to save to config file)
            self.camera_index = camera_index
            self.camera_resolution = resolution
            messagebox.showinfo("Settings Saved", 
                              f"Camera settings saved:\nCamera: {camera_index}\nResolution: {resolution}")
            window.destroy()
        except Exception as e:
            messagebox.showerror("Save Error", f"Failed to save settings: {e}")

    def open_system_configuration(self):
        """Comprehensive system configuration window."""
        config_win = tk.Toplevel(self.root)
        config_win.title("System Configuration")
        config_win.transient(self.root)
        config_win.grab_set()
        config_win.geometry("800x600")
        
        # Create notebook for different configuration sections
        notebook = ttk.Notebook(config_win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Column Configuration Tab
        column_frame = ttk.Frame(notebook)
        notebook.add(column_frame, text="📋 Columns & Data")
        self._create_column_config_tab(column_frame)
        
        # Game Phases Tab
        phases_frame = ttk.Frame(notebook)
        notebook.add(phases_frame, text="🎮 Game Phases")
        self._create_phases_config_tab(phases_frame)
        
        # Robot Valuation Tab
        valuation_frame = ttk.Frame(notebook)
        notebook.add(valuation_frame, text="🤖 Robot Valuation")
        self._create_valuation_config_tab(valuation_frame)
        
        # Import/Export Tab
        io_frame = ttk.Frame(notebook)
        notebook.add(io_frame, text="💾 Import/Export")
        self._create_io_config_tab(io_frame)
        
        # System Info Tab
        info_frame = ttk.Frame(notebook)
        notebook.add(info_frame, text="ℹ️ System Info")
        self._create_info_tab(info_frame)
    
    def _create_column_config_tab(self, parent):
        """Create column configuration tab content."""
        frame = ttk.Frame(parent, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Column Configuration", 
                 font=("Arial", 12, "bold")).pack(pady=(0, 10))
        
        # Quick actions
        actions_frame = ttk.LabelFrame(frame, text="Quick Actions")
        actions_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(actions_frame, text="Configure Columns", 
                  command=self.configure_columns).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(actions_frame, text="Update Headers", 
                  command=self.update_header).pack(side=tk.LEFT, padx=5, pady=5)
        ttk.Button(actions_frame, text="Auto-detect Phases", 
                  command=self._auto_detect_phases).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Current configuration summary
        summary_frame = ttk.LabelFrame(frame, text="Current Configuration")
        summary_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Create text widget with scrollbar
        text_frame = ttk.Frame(summary_frame)
        text_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        summary_text = tk.Text(text_frame, wrap=tk.WORD, height=15)
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=summary_text.yview)
        summary_text.configure(yscrollcommand=scrollbar.set)
        
        summary_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Populate summary
        config_summary = self.analizador.get_columns_config_summary()
        summary_content = f"""Configuration Summary:

Total Headers: {config_summary['total_headers']}

Column Categories:
• Numeric for Overall: {config_summary['numeric_for_overall_count']} columns
• Stats Columns: {config_summary['stats_columns_count']} columns  
• Mode Boolean: {config_summary['mode_boolean_count']} columns

Game Phases:
• Autonomous: {config_summary['autonomous_columns_count']} columns
• Teleop: {config_summary['teleop_columns_count']} columns
• Endgame: {config_summary['endgame_columns_count']} columns

Autonomous Columns:
{chr(10).join('• ' + col for col in config_summary['game_phases_configured']['autonomous'])}

Teleop Columns:
{chr(10).join('• ' + col for col in config_summary['game_phases_configured']['teleop'])}

Endgame Columns:
{chr(10).join('• ' + col for col in config_summary['game_phases_configured']['endgame'])}

Robot Valuation Weights: {config_summary['robot_valuation_weights']}
"""
        
        summary_text.insert(tk.END, summary_content)
        summary_text.config(state=tk.DISABLED)
    
    def _create_phases_config_tab(self, parent):
        """Create game phases configuration tab content."""
        frame = ttk.Frame(parent, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Game Phases Configuration", 
                 font=("Arial", 12, "bold")).pack(pady=(0, 10))
        
        ttk.Button(frame, text="Open Game Phase Configuration", 
                  command=self.show_phase_config).pack(pady=5)
        
        # Phase summary
        ttk.Label(frame, text="Current phases are automatically detected based on column names.\n"
                             "You can manually configure them using the button above.",
                 justify=tk.CENTER).pack(pady=10)
    
    def _create_valuation_config_tab(self, parent):
        """Create robot valuation configuration tab content."""
        frame = ttk.Frame(parent, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Robot Valuation Configuration", 
                 font=("Arial", 12, "bold")).pack(pady=(0, 10))
        
        ttk.Button(frame, text="Configure Robot Valuation Weights", 
                  command=self.configure_robot_valuation_weights).pack(pady=5)
        
        # Current weights display
        weights = self.analizador.get_robot_valuation_phase_weights()
        weight_text = f"Current Weights:\nEarly Season: {weights[0]:.2f}\nMid Season: {weights[1]:.2f}\nLate Season: {weights[2]:.2f}"
        ttk.Label(frame, text=weight_text, justify=tk.CENTER).pack(pady=10)
    
    def _create_io_config_tab(self, parent):
        """Create import/export configuration tab content."""
        frame = ttk.Frame(parent, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="Import/Export Configuration", 
                 font=("Arial", 12, "bold")).pack(pady=(0, 10))
        
        # Export section
        export_frame = ttk.LabelFrame(frame, text="Export Configuration")
        export_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(export_frame, text="Export Current Configuration", 
                  command=self._export_config).pack(pady=5)
        
        # Import section
        import_frame = ttk.LabelFrame(frame, text="Import Configuration")
        import_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(import_frame, text="Import Configuration File", 
                  command=self._import_config).pack(pady=5)
        
        # Presets section
        presets_frame = ttk.LabelFrame(frame, text="Configuration Presets")
        presets_frame.pack(fill=tk.X, pady=5)
        
        presets = self.analizador.get_available_presets()
        for preset_name in presets.keys():
            ttk.Button(presets_frame, text=f"Apply {preset_name.title()} Format", 
                      command=lambda p=preset_name: self._apply_preset(p)).pack(side=tk.LEFT, padx=5, pady=5)
    
    def _create_info_tab(self, parent):
        """Create system information tab content."""
        frame = ttk.Frame(parent, padding=10)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="System Information", 
                 font=("Arial", 12, "bold")).pack(pady=(0, 10))
        
        info_text = f"""Alliance Simulator - Team Stats and Selector

Current Data:
• Total rows: {len(self.analizador.sheet_data) - 1 if self.analizador.sheet_data else 0}
• Headers: {len(self.analizador.get_current_headers())}
• Teams analyzed: {len(self.analizador.get_team_data_grouped()) if self.analizador.sheet_data else 0}

Features:
• CSV data import and QR code scanning
• Comprehensive team statistics analysis  
• Alliance selection optimization
• Honor roll scoring system
• Match prediction (Foreshadowing)
• Robot performance valuation

Configuration:
• Format detection and conversion
• Customizable column mapping
• Game phase analysis
• Export/import settings
"""
        
        ttk.Label(frame, text=info_text, justify=tk.LEFT).pack(anchor=tk.W)
    
    def _auto_detect_phases(self):
        """Auto-detect game phases."""
        self.analizador._auto_detect_game_phase_columns()
        messagebox.showinfo("Auto-detection", "Game phases have been auto-detected based on column names.")
        self.refresh_all()
    
    def _export_config(self):
        """Export configuration to file."""
        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export Configuration"
        )
        if file_path:
            if self.analizador.export_columns_config(file_path):
                messagebox.showinfo("Export", f"Configuration exported to {file_path}")
    
    def _import_config(self):
        """Import configuration from file."""
        file_path = filedialog.askopenfilename(
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Import Configuration"
        )
        if file_path:
            success, message = self.analizador.import_columns_config(file_path)
            if success:
                messagebox.showinfo("Import", "Configuration imported successfully!")
                self.refresh_all()
            else:
                messagebox.showerror("Import Error", f"Failed to import: {message}")
    
    def _apply_preset(self, preset_name):
        """Apply a configuration preset."""
        if self.analizador.apply_configuration_preset(preset_name):
            messagebox.showinfo("Preset Applied", f"{preset_name.title()} configuration applied successfully!")
            self.refresh_all()
        else:
            messagebox.showerror("Preset Error", f"Failed to apply {preset_name} preset")

    def open_foreshadowing(self):
        def _launch():
            try:
                from foreshadowing import launch_foreshadowing
            except ImportError as e:
                messagebox.showerror("Foreshadowing", f"No se pudo importar módulo: {e}")
                return
            launch_foreshadowing(self.root, self.analizador)
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
        
        # Calculate correct row index in sheet_data
        # tree_raw items are indexed starting from 0, sheet_data[0] is headers, so data starts at index 1
        row_index = self.tree_raw.index(item) + 1
        
        # Create edit dialog
        edit_window = tk.Toplevel(self.root)
        edit_window.title("Edit Row")
        edit_window.transient(self.root)
        edit_window.grab_set()
        edit_window.geometry("500x600")
        
        # Create scrollable frame for many fields
        canvas = tk.Canvas(edit_window)
        scrollbar = ttk.Scrollbar(edit_window, orient="vertical", command=canvas.yview)
        scrollable_frame = ttk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # Create form fields
        entries = {}
        for i, (header, value) in enumerate(zip(headers, current_values)):
            ttk.Label(scrollable_frame, text=f"{header}:").grid(row=i, column=0, sticky='e', padx=5, pady=2)
            entry = ttk.Entry(scrollable_frame, width=40)
            entry.insert(0, str(value))
            entry.grid(row=i, column=1, padx=5, pady=2)
            entries[header] = entry
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # Buttons frame
        btn_frame = ttk.Frame(edit_window)
        btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        def save_changes():
            try:
                new_values = [entries[header].get() for header in headers]
                
                # Update treeview
                self.tree_raw.item(item, values=new_values)
                
                # Update analyzer data - ensure we have enough space
                while len(self.analizador.sheet_data) <= row_index:
                    self.analizador.sheet_data.append([''] * len(headers))
                
                self.analizador.sheet_data[row_index] = new_values
                
                # Mark this row as modified
                self.modified_rows.add(row_index)
                
                # Update column indices in case structure changed
                self.analizador._update_column_indices()
                
                messagebox.showinfo("Success", "Row updated successfully!")
                self.status_var.set("Row updated. Changes are saved in memory. Use 'Save Changes' to export to file.")
                edit_window.destroy()
                
            except Exception as e:
                messagebox.showerror("Error", f"Failed to save changes: {e}")
        
        ttk.Button(btn_frame, text="Save", command=save_changes).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Cancel", command=edit_window.destroy).pack(side=tk.LEFT, padx=5)

    def delete_raw_data_row(self):
        """Delete the selected row from the raw data table."""
        selection = self.tree_raw.selection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a row to delete.")
            return
        
        # Confirm deletion
        result = messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected row?")
        if not result:
            return
        
        try:
            item = selection[0]
            # Get the correct row index in sheet_data
            row_index = self.tree_raw.index(item) + 1  # +1 because sheet_data[0] is headers
            
            # Validate row index
            if row_index < len(self.analizador.sheet_data) and row_index > 0:
                # Remove from analyzer data first
                self.analizador.sheet_data.pop(row_index)
                
                # Remove from treeview
                self.tree_raw.delete(item)
                
                # Update tracking sets - shift indices down for rows after deleted row
                new_modified_rows = set()
                for mod_row in self.modified_rows:
                    if mod_row < row_index:
                        new_modified_rows.add(mod_row)
                    elif mod_row > row_index:
                        new_modified_rows.add(mod_row - 1)
                    # Don't add mod_row if it equals row_index (it's being deleted)
                self.modified_rows = new_modified_rows
                
                # Update column indices in case structure changed
                self.analizador._update_column_indices()
                
                messagebox.showinfo("Success", "Row deleted successfully!")
                self.status_var.set("Row deleted. Changes are saved in memory. Use 'Save Changes' to export to file.")
            else:
                messagebox.showerror("Error", f"Invalid row index: {row_index}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete row: {e}")
            print(f"Delete error: {e}")  # Debug info

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
                
                # Clear modification tracking since data has been saved
                self.modified_rows.clear()
                
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
        """Auto-populate SchoolSystem with teams from raw data using enhanced calculated phase scores"""
        team_data = self.analizador.get_team_data_grouped()
        if not team_data:
            messagebox.showwarning("No Data", "No team data available. Please load some data first.")
            return
        
        teams_added = 0
        teams_with_calculated_scores = 0
        
        # Get enhanced team stats for better scoring
        team_stats_dict = {}
        detailed_stats = self.analizador.get_detailed_team_stats()
        for stat in detailed_stats:
            team_stats_dict[str(stat["team"])] = stat
        
        for team_number in team_data.keys():
            self.school_system.add_team(team_number)
            
            # Calculate enhanced scores from game phases with proper weighting
            phase_scores = self.analizador.calculate_team_phase_scores(int(team_number))
            
            if any(score > 0 for score in phase_scores.values()):
                # Use calculated scores from actual data with enhanced scaling
                # Match performance should reflect actual game performance similar to overall and robot valuation
                
                # Get the stats for comparison with robot valuation and overall
                team_stat = team_stats_dict.get(team_number, {})
                overall_avg = team_stat.get("overall_avg", 0)
                robot_valuation = team_stat.get("RobotValuation", 0)
                
                # Instead of arbitrary scaling, use the relationship between phase scores and overall performance
                # Phase scores are raw averages, but match performance should be scaled to be comparable to overall/robot_valuation
                
                # Calculate scaling factor based on the relationship between raw scores and final metrics
                if overall_avg > 0:
                    # Scale phase scores to be in a similar range as overall performance
                    # Typical overall scores are 20-100, phase scores might be 0-20
                    total_phase_score = sum(phase_scores.values())
                    if total_phase_score > 0:
                        # Scale factor to make match performance comparable to overall
                        # Increased multiplier to get closer to the 0.8x target ratio
                        scale_factor = overall_avg / total_phase_score * 2.5  # Increased from 0.8 to 2.5
                    else:
                        scale_factor = 1.0
                else:
                    # Fallback scaling based on typical game scoring
                    scale_factor = 5.0  # Increased from 3.0 to 5.0
                
                # Apply scaling with reasonable bounds
                scale_factor = max(2.0, min(10.0, scale_factor))  # Increased minimum from 1.0 to 2.0
                
                auto_scaled = min(100, max(0, phase_scores["autonomous"] * scale_factor))
                teleop_scaled = min(100, max(0, phase_scores["teleop"] * scale_factor))
                endgame_scaled = min(100, max(0, phase_scores["endgame"] * scale_factor))
                
                self.school_system.update_autonomous_score(team_number, auto_scaled)
                self.school_system.update_teleop_score(team_number, teleop_scaled)
                self.school_system.update_endgame_score(team_number, endgame_scaled)
                teams_with_calculated_scores += 1
            else:
                # Use enhanced default values based on ranking
                rank_factor = max(0.5, 1.0 - (teams_added * 0.05))  # Decreasing factor for lower teams
                self.school_system.update_autonomous_score(team_number, 75.0 * rank_factor)
                self.school_system.update_teleop_score(team_number, 80.0 * rank_factor)
                self.school_system.update_endgame_score(team_number, 70.0 * rank_factor)
            
            # Enhanced pit scouting scores based on team performance
            team_stat = team_stats_dict.get(team_number, {})
            robot_valuation = team_stat.get("robot_valuation", 50)
            overall_avg = team_stat.get("overall_avg", 50)
            
            # Scale pit scores based on robot valuation and performance
            base_electrical = 85.0
            base_mechanical = 80.0
            performance_factor = min(1.3, max(0.7, robot_valuation / 70))  # Scale based on robot quality
            
            self.school_system.update_electrical_score(team_number, base_electrical * performance_factor)
            self.school_system.update_mechanical_score(team_number, base_mechanical * performance_factor)
            self.school_system.update_driver_station_layout_score(team_number, 75.0 + (overall_avg * 0.3))
            self.school_system.update_tools_score(team_number, 70.0 + (robot_valuation * 0.2))
            self.school_system.update_spare_parts_score(team_number, 65.0 + (robot_valuation * 0.15))
            
            # Enhanced during event scores based on team behavior and performance
            consistency = 100 - team_stat.get("overall_std", 20)  # Lower std = higher organization
            collaboration_base = 85.0
            
            self.school_system.update_team_organization_score(team_number, max(60, min(95, consistency)))
            self.school_system.update_collaboration_score(team_number, collaboration_base)
            
            # Enhanced competency inference from performance data
            if team_number in team_stats_dict:
                stats = team_stats_dict[team_number]
                
                # Enhanced reliability detection
                died_rate = stats.get("died_rate", 0.5)
                if died_rate < 0.15:  # Very low death rate
                    self.school_system.update_competency(team_number, "no_deaths", True)
                    self.school_system.update_competency(team_number, "reliability", True)
                
                # Enhanced driving skills detection
                teleop_score = phase_scores["teleop"]
                if teleop_score > 70:
                    self.school_system.update_competency(team_number, "driving_skills", True)
                
                # Enhanced autonomous competency
                auto_score = phase_scores["autonomous"]
                if auto_score > 60:
                    self.school_system.update_competency(team_number, "pasar_inspeccion_primera", True)
                
                # Enhanced subcompetencies based on overall performance
                if overall_avg > 75:
                    self.school_system.update_competency(team_number, "win_most_games", True)
                
                if robot_valuation > 80:
                    self.school_system.update_competency(team_number, "commitment", True)
                
                # Consistency and pressure performance
                overall_std = stats.get("overall_std", float('inf'))
                if overall_std < 10:  # Very consistent performance
                    self.school_system.update_competency(team_number, "working_under_pressure", True)
            
            # Set enhanced default competencies
            self.school_system.update_competency(team_number, "team_communication", True)
            
            teams_added += 1
        
        self.refresh_honor_roll_tab()
        
        message = f"Enhanced auto-population complete!\n\n"
        message += f"📊 Teams added: {teams_added}\n"
        message += f"🎯 Teams with calculated scores: {teams_with_calculated_scores}\n"
        message += f"⚙️ Teams with defaults: {teams_added - teams_with_calculated_scores}\n\n"
        message += f"🔧 Enhanced Features:\n"
        message += f"• Pit scores scaled by robot valuation\n"
        message += f"• Competencies inferred from performance\n"
        message += f"• Organization based on consistency\n"
        message += f"• Phase scores properly weighted\n\n"
        message += f"💡 Note: Review and adjust pit scouting scores as needed."
        
        messagebox.showinfo("Enhanced Auto-populate Complete", message)

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

    def export_tier_list(self):
        """Export Honor Roll results to tier_list.txt format with detailed team information"""
        if not self.school_system.teams:
            messagebox.showwarning("No Data", "No teams in SchoolSystem to export.")
            return
        
        # Ask for images folder
        images_folder = None
        result = messagebox.askyesno("Robot Images", 
                                   "¿Quieres seleccionar una carpeta con las imágenes de los robots?\n\n"
                                   "Las imágenes deben tener el nombre del número del equipo (ej: 1234.png)\n"
                                   "Si no seleccionas carpeta, se usarán imágenes por defecto.")
        
        if result:
            images_folder = filedialog.askdirectory(title="Seleccionar carpeta con imágenes de robots")
            if images_folder:
                messagebox.showinfo("Carpeta seleccionada", f"Usando imágenes de: {images_folder}")
            else:
                messagebox.showinfo("Sin carpeta", "Se usarán imágenes por defecto")
        
        file_path = filedialog.asksaveasfilename(
            defaultextension=".txt",
            filetypes=[("Text Files", "*.txt"), ("All Files", "*.*")],
            title="Export Tier List",
            initialfile="tier_list.txt"
        )
        
        if file_path:
            try:
                # Debug information
                print(f"Starting tier list export...")
                
                rankings = self.school_system.get_honor_roll_ranking()
                disqualified = self.school_system.get_disqualified_teams()
                
                print(f"Found {len(rankings)} qualified teams, {len(disqualified)} disqualified teams")
                
                # Get all teams stats for additional information
                all_team_stats = {}
                if hasattr(self, 'analizador') and self.analizador:
                    try:
                        stats = self.analizador.get_detailed_team_stats()
                        for stat in stats:
                            team_num = str(stat.get('team_number', 'unknown'))
                            if team_num != 'unknown':
                                all_team_stats[team_num] = stat
                        print(f"Loaded stats for {len(all_team_stats)} teams")
                    except Exception as e:
                        print(f"Warning: Could not load team stats: {e}")
                        all_team_stats = {}
                
                # Get defensive teams info from the analyzer (ALL defensive teams, not just disqualified)
                defensive_teams = set()
                if hasattr(self, 'analizador') and self.analizador:
                    try:
                        defensive_ranking = self.analizador.get_defensive_robot_ranking()
                        # Teams with defense rate > 0.3 are considered defensive
                        defensive_teams = {str(team.get('team_number', '')) for team in defensive_ranking if team.get('defense_rate', 0) > 0.3}
                        # Remove empty team numbers
                        defensive_teams.discard('')
                        print(f"Found {len(defensive_teams)} defensive teams: {defensive_teams}")
                    except Exception as e:
                        print(f"Warning: Could not load defensive teams: {e}")
                        defensive_teams = set()
                
                # Categorize qualified teams into picks
                qualified_teams = [team_num for team_num, _ in rankings]
                total_qualified = len(qualified_teams)
                
                print(f"Qualified teams: {qualified_teams}")
                
                # Remove defensive teams from qualified teams (they go to Defense Pick regardless of qualification)
                qualified_non_defensive = [team for team in qualified_teams if team not in defensive_teams]
                
                print(f"Qualified non-defensive teams: {qualified_non_defensive}")
                
                # Divide non-defensive qualified teams into 3 tiers
                if qualified_non_defensive:
                    tier_1_size = max(1, len(qualified_non_defensive) // 3)
                    tier_2_size = max(1, len(qualified_non_defensive) // 3)
                    
                    tier_1_teams = qualified_non_defensive[:tier_1_size]
                    tier_2_teams = qualified_non_defensive[tier_1_size:tier_1_size + tier_2_size]
                    tier_3_teams = qualified_non_defensive[tier_1_size + tier_2_size:]
                else:
                    tier_1_teams = []
                    tier_2_teams = []
                    tier_3_teams = []
                
                # All disqualified non-defensive teams go to dash tier
                disqualified_teams = [team_num for team_num, _ in disqualified]
                disqualified_non_defensive = [team for team in disqualified_teams if team not in defensive_teams]
                
                print(f"Tier distribution: 1st={tier_1_teams}, 2nd={tier_2_teams}, 3rd={tier_3_teams}")
                print(f"Defense={defensive_teams}, Dash={disqualified_non_defensive}")
                
                # Function to get team information for detailed export
                def get_team_info(team_num):
                    """Get detailed team information for tier list export"""
                    try:
                        # Ensure team_num is string
                        team_num = str(team_num)
                        
                        # Get honor roll data (always available if we got here)
                        honor_result = self.school_system.get_team_results(team_num)
                        
                        # Get team stats (may not be available)
                        team_stats = all_team_stats.get(team_num, {})
                        
                        # Create team information with safe defaults
                        team_info = {
                            'title': f"Team {team_num}",
                            'text': {
                                'honor_score': round(honor_result.honor_roll_score, 1) if honor_result else 0.0,
                                'final_points': honor_result.final_points if honor_result else 0,
                                'overall_avg': round(float(team_stats.get('overall_avg', 0.0)), 2),
                                'robot_valuation': round(float(team_stats.get('robot_valuation', 0.0)), 2),
                                'defense_rate': round(float(team_stats.get('teleop_crossed_played_defense_rate', 0.0)), 3),
                                'died_rate': round(float(team_stats.get('died_rate', 0.0)), 3),
                                'matches_played': int(team_stats.get('matches_played', 0))
                            },
                            'driverSkills': 'Defensive' if team_num in defensive_teams else 'Offensive'
                        }
                        return team_info
                    except Exception as e:
                        print(f"Error getting team info for {team_num}: {e}")
                        # Return minimal safe info if there's any error
                        return {
                            'title': f"Team {team_num}",
                            'text': {
                                'honor_score': 0.0,
                                'final_points': 0,
                                'overall_avg': 0.0,
                                'robot_valuation': 0.0,
                                'defense_rate': 0.0,
                                'died_rate': 0.0,
                                'matches_played': 0
                            },
                            'driverSkills': 'Offensive'
                        }
                
                # Write tier_list.txt in the detailed format
                with open(file_path, 'w', encoding='utf-8') as f:
                    try:
                        # 1st Pick tier
                        f.write("Tier: 1st Pick\n")
                        for team_num in tier_1_teams:
                            try:
                                team_info = get_team_info(team_num)
                                # Get team image (from folder or default)
                                team_image_base64 = load_team_image(team_num, images_folder)
                                f.write(f"  Image: {team_image_base64}\n")
                                f.write(f"    Title: {team_info['title']}\n")
                                f.write(f"    Text: {json.dumps(team_info['text'])}\n")
                                f.write(f"    DriverSkills: {team_info['driverSkills']}\n")
                                f.write(f"    ImageList:\n")
                            except Exception as e:
                                print(f"Error writing team {team_num} to 1st Pick: {e}")
                        f.write("\n")
                        
                        # 2nd Pick tier
                        f.write("Tier: 2nd Pick\n")
                        for team_num in tier_2_teams:
                            try:
                                team_info = get_team_info(team_num)
                                # Get team image (from folder or default)
                                team_image_base64 = load_team_image(team_num, images_folder)
                                f.write(f"  Image: {team_image_base64}\n")
                                f.write(f"    Title: {team_info['title']}\n")
                                f.write(f"    Text: {json.dumps(team_info['text'])}\n")
                                f.write(f"    DriverSkills: {team_info['driverSkills']}\n")
                                f.write(f"    ImageList:\n")
                            except Exception as e:
                                print(f"Error writing team {team_num} to 2nd Pick: {e}")
                        f.write("\n")
                        
                        # 3rd Pick tier
                        f.write("Tier: 3rd Pick\n")
                        for team_num in tier_3_teams:
                            try:
                                team_info = get_team_info(team_num)
                                # Get team image (from folder or default)
                                team_image_base64 = load_team_image(team_num, images_folder)
                                f.write(f"  Image: {team_image_base64}\n")
                                f.write(f"    Title: {team_info['title']}\n")
                                f.write(f"    Text: {json.dumps(team_info['text'])}\n")
                                f.write(f"    DriverSkills: {team_info['driverSkills']}\n")
                                f.write(f"    ImageList:\n")
                            except Exception as e:
                                print(f"Error writing team {team_num} to 3rd Pick: {e}")
                        f.write("\n")
                        
                        # Ojito tier (empty by default)
                        f.write("Tier: Ojito\n")
                        f.write("\n")
                        
                        # Dash tier (disqualified non-defensive teams)
                        f.write("Tier: -\n")
                        for team_num in disqualified_non_defensive:
                            try:
                                team_info = get_team_info(team_num)
                                # Get team image (from folder or default)
                                team_image_base64 = load_team_image(team_num, images_folder)
                                f.write(f"  Image: {team_image_base64}\n")
                                f.write(f"    Title: {team_info['title']}\n")
                                f.write(f"    Text: {json.dumps(team_info['text'])}\n")
                                f.write(f"    DriverSkills: {team_info['driverSkills']}\n")
                                f.write(f"    ImageList:\n")
                            except Exception as e:
                                print(f"Error writing team {team_num} to Dash tier: {e}")
                        f.write("\n")
                        
                        # Defense Pick tier (ALL defensive teams, qualified or not)
                        f.write("Tier: Defense Pick\n")
                        for team_num in sorted(defensive_teams):
                            try:
                                team_info = get_team_info(team_num)
                                # Get team image (from folder or default)
                                team_image_base64 = load_team_image(team_num, images_folder)
                                f.write(f"  Image: {team_image_base64}\n")
                                f.write(f"    Title: {team_info['title']}\n")
                                f.write(f"    Text: {json.dumps(team_info['text'])}\n")
                                f.write(f"    DriverSkills: {team_info['driverSkills']}\n")
                                f.write(f"    ImageList:\n")
                            except Exception as e:
                                print(f"Error writing team {team_num} to Defense Pick: {e}")
                        f.write("\n")
                        
                        # Unassigned tier (empty by default)
                        f.write("Tier: Unassigned\n")
                        f.write("\n")
                        
                    except Exception as e:
                        raise Exception(f"Error writing to file: {e}")
                
                # Show summary of categorization
                summary_msg = (
                    f"Tier List exported successfully!\n\n"
                    f"📊 Team Distribution:\n"
                    f"• 1st Pick: {len(tier_1_teams)} teams\n"
                    f"• 2nd Pick: {len(tier_2_teams)} teams\n"
                    f"• 3rd Pick: {len(tier_3_teams)} teams\n"
                    f"• Defense Pick: {len(defensive_teams)} teams (ALL defensive)\n"
                    f"• Dash (-): {len(disqualified_non_defensive)} teams\n\n"
                    f"📁 File saved to:\n{file_path}"
                )
                
                messagebox.showinfo("Export Complete", summary_msg)
                self.status_var.set(f"Tier List exported to {os.path.basename(file_path)}")
                
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export Tier List: {e}")

    def auto_optimize_alliances(self):
        """Automatically optimize alliance selections using enhanced algorithm"""
        if not hasattr(self, 'alliance_selector') or not self.alliance_selector:
            messagebox.showwarning("No Data", "Alliance selector not initialized.")
            return
        
        selector = self.alliance_selector
        
        # Reset current picks to start fresh
        selector.reset_picks()
        
        # Pick 1 round (1-8)
        for alliance in selector.alliances:
            available_teams = selector.get_available_teams(alliance.captainRank, 'pick1')
            if available_teams:
                try:
                    best_pick = self._find_optimal_pick(alliance, available_teams, "pick1")
                    if best_pick:
                        selector.set_pick(alliance.allianceNumber - 1, 'pick1', best_pick.team)
                except Exception as e:
                    print(f"Error setting pick1 for alliance {alliance.allianceNumber}: {e}")

        # Pick 2 round (8-1)
        for alliance in reversed(selector.alliances):
            available_teams = selector.get_available_teams(alliance.captainRank, 'pick2')
            if available_teams:
                try:
                    best_pick = self._find_optimal_pick(alliance, available_teams, "pick2")
                    if best_pick:
                        selector.set_pick(alliance.allianceNumber - 1, 'pick2', best_pick.team)
                except Exception as e:
                    print(f"Error setting pick2 for alliance {alliance.allianceNumber}: {e}")
        
        self.update_alliance_table()
        messagebox.showinfo("Auto-Optimization", "Alliance selections have been optimized using enhanced algorithm!")
    
    def _find_optimal_pick(self, alliance, available_teams, pick_type):
        """Find the optimal pick for an alliance considering team synergy"""
        if not available_teams:
            return None
        
        captain_team = next((t for t in self.alliance_selector.teams if t.team == alliance.captain), None)
        if not captain_team:
            return available_teams[0]  # Fallback to best available
        
        # Score each available team based on synergy with captain
        scored_teams = []
        for team in available_teams:
            synergy_score = self._calculate_team_synergy(captain_team, team, alliance, pick_type)
            scored_teams.append((team, synergy_score))
        
        # Sort by synergy score and return best match
        scored_teams.sort(key=lambda x: x[1], reverse=True)
        return scored_teams[0][0] if scored_teams else None
    
    def _calculate_team_synergy(self, captain, candidate, alliance, pick_type):
        """Calculate synergy score between captain and candidate team"""
        base_score = candidate.score
        
        # Synergy bonuses
        synergy_bonus = 0
        
        # Complement defensive strategies
        if captain.defense and not candidate.defense:
            synergy_bonus += 15  # Defensive captain with offensive pick
        elif not captain.defense and candidate.defense:
            synergy_bonus += 10  # Offensive captain with defensive pick
        
        # Complement autonomous strengths
        if captain.auto_epa > 40 and candidate.auto_epa > 40:
            synergy_bonus += 8  # Both strong in auto
        
        # Endgame synergy
        if captain.endgame_epa > 30 and candidate.endgame_epa > 30:
            synergy_bonus += 12  # Both strong in endgame
        
        # Consistency and clutch factor synergy
        if hasattr(candidate, 'consistency_score') and candidate.consistency_score > 80:
            synergy_bonus += 5  # Reliable performance
        
        if hasattr(candidate, 'clutch_factor') and candidate.clutch_factor > 75:
            synergy_bonus += 8  # Clutch performance
        
        # Robot valuation synergy
        if hasattr(candidate, 'robot_valuation') and candidate.robot_valuation > 85:
            synergy_bonus += 10  # Elite robot
        
        return base_score + synergy_bonus
    
    def balance_alliance_strategies(self):
        """Balance alliance strategies to ensure diverse approaches"""
        if not hasattr(self, 'alliance_selector') or not self.alliance_selector:
            messagebox.showwarning("No Data", "Alliance selector not initialized.")
            return
        
        selector = self.alliance_selector
        
        # Analyze current strategy distribution
        defensive_alliances = 0
        offensive_alliances = 0
        balanced_alliances = 0
        
        for alliance in selector.alliances:
            strategy = self._analyze_alliance_strategy(alliance)
            if strategy == "defensive":
                defensive_alliances += 1
            elif strategy == "offensive":
                offensive_alliances += 1
            else:
                balanced_alliances += 1
        
        # Provide strategic recommendations
        total_alliances = len(selector.alliances)
        message = f"Current Alliance Strategy Analysis:\n\n"
        message += f"🛡️ Defensive Alliances: {defensive_alliances}/{total_alliances}\n"
        message += f"⚔️ Offensive Alliances: {offensive_alliances}/{total_alliances}\n"
        message += f"⚖️ Balanced Alliances: {balanced_alliances}/{total_alliances}\n\n"
        
        # Strategic recommendations
        if defensive_alliances > total_alliances * 0.4:
            message += "⚠️ Too many defensive alliances. Consider more offensive picks.\n"
        elif offensive_alliances > total_alliances * 0.6:
            message += "⚠️ Too many offensive alliances. Consider more defensive picks.\n"
        else:
            message += "✅ Good strategic balance achieved!\n"
        
        message += f"\nRecommendation: Aim for 30% defensive, 50% offensive, 20% balanced."
        
        messagebox.showinfo("Strategy Balance Analysis", message)
    
    def _analyze_alliance_strategy(self, alliance):
        """Analyze the strategic approach of an alliance"""
        if not alliance.captain:
            return "unknown"
        
        # Get team data for analysis
        teams_in_alliance = [alliance.captain]
        if alliance.pick1:
            teams_in_alliance.append(alliance.pick1)
        if alliance.pick2:
            teams_in_alliance.append(alliance.pick2)
        
        defensive_count = 0
        high_auto_count = 0
        high_endgame_count = 0
        
        for team_num in teams_in_alliance:
            team = next((t for t in self.alliance_selector.teams if t.team == team_num), None)
            if team:
                if team.defense:
                    defensive_count += 1
                if team.auto_epa > 40:
                    high_auto_count += 1
                if team.endgame_epa > 30:
                    high_endgame_count += 1
        
        # Classify strategy
        if defensive_count >= 2:
            return "defensive"
        elif high_auto_count >= 2 or high_endgame_count >= 2:
            return "offensive"
        else:
            return "balanced"

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