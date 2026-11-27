"""从权威清单生成README使用的静态知识与能力地图。"""
import argparse
from html import escape
import json
from pathlib import Path
import unicodedata


ROOT = Path(__file__).resolve().parents[1]


def text_lines(text, limit=25):
    lines, current, used = [], "", 0
    for character in text:
        size = 1 if unicodedata.east_asian_width(character) in "WF" else 0.55
        if used + size > limit and current:
            lines.append(current)
            current, used = "", 0
        current += character
        used += size
    return lines + ([current] if current else [])


def render(root=ROOT, capabilities=False, preview=False):
    def load(name):
        return json.loads((Path(root) / "knowledge" / (name + ".json")).read_text(encoding="utf-8"))
    modules, topics, units, goals = (load(name) for name in ("modules", "topics", "units", "capabilities"))
    title = f'{len(modules)}模块{"能力" if capabilities else "知识"}地图'
    subtitle = f'{len(topics)}个主题 · {len(units)}个知识点 · {len(goals)}项分层能力'
    levels = {"understand": "理解", "derive": "推导", "build": "实践", "practice": "实践", "evaluate": "评估"}
    cards = []
    for module in modules:
        selected = [topic for topic in topics if topic["module"] == module["id"]]
        selected_ids = {topic["id"] for topic in selected}
        selected_goals = [goal for goal in goals if goal["module"] == module["id"]]
        entries = [
            f'{levels.get(goal["level"], goal["level"])} · {goal["outcome"]}'
            for goal in selected_goals
        ] if capabilities else [topic["title"] for topic in selected]
        lines = [line for entry in (entries[:1] if preview else entries) for line in text_lines(entry)]
        count = sum(unit["topic"] in selected_ids for unit in units)
        detail = f'{len(selected)} 主题 / {count} 知识点 / {len(selected_goals)} 能力'
        cards.append((module, lines, detail))
    row_heights = [
        max(176, 118 + max(len(card[1]) for card in cards[index:index + 2]) * 27)
        for index in range(0, len(cards), 2)
    ]
    height = 190 + sum(row_heights) + max(0, len(row_heights) - 1) * 22
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1120" height="{height}" viewBox="0 0 1120 {height}" role="img" aria-labelledby="title description">',
        f'<title id="title">{title}</title><desc id="description">{subtitle}；模块为学习分类，不表示严格执行顺序。{"预览每模块首项，完整地图保留全部条目。" if preview else "全部条目由权威清单生成。"}</desc>',
        f'<rect width="1120" height="{height}" rx="16" fill="#ffffff"/>',
        '<g font-family="Inter, PingFang SC, Microsoft YaHei, Noto Sans CJK SC, sans-serif" fill="#183654">',
        '<text x="36" y="36" font-size="15" letter-spacing="3" fill="#607286">LLM SYSTEMS / LEARNING ATLAS</text>',
        f'<text x="36" y="77" font-size="32" font-weight="700">{title}</text>',
        f'<text x="36" y="109" font-size="19" fill="#607286">{subtitle}</text>',
    ]
    for position, (module, lines, detail) in enumerate(cards):
        row = position // 2
        left = 36 + (position % 2) * 536
        top = 138 + sum(row_heights[:row]) + row * 22
        card_height = row_heights[row]
        parts.extend([
            f'<rect x="{left}" y="{top}" width="512" height="{card_height}" rx="12" fill="#f6f8fc" stroke="#ccd6e3"/>',
            f'<rect x="{left + 18}" y="{top + 21}" width="36" height="30" rx="7" fill="#e5edfa"/>',
            f'<text x="{left + 36}" y="{top + 43}" text-anchor="middle" font-size="18" fill="#3158a0">{position + 1:02}</text>',
            f'<text x="{left + 66}" y="{top + 44}" font-size="25" font-weight="650">{escape(module["title"])}</text>',
            f'<text x="{left + 20}" y="{top + card_height - 21}" font-size="18" fill="#607286">{detail}</text>',
        ])
        for index, line in enumerate(lines):
            parts.append(f'<text x="{left + 20}" y="{top + 82 + index * 27}" font-size="19">{escape(line)}</text>')
    footer = "预览仅列各模块首项；完整清单见原图。学习目标不等于已完成真实复现实验。" if preview else "由 knowledge 清单生成；编号表示目录顺序，不代表依赖关系或学习成果。"
    parts.extend([f'<text x="36" y="{height - 19}" font-size="18" fill="#607286">{footer}</text>', '</g></svg>'])
    return "\n".join(parts) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    stale = []
    for name, is_capability in (("知识地图", False), ("能力地图", True)):
        for suffix in ("", "预览"):
            text = render(capabilities=is_capability, preview=bool(suffix))
            path = ROOT / "assets" / (name + suffix + ".svg")
            if args.write and not args.check:
                path.write_text(text, encoding="utf-8")
            elif not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(str(path.relative_to(ROOT)))
    print("\n".join(stale) if stale else "知识与能力地图已同步")
    return int(bool(stale))


if __name__ == "__main__":
    raise SystemExit(main())
