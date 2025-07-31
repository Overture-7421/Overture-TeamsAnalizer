# Alliance Simulator - Sistema Completo de Análisis de Equipos de Robótica

## 📋 Descripción General

Alliance Simulator es una aplicación integral para el análisis de datos de competencias de robótica. Permite cargar, procesar y analizar datos de equipos, calcular estadísticas detalladas, crear rankings defensivos, simular alianzas y gestionar un sistema completo de Honor Roll con puntuaciones "académicas".

## 🚀 Características Principales

### 1. **Gestión de Datos**
- ✅ Carga de datos desde archivos CSV
- ✅ Escaneo de códigos QR en tiempo real con cámara
- ✅ Entrada manual de datos QR
- ✅ Edición interactiva de datos crudos
- ✅ Validación automática de datos

### 2. **Análisis Estadístico Avanzado**
- ✅ Estadísticas detalladas por equipo (promedio ± desviación estándar)
- ✅ Cálculo de RobotValuation con pesos configurables por fases (Q1, Q2, Q3)
- ✅ Ranking defensivo especializado
- ✅ Análisis de rendimiento por partida
- ✅ Modos estadísticos para columnas booleanas

### 3. **Sistema de Honor Roll (SchoolSystem)**
- ✅ Puntuación académica integral con múltiples componentes
- ✅ Cálculo de Honor Roll Score con fórmulas matemáticas complejas
- ✅ Sistema de disqualificaciones automáticas
- ✅ Predicción "Forshadowing" de rendimiento futuro
- ✅ Exportación de reportes académicos

### 4. **Simulador de Alianzas**
- ✅ Selección inteligente de alianzas basada en estadísticas
- ✅ Algoritmos de optimización para formación de equipos
- ✅ Análisis de compatibilidad entre equipos
- ✅ Simulación de escenarios de competencia

### 5. **Configuración Avanzada**
- ✅ Importar/Exportar configuraciones de columnas en formato JSON
- ✅ Configuración personalizable de pesos para RobotValuation
- ✅ Selección intuitiva de columnas para diferentes análisis
- ✅ Respaldo y restauración de configuraciones

### 6. **Interfaz de Usuario**
- ✅ Interfaz gráfica intuitiva con múltiples pestañas
- ✅ Tablas interactivas con capacidades de edición
- ✅ Visualizaciones gráficas de rendimiento
- ✅ Sistema de notificaciones y validaciones

## 🛠️ Instalación y Configuración

### Requisitos del Sistema
- Python 3.7+
- Windows 10/11 (optimizado para PowerShell)
- Cámara web (para funcionalidad QR)

### Dependencias Requeridas
```powershell
pip install tkinter matplotlib numpy pandas opencv-python pyzbar
```

### Instalación Adicional para QR Scanner
En algunos sistemas, puede ser necesario instalar ZBar por separado:
```powershell
# Windows
pip install pyzbar[scripts]
```

### Estructura de Archivos
```
AllianceSimulator/
├── main.py                     # Aplicación principal
├── qr_scanner.py              # Módulo de escaneo QR
├── school_system.py           # Sistema de Honor Roll
├── allianceSelector.py        # Selector de alianzas
├── test_data.csv              # Datos de prueba
├── sample_column_config.json  # Configuración de ejemplo
├── test_json_config.py        # Script de test
└── README.md                  # Este archivo
```

## 📊 Guía de Uso Completa

### 1. **Inicio Rápido**

#### Cargar Datos de Prueba
1. Ejecuta la aplicación: `python main.py`
2. Haz clic en **"Load CSV"**
3. Selecciona el archivo `test_data.csv`
4. Los datos se cargarán automáticamente en la pestaña "Raw Data"

#### Configurar Columnas
1. Haz clic en **"Configure Columns"**
2. Selecciona las columnas apropiadas para cada categoría:
   - **Numeric for overall**: Columnas que afectan el puntaje general
   - **Stats columns**: Columnas que aparecen en estadísticas
   - **Mode boolean**: Columnas booleanas para calcular modos

### 2. **Funcionalidades Detalladas**

#### A. **Gestión de Datos**

