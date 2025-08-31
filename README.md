# 🤖 Overture Teams Analyzer

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)
[![FRC](https://img.shields.io/badge/FRC-2025%20REEFSCAPE-orange.svg)](https://www.firstinspires.org/robotics/frc)
[![Team](https://img.shields.io/badge/Team-Overture%207421-purple.svg)](https://github.com/Overture-7421)

Una herramienta avanzada de análisis de equipos para **FIRST Robotics Competition - REEFSCAPE 2025**, desarrollada por **Team Overture 7421**.

## 🌟 Características Principales

### 📊 Análisis Estadístico Avanzado
- **Estadísticas por Equipo**: Promedios, desviaciones estándar y métricas de consistencia
- **Robot Valuation**: Sistema de evaluación ponderada por tiempo y rendimiento
- **Honor Roll System**: Sistema de calificación académica integral
- **Análisis de Categorías**: Breakdown detallado por Coral, Algae y Endgame

### 📱 Escaneo QR en Tiempo Real
- **Scanner Multi-Cámara**: Soporte para múltiples cámaras y configuraciones
- **Detección Automática**: Procesamiento instantáneo de códigos QR
- **Validación de Datos**: Verificación automática de formato y consistencia
- **Integración Seamless**: Datos agregados automáticamente al sistema

### 🔮 Foreshadowing v2.0 - Sistema de Predicción
- **Simulación Monte Carlo**: 5000+ iteraciones para máxima precisión
- **Predicción de Matches**: Análisis probabilístico de resultados
- **Ranking Points**: Cálculo automático de RP según reglas FRC 2025
- **Análisis de Confianza**: Métricas de confiabilidad estadística

### 🤝 Alliance Selector Inteligente
- **Auto-Optimización**: Algoritmo de selección automática de alianzas
- **Asignación de Capitanes**: Basado en rendimiento y consistencia
- **Análisis de Sinergia**: Evaluación de compatibilidad entre equipos
- **Comparación de Opciones**: Herramientas de decisión estratégica

### 🛠 Gestión Avanzada de Datos
- **Editor de Raw Data**: Modificación y eliminación de registros
- **Persistencia Inteligente**: Preserva cambios manuales durante QR scanning
- **Exportación de Datos**: Múltiples formatos de salida
- **Backup Automático**: Sistema de respaldo y recuperación

## 🚀 Instalación Rápida

### Prerrequisitos
- **Python 3.8 o superior**
- **Git** (para clonar el repositorio)
- **Cámara USB** (opcional, para QR scanning)

### Pasos de Instalación

1. **Clonar el repositorio**
```bash
git clone https://github.com/Overture-7421/Overture-TeamsAnalizer.git
cd Overture-TeamsAnalizer
```

2. **Crear entorno virtual (recomendado)**
```bash
python -m venv venv
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

3. **Instalar dependencias**
```bash
pip install -r requirements.txt
```

4. **Ejecutar la aplicación**
```bash
python main.py
```

### Dependencias Principales
- `tkinter` - Interfaz gráfica
- `matplotlib` - Gráficos y visualizaciones
- `opencv-python` - Procesamiento de cámara
- `pyzbar` - Decodificación de códigos QR
- `pandas` - Manipulación de datos
- `numpy` - Cálculos numéricos
- `Pillow` - Procesamiento de imágenes

## 📖 Uso Básico

### 1. Cargar Datos
```
1. Click en "Load CSV"
2. Seleccionar archivo de datos de scouting
3. Los datos se procesan automáticamente
4. Ver resultados en pestañas "Raw Data" y "Team Stats"
```

### 2. Escaneo QR
```
1. Click en "Camera Settings" para configurar cámara
2. Click en "Real-Time QR Scanner"
3. Apuntar cámara hacia códigos QR
4. Datos se agregan automáticamente
```

### 3. Predicción de Matches
```
1. Click en "Foreshadowing"
2. Seleccionar equipos RED y BLUE
3. Click en "🔮 Predecir Match"
4. Ver resultados y probabilidades
```

### 4. Selección de Alianzas
```
1. Ir a pestaña "Alliance Selector"
2. Click en "Auto-Optimize"
3. Ver recomendaciones de alianzas
4. Ajustar manualmente si necesario
```

## 🎯 Características Específicas para REEFSCAPE 2025

### Coral Scoring System
- **4 Niveles de Coral** (L1, L2, L3, L4)
- **Puntuación Diferenciada** Auto vs Teleop
- **Análisis Estadístico** por nivel y período

### Algae Management
- **Processor Algae**: Scoring en zona de procesamiento
- **Barge Algae**: Solo durante Teleop
- **Net Algae**: Scoring en redes
- **Métricas de Eficiencia** por tipo de algae

### Endgame Analysis
- **Climb Analysis**: Deep, Shallow, Park, None
- **Probabilidades de Climb** basadas en datos históricos
- **Puntuación de Endgame** integrada en predicciones

### Autonomous Period
- **Movement Tracking**: Robots que salen de zona Auto
- **Auto Scoring**: Coral y Processor con bonificación
- **Cooperation**: Detección automática de cooperation

## 🔧 Configuración Avanzada

### Configurar Cámara QR
```python
# Camera settings en config_manager.py
camera_settings = {
    'resolution': (1280, 720),
    'fps': 30,
    'camera_index': 0,
    'auto_focus': True
}
```

### Personalizar Columnas de Datos
```json
// columnsConfig.json
{
    "required_columns": ["Team", "Match"],
    "numeric_columns": ["Coral L1 (Auto)", "Coral L2 (Auto)"],
    "analysis_columns": ["custom_metric_1", "custom_metric_2"]
}
```

### Ajustar Algoritmo de Predicción
```python
# En foreshadowing.py
MONTE_CARLO_ITERATIONS = 5000
AUTO_TELEOP_RATIO = 0.3
COOPERATION_THRESHOLD = 6
```

## 📊 Métricas y Análisis

### Estadísticas Calculadas
- **Overall Average**: Rendimiento promedio ponderado
- **Standard Deviation**: Medida de consistencia
- **Robot Valuation**: Puntuación avanzada con peso temporal
- **Defense Rate**: Porcentaje de juego defensivo
- **Climb Rate**: Probabilidad de climb exitoso

### Fórmulas Principales
```
Robot Valuation = Σ(match_score × time_weight) / Σ(time_weight)
Defense Rate = defense_matches / total_matches
Overall Average = weighted_sum_of_scores / total_weights
```

## 🧪 Testing y Validación

### Ejecutar Tests
```bash
# Tests unitarios
python -m pytest tests/

# Test específico de Foreshadowing
python test_foreshadowing_improvements.py

# Test de integración principal
python test_main_integration.py
```

### Datos de Prueba
- `test_data.csv` - Datos básicos de prueba
- `extended_test_data.csv` - Dataset extendido
- `example_phase_config.json` - Configuración de ejemplo

## 🔍 Troubleshooting

### Problemas Comunes

**Cámara no detectada:**
```bash
# Verificar cámaras disponibles
python -c "import cv2; print([i for i in range(10) if cv2.VideoCapture(i).read()[0]])"
```

**Error de importación de módulos:**
```bash
# Reinstalar dependencias
pip uninstall -r requirements.txt -y
pip install -r requirements.txt
```

**Datos QR no se procesan:**
- Verificar formato del código QR
- Comprobar iluminación de la cámara
- Validar configuración en `Camera Settings`

**Predicciones inconsistentes:**
- Verificar que hay suficientes datos por equipo (mínimo 3 matches)
- Comprobar que las columnas numéricas tienen valores válidos
- Revisar configuración en `System Configuration`

### Logs y Debugging

```python
# Habilitar logs detallados
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 🤝 Contribuir

### Guidelines de Contribución
1. **Fork** el repositorio
2. Crear **branch** para feature (`git checkout -b feature/nueva-caracteristica`)
3. **Commit** cambios (`git commit -am 'Agregar nueva característica'`)
4. **Push** al branch (`git push origin feature/nueva-caracteristica`)
5. Crear **Pull Request**

### Estándares de Código
- **PEP 8** para estilo Python
- **Docstrings** para todas las funciones públicas
- **Type hints** donde sea apropiado
- **Tests unitarios** para nuevas features

## 📈 Roadmap y Futuras Mejoras

### v3.0 Planned Features
- [ ] **Machine Learning**: Predicciones con IA
- [ ] **API REST**: Integración con sistemas externos
- [ ] **Multi-Competition**: Soporte para múltiples competencias
- [ ] **Real-time Collaboration**: Colaboración en tiempo real

### Integraciones Planeadas
- **FRC Events API**: Información de eventos
- **Tableau/PowerBI**: Dashboards avanzados
- **Cloud Storage**: Backup automático en la nube

## 📜 Licencia

Este proyecto está licenciado bajo la **MIT License** - ver el archivo [LICENSE](LICENSE) para detalles.

## 👥 Equipo de Desarrollo

**Team Overture 7421**
- 🏆 **FRC Team**: rgba(215, 1, 248, 0.07) Overture
- 🌍 **Ubicación**: México
- 🎯 **Temporada**: 2025 REEFSCAPE
- 🚀 **Misión**: Desarrollar herramientas innovadoras para FRC

### Contacto
- **GitHub**: [@Overture-7421](https://github.com/Overture-7421)
- **Email**: 
- **Website**: [overture7421.org](https://overture7421.org)

## 🙏 Agradecimientos

- **FIRST Robotics Competition** - Por inspirar innovación
- **Python Community** - Por las increíbles librerías
- **Mentores y Students** - Por testing y mejoras continuas

## 📞 Soporte

¿Necesitas ayuda? Aquí te podemos ayudar:

1. **GitHub Issues**: [Reportar bug o solicitar feature](https://github.com/Overture-7421/Overture-TeamsAnalizer/issues)
2. **Documentación**: Ver [DOCUMENTACION.md](DOCUMENTACION.md) para guía detallada
3. **Wiki**: Consultar wiki del proyecto para tutoriales
4. **Discord/Slack**: Unirse a canales de la comunidad FRC

---

**💡 "Innovating through robotics, one algorithm at a time."**

*Desarrollado con ❤️ por Team Overture 7421*

---

## ⭐ Star History

Si este proyecto te ha sido útil, ¡no olvides darle una estrella! ⭐

[![Star History Chart](https://api.star-history.com/svg?repos=Overture-7421/Overture-TeamsAnalizer&type=Date)](https://star-history.com/#Overture-7421/Overture-TeamsAnalizer&Date)