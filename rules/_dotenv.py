"""Helpers para cargar .env sin dependencias externas.

El script `scripts/run.py` llama a `load_dotenv()` al inicio para popular
`os.environ` desde el archivo `.env` del proyecto (si existe). Las env vars
ya seteadas en el shell tienen prioridad — esto permite override temporal sin
editar el archivo.

Formato soportado (estandar):
    KEY=value
    KEY="valor con espacios"
    KEY='valor con comillas'
    # comentario
    KEY=                     # valor vacio: NO se exporta (preserva el del shell)

No soporta expansion de variables (${VAR} no se expande). Para eso usar
python-dotenv o direnv.
"""

from __future__ import annotations

import os
from pathlib import Path


def load_dotenv(path: str | Path | None = None, override: bool = False) -> int:
    """Lee un archivo `.env` y exporta las variables a `os.environ`.

    Args:
        path: ruta al archivo .env. Si es None, busca `.env` en el cwd
              y luego junto al script principal.
        override: si True, sobreescribe env vars ya seteadas. Default False
                  (env vars del shell tienen prioridad sobre .env).

    Returns:
        Cantidad de variables exportadas.
    """
    if path is None:
        candidates = [Path.cwd() / ".env", Path(__file__).parent.parent / ".env"]
        path = next((p for p in candidates if p.exists()), None)
        if path is None:
            return 0
    path = Path(path)
    if not path.exists():
        return 0

    count = 0
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]
        if not value:
            continue
        if not override and key in os.environ:
            continue
        os.environ[key] = value
        count += 1
    return count
