from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

BASE_DIR = Path(__file__).resolve().parent


def load_json_config(*relative_paths: str) -> Dict[str, Any]:
    """
    Try each relative path under the runtrack package and load the first JSON file found.
    Returns an empty dict if no file can be read.
    """
    for rel_path in relative_paths:
        path = BASE_DIR / rel_path
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text())
            if isinstance(data, dict):
                return data
        except Exception:
            continue
    return {}

