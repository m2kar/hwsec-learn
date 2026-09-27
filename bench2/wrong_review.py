#!/usr/bin/env python3
"""从 results_full/<model>.jsonl 提取答错题目，生成便于人工逐题审阅的 Markdown。

用法: python3 wrong_review.py [模型名，默认 DeepSeek-V4.1-Flash]
输出: bench2/wrong_review_<model>.md
"""
import csv
import json
import sys
from collections import Counter
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent
CSV_PATH = BENCH_DIR.parent / "硬件安全题库2.csv"
FULL_DIR = BENCH_DIR / "results_full"

model = sys.argv[1] if len(sys.argv) > 1 else "DeepSeek-V4.1-Flash"

bank = {}
with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        bank[r["题号"].strip()] = r

recs = {}
with open(FULL_DIR / f"{model}.jsonl", encoding="utf-8") as f:
    for line in f:
        try:
            r = json.loads(line)
        except Exception:
            continue
        if not r.get("error"):
            recs[r["qid"]] = r

wrong = [q for q, r in recs.items() if not r["correct"]]
wrong.sort()

lines = [f"# {model} 全库错题审阅（{len(recs)} 题答错 {len(wrong)} 题，正确率 {100 * (len(recs) - len(wrong)) / len(recs):.1f}%）\n"]
dom = Counter(bank[q]["知识域"] for q in wrong)
typ = Counter(bank[q]["题型"] for q in wrong)
diff = Counter(bank[q]["难度"] for q in wrong)
lines.append(f"错题分布 —— 知识域：{dict(dom)}；题型：{dict(typ)}；难度：{dict(diff)}\n")

for i, qid in enumerate(wrong, 1):
    b = bank[qid]
    r = recs[qid]
    lines.append(f"\n---\n\n## [{i}] {qid}  {b['题型']}/{b['难度']}/{b['知识域']}  标准答案={b['答案']}  模型作答={r['pred']}\n")
    lines.append(f"**考点**：{b['考点']}\n\n")
    lines.append(f"**题干**：{b['题干']}\n\n")
    for k in "ABCDEFG":
        v = (b.get(f"选项{k}") or "").strip()
        if v:
            mark = " ←模型选" if k in r["pred"] else ""
            correct_mark = " ✓" if k in b["答案"] else ""
            lines.append(f"- {k}. {v}{correct_mark}{mark}\n")
    lines.append(f"\n**标准解析**：{b['解析']}\n\n")
    lines.append(f"**模型原始回复**：\n\n> {r['raw'].replace(chr(10), chr(10) + '> ')}\n\n")

out = BENCH_DIR / f"wrong_review_{model}.md"
out.write_text("".join(lines), encoding="utf-8")
print(f"错题 {len(wrong)} 道，输出 {out}")
print("错题列表:", " ".join(wrong))