##### Carga de CSV
- **Función**: Importa datos desde archivos CSV
- **Uso**: Load CSV → Seleccionar archivo
- **Formato**: Primera fila debe contener encabezados
- **Validación**: Automática con mensajes de error descriptivos

##### Escaneo QR en Tiempo Real
- **Función**: Escanea códigos QR con actualización inmediata
- **Uso**: Real-Time QR Scanner → Autorizar cámara
- **Características**:
  - Actualización en tiempo real de la tabla
  - Feedback visual y sonoro
  - Procesamiento de múltiples formatos (CSV, tabulado, texto)
  - Presiona 'q' para salir

##### Entrada Manual QR
- **Función**: Ingreso manual de datos QR
- **Uso**: Paste QR Data → Introducir datos
- **Formatos soportados**: CSV, tabulado, texto plano

##### Edición de Datos Crudos
- **Función**: Modificación interactiva de datos
- **Uso**: 
  - Doble clic en celda para editar
  - "Edit Selected Row" para edición completa
  - "Add New Row" para nuevas entradas
  - "Delete Selected Row" para eliminar
  - "Save Changes" para guardar

#### B. **Análisis Estadístico**

##### Estadísticas por Equipo
- **Ubicación**: Pestaña "Team Stats"
- **Contenido**:
  - Team Number
  - RobotValuation (ponderado por fases)
  - Overall (avg±std)
  - Estadísticas individuales por columna
  - Tasas para columnas booleanas
  - Modos para columnas seleccionadas

##### RobotValuation
- **Concepto**: Evaluación ponderada por fases temporales
- **Configuración**: RobotValuation Weights → Ajustar Q1, Q2, Q3
- **Fórmula**: Q1×peso1 + Q2×peso2 + Q3×peso3 (pesos suman 1.0)
- **Uso**: Evaluar mejora/deterioro a lo largo de la competencia

##### Ranking Defensivo
- **Ubicación**: Pestaña "Defensive Ranking"
- **Criterios**:
  - Tasa de defensa ("Crossed Field/Played Defense?")
  - Puntaje general promedio
  - Tasa de "muerte" del robot
  - Tasa de movimiento/actividad

#### C. **Sistema de Honor Roll (SchoolSystem)**

##### Características del Sistema
- **Puntuación académica**: Fórmulas matemáticas complejas
- **Componentes evaluados**:
  - Performance Score (40%)
  - Consistency Score (25%)
  - Improvement Score (20%)
  - Participation Score (15%)

##### Uso del Honor Roll
1. **Auto-populate from Team Data**: Llena automáticamente desde datos de equipos
2. **Manual Team Entry**: Entrada manual de equipos
3. **Edit Team Scores**: Modificar puntuaciones individuales
4. **Export Honor Roll**: Exportar reportes académicos

##### Fórmulas de Cálculo
```
Honor Roll Score = (
    Performance × 0.4 +
    Consistency × 0.25 +
    Improvement × 0.2 +
    Participation × 0.15
) × 100
```

#### D. **Simulador de Alianzas**

##### Características
- **Selección inteligente**: Basada en estadísticas reales
- **Optimización**: Algoritmos para maximizar potencial de alianza
- **Análisis de compatibilidad**: Evaluación de sinergia entre equipos

##### Uso
1. Ve a la pestaña "Alliance Selector"
2. Los equipos se muestran ordenados por rendimiento
3. Selecciona equipos para formar alianzas
4. El sistema sugiere las mejores combinaciones

#### E. **Gestión de Configuraciones JSON**

##### Exportar Configuración
1. Configure Columns → 📤 Exportar Configuración
2. Selecciona ubicación y nombre del archivo
3. Se guarda toda la configuración actual

##### Importar Configuración
1. Configure Columns → 📥 Importar Configuración
2. Selecciona archivo JSON de configuración
3. Se aplica automáticamente la configuración

##### Formato de Configuración
```json
{
    "version": "1.0",
    "column_configuration": {
        "numeric_for_overall": ["Coral L1 Scored", "Coral L2 Scored", ...],
        "stats_columns": ["Team Number", "Auto Points", ...],
        "mode_boolean_columns": ["Won Match", "Climbed", ...]
    },
    "robot_valuation": {
        "phase_weights": [0.3, 0.4, 0.3],
        "phase_names": ["Q1", "Q2", "Q3"]
    }
}
```

