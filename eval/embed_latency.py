# /// script
# requires-python = ">=3.11"
# dependencies = ["numpy", "httpx>=0.28"]
# ///
import json, time
import httpx, numpy as np
D = "/Users/melkowskiphilip/Desktop/inz/deepfellow-router/data/datasets/"
with open(D + "labels.jsonl", encoding="utf-8") as f:
    cal = {r["id"] for r in map(json.loads, f) if r["split"] == "cal"}
with open(D + "questions_v2_split.jsonl", encoding="utf-8") as f:
    prompts = [r["prompt"] for r in map(json.loads, f) if r["id"] in cal][:150]
cfg = {
    "nomic-embed-text": ("classification: ", 2048),
    "qwen3-embedding:0.6b": ("Instruct: Rate how complex this user request is for a language model\nQuery: ", 4096),
}
with httpx.Client(timeout=120) as c:
    for model, (prefix, ctx) in cfg.items():
        c.post("http://localhost:11434/api/embed", json={"model": model, "input": ["warm up"], "options": {"num_ctx": ctx}})
        t = []
        for p in prompts:
            s = time.perf_counter()
            r = c.post("http://localhost:11434/api/embed", json={"model": model, "input": [prefix + p], "options": {"num_ctx": ctx}})
            r.raise_for_status()
            t.append((time.perf_counter() - s) * 1000)
        print(f"{model:24s} p50 {np.percentile(t, 50):6.1f} ms  p90 {np.percentile(t, 90):6.1f} ms  p99 {np.percentile(t, 99):6.1f} ms  (n={len(t)})")
