#!/usr/bin/env python3
"""装配校验工具：把 bank_batches/part_*.jsonl 中人工定稿的题目装配成最终 CSV。
只做格式装配与质量统计，不生成任何题目内容。"""
import csv, json, sys
from pathlib import Path
from collections import Counter

ROOT = Path(__file__).parent
parts = sorted(ROOT.glob("part_*.jsonl"))
if not parts:
    sys.exit("未找到 part_*.jsonl")
rows, seen = [], set()
for p in parts:
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        q = json.loads(line)
        assert q["id"] not in seen, f"重复题号 {q['id']}"
        seen.add(q["id"])
        rows.append(q)

BANNED = ["只凭宣传", "只要设备处于内网", "其余选项混淆了安全目标", "以上都对", "以上都不对", "以上都正确"]
dup_opts = {}
for q in rows:
    qid, t = q["id"], q["type"]
    assert t in ("单选", "多选"), (qid, t)
    assert q["domain"] and q["diff"] in ("核心", "扩展"), (qid, q["domain"], q["diff"])
    assert q["stem"] and q["exp"] and q["tag"], qid
    opts = (q["opts"] + [""] * 7)[:7]
    n = len([o for o in opts if o])
    assert opts == [o for o in opts if o] + [""] * (7 - n), (qid, "选项必须连续填充")
    ans = q["ans"]
    assert ans and set(ans) <= set("ABCDEFG") and list(ans) == sorted(set(ans)), (qid, ans)
    assert all(opts[ord(a) - 65] for a in ans), (qid, "答案指向空选项")
    if t == "单选":
        assert len(ans) == 1 and n == 5 and not opts[5] and not opts[6], (qid, n, ans)
    else:
        assert 2 <= len(ans) <= 4 and n == 6 and not opts[6], (qid, n, ans)
    for b in BANNED:
        assert b not in q["exp"] and all(b not in o for o in opts), (qid, f"出现禁用语: {b}")
    for o in opts:
        if o:
            dup_opts.setdefault(o, []).append(qid)
    for a in ans:
        pass

dups = {o: ids for o, ids in dup_opts.items() if len(ids) > 2}
if dups:
    print(f"警告：{len(dups)} 条选项文本在 3 题以上复用：")
    for o, ids in list(dups.items())[:10]:
        print("  ", ids, o[:40])

FINAL = "--final" in sys.argv
ids = [r["id"] for r in rows]
assert len(ids) == len(set(ids)), "存在重复题号"
if FINAL:
    assert len(ids) == 600, f"题量 {len(ids)} != 600"
    missing = [f"{p}{i:03d}" for p, lo, hi in (("Z", 1, 200), ("Y", 1, 400))
               for i in range(lo, hi + 1) if f"{p}{i:03d}" not in seen]
    assert not missing, f"缺题: {missing[:20]}"

rows.sort(key=lambda r: (0 if r["id"].startswith("Z") else 1, r["id"]))
HEADERS = ["题号", "题型", "知识域", "难度", "题干", *[f"选项{x}" for x in "ABCDEFG"], "答案", "解析", "考点"]
out = ROOT.parent / "硬件安全题库2.csv"
with out.open("w", encoding="utf-8-sig", newline="") as f:
    w = csv.writer(f, quoting=csv.QUOTE_ALL)
    w.writerow(HEADERS)
    for q in rows:
        w.writerow([q["id"], q["type"], q["domain"], q["diff"], q["stem"],
                    *((q["opts"] + [""] * 7)[:7]), q["ans"], q["exp"], q["tag"]])

print("装配完成:", out)
print("总题数:", len(rows))
print("按域:", dict(Counter(r["domain"] for r in rows)))
print("按难度:", dict(Counter(r["diff"] for r in rows)))
print("按题型:", dict(Counter(r["type"] for r in rows)))
print("单选答案分布:", dict(Counter(r["ans"] for r in rows if r["type"] == "单选")))
