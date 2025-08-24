# 🧪 Guía de Datos de Test - Alliance Simulator

## 📊 Datos de Test Incluidos

### Archivo Principal: `test_data.csv`
- **30 registros** de datos simulados de competencia
- **6 equipos** diferentes con características distintas
- **10 partidas** distribuidas a lo largo de una competencia
- **21 columnas** de datos representando una competencia real

## 🏁 Inicio Rápido (5 minutos)

### 1. **Ejecutar Test Básico**
```powershell
python quick_test.py
```
Este comando verifica que todo funciona y muestra estadísticas básicas.

### 2. **Abrir Aplicación Completa**
```powershell
python main.py
```

### 3. **Cargar Datos de Test**
1. Clic en **"Load CSV"**
2. Seleccionar `test_data.csv`
3. ✅ Verás 30 filas en la pestaña "Raw Data"

### 4. **Aplicar Configuración Optimizada**
1. Clic en **"Configure Columns"** 
2. Clic en **"📥 Importar Configuración"**
3. Seleccionar `test_data_config.json`
4. Clic en **"Apply"**

### 5. **Explorar Resultados**
- **Team Stats**: Ver estadísticas calculadas automáticamente
- **Defensive Ranking**: Equipos ordenados por capacidad defensiva
- **Alliance Selector**: Simulación de alianzas optimizadas

## 🤖 Equipos de Test - Perfiles

### Equipo 1234 - "Los Consistentes" ⭐
- **Perfil**: Alto rendimiento, muy consistentes
- **Partidas**: 6 matches registrados
- **Fortalezas**: Scoring de corales, autonomous confiable
- **Overall promedio**: ~3.7 puntos
- **Uso recomendado**: Captain picks, alianzas fuertes

### Equipo 5678 - "Los Versátiles" 🔄
- **Perfil**: Rendimiento sólido, capacidad defensiva
- **Partidas**: 6 matches registrados  
- **Fortalezas**: Defensa + scoring balanceado
- **Características**: Juego defensivo ocasional
- **Uso recomendado**: Picks estratégicos, roles flexibles

### Equipo 9012 - "Los Problemáticos" ⚠️
- **Perfil**: Rendimiento inconsistente, problemas técnicos
- **Partidas**: 6 matches registrados
- **Debilidades**: Fallas frecuentes, penalizaciones
- **Características**: Tipped/died, tarjetas amarillas/rojas
- **Uso recomendado**: Análisis de problemas, evitar en playoffs

### Equipo 3456 - "Los Emergentes" 📈
- **Perfil**: Mejora progresiva a lo largo de la competencia
- **Partidas**: 4 matches registrados
- **Fortalezas**: Curva de aprendizaje positiva
- **RobotValuation**: Debería mostrar mejora Q1→Q3
- **Uso recomendado**: Dark horses, potencial oculto

### Equipo 7890 - "Los Defensores" 🛡️
- **Perfil**: Especialistas en defensa
- **Partidas**: 4 matches registrados
- **Fortalezas**: Alta tasa de "Crossed Field/Played Defense"
- **Estrategia**: Foco en disruption del oponente
- **Uso recomendado**: Alianzas defensivas, counter-strategies

### Equipo 2468 - "Los Variables" 📊
- **Perfil**: Rendimiento altamente variable
- **Partidas**: 4 matches registrados
- **Características**: Mix de excelente y pobre rendimiento
- **Estadísticas**: Alta desviación estándar
- **Uso recomendado**: Análisis de risk/reward

## 📈 Escenarios de Análisis Sugeridos

### Escenario 1: "Capitanes de Alianza"
**Objetivo**: Identificar los mejores capitanes
1. Revisar **Team Stats** ordenado por Overall
2. Verificar **RobotValuation** para consistencia
3. Resultado esperado: 1234 y 5678 como top picks

### Escenario 2: "Estrategia Defensiva"
**Objetivo**: Formar alianza anti-meta
1. Revisar **Defensive Ranking**
2. Identificar equipos con alta defense rate
3. Resultado esperado: 7890 y 5678 como specialists

### Escenario 3: "Análisis de Riesgo"
**Objetivo**: Evaluar confiabilidad vs potencial
1. Comparar **Overall avg** vs **Standard deviation**
2. Analizar tasas de "Died?" y "Tipped/Fell Over?"
3. Resultado esperado: 9012 como alto riesgo, 1234 como bajo riesgo

