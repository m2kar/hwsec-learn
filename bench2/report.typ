// 硬件安全题库2 多模型评测报告
// 数据源: agg/stats.json（由 report.py 生成）；图表: charts/*.svg
#let stats = json("agg/stats.json")
#let sample = json("sample_questions.json")
#let sq(qid) = sample.find(q => q.qid == qid)
#let M(name) = stats.models.find(m => m.name == name)

#let SHORT = (
  "DeepSeek-V4.1-Flash": "DS-V4.1",
  "GLM-5.3": "GLM-5.3",
  "GLM-5.3-Flash": "GLM-5.3F",
  "GPT-5.6-Sol": "GPT-Sol",
  "GPT-5.6-Terra": "GPT-Terra",
  "Claude-Sonnet-5": "Sonnet-5",
  "Gemini-3.8-Flash": "Gem-3.8",
)

#let ACCENT = rgb("#1f4e79")
#let LIGHT = rgb("#dbe5f1")
#let ZEBRA = rgb("#f4f7fb")

#set page(paper: "a4", margin: (x: 1.9cm, y: 2.1cm), numbering: "1", number-align: center)
#set text(font: ("PingFang SC", "Heiti SC"), size: 10.5pt, lang: "zh")
#set par(justify: true, leading: 0.72em)
#set heading(numbering: "1.1 ")
#show heading: set text(font: ("Heiti SC", "PingFang SC"), weight: 700)
#show heading.where(level: 1): set text(size: 14.5pt)
#show heading.where(level: 2): set text(size: 11.5pt)
#show heading.where(level: 1): block(above: 1.4em, below: 0.8em)
#show table: set text(size: 8.8pt)
#show figure: set block(breakable: false)
#show figure.caption: set text(size: 9pt, fill: luma(90))
#show figure.caption: set text(font: ("Heiti SC", "PingFang SC"), size: 9pt, fill: luma(70))
#set figure.caption(separator: "：")
#set figure(numbering: "1")
#show figure.where(kind: image): set figure(supplement: [图])
#show figure.where(kind: table): set figure(supplement: [表])

// 表格头样式
#let th(..args) = table.cell(fill: LIGHT, text(font: ("Heiti SC",), size: 8.6pt, weight: 600, args.pos().join([ ])))
#let hdrtxt(..args) = text(font: ("Heiti SC",), size: 8.6pt, weight: 600, args.pos().join([ ]))
#let zebra(y) = if calc.even(y) { white } else { ZEBRA }

#align(center)[
  #text(size: 19pt, font: ("Heiti SC",), weight: 700)[硬件安全题库 2 · 多模型评测报告]
  #v(0.3em)
  #text(size: 11pt, fill: luma(90))[正确率与响应时间 —— 600 题库随机抽样 100 题 × 7 个模型 × 700 次请求]
  #v(0.2em)
  #text(size: 9.5pt, fill: luma(110))[2026 年 9 月 27 日 · llmapi.isrc.ac.cn · temperature 0.1 · 逐条原始数据与脚本清单见附录 B]
]
#v(0.5em)

= 摘要

#block(
  fill: rgb("#f0f4fa"), stroke: (left: 3pt + ACCENT), radius: 3pt,
  inset: 11pt, width: 100%,
)[
  #set par(leading: 0.68em)
  本次评测在《硬件安全题库 2》（600 题）中#strong[随机抽取 100 题]，对 7 个模型发起共 700 次答题请求（全部成功），测量正确率与响应时间。主要结论：

  - #strong[正确率 91.0%–93.0%]，模型间差距仅 2 个百分点，但整体比旧题库测评（96.0%–97.6%）#strong[低 3–6 个百分点]：题库 2 明显更难。
  - 差距几乎全部来自#strong[多选题]（83.3%–87.5%，单选为 96.2%–98.1%）；"核心/扩展"难度标签反而未拉开差距（92.3% vs 88.5%–93.4%）。
  - 分知识域看，#strong[故障注入（70%–80%）与密码算法（78%–83%）]显著低于其余各域；处理器微架构、综合两域全员 100%。
  - 87/100 题被 7 个模型全部答对；#strong[6 题七个模型全部答错且作答完全一致]，另 1 题仅 1 个模型答对——强烈提示这 7 道题的参考答案存在争议，建议人工复核。
  - 响应时间：#strong[Claude-Sonnet-5 最快]（中位 2.4 s，P95 仅 5.1 s），Gemini-3.8-Flash 最慢（中位 8.0 s）；DeepSeek-V4.1-Flash 以中位 3.5 s 位居第二快，且#strong[正确率并列第一]，综合表现最优。
]

