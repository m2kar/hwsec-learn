#!/usr/bin/env python3
"""用改进后的提取规则，依据已存 raw 重新判分（不重新请求 API）。"""
import json
from pathlib import Path

from bench import extract_letters

RESULTS_DIR = Path(__file__).resolve().parent / "results"

changed = 0
for p in sorted(RESULTS_DIR.glob("*.jsonl")):
    recs = [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()]
    for r in recs:
        pred, parse_ok = extract_letters(r["raw"], r["qtype"])
        correct = (pred == r["truth"])
        if (pred, parse_ok) != (r["pred"], r["parse_ok"]):
            print(f"[变更] {p.stem} {r['qid']}: pred {r['pred']}→{pred}, "
                  f"parse_ok {r['parse_ok']}→{parse_ok}, correct {r['correct']}→{correct}")
            print(f"       raw: {r['raw'][:160]!r}")
            changed += 1
        r["pred"], r["parse_ok"], r["correct"] = pred, parse_ok, correct
    with open(p, "w", encoding="utf-8") as f:
        for r in recs:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
print(f"完成，共变更 {changed} 条")
