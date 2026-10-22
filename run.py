"""
TerraFlood Launcher
===================
Launches the TerraFlood Tactical Command Center Streamlit application.
Usage:
    python run.py
or
    streamlit run terraflood/app.py
"""

import sys
import subprocess
from pathlib import Path

if __name__ == "__main__":
    app_path = Path(__file__).resolve().parent / "terraflood" / "app.py"
    print(f"Launching TerraFlood Command Center from: {app_path}")
    cmd = [sys.executable, "-m", "streamlit", "run", str(app_path)]
    subprocess.run(cmd)
