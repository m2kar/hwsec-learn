#!/usr/bin/env python3
"""多选题投票集成模拟：DeepSeek-V4.1-Flash + GLM-5.3 + Claude-Sonnet-5 三模型逐选项投票。

规则：对每个选项，≥2 个模型选择则入选，否则不选。纯离线，基于 results/*.jsonl。
"""
import json
from pathlib import Path

RESULTS = Path(__file__).resolve().parent / "results"
TRIO = ["DeepSeek-V4.1-Flash", "GLM-5.3", "Claude-Sonnet-5"]
ALL7 = ["DeepSeek-V4.1-Flash", "GLM-5.3", "GLM-5.3-Flash", "GPT-5.6-Sol",
        "GPT-5.6-Terra", "Claude-Sonnet-5", "Gemini-3.8-Flash"]


def load(m):
    recs = [json.loads(l) for l in open(RESULTS / f"{m}.jsonl", encoding="utf-8") if l.strip()]
    return {r["qid"]: r for r in recs}


def main():
    data = {m: load(m) for m in ALL7}
    mc_qids = sorted(q for q, r in data["DeepSeek-V4.1-Flash"].items() if r["qtype"] == "多选")
    n = len(mc_qids)
    print(f"多选题共 {n} 道；投票模型：{' + '.join(TRIO)}\n")

    def acc(preds_by_q):
        return sum(1 for q in mc_qids if preds_by_q[q] == data[TRIO[0]][q]["truth"])

    ens_pred, changed = {}, []
    for q in mc_qids:
        truth = data[TRIO[0]][q]["truth"]
        preds = {m: data[m][q]["pred"] for m in TRIO}
        votes = {L: sum(L in preds[m] for m in TRIO) for L in "ABCD"}
        ens = "".join(L for L in "ABCD" if votes[L] >= 2)
        ens_pred[q] = ens
        if ens != truth and any(preds[m] == truth for m in TRIO):
            changed.append(("票毁正确", q, preds, votes, ens, truth))
        elif ens == truth and any(preds[m] != truth for m in TRIO):
            changed.append(("票回正确", q, preds, votes, ens, truth))

    print(f"{'方案':<28} 多选正确/44  正确率")
    print("-" * 52)
    for m in TRIO:
        k = acc({q: data[m][q]["pred"] for q in mc_qids})
        print(f"{m:<28} {k:>6}/44   {k/n*100:.1f}%")
    k = acc(ens_pred)
    print(f"{'三模型逐选项投票(≥2/3)':<24} {k:>6}/44   {k/n*100:.1f}%")
    # 对照：7 模型逐选项多数投票(≥4/7)
    ens7 = {}
    for q in mc_qids:
        votes = {L: sum(L in data[m][q]["pred"] for m in ALL7) for L in "ABCD"}
        ens7[q] = "".join(L for L in "ABCD" if votes[L] >= 4)
    k7 = acc(ens7)
    print(f"{'对照:7模型逐选项投票(≥4/7)':<23} {k7:>6}/44   {k7/n*100:.1f}%")

    print(f"\n与单模型相比发生翻转的题目（{len(changed)} 道）:")
    for kind, q, preds, votes, ens, truth in changed:
        pv = " ".join(f"{m.split('-')[0][:4]}={preds[m] or '空'}" for m in TRIO)
        mark = "✓" if ens == truth else "✗"
        print(f"  {q} [{kind}] {pv} | 票数 {votes} → 集成 {ens} (正确 {truth}) {mark}")

    print("\n投票后仍答错的题目:")
    for q in mc_qids:
        truth = data[TRIO[0]][q]["truth"]
        if ens_pred[q] != truth:
            preds = {m: data[m][q]["pred"] for m in TRIO}
            votes = {L: sum(L in preds[m] for m in TRIO) for L in "ABCD"}
            print(f"  {q} 三家: {' '.join(preds[m] or '空' for m in TRIO)} | 票数 {votes} "
                  f"→ 集成 {ens_pred[q] or '空'} (正确 {truth})")

    # 整卷口径
    for m in TRIO:
        total = sum(1 for r in data[m].values() if r["correct"])
    trio_singles = {m: {q: data[m][q] for q in data[m] if data[m][q]["qtype"] == "单选"} for m in TRIO}
    print("\n整卷口径（82 单选取三模型中正确率最高者视为该路输出 + 44 多选投票）:")
    best = max(TRIO, key=lambda m: sum(1 for r in trio_singles[m].values() if r["correct"]))
    s = sum(1 for r in trio_singles[best].values() if r["correct"])
    print(f"  单选最优 {best}: {s}/82；多选投票 {k}/44 → 合计 {s + k}/126 = {(s + k) / 126 * 100:.1f}%")


if __name__ == "__main__":
    main()
