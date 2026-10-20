"""Quick end-to-end test: process first 3 rules only."""
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

sys.path.insert(0, ".")

from rules.llm_extractor import extract_metadata, _default_call, _is_ollama_model, _resolve_model
from rules.prompts import build_messages

model = _resolve_model()
print(f"Model: {model} (Ollama: {_is_ollama_model(model)})")

sample_chunks = [
    """Ambito - Modelo A nivel de modelo se deben cumplir los siguientes items.
Objetivo Item Descripcion Requisito Capacidad
Performance Uso de tipos de datos correcto
Evitar el uso de tipo texto en campos numericos o de fecha.
Obligatorio MidPerf""",

    """Ambito - Modelo A nivel de modelo se deben cumplir los siguientes items.
Objetivo Item Descripcion Requisito Capacidad
Performance Definir y documentar la granularidad del modelo
Es obligatorio definir y documentar la granularidad (granularity) del modelo.
Obligatorio MidPerf""",

    """Ambito - DAX A nivel de DAX se deben cumplir los siguientes items.
Objetivo Item Descripcion Requisito Capacidad
Performance Evitar la funcion FILTER como filtro de medida
No se debe usar la funcion FILTER como filtro de medida en columnas calculadas.
Obligatorio MidPerf""",
]

print(f"\nProcessing {len(sample_chunks)} chunks with 2 workers...")
t0 = time.time()
with ThreadPoolExecutor(max_workers=2) as executor:
    futures = {executor.submit(extract_metadata, c, model=model, timeout=120.0): i for i, c in enumerate(sample_chunks)}
    for f in as_completed(futures):
        i = futures[f]
        try:
            r = f.result()
            elapsed = time.time() - t0
            print(f"  Chunk {i}: is_rule={r['is_rule']}, title='{r.get('title','')[:50]}', elapsed={elapsed:.1f}s")
            if r.get("_error"):
                print(f"    ERR: {r['_error'][:120]}")
        except Exception as e:
            print(f"  Chunk {i} ERROR: {e}")

print(f"\nTotal: {time.time()-t0:.1f}s for {len(sample_chunks)} chunks")
