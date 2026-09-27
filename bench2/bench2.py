#!/usr/bin/env python3
"""硬件安全题库2 多模型评测：正确率 + 响应时间。

与 bench/bench.py 的区别：
  - 题库改为 硬件安全题库2.csv（600 题），从中随机抽取 100 题（固定种子，抽样结果存
    sample_questions.json，重跑复用同一份，保证断点续跑与可复现）
  - 选项支持 A–G（只列非空选项）
  - 结果写入 bench2/results/<model>.jsonl

用法:
  python3 bench2.py                    # 跑全部 7 个模型 × 抽样的 100 题
  python3 bench2.py --models GLM-5.3   # 只跑指定模型
  python3 bench2.py --limit 2          # 每个模型只跑前 2 题（冒烟测试）
  python3 bench2.py --resample 20260927  # 重新抽样（会覆盖 sample_questions.json）
"""
import argparse
import csv
import json
import os
import random
import re
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

API_URL = "https://llmapi.isrc.ac.cn/v1/chat/completions"

ALL_MODELS = [
    "DeepSeek-V4.1-Flash",
    "GLM-5.3",
    "GLM-5.3-Flash",
    "GPT-5.6-Sol",
    "GPT-5.6-Terra",
    "Claude-Sonnet-5",
    "Gemini-3.8-Flash",
]

BENCH_DIR = Path(__file__).resolve().parent
CSV_PATH = BENCH_DIR.parent / "硬件安全题库2.csv"
SAMPLE_PATH = BENCH_DIR / "sample_questions.json"
RESULTS_DIR = BENCH_DIR / "results"
RESULTS_FULL_DIR = BENCH_DIR / "results_full"
RESULTS_DIR.mkdir(exist_ok=True)

SAMPLE_SEED = 20260927
SAMPLE_N = 100

SYSTEM_PROMPT = "你是硬件安全领域专家。回答选择题时，只输出正确选项的字母，不要输出任何解释、标点或其他文字。"
TEMPERATURE = 0.1
TIMEOUT = 300
MAX_RETRY = 5


def load_api_key() -> str:
    key = os.environ.get("HWSEC_LLM_API_KEY", "").strip()
    if not key:
        key_file = BENCH_DIR.parent / "bench" / "api_key.txt"
        if key_file.exists():
            key = key_file.read_text().strip()
    if not key:
        sys.exit("缺少 API 密钥：请设置环境变量 HWSEC_LLM_API_KEY，或将密钥写入 bench/api_key.txt（已被 .gitignore 排除）")
    return key


API_KEY = load_api_key()


def load_bank():
    with open(CSV_PATH, newline="", encoding="utf-8-sig") as f:
        rows = list(csv.DictReader(f))
    qs = []
    for r in rows:
        options = {k: (r.get(f"选项{k}") or "").strip() for k in "ABCDEFG"}
        options = {k: v for k, v in options.items() if v}
        qs.append({
            "qid": r["题号"].strip(),
            "qtype": r["题型"].strip(),
            "domain": r["知识域"].strip(),
            "difficulty": r["难度"].strip(),
            "stem": r["题干"].strip(),
            "options": options,
            "answer": re.sub(r"[^A-G]", "", r["答案"].strip().upper()),
        })
    return qs


def make_sample(bank, seed=SAMPLE_SEED, n=SAMPLE_N, force=False):
    """随机抽取 n 题；抽样落盘后重跑复用同一份。"""
    if SAMPLE_PATH.exists() and not force:
        with open(SAMPLE_PATH, encoding="utf-8") as f:
            return json.load(f)
    rng = random.Random(seed)
    sample = sorted(rng.sample(bank, n), key=lambda q: q["qid"])
    with open(SAMPLE_PATH, "w", encoding="utf-8") as f:
        json.dump(sample, f, ensure_ascii=False, indent=1)
    return sample


def build_prompt(q):
    keys = sorted(q["options"].keys())
    lines = []
    if q["qtype"] == "单选":
        lines.append(f"以下是单项选择题，请只输出一个正确选项的字母（{'、'.join(keys)} 中选一个）。")
    else:
        lines.append("以下是多项选择题，请只输出所有正确选项的字母组合，按字母顺序排列（例如 ABD）。")
    lines.append("")
    lines.append(q["stem"])
    for k in keys:
        lines.append(f"{k}. {q['options'][k]}")
    return "\n".join(lines)


def extract_letters(text, qtype):
    """从模型回复中提取选项字母（A–G）。优先取加粗结论，避免解释文字里的字母污染。"""
    if not text:
        return "", False
    t = text.strip()

    def norm(s):
        return "".join(sorted(set(re.sub(r"[^A-G]", "", s.upper()))))

    # 1) 加粗结论 **ABC**（部分模型先复述选项、最后加粗给答案）
    m = re.findall(r"\*\*([A-G][A-G\s,，、]*)\*\*", t)
    if m:
        letters = norm(m[-1])
        if letters:
            return letters, True
    # 2) 整个回复就是字母（可带空格/逗号/顿号/星号分隔）
    whole = re.sub(r"[\s,，、*]+", "", t).upper()
    if re.fullmatch(r"[A-G]{1,7}", whole):
        return norm(whole), True
    # 3) “答案/选”等提示词后面的字母，取最后一处
    matches = re.findall(r"(?:答案|答|选|选择|正确选项|正确答案)[^\nA-G]{0,6}([A-G][A-G\s,，、\*]*)",
                         t, flags=re.IGNORECASE)
    if matches:
        letters = norm(matches[-1])
        if letters:
            return letters, True
    # 4) 兜底：回复中出现的全部字母
    letters = re.sub(r"[^A-G]", "", t.upper())
    if letters:
        return "".join(sorted(set(letters))), False
    return "", False


