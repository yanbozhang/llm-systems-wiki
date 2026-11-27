"""从模块 Markdown 的 Mermaid 权威源生成固定布局、可访问的 SVG。"""
import argparse
from html import escape
import json
from pathlib import Path
import re
import unicodedata


ROOT = Path(__file__).resolve().parents[1]
FONT = "Inter, PingFang SC, Microsoft YaHei, Noto Sans CJK SC, sans-serif"
PALETTE = {
    "main": ("#eef4ff", "#728eb7", "#183654"),
    "state": ("#eaf7f5", "#74aaa4", "#175e59"),
    "check": ("#edf7ee", "#82a78a", "#285b39"),
    "external": ("#ffffff", "#96a3b3", "#34485e"),
    "guard": ("#fff4e5", "#d8a56b", "#8b5219"),
    "offline": ("#f4effc", "#aa91ce", "#664492"),
}
LAYOUTS = {
    "network": {
        "height": 650,
        "note": "概念数据流；采样结果追加到输入，继续自回归生成。未展开各层内部计算。",
        "groups": [(28, 112, 984, 454, "自回归模型 · 概念计算结构", "main")],
        "nodes": {"Input": (70, 190), "Embed": (420, 190), "Attention": (770, 190),
                  "FFN": (770, 410), "Output": (420, 410)},
        "roles": {"Input": "external", "Output": "check"},
        "routes": {("Output", "Input"): [(420, 454), (170, 454), (170, 278)]},
        "labels": {("Output", "Input"): ("追加已采样 token", 170, 352)},
    },
    "training": {
        "height": 650,
        "note": "训练与验证闭环；回到数据与采样协议表示下一轮调整，不代表验证集进入训练。",
        "groups": [(28, 112, 984, 454, "参数学习与验证 · 概念流程", "main")],
        "nodes": {"Data": (70, 190), "Forward": (420, 190), "Loss": (770, 190),
                  "Update": (770, 410), "Checkpoint": (420, 410), "Evaluate": (70, 410)},
        "roles": {"Data": "external", "Checkpoint": "state", "Evaluate": "check"},
        "routes": {},
        "labels": {("Evaluate", "Data"): ("下一轮调整", 170, 350)},
    },
    "inference": {
        "height": 650,
        "note": "调度与缓存管理是运行职责；Decode 返回调度队列，指标需绑定负载与服务目标。",
        "groups": [(28, 112, 984, 454, "推理服务 · 请求、状态与输出", "main")],
        "nodes": {"Request": (70, 190), "Queue": (420, 190), "Prefill": (770, 190),
                  "Cache": (770, 410), "Decode": (420, 410), "Metrics": (70, 410)},
        "roles": {"Request": "external", "Cache": "state", "Metrics": "check"},
        "routes": {},
        "labels": {("Decode", "Queue"): ("继续调度", 520, 350)},
    },
    "knowledge": {
        "height": 780,
        "note": "三条组织路径不是必须串行执行的步骤；引用核对与更正反馈回接入过程。",
        "groups": [(28, 112, 984, 584, "知识系统 · 接入、组织、回答与更正", "main")],
        "nodes": {"Sources": (70, 185), "Ingestion": (420, 185),
                  "Retrieval": (70, 390), "Graph": (420, 390), "Wiki": (770, 390),
                  "Answer": (420, 585), "Audit": (770, 585)},
        "roles": {"Sources": "external", "Graph": "state", "Wiki": "state", "Audit": "check"},
        "routes": {
            ("Ingestion", "Retrieval"): [(450, 273), (450, 330), (170, 330), (170, 390)],
            ("Ingestion", "Wiki"): [(590, 273), (590, 330), (870, 330), (870, 390)],
            ("Retrieval", "Answer"): [(170, 478), (170, 542), (470, 542), (470, 585)],
            ("Wiki", "Answer"): [(870, 478), (870, 542), (570, 542), (570, 585)],
            ("Audit", "Ingestion"): [(970, 629), (990, 629), (990, 229), (620, 229)],
        },
        "labels": {("Audit", "Ingestion"): ("更正反馈", 790, 211)},
    },
    "agents": {
        "height": 780,
        "note": "授权边界贯穿执行；只有独立验收通过才交付，失败回到真实状态观察。",
        "groups": [(28, 112, 984, 584, "业务 Agent · 行动与真实状态闭环", "main")],
        "nodes": {"Task": (70, 185), "Observe": (420, 185), "Plan": (770, 185),
                  "Execute": (770, 390), "Evidence": (420, 390), "Verify": (70, 390),
                  "Deliver": (70, 585)},
        "roles": {"Task": "external", "Evidence": "state", "Verify": "check", "Deliver": "check"},
        "routes": {("Verify", "Observe"): [(170, 390), (170, 332), (520, 332), (520, 273)]},
        "labels": {("Verify", "Observe"): ("修复：重新观察", 330, 319)},
    },
    "benchmark": {
        "height": 780,
        "note": "结论绑定任务、切分、预算和版本；汇总分数不能替代轨迹、方差及限制。",
        "groups": [(28, 112, 984, 584, "评测协议 · 可复现运行与可追溯结论", "main")],
        "nodes": {"Claim": (70, 185), "Protocol": (420, 185), "Run": (770, 185),
                  "Evidence": (770, 390), "Judge": (420, 390), "Statistics": (70, 390),
                  "Report": (70, 585)},
        "roles": {"Claim": "external", "Evidence": "state", "Judge": "check", "Report": "check"},
        "routes": {},
        "labels": {},
    },
    "rsi": {
        "height": 830,
        "note": "候选不能改写验证器；改进器更新另做同起点、同预算对照，不由系统增益直接推出。",
        "groups": [(28, 112, 984, 644, "跨任务改进 · 候选与准入分离", "offline")],
        "nodes": {"Version": (70, 180), "Run": (420, 180), "Propose": (770, 180),
                  "Next": (70, 405), "Gate": (420, 405), "Candidate": (770, 405),
                  "Meta": (770, 635)},
        "roles": {"Version": "state", "Run": "main", "Propose": "offline", "Next": "state",
                  "Gate": "check", "Candidate": "offline", "Meta": "check"},
        "routes": {
            ("Gate", "Version"): [(470, 405), (470, 335), (170, 335), (170, 268)],
            ("Next", "Run"): [(70, 449), (45, 449), (45, 155), (520, 155), (520, 180)],
            ("Gate", "Meta"): [(520, 493), (520, 679), (770, 679)],
            ("Meta", "Propose"): [(970, 679), (990, 679), (990, 224), (970, 224)],
        },
        "labels": {
            ("Gate", "Version"): ("拒绝并记账", 300, 319),
            ("Gate", "Next"): ("接收 / 留档 / 可回退", 346, 475),
            ("Meta", "Propose"): ("单独证明后更新", 830, 598),
        },
    },
    "harness": {
        "width": 1120,
        "height": 790,
        "note": "参考职责架构，不对应独立服务。M7 贯穿运行；M8 离线改进另图展开。",
        "groups": [(28, 108, 754, 597, "Harness 运行系统", "main"),
                   (802, 195, 290, 403, "外部依赖 · 不是 Harness 本体", "external")],
        "nodes": {"Goal": (50, 240), "Schedule": (300, 240), "Tools": (550, 240),
                  "State": (50, 480), "Context": (300, 480), "Verify": (550, 480),
                  "Model": (840, 480), "Resource": (840, 240), "Guard": (50, 152, 700, 58)},
        "roles": {"Goal": "main", "Schedule": "main", "Tools": "main", "State": "state",
                  "Context": "state", "Verify": "check", "Model": "external",
                  "Resource": "external", "Guard": "guard"},
        "routes": {
            ("Context", "Model"): [(500, 524), (515, 524), (515, 625), (940, 625), (940, 568)],
            ("Model", "Schedule"): [(940, 480), (940, 410), (350, 410), (350, 328)],
            ("Tools", "Schedule"): [(600, 240), (600, 224), (400, 224), (400, 240)],
            ("Verify", "Schedule"): [(550, 524), (532, 524), (532, 355), (450, 355), (450, 328)],
            ("Verify", "Goal"): [(650, 568), (650, 674), (32, 674), (32, 284), (50, 284)],
            ("Tools", "State"): [(550, 300), (518, 300), (518, 380), (150, 380), (150, 480)],
            ("State", "Schedule"): [(250, 524), (275, 524), (275, 300), (300, 300)],
            ("Resource", "Tools"): [(940, 328), (940, 362), (700, 362), (700, 328)],
            ("Guard", "Tools"): [(650, 210), (650, 240)],
        },
        "labels": {
            ("Context", "Model"): ("上下文与模型请求", 775, 650),
            ("Model", "Schedule"): ("行动建议，由 Harness 决定是否执行", 725, 430),
            ("Verify", "Goal"): ("验收结果 → M1 判定完成", 390, 694),
            ("Verify", "Schedule"): ("修复", 493, 347),
            ("Tools", "State"): ("记录执行事实", 260, 373),
            ("State", "Schedule"): ("恢复", 271, 452),
            ("Tools", "Schedule"): ("观察", 530, 229),
            ("Tools", "Resource"): ("调用", 795, 272),
            ("Resource", "Tools"): ("执行结果", 830, 382),
            ("Guard", "Tools"): ("", 0, 0),
        },
        "omit": {"Improve"},
    },
    "harness-improvement": {
        "module": "harness",
        "title": "Harness · 离线改进与版本准入",
        "height": 650,
        "note": "只更新后续版本的运行配置，不在当前任务中修改验收标准；候选必须经过离线评测。",
        "groups": [(28, 112, 984, 454, "离线改进 · 与当前执行闭环分开", "offline")],
        "nodes": {"State": (70, 185), "Verify": (70, 410), "Improve": (420, 300),
                  "Schedule": (770, 300)},
        "roles": {"State": "state", "Verify": "check", "Improve": "offline", "Schedule": "main"},
        "routes": {
            ("State", "Improve"): [(270, 229), (340, 229), (340, 322), (420, 322)],
            ("Verify", "Improve"): [(270, 454), (340, 454), (340, 366), (420, 366)],
        },
        "labels": {("Improve", "Schedule"): ("评测后发布新版本", 695, 288)},
        "only": {("State", "Improve"), ("Verify", "Improve"), ("Improve", "Schedule")},
    },
}


