"""
Alliance Simulator - Streamlit Web Application
Main entry point for the Streamlit-exclusive architecture.

This module serves as the root entry point that imports and runs
the Streamlit application from lib/streamlit_app.py
"""

import sys
import os
from pathlib import Path

# Use absolute paths to ensure consistency across Streamlit reruns
ROOT_DIR = Path(__file__).resolve().parent
LIB_DIR = ROOT_DIR / "lib"

# Add lib directory to path for imports (use resolved absolute path)
lib_path_str = str(LIB_DIR)
if lib_path_str not in sys.path:
    sys.path.insert(0, lib_path_str)

# Also ensure lib is in path for relative imports within lib modules
if str(LIB_DIR) not in sys.path:
    sys.path.insert(0, str(LIB_DIR))

# Change working directory to lib for consistent file path resolution
os.chdir(LIB_DIR)

# Import and run the streamlit app
# Using import * executes all the Streamlit code in lib/streamlit_app.py
from streamlit_app import *

# Note: When running with streamlit, use:
# streamlit run streamlit_app.py
#
# The app can also be run from the lib directory:
# cd lib && streamlit run streamlit_app.py
