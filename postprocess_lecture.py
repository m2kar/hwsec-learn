#!/usr/bin/env python3
"""讲义 HTML 导出后的公开版后处理：
用法: typst compile --features html --format html 讲义/main.typ lecture/index.html 之后运行本脚本。
功能: 弱化厂商字样（标题与框标签）、注入站点导航、主题（深色/浅色）CSS 与切换按钮。
"""
import sys

p = sys.argv[1] if len(sys.argv) > 1 else "lecture/index.html"
s = open(p, encoding="utf-8").read()

# 1) 弱化厂商字样（标题与框标签；正文中的产品名保留）
s = s.replace("华为硬件安全专题", "厂商安全实践案例")
s = s.replace("华为实践与拓展", "厂商实践与拓展")
s = s.replace("华为技术专题", "厂商实践案例")

# 2) 深色模式 CSS（typst 导出内容无显式颜色，覆盖 html/body 与常见元素即可）
theme_css = """
/* 深色模式 */
html { background:#14161a; }
html[data-theme="dark"] { color-scheme:dark; background:#14161a; }
html[data-theme="dark"] body { color:#d6d3cd; background:#14161a; }
html[data-theme="dark"] h2, html[data-theme="dark"] h3, html[data-theme="dark"] h4 { color:#e0ddd6; }
html[data-theme="dark"] a, html[data-theme="dark"] a * { color:#8ab8e8 !important; }
html[data-theme="dark"] table, html[data-theme="dark"] td, html[data-theme="dark"] th { border-color:#3a3f47; }
html[data-theme="dark"] strong, html[data-theme="dark"] b { color:#cdc9c2; }
"""
if "深色模式" not in s:
    s = s.replace("</style>", theme_css + "</style>", 1)

# 3) 首屏主题初始化（避免闪烁）：无本地选择时跟随系统
init = ('<script>(function(){var t=null;try{t=localStorage.getItem("theme")}catch(e){}'
        'if(!t)t=window.matchMedia&&matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light";'
        'document.documentElement.dataset.theme=t;})();</script>')
s = s.replace("<body>", "<body>" + init, 1)

# 4) 顶部导航 + 主题切换按钮
nav = ('<nav style="background:#C7000B;padding:10px 16px;font-size:14px;display:flex;'
       'align-items:center;gap:20px;">'
       '<a href="../" style="color:#fff;text-decoration:none;font-weight:600;">← 首页</a>'
       '<a href="../quiz/" style="color:#fff;text-decoration:none;font-weight:600;">在线刷题</a>'
       '<span style="color:#fff;opacity:.85;">硬件安全学习讲义</span>'
       '<button id="themeBtn" onclick="toggleTheme()" '
       'style="margin-left:auto;background:transparent;border:1px solid rgba(255,255,255,.5);'
       'color:#fff;font-size:12px;padding:4px 12px;border-radius:14px;cursor:pointer;">☾ 深色</button>'
       '</nav>'
       '<script>function toggleTheme(){var d=document.documentElement,'
       'dark=d.dataset.theme==="dark";d.dataset.theme=dark?"light":"dark";'
       'try{localStorage.setItem("theme",d.dataset.theme)}catch(e){}'
       'var b=document.getElementById("themeBtn");'
       'if(b)b.textContent=dark?"☾ 深色":"☀ 浅色";}'
       'document.getElementById("themeBtn").textContent='
       'document.documentElement.dataset.theme==="dark"?"☀ 浅色":"☾ 深色";</script>')
s = s.replace("<body>" + init, "<body>" + init + nav, 1)

open(p, "w", encoding="utf-8").write(s)
print("后处理完成:", p, "| 华为出现:", s.count("华为"), "| 深色CSS:", "data-theme" in s)
