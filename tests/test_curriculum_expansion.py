import importlib.util
import json
import math
from pathlib import Path
import unittest

from examples.knowledge import llm_wiki
from examples.rsi import evaluation, evolution, loop, memory
from scripts import wiki_tool
from tests.test_wiki_tool import CurriculumCase


ROOT = Path(__file__).resolve().parents[1]


class RsiExampleTests(unittest.TestCase):
    def test_persistent_changes_only_include_used_new_values(self):
        self.assertEqual(loop.persistent_changes({"old": None}, {"old": None, "new": 2}, ["old", "new"]), ["new"])
        self.assertEqual(loop.persistent_changes({"skill": 1}, {"skill": 2}, []), [])
        self.assertEqual(loop.persistent_changes({}, {"skill": 2}, ["skill", "skill"]), ["skill"])

    def test_admission_rejects_regression_and_modified_verifier(self):
        self.assertTrue(loop.accept_candidate(0.1, 1))
        self.assertFalse(loop.accept_candidate(0.1, 0.9))
        self.assertFalse(loop.accept_candidate(0.1, 1, verifier_unchanged=False))
        with self.assertRaises(ValueError):
            loop.accept_candidate(math.nan, 1)

    def test_rejected_and_accepted_versions_do_not_alias_inputs(self):
        old, candidate = {"skills": ["old"]}, {"skills": ["new"]}
        for accepted in (False, True):
            result = loop.advance_version(old, candidate, accepted)
            result["skills"].append("mutation")
        self.assertEqual(old, {"skills": ["old"]})
        self.assertEqual(candidate, {"skills": ["new"]})
        with self.assertRaises(ValueError):
            loop.advance_version(old, candidate, 1)

    def test_memory_checks_status_version_and_task_scope(self):
        record = {"id": "skill", "source_id": "run", "source_version": "v1",
                  "status": "verified", "task_families": ["coding"]}
        self.assertEqual(memory.eligible_experience([record], {"run": "v1"}, "coding"), [record])
        self.assertEqual(memory.eligible_experience([record], {"run": "v2"}, "coding"), [])
        self.assertEqual(memory.eligible_experience([record], {"run": "v1"}, "gui"), [])
        self.assertEqual(memory.eligible_experience([{**record, "status": "draft"}], {"run": "v1"}, "coding"), [])

    def test_edit_budget_boundaries_and_adoption(self):
        self.assertTrue(memory.bounded_edit(2, 10, 0.2))
        self.assertFalse(memory.bounded_edit(3, 10, 0.2))
        for args in ((1, 0, 0.2), (11, 10, 0.2), (True, 10, 0.2), (1, 10, math.nan)):
            with self.assertRaises(ValueError):
                memory.bounded_edit(*args)
        self.assertEqual(memory.adoption_rate(["a", "a", "b"], ["a", "a"]), 0.5)
        self.assertEqual(memory.adoption_rate([], []), 0)
        with self.assertRaises(ValueError):
            memory.adoption_rate(["a"], ["unknown"])

    def test_cross_effect_and_pareto_tradeoffs(self):
        self.assertAlmostEqual(evolution.cross_effect(0.5, 0.6, 0.7, 0.85), 0.05)
        candidates = [{"quality": 0.8, "cost": 4}, {"quality": 0.7, "cost": 5}, {"quality": 0.6, "cost": 2}]
        self.assertEqual(evolution.pareto_front(candidates), [candidates[0], candidates[2]])
        self.assertEqual(evolution.pareto_front([candidates[0], candidates[0]]), [candidates[0], candidates[0]])
        self.assertEqual(evolution.pareto_front([]), [])
        with self.assertRaises(ValueError):
            evolution.pareto_front([{"quality": 0.5, "cost": -1}])

    def test_improver_comparison_requires_matched_start_and_budget(self):
        self.assertAlmostEqual(evolution.compare_improvers([0.1, 0.2], [0.2, 0.4], "v1", "v1", 10, 10), 0.15)
        for args in (([], [], "v1", "v1", 10, 10), ([1], [2], "v1", "v2", 10, 10),
                     ([1], [2], "v1", "v1", 10, 20), ([1], [math.inf], "v1", "v1", 10, 10)):
            with self.assertRaises(ValueError):
                evolution.compare_improvers(*args)

    def test_split_and_retention_edge_cases(self):
        self.assertTrue(evaluation.disjoint_splits(["a"], ["b"], ["c"]))
        self.assertFalse(evaluation.disjoint_splits(["a"], ["a"], ["c"]))
        self.assertEqual(evaluation.capability_changes(["a", "b"], ["b", "c"]),
                         {"gained": ["c"], "lost": ["a"], "retention": 0.5})
        self.assertIsNone(evaluation.capability_changes([], ["a"])["retention"])

    def test_costs_include_rejected_candidates_and_allow_negative_gain(self):
        self.assertAlmostEqual(evaluation.net_efficiency(0.1, [2, 3, 1, 4]), 0.01)
        self.assertLess(evaluation.net_efficiency(-0.1, [10]), 0)
        for costs in ([], [0], [-1], [math.nan], [1e308, 1e308]):
            with self.assertRaises(ValueError):
                evaluation.net_efficiency(0.1, costs)

    def test_llm_wiki_layers_publication_and_typed_cycles(self):
        self.assertEqual(llm_wiki.source_layers([{"layer": "raw", "id": "s"}])["raw"], ["s"])
        self.assertFalse(llm_wiki.publication_ready([], {}))
        evidence = [{"source_id": "s", "source_version": "v1", "reviewed": True}]
        self.assertTrue(llm_wiki.publication_ready(evidence, {"s": "v1"}))
        self.assertFalse(llm_wiki.publication_ready(evidence, {"s": "v2"}))
        dependencies = {"a": [("source", "supported_by"), ("b", "requires")],
                        "b": [("a", "requires")], "neighbor": [("a", "related")]}
        self.assertEqual(llm_wiki.wiki_impact(dependencies, ["source"]), ["a", "b"])

    def test_graph_coverage_deduplicates_and_does_not_assume_empty_success(self):
        spec = importlib.util.spec_from_file_location("graph_example", ROOT / "examples/knowledge/graph-wiki.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertEqual(module.provenance_coverage(["a", "a", "b"], ["a"]), 0.5)
        self.assertEqual(module.provenance_coverage([], []), 0)

    def test_new_examples_have_executable_demo_results(self):
        for module in (loop, memory, evolution, evaluation, llm_wiki):
            with self.subTest(module=module.__name__):
                self.assertIsInstance(module.demo(), dict)


class ModuleRotationTests(CurriculumCase):
    def test_shared_weekday_rotates_modules_and_each_modules_topics(self):
        self.modules[3]["rotation_group"] = "agent-systems"
        self.modules.append({"id": "rsi", "title": "RSI", "weekday": 3,
                             "rotation_group": "agent-systems", "page": "wiki/modules/rsi.md"})
        self.write_page("wiki/modules/rsi.md", "# RSI")
        self.add_topic("rsi", "rsi-a")
        self.add_topic("rsi", "rsi-b")
        self.persist_curriculum()
        from datetime import date, timedelta
        dates = [date(2026, 10, 22) + timedelta(weeks=week) for week in range(4)]
        planned = [wiki_tool.plan(day, self.root) for day in dates]
        self.assertEqual([entry["module"] for entry in planned], ["harness", "rsi", "harness", "rsi"])
        self.assertEqual([entry["topic"] for entry in planned if entry["module"] == "rsi"], ["rsi-a", "rsi-b"])

    def test_unrelated_duplicate_weekday_is_still_rejected(self):
        self.modules[1]["weekday"] = 0
        self.persist_curriculum()
        with self.assertRaises(ValueError):
            wiki_tool.load_modules(self.root)

    def test_repository_graph_and_wiki_units_are_disjoint(self):
        topics = json.loads((ROOT / "knowledge/topics.json").read_text())
        selected = {topic["id"]: topic for topic in topics}
        self.assertFalse(set(selected["graph-wiki"]["unit_ids"]) & set(selected["llm-wiki"]["unit_ids"]))
        self.assertEqual(sum(topic["module"] == "rsi" for topic in topics), 4)