= 测评设置与方法

#figure(
  table(
    columns: (auto, 1fr),
    inset: (y: 4.5pt, x: 7pt),
    fill: (_, y) => if y == 0 { LIGHT } else if calc.even(y) { white } else { ZEBRA },
    table.header(table.cell(colspan: 2, hdrtxt[测评配置])),
    [题库], [《硬件安全题库 2》共 600 题（单选 322 / 多选 278；核心 200 / 扩展 400；9 个知识域），选项数 4–7 个],
    [抽样], [随机抽取 100 题（随机种子 20260927，抽样结果固化于 sample\_questions.json，可复现），构成见附录 A],
    [模型], [DeepSeek-V4.1-Flash、GLM-5.3、GLM-5.3-Flash、GPT-5.6-Sol、GPT-5.6-Terra、Claude-Sonnet-5、Gemini-3.8-Flash（与 2026-09-25 旧题库测评相同的 7 个模型，便于对比）],
    [接口], [llmapi.isrc.ac.cn（OpenAI 兼容 /v1/chat/completions），temperature = 0.1],
    [提示与判分], [系统提示要求只输出选项字母；答案提取优先识别加粗结论（如 \*\*ABC\*\*），选项字母集合精确匹配判分；仅 1 条回复落入兜底解析],
    [时延口径], [单请求墙钟时间（客户端计时）；各模型并行推进，模型内部并发 4 线程，因此时延含服务端排队成分，尾部偏保守],
    [规模], [700 次请求，0 次最终失败（7 次瞬时错误经指数退避重试成功），总耗时 394 s],
  ),
  caption: [测评配置总览],
)

全部逐题原始回复（含模型答案、判分、时延、token 数与回复原文）已保留于 bench2/results/〈模型〉.jsonl，明细汇总见 `bench2/agg/results_all.csv`（700 行），统计口径见 `bench2/agg/stats.json`。

= 总体正确率

#figure(
  image("charts/overall_accuracy.svg", width: 100%),
  caption: [七个模型总体正确率排名（n = 100，误差条为 95% Wilson 置信区间）],
)

正确率高度收敛：DeepSeek-V4.1-Flash 与 GPT-5.6-Sol 以 93.0% 并列第一，Claude-Sonnet-5 以 91.0% 垫底，极差仅 2.0 个百分点。在 n = 100 下，单模型正确率的 95% 置信区间半宽约 ±5 个百分点，各模型区间全部重叠——#strong[单次 100 题不足以在统计上区分这 7 个模型]，名次差异应在抽样误差范围内理解。真正拉开差距的是下文的题型与知识域维度。

#figure(
  table(
    columns: (1.2em, auto, auto, auto, auto, 1fr, 1fr, 1fr, auto),
    align: (center, left, center, center, center, center, center, center, center),
    inset: (y: 4.2pt, x: 5pt),
    fill: (_, y) => if y == 0 { LIGHT } else { zebra(y) },
    table.header(
      table.cell(colspan: 9, align: left, hdrtxt[总体正确率一览（按正确率降序）]),
      [排名], [模型], [答对], [正确率], [95% 置信区间], [单选 (52)], [多选 (48)], [答错], [错误构成（单/多）],
    ),
    ..stats.models_by_acc.enumerate().map(((i, name)) => {
      let m = M(name)
      (
        str(i + 1), name, str(m.correct), m.acc_str, m.ci_str,
        stats.qtype_acc.at(name).at("单选").acc_str,
        stats.qtype_acc.at(name).at("多选").acc_str,
        m.err_str,
        str(m.errors_single) + " / " + str(m.errors_multi),
      )
    }).flatten(),
  ),
  caption: [总体正确率、分题型正确率与错误构成],
)

= 响应时间分析

#figure(
  image("charts/latency_summary.svg", width: 100%),
  caption: [各模型时延的均值 / 中位数 / P95 对比],
)

