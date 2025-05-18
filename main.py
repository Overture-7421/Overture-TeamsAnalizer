import csv
import math
from collections import Counter, defaultdict
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
from tkinter import simpledialog
from allianceSelector import AllianceSelector, Team, teams_from_dicts

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
            'Coral L1 Scored', 'Coral L2 Scored', 'Coral L3 Scored', 'Coral L4 Scored'
        ]
        self._selected_numeric_columns_for_overall = [
            col for col in default_overall_columns if col in current_header
        ]
        excluded_from_stats = ["Lead Scouter", "Scouter Name", "Highlights Scouter Name"]
        self._selected_stats_columns = [
            col for col in current_header if col not in excluded_from_stats
        ]
        self._mode_boolean_columns = []  # El usuario elige, por defecto vacío

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
        Procesa datos desde un string (simulando entrada de QR).
        Recibe un String con líneas separadas por tabuladores (\t), lo parsea y
        reemplaza el encabezado actual. (Según la descripción, aunque el código Dart parece añadir los datos)

        NOTA: La descripción dice "reemplaza el encabezado actual", pero el código Dart
        parece usar el encabezado existente o por defecto y añade las filas de datos del QR.
        Implementaré la lógica del código Dart (añadir datos bajo el encabezado actual/default).
        Si el objetivo es reemplazar el encabezado con la primera línea del QR, la lógica debe cambiar.

        Args:
            qr_string_data (str): String con los datos, líneas separadas por '\n',
                                  columnas separadas por '\t'.
        """
        if not qr_string_data.strip():
            print("Datos de QR vacíos.")
            return

        lines = qr_string_data.strip().split('\n')
        qr_rows = [[field.strip() for field in line.split('\t')] for line in lines if line.strip()]

        if not qr_rows:
            print("No se pudieron parsear filas de los datos QR.")
            return

        # Usar el encabezado actualmente definido (o el default si sheet_data está vacío)
        if not self.sheet_data or not self.sheet_data[0]: # Si no hay encabezado
            if self.default_column_names:
                self.sheet_data = [list(self.default_column_names)] # Empezar con el encabezado default
            else:
                # Si no hay default_column_names y no hay encabezado en sheet_data,
                # podríamos asumir que la primera línea de qr_rows ES el encabezado.
                # Por ahora, se requiere que el encabezado esté definido o se use el default.
                print("Error: No hay un encabezado definido para los datos QR y no hay nombres de columna por defecto.")
                # Alternativamente, si la primera fila del QR debe ser el encabezado:
                # self.sheet_data = [qr_rows[0]]
                # self.sheet_data.extend(qr_rows[1:])
                # self._update_column_indices()
                # self._initialize_selected_columns()
                return


        # Añadir las filas de datos del QR. Se asume que qr_rows NO contiene un encabezado.
        # Si qr_rows SÍ contiene un encabezado, se debería omitir qr_rows[0] al extender.
        # Por simplicidad y siguiendo el ejemplo Dart (donde procesa widget.initialData sin tratarlo como header)
        self.sheet_data.extend(qr_rows)
        
        print(f"Datos de QR procesados. Total {len(self.sheet_data)} filas.")
        # No es necesario _update_column_indices ni _initialize_selected_columns aquí si solo añadimos datos
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
            'Was the robot Defended by someone?': 'defended_by_other'
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


# GUI Application
class AnalizadorGUI:
    def __init__(self, root, analizador):
        self.root = root
        self.analizador = analizador
        self.root.title("Alliance Simulator Analyzer")
        self.create_widgets()

    def create_widgets(self):
        # Mejoras visuales y de disposición
        frame = ttk.Frame(self.root, padding=8)
        frame.pack(fill=tk.BOTH, expand=True)

        btn_frame = ttk.Frame(frame)
        btn_frame.pack(side=tk.TOP, fill=tk.X, pady=5)
        ttk.Button(btn_frame, text="Load CSV", command=self.load_csv).pack(side=tk.LEFT, padx=4, pady=2)
        ttk.Button(btn_frame, text="Load QR Data", command=self.load_qr).pack(side=tk.LEFT, padx=4, pady=2)
        ttk.Button(btn_frame, text="Update Header", command=self.update_header).pack(side=tk.LEFT, padx=4, pady=2)
        ttk.Button(btn_frame, text="Configure Columns", command=self.configure_columns).pack(side=tk.LEFT, padx=4, pady=2)
        ttk.Button(btn_frame, text="About", command=self.show_about).pack(side=tk.RIGHT, padx=4, pady=2)

        self.status_var = tk.StringVar()
        status_bar = ttk.Label(frame, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        self.notebook = ttk.Notebook(frame)
        self.notebook.pack(fill=tk.BOTH, expand=True, pady=5)

        # Raw Data Tab
        self.raw_frame = ttk.Frame(self.notebook)
        self.tree_raw = ttk.Treeview(self.raw_frame, show='headings')
        self.tree_raw.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scrollbar_raw = ttk.Scrollbar(self.raw_frame, orient=tk.VERTICAL, command=self.tree_raw.yview)
        self.tree_raw.configure(yscroll=scrollbar_raw.set)
        scrollbar_raw.pack(side=tk.LEFT, fill=tk.Y)
        self.notebook.add(self.raw_frame, text="Raw Data")

        # Team Stats Tab
        self.stats_frame = ttk.Frame(self.notebook)
        self.tree_stats = ttk.Treeview(self.stats_frame, show='headings')
        self.tree_stats.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scrollbar_stats = ttk.Scrollbar(self.stats_frame, orient=tk.VERTICAL, command=self.tree_stats.yview)
        self.tree_stats.configure(yscroll=scrollbar_stats.set)
        scrollbar_stats.pack(side=tk.LEFT, fill=tk.Y)
        self.notebook.add(self.stats_frame, text="Team Stats")

        # Defensive Ranking Tab
        self.def_frame = ttk.Frame(self.notebook)
        self.tree_def = ttk.Treeview(self.def_frame, show='headings')
        self.tree_def.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scrollbar_def = ttk.Scrollbar(self.def_frame, orient=tk.VERTICAL, command=self.tree_def.yview)
        self.tree_def.configure(yscroll=scrollbar_def.set)
        scrollbar_def.pack(side=tk.LEFT, fill=tk.Y)
        self.notebook.add(self.def_frame, text="Defensive Ranking")

        # Alliance Selector Tab
        self.alliance_frame = ttk.Frame(self.notebook)
        self.tree_alliance = ttk.Treeview(self.alliance_frame, show='headings')
        self.tree_alliance.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)
        scrollbar_alliance = ttk.Scrollbar(self.alliance_frame, orient=tk.VERTICAL, command=self.tree_alliance.yview)
        self.tree_alliance.configure(yscroll=scrollbar_alliance.set)
        scrollbar_alliance.pack(side=tk.LEFT, fill=tk.Y)
        self.notebook.add(self.alliance_frame, text="Alliance Selector")

        # For dropdowns in the alliance selector
        self.alliance_selector = None
        self.alliance_pick_vars = []  # List of (pick1_var, pick2_var) for each alliance

        # Mejorar resize de columnas
        for tree in [self.tree_raw, self.tree_stats, self.tree_def, self.tree_alliance]:
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
        headers = self.analizador.get_current_headers()

        # Variables para checkboxes
        var_nums = {h: tk.BooleanVar(value=h in self.analizador._selected_numeric_columns_for_overall) for h in headers}
        var_stats = {h: tk.BooleanVar(value=h in self.analizador._selected_stats_columns) for h in headers}
        var_modes = {h: tk.BooleanVar(value=h in self.analizador._mode_boolean_columns) for h in headers}

        frm = ttk.Frame(cfg)
        frm.pack(padx=10, pady=10)

        ttk.Label(frm, text="Numeric for overall").grid(row=0, column=0, padx=5, pady=5)
        ttk.Label(frm, text="Stats columns").grid(row=0, column=1, padx=5, pady=5)
        ttk.Label(frm, text="Mode boolean").grid(row=0, column=2, padx=5, pady=5)

        # Crear columnas de checkboxes
        for i, h in enumerate(headers):
            ttk.Checkbutton(frm, text=h, variable=var_nums[h]).grid(row=i+1, column=0, sticky='w')
            ttk.Checkbutton(frm, text=h, variable=var_stats[h]).grid(row=i+1, column=1, sticky='w')
            ttk.Checkbutton(frm, text=h, variable=var_modes[h]).grid(row=i+1, column=2, sticky='w')

        def apply_cfg():
            sel_nums  = [h for h in headers if var_nums[h].get()]
            sel_stats = [h for h in headers if var_stats[h].get()]
            sel_modes = [h for h in headers if var_modes[h].get()]
            self.analizador.set_selected_numeric_columns_for_overall(sel_nums)
            self.analizador.set_selected_stats_columns(sel_stats)
            self.analizador.set_mode_boolean_columns(sel_modes)
            cfg.destroy()
            self.refresh_all()

        # Add a title and a close button for better UX
        ttk.Label(frm, text="Select columns for each category:", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, columnspan=3, pady=(0,8))
        ttk.Button(frm, text="Close", command=cfg.destroy).grid(row=len(headers)+2, column=2, pady=10, sticky='e')
        ttk.Button(frm, text="Apply", command=apply_cfg).grid(row=len(headers)+1, column=1, pady=10)
        cfg.wait_window()

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
        # Raw Data
        raw = self.analizador.get_raw_data()
        if raw:
            headers = raw[0]
            data = raw[1:]
            self.refresh_table(self.tree_raw, headers, data)
        # Team Stats
        stats = self.analizador.get_detailed_team_stats()
        if stats:
            # --- Build columns: Team, Overall (avg±std), ...rest ---
            stat_keys = list(stats[0].keys())
            columns = []
            avgstd_map = {}
            skip_keys = set()
            # Always put 'team' first, then 'overall_avg'+'overall_std' as one column
            if 'team' in stat_keys:
                columns.append('team')
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
        self.status_var.set("Ready.")

    def refresh_alliance_selector_tab(self):
        stats = self.analizador.get_detailed_team_stats()
        if not stats:
            self.tree_alliance.delete(*self.tree_alliance.get_children())
            self.tree_alliance["columns"] = ["Alliance #", "Captain", "Pick 1", "Recommendation 1", "Pick 2", "Recommendation 2", "Alliance Score"]
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

        # Only recreate selector if teams changed, otherwise keep picks
        if not hasattr(self, 'alliance_selector') or self.alliance_selector is None or len(self.alliance_selector.teams) != len(teams):
            self.alliance_selector = AllianceSelector(teams)
            self.alliance_pick_vars = []
        selector = self.alliance_selector

        table = selector.get_alliance_table()
        columns = ["Alliance #", "Captain", "Pick 1", "Recommendation 1", "Pick 2", "Recommendation 2", "Alliance Score"]
        self.tree_alliance.delete(*self.tree_alliance.get_children())
        self.tree_alliance["columns"] = columns
        for col in columns:
            self.tree_alliance.heading(col, text=col)
            self.tree_alliance.column(col, width=120, anchor=tk.W)

        self.alliance_pick_vars.clear()
        # Remove any previous comboboxes
        if hasattr(self, '_alliance_selector_combos'):
            for cb in self._alliance_selector_combos:
                try:
                    cb.destroy()
                except Exception:
                    pass
        combo_refs = []

        # For each alliance, create pick dropdowns
        for idx, row in enumerate(table):
            pick1_var = tk.StringVar(value=str(row["Pick 1"]) if row["Pick 1"] else "")
            pick2_var = tk.StringVar(value=str(row["Pick 2"]) if row["Pick 2"] else "")

            # Pick 1 options: allow stealing captains with worse rank
            pick1_options = [("", "Select team")]
            available_pick1 = selector.get_available_teams(selector.alliances[idx].captainRank, 'pick1')
            # Remove already picked teams for pick1
            already_picked = selector.get_selected_picks()
            available_pick1 = [t for t in available_pick1 if str(t.team) not in [str(p) for p in already_picked if p is not None]]
            if row["Pick 1"] and not any(str(t.team) == str(row["Pick 1"]) for t in available_pick1):
                tval = next((t for t in selector.teams if str(t.team) == str(row["Pick 1"])), None)
                if tval:
                    pick1_options.append((str(tval.team), f"{tval.team} (Score: {tval.score:.1f})"))
            for t in available_pick1:
                pick1_options.append((str(t.team), f"{t.team} (Score: {t.score:.1f})"))

            # Pick 2 options: captains not allowed, and remove already picked
            pick2_options = [("", "Select team")]
            available_pick2 = selector.get_available_teams(selector.alliances[idx].captainRank, 'pick2')
            already_picked2 = selector.get_selected_picks()
            available_pick2 = [t for t in available_pick2 if str(t.team) not in [str(p) for p in already_picked2 if p is not None]]
            if row["Pick 2"] and not any(str(t.team) == str(row["Pick 2"]) for t in available_pick2):
                tval = next((t for t in selector.teams if str(t.team) == str(row["Pick 2"])), None)
                if tval:
                    pick2_options.append((str(tval.team), f"{tval.team} (Score: {tval.score:.1f})"))
            for t in available_pick2:
                pick2_options.append((str(t.team), f"{t.team} (Score: {t.score:.1f})"))

            self.alliance_pick_vars.append((pick1_var, pick2_var, pick1_options, pick2_options))

            values = [
                row["Alliance #"],
                row["Captain"],
                "",  # Pick 1 (widget)
                row["Recommendation 1"],
                "",  # Pick 2 (widget)
                row["Recommendation 2"],
                row["Alliance Score"]
            ]
            item_id = self.tree_alliance.insert("", tk.END, values=values)
            self.tree_alliance.set(item_id, "Pick 1", "")
            self.tree_alliance.set(item_id, "Pick 2", "")
            self.tree_alliance.update_idletasks()
            bbox1 = self.tree_alliance.bbox(item_id, "Pick 1")
            bbox2 = self.tree_alliance.bbox(item_id, "Pick 2")
            if bbox1:
                pick1_combo = ttk.Combobox(self.tree_alliance, textvariable=pick1_var, values=[v[1] for v in pick1_options], state="readonly")
                # Set to current value or default
                if pick1_var.get():
                    for v in pick1_options:
                        if v[0] == pick1_var.get():
                            pick1_combo.set(v[1])
                            break
                    else:
                        pick1_combo.set(pick1_options[0][1])
                else:
                    pick1_combo.set(pick1_options[0][1])
                pick1_combo.bind("<<ComboboxSelected>>", lambda e, idx=idx, var=pick1_var: self.on_alliance_pick_html_logic(idx, 'pick1', var))
                pick1_combo.place(in_=self.tree_alliance, x=bbox1[0], y=bbox1[1], width=bbox1[2], height=bbox1[3])
                combo_refs.append(pick1_combo)
            if bbox2:
                pick2_combo = ttk.Combobox(self.tree_alliance, textvariable=pick2_var, values=[v[1] for v in pick2_options], state="readonly")
                if pick2_var.get():
                    for v in pick2_options:
                        if v[0] == pick2_var.get():
                            pick2_combo.set(v[1])
                            break
                    else:
                        pick2_combo.set(pick2_options[0][1])
                else:
                    pick2_combo.set(pick2_options[0][1])
                pick2_combo.bind("<<ComboboxSelected>>", lambda e, idx=idx, var=pick2_var: self.on_alliance_pick_html_logic(idx, 'pick2', var))
                pick2_combo.place(in_=self.tree_alliance, x=bbox2[0], y=bbox2[1], width=bbox2[2], height=bbox2[3])
                combo_refs.append(pick2_combo)
        self._alliance_selector_combos = combo_refs

    def on_alliance_pick_html_logic(self, alliance_idx, pick_type, var):
        selector = self.alliance_selector
        pick_vars = self.alliance_pick_vars[alliance_idx]
        options = pick_vars[2] if pick_type == 'pick1' else pick_vars[3]
        selected_label = var.get()
        selected_team = ""
        for val, label in options:
            if label == selected_label:
                selected_team = val
                break

        if not selected_team:
            setattr(selector.alliances[alliance_idx], pick_type, None)
            selector.update_alliance_captains()
            selector.update_recommendations()
            self.refresh_alliance_selector_tab()
            return

        team_number = int(selected_team)
        # For pick2, captains are not allowed
        if pick_type == 'pick2':
            captains = [a.captain for a in selector.alliances if a.captain]
            if team_number in captains:
                messagebox.showerror("Alliance Selector", "You cannot pick an alliance captain for the second pick.")
                setattr(selector.alliances[alliance_idx], pick_type, None)
                selector.update_alliance_captains()
                selector.update_recommendations()
                self.refresh_alliance_selector_tab()
                return
        # Team already picked?
        selected_picks = selector.get_selected_picks()
        if team_number in selected_picks:
            messagebox.showerror("Alliance Selector", f"Team {team_number} is already selected.")
            setattr(selector.alliances[alliance_idx], pick_type, None)
            selector.update_alliance_captains()
            selector.update_recommendations()
            self.refresh_alliance_selector_tab()
            return

        setattr(selector.alliances[alliance_idx], pick_type, team_number)
        selector.update_alliance_captains()
        selector.update_recommendations()
        self.refresh_alliance_selector_tab()

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

# Replace CLI example with GUI launch
if __name__ == "__main__":
    root = tk.Tk()
    analizador = AnalizadorRobot()
    app = AnalizadorGUI(root, analizador)
    root.mainloop()