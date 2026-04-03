# Project Guidelines

## Overview
Overture Teams Analyzer is a Streamlit-based FRC scouting and alliance simulation app. The canonical entry point is [streamlit_app.py](streamlit_app.py), which re-exports the implementation in [lib/streamlit_app.py](lib/streamlit_app.py). Treat [lib/config/columns.json](lib/config/columns.json) as the authoritative column schema.

## Code Style
- Keep Python changes small and local.
- Preserve the existing lazy-import and caching patterns in Streamlit modules; do not eagerly load heavy dependencies unless the feature needs them.
- Maintain backward-compatible field names and labels when touching CSV parsing, scoring, or display logic.
- When adding new features, follow the existing code style and patterns for consistency. For example, use the same structure for new functions, maintain the same error handling approach, and adhere to the existing naming conventions.
- When refactoring, ensure that the same input data produces the same output data and display, unless the change is explicitly about modifying the schema or scoring rules. This is critical for maintaining compatibility with existing scouting data and user expectations.
- When implementing new features, consider the impact on the user interface and user experience, also focus the changes in a modular way. For example, if adding new fields to the scouting schema, ensure that they are displayed in a logical and intuitive way in the UI, and that they do not overwhelm the user with too much information at once. Another example is if adding a new feature like foreshadowing, keep the logic separate from the core data processing and display logic, so that it can be easily maintained and updated without affecting the rest of the app.

## Architecture
- [lib/](lib/) contains the app logic, data processing, and reusable modules.
- [data/](data/) contains sample data and team/event JSON used by the app.
- [documentation/](documentation/) contains the current implementation docs.
- [docs/](docs/) contains deployment and setup guides.
- [legacy/](legacy/) is historical reference and should not be treated as source of truth when it conflicts with code.

## Build and Test
- Install dependencies with [scripts/install_dependencies_windows.cmd](scripts/install_dependencies_windows.cmd) on Windows or [scripts/install_dependencies_linux.sh](scripts/install_dependencies_linux.sh) on Linux.
- Run the app with `streamlit run streamlit_app.py` from the repo root.
- There is no maintained automated test suite today; verify changes by launching the app and exercising the affected workflow with sample data.

## Conventions
- Use [requirements_web.txt](requirements_web.txt) for the Streamlit app dependencies; do not assume a `requirements.txt` or `main.py`.
- Use [lib/config_manager.py](lib/config_manager.py) for CSV format detection and config loading instead of ad hoc parsing.
- `None` and `None Value` are intentional missing-value placeholders in [lib/engine.py](lib/engine.py).
- Team display labels may fall back to the list of .json in [data/](data/) when TBA is unavailable.
- When changing scouting schema or scoring rules, update the code, sample data, and matching docs together.
- Link to existing docs instead of duplicating them, especially [documentation/README.md](documentation/README.md), [documentation/CHANGELOG.md](documentation/CHANGELOG.md), [documentation/engine.md](documentation/engine.md), [documentation/config_manager.md](documentation/config_manager.md), [documentation/foreshadowing.md](documentation/foreshadowing.md), and [docs/DOCKER_DEPLOYMENT.md](docs/DOCKER_DEPLOYMENT.md).
- When adding new features, consider the impact on the user interface and user experience, also focus the changes in a modular way. For example, if adding new fields to the scouting schema, ensure that they are displayed in a logical and intuitive way in the UI, and that they do not overwhelm the user with too much information at once. Another example is if adding a new feature like foreshadowing, keep the logic separate from the core data processing and display logic, so that it can be easily maintained and updated without affecting the rest of the app.
- Use the existing .md files in [.github/agents/](.github/agents/) as context if needed for some context about scorings from FRC or FTC,or QR codes logic.