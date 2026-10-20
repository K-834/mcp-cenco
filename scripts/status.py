import json
from pathlib import Path
import datetime
from collections import Counter

p = Path("rules/rules.json")
mtime = datetime.datetime.fromtimestamp(p.stat().st_mtime)
print(f"rules.json last modified: {mtime}")
data = json.loads(p.read_text(encoding="utf-8"))
rules = data["rules"]
print("Compiled by breakdown:")
cb = Counter(r.get("compiled_by", "none") for r in rules)
for k, v in cb.items():
    print(f"  {k}: {v}")
print(f"Total: {len(rules)}")
print()
print("Sample LLM rule:")
for r in rules:
    if r.get("compiled_by") == "llm":
        print(f"  {r['id']}: {r['title']}")
        print(f"    category={r.get('category')} severity={r.get('severity')} scope={r.get('scope')}")
        print(f"    keywords={r.get('keywords')[:3] if r.get('keywords') else []}")
        break
