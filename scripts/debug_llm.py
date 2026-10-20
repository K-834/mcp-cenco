"""Debug: time the native Ollama call with gemma3:4b."""
import sys
import time

sys.path.insert(0, ".")

from rules.llm_extractor import _default_call, _is_ollama_model, build_messages

sample_chunk = """Ambito - Modelo A nivel de modelo se deben cumplir los siguientes items.
Objetivo Item Descripcion Requisito Capacidad
Performance Uso de tipos de datos correcto
Evitar el uso de tipo texto en campos numericos o de fecha.
Obligatorio MidPerf"""

messages = build_messages(sample_chunk)

print("Test: gemma3:4b native HTTP call")
t0 = time.time()
try:
    out = _default_call(messages, "ollama/gemma3:4b", 180.0)
    print(f"OK in {time.time()-t0:.1f}s")
    print(out[:400])
except Exception as e:
    print(f"ERROR after {time.time()-t0:.1f}s: {type(e).__name__}: {e}")
