# OpenCode / AI Agent Instructions

This repository contains the **Overture Teams Analyzer** (also known as the Alliance Simulator), a tool for analyzing FRC/FTC robotics scouting and exam data.

## Architecture & Entrypoints

- **Framework**: The current app is a **Streamlit** web application.
- **Entrypoint**: `streamlit run streamlit_app.py` from the root directory. 
- **Code Location**: The root `streamlit_app.py` is a simple wrapper that injects `lib/` into the python path and delegates to `lib/streamlit_app.py`. **All active UI and backend logic lives in `lib/`**.
- **Legacy Code**: The `legacy/` folder contains an old Tkinter-based version (`legacy/main.py`). Do not edit files in `legacy/` when adding features unless explicitly asked.

## Domain & Data 

- **Data Sources**: The system integrates "Match Scouting" (robot performance) and "Pit Scouting / Exams" (competency, programming, electrical, mechanical).
- **Bilingual Support**: The expected CSV files (from Google Forms/scouting apps) often use Spanish column names (`Examen de Programacion`, `Marca temporal`, `Puntuacion`). The parsers in `lib/` explicitly check for both Spanish and English aliases (e.g., in `lib/exam_integrator.py`).
- **Sample Data**: Use `archivos ejemplo/` to find sample CSVs and JSONs to understand the expected input schemas. Do not overwrite these files with garbage.

## Testing & Verification

- **Running Tests**: The project uses standard `unittest`. Run all tests using:
  ```bash
  python -m unittest discover tests
  ```
- **Test Structure**: Tests live in the `tests/` directory. When adding logic (especially parsers like `lib/exam_integrator.py` or scoring calculations in `lib/school_system.py`), include corresponding `unittest` test cases.

## Build & Release Process

- **Executables**: While it is a Streamlit app, it is also packaged as a standalone desktop executable for users without Python.
- **Build Scripts**: Look in `scripts/` (e.g., `build_windows_exe.cmd`, `build_macos_executable.sh`). 
- **Constraint**: Because the app is compiled with PyInstaller, **do not rely on hardcoded absolute file paths or `__file__` assumptions without handling PyInstaller's `sys._MEIPASS`**. Always use path resolution that is safe for bundled executables.

## Dependencies

- Managed via standard Python virtual environments. 
- Core dependencies are listed in `requirements_web.txt`. Add any new packages there.