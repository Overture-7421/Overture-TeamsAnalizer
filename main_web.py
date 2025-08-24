"""
Web-compatible version of the main analyzer without tkinter dependencies
"""
import csv
import json
import math
from collections import Counter, defaultdict
import os
from config_manager import ConfigManager
from csv_converter import CSVFormatConverter


class AnalizadorRobotWeb:
    """Web-compatible version of AnalizadorRobot without tkinter dependencies"""
    
    def __init__(self, default_column_names=None, config_file="columnsConfig.json"):
        """
        Inicializa el analizador para uso web.

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

    def _auto_detect_game_phase_columns(self):
        """
        Auto-detecta columnas por fase del juego basándose en palabras clave en los nombres.
        """
        if not self.sheet_data or not self.sheet_data[0]:
            return
            
        header = self.sheet_data[0]
        
        # Palabras clave para identificar fases del juego
        autonomous_keywords = ['auto', 'autonomous']
        teleop_keywords = ['teleop', 'coral', 'algae', 'barge', 'processor', 'crossed', 'defense', 'defended']
        endgame_keywords = ['endgame', 'end game', 'tipped', 'fell', 'died']
        
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

    def load_csv(self, file_path):
        """
        Carga un archivo CSV, detectando automáticamente el formato y convirtiéndolo si es necesario.
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
                    print("Advertencia: Encabezado del CSV no coincide con el existente. Añadiendo solo filas de datos.")
                    self.sheet_data.extend(csv_rows[1:])
            
            self._update_column_indices()
            self._initialize_selected_columns()
        except FileNotFoundError:
            print(f"Error: Archivo no encontrado en {file_path}")
        except Exception as e:
            print(f"Error al cargar CSV: {e}")

    def load_csv_from_text(self, csv_text):
        """Load CSV data from text content"""
        try:
            import io
            reader = csv.reader(io.StringIO(csv_text))
            csv_rows = [row for row in reader if any(field.strip() for field in row)]

            if not csv_rows:
                print("CSV text is empty or contains no data.")
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

            # Load data
            if not self.sheet_data or (len(self.sheet_data) == 1 and not any(self.sheet_data[0])): 
                self.sheet_data = csv_rows
            else:
                current_header = self.sheet_data[0]
                csv_header = csv_rows[0]
                if current_header == csv_header:
                    self.sheet_data.extend(csv_rows[1:])
                else:
                    self.sheet_data.extend(csv_rows[1:])
            
            self._update_column_indices()
            self._initialize_selected_columns()
            
        except Exception as e:
            print(f"Error loading CSV from text: {e}")

    def get_team_data_grouped(self):
        """Get team data grouped by team number"""
        if len(self.sheet_data) < 2:
            return {}
        
        team_number_idx = self._column_indices.get('Team Number')
        if team_number_idx is None:
            return {}
        
        team_data = defaultdict(list)
        for row in self.sheet_data[1:]:  # Skip header
            if team_number_idx < len(row) and row[team_number_idx].strip():
                team_number = row[team_number_idx].strip()
                team_data[team_number].append(row)
        
        return dict(team_data)

    def _average(self, values):
        """Calculate average of numeric values"""
        if not values:
            return 0.0
        return sum(values) / len(values)

    def _standard_deviation(self, values):
        """Calculate standard deviation of numeric values"""
        if len(values) < 2:
            return 0.0
        avg = self._average(values)
        variance = sum((x - avg) ** 2 for x in values) / len(values)
        return math.sqrt(variance)

    def _generate_stat_key(self, base_name, stat_type):
        """Generate a stat key name"""
        # Simplify the key generation
        base_clean = base_name.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('/', '_')
        return f"{base_clean}_{stat_type}"

    def get_detailed_team_stats(self):
        """Get detailed team statistics"""
        if len(self.sheet_data) < 2:
            return []
        
        team_data_grouped = self.get_team_data_grouped()
        if not team_data_grouped:
            return []
        
        detailed_stats_list = []
        
        for team_number, rows in team_data_grouped.items():
            team_stats = {'team': team_number}
            
            # Calculate basic numeric stats for important columns
            numeric_columns = [
                'Coral L1 (Auto)', 'Coral L2 (Auto)', 'Coral L3 (Auto)', 'Coral L4 (Auto)',
                'Coral L1 (Teleop)', 'Coral L2 (Teleop)', 'Coral L3 (Teleop)', 'Coral L4 (Teleop)',
                'Barge Algae (Auto)', 'Barge Algae (Teleop)', 
                'Processor Algae (Auto)', 'Processor Algae (Teleop)'
            ]
            
            for col_name in numeric_columns:
                col_idx = self._column_indices.get(col_name)
                if col_idx is None:
                    continue
                
                values = []
                for row in rows:
                    if col_idx < len(row):
                        try:
                            values.append(float(row[col_idx]))
                        except (ValueError, TypeError):
                            pass
                
                avg_key = self._generate_stat_key(col_name, 'avg')
                std_key = self._generate_stat_key(col_name, 'std')
                team_stats[avg_key] = self._average(values) if values else 0.0
                team_stats[std_key] = self._standard_deviation(values) if values else 0.0
            
            # Overall stats
            overall_values = []
            for col_name in self._selected_numeric_columns_for_overall:
                col_idx = self._column_indices.get(col_name)
                if col_idx is None:
                    continue
                for row in rows:
                    if col_idx < len(row):
                        try:
                            overall_values.append(float(row[col_idx]))
                        except (ValueError, TypeError):
                            pass
            
            team_stats['overall_avg'] = self._average(overall_values) if overall_values else 0.0
            team_stats['overall_std'] = self._standard_deviation(overall_values) if overall_values else 0.0
            
            detailed_stats_list.append(team_stats)
        
        return detailed_stats_list

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

    def get_robot_valuation_phase_weights(self):
        """Get current robot valuation phase weights"""
        return self.robot_valuation_phase_weights.copy()

    def set_robot_valuation_phase_weights(self, weights):
        """Set robot valuation phase weights"""
        self.robot_valuation_phase_weights = weights.copy()

    def get_autonomous_columns(self):
        """Get autonomous columns"""
        return self._autonomous_columns.copy()

    def get_teleop_columns(self):
        """Get teleop columns"""
        return self._teleop_columns.copy()

    def get_endgame_columns(self):
        """Get endgame columns"""
        return self._endgame_columns.copy()