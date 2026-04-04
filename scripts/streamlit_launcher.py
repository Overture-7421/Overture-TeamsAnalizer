"""PyInstaller launcher for Overture Teams Analyzer.

This wrapper starts Streamlit with the project entrypoint while supporting
both normal source runs and frozen (PyInstaller) runs.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def _bundle_root() -> Path:
    """Return the root directory that contains bundled app files."""
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(getattr(sys, "_MEIPASS"))
    return Path(__file__).resolve().parent.parent


def _resolve_app_path(bundle_root: Path) -> Path:
    """Locate the Streamlit implementation entrypoint in source or frozen layouts."""
    exe_dir = Path(sys.executable).resolve().parent
    candidates = [
        bundle_root / "lib" / "streamlit_app.py",
        bundle_root / "streamlit_app.py",
        exe_dir / "lib" / "streamlit_app.py",
        exe_dir / "streamlit_app.py",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate

    raise FileNotFoundError("Could not find bundled lib/streamlit_app.py")


def main() -> int:
    bundle_root = _bundle_root()
    os.chdir(bundle_root)

    # Ensure absolute imports used by streamlit_app.py and lib modules work.
    sys.path.insert(0, str(bundle_root))
    lib_path = bundle_root / "lib"
    if lib_path.exists():
        sys.path.insert(0, str(lib_path))

    app_path = _resolve_app_path(bundle_root)

    from streamlit.web import cli as stcli

    server_port = os.environ.get("OVERTURE_PORT", "8501")
    sys.argv = [
        "streamlit",
        "run",
        str(app_path),
        "--global.developmentMode=false",
        "--server.headless=true",
        "--browser.gatherUsageStats=false",
        f"--server.port={server_port}",
    ]
    return int(stcli.main())


if __name__ == "__main__":
    raise SystemExit(main())
