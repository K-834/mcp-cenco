from __future__ import annotations

import json
from pathlib import Path
from typing import Callable

URI = "rules://best-practices"


def register(mcp, load_rules: Callable[[], dict]) -> None:
    @mcp.resource(URI)
    def best_practices() -> str:
        """Devuelve el rules.json compilado para que el cliente lo lea una vez por sesion."""
        return json.dumps(load_rules(), ensure_ascii=False, indent=2)
