"""Punto de entrada para Streamlit Community Cloud."""

from pathlib import Path
import runpy
import sys


ROOT_DIR = Path(__file__).resolve().parent
SRC_DIR = ROOT_DIR / "src"

sys.path.insert(0, str(SRC_DIR))
runpy.run_path(str(SRC_DIR / "app.py"), run_name="__main__")