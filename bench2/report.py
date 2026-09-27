#!/usr/bin/env python3
"""汇总 bench2/results/*.jsonl，生成统计 agg/stats.json、明细 agg/results_all.csv
与图表 charts/*.svg（供 report.typ 使用）。

用法: python3 report.py
"""
import csv
import json
import math
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

BENCH_DIR = Path(__file__).resolve().parent
RESULTS_DIR = BENCH_DIR / "results"
AGG_DIR = BENCH_DIR / "agg"
CHARTS_DIR = BENCH_DIR / "charts"
AGG_DIR.mkdir(exist_ok=True)
CHARTS_DIR.mkdir(exist_ok=True)

MODELS = [
    "DeepSeek-V4.1-Flash",
    "GLM-5.3",
    "GLM-5.3-Flash",
    "GPT-5.6-Sol",
    "GPT-5.6-Terra",
    "Claude-Sonnet-5",
    "Gemini-3.8-Flash",
]
MODEL_COLORS = {
    "DeepSeek-V4.1-Flash": "#4C72B0",
    "GLM-5.3": "#DD8452",
    "GLM-5.3-Flash": "#55A868",
    "GPT-5.6-Sol": "#C44E52",
    "GPT-5.6-Terra": "#8172B3",
    "Claude-Sonnet-5": "#937860",
    "Gemini-3.8-Flash": "#DA8BC3",
}

