# Dockerfile para Alliance Simulator Web
FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Copiar archivos de requisitos
COPY requirements_web.txt .

# Instalar dependencias del sistema para OpenCV
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libzbar0 \
    && rm -rf /var/lib/apt/lists/*

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements_web.txt

# Copiar código de la aplicación
COPY . .

# Exponer puerto
EXPOSE 8501

# Configurar Streamlit
RUN mkdir -p ~/.streamlit
RUN echo "\
[server]\n\
headless = true\n\
port = 8501\n\
address = 0.0.0.0\n\
enableCORS = false\n\
enableXsrfProtection = false\n\
\n\
[browser]\n\
gatherUsageStats = false\n\
" > ~/.streamlit/config.toml

# Comando para ejecutar la aplicación
CMD ["streamlit", "run", "streamlit_app.py"]
