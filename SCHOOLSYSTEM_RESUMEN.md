# 🏆 SchoolSystem - Honor Roll Scoring System

## 🎯 CARACTERÍSTICAS PRINCIPALES

### **1. Cálculo del Honor Roll Score**
```
HonorRollScore = (MatchPerformanceScore × 0.50) + (PitScoutingScore × 0.30) + (DuringEventScore × 0.20)
```

#### **Match Performance Score (50% del total)**
- **Autonomous Score**: 20% (interno)
- **Teleop Score**: 60% (interno) 
- **Endgame Score**: 20% (interno)

#### **Pit Scouting Score (30% del total)**
- **Electrical Score**: 33.33% (10/30)
- **Mechanical Score**: 25.00% (7.5/30)
- **Driver Station Layout**: 16.67% (5/30)
- **Tools Score**: 16.67% (5/30)
- **Spare Parts Score**: 8.33% (2.5/30)

#### **During Event Score (20% del total)**
- **Team Organization**: 50%
- **Collaboration**: 50%

### **2. Sistema de Competencias**
#### **Competencias (c)** - Multiplicador ×6
- Team Communication
- Driving Skills
- Reliability
- No Deaths
- Pasar Inspección Primera
- Human Player
- Necessary Drivers Fix

#### **Subcompetencias (sc)** - Multiplicador ×3
- Working Under Pressure
- Commitment
- Win Most Games
- Never Ask Pit Admin
- Knows the Rules

#### **Behavior Reports (rp)** - Penalizaciones
- **Low Conduct**: +2 puntos (llegar tarde, pedir herramientas)
- **Very Low Conduct**: +5 puntos (fallar en match, no mostrar GP)

### **3. Sistema de Calificación y Descalificación**

#### **Reglas de Descalificación**
1. **Performance DQ**: c < 2 OR sc < 1
2. **Score DQ**: Honor Roll Score < 70

#### **Curva de Calificación**
```
CurvedScore = (team_HonorRollScore / top_score) × 100
```

#### **Puntos Finales**
```
FinalPoints = round(CurvedScore) + (c × 6) + (sc × 3) + (rp × 0)
```

---

## 🚀 INTEGRACIÓN CON ALLIANCE SIMULATOR

### **Nueva Pestaña "Honor Roll System"**
- ✅ **Interfaz completa** integrada en la GUI principal
- ✅ **Botón SchoolSystem** en la barra de herramientas
- ✅ **Gestión de equipos** con auto-población desde datos existentes
- ✅ **Editor detallado** para scores y competencias de cada equipo
- ✅ **Tabla de rankings** en tiempo real
- ✅ **Exportación a CSV** con estadísticas de resumen

### **Funcionalidades de la GUI**
1. **Auto-populate from Team Data**: Importa equipos automáticamente
2. **Manual Team Entry**: Agregar equipos manualmente
3. **Edit Team Scores**: Editor completo de scores y competencias
4. **Export Honor Roll**: Exportar resultados a CSV con resumen

### **Ventana de Configuración**
- **Team Management**: Agregar/remover equipos
- **Quick Configuration**: Ajustar multiplicadores y umbrales
- **Results Preview**: Vista previa de rankings y descalificados

---

## 🔮 SISTEMA FORSHADOWING (SEPARADO)

### **Match Forshadow**
```python
ForshadowingSystem.match_forshadow(rivals_performance_score)
```
- Predice resultados de matches basado en performance rival
- Retorna probabilidad de victoria y nivel de confianza

### **Ranking Forshadow**
```python
ForshadowingSystem.ranking_forshadow(
    alliance_performance_score,
    alliance_ranking_points,
    alliance_selector_output,
    sidenote_pt1, sidenote_pt2
)
```
- Predice ranking del evento basado en múltiples factores
- Incluye notas cualitativas y factores de alliance selector

---

## 📋 EJEMPLO DE RESULTADOS

```
🏆 HONOR ROLL RANKING FINAL:
Rank   Team     Final Pts  Honor Roll   Curved     Match    Pit      Event    C/SC/RP  Status
1      9012     140        83.9         97.7       86.0     82.9     80.0     5/4/0    Qualified
2      1234     133        85.9         100.0      86.0     84.6     87.5     4/3/0    Qualified
3      5678     118        80.9         94.2       79.0     81.2     85.0     3/2/2    Qualified

❌ EQUIPOS DESCALIFICADOS:
Team 3456: Insufficient competencies: 1 < 2
```

---

## 🎮 CÓMO USAR

### **1. Ejecutar Alliance Simulator**
```bash
python main.py
```

### **2. Acceder al SchoolSystem**
- Hacer clic en el botón **"SchoolSystem"** en la barra de herramientas
- O navegar a la pestaña **"Honor Roll System"**

### **3. Configurar Equipos**
1. **Auto-populate**: Importar equipos desde Raw Data
2. **Manual Entry**: Agregar equipos individualmente
3. **Edit Scores**: Configurar scores detallados y competencias

### **4. Ver Resultados**
- La tabla se actualiza automáticamente
- Rankings con curva de calificación aplicada
- Equipos descalificados mostrados con razones

### **5. Exportar Resultados**
- CSV con rankings completos
- Archivo de resumen con estadísticas
- Configuración del sistema incluida

---

## 📁 ARCHIVOS CREADOS

1. **`school_system.py`**: Módulo principal del SchoolSystem
2. **`test_school_system.py`**: Script de prueba completa
3. **Integración en `main.py`**: GUI completa integrada

---

## 🔧 CARACTERÍSTICAS TÉCNICAS

### **Arquitectura Modular**
- ✅ Clase `TeamScoring` principal
- ✅ Dataclasses para organización de datos
- ✅ Enums para tipos de reportes
- ✅ Sistema de configuración flexible

### **Validación de Datos**
- ✅ Scores normalizados a escala 0-100
- ✅ Validación de umbrales configurables
- ✅ Manejo de errores robusto

### **Exportación y Reportes**
- ✅ CSV detallado con todos los scores
- ✅ Archivo de resumen con estadísticas
- ✅ Configuración del sistema documentada

---

## 🎉 RESULTADO FINAL

**El SchoolSystem está 100% implementado y completamente integrado con el Alliance Simulator!**

### ✅ **Todas las Especificaciones Cumplidas:**
- ✅ Honor Roll Score con fórmulas matemáticas exactas
- ✅ Sistema de competencias (c/sc/rp) completo
- ✅ Reglas de descalificación implementadas
- ✅ Curva de calificación funcional
- ✅ Cálculo de puntos finales correcto
- ✅ Sistema Forshadowing separado
- ✅ GUI intuitiva y completa
- ✅ Exportación de resultados
- ✅ Configuración flexible

### 🚀 **Listo para Producción:**
El sistema puede manejar múltiples equipos, calcular scores complejos, aplicar reglas de descalificación, y generar rankings finales con curva de calificación, todo desde una interfaz gráfica integrada en el Alliance Simulator existente.

**¡Tu sistema de Honor Roll está completamente operativo!** 🏆