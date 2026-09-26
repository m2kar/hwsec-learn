#!/usr/bin/env python3
"""重建思维导图产物：YAML → Markdown 大纲 + markmap 离线交互 HTML + Xmind 导入版 Markdown。

用法：python3 build.py
产物：
- 硬件安全知识思维导图.md        markmap 渲染用（标题层级 + 引用块解释）
- 硬件安全知识思维导图.html      可交互网页（自动打补丁，依赖 npx markmap-cli）
- 硬件安全知识思维导图-xmind.md  Xmind 导入用（纯嵌套列表，标签与解释内联进主题文本）
"""
import os
import subprocess

import yaml

os.chdir(os.path.dirname(os.path.abspath(__file__)))
YAML_SRC = "硬件安全知识思维导图.yaml"
MD_OUT = "硬件安全知识思维导图.md"
HTML_OUT = "硬件安全知识思维导图.html"
XMIND_MD_OUT = "硬件安全知识思维导图-xmind.md"

# 1. YAML → Markdown 大纲
data = yaml.safe_load(open(YAML_SRC))


def walk(node, depth):
    lines = ["#" * min(depth, 6) + " " + node["name"]]
    if node.get("desc"):
        lines.append("> " + node["desc"])
    for child in node.get("children", []):
        lines += walk(child, depth + 1)
    return lines


open(MD_OUT, "w").write("\n\n".join(walk(data["root"], 1)))


def xmind_lines(node, depth):
    """Xmind 导入格式：纯嵌套列表；标签用【】、解释用冒号内联进主题文本。"""
    title = node["name"]
    if node.get("tag"):
        title += f"【{node['tag']}】"
    if node.get("desc"):
        title += f"：{node['desc']}"
    lines = ["  " * depth + "- " + title]
    for child in node.get("children", []):
        lines += xmind_lines(child, depth + 1)
    return lines


open(XMIND_MD_OUT, "w").write("\n".join(xmind_lines(data["root"], 0)))

# 2. Markdown → markmap 离线 HTML
subprocess.run(
    ["npx", "-y", "markmap-cli", MD_OUT, "-o", HTML_OUT, "--offline", "--no-open"],
    check=True,
)

# 3. 补丁：中文标题 + 初始展开到第 2 层 + 加载后自动适配视图
html = open(HTML_OUT).read()
html = html.replace(
    "<title>Markmap</title>", "<title>硬件安全知识思维导图</title>", 1
)
old = "(getOptions || markmap.deriveOptions)(jsonOptions)"
assert old in html, "markmap 实例化代码结构变化，请检查补丁"
html = html.replace(
    old,
    '(getOptions || markmap.deriveOptions)({"initialExpandLevel": 2, "autoFit": true})',
    1,
)
assert "</body>" in html
html = html.replace(
    "</body>",
    """<script>
window.addEventListener("load", () => {
  if (window.mm) {
    try {
      window.mm.setOptions(Object.assign({}, window.mm.options, { autoFit: true }));
      window.mm.fit();
    } catch (e) {}
  }
});
</script>
</body>""",
    1,
)
open(HTML_OUT, "w").write(html)


def count(node):
    return 1 + sum(count(c) for c in node.get("children", []))


print(
    f"OK: {MD_OUT} + {HTML_OUT} + {XMIND_MD_OUT} 已重建（{count(data['root'])} 个节点）"
)
