"""
Alliance Simulator - Streamlit Web Application
Main entry point for the Streamlit-exclusive architecture.

This module serves as the root entry point that imports and runs
the Streamlit application from lib/streamlit_app.py
"""

import sys
from pathlib import Path

# Add lib directory to path for imports
lib_path = Path(__file__).parent / "lib"
if str(lib_path) not in sys.path:
    sys.path.insert(0, str(lib_path))

# Import and run the streamlit app
# The actual app is in lib/streamlit_app.py
# This file serves as a clean entry point from the project root

# Re-export everything from the lib streamlit app
from lib.streamlit_app import *

# Note: When running with streamlit, use:
# streamlit run streamlit_app.py
# 
# The app can also be run from the lib directory:
# cd lib && streamlit run streamlit_app.py
