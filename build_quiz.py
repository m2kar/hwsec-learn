#!/usr/bin/env python3
"""从 硬件安全题库.csv 生成单文件刷题网页 硬件安全刷题.html"""
import csv, json, html

CSV = "硬件安全题库.csv"
OUT = "quiz/index.html"

questions = []
with open(CSV, encoding="utf-8-sig") as f:
    for r in csv.DictReader(f):
        questions.append({
            "id": r["题号"], "type": r["题型"], "domain": r["知识域"],
            "diff": r["难度"], "stem": r["题干"],
            "opts": [r["选项A"], r["选项B"], r["选项C"], r["选项D"]],
            "ans": r["答案"], "exp": r["解析"], "tag": r["考点"],
        })

data_js = json.dumps(questions, ensure_ascii=False)

page = """<!DOCTYPE html>
<html lang="zh">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>硬件安全刷题</title>
<script>(function(){var t=null;try{t=localStorage.getItem("theme")}catch(e){}if(!t)t=window.matchMedia&&matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";document.documentElement.dataset.theme=t;})();</script>
<style>
:root { --accent:#C7000B; --accentT:#C7000B; --blue:#1F4E79; --bg:#f7f5f2; --card:#fff; --text:#222; --muted:#666; --line:#e3e0dc; --optbg:#fafaf8; --selbg:#eef4fa; --okbg:#eef8f0; --okline:#2e8b57; --badbg:#fdf0ef; --badgebg:#f0ece8; --badgetext:#666; --warnbg:#fff3e0; --warntext:#b26a00; color-scheme:light; }
:root[data-theme="dark"] { --accent:#e5483d; --accentT:#ff6b60; --blue:#8ab8e8; --bg:#14161a; --card:#1d2026; --text:#d6d3cd; --muted:#9a968f; --line:#34383f; --optbg:#23262c; --selbg:#20304a; --okbg:#1d3226; --okline:#4caf7d; --badbg:#3a2020; --badgebg:#2a2d33; --badgetext:#9a968f; --warnbg:#382c16; --warntext:#d8a04a; color-scheme:dark; }
* { box-sizing:border-box; }
body { margin:0; font-family:"PingFang SC","Microsoft YaHei",system-ui,sans-serif; background:var(--bg); color:var(--text); }
header { position:relative; background:var(--card); border-bottom:3px solid var(--accent); padding:14px 20px; }
h1 { margin:0 0 8px; font-size:20px; color:var(--accentT); }
#themeBtn { position:absolute; top:14px; right:20px; font-size:12px; padding:5px 12px; border:1px solid var(--line); border-radius:14px; background:var(--optbg); color:var(--text); cursor:pointer; }
#stats { font-size:13px; color:var(--muted); display:flex; gap:16px; flex-wrap:wrap; }
#stats b { color:var(--blue); }
#controls { display:flex; gap:10px; flex-wrap:wrap; align-items:center; padding:12px 20px; background:var(--card); border-bottom:1px solid var(--line); }
#controls select, #controls button { font-size:13px; padding:6px 10px; border:1px solid var(--line); border-radius:6px; background:var(--card); color:var(--text); }
#controls button { cursor:pointer; }
#controls .primary { background:var(--accent); color:#fff; border-color:var(--accent); }
#controls .ghost { color:var(--muted); border:none; background:none; text-decoration:underline; }
main { max-width:760px; margin:20px auto; padding:0 16px; }
.card { background:var(--card); border:1px solid var(--line); border-radius:10px; padding:18px 20px; box-shadow:0 1px 3px rgba(0,0,0,.08); }
.badges { display:flex; gap:8px; flex-wrap:wrap; margin-bottom:10px; }
.badge { font-size:12px; padding:2px 8px; border-radius:10px; background:var(--badgebg); color:var(--badgetext); }
.badge.type { background:var(--badgebg); color:var(--accentT); font-weight:600; }
.badge.diff-挑战 { background:var(--warnbg); color:var(--warntext); }
#pos { font-size:12px; color:var(--muted); margin-bottom:6px; }
#stem { font-size:16px; line-height:1.6; margin:0 0 14px; font-weight:600; }
.opt { display:block; width:100%; text-align:left; margin:8px 0; padding:10px 12px; border:1.5px solid var(--line); border-radius:8px; background:var(--optbg); color:var(--text); font-size:14.5px; line-height:1.5; cursor:pointer; }
.opt:hover { border-color:var(--muted); }
.opt.sel { border-color:var(--blue); background:var(--selbg); }
.opt.right { border-color:var(--okline); background:var(--okbg); }
.opt.wrongpick { border-color:var(--accent); background:var(--badbg); }
.opt.disabled { cursor:default; }
.letter { font-weight:700; margin-right:6px; color:var(--blue); }
#feedback { margin-top:14px; padding:12px 14px; border-radius:8px; font-size:14px; line-height:1.7; display:none; }
#feedback.ok { background:var(--okbg); border-left:4px solid var(--okline); }
#feedback.bad { background:var(--badbg); border-left:4px solid var(--accent); }
#feedback .verdict { font-weight:700; }
#exp { margin-top:8px; color:var(--text); }
#nav { display:flex; gap:10px; margin-top:16px; }
#nav button { font-size:14px; padding:9px 22px; border-radius:8px; border:none; cursor:pointer; }
#submit { background:var(--blue); color:#fff; }
#next { background:var(--accent); color:#fff; }
#summary { text-align:center; padding:34px 20px; }
#summary h2 { color:var(--accentT); }
#summary .nums { font-size:15px; line-height:2; color:var(--text); }
#summary button { margin:8px; font-size:14px; padding:9px 20px; border:none; border-radius:8px; background:var(--blue); color:#fff; cursor:pointer; }
#summary button.red { background:var(--accent); }
.hint { font-size:12px; color:var(--muted); margin-top:10px; }
</style>
</head>
<body>
<header>
  <h1>硬件安全刷题</h1>
  <div id="stats">
    <span>本次已答 <b id="stAnswered">0</b></span>
    <span>答对 <b id="stCorrect">0</b></span>
    <span>正确率 <b id="stRate">–</b></span>
    <span>模拟得分 <b id="stScore">0</b> 分</span>
    <span>错题本 <b id="stWrong">0</b></span>
    <button id="themeBtn" title="切换深色 / 浅色（默认跟随系统）">☾ 深色</button>
  </div>
</header>
<div id="controls">
  <select id="mode">
    <option value="seq">顺序刷题</option>
    <option value="rand">随机刷题</option>
    <option value="wrong">错题重刷</option>
  </select>
  <select id="domain"><option value="">全部知识域</option></select>
  <select id="qtype"><option value="">全部题型</option><option>单选</option><option>多选</option></select>
  <select id="diff"><option value="">全部难度</option><option>基础</option><option>进阶</option><option>挑战</option></select>
  <button id="startBtn" class="primary">开始 / 重置</button>
  <button id="clearWrong" class="ghost">清空错题本</button>
</div>
<main>
  <div id="quiz" style="display:none">
    <div class="card">
      <div id="pos"></div>
      <div class="badges" id="badges"></div>
      <p id="stem"></p>
      <div id="opts"></div>
      <div id="feedback"></div>
      <div class="hint" id="hint"></div>
    </div>
    <div id="nav">
      <button id="submitBtn">确认答案</button>
      <button id="nextBtn" style="display:none">下一题</button>
    </div>
  </div>
  <div id="summary" class="card" style="display:none"></div>
</main>
<script>
const QUESTIONS = __DATA__;
const KEY_WRONG = "hwsec_wrong_v1";
const $ = id => document.getElementById(id);
let wrongBook = new Set(JSON.parse(localStorage.getItem(KEY_WRONG) || "[]"));
let queue = [], idx = 0, picked = new Set(), submitted = false;
let stats = { answered: 0, correct: 0, score: 0 };
let mode = "seq";

function saveWrong() {
  localStorage.setItem(KEY_WRONG, JSON.stringify([...wrongBook]));
  $("stWrong").textContent = wrongBook.size;
}
function renderStats() {
  $("stAnswered").textContent = stats.answered;
  $("stCorrect").textContent = stats.correct;
  $("stRate").textContent = stats.answered ? Math.round(stats.correct / stats.answered * 100) + "%" : "–";
  $("stScore").textContent = stats.score;
}
function shuffle(a) { for (let i = a.length - 1; i > 0; i--) { const j = Math.floor(Math.random() * (i + 1)); [a[i], a[j]] = [a[j], a[i]]; } return a; }
function buildPool() {
  const domain = $("domain").value, qtype = $("qtype").value, diff = $("diff").value;
  let pool = QUESTIONS.filter(q =>
    (!domain || q.domain === domain) && (!qtype || q.type === qtype) && (!diff || q.diff === diff));
  if (mode === "wrong") pool = pool.filter(q => wrongBook.has(q.id));
  if (mode === "rand") shuffle(pool);
  return pool;
}
function start() {
  mode = $("mode").value;
  queue = buildPool();
  idx = 0; stats = { answered: 0, correct: 0, score: 0 };
  renderStats();
  $("summary").style.display = "none";
  if (!queue.length) {
    $("quiz").style.display = "none";
    $("summary").style.display = "block";
    $("summary").innerHTML = "<h2>没有符合条件的题目</h2><div class='nums'>" +
      (mode === "wrong" ? "错题本是空的，先去刷题吧。" : "请调整筛选条件。") + "</div>";
    return;
  }
  $("quiz").style.display = "block";
  render();
}
function render() {
  const q = queue[idx];
  picked = new Set(); submitted = false;
  $("pos").textContent = "第 " + (idx + 1) + " / " + queue.length + " 题";
  $("badges").innerHTML =
    "<span class='badge type'>" + q.type + "</span>" +
    "<span class='badge'>" + q.domain + "</span>" +
    "<span class='badge diff-" + q.diff + "'>" + q.diff + "</span>" +
    "<span class='badge'>" + q.id + "</span>";
  $("stem").textContent = q.stem;
  const box = $("opts");
  box.innerHTML = "";
  "ABCD".split("").forEach((L, i) => {
    const b = document.createElement("button");
    b.className = "opt"; b.dataset.letter = L;
    b.innerHTML = "<span class='letter'>" + L + ".</span>" + q.opts[i];
    b.onclick = () => pick(L, b);
    box.appendChild(b);
  });
  $("feedback").style.display = "none";
  $("submitBtn").style.display = q.type === "多选" ? "inline-block" : "none";
  $("nextBtn").style.display = "none";
  $("hint").textContent = q.type === "单选" ? "单击选项即确认判分。" : "多选题：勾选全部正确选项后确认（需完全选对才得分）。";
}
function pick(L, btn) {
  if (submitted) return;
  const q = queue[idx];
  if (q.type === "单选") {
    picked = new Set([L]);
    document.querySelectorAll(".opt").forEach(o => o.classList.remove("sel"));
    btn.classList.add("sel");
    submit();
  } else {
    if (picked.has(L)) { picked.delete(L); btn.classList.remove("sel"); }
    else { picked.add(L); btn.classList.add("sel"); }
  }
}
function submit() {
  if (submitted) return;
  if (!picked.size) { alert("请先选择答案"); return; }
  const q = queue[idx];
  submitted = true;
  const ansSet = new Set(q.ans.split(""));
  const isRight = picked.size === ansSet.size && [...picked].every(x => ansSet.has(x));
  stats.answered++;
  if (isRight) {
    stats.correct++;
    stats.score += q.type === "单选" ? 2 : 3;
    if (mode === "wrong") { wrongBook.delete(q.id); }
  } else {
    wrongBook.add(q.id);
  }
  saveWrong(); renderStats();
  document.querySelectorAll(".opt").forEach(o => {
    const L = o.dataset.letter;
    o.classList.add("disabled");
    if (ansSet.has(L)) o.classList.add("right");
    else if (picked.has(L)) o.classList.add("wrongpick");
  });
  const fb = $("feedback");
  fb.className = isRight ? "ok" : "bad";
  fb.style.display = "block";
  fb.innerHTML = "<div class='verdict'>" + (isRight ? "回答正确 +" + (q.type === "单选" ? 2 : 3) + " 分"
      : "回答错误　正确答案：" + q.ans + (mode !== "wrong" ? "　（已加入错题本）" : "")) +
    "</div><div id='exp'><b>解析：</b>" + q.exp + "　<b>考点：</b>" + q.tag + "</div>";
  $("submitBtn").style.display = "none";
  const next = $("nextBtn");
  next.style.display = "inline-block";
  next.textContent = idx + 1 >= queue.length ? "查看成绩" : "下一题";
}
function summary() {
  $("quiz").style.display = "none";
  const s = $("summary");
  s.style.display = "block";
  const rate = stats.answered ? Math.round(stats.correct / stats.answered * 100) : 0;
  s.innerHTML = "<h2>本轮成绩</h2><div class='nums'>" +
    "共 " + queue.length + " 题　|　已答 " + stats.answered + " 题　|　答对 " + stats.correct + " 题<br>" +
    "正确率 " + rate + "%　|　模拟得分 " + stats.score + " 分<br>" +
    "错题本现有 " + wrongBook.size + " 题</div>" +
    "<button onclick='start()'>再刷一遍（同筛选）</button>" +
    "<button class='red' onclick='startWrong()'>重刷错题本</button>";
}
function startWrong() { $("mode").value = "wrong"; start(); }
$("submitBtn").onclick = submit;
$("nextBtn").onclick = () => { idx++; if (idx >= queue.length) summary(); else render(); };
$("startBtn").onclick = start;
$("clearWrong").onclick = () => {
  if (wrongBook.size && confirm("确定清空全部错题记录？")) { wrongBook.clear(); saveWrong(); }
};
function effectiveTheme() {
  return document.documentElement.dataset.theme ||
    (window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light");
}
function updateThemeBtn() {
  $("themeBtn").textContent = effectiveTheme() === "dark" ? "☀ 浅色" : "☾ 深色";
}
$("themeBtn").onclick = () => {
  const system = window.matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light";
  const next = effectiveTheme() === "dark" ? "light" : "dark";
  document.documentElement.dataset.theme = next;
  if (next === system) { localStorage.removeItem("theme"); delete document.documentElement.dataset.theme; }
  else { localStorage.setItem("theme", next); }
  updateThemeBtn();
};
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", updateThemeBtn);
(function init() {
  const domains = [...new Set(QUESTIONS.map(q => q.domain))].sort();
  const sel = $("domain");
  domains.forEach(d => { const o = document.createElement("option"); o.textContent = d; sel.appendChild(o); });
  saveWrong(); start(); updateThemeBtn();
})();
</script>
</body>
</html>
"""

out = page.replace("__DATA__", data_js)
with open(OUT, "w", encoding="utf-8") as f:
    f.write(out)
print("生成", OUT, "题数:", len(questions), "大小:", len(out.encode("utf-8")), "字节")
