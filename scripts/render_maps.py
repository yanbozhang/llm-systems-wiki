"""从权威清单生成README使用的静态知识与能力地图。"""
import argparse
from html import escape
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def render(root=ROOT, capabilities=False):
    def load(name):
        return json.loads((Path(root) / "knowledge" / (name + ".json")).read_text(encoding="utf-8"))
    modules, topics, units, goals = (load(name) for name in ("modules", "topics", "units", "capabilities"))
    height = 150 + ((len(modules) + 1) // 2) * 140
    title = f'{len(modules)}模块{"能力" if capabilities else "知识"}地图'
    subtitle = f'{len(topics)}个主题 · {len(units)}个知识点 · {len(goals)}项分层能力'
    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="{height}" viewBox="0 0 1100 {height}" role="img" aria-labelledby="title description">',
        f'<title id="title">{title}</title><desc id="description">{subtitle}；先系统架构，再主题总览，最后细化知识点。</desc>',
        f'<rect width="1100" height="{height}" fill="#f8f9f6"/>',
        '<g font-family="PingFang SC, Microsoft YaHei, sans-serif" fill="#202824">',
        f'<text x="35" y="48" font-size="28" font-weight="700">{title}</text>',
        f'<text x="35" y="78" font-size="16" fill="#59675f">{subtitle}</text>',
    ]
    for position, module in enumerate(modules):
        left, top = 35 + (position % 2) * 535, 105 + (position // 2) * 140
        selected = {topic["id"] for topic in topics if topic["module"] == module["id"]}
        count = sum(unit["topic"] in selected for unit in units)
        goal_count = sum(goal["module"] == module["id"] for goal in goals)
        route = "理解 → 推导 → 实践 → 评估" if capabilities else "系统架构 → 主题总览 → 细化知识点"
        detail = f'{len(selected)}个主题 · {count}个知识点 · {goal_count}项能力'
        parts.extend([
            f'<rect x="{left}" y="{top}" width="500" height="116" rx="12" fill="#ffffff" stroke="#d9e0d9"/>',
            f'<text x="{left + 22}" y="{top + 35}" font-size="21" font-weight="650">{escape(module["title"])}</text>',
            f'<text x="{left + 22}" y="{top + 67}" font-size="15" fill="#3158d4">{route}</text>',
            f'<text x="{left + 22}" y="{top + 95}" font-size="13" fill="#59675f">{detail}</text>',
        ])
    parts.extend([f'<text x="35" y="{height - 20}" font-size="13" fill="#59675f">由knowledge清单生成；教学模型与真实复现实验保持区分。</text>', '</g></svg>'])
    return "\n".join(parts) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    stale = []
    for name, is_capability in (("知识地图", False), ("能力地图", True)):
        text = render(capabilities=is_capability)
        for suffix in ("", "预览"):
            path = ROOT / "assets" / (name + suffix + ".svg")
            if args.write and not args.check:
                path.write_text(text, encoding="utf-8")
            elif not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(str(path.relative_to(ROOT)))
    print("\n".join(stale) if stale else "知识与能力地图已同步")
    return int(bool(stale))


if __name__ == "__main__":
    raise SystemExit(main())
