import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEYS_PATH = Path(os.environ.get("PKM_KEYS") or (ROOT / "keys" / "keys.json"))
