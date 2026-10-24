"""按规范化等价、集合公式和左闭右开日期区间验证教学候选。"""
import copy
import hashlib
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch


path = Path(__file__).resolve().parents[1] / 'examples/benchmark/benchmark-contamination.py'
spec = importlib.util.spec_from_file_location('benchmark_contamination_example', path)
example = importlib.util.module_from_spec(spec)
spec.loader.exec_module(example)


class NormalizedFingerprintTests(unittest.TestCase):
    def test_nfkc_casefold_and_whitespace_match_known_utf8_bytes(self):
        expected = hashlib.sha256(b'a b').hexdigest()
        self.assertEqual(example.normalized_fingerprint(' Ａ\t B\n'), expected)
        self.assertEqual(example.normalized_fingerprint('a b'), expected)

    def test_nfkc_precedes_casefold_and_casefold_is_not_lower(self):
        self.assertEqual(example.normalized_fingerprint('ϒ'), hashlib.sha256('υ'.encode()).hexdigest())
        self.assertEqual(example.normalized_fingerprint('Straße'), hashlib.sha256(b'strasse').hexdigest())

    def test_punctuation_and_numbers_are_preserved(self):
        self.assertNotEqual(example.normalized_fingerprint('a,b'), example.normalized_fingerprint('ab'))
        self.assertNotEqual(example.normalized_fingerprint('a 10'), example.normalized_fingerprint('a 100'))

    def test_empty_normalized_text_and_non_string_are_rejected(self):
        for value in ('', ' \t\n', '\u3000', None, 1, []):
            with self.assertRaises(ValueError, msg=repr(value)):
                example.normalized_fingerprint(value)


class NgramJaccardTests(unittest.TestCase):
    def test_documented_bigram_intersection_two_union_four(self):
        self.assertEqual(example.ngram_jaccard('a b c d', 'a b c e'), 0.5)

    def test_duplicate_grams_are_set_members_not_frequencies(self):
        self.assertEqual(example.ngram_jaccard('a a a', 'a a'), 1)
        self.assertEqual(example.ngram_jaccard('a a b', 'a c', n=1), 1 / 3)

    def test_symmetry_probability_range_and_disjoint_sets(self):
        for left, right in (('a b c', 'b c d'), ('x y', 'a b'), ('a b', 'a b')):
            result = example.ngram_jaccard(left, right)
            self.assertEqual(result, example.ngram_jaccard(right, left))
            self.assertTrue(0 <= result <= 1)
        self.assertEqual(example.ngram_jaccard('x y', 'a b'), 0)

    def test_short_either_side_and_empty_both_are_undefined(self):
        for left, right in (('a', 'a b'), ('a b', 'a'), ('', ''), ('', 'a b')):
            self.assertIsNone(example.ngram_jaccard(left, right))
        self.assertIsNone(example.ngram_jaccard('a b', 'a b', n=3))

    def test_invalid_n_and_non_string_inputs_are_rejected(self):
        for n in (0, -1, 1.5, True):
            with self.assertRaises(ValueError):
                example.ngram_jaccard('a b', 'a b', n)
        with self.assertRaises(ValueError):
            example.ngram_jaccard(None, 'a b')
        with self.assertRaises(ValueError):
            example.ngram_jaccard('a b', [])


class ReleaseMembershipTests(unittest.TestCase):
    def setUp(self):
        self.items = [{'id': 'a', 'released': '2026-01-01', 'removed': '2026-03-01'},
                      {'id': 'b', 'released': '2026-02-01'}]

    def test_release_inclusive_and_removal_exclusive(self):
        self.assertEqual(example.release_membership(self.items, '2025-12-31'), [])
        self.assertEqual(example.release_membership(self.items, '2026-01-01'), ['a'])
        self.assertEqual(example.release_membership(self.items, '2026-02-15'), ['a', 'b'])
        self.assertEqual(example.release_membership(self.items, '2026-03-01'), ['b'])

    def test_zero_length_lifetime_and_explicit_no_removal(self):
        items = [{'id': 'zero', 'released': '2026-02-01', 'removed': '2026-02-01'},
                 {'id': 'open', 'released': '2026-02-01', 'removed': None}]
        self.assertEqual(example.release_membership(items, '2026-02-01'), ['open'])
        self.assertEqual(example.release_membership(items, '2099-01-01'), ['open'])

    def test_sorted_ids_input_preservation_and_empty_snapshot(self):
        items = [{'id': 'z', 'released': '2024-02-29'}, {'id': 'a', 'released': '2024-02-29'}]
        before = copy.deepcopy(items)
        self.assertEqual(example.release_membership(items, '2024-02-29'), ['a', 'z'])
        self.assertEqual(items, before)
        self.assertEqual(example.release_membership([], '2026-01-01'), [])

    def test_snapshot_requires_strict_calendar_date(self):
        for as_of in ('20260301', '2026-W09-7', '2026-3-01', '2026-02-29', '2026-01-01T00:00:00', None):
            with self.assertRaises(ValueError, msg=repr(as_of)):
                example.release_membership(self.items, as_of)

    def test_each_item_date_is_strict_and_removal_cannot_precede_release(self):
        for row in ({'id': 'a', 'released': '20260101'},
                    {'id': 'a', 'released': '2026-01-01', 'removed': '20260102'},
                    {'id': 'a', 'released': '2026-03-01', 'removed': '2026-02-01'},
                    {'id': 'a'}):
            with self.assertRaises(ValueError):
                example.release_membership([row], '2026-03-01')

    def test_duplicate_ids_rejected_even_outside_snapshot(self):
        with self.assertRaises(ValueError):
            example.release_membership([self.items[0], dict(self.items[0])], '2025-01-01')

    def test_invalid_record_shape_and_empty_or_non_string_id_rejected(self):
        for rows in (None, {}, [None], ['row'], [{'released': '2026-01-01'}],
                     [{'id': '', 'released': '2026-01-01'}], [{'id': 1, 'released': '2026-01-01'}]):
            with self.assertRaises(ValueError):
                example.release_membership(rows, '2026-03-01')


class ContaminationDemoTests(unittest.TestCase):
    def test_demo_runs_real_functions_and_returns_teaching_result(self):
        with patch.object(example, 'normalized_fingerprint', wraps=example.normalized_fingerprint) as fingerprint, \
             patch.object(example, 'ngram_jaccard', wraps=example.ngram_jaccard) as jaccard, \
             patch.object(example, 'release_membership', wraps=example.release_membership) as membership:
            result = example.demo()
        self.assertEqual(fingerprint.call_count, 2)
        jaccard.assert_called_once()
        membership.assert_called_once()
        self.assertEqual(result, {'same_normalized_text': True, 'bigram_similarity': 0.5, 'snapshot': ['b']})

from tests.v1_entrypoint_support import assert_cli_matches_demo, assert_quiet_import


class EntrypointTests(unittest.TestCase):
    def test_benchmark_contamination_cli(self):
        assert_cli_matches_demo(self, 'examples/benchmark/benchmark-contamination.py')

    def test_benchmark_contamination_quiet_import(self):
        assert_quiet_import(self, 'examples/benchmark/benchmark-contamination.py')
