"""Launch the Streamlit dashboard: python run_dashboard.py (or streamlit run dashboard/app.py)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

if __name__ == "__main__":
    app = Path(__file__).resolve().parent / "dashboard" / "app.py"
    subprocess.run([sys.executable, "-m", "streamlit", "run", str(app)], check=False)
