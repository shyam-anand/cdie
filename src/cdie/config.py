import argparse
import os
from pathlib import Path

import dotenv

_CURRENT_DIR = Path(os.path.dirname(__file__))

# Path to the src/ directory
SRC_ROOT = _CURRENT_DIR.parent

# Path to the app directory (cdie/)
APP_ROOT = SRC_ROOT.parent

# Path to the resources directory (contains the sample pdfs)
RESOURCES_ROOT = APP_ROOT / "resources"

# Path to the data directory (contains the extracted data)
DATA_ROOT = APP_ROOT / "data"


_config_arg_parser = argparse.ArgumentParser()
_config_arg_parser.add_argument(
    "-e",
    "--env",
    type=str,
    help="Path to the .env file to use.",
)

_config_args, _ = _config_arg_parser.parse_known_args()
CONFIG_FILE = _config_args.env or APP_ROOT / ".env"

_dotenv_values = dotenv.dotenv_values(CONFIG_FILE)

# _env contains all the variables in the .env file. Use this to access the variables not
# defined in the AppConfig class.
_env = {
    **_dotenv_values,
    "CONFIG_FILE": str(CONFIG_FILE),
}


def get_config(key: str) -> str | None:
    """Get a configuration value from the environment."""
    return _env.get(key.upper())