def parse_graph(markdown):
    match = re.search(r"```mermaid\s*\n([\s\S]*?)```", markdown)
    if not match:
        raise ValueError("模块缺少 Mermaid 权威源")
    source = match.group(1)
    declarations = re.findall(r'(\w+)\["([^"]+)"\]', source)
    nodes = {}
    for identity, label in declarations:
        if identity in nodes and nodes[identity] != label:
            raise ValueError(f"节点 {identity} 有冲突标签")
        nodes[identity] = label
    flattened = re.sub(r'(\w+)\["[^"]+"\]', r"\1", source)
    edge_pattern = r"(\w+)\s+(-->|-\.->)(?:\|([^|]+)\|)?\s*(\w+)"
    edges = []
    for line in flattened.splitlines():
        line = line.strip()
        if not line or line.startswith("%%") or re.fullmatch(r"flowchart (LR|TB|TD)", line) or line in nodes:
            continue
        edge = re.fullmatch(edge_pattern, line)
        if not edge:
            raise ValueError(f"固定布局暂不支持此语句，请显式扩展解析器：{line}")
        origin, kind, label, target = edge.groups()
        edges.append((origin, kind, label or "", target))
    if not nodes or not edges:
        raise ValueError("模块图没有节点或连线")
    for origin, _, _, target in edges:
        if origin not in nodes or target not in nodes:
            raise ValueError(f"未知节点：{origin} → {target}")
    return nodes, edges


