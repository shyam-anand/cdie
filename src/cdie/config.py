import os
from pathlib import Path

_CURRENT_DIR = Path(os.path.dirname(__file__))

# Path to the src/ directory
SRC_ROOT = _CURRENT_DIR.parent

# Path to the app directory (cdie/)
APP_ROOT = SRC_ROOT.parent

# Path to the resources directory (contains the sample pdfs)
RESOURCES_ROOT = APP_ROOT / "resources"

# Path to the data directory (contains the extracted data)
DATA_ROOT = APP_ROOT / "data"
