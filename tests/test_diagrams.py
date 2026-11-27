import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

from scripts import render_diagrams, render_maps


ROOT = Path(__file__).resolve().parents[1]
NAMESPACE = {"svg": "http://www.w3.org/2000/svg"}


class DiagramTests(unittest.TestCase):
    def test_all_module_exports_match_the_markdown_source(self):
        modules = {module["id"]: module for module in json.loads((ROOT / "knowledge/modules.json").read_text())}
        self.assertEqual(set(modules), set(render_diagrams.LAYOUTS) - {"harness-improvement"})
        for identity, layout in render_diagrams.LAYOUTS.items():
            with self.subTest(diagram=identity):
                module = modules[layout.get("module", identity)]
                markdown = (ROOT / module["page"]).read_text()
                output = render_diagrams.render(module, markdown, layout)
                self.assertEqual((ROOT / "assets" / f"architecture-{identity}.svg").read_text(), output)
                self.assertIn(f"architecture-{identity}.svg", markdown)
                document = ET.fromstring(output)
                self.assertIsNotNone(document.find("svg:title", NAMESPACE))
                self.assertIsNotNone(document.find("svg:desc", NAMESPACE))
                self.assertNotIn("foreignObject", output)
                self.assertNotIn("<script", output)

    def test_connectors_are_orthogonal_and_do_not_cross_node_interiors(self):
        modules = {module["id"]: module for module in json.loads((ROOT / "knowledge/modules.json").read_text())}
        for identity, layout in render_diagrams.LAYOUTS.items():
            module = modules[layout.get("module", identity)]
            _, edges = render_diagrams.parse_graph((ROOT / module["page"]).read_text())
            for origin, _, _, target in edges:
                if "only" in layout and (origin, target) not in layout["only"]:
                    continue
                if origin not in layout["nodes"] or target not in layout["nodes"]:
                    continue
                points = layout["routes"].get((origin, target))
                if points is None:
                    points = render_diagrams.route(layout["nodes"][origin], layout["nodes"][target])
                for start, end in zip(points, points[1:]):
                    self.assertTrue(start[0] == end[0] or start[1] == end[1])
                    for node, position in layout["nodes"].items():
                        left, top, width, height = render_diagrams.box(position)
                        if start[0] == end[0]:
                            crosses = left < start[0] < left + width and max(min(start[1], end[1]), top) < min(max(start[1], end[1]), top + height)
                        else:
                            crosses = top < start[1] < top + height and max(min(start[0], end[0]), left) < min(max(start[0], end[0]), left + width)
                        self.assertFalse(crosses, f"{identity}: {origin} → {target} crosses {node}")

    def test_maps_have_real_previews_and_all_full_entries(self):
        for capabilities, name in ((False, "知识地图"), (True, "能力地图")):
            full = render_maps.render(capabilities=capabilities)
            preview = render_maps.render(capabilities=capabilities, preview=True)
            self.assertNotEqual(full, preview)
            self.assertLess(int(ET.fromstring(preview).attrib["height"]), int(ET.fromstring(full).attrib["height"]))
            for suffix, output in (("", full), ("预览", preview)):
                self.assertEqual((ROOT / "assets" / f"{name}{suffix}.svg").read_text(), output)
                self.assertEqual(ET.fromstring(output).attrib["role"], "img")
            text = "".join(ET.fromstring(full).itertext())
            entries = json.loads((ROOT / "knowledge" / ("capabilities.json" if capabilities else "topics.json")).read_text())
            for entry in entries:
                self.assertIn(entry["outcome" if capabilities else "title"], text)

    def test_parser_rejects_unknown_endpoints(self):
        with self.assertRaises(ValueError):
            render_diagrams.parse_graph('```mermaid\nflowchart LR\n A["输入"] --> Missing\n```')

    def test_parser_never_silently_drops_unsupported_edges(self):
        with self.assertRaises(ValueError):
            render_diagrams.parse_graph('```mermaid\nflowchart LR\n A["输入"] --> B["输出"]\n A --> B --> A\n```')
        with self.assertRaises(ValueError):
            render_diagrams.parse_graph('```mermaid\nflowchart LR\n A["输入"] --> B["输出"]\n A["另一个标签"] --> B\n```')

    def test_inventory_stays_in_sync(self):
        self.assertEqual((ROOT / "docs/图示索引.md").read_text(), render_diagrams.inventory())

    def test_unicode_wrapping_escapes_svg_labels(self):
        self.assertEqual("".join(render_diagrams.wrap("中文与 R&D <test>", 5)), "中文与 R&D <test>")


if __name__ == "__main__":
    unittest.main()
