# Changelog

## [2026-04-03] — Windows Executable Packaging

### Added
- `scripts/streamlit_launcher.py`: Streamlit launcher wrapper compatible with source and PyInstaller-frozen execution.
- `scripts/build_windows_exe.cmd`: One-command Windows build script for creating a distributable executable package.
- `documentation/windows_executable_build.md`: Build and run guide for the Windows `.exe` package.
- `scripts/build_macos_executable.sh`: One-command macOS build script for creating a distributable executable package.
- `documentation/macos_executable_build.md`: Build and run guide for the macOS executable package.
- `scripts/zip_windows_release.cmd`: One-command Windows zip packaging script for the built distribution.
- `scripts/zip_macos_release.sh`: One-command macOS zip packaging script for the built distribution.

### Changed
- `documentation/README.md`: Added a Build & Packaging section linking to the Windows executable guide.
- `documentation/README.md`: Added a Build & Packaging link for the macOS executable guide.
- `requirements_web.txt`: Marked `evdev` as Linux-only via environment marker to avoid Windows installation failures.
- `scripts/streamlit_launcher.py`: Added `--global.developmentMode=false` to avoid `server.port` runtime conflict in frozen builds.

### Fixed
- `lib/qr_utils.py`: Added safer camera backend fallback and defensive handling for OpenCV camera read/window exceptions (including macOS C++ backend exceptions).
- `lib/streamlit_app.py`: QR scanner now uses a stop event for clean shutdown and disables OpenCV preview window on macOS background thread for improved camera stability.

## [2026-03-01] — FRC REBUILT 2026 Season Update

### Removed
- **TOA (The Orange Alliance) integration** — Completely removed `toa_manager.py` and all TOA-related UI (⚙️ TOA Settings page, team nickname lookups via TOA API, session state variables: `toa_manager`, `toa_api_key`, `toa_application_origin`, `toa_use_api`, `toa_event_key`, `events_list`, `selected_event_name`). The FRC REBUILT 2026 season uses TBA (The Blue Alliance) exclusively.

### Changed — Game: FRC REBUILT 2026
- **Scouting columns** (`lib/config/columns.json`): Replaced FTC DECODE 2026 artifact columns with FRC REBUILT 2026 columns:
  - **AUTO**: FUEL Scored (Active HUB), Tower Level 1 - Auto (15 pts), Left Launch Line (LEAVE, 3 pts)
  - **TELEOP**: FUEL Scored (Active HUB) (1 pt each in active HUB), Cycle Focus, Defense flags
  - **ENDGAME**: Tower Climb Level (Did Not Climb / Level 1 = 10 pts / Level 2 = 20 pts / Level 3 = 30 pts), Disabled
  - **VIOLATIONS**: Card (Yellow/Red), Tipped/Fell Over, Broke/Major Failure
- **Robot positions** now include **Blue 1/2/3** and **Red 1/2/3** (3 robots per alliance)
- **`lib/config/game.json`**: Updated game name (`REBUILT 2026`) and all scoring values
- **`lib/config/alliance.json`** and **`config/config.json`**: `teams_per_alliance` changed from 2 to 3

### Changed — Alliance Selection (3-Robot Alliances)
- `Alliance` class (`lib/allianceSelector.py`): Added `pick2` / `pick2Rec` fields
- All methods updated: `get_selected_picks`, `set_pick`, `reset_picks`, `get_alliance_table`, `update_recommendations`, `update_teams`
- Fixed a logic bug in `set_pick` duplicate-check: was using `or` instead of `and`, causing false "already selected" errors when re-assigning a pick
- UI: Alliance Selector shows Pick 2 column; Auto-optimize fills both Pick 1 and Pick 2 rounds
- `validate_alliance_selection` now requires exactly **3 teams per alliance**

### Changed — Scoring & Simulation
- `lib/engine.py`: `_decode_score_row` updated to compute FRC REBUILT 2026 scoring (FUEL lookup, Tower Level 1 Auto, Tower Climb Level endgame)
- `lib/foreshadowing.py`: `TeamPerformance` fields replaced (`auto_classified/teleop_classified/return_distribution` → `auto_fuel`, `teleop_fuel`, `p_auto_tower_l1`, `climb_distribution`); `GameConfig.from_json()`, `_simulate_alliance()`, and point-calculation methods updated; Tower L1 auto capped at 2 robots per game rule

### Added — Post-Match Analytics Page
- New **📊 Post-Match** page in the navigation
- **Match Entry** tab: record match number, Red/Blue alliance points, team count, per-team contribution (7 levels from "Did not score any points" to "Scored almost all")
- **Qualitative Metrics** tab: contribution distribution bar chart, average Red/Blue/total points, points-per-match line chart
- Post-match data capped to 200 entries to prevent unbounded memory growth

### Changed — Headless Interceptor (Linux compatibility)
- `lib/headless_interceptor.py`: Now works on **any Linux distribution** (not just Debian/Ubuntu)
  - Added `/proc/bus/input/devices` fallback for device discovery when `evdev.list_devices()` returns empty (common on some distros or permission setups)
  - Error messages updated to be distro-agnostic
  - `PermissionError` handler now documents three fix options including udev rules (no re-login required)
  - `HIDInterceptor` docstring updated to list compatible distros
  - `list_all_input_devices` and `find_scanner_device` both use the new fallback

### Changed — TBA Manager (security & robustness)
- `lib/tba_manager.py`: Cache files now stored in `data/` instead of next to source code (avoids accidental disclosure and keeps source tree clean)
- Added `timeout=(10, 30)` to all HTTP requests to prevent connection hangs

### Changed — CSV Upload (security)
- `streamlit_app.py` `load_csv_data`: Added 50 MB file-size guard before writing to disk; returns a clear error message for oversized uploads

### Documentation
- `documentation/README.md`: Updated for FRC REBUILT 2026, added scoring table, updated architecture diagram
- `documentation/linux_headless_server_setup.md`: Completely rewritten for all Linux distributions; added Fedora, Arch, openSUSE instructions; added firewall section; added udev rule instructions
- `documentation/headless_interceptor.md`: Updated to document all-distro support, two-stage device discovery, and per-distro permission setup
- `documentation/CHANGELOG.md`: This file — new addition