def wrap(text, limit):
    if re.search(r"<br\s*/?>", text):
        return [line for section in re.split(r"<br\s*/?>", text) for line in wrap(section, limit)]
    lines, current, used = [], "", 0
    for character in text:
        size = 1 if unicodedata.east_asian_width(character) in "WF" else 0.55
        if used + size > limit and current:
            lines.append(current.strip())
            current, used = "", 0
        current += character
        used += size
    if current:
        lines.append(current.strip())
    return lines


def box(position):
    return (*position[:2], *(position[2:] or (200, 88)))


def route(origin, target):
    left, top, width, height = box(origin)
    other_left, other_top, other_width, other_height = box(target)
    if top == other_top:
        if left < other_left:
            return [(left + width, top + height / 2), (other_left, other_top + other_height / 2)]
        return [(left, top + height / 2), (other_left + other_width, other_top + other_height / 2)]
    if left != other_left:
        raise ValueError("非对齐节点必须显式指定正交路线")
    if top < other_top:
        return [(left + width / 2, top + height), (other_left + other_width / 2, other_top)]
    return [(left + width / 2, top), (other_left + other_width / 2, other_top + other_height)]


def render(module, markdown, layout):
    nodes, edges = parse_graph(markdown)
    positions = layout["nodes"]
    width, height = layout.get("width", 1040), layout["height"]
    title = layout.get("title", f'{module["title"]} · 系统架构')
    note = layout["note"]
    if not set(positions).issubset(nodes):
        raise ValueError(f"{module['id']} 布局包含源文件中不存在的节点")
    if "only" not in layout and set(nodes) - set(positions) - layout.get("omit", set()):
        raise ValueError(f"{module['id']} 有未布局的节点")
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title description">',
        f"<title id=\"title\">{escape(title)}</title><desc id=\"description\">{escape(note)}</desc>",
        '<defs><marker id="arrow" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M1 1L9 5L1 9" fill="none" stroke="#596f88" stroke-width="1.5"/></marker></defs>',
        f'<rect width="{width}" height="{height}" rx="16" fill="#ffffff"/>',
        f'<g font-family="{FONT}" fill="#183654">',
        f'<text x="32" y="49" font-size="30" font-weight="700">{escape(title)}</text>',
        '<text x="32" y="81" font-size="17" fill="#607286">先看边界与主路径，再看状态、反馈与约束</text>',
    ]
    for left, top, group_width, group_height, label, role in layout["groups"]:
        fill, stroke, color = PALETTE[role]
        parts.extend([
            f'<rect x="{left}" y="{top}" width="{group_width}" height="{group_height}" rx="12" fill="{fill}" fill-opacity=".4" stroke="{stroke}" stroke-opacity=".45"/>',
            f'<text x="{left + 18}" y="{top + 29}" font-size="17" font-weight="600" fill="{color}">{escape(label)}</text>',
        ])
    labels = []
    for origin, kind, label, target in edges:
        pair = (origin, target)
        if "only" in layout and pair not in layout["only"]:
            continue
        if origin not in positions or target not in positions:
            continue
        points = layout["routes"].get(pair)
        if points is None:
            points = route(positions[origin], positions[target])
        path = "M" + " L".join(f"{horizontal:g} {vertical:g}" for horizontal, vertical in points)
        dash = ' stroke-dasharray="6 5"' if kind == "-.->" else ""
        parts.append(f'<path d="{path}" fill="none" stroke="#596f88" stroke-width="2" stroke-linejoin="round"{dash} marker-end="url(#arrow)"/>')
        if pair in layout["labels"]:
            label, horizontal, vertical = layout["labels"][pair]
        else:
            horizontal = (points[0][0] + points[-1][0]) / 2
            vertical = (points[0][1] + points[-1][1]) / 2 - 13
        if label:
            labels.append(f'<text x="{horizontal}" y="{vertical}" text-anchor="middle" font-size="16" fill="#425a73" stroke="#ffffff" stroke-width="5" paint-order="stroke">{escape(label)}</text>')
    for identity, position in positions.items():
        left, top, node_width, node_height = box(position)
        fill, stroke, color = PALETTE[layout["roles"].get(identity, "main")]
        lines = wrap(nodes[identity], (node_width - 26) / 20)
        if len(lines) * 25 > node_height - 10:
            raise ValueError(f"{module['id']}/{identity} 文字超出节点")
        parts.append(f'<rect x="{left}" y="{top}" width="{node_width}" height="{node_height}" rx="9" fill="{fill}" stroke="{stroke}" stroke-width="1.5"/>')
        baseline = top + node_height / 2 - (len(lines) - 1) * 12.5 + 7
        for index, line in enumerate(lines):
            parts.append(f'<text x="{left + node_width / 2}" y="{baseline + index * 25}" text-anchor="middle" font-size="20" font-weight="550" fill="{color}">{escape(line)}</text>')
    parts.extend(labels)
    for index, line in enumerate(wrap(note, (width - 64) / 17)):
        parts.append(f'<text x="32" y="{height - 45 + index * 24}" font-size="17" fill="#607286">{escape(line)}</text>')
    parts.append("</g></svg>")
    return "\n".join(parts) + "\n"


