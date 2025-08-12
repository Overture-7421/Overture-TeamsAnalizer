#!/bin/bash

echo "============================================"
echo "   🌐 Alliance Simulator - Versión Web"
echo "============================================"
echo ""
echo "Iniciando aplicación web..."
echo "La aplicación se abrirá en tu navegador en unos segundos."
echo ""
echo "Para cerrar la aplicación, presiona Ctrl+C en esta terminal."
echo ""

# Activar entorno virtual si existe
if [ -d ".venv" ]; then
    echo "Activando entorno virtual..."
    source .venv/bin/activate
fi

# Ejecutar Streamlit
streamlit run streamlit_app.py