### 3. **Visualizaciones y Reportes**

#### Gráficas de Rendimiento
- **Función**: Plot Team Performance
- **Contenido**: Evolución del rendimiento por equipo a lo largo de partidas
- **Uso**: Identificar tendencias y patrones

#### Exportación de Datos
- **Honor Roll**: Reportes académicos completos
- **Configuraciones**: Respaldo de configuraciones personalizadas
- **Datos procesados**: Estadísticas calculadas

## 🔧 Configuración Avanzada

### Personalización de Columnas

#### Columnas Numéricas para Overall
- **Propósito**: Definen qué columnas afectan el puntaje general
- **Recomendación**: Seleccionar métricas de rendimiento core
- **Ejemplo**: Corales anotados, puntos de autonomous, climb

#### Columnas de Estadísticas
- **Propósito**: Aparecen en la tabla de estadísticas por equipo
- **Recomendación**: Incluir todas las métricas relevantes
- **Exclusiones**: Datos de identificación (nombres de scouts)

#### Columnas de Modo Booleano
- **Propósito**: Calculan el valor más común (moda)
- **Uso**: Variables categóricas o binarias
- **Ejemplo**: Color de alianza, estado de climb, tarjetas

### Pesos de RobotValuation

#### Configuración de Fases
- **Q1 (Primer tercio)**: Peso típico 0.2-0.3
- **Q2 (Segundo tercio)**: Peso típico 0.3-0.4
- **Q3 (Tercer tercio)**: Peso típico 0.3-0.5

#### Estrategias de Ponderación
- **Mejora progresiva**: Más peso en Q3 (0.2, 0.3, 0.5)
- **Consistencia temprana**: Más peso en Q1 (0.4, 0.3, 0.3)
- **Equilibrado**: Pesos iguales (0.33, 0.33, 0.34)

## 📋 Datos de Prueba Incluidos

### Archivo: test_data.csv

#### Estructura de Datos
- **30 registros** de muestra
- **6 equipos** diferentes (1234, 5678, 9012, 3456, 7890, 2468)
- **10 partidas** simuladas
- **21 columnas** de datos

#### Columnas Incluidas
1. **Identificación**: Lead Scouter, Scouter Name, Team Number, Match Number
2. **Autonomous**: Did something?, Did Foul?, Did auton worked?
3. **Scoring**: Coral L1-L4 Scored, Algae Scored in Barge
4. **Gameplay**: Played Algae?, Crossed Field/Played Defense?
5. **Estados**: Tipped/Fell Over?, Died?, Climbed?
6. **Penalizaciones**: Yellow/Red Card
7. **Contexto**: Alliance Color, Was robot Defended?

#### Escenarios de Prueba
- **Equipos de alto rendimiento**: 1234, 5678 (consistentes)
- **Equipos problemáticos**: 9012 (múltiples fallas)
- **Equipos en desarrollo**: 2468 (rendimiento variable)
- **Equipos defensivos**: 7890 (alta tasa de defensa)

## 🚀 Casos de Uso Recomendados

### Para Equipos de Robótica
1. **Análisis post-competencia**: Cargar datos reales y analizar rendimiento
2. **Preparación de alianzas**: Usar el simulador para estrategia de picks
3. **Identificación de fortalezas**: Revisar estadísticas detalladas
4. **Tracking de mejora**: Usar RobotValuation para ver evolución

### Para Organizadores
1. **Ranking oficial**: Usar estadísticas para rankings transparentes
2. **Análisis de meta-juego**: Identificar estrategias dominantes
3. **Balanceo de reglas**: Detectar mecánicas problemáticas

### Para Scouts
1. **Validación de datos**: Verificar consistency en recolección
2. **Training**: Usar datos de prueba para entrenar nuevos scouts
3. **QR workflow**: Implementar flujo de trabajo con códigos QR

## 🔍 Solución de Problemas

### Problemas Comunes

