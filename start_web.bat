@echo off
echo ============================================
echo    🌐 Alliance Simulator - Versión Web
echo ============================================
echo.
echo Iniciando aplicación web...
echo La aplicación se abrirá en tu navegador en unos segundos.
echo.
echo Para cerrar la aplicación, presiona Ctrl+C en esta ventana.
echo.

REM Activar entorno virtual si existe
if exist ".venv\Scripts\activate.bat" (
    echo Activando entorno virtual...
    call .venv\Scripts\activate.bat
)

REM Ejecutar Streamlit
streamlit run streamlit_app.py

pause
