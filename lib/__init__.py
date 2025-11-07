"""Core modules for the Overture Teams Analyzer application."""

from pathlib import Path

LIB_ROOT = Path(__file__).resolve().parent


def resource_path(*relative_parts: str) -> Path:
    """Return an absolute path inside the lib package."""
    return LIB_ROOT.joinpath(*relative_parts)
