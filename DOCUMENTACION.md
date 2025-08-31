# 📚 Documentación Técnica - Overture Teams Analyzer

## 📋 Tabla de Contenidos

### PARTE I: GUÍA DE USUARIO
- [Interfaz Principal](#-interfaz-principal)
- [Carga de Datos](#-carga-de-datos)
- [Escaneo QR](#-escaneo-qr)
- [Análisis de Equipos](#-análisis-de-equipos)
- [Sistema Foreshadowing](#-sistema-foreshadowing)
- [Alliance Selector](#-alliance-selector)
- [Gestión de Datos](#-gestión-de-datos)

### PARTE II: DOCUMENTACIÓN TÉCNICA
- [Arquitectura del Sistema](#-arquitectura-del-sistema)
- [Módulos Principales](#-módulos-principales)
- [Análisis del Código](#-análisis-del-código)
- [Base de Datos y Estructuras](#-base-de-datos-y-estructuras)
- [Algoritmos Implementados](#-algoritmos-implementados)
- [APIs y Interfaces](#-apis-y-interfaces)

---

# PARTE I: GUÍA DE USUARIO

## 🖥️ Interfaz Principal

Al ejecutar `python main.py`, aparece la ventana principal dividida en varias secciones:

### Barra de Herramientas Superior
```
[Load CSV] [Real-Time QR Scanner] [Camera Settings] [Paste QR Data] 
[System Configuration] [Plot Team Performance] [Foreshadowing] [About]
```

**Descripción de Botones:**
- **Load CSV**: Carga archivos de datos de scouting
- **Real-Time QR Scanner**: Inicia escaneo continuo con cámara
- **Camera Settings**: Configura parámetros de cámara
- **Paste QR Data**: Permite pegar datos QR manualmente
- **System Configuration**: Configuraciones avanzadas del sistema
- **Plot Team Performance**: Genera gráficos de rendimiento
- **Foreshadowing**: Sistema de predicción de matches
- **About**: Información del software

### Pestañas Principales
1. **Raw Data**: Datos sin procesar importados
2. **Team Stats**: Estadísticas calculadas por equipo
3. **Honor Roll**: Sistema de calificación académica
4. **Alliance Selector**: Herramienta de selección de alianzas

### Barra de Estado
Muestra información en tiempo real sobre operaciones del sistema.

## 📊 Carga de Datos

### Formatos Soportados

**CSV Estándar FRC**
```csv
Team,Match,Coral L1 (Auto),Coral L2 (Auto),Coral L3 (Auto),Coral L4 (Auto),
Coral L1 (Teleop),Coral L2 (Teleop),Coral L3 (Teleop),Coral L4 (Teleop),
Barge Algae (Auto),Barge Algae (Teleop),Processor Algae (Auto),Processor Algae (Teleop),
Moved (Auto),End Position
```

**Datos QR Escaneados**
El sistema convierte automáticamente códigos QR a formato CSV.

### Proceso de Carga

1. **Click en "Load CSV"**
2. **Seleccionar archivo** en el explorador
3. **Validación automática** de formato
4. **Procesamiento** y cálculo de estadísticas
5. **Visualización** en pestañas correspondientes

### Validaciones Automáticas
- Verificación de headers requeridos
- Validación de tipos de datos
- Detección de duplicados
- Corrección de formatos

## 📱 Escaneo QR

### Configuración de Cámara

**Pasos:**
1. Click en **"Camera Settings"**
2. Seleccionar cámara disponible
3. Ajustar configuraciones:
   - Resolución (640x480, 1280x720, etc.)
   - FPS (frames por segundo)
   - Índice de cámara
   - Formato de color

### Escaneo en Tiempo Real

**Iniciar Escaneo:**
1. Click en **"Real-Time QR Scanner"**
2. Se abre ventana de cámara en vivo
3. Apuntar cámara hacia código QR
4. **Detección automática** y procesamiento
5. Datos se agregan automáticamente al sistema

**Características del Scanner:**
- Detección múltiple simultánea
- Filtrado de duplicados
- Validación de formato QR
- Feedback visual en tiempo real
- Auto-guardado de datos

### Configuraciones Avanzadas

**Parámetros Ajustables:**
```python
# Configuración típica
camera_settings = {
    'resolution': (1280, 720),
    'fps': 30,
    'camera_index': 0,
    'auto_focus': True,
    'brightness': 50,
    'contrast': 50
}
```

## 📈 Análisis de Equipos

### Pestaña Team Stats

**Métricas Calculadas:**

#### Estadísticas Básicas
- **Overall Average**: Rendimiento promedio general
- **Standard Deviation**: Consistencia del equipo
- **Match Count**: Número de matches analizados

#### Estadísticas por Categoría
- **Coral Statistics**: Promedios y desviaciones por nivel (L1-L4)
- **Algae Performance**: Barge y Processor algae
- **Auto Performance**: Rendimiento en período autónomo
- **Teleop Performance**: Rendimiento en período teleoperated
- **Endgame Performance**: Climb y posiciones finales

#### Métricas Avanzadas
- **RobotValuation**: Evaluación ponderada por tiempo
- **Defense Rate**: Porcentaje de juego defensivo
- **Honor Roll Score**: Puntuación académica integral

### Interpretación de Resultados

**Equipos Fuertes:**
```
Overall Avg: > 80
Std Dev: < 15
RobotValuation: > 100
Defense Rate: Variable
```

**Equipos Consistentes:**
```
Overall Avg: > 60
Std Dev: < 10
Coral L1-L4: Promedios estables
Climb Rate: > 70%
```

**Equipos Defensivos:**
```
Defense Rate: > 50%
Overall Avg: Puede ser menor
Crossed Field: > 60%
```

### Gráficos de Rendimiento

**Tipos Disponibles:**
1. **Performance over Time**: Evolución por match
2. **Category Breakdown**: Distribución por categoría
3. **Comparison Charts**: Comparación entre equipos
4. **Statistical Distribution**: Histogramas y distribuciones

## 🔮 Sistema Foreshadowing

El sistema de predicción más avanzado para FRC.

### Interfaz Principal

**Secciones:**
1. **Selección de Equipos**: RED vs BLUE alliances
2. **Botones de Control**: Predicción, estadísticas, Monte Carlo
3. **Área de Resultados**: Breakdown detallado

### Selección de Alianzas

**Proceso:**
1. **RED Alliance**: Seleccionar 3 equipos del dropdown
2. **BLUE Alliance**: Seleccionar 3 equipos del dropdown
3. Equipos disponibles basados en datos cargados

### Tipos de Predicción

#### 1. Predicción Básica
```
Click: "🔮 Predecir Match"
```
**Resultado:**
- Puntuación predicha por alianza
- Probabilidades de victoria
- Ranking Points esperados
- Breakdown básico por categoría

#### 2. Estadísticas Individuales
```
Click: "📊 Estadísticas Individuales"
```
**Muestra tabla con:**
- Coral Auto/Teleop por nivel
- Processor/Net algae esperadas
- Probabilidades de Auto movement
- Puntos esperados de Climb

#### 3. Simulación Monte Carlo
```
Click: "🎲 Simulación Monte Carlo"
```
**Características:**
- 5000 iteraciones de simulación
- Análisis de confianza estadística
- Recomendaciones estratégicas
- Factores clave de victoria

### Interpretación de Resultados

**Ejemplo de Output:**
```
🔮 PREDICCIÓN DE MATCH - REEFSCAPE 2025
========================================

🔴 RED Alliance:  7421 + 3000 + 5000
🔵 BLUE Alliance: 1000 + 2000 + 4000

📊 PUNTUACIÓN PREDICHA:
  🔴 RED:  220.8 puntos
  🔵 BLUE: 105.2 puntos

🎯 PROBABILIDADES:
  🔴 RED gana:  100.0%
  🔵 BLUE gana: 0.0%
  🟡 Empate:    0.0%

🏆 RANKING POINTS PREDICHOS:
  🔴 RED:  4 RP (Win + Auto + Coral)
  🔵 BLUE: 0 RP
```

**Factors to Consider:**
- **Confianza Alta**: Diferencia de probabilidades > 30%
- **Confianza Media**: Diferencia 10-30%
- **Confianza Baja**: Diferencia < 10%

### Algoritmo de Predicción

**Pasos del Algoritmo:**
1. **Extracción de estadísticas** de cada equipo
2. **Distribución proporcional** Auto (30%) / Teleop (70%)
3. **Simulación Monte Carlo** con distribuciones Poisson
4. **Cálculo de puntos** según reglas REEFSCAPE 2025
5. **Análisis de Ranking Points** según criterios FRC

## 🤝 Alliance Selector

### Funcionalidad Principal

**Objetivo:** Optimizar selección de alianzas para maximizar probabilidades de victoria.

### Características

#### Auto-Optimize
```
Click: "Auto-Optimize" 
```
**Proceso:**
1. Analiza todos los equipos disponibles
2. Calcula combinaciones óptimas
3. Asigna capitanes basado en Overall Average
4. Genera recomendaciones por ranking

#### Manual Selection
- Selección manual de equipos
- Predicción en tiempo real
- Comparación de opciones
- Guardado de configuraciones

#### Captain Assignment
**Criterios para Capitanes:**
- Overall Average más alto
- Consistencia (baja std deviation)
- RobotValuation elevado
- Experiencia en competencia

### Algoritmo de Optimización

**Factores Considerados:**
1. **Synergy**: Complementariedad de habilidades
2. **Reliability**: Consistencia histórica
3. **Potential**: Máximo rendimiento posible
4. **Strategy**: Compatibilidad estratégica

## 🛠 Gestión de Datos

### Raw Data Manager

**Funciones Disponibles:**
- **Edit Row**: Modificar registros individuales
- **Delete Row**: Eliminar registros
- **Add Row**: Agregar nuevos registros
- **Save Changes**: Exportar modificaciones

### Características Avanzadas

#### Persistence During QR Scanning
- Las modificaciones manuales se preservan
- QR scanning solo agrega nuevos datos
- No sobrescribe cambios del usuario

#### Data Validation
- Verificación automática de tipos
- Validación de rangos de valores
- Detección de inconsistencias

#### Backup System
- Auto-backup antes de cambios importantes
- Restore points disponibles
- History tracking de modificaciones

---

# PARTE II: DOCUMENTACIÓN TÉCNICA

## 🏗️ Arquitectura del Sistema

### Diseño General

```
┌─────────────────────────────────────────────────────────────┐
│                    OVERTURE TEAMS ANALYZER                  │
├─────────────────────────────────────────────────────────────┤
│  🖥️ PRESENTATION LAYER (GUI)                               │
│  ├── main.py (Tkinter Interface)                           │
│  ├── Tabs Management                                       │
│  └── Event Handling                                        │
├─────────────────────────────────────────────────────────────┤
│  🧠 BUSINESS LOGIC LAYER                                   │
│  ├── foreshadowing.py (Prediction Engine)                  │
│  ├── allianceSelector.py (Optimization)                    │
│  ├── school_system.py (Honor Roll)                         │
│  └── csv_converter.py (Data Processing)                    │
├─────────────────────────────────────────────────────────────┤
│  📊 DATA ACCESS LAYER                                      │
│  ├── AnalizadorRobot (Core Analytics)                      │
│  ├── Data Structures & Models                              │
│  └── File I/O Operations                                   │
├─────────────────────────────────────────────────────────────┤
│  🔧 INFRASTRUCTURE LAYER                                   │
│  ├── qr_scanner.py (Camera Interface)                      │
│  ├── config_manager.py (Settings)                          │
│  └── External Libraries                                    │
└─────────────────────────────────────────────────────────────┘
```

### Patrones de Diseño Implementados

#### 1. Model-View-Controller (MVC)
- **Model**: `AnalizadorRobot`, Data structures
- **View**: Tkinter GUI components
- **Controller**: Event handlers, business logic

#### 2. Strategy Pattern
- Multiple algorithms for team analysis
- Configurable statistical methods
- Plugin-like architecture for extensions

#### 3. Observer Pattern
- Real-time updates during QR scanning
- Event-driven data refreshing
- Status notifications

## 📦 Módulos Principales

### main.py - Core GUI Module

**Clase Principal:** `AnalizadorGUI`

```python
class AnalizadorGUI:
    def __init__(self, root, analizador):
        self.root = root
        self.analizador = analizador  # Core analytics engine
        self.modified_rows = set()    # Track manual edits
        # UI components initialization
```

**Responsabilidades:**
- Interfaz gráfica principal
- Gestión de pestañas y eventos
- Coordinación entre módulos
- Manejo de datos en tiempo real

**Métodos Clave:**
```python
def load_csv(self)                    # Carga archivos CSV
def scan_and_load_qr(self)           # Inicia scanner QR
def refresh_all_tabs(self)           # Actualiza todas las pestañas
def edit_raw_data_row(self)          # Editor de datos
def open_foreshadowing(self)         # Lanza predicción
```

### AnalizadorRobot - Analytics Engine

**Ubicación:** `main.py` (líneas 17-1266)

```python
class AnalizadorRobot:
    def __init__(self, default_column_names=None, config_file="columnsConfig.json"):
        self.sheet_data = []                    # Raw data storage
        self._column_indices = {}               # Column mapping
        self._selected_numeric_columns = []     # Numeric analysis columns
        # Configuration and statistics setup
```

**Capacidades Principales:**

#### Data Processing
```python
def _update_column_indices(self)                # Maps columns to indices
def get_team_data_grouped(self)                 # Groups data by team
def get_detailed_team_stats(self)               # Calculates all statistics
```

#### Statistical Analysis
```python
def _average(self, values)                      # Mean calculation
def _standard_deviation(self, values)           # Std dev calculation
def _robot_valuation(self, rows)                # Advanced scoring
```

#### Performance Metrics
```python
def calculate_team_phase_scores(self, team_number)  # Auto/Teleop/Endgame
def get_team_match_performance(self, team_numbers)  # Match-by-match
def _generate_stat_key(self, col_name, stat_type)   # Stat naming
```

### foreshadowing.py - Prediction System v2.0

**Arquitectura Modular:**

#### Game Configuration
```python
@dataclass
class GameConfig:
    coral_auto_points = {"L1": 3, "L2": 4, "L3": 6, "L4": 7}
    coral_teleop_points = {"L1": 2, "L2": 3, "L3": 4, "L4": 5}
    processor_points = 6
    net_points = 4
    climb_points = {"none": 0, "park": 2, "shallow": 6, "deep": 12}
```

#### Team Performance Model
```python
@dataclass
class TeamPerformance:
    team_number: str
    auto_L1: float = 0.0        # Coral auto per level
    auto_L2: float = 0.0
    auto_L3: float = 0.0
    auto_L4: float = 0.0
    teleop_L1: float = 0.0      # Coral teleop per level
    teleop_L2: float = 0.0
    teleop_L3: float = 0.0
    teleop_L4: float = 0.0
    auto_processor: float = 0.0  # Processor algae auto
    teleop_processor: float = 0.0 # Processor algae teleop
    teleop_net: float = 0.0     # Net algae teleop
    p_leave_auto_zone: float = 0.5  # Auto movement probability
    p_cooperation: float = 0.3   # Cooperation probability
    climb_distribution: Dict[str, float]  # Climb probabilities
```

#### Statistics Extractor
```python
class TeamStatsExtractor:
    def extract_team_performance(self, team_number: str) -> TeamPerformance:
        # Extracts stats from AnalizadorRobot
        # Applies proportional distribution (30% auto, 70% teleop)
        # Calculates probabilities based on historical data
```

#### Match Simulator
```python
class MatchSimulator:
    def simulate_match(self, red_teams, blue_teams, num_simulations=1000):
        # Monte Carlo simulation
        # Poisson distributions for piece scoring
        # Realistic climb sampling
        # Ranking Points calculation
```

### allianceSelector.py - Alliance Optimization

**Core Classes:**

#### Team Model
```python
@dataclass
class Team:
    number: str
    overall_avg: float = 0.0
    overall_std: float = 0.0
    robot_valuation: float = 0.0
    # Additional performance metrics
```

#### Alliance Selector Engine
```python
class AllianceSelector:
    def __init__(self, teams_data):
        self.teams = self._create_teams_from_data(teams_data)
        self.available_teams = set(team.number for team in self.teams)
    
    def auto_optimize_alliances(self, num_alliances=8):
        # Optimization algorithm for alliance selection
        # Captain assignment based on performance
        # Synergy analysis between teams
```

### qr_scanner.py - Camera Interface

**QR Scanner Implementation:**

```python
class QRScannerThread(threading.Thread):
    def __init__(self, callback, camera_index=0):
        self.callback = callback        # Data processing callback
        self.camera_index = camera_index
        self.running = False
        
    def run(self):
        # OpenCV camera initialization
        # Continuous frame capture
        # QR code detection with pyzbar
        # Data validation and callback
```

**Features:**
- Multi-threaded scanning for real-time performance
- Automatic duplicate filtering
- Configurable camera parameters
- Error handling and recovery

### school_system.py - Honor Roll System

**Academic Scoring:**

```python
class TeamScoring:
    def __init__(self):
        self.teams = {}                 # Team academic data
        self.honor_roll_criteria = {}   # Scoring criteria
        
    def calculate_honor_roll_score(self, team_num):
        # Academic performance calculation
        # Multiple criteria weighting
        # Normalization and scaling
```

## 🧮 Análisis del Código

### Estructura de Datos Principal

#### Sheet Data Format
```python
sheet_data = [
    ["Team", "Match", "Coral L1 (Auto)", ..., "End Position"],  # Headers
    ["7421", "Q1", "3", "2", "1", ..., "deep"],                # Data rows
    ["1000", "Q1", "2", "1", "0", ..., "shallow"],
    # ... more data rows
]
```

#### Column Indices Mapping
```python
_column_indices = {
    "Team": 0,
    "Match": 1,
    "Coral L1 (Auto)": 2,
    "Coral L2 (Auto)": 3,
    # ... mapping for all columns
}
```

#### Team Statistics Structure
```python
team_stats = {
    'team': '7421',
    'overall_avg': 92.5,
    'overall_std': 12.3,
    'coral_l1__avg': 2.5,
    'coral_l1__std': 0.8,
    'teleop_processor_algae_avg': 3.2,
    'RobotValuation': 115.6,
    # ... all calculated statistics
}
```

### Algoritmos Clave

#### 1. Statistical Calculations

**Average Calculation:**
```python
def _average(self, values):
    if not values:
        return 0.0
    return sum(values) / len(values)
```

**Standard Deviation:**
```python
def _standard_deviation(self, values):
    if len(values) < 2:
        return 0.0
    avg = self._average(values)
    variance = sum((x - avg) ** 2 for x in values) / (len(values) - 1)
    return math.sqrt(variance)
```

#### 2. Robot Valuation Algorithm

**Multi-phase weighted scoring:**
```python
def _robot_valuation(self, rows):
    total_valuation = 0.0
    weight_sum = 0.0
    
    for i, row in enumerate(rows):
        # Time-based weighting (recent matches more important)
        time_weight = math.log(i + 2)
        
        match_score = 0.0
        
        # Coral scoring with level-based weights
        coral_weights = {'L1': 2, 'L2': 3, 'L3': 4, 'L4': 5}
        for level, weight in coral_weights.items():
            # Auto coral (double points)
            auto_val = self._get_numeric_value(row, f'Coral {level} (Auto)')
            match_score += auto_val * weight * 2
            
            # Teleop coral (standard points)
            teleop_val = self._get_numeric_value(row, f'Coral {level} (Teleop)')
            match_score += teleop_val * weight
        
        # Algae scoring
        processor_auto = self._get_numeric_value(row, 'Processor Algae (Auto)')
        processor_teleop = self._get_numeric_value(row, 'Processor Algae (Teleop)')
        barge_teleop = self._get_numeric_value(row, 'Barge Algae (Teleop)')
        
        match_score += processor_auto * 9    # 6 points * 1.5 auto bonus
        match_score += processor_teleop * 6  # 6 points
        match_score += barge_teleop * 4      # 4 points
        
        # Endgame scoring
        end_position = self._get_string_value(row, 'End Position').lower()
        if 'deep' in end_position:
            match_score += 12
        elif 'shallow' in end_position:
            match_score += 6
        elif 'park' in end_position:
            match_score += 2
        
        # Apply time weighting
        total_valuation += match_score * time_weight
        weight_sum += time_weight
    
    return total_valuation / weight_sum if weight_sum > 0 else 0.0
```

#### 3. Monte Carlo Simulation (Foreshadowing)

**Core simulation loop:**
```python
def simulate_match(self, red_teams, blue_teams, num_simulations=1000):
    red_scores = []
    blue_scores = []
    red_rps = []
    blue_rps = []
    
    for _ in range(num_simulations):
        # Simulate one instance of the match
        red_result = self._simulate_alliance(red_teams)
        blue_result = self._simulate_alliance(blue_teams)
        
        red_scores.append(red_result['total_score'])
        blue_scores.append(blue_result['total_score'])
        
        # Calculate Ranking Points
        red_rp, blue_rp = self._calculate_ranking_points(
            red_result, blue_result, red_teams, blue_teams
        )
        red_rps.append(red_rp)
        blue_rps.append(blue_rp)
    
    # Calculate averages and probabilities
    avg_red_score = sum(red_scores) / num_simulations
    avg_blue_score = sum(blue_scores) / num_simulations
    
    red_wins = sum(1 for r, b in zip(red_scores, blue_scores) if r > b)
    blue_wins = sum(1 for r, b in zip(red_scores, blue_scores) if b > r)
    ties = num_simulations - red_wins - blue_wins
    
    return MatchPrediction(
        red_teams=red_teams,
        blue_teams=blue_teams,
        red_score=avg_red_score,
        blue_score=avg_blue_score,
        red_rp=round(sum(red_rps) / num_simulations),
        blue_rp=round(sum(blue_rps) / num_simulations),
        red_win_probability=red_wins / num_simulations,
        blue_win_probability=blue_wins / num_simulations,
        tie_probability=ties / num_simulations
    )
```

**Alliance simulation with Poisson distributions:**
```python
def _simulate_alliance(self, teams):
    result = {
        'coral_scores': {'L1': 0, 'L2': 0, 'L3': 0, 'L4': 0},
        'auto_coral': {'L1': 0, 'L2': 0, 'L3': 0, 'L4': 0},
        'teleop_coral': {'L1': 0, 'L2': 0, 'L3': 0, 'L4': 0},
        'processor_algae': {'auto': 0, 'teleop': 0},
        'net_algae': 0,
        'climb_scores': [],
        'teams_left_auto_zone': 0,
        'cooperation_achieved': False
    }
    
    for team in teams:
        # Simulate coral using Poisson distribution
        auto_coral = {
            'L1': self._poisson_sample(team.auto_L1),
            'L2': self._poisson_sample(team.auto_L2),
            'L3': self._poisson_sample(team.auto_L3),
            'L4': self._poisson_sample(team.auto_L4)
        }
        
        teleop_coral = {
            'L1': self._poisson_sample(team.teleop_L1),
            'L2': self._poisson_sample(team.teleop_L2),
            'L3': self._poisson_sample(team.teleop_L3),
            'L4': self._poisson_sample(team.teleop_L4)
        }
        
        # Accumulate results
        for level in ['L1', 'L2', 'L3', 'L4']:
            result['auto_coral'][level] += auto_coral[level]
            result['teleop_coral'][level] += teleop_coral[level]
            result['coral_scores'][level] += auto_coral[level] + teleop_coral[level]
        
        # Simulate algae
        result['processor_algae']['auto'] += self._poisson_sample(team.auto_processor)
        result['processor_algae']['teleop'] += self._poisson_sample(team.teleop_processor)
        result['net_algae'] += self._poisson_sample(team.teleop_net)
        
        # Simulate climb
        climb_type = self._sample_climb(team.climb_distribution)
        climb_points = self.config.climb_points[climb_type]
        result['climb_scores'].append((team.team_number, climb_type, climb_points))
        
        # Auto zone
        if random.random() < team.p_leave_auto_zone:
            result['teams_left_auto_zone'] += 1
    
    # Calculate points and cooperation
    result['coral_points'] = self._calculate_coral_points(result)
    result['algae_points'] = self._calculate_algae_points(result)
    result['climb_points'] = sum(score[2] for score in result['climb_scores'])
    
    total_processor = result['processor_algae']['auto'] + result['processor_algae']['teleop']
    result['cooperation_achieved'] = total_processor >= self.config.cooperation_threshold * 2
    
    result['total_score'] = result['coral_points'] + result['algae_points'] + result['climb_points']
    
    return result
```

#### 4. Alliance Optimization Algorithm

**Auto-optimization process:**
```python
def auto_optimize_alliances(self, num_alliances=8):
    # Sort teams by overall performance
    sorted_teams = sorted(self.teams, key=lambda t: t.overall_avg, reverse=True)
    
    alliances = []
    available = set(team.number for team in sorted_teams)
    
    for i in range(num_alliances):
        if len(available) < 3:
            break
            
        # Select captain (highest remaining overall_avg)
        captain = None
        for team in sorted_teams:
            if team.number in available:
                captain = team
                break
        
        if not captain:
            break
            
        available.remove(captain.number)
        
        # Select first pick (best synergy with captain)
        pick1 = self._find_best_synergy(captain, available, sorted_teams)
        if pick1:
            available.remove(pick1.number)
        
        # Select second pick (complements alliance)
        pick2 = self._find_complementary_pick(captain, pick1, available, sorted_teams)
        if pick2:
            available.remove(pick2.number)
        
        alliance = {
            'alliance_number': i + 1,
            'captain': captain,
            'pick1': pick1,
            'pick2': pick2,
            'predicted_score': self._predict_alliance_score(captain, pick1, pick2)
        }
        
        alliances.append(alliance)
    
    return alliances
```

### Data Flow Architecture

#### 1. Data Input Pipeline
```
CSV File → load_csv() → sheet_data → _update_column_indices() → Processing Ready
QR Code → QRScanner → parse_qr_data() → sheet_data → Auto Refresh
Manual → edit_raw_data_row() → sheet_data → modified_rows tracking
```

#### 2. Statistics Calculation Pipeline
```
sheet_data → get_team_data_grouped() → 
            team_data_by_number → 
            get_detailed_team_stats() → 
            Statistical Calculations → 
            team_stats_list → 
            UI Display
```

#### 3. Prediction Pipeline
```
team_stats_list → TeamStatsExtractor → 
                  TeamPerformance models → 
                  MatchSimulator → 
                  Monte Carlo Simulation → 
                  MatchPrediction → 
                  UI Results
```

#### 4. Real-time Update Flow
```
QR Scanner → New Data → refresh_raw_data_only() → 
            Preserve Modified Rows → 
            Update UI → 
            Auto-calculate Stats → 
            Notify User
```

### Error Handling Strategy

#### 1. Data Validation
```python
def _validate_csv_data(self, data):
    errors = []
    
    # Check headers
    required_headers = ['Team', 'Match']
    if not all(header in data[0] for header in required_headers):
        errors.append("Missing required headers")
    
    # Check data types
    for row_idx, row in enumerate(data[1:], 1):
        try:
            team = str(row[0])
            match = str(row[1])
            # Additional validations...
        except (IndexError, ValueError) as e:
            errors.append(f"Row {row_idx}: {e}")
    
    return errors
```

#### 2. Exception Handling
```python
def safe_numeric_operation(self, func, default=0.0):
    try:
        return func()
    except (ValueError, TypeError, ZeroDivisionError):
        return default
    except Exception as e:
        self.log_error(f"Unexpected error: {e}")
        return default
```

#### 3. Recovery Mechanisms
- Automatic data backup before major operations
- Graceful degradation when modules fail
- User notification of non-critical errors
- Retry mechanisms for camera operations

### Performance Optimizations

#### 1. Caching Strategy
```python
class StatisticsCache:
    def __init__(self):
        self._cache = {}
        self._cache_timestamps = {}
    
    def get_stats(self, team_number, data_hash):
        key = (team_number, data_hash)
        if key in self._cache:
            return self._cache[key]
        return None
    
    def set_stats(self, team_number, data_hash, stats):
        key = (team_number, data_hash)
        self._cache[key] = stats
        self._cache_timestamps[key] = time.time()
```

#### 2. Lazy Loading
- Statistics calculated only when needed
- UI components loaded on demand
- Large datasets processed in chunks

#### 3. Efficient Data Structures
- Dictionary mapping for O(1) column lookups
- Set operations for team filtering
- List comprehensions for bulk operations

### Testing Framework

#### 1. Unit Tests
```python
def test_average_calculation():
    analyzer = AnalizadorRobot()
    values = [1, 2, 3, 4, 5]
    assert analyzer._average(values) == 3.0
    assert analyzer._average([]) == 0.0
```

#### 2. Integration Tests
```python
def test_full_pipeline():
    # Load test data
    # Process through full pipeline
    # Verify expected outputs
    # Check performance metrics
```

#### 3. Performance Tests
```python
def test_monte_carlo_performance():
    # Measure simulation time
    # Verify memory usage
    # Check accuracy vs speed tradeoffs
```

### Configuration Management

#### 1. JSON Configuration Files
```json
{
    "columns": {
        "required": ["Team", "Match"],
        "numeric": ["Coral L1 (Auto)", "Coral L2 (Auto)"],
        "boolean": ["Moved (Auto)"],
        "categorical": ["End Position"]
    },
    "analysis": {
        "auto_teleop_ratio": 0.3,
        "monte_carlo_iterations": 1000,
        "confidence_threshold": 0.7
    }
}
```

#### 2. Runtime Configuration
```python
class ConfigManager:
    def __init__(self, config_file="config.json"):
        self.config = self.load_config(config_file)
    
    def get(self, key_path, default=None):
        # Navigate nested configuration
        # Return value or default
    
    def set(self, key_path, value):
        # Update configuration
        # Auto-save changes
```

### Security Considerations

#### 1. Input Validation
- Sanitize all user inputs
- Validate file formats and sizes
- Prevent code injection through data

#### 2. File System Security
- Restrict file access to allowed directories
- Validate file extensions
- Safe handling of temporary files

#### 3. Camera Privacy
- User consent for camera access
- No automatic recording or storage
- Clear indication when camera is active

### Future Extensibility

#### 1. Plugin Architecture
```python
class PluginManager:
    def __init__(self):
        self.plugins = {}
    
    def register_plugin(self, name, plugin_class):
        self.plugins[name] = plugin_class
    
    def execute_plugin(self, name, *args, **kwargs):
        if name in self.plugins:
            return self.plugins[name](*args, **kwargs)
```

#### 2. API Interfaces
- RESTful API for external integrations
- Webhook support for real-time data
- Database connectivity options

#### 3. Modular Design
- Clear separation of concerns
- Well-defined interfaces between modules
- Easy addition of new analysis methods

---

**Desarrollado por Team Overture 7421**  
*Para FIRST Robotics Competition - REEFSCAPE 2025*

*Esta documentación técnica proporciona una visión completa del sistema, desde el uso básico hasta la implementación técnica detallada.*