def call_model(model, prompt, session):
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": TEMPERATURE,
    }
    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    last_err = None
    for attempt in range(1, MAX_RETRY + 1):
        t0 = time.perf_counter()
        try:
            resp = session.post(API_URL, json=payload, headers=headers, timeout=TIMEOUT)
            elapsed = time.perf_counter() - t0
            if resp.status_code == 200:
                data = resp.json()
                msg = data["choices"][0]["message"]
                content = msg.get("content") or ""
                usage = data.get("usage", {})
                return {
                    "ok": True, "latency_s": round(elapsed, 3),
                    "content": content, "usage": usage, "error": None,
                }
            last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
        except Exception as e:  # noqa: BLE001
            elapsed = time.perf_counter() - t0
            last_err = f"{type(e).__name__}: {e}"
        # 指数退避重试
        time.sleep(min(2 ** attempt, 30))
    return {"ok": False, "latency_s": None, "content": "", "usage": {}, "error": last_err}


def run_model(model, questions, concurrency, results_dir=None):
    out_path = (results_dir or RESULTS_DIR) / f"{model}.jsonl"
    done = set()
    if out_path.exists():
        with open(out_path, encoding="utf-8") as f:
            for line in f:
                try:
                    done.add(json.loads(line)["qid"])
                except Exception:  # noqa: BLE001
                    pass
    todo = [q for q in questions if q["qid"] not in done]
    print(f"[{model}] 已完成 {len(done)}，待跑 {len(todo)}", flush=True)
    if not todo:
        return

    lock = threading.Lock()
    session = requests.Session()
    session.headers["Authorization"] = f"Bearer {API_KEY}"

    def work(q):
        rec = call_model(model, build_prompt(q), session)
        pred, parse_ok = extract_letters(rec["content"], q["qtype"])
        correct = (pred == q["answer"])
        out = {
            "qid": q["qid"], "qtype": q["qtype"], "domain": q["domain"],
            "difficulty": q["difficulty"], "truth": q["answer"],
            "pred": pred, "parse_ok": parse_ok, "correct": correct,
            "latency_s": rec["latency_s"],
            "prompt_tokens": rec["usage"].get("prompt_tokens"),
            "completion_tokens": rec["usage"].get("completion_tokens"),
            "error": rec["error"], "raw": rec["content"][:500],
        }
        with lock:
            with open(out_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(out, ensure_ascii=False) + "\n")
        return out

    n_ok = n_fail = 0
    with ThreadPoolExecutor(max_workers=concurrency) as ex:
        futs = {ex.submit(work, q): q for q in todo}
        for fut in as_completed(futs):
            r = fut.result()
            if r["error"]:
                n_fail += 1
                print(f"[{model}] {r['qid']} 失败: {r['error']}", flush=True)
            else:
                n_ok += 1
                mark = "√" if r["correct"] else "×"
                print(f"[{model}] {r['qid']} {mark} pred={r['pred'] or '-'} truth={r['truth']} "
                      f"{r['latency_s']}s ({n_ok + n_fail}/{len(todo)})", flush=True)
    print(f"[{model}] 完成：成功 {n_ok}，失败 {n_fail}", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--models", nargs="*", default=ALL_MODELS)
    ap.add_argument("--concurrency", type=int, default=4, help="每个模型的并发请求数")
    ap.add_argument("--limit", type=int, default=0, help="每个模型只跑前 N 题（0=全部）")
    ap.add_argument("--resample", action="store_true", help="忽略已有抽样，重新随机抽取")
    ap.add_argument("--all", action="store_true", help="跑全库 600 题（结果写入 results_full/，与抽样结果分离）")
    args = ap.parse_args()

    if args.all:
        questions = load_bank()
        results_dir = RESULTS_FULL_DIR
        results_dir.mkdir(exist_ok=True)
    else:
        questions = make_sample(load_bank(), force=args.resample)
        results_dir = RESULTS_DIR
    if args.limit:
        questions = questions[: args.limit]
    print(f"题数 {len(questions)}；模型 {len(args.models)} 个；"
          f"temperature={TEMPERATURE}；每模型并发 {args.concurrency}"
          f"{'；全库模式' if args.all else ''}", flush=True)
    t0 = time.time()
    # 各模型并行推进，模型内部再按并发数跑题
    threads = []
    for m in args.models:
        th = threading.Thread(target=run_model, args=(m, questions, args.concurrency, results_dir))
        th.start()
        threads.append(th)
    for th in threads:
        th.join()
    print(f"全部完成，总耗时 {time.time() - t0:.0f}s", flush=True)


if __name__ == "__main__":
    main()