#figure(
  image("charts/latency_box.svg", width: 100%),
  caption: [各模型时延分布箱线图（每模型 100 次请求）],
)

#figure(
  image("charts/latency_ecdf.svg", width: 100%),
  caption: [响应时间累计分布（ECDF），曲线越靠左代表整体越快],
)

时延呈三个梯队：#strong[Claude-Sonnet-5 一枝独秀]（中位 2.4 s，P95 仅 5.1 s，且箱体最紧，长尾风险最小）；DeepSeek-V4.1-Flash（中位 3.5 s）与 GPT-5.6-Terra（中位 3.9 s）构成第二梯队，其中 Terra 的 P95（11.2 s）是该梯队中最稳的；GLM 双子、GPT-5.6-Sol 与 Gemini-3.8-Flash 中位时延在 5.7–8.0 s 之间，P95 普遍超过 14 s。GLM-5.3 均值（10.9 s）明显高于中位数（5.7 s），说明其慢请求拖尾严重。

需要注意本口径为"并发 4 下的墙钟时间"，包含服务端排队：P95 与均值会因并发而膨胀，跨模型相对快慢仍有参考价值，但不宜当作单并发服务水平。

#figure(
  table(
    columns: (auto, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr),
    align: (left, center, center, center, center, center, center, center, center),
    inset: (y: 4.2pt, x: 5pt),
    fill: (_, y) => if y == 0 { LIGHT } else { zebra(y) },
    table.header(
      table.cell(colspan: 9, align: left, hdrtxt[时延与输出统计（单位：秒；按中位数升序）]),
      [模型], [均值], [中位], [P90], [P95], [最快], [最慢], [中位输出 token], [中位吞吐 (tok/s)],
    ),
    ..stats.models_by_medlat.map(name => {
      let m = M(name)
      (name, m.mean_str, m.median_str, m.p90_str, m.p95_str, m.min_str, m.max_str, m.tok_str, m.tps_str)
    }).flatten(),
  ),
  caption: [各模型时延明细与输出长度、生成吞吐],
)

= 正确率—时延权衡

#figure(
  image("charts/acc_vs_latency.svg", width: 100%),
  caption: [正确率与中位时延的权衡（气泡大小为中位输出 token 数，虚线为两维中位数分界）],
)

以两维中位数为界分四象限：#strong[DeepSeek-V4.1-Flash 独处"快且准"的理想区]；GPT-5.6-Sol 落在"准但偏慢"区；Claude-Sonnet-5 最快但正确率垫底，属于"快但略逊"；Gemini-3.8-Flash、GLM-5.3、GLM-5.3-Flash 落入"慢且无明显准确率优势"的不利区。气泡大小揭示另一层差异：Claude-Sonnet-5、GPT-5.6-Terra、GPT-5.6-Sol 输出近乎只有答案字母（中位 1/5/38 token），而 GLM、DeepSeek、Gemini 会附带简短解释（260–350 token）——后者的时延中有一部分是为更长输出付出的。

= 分题型与分难度

#figure(
  image("charts/qtype_accuracy.svg", width: 100%),
  caption: [分题型正确率：单选（左）vs 多选（右）],
)

#figure(
  image("charts/difficulty_accuracy.svg", width: 100%),
  caption: [分难度正确率：核心（39 题）vs 扩展（61 题）],
)

题型是本次评测#strong[最有区分度的维度]：单选正确率 96.2%–98.1%（各模型仅错 1–2 题），多选骤降至 83.3%–87.5%（错 6–8 题），落差达 9–13 个百分点。多选题要求完整命中最优字母集合，多答、漏答任何一项即判错，这对模型的边界把握能力要求显著更高。相比之下，"核心 / 扩展"标签几乎未拉开差距（92.3% vs 91.8%–93.4%），说明本库的难度信息更多由题型与知识域承载，而非难度标签。个别模型的偏科值得注意：Claude-Sonnet-5 核心题正确率全场最高（94.9%），扩展题却全场最低（88.5%）。

= 分知识域表现

#figure(
  image("charts/domain_heatmap.svg", width: 100%),
  caption: [模型 × 知识域正确率热力图（%）],
)