### Escenario 4: "Mejora Temporal"
**Objetivo**: Encontrar equipos que mejoran con el tiempo
1. Configurar **RobotValuation** con peso alto en Q3 (ej: 0.2, 0.3, 0.5)
2. Comparar RobotValuation vs Overall promedio
3. Resultado esperado: 3456 debería rankear mejor en RobotValuation

### Escenario 5: "Meta-Game Analysis"
**Objetivo**: Identificar estrategias dominantes
1. Analizar **mode** de columnas booleanas
2. Ver correlación entre "Climbed?" y overall score
3. Revisar impact de "Algae vs Coral" strategies

## 🔧 Configuraciones Recomendadas

### Para Análisis de Scoring
```json
"numeric_for_overall": [
    "Coral L1 Scored", "Coral L2 Scored", 
    "Coral L3 Scored", "Coral L4 Scored",
    "Algae Scored in Barge"
]
```

### Para Análisis de Autonomous
```json
"numeric_for_overall": [
    "Did something?", "Did auton worked?"
],
"mode_boolean_columns": [
    "Did something?", "Did auton worked?"
]
```

### Para Análisis de Endgame
```json
"numeric_for_overall": ["Climbed?"],
"mode_boolean_columns": ["Climbed?"]
```

## 🎯 Ejercicios Prácticos

### Ejercicio 1: "Optimización de Alianza"
1. Formar la mejor alianza de 3 equipos
2. Maximizar Overall promedio
3. Minimizar Standard deviation combinada
4. **Respuesta esperada**: 1234 + 5678 + 3456

### Ejercicio 2: "Counter-Strategy"
1. Identificar la alianza más defensiva
2. Formar contra-alianza para scoring puro
3. **Respuesta esperada**: Anti: 7890+5678, Counter: 1234+3456

### Ejercicio 3: "Gallito de Oro Discovery"
1. Encontrar el equipo con mayor potencial oculto
2. Usar RobotValuation con peso temporal
3. **Respuesta esperada**: 3456 como Gallito de Oro

### Ejercicio 4: "Risk Assessment"
1. Calcular "reliability score" personalizado
2. Combinar Overall + (1/StdDev) + (1-FailureRate)
3. Rankear equipos por confiabilidad

## 🔍 Validación de Resultados

### Estadísticas Esperadas (aproximadas)
- **Equipo 1234**: Overall ~3.7, RobotVal ~3.8, StdDev bajo
- **Equipo 5678**: Overall ~3.2, Defense rate >0, Climb rate >0
- **Equipo 9012**: Overall <2.0, Died rate >0, Penalty rate >0
- **Equipo 3456**: RobotVal > Overall (mejora temporal)
- **Equipo 7890**: Defense rate más alto del grupo
- **Equipo 2468**: StdDev más alto del grupo

### Validar Honor Roll System
1. Auto-populate desde team data
2. Verificar que los scores reflejen rendimiento
3. Comprobar que 1234 > 5678 > 3456 > 7890 > 2468 > 9012

## 💡 Tips de Análisis

### Interpretación de Datos
- **Overall alta + StdDev baja** = Equipo confiable (1234)
- **Defense rate alta** = Specialist defensivo (7890)  
- **RobotVal > Overall** = Mejora temporal (3456)
- **Penalty rate alta** = Equipo riesgoso (9012)

### Configuraciones de RobotValuation
- **Mejora progresiva**: [0.2, 0.3, 0.5] (valora Q3)
- **Inicio fuerte**: [0.5, 0.3, 0.2] (valora Q1)
- **Consistencia**: [0.33, 0.33, 0.34] (igual peso)

### Columns Selection Strategy  
- **Numeric for overall**: Solo scoring metrics principales
- **Stats columns**: Todo excepto scouter names
- **Mode boolean**: Preguntas sí/no relevantes

## 🚀 Siguientes Pasos

1. **Dominar datos de test** con estos ejercicios
2. **Crear configuraciones** personalizadas
3. **Experimentar con QR scanner** usando datos reales
4. **Implementar Honor Roll** para evaluación académica
5. **Exportar resultados** para compartir análisis

---

¡Estos datos de test te permiten explorar todas las funcionalidades del Alliance Simulator sin necesidad de una competencia real! 🎉