#### Error de Cámara
- **Síntoma**: "Camera not found" o error al abrir QR scanner
- **Solución**: Verificar que ninguna otra aplicación use la cámara
- **Alternativa**: Usar "Paste QR Data" para entrada manual

#### Error de Importación JSON
- **Síntoma**: "Las siguientes columnas no existen"
- **Causa**: Configuración creada con diferentes columnas
- **Solución**: Verificar que los headers coincidan o crear nueva configuración

#### Datos QR no procesados
- **Síntoma**: QR escaneado pero no aparece en tabla
- **Solución**: Verificar formato de datos (debe ser CSV, tabulado o texto)
- **Debug**: Revisar consola para mensajes de error

#### Pesos de RobotValuation inválidos
- **Síntoma**: "Weights must sum to 1.0"
- **Solución**: Asegurar que Q1 + Q2 + Q3 = 1.0
- **Ejemplo**: 0.3 + 0.4 + 0.3 = 1.0 ✓

### Logs y Debugging
- **Consola**: Mensajes detallados se imprimen en la consola
- **Status bar**: Información de estado en la parte inferior
- **Validaciones**: Mensajes de error descriptivos en diálogos

## 🔄 Flujo de Trabajo Recomendado

### Setup Inicial
1. **Cargar datos**: CSV o QR scanner
2. **Configurar columnas**: Seleccionar apropiadas para análisis
3. **Ajustar pesos**: Configurar RobotValuation según estrategia
4. **Exportar configuración**: Guardar setup para reutilización

### Análisis de Competencia
1. **Raw Data**: Verificar calidad de datos
2. **Team Stats**: Revisar rendimiento general
3. **Defensive Ranking**: Identificar equipos defensivos
4. **Alliance Selector**: Planificar estrategia de picks
5. **Honor Roll**: Evaluación académica completa

### Post-Competencia
1. **Export Honor Roll**: Generar reportes finales
2. **Plot Performance**: Analizar tendencias
3. **Backup configuration**: Guardar configuración exitosa

## 📈 Métricas y KPIs

### Estadísticas Clave
- **Overall Average**: Rendimiento promedio general
- **Standard Deviation**: Consistencia del equipo
- **RobotValuation**: Evaluación ponderada por tiempo
- **Defense Rate**: Porcentaje de juego defensivo
- **Honor Roll Score**: Puntuación académica integral

### Interpretación de Resultados
- **Alto Overall + Baja StdDev**: Equipo confiable y consistente
- **Alto RobotValuation**: Equipo que mejora con el tiempo
- **Alta Defense Rate**: Equipo especializado en defensa
- **Alto Honor Roll**: Excelencia académica integral

## 🤝 Contribución y Desarrollo

### Arquitectura del Código
- **main.py**: GUI principal y lógica de interfaz
- **qr_scanner.py**: Funcionalidad de escaneo QR
- **school_system.py**: Sistema de Honor Roll
- **allianceSelector.py**: Algoritmos de selección de alianzas

### Extensibilidad
- **Nuevas métricas**: Agregar en `get_detailed_team_stats()`
- **Nuevos análisis**: Crear nuevas pestañas en GUI
- **Formatos de datos**: Extender parsers en `load_qr_data()`

## 📝 Notas de Versión

### Versión Actual: 2.0
- ✅ Sistema completo de Honor Roll
- ✅ Importar/Exportar configuraciones JSON
- ✅ Escaneo QR en tiempo real
- ✅ Edición interactiva de datos
- ✅ RobotValuation configurable
- ✅ Interfaz mejorada con múltiples pestañas

### Próximas Funcionalidades
- 🔄 Análisis predictivo avanzado
- 🔄 Exportación a múltiples formatos
- 🔄 Dashboard en tiempo real
- 🔄 API para integración externa

## 📞 Soporte

Para problemas, sugerencias o contribuciones:
1. Revisar este README completo
2. Verificar archivos de ejemplo incluidos
3. Consultar mensajes de error en consola
4. Probar con datos de test proporcionados

---

**Alliance Simulator** - Sistema integral para análisis de competencias de robótica con capacidades avanzadas de estadística, simulación de alianzas y evaluación académica.