plt.rcParams["font.sans-serif"] = ["PingFang SC", "Hiragino Sans GB", "Arial Unicode MS"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["svg.fonttype"] = "path"  # 文字转路径，避免 Typst 渲染 SVG 缺字体
plt.rcParams["figure.dpi"] = 120
plt.rcParams["savefig.bbox"] = "tight"


def wilson(p, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    denom = 1 + z**2 / n
    center = (p + z**2 / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return (max(0, center - half), min(1, center + half))


def pct(x):
    return round(100 * x, 1)


def main():
    sample = json.load(open(BENCH_DIR / "sample_questions.json", encoding="utf-8"))
    qmeta = {q["qid"]: q for q in sample}
    qids = [q["qid"] for q in sample]

    # ---------- 载入各模型结果 ----------
    raw = {}
    for m in MODELS:
        recs = {}
        with open(RESULTS_DIR / f"{m}.jsonl", encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if r.get("error"):
                    continue
                recs[r["qid"]] = r
        missing = [q for q in qids if q not in recs]
        if missing:
            print(f"[警告] {m} 缺 {len(missing)} 题: {missing[:5]}...")
        raw[m] = recs

    lat = {m: [raw[m][q]["latency_s"] for q in qids if q in raw[m]] for m in MODELS}

    # ---------- 模型级统计 ----------
    models_stat = []
    for m in MODELS:
        recs = raw[m]
        n = sum(1 for q in qids if q in recs)
        c = sum(1 for q in qids if recs.get(q, {}).get("correct"))
        acc = c / n if n else 0
        lo, hi = wilson(acc, n)
        ls = sorted(lat[m])
        k = len(ls)
        toks = [recs[q]["completion_tokens"] for q in qids
                if q in recs and recs[q].get("completion_tokens")]
        lats_t = [recs[q]["latency_s"] for q in qids
                  if q in recs and recs[q].get("completion_tokens")]
        tps = sorted(t / l for t, l in zip(toks, lats_t) if l > 0)
        models_stat.append({
            "name": m, "n": n, "correct": c, "accuracy": round(acc, 4),
            "ci_lo": round(lo, 4), "ci_hi": round(hi, 4),
            "mean_lat": round(float(np.mean(ls)), 2), "median_lat": round(float(np.median(ls)), 2),
            "p90_lat": round(ls[min(k - 1, int(math.ceil(0.90 * k)) - 1)], 2),
            "p95_lat": round(ls[min(k - 1, int(math.ceil(0.95 * k)) - 1)], 2),
            "min_lat": round(ls[0], 2), "max_lat": round(ls[-1], 2),
            "median_tokens": int(np.median(toks)) if toks else None,
            "median_tps": round(float(np.median(tps)), 1) if tps else None,
            "parse_fail": sum(1 for q in qids if q in recs and not recs[q].get("parse_ok")),
            "errors_single": sum(1 for q in qids if q in recs and not recs[q]["correct"]
                                 and recs[q]["qtype"] == "单选"),
            "errors_multi": sum(1 for q in qids if q in recs and not recs[q]["correct"]
                                and recs[q]["qtype"] == "多选"),
        })

    # ---------- 分组正确率 ----------
    def group_acc(keyfn, groups):
        out = {}
        for m in MODELS:
            out[m] = {}
            for g in groups:
                qs_ = [q for q in qids if keyfn(qmeta[q]) == g]
                c = sum(1 for q in qs_ if raw[m].get(q, {}).get("correct"))
                out[m][g] = {"correct": c, "n": len(qs_),
                             "acc": round(c / len(qs_), 4) if qs_ else None}
        return out

    qtypes = ["单选", "多选"]
    diffs = ["核心", "扩展"]
    domains = sorted({qmeta[q]["domain"] for q in qids})
    qtype_acc = group_acc(lambda q: q["qtype"], qtypes)
    diff_acc = group_acc(lambda q: q["difficulty"], diffs)
    domain_acc = group_acc(lambda q: q["domain"], domains)

    # ---------- 题目级 ----------
    per_question = []
    for q in qids:
        wrong = [m for m in MODELS if not raw[m].get(q, {}).get("correct")]
        preds = Counter(raw[m][q]["pred"] for m in MODELS if q in raw[m] and raw[m][q]["pred"])
        per_question.append({
            "qid": q, "domain": qmeta[q]["domain"], "qtype": qmeta[q]["qtype"],
            "difficulty": qmeta[q]["difficulty"], "answer": qmeta[q]["answer"],
            "n_correct": len(MODELS) - len(wrong), "models_wrong": wrong,
            "pred_summary": "、".join(f"{p}×{c}" for p, c in preds.most_common()),
            "wrong_preds": {m: raw[m][q]["pred"] for m in wrong if raw[m].get(q)},
        })
    hist = Counter(pq["n_correct"] for pq in per_question)
    all_correct = sum(1 for pq in per_question if pq["n_correct"] == len(MODELS))
    consensus_wrong = [pq for pq in per_question if pq["n_correct"] <= 1]

    # ---------- 模型间一致率（预测完全相同的比例）----------
    agree = {}
    for i, m1 in enumerate(MODELS):
        for m2 in MODELS[i + 1:]:
            both = [q for q in qids if q in raw[m1] and q in raw[m2]]
            same = sum(1 for q in both if raw[m1][q]["pred"] == raw[m2][q]["pred"])
            agree[f"{m1}|{m2}"] = round(same / len(both), 4) if both else None

    # ---------- 明细 CSV ----------
    with open(AGG_DIR / "results_all.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["模型", "题号", "题型", "难度", "知识域", "标准答案", "模型答案",
                    "是否正确", "解析成功", "时延s", "completion_tokens", "原始回复(截断)"])
        for m in MODELS:
            for q in qids:
                r = raw[m].get(q)
                if not r:
                    continue
                w.writerow([m, q, qmeta[q]["qtype"], qmeta[q]["difficulty"], qmeta[q]["domain"],
                            qmeta[q]["answer"], r["pred"], int(r["correct"]),
                            int(r.get("parse_ok", True)), r["latency_s"],
                            r.get("completion_tokens"), r.get("raw", "").replace("\n", " ")[:200]])

    # ---------- 与上次测评（bench/，旧题库 126 题）对比 ----------
    old = {}
    old_dir = BENCH_DIR.parent / "bench" / "results"
    if old_dir.exists():
        for m in MODELS:
            p = old_dir / f"{m}.jsonl"
            if not p.exists():
                continue
            recs = []
            with open(p, encoding="utf-8") as f:
                for line in f:
                    try:
                        r = json.loads(line)
                    except Exception:
                        continue
                    if not r.get("error"):
                        recs.append(r)
            if recs:
                old[m] = {
                    "n": len(recs),
                    "accuracy": round(sum(r["correct"] for r in recs) / len(recs), 4),
                    "mean_lat": round(float(np.mean([r["latency_s"] for r in recs])), 2),
                }

    sample_comp = {
        "qtype": dict(Counter(q["qtype"] for q in sample)),
        "difficulty": dict(Counter(q["difficulty"] for q in sample)),
        "domain": dict(Counter(q["domain"] for q in sample)),
    }

    # ---------- 预格式化显示字符串（Typst 端直接引用，避免排版端格式化）----------
    def s1(v):
        return f"{v:.1f}"

    for m in models_stat:
        m["acc_str"] = f"{100 * m['accuracy']:.1f}%"
        m["ci_str"] = f"[{100 * m['ci_lo']:.1f}%, {100 * m['ci_hi']:.1f}%]"
        m["mean_str"] = s1(m["mean_lat"])
        m["median_str"] = s1(m["median_lat"])
        m["p90_str"] = s1(m["p90_lat"])
        m["p95_str"] = s1(m["p95_lat"])
        m["min_str"] = s1(m["min_lat"])
        m["max_str"] = s1(m["max_lat"])
        m["tok_str"] = str(m["median_tokens"]) if m["median_tokens"] is not None else "—"
        m["tps_str"] = s1(m["median_tps"]) if m["median_tps"] is not None else "—"
        m["err_str"] = str(m["errors_single"] + m["errors_multi"])
    for grp in (qtype_acc, diff_acc, domain_acc):
        for m in grp.values():
            for g in m.values():
                g["acc_str"] = "—" if g["acc"] is None else f"{100 * g['acc']:.1f}%"
    for key, v in old.items():
        v["acc_str"] = f"{100 * v['accuracy']:.1f}%"
        v["mean_str"] = s1(v["mean_lat"])
    models_by_acc = sorted(models_stat, key=lambda m: -m["accuracy"])
    models_by_medlat = sorted(models_stat, key=lambda m: m["median_lat"])
    stats = {
        "meta": {
            "date": date.today().isoformat(),
            "n_questions": len(qids), "n_models": len(MODELS),
            "temperature": 0.1, "concurrency": 4, "seed": 20260927,
            "sample_comp": sample_comp,
        },
        "models": models_stat,
        "qtypes": qtypes, "diffs": diffs, "domains": domains,
        "qtype_acc": qtype_acc, "diff_acc": diff_acc, "domain_acc": domain_acc,
        "per_question": per_question,
        "question_hist": {str(k): hist.get(k, 0) for k in range(len(MODELS) + 1)},
        "all_correct": all_correct,
        "consensus_wrong": consensus_wrong,
        "agree": agree,
        "latencies": {m: lat[m] for m in MODELS},
        "old_bench": old,
        "models_by_acc": [m["name"] for m in models_by_acc],
        "models_by_medlat": [m["name"] for m in models_by_medlat],
    }
    with open(AGG_DIR / "stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=1)

    make_charts(stats, sample, raw, qids)
    print_summary(stats)
    print(f"\n输出: {AGG_DIR}/stats.json, {AGG_DIR}/results_all.csv, charts/*.svg")


# ---------------- 图表 ----------------
def make_charts(stats, sample, raw, qids):
    ms = stats["models"]
    names = [m["name"] for m in ms]

    # 1. 总体正确率排名（含 Wilson 置信区间）
    order = sorted(ms, key=lambda x: -x["accuracy"])
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    ys = np.arange(len(order))[::-1]
    for y, m in zip(ys, order):
        ax.errorbar(100 * m["accuracy"], y,
                    xerr=[[100 * (m["accuracy"] - m["ci_lo"])], [100 * (m["ci_hi"] - m["accuracy"])]],
                    fmt="o", color=MODEL_COLORS[m["name"]], capsize=4, markersize=7, lw=1.6)
        ax.text(100 * m["ci_hi"] + 1.0, y, f"{100 * m['accuracy']:.1f}%  ({m['correct']}/{m['n']})",
                va="center", fontsize=10)
    ax.set_yticks(ys, [m["name"] for m in order])
    ax.set_xlim(88, max(100 * m["ci_hi"] + 7.5 for m in ms))
    ax.set_xlabel("正确率（%）与 95% Wilson 置信区间")
    ax.grid(axis="x", ls=":", alpha=0.5)
    fig.savefig(CHARTS_DIR / "overall_accuracy.svg")
    plt.close(fig)

    # 2. 时延统计：mean/median/P95
    order_l = sorted(ms, key=lambda x: x["median_lat"])
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    x = np.arange(len(order_l))
    w = 0.26
    for i, (key, lab) in enumerate([("mean_lat", "均值"), ("median_lat", "中位数"), ("p95_lat", "P95")]):
        vals = [m[key] for m in order_l]
        b = ax.bar(x + (i - 1) * w, vals, w, label=lab,
                   color=["#4C72B0", "#55A868", "#C44E52"][i], alpha=0.88)
        ax.bar_label(b, fmt="%.1f", fontsize=8, padding=1.5)
    ax.set_xticks(x, [m["name"] for m in order_l], rotation=18, ha="right")
    ax.set_ylabel("时延（秒）")
    ax.legend()
    ax.grid(axis="y", ls=":", alpha=0.5)
    fig.savefig(CHARTS_DIR / "latency_summary.svg")
    plt.close(fig)

    # 3. 正确率 vs 中位时延 散点（象限）
    fig, ax = plt.subplots(figsize=(8.2, 5.4))
    xs = [m["median_lat"] for m in ms]
    ys2 = [100 * m["accuracy"] for m in ms]
    sizes = [max(80, (m["median_tokens"] or 0) / 3) for m in ms]
    ax.scatter(xs, ys2, s=sizes, c=[MODEL_COLORS[m["name"]] for m in ms],
               alpha=0.85, edgecolors="white", linewidths=1.2, zorder=3)
    offsets = {"DeepSeek-V4.1-Flash": (8, 6), "GLM-5.3": (8, -14), "GLM-5.3-Flash": (8, 6),
               "GPT-5.6-Sol": (8, 6), "GPT-5.6-Terra": (-10, 8), "Claude-Sonnet-5": (8, 6),
               "Gemini-3.8-Flash": (-30, -20)}
    for m, x0, y0 in zip(ms, xs, ys2):
        dx, dy = offsets.get(m["name"], (8, 6))
        ax.annotate(m["name"], (x0, y0), textcoords="offset points", xytext=(dx, dy), fontsize=9.5)
    med_x = float(np.median(xs))
    med_y = float(np.median(ys2))
    ax.axvline(med_x, ls="--", c="gray", lw=1, alpha=0.6)
    ax.axhline(med_y, ls="--", c="gray", lw=1, alpha=0.6)
    ax.text(0.985, 0.975, "快 且 准（理想区）", transform=ax.transAxes, ha="right", va="top",
            fontsize=10, color="#2a7", fontweight="bold")
    ax.text(0.015, 0.975, "慢 但 准", transform=ax.transAxes, ha="left", va="top",
            fontsize=10, color="#888")
    ax.set_xlabel("中位响应时间（秒，气泡大小=中位输出 token 数）")
    ax.set_ylabel("正确率（%）")
    ax.grid(ls=":", alpha=0.5)
    fig.savefig(CHARTS_DIR / "acc_vs_latency.svg")
    plt.close(fig)

    # 4. 单选/多选正确率
    fig, axes = plt.subplots(1, 2, figsize=(9.4, 4.0), sharey=True)
    for ax, qt in zip(axes, stats["qtypes"]):
        order_q = sorted(ms, key=lambda m: -(m2 := stats["qtype_acc"][m["name"]][qt])["acc"])
        vals = [100 * stats["qtype_acc"][m["name"]][qt]["acc"] for m in order_q]
        b = ax.barh(np.arange(len(order_q))[::-1], vals,
                    color=[MODEL_COLORS[m["name"]] for m in order_q], alpha=0.9)
        for y, m, v in zip(np.arange(len(order_q))[::-1], order_q, vals):
            d = stats["qtype_acc"][m["name"]][qt]
            ax.text(v + 0.3, y, f"{v:.1f}% ({d['correct']}/{d['n']})", va="center", fontsize=9)
        ax.set_yticks(np.arange(len(order_q))[::-1], [m["name"] for m in order_q], fontsize=9)
        ax.set_xlim(80, 104)
        ax.set_title(f"{qt}（n={next(iter(stats['qtype_acc'].values()))[qt]['n']}）", fontsize=11)
        ax.grid(axis="x", ls=":", alpha=0.5)
    axes[0].set_xlabel("正确率（%）")
    axes[1].set_xlabel("正确率（%）")
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "qtype_accuracy.svg")
    plt.close(fig)

    # 5. 核心/扩展 正确率
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    order_d = sorted(ms, key=lambda m: -100 * stats["diff_acc"][m["name"]]["核心"]["acc"])
    x = np.arange(len(order_d))
    w = 0.36
    for i, (df, col) in enumerate(zip(stats["diffs"], ["#4C72B0", "#DD8452"])):
        vals = [100 * stats["diff_acc"][m["name"]][df]["acc"] for m in order_d]
        b = ax.bar(x + (i - 0.5) * w, vals, w, label=df, color=col, alpha=0.88)
        ax.bar_label(b, fmt="%.1f", fontsize=8, padding=1.5)
    ax.set_xticks(x, [m["name"] for m in order_d], rotation=18, ha="right")
    ax.set_ylabel("正确率（%）")
    ax.set_ylim(85, 102)
    ax.legend()
    ax.grid(axis="y", ls=":", alpha=0.5)
    fig.savefig(CHARTS_DIR / "difficulty_accuracy.svg")
    plt.close(fig)

    # 6. 知识域热力图
    doms = stats["domains"]
    mat = np.full((len(doms), len(MODELS)), np.nan)
    for j, m in enumerate(MODELS):
        for i, d in enumerate(doms):
            v = stats["domain_acc"][m][d]
            if v["acc"] is not None:
                mat[i, j] = 100 * v["acc"]
    fig, ax = plt.subplots(figsize=(9.0, 5.2))
    im = ax.imshow(mat, cmap="RdYlGn", vmin=60, vmax=100, aspect="auto")
    ax.set_xticks(range(len(MODELS)), [m.replace("-", "\n", 1) for m in MODELS], fontsize=8.5)
    ax.set_yticks(range(len(doms)), [f"{d}（n={stats['domain_acc']['GLM-5.3'][d]['n']}）" for d in doms],
                  fontsize=9.5)
    for i in range(len(doms)):
        for j in range(len(MODELS)):
            if not math.isnan(mat[i, j]):
                ax.text(j, i, f"{mat[i, j]:.0f}", ha="center", va="center", fontsize=9,
                        color="black" if 75 < mat[i, j] < 99 else "white")
    fig.colorbar(im, ax=ax, shrink=0.85, label="正确率（%）")
    fig.savefig(CHARTS_DIR / "domain_heatmap.svg")
    plt.close(fig)

    # 7. 时延箱线图
    fig, ax = plt.subplots(figsize=(8.6, 4.4))
    data = [stats["latencies"][m] for m in names]
    bp = ax.boxplot(data, tick_labels=names, patch_artist=True, showfliers=True,
                    flierprops={"marker": ".", "markersize": 4, "alpha": 0.5},
                    medianprops={"color": "black", "lw": 1.6}, widths=0.55)
    for patch, m in zip(bp["boxes"], names):
        patch.set_facecolor(MODEL_COLORS[m])
        patch.set_alpha(0.75)
    ax.set_ylabel("时延（秒）")
    plt.setp(ax.get_xticklabels(), rotation=18, ha="right")
    ax.grid(axis="y", ls=":", alpha=0.5)
    fig.savefig(CHARTS_DIR / "latency_box.svg")
    plt.close(fig)

    # 8. 时延 ECDF
    fig, ax = plt.subplots(figsize=(8.2, 4.4))
    for m in MODELS:
        v = np.sort(stats["latencies"][m])
        ax.step(v, np.arange(1, len(v) + 1) / len(v) * 100, where="post",
                color=MODEL_COLORS[m], lw=1.8, label=m)
    ax.set_xlabel("时延（秒）")
    ax.set_ylabel("累计请求比例（%）")
    ax.legend(fontsize=8.5, loc="lower right")
    ax.grid(ls=":", alpha=0.5)
    fig.savefig(CHARTS_DIR / "latency_ecdf.svg")
    plt.close(fig)

    # 9. 每题被答对的模型数分布
    hist = stats["question_hist"]
    fig, ax = plt.subplots(figsize=(8.2, 3.8))
    ks = list(range(len(MODELS) + 1))
    vals = [hist.get(str(k), 0) for k in ks]
    cols = ["#C44E52" if k <= 1 else "#4C72B0" if k == len(MODELS) else "#7f9fc9" for k in ks]
    b = ax.bar(ks, vals, color=cols, alpha=0.9)
    ax.bar_label(b, fontsize=9)
    ax.set_xticks(ks, [str(k) for k in ks])
    ax.set_xlabel("一道题被多少个模型答对（共 7 个模型）")
    ax.set_ylabel("题数")
    ax.grid(axis="y", ls=":", alpha=0.5)
    fig.savefig(CHARTS_DIR / "question_consensus.svg")
    plt.close(fig)

    # 10. 各模型错误构成（单选/多选）+ 一致率热力图
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.6, 4.6), width_ratios=[1, 1.15])
    order_e = sorted(ms, key=lambda m: m["errors_single"] + m["errors_multi"])
    x = np.arange(len(order_e))
    es = [m["errors_single"] for m in order_e]
    em = [m["errors_multi"] for m in order_e]
    ax1.bar(x, es, 0.6, label="单选错误", color="#4C72B0")
    ax1.bar(x, em, 0.6, bottom=es, label="多选错误", color="#DD8452")
    for xi, (a, b_) in zip(x, zip(es, em)):
        if a + b_:
            ax1.text(xi, a + b_ + 0.12, str(a + b_), ha="center", fontsize=9)
    ax1.set_xticks(x, [m["name"] for m in order_e], rotation=18, ha="right", fontsize=8.5)
    ax1.set_ylabel("错误题数")
    ax1.set_title("(a) 各模型错误构成", fontsize=11)
    ax1.legend()
    ax1.grid(axis="y", ls=":", alpha=0.5)

    nM = len(MODELS)
    amat = np.ones((nM, nM))
    for key, v in stats["agree"].items():
        i, j = MODELS.index(key.split("|")[0]), MODELS.index(key.split("|")[1])
        amat[i, j] = amat[j, i] = v if v is not None else 0
    im = ax2.imshow(amat * 100, cmap="viridis", vmin=80, vmax=100)
    ax2.set_xticks(range(nM), MODELS, rotation=40, ha="right", fontsize=8)
    ax2.set_yticks(range(nM), MODELS, fontsize=8)
    for i in range(nM):
        for j in range(nM):
            ax2.text(j, i, f"{amat[i, j] * 100:.0f}", ha="center", va="center", fontsize=7.5,
                     color="white" if amat[i, j] * 100 < 92 else "black")
    ax2.set_title("(b) 模型两两作答一致率（%）", fontsize=11)
    fig.colorbar(im, ax=ax2, shrink=0.85)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / "errors_agreement.svg")
    plt.close(fig)

    # 11. 输出 token 与吞吐
    fig, ax = plt.subplots(figsize=(8.6, 4.2))
    order_t = sorted(ms, key=lambda m: -(m["median_tps"] or 0))
    x = np.arange(len(order_t))
    w = 0.38
    b1 = ax.bar(x - w / 2, [m["median_tps"] or 0 for m in order_t], w,
                label="中位吞吐（token/s）", color="#55A868")
    ax2b = ax.twinx()
    b2 = ax2b.bar(x + w / 2, [m["median_tokens"] or 0 for m in order_t], w,
                  label="中位输出 token 数", color="#8172B3", alpha=0.85)
    ax.bar_label(b1, fmt="%.0f", fontsize=8, padding=1.5)
    ax2b.bar_label(b2, fmt="%.0f", fontsize=8, padding=1.5)
    ax.set_xticks(x, [m["name"] for m in order_t], rotation=18, ha="right")
    ax.set_ylabel("吞吐（token/s）")
    ax2b.set_ylabel("输出 token 数")
    h1, l1 = ax.get_legend_handles_labels()
    h2, l2 = ax2b.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, loc="upper right", fontsize=9)
    ax.grid(axis="y", ls=":", alpha=0.5)
    fig.savefig(CHARTS_DIR / "throughput.svg")
    plt.close(fig)


def print_summary(stats):
    print(f"{'模型':<22}{'正确率':>8}{'单选':>10}{'多选':>10}{'均延':>7}{'中位':>7}{'P95':>7}")
    for m in stats["models"]:
        n = stats["meta"]["n_questions"]
        q = stats["qtype_acc"][m["name"]]
        print(f"{m['name']:<22}{100 * m['accuracy']:>7.1f}%"
              f"{100 * q['单选']['acc']:>8.1f}% ({q['单选']['correct']:>2}/{q['单选']['n']})"
              f"{100 * q['多选']['acc']:>8.1f}% ({q['多选']['correct']:>2}/{q['多选']['n']})"
              f"{m['mean_lat']:>7.1f}{m['median_lat']:>7.1f}{m['p95_lat']:>7.1f}")


if __name__ == "__main__":
    main()
