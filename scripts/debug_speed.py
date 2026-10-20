"""Compare models: gemma3:4b vs qwen2.5-coder:7b."""
import json, time, urllib.request

def call(model, prompt, num_predict=400, num_ctx=1024):
    data = json.dumps({"model": model, "prompt": prompt, "stream": False, "options": {"num_predict": num_predict, "num_ctx": num_ctx, "temperature": 0}}).encode()
    req = urllib.request.Request("http://localhost:11434/api/generate", data=data, headers={"Content-Type": "application/json"})
    t0 = time.time()
    r = urllib.request.urlopen(req, timeout=300)
    out = json.loads(r.read())
    total = time.time() - t0
    ld = out.get("load_duration", 0) / 1e6
    pec = out.get("prompt_eval_count", 0)
    ped = out.get("prompt_eval_duration", 0) / 1e6
    ec = out.get("eval_count", 0)
    ed = out.get("eval_duration", 0) / 1e6
    return total, ld, pec, ped, ec, ed

sys_prompt = """Eres auditor Power BI. Extrae metadata estructurada como JSON. Categorias validas: modelo_datos, medidas_dax, reporte_visual, rendimiento, nomenclatura, seguridad, documentacion. Severities: alta, media, baja. Scopes: tables, columns, measures, relationships, pages, visuals, dataset. Responde SOLO con JSON valido sin markdown."""

user_prompt = """Fragmento: Uso de tipos de datos correcto. Evitar el uso de tipo texto en campos numericos o de fecha. JSON:"""

prompt = sys_prompt + "\n\n" + user_prompt

for model in ["gemma3:4b", "qwen2.5-coder:7b", "qwen2.5-coder:14b"]:
    print(f"=== {model} ===")
    try:
        for i in range(2):
            t, ld, pec, ped, ec, ed = call(model, prompt, 400, 1024)
            print(f"  call {i+1}: total={t:.1f}s load={ld:.0f}ms prompt={pec}tok/{ped:.0f}ms eval={ec}tok/{ed:.0f}ms")
    except Exception as e:
        print(f"  ERROR: {type(e).__name__}: {e}")
    print()
