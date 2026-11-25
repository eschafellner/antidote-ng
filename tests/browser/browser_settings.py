from os import environ as _environment
from pathlib import Path

from config.settings import *

BASE_DIR = Path(_environment["ANTIDOTE_BROWSER_DIR"])
STATICFILES_DIRS = [BASE_DIR / "static"]