#let domrows = {
  let rows = ()
  for d in stats.domains {
    let label = d + "（n=" + str(stats.domain_acc.at("GLM-5.3").at(d).n) + "）"
    rows.push(table.cell(fill: LIGHT, hdrtxt(label)))
    for name in stats.models_by_acc {
      rows.push(stats.domain_acc.at(name).at(d).acc_str)
    }
  }
  rows
}
#figure(
  table(
    columns: (2.6fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr, 1fr),
    align: (left, center, center, center, center, center, center, center),
    inset: (y: 4pt, x: 4.5pt),
    fill: (x, y) => if x == 0 or y == 0 { LIGHT } else { zebra(calc.floor(y / 8)) },
    table.header(
      table.cell(colspan: 8, align: left, hdrtxt[知识域 × 模型 正确率（%，列按总体正确率排序）]),
      [知识域], ..stats.models_by_acc.map(n => SHORT.at(n)),
    ),
    ..domrows,
  ),
  caption: [知识域正确率明细（列标题缩写：GLM-5.3F = GLM-5.3-Flash，GPT-Sol = GPT-5.6-Sol，GPT-Terra = GPT-5.6-Terra，Sonnet-5 = Claude-Sonnet-5，Gem-3.8 = Gemini-3.8-Flash，DS-V4.1 = DeepSeek-V4.1-Flash；括号内 n 为该域题数）],
)

知识域维度分化明显：#strong[故障注入是全场最弱域]（各模型 70%–80%，共识错题 Y131、Z088 所在域），#strong[密码算法次之]（78%–83%，六道全错题中三道在此）；供应链安全呈现罕见的完全一致（89% = 8/9，九个模型错同一道 Z186）。相反，处理器微架构与综合两域全员满分，硬件可信根、TEE、侧信道也都在 92% 以上。模型之间的知识域轮廓高度相似，未出现"某家独strong于某域"的互补格局。

= 题目层面：共识与分歧

#figure(
  image("charts/question_consensus.svg", width: 100%),
  caption: [题目共识分布：每道题被多少个模型答对],
)

#figure(
  image("charts/errors_agreement.svg", width: 100%),
  caption: [错误构成（a）与模型两两作答一致率（b）],
)

100 道题中 87 道被全员答对，错误高度集中：仅 13 道题出现错误，且多数题是"多家齐错"。#strong[六道题（Y043、Y045、Y116、Y131、Z088、Z186）被七个模型全部答错，且每道题七个模型给出的答案完全相同]；Z115 仅 Claude-Sonnet-5 答对，其余六家同样给出一致答案。两两作答一致率高达 95%–100%。当互相独立的七个模型在同一道题上给出同一个"错"答案时，更可能的解释不是七家同时犯同一错误，而是#strong[参考答案本身值得商榷]——这与旧题库测评中 Q087、Q094、Q123 的情形一脉相承，建议对下列题目逐题人工复核。

#let consrows = {
  let rows = ()
  for q in stats.consensus_wrong {
    let sqq = sq(q.qid)
    rows.push(
      (
        q.qid, q.domain, q.qtype, text(fill: rgb("#b03030"), q.answer),
        text(fill: rgb("#3060b0"), q.pred_summary),
        {
          let cl = sqq.stem.clusters()
          cl.slice(0, calc.min(52, cl.len())).join() + "…"
        },
      ),
    )
  }
  rows
}
#figure(
  table(
    columns: (auto, auto, auto, auto, auto, 1fr),
    align: (center, left, center, center, center, left),
    inset: (y: 4.2pt, x: 5pt),
    fill: (_, y) => if y == 0 { LIGHT } else { zebra(y) },
    table.header(
      table.cell(colspan: 6, align: left, hdrtxt[共识错题（≤1 个模型答对，共 7 道）]),
      [题号], [知识域], [题型], [参考答案], [七模型作答], [题干摘句],
    ),
    ..consrows.flatten(),
  ),
  caption: [共识错题清单：红色为参考答案，蓝色为各模型实际作答分布],
)

