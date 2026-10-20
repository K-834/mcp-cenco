"""Debug: litellm Ollama call directly."""
import sys
import time

sys.path.insert(0, ".")

import litellm
from rules.prompts import build_messages

print("Test 1: small prompt via litellm")
sample_chunk = """Ambito - Modelo A nivel de modelo se deben cumplir los siguientes items.
Objetivo Item Descripcion Requisito Capacidad
Performance Uso de tipos de datos correcto
Evitar el uso de tipo texto en campos numericos o de fecha.
Obligatorio MidPerf"""

messages = build_messages(sample_chunk)

t0 = time.time()
try:
    resp = litellm.completion(
        model="ollama/qwen2.5-coder:14b",
        messages=messages,
        temperature=0,
        max_tokens=2500,
        timeout=300,
        api_base="http://localhost:11434",
    )
    print(f"OK in {time.time()-t0:.1f}s")
    print("Content:", resp.choices[0].message.content[:300])
except Exception as e:
    print(f"ERROR after {time.time()-t0:.1f}s: {type(e).__name__}: {e}")
