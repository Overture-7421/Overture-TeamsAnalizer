# Alliance Simulator - Versión Web

## 🌐 Cómo ejecutar la versión web

### 1. **Instalación de dependencias:**
```bash
pip install -r requirements_web.txt
```

### 2. **Ejecutar la aplicación web:**
```bash
streamlit run streamlit_app.py
```

### 3. **Abrir en el navegador:**
La aplicación se abrirá automáticamente en `http://localhost:8501`

## 🚀 Características de la versión web

### ✅ **Funcionalidades implementadas:**
- 📊 **Carga de datos CSV** con interfaz drag-and-drop
- 📱 **Entrada de datos QR** manual
- 📈 **Visualización de estadísticas** por equipo
- 🎮 **Configuración de fases del juego** (Autonomous, Teleop, Endgame)
- 🤝 **Alliance Selector** interactivo
- 🏆 **Honor Roll System** con ranking automático
- 💾 **Exportar/Importar configuraciones** en JSON
- 📊 **Gráficos interactivos** con Plotly/Streamlit

### 📋 **Páginas disponibles:**
1. **📊 Datos y Configuración** - Cargar y gestionar datos
2. **📈 Estadísticas de Equipos** - Análisis detallado por equipo  
3. **🤝 Selector de Alianzas** - Simulador de draft de alianzas
4. **🏆 Honor Roll System** - Sistema de ranking con puntajes
5. **⚙️ Configuración de Fases** - Configurar columnas por fase del juego

### 🎯 **Ventajas de la versión web:**
- ✅ **Multiplataforma** - Funciona en Windows, Mac, Linux
- ✅ **Sin instalación** - Solo necesita un navegador web
- ✅ **Compartible** - Puede desplegarse en la nube
- ✅ **Interfaz moderna** - UI responsive y atractiva
- ✅ **Colaborativo** - Múltiples usuarios pueden acceder
- ✅ **Móvil-friendly** - Funciona en tablets y móviles

## 🔧 **Opciones de despliegue:**

### **Opción 1: Local (desarrollo)**
```bash
streamlit run streamlit_app.py
```

### **Opción 2: Streamlit Cloud (gratuito)**
1. Sube el código a GitHub
2. Conecta con [share.streamlit.io](https://share.streamlit.io)
3. Deploy automático

### **Opción 3: Heroku/Railway/Render**
Para deployment más avanzado con dominio personalizado

### **Opción 4: Docker**
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements_web.txt .
RUN pip install -r requirements_web.txt

COPY . .

EXPOSE 8501

CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
```

## 📱 **Uso de la aplicación web:**

### **1. Cargar datos:**
- Ve a "📊 Datos y Configuración"
- Arrastra tu archivo CSV o usa el botón "Browse files"
- Los datos se procesarán automáticamente

### **2. Configurar fases del juego:**
- Ve a "⚙️ Configuración de Fases"
- Usa "🔍 Auto-detectar" para detección automática
- O configura manualmente las columnas por fase

### **3. Ver estadísticas:**
- Ve a "📈 Estadísticas de Equipos"
- Visualiza tablas y gráficos interactivos
- Analiza rendimiento por fase del juego

### **4. Simular alianzas:**
- Ve a "🤝 Selector de Alianzas" 
- Crea el selector basado en tus datos
- Visualiza recomendaciones de picks

### **5. Generar ranking:**
- Ve a "🏆 Honor Roll System"
- Auto-pobla con datos reales de tus equipos
- Visualiza ranking final con puntajes

## 🆚 **Comparación: Desktop vs Web**

| Característica | Desktop (Tkinter) | Web (Streamlit) |
|----------------|------------------|-----------------|
| **Instalación** | Requiere Python local | Solo navegador |
| **Plataforma** | Windows principalmente | Multiplataforma |
| **Compartir** | Archivo ejecutable | URL web |
| **Colaboración** | Individual | Múltiples usuarios |
| **Actualizaciones** | Manual | Automáticas |
| **Móviles** | No | Sí |
| **Gráficos** | Matplotlib | Plotly interactivo |
| **UI** | Tkinter tradicional | Moderna y responsive |

## 🔮 **Funcionalidades futuras posibles:**
- 🔐 **Autenticación** de usuarios
- 💾 **Base de datos** persistente
- 📊 **Dashboard** en tiempo real
- 🔔 **Notificaciones** push
- 📱 **APP móvil** nativa
- 🤖 **API REST** para integración
- 📈 **Analytics** avanzados
- 🎨 **Temas** personalizables

## 🆘 **Solución de problemas:**

### **Error: "streamlit: command not found"**
```bash
pip install streamlit
# o
python -m streamlit run streamlit_app.py
```

### **Error de puertos:**
```bash
streamlit run streamlit_app.py --server.port=8502
```

### **Problemas de dependencias:**
```bash
pip install -r requirements_web.txt --upgrade
```

¡La versión web está lista para usar! 🚀