def inventory(root=ROOT):
    pages = []
    for directory in ("docs", "wiki"):
        for path in sorted((root / directory).rglob("*.md")):
            count = len(re.findall(r"^```mermaid\s*$", path.read_text(encoding="utf-8"), re.M))
            if count:
                pages.append((path.relative_to(root).as_posix(), count))
    total = sum(count for _, count in pages)
    lines = [
        "# 图示索引",
        "",
        "由 `python scripts/render_diagrams.py --write` 生成；不要手动维护数量。",
        "",
        f"当前 {len(pages)} 个 Markdown 页面包含 {total} 张 Mermaid 权威源图。"
        f"其中模块总览 {len(LAYOUTS) - 1} 张源图生成 {len(LAYOUTS)} 张固定布局 SVG；"
        "其余局部图由网站的共享 Mermaid 主题渲染，GitHub 保留原生 Mermaid 展示。",
        "",
        "图示维护者为对应模块的内容维护者；展示控件与导出脚本由网站维护者共同检查。",
        "图标、Logo、首页装饰示意和历史网站截图不属于技术关系图。",
        "",
        "## 固定布局与地图",
        "",
        "| 展示文件 | 唯一内容源 | 布局与生成 |",
        "| --- | --- | --- |",
    ]
    modules = {module["id"]: module for module in json.loads((root / "knowledge/modules.json").read_text())}
    for identity, layout in LAYOUTS.items():
        module = modules[layout.get("module", identity)]
        lines.append(f'| [architecture-{identity}.svg](../assets/architecture-{identity}.svg) | [{module["title"]}的折叠 Mermaid 源](../{module["page"]}) | [render_diagrams.py](../scripts/render_diagrams.py) |')
    for name in ("知识地图", "能力地图"):
        for suffix in ("", "预览"):
            lines.append(f"| [{name}{suffix}.svg](../assets/{name}{suffix}.svg) | [knowledge 清单](../knowledge/README.md) | [render_maps.py](../scripts/render_maps.py) |")
    lines.extend([
        "", "## 逐页权威源", "",
        "| Markdown 页面 | 图数 |", "| --- | ---: |",
        *[f"| [{path}](../{path}) | {count} |" for path, count in pages],
        "",
        "## 验证入口",
        "",
        "- [绘图标准](GitHub仓库绘图标准指南.md)",
        "- [本次绘图验收记录](绘图优化与验收记录.md)",
        "- `python scripts/render_diagrams.py --check`：检查架构导出与本索引同步。",
        "- `python scripts/render_maps.py --check`：检查完整地图和精简预览同步。",
        "- `python -m unittest tests.test_diagrams`：检查权威源、SVG 结构、连线避让及地图内容。",
        "- `cd web && npm test`：含共享图示控件的顺序渲染、失败、缩放、源码和语言切换。",
        "",
    ])
    return "\n".join(lines)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    modules = {module["id"]: module for module in json.loads((ROOT / "knowledge/modules.json").read_text())}
    stale = []
    for identity, layout in LAYOUTS.items():
        module = modules[layout.get("module", identity)]
        markdown = (ROOT / module["page"]).read_text(encoding="utf-8")
        output = render(module, markdown, layout)
        path = ROOT / "assets" / f"architecture-{identity}.svg"
        if args.write and not args.check:
            path.write_text(output, encoding="utf-8")
        elif not path.exists() or path.read_text(encoding="utf-8") != output:
            stale.append(str(path.relative_to(ROOT)))
    index_path = ROOT / "docs/图示索引.md"
    index_text = inventory()
    if args.write and not args.check:
        index_path.write_text(index_text, encoding="utf-8")
    elif not index_path.exists() or index_path.read_text(encoding="utf-8") != index_text:
        stale.append(str(index_path.relative_to(ROOT)))
    print("\n".join(stale) if stale else "模块架构 SVG 与 Markdown 权威源已同步")
    return int(bool(stale))


if __name__ == "__main__":
    raise SystemExit(main())
