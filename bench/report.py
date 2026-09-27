#!/usr/bin/env python3
"""汇总 bench.py 的结果：生成 results_all.csv 与 report.md。"""
import csv
import json
import statistics
from pathlib import Path

BENCH_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BENCH_DIR / "results"
ALL_MODELS = [
    "DeepSeek-V4.1-Flash",
    "GLM-5.3",
    "GLM-5.3-Flash",
    "GPT-5.6-Sol",
    "GPT-5.6-Terra",
    "Claude-Sonnet-5",
    "Gemini-3.8-Flash",
]
DIFFS = ["基础", "进阶", "挑战"]


def load():
    data = {}
    for m in ALL_MODELS:
        p = RESULTS_DIR / f"{m}.jsonl"
        recs = []
        if p.exists():
            with open(p, encoding="utf-8") as f:
                recs = [json.loads(l) for l in f if l.strip()]
        data[m] = recs
    return data


def pct(n, d):
    return f"{n / d * 100:.1f}%" if d else "-"


def lat_stats(recs):
    lat = sorted(r["latency_s"] for r in recs if r["latency_s"] is not None)
    if not lat:
        return 0, 0, 0, 0
    p95 = lat[min(len(lat) - 1, max(0, int(len(lat) * 0.95) - 1))]
    return statistics.mean(lat), statistics.median(lat), p95, max(lat)


def acc(recs, **filt):
    rs = [r for r in recs if all(r[k] == v for k, v in filt.items())]
    return pct(sum(1 for r in rs if r["correct"]), len(rs))


def main():
    data = load()
    domains = sorted({r["domain"] for recs in data.values() for r in recs})

    # ---- 明细 CSV ----
    with open(BENCH_DIR / "results_all.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["model", "qid", "qtype", "domain", "difficulty",
                    "pred", "truth", "correct", "parse_ok", "latency_s",
                    "completion_tokens", "error"])
        for m in ALL_MODELS:
            for r in sorted(data[m], key=lambda x: x["qid"]):
                w.writerow([m, r["qid"], r["qtype"], r["domain"], r["difficulty"],
                            r["pred"], r["truth"], int(r["correct"]), int(r["parse_ok"]),
                            r["latency_s"], r.get("completion_tokens"), r.get("error") or ""])

    # ---- Markdown 报告 ----
    L = []
    L.append("# 硬件安全题库多模型评测报告")
    L.append("")
    L.append("- 题库：硬件安全题库.csv，126 题（单选 82、多选 44），覆盖 17 个知识域")
    L.append("- 采集：temperature=0.1；提示词要求只输出选项字母；按字母集合精确匹配判分")
    L.append("- 响应时间：单次 HTTP 请求墙钟时间（秒）；失败自动重试，无请求最终失败")
    L.append("- 日期：2026-09-25")
    L.append("")
    L.append("## 总览")
    L.append("")
    L.append("| 模型 | 正确/总数 | 正确率 | 单选 | 多选 | 平均时延(s) | 中位(s) | P95(s) | 最大(s) | 平均输出tokens | 解析异常 |")
    L.append("|---|---|---|---|---|---|---|---|---|---|---|")
    for m in ALL_MODELS:
        recs = data[m]
        if not recs:
            L.append(f"| {m} | - | - | - | - | - | - | - | - | - | - |")
            continue
        mean, med, p95, mx = lat_stats(recs)
        toks = [r["completion_tokens"] for r in recs if r.get("completion_tokens")]
        bad = sum(1 for r in recs if not r["parse_ok"])
        L.append(f"| {m} | {sum(1 for r in recs if r['correct'])}/{len(recs)} "
                 f"| {pct(sum(1 for r in recs if r['correct']), len(recs))} "
                 f"| {acc(recs, qtype='单选')} | {acc(recs, qtype='多选')} "
                 f"| {mean:.1f} | {med:.1f} | {p95:.1f} | {mx:.1f} "
                 f"| {statistics.mean(toks):.0f} | {bad} |")

    L.append("")
    L.append("## 按知识域正确率（括号内为题数）")
    L.append("")
    L.append("| 知识域 | " + " | ".join(ALL_MODELS) + " |")
    L.append("|---|" + "---|" * len(ALL_MODELS))
    dom_total = {}
    for r in data[ALL_MODELS[0]]:
        dom_total.setdefault(r["domain"], set()).add(r["qid"])
    for d in domains:
        cells = [acc(data[m], domain=d) for m in ALL_MODELS]
        L.append(f"| {d}({len(dom_total.get(d, set()))}) | " + " | ".join(cells) + " |")

    L.append("")
    L.append("## 按难度正确率")
    L.append("")
    L.append("| 难度 | " + " | ".join(ALL_MODELS) + " |")
    L.append("|---|" + "---|" * len(ALL_MODELS))
    for d in DIFFS:
        L.append(f"| {d} | " + " | ".join(acc(data[m], difficulty=d) for m in ALL_MODELS) + " |")

    L.append("")
    L.append("## 答错题目明细")
    L.append("")
    for m in ALL_MODELS:
        wrong = [r for r in sorted(data[m], key=lambda x: x["qid"]) if not r["correct"]]
        ids = ", ".join(f"{r['qid']}(答{r['pred'] or '空'},正确{r['truth']})" for r in wrong)
        L.append(f"- **{m}**（{len(wrong)} 题）：{ids or '无'}")

    with open(BENCH_DIR / "report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(L) + "\n")
    print(f"已生成 {BENCH_DIR / 'results_all.csv'} 和 {BENCH_DIR / 'report.md'}")


if __name__ == "__main__":
    main()