除共识错题外，其余 6 道为个别模型的孤立失误（Y066 双错、Y010/Y159/Y238/Y386/Y334 各 1–2 家漏选或多选），多为多选题漏选一项的边缘失误，例如 Gemini-3.8-Flash 在 Y334 漏选 A、Claude-Sonnet-5 在 Y159 漏选 D。没有任何模型在单选题上出现"理解性连环错"，单选失分全部落在两道争议题（Z088）之外仅 Y066、Y010 两题。

#let sliprows = {
  let rows = ()
  for q in stats.per_question {
    if q.n_correct >= 2 and q.n_correct <= 6 {
      let wp = q.wrong_preds.pairs().map(((m, p)) => SHORT.at(m) + "→" + p).join("，")
      rows.push((q.qid, q.domain, q.qtype, q.answer, str(q.n_correct) + "/7", wp))
    }
  }
  rows
}
#figure(
  table(
    columns: (auto, auto, auto, auto, auto, 1fr),
    align: (center, left, center, center, center, left),
    inset: (y: 4.2pt, x: 5pt),
    fill: (_, y) => if y == 0 { LIGHT } else { zebra(y) },
    table.header(
      table.cell(colspan: 6, align: left, hdrtxt[非共识错题（2–6 个模型答对）]),
      [题号], [知识域], [题型], [参考答案], [答对], [答错模型 → 其作答],
    ),
    ..sliprows.flatten(),
  ),
  caption: [非共识错题清单],
)

= 输出长度与生成吞吐

#figure(
  image("charts/throughput.svg", width: 100%),
  caption: [中位输出 token 数与中位生成吞吐],
)

输出行为分成两派：GLM 双子、DeepSeek、Gemini 输出 260–350 token 的简短解析，生成吞吐以 DeepSeek-V4.1-Flash 最高（72.3 tok/s）、GLM-5.3 次之（61.8 tok/s）；Claude-Sonnet-5、GPT-5.6-Terra、GPT-5.6-Sol 严格遵守"只输出字母"的指令（中位 1–38 token）。对后者，"token/s"分母极小、数值不再代表生成速度（如 Terra 的 2.1 tok/s 实为几乎无输出），其时延主要消耗在排队与推理调度上。这一差异也提示：若下游应用需要#strong[带解析的回答]，GLM / DeepSeek 系的输出格式更接近可用形态；若只要#strong[裸答案做自动判分]，答案式输出更省时省 token。

= 与上次测评对比

#let oldrows = stats.models.map(mst => {
  let old = stats.old_bench.at(mst.name)
  (mst.name, old.acc_str, mst.acc_str, str(calc.round((mst.accuracy - old.accuracy) * 1000) / 10), old.mean_str, mst.median_str)
})
#figure(
  table(
    columns: (auto, 1fr, 1fr, 1fr, 1fr, 1fr),
    align: (left, center, center, center, center, center),
    inset: (y: 4.2pt, x: 5pt),
    fill: (_, y) => if y == 0 { LIGHT } else { zebra(y) },
    table.header(
      table.cell(colspan: 6, align: left, hdrtxt[新旧题库测评对比（旧：2026-09-25，126 题；新：本次，随机 100 题）]),
      [模型], [旧正确率], [新正确率], [变化 (pt)], [旧均延时 (s)], [新中位延时 (s)],
    ),
    ..oldrows.flatten(),
  ),
  caption: [同一批模型在旧题库与题库 2 抽样上的表现对比],
)

同一批模型全体从旧题库的 96.0%–97.6% 下降至 91.0%–93.0%，降幅 3.7–6.0 个百分点；其中 Claude-Sonnet-5 降幅最大（96.0%→91.0%），DeepSeek-V4.1-Flash 与 GPT-5.6-Sol 最抗跌（均 97.6%→93.0%）。原因不在模型退步，而在题库升级：题库 2 的多选占比更高（48% vs 35%）、多选答案普遍含 3–4 项、61% 为扩展题，且选项最多 7 个，整体对边界概念与多要点合并考查的要求更高。旧题库上"接近满分"的表面繁荣被题库 2 打破，#strong[模型间真实差距反而更清晰地显现在多选题与故障注入、密码算法两个知识域]。

= 结论与建议

- #strong[模型选型]：综合准确率与响应时间，#strong[DeepSeek-V4.1-Flash 为本次评测最优]（正确率并列第一 93.0%，中位 3.5 s，生成吞吐 72 tok/s）；GPT-5.6-Sol 同为 93.0% 但时延约为前者 1.7 倍；对时延敏感的在线场景 Claude-Sonnet-5（中位 2.4 s、P95 5.1 s）值得以 2 个百分点正确率换取。
- #strong[评测方法]：题库 2 有效拉开了模型差距（相对旧题库），但 7 模型在 100 题上的置信区间仍全部重叠；如需统计显著的名次，建议每模型 400 题以上或多次重复抽样。
- #strong[题库修订]：建议人工复核 7 道共识错题（Y043、Y045、Y116、Y131、Z088、Z115、Z186）的参考答案；复核前可将这 7 题标记为"存疑"，避免污染后续评测。
- #strong[判分口径]：当前多选"全对才得分"的口径对模型最严苛、区分度也最大；可补充 Jaccard 部分得分口径作为辅助维度。
- #strong[后续工作]：单并发时延测量（剥离排队影响）、同一题多轮重复评测的稳定性（方差）分析、以及 3 模型投票集成在更大题量下的收益验证。

= 附录 A · 抽样构成

#let bankcomp = (
  ("题型", (单选: (322, stats.meta.sample_comp.qtype.at("单选")), 多选: (278, stats.meta.sample_comp.qtype.at("多选")))),
  ("难度", (核心: (200, stats.meta.sample_comp.difficulty.at("核心")), 扩展: (400, stats.meta.sample_comp.difficulty.at("扩展")))),
)
#let domcomp = (
  "密码算法": (111, 18), "硬件可信根": (92, 18), "侧信道攻击": (91, 13), "TEE": (72, 13),
  "故障注入": (72, 10), "处理器微架构": (54, 9), "供应链安全": (54, 9),
  "调试接口安全": (46, 8), "综合": (8, 2),
)
#let comprows = {
  let rows = ()
  for (dim, vals) in bankcomp {
    for (k, v) in vals {
      rows.push((dim, k, str(v.at(0)), str(v.at(1))))
    }
  }
  for (k, v) in domcomp {
    rows.push(("知识域", k, str(v.at(0)), str(v.at(1))))
  }
  rows
}
#figure(
  table(
    columns: (auto, auto, 1fr, 1fr),
    align: (center, left, center, center),
    inset: (y: 3.8pt, x: 5pt),
    fill: (_, y) => if y == 0 { LIGHT } else { zebra(y) },
    table.header(
      table.cell(colspan: 4, align: left, hdrtxt[题库 2 全库与本次抽样构成对比]),
      [维度], [取值], [全库 (600)], [样本 (100)],
    ),
    ..comprows.flatten(),
  ),
  caption: [随机抽样（seed = 20260927）各维度构成与全库对比，比例基本一致],
)

= 附录 B · 数据与脚本清单

#block(breakable: false)[#grid(
  columns: (auto, 1fr),
  column-gutter: 14pt, row-gutter: 5.5pt,
  text(font: ("Menlo",), size: 8.6pt)[bench2/sample\_questions.json], [抽样的 100 道题全文（题干、7 个选项、答案、解析、考点），固定种子可复现],
  text(font: ("Menlo",), size: 8.6pt)[bench2/results/\*.jsonl], [#strong[原始数据]：7 个模型逐题回复记录共 700 条（模型答案、判分、时延、token 数、回复原文截断 500 字）],
  text(font: ("Menlo",), size: 8.6pt)[bench2/agg/results\_all.csv], [700 行明细汇总表（UTF-8 BOM，可直接用 Excel 打开）],
  text(font: ("Menlo",), size: 8.6pt)[bench2/agg/stats.json], [报告全部统计量的机器可读版本（本报告各表均由此生成）],
  text(font: ("Menlo",), size: 8.6pt)[bench2/charts/\*.svg], [本报告全部 11 幅图表的矢量原稿],
  text(font: ("Menlo",), size: 8.6pt)[bench2/bench2.py], [评测脚本（随机抽样、并发请求、断点续跑、答案提取与判分）],
  text(font: ("Menlo",), size: 8.6pt)[bench2/report.py], [聚合统计与图表生成脚本],
  text(font: ("Menlo",), size: 8.6pt)[bench2/run.log], [评测运行日志（含重试记录）],
)]
