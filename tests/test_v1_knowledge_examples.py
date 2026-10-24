"""知识库教学概率、身份、预算与影响传播的独立契约测试。"""
import copy
import hashlib
import importlib.util
import math
from pathlib import Path
import unittest


def load_example(name):
    p = Path(__file__).resolve().parents[1] / 'examples/knowledge' / (name + '.py')
    spec = importlib.util.spec_from_file_location(name.replace('-', '_'), p)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


rag = load_example('rag')
ingest = load_example('ingestion')
hybrid = load_example('hybrid-search')
graph = load_example('graph-wiki')


class RagTests(unittest.TestCase):
    def test_sequence_and_token_marginals_do_not_commute(self):
        result = rag.rag_marginals([0.6, 0.4], [[0.9, 0.1], [0.2, 0.8]])
        self.assertAlmostEqual(result['sequence_probability'], 0.118)
        self.assertAlmostEqual(result['token_probability'], 0.2356)
        self.assertAlmostEqual(result['per_token_probabilities'][0], 0.62)
        self.assertAlmostEqual(result['per_token_probabilities'][1], 0.38)

    def test_single_token_single_document_and_probability_bounds(self):
        result = rag.rag_marginals([0.6, 0.4], [[0.9], [0.2]])
        self.assertAlmostEqual(result['sequence_probability'], 0.62)
        self.assertAlmostEqual(result['token_probability'], 0.62)
        result = rag.rag_marginals([0, 1], [[1, 1], [0.2, 0.5]])
        self.assertAlmostEqual(result['sequence_probability'], 0.1)
        self.assertAlmostEqual(result['token_probability'], 0.1)
        for priors, rows in (([0.2, 0.2], [[1], [1]]), ([1], [[-0.1]]), ([1], [[float('nan')]]), ([1], [[]])):
            with self.assertRaises(ValueError):
                rag.rag_marginals(priors, rows)

    def test_context_deducts_fixed_and_output_budget_skips_long_chunk(self):
        chunks = [{'source': 'a', 'version': 'v1', 'chunk': 'x', 'tokens': 7},
                  {'source': 'b', 'version': 'v1', 'chunk': 'y', 'tokens': 4},
                  {'source': 'b', 'version': 'v1', 'chunk': 'y', 'tokens': 4},
                  {'source': 'b', 'version': 'v2', 'chunk': 'y', 'tokens': 2}]
        before = copy.deepcopy(chunks)
        result = rag.select_context(chunks, 10, 2, 2)
        self.assertEqual(result, {'selected': [chunks[1], chunks[3]],
                                  'skipped': [('a', 'v1', 'x')], 'remaining_tokens': 0})
        self.assertEqual(chunks, before)

    def test_context_rejects_overcommitted_fixed_budget_and_nonpositive_cost(self):
        with self.assertRaises(ValueError):
            rag.select_context([], 3, 2, 2)
        with self.assertRaises(ValueError):
            rag.select_context([{'source': 'a', 'version': 'v1', 'chunk': 'x', 'tokens': 0}], 3, 0, 0)

    def test_citations_distinguish_unknown_version_from_known_unsupported(self):
        valid, old, irrelevant = ('a', 'v2', 'x'), ('a', 'v1', 'x'), ('b', 'v1', 'y')
        result = rag.audit_citations({'yes': [valid, valid], 'no': [old, irrelevant]},
                                     {valid: {'yes'}, irrelevant: {'other'}})
        self.assertEqual(result, {'claims': [
            {'claim': 'yes', 'supporting': [valid], 'unknown': [], 'supported': True},
            {'claim': 'no', 'supporting': [], 'unknown': [old], 'supported': False}],
            'supported_claims': 1, 'coverage': 0.5})
        self.assertIsNone(rag.audit_citations({}, {})['coverage'])
        self.assertEqual(rag.audit_citations({'empty': []}, {})['coverage'], 0)
        with self.assertRaises(ValueError):
            rag.audit_citations({'bad': [('a', 'v1')]}, {})

    def test_rag_demo_all_three_functions(self):
        result = rag.demo()
        self.assertAlmostEqual(result['probability']['sequence_probability'], 0.118)
        self.assertEqual(result['context']['remaining_tokens'], 2)
        self.assertEqual(result['citations']['supported_claims'], 0)


class IngestionTests(unittest.TestCase):
    def test_raw_normalized_and_parser_identity_are_separate(self):
        crlf = ingest.source_fingerprint('s', 'a\r\nb', 'p1')
        lf = ingest.source_fingerprint('s', 'a\nb', 'p1')
        bare_cr = ingest.source_fingerprint('s', 'a\rb', 'p1')
        normalized = hashlib.sha256(b'a\nb').hexdigest()
        identity = '["s","p1","' + normalized + '"]'
        self.assertEqual(crlf['raw_text_sha256'], hashlib.sha256(b'a\r\nb').hexdigest())
        self.assertEqual(crlf['normalized_text_sha256'], normalized)
        self.assertEqual(crlf['index_identity'], hashlib.sha256(identity.encode()).hexdigest())
        self.assertEqual(crlf['index_identity'], lf['index_identity'])
        self.assertEqual(lf['normalized_text_sha256'], bare_cr['normalized_text_sha256'])
        self.assertNotEqual(crlf['raw_text_sha256'], lf['raw_text_sha256'])
        self.assertNotEqual(crlf['index_identity'], ingest.source_fingerprint('s', 'a\nb', 'p2')['index_identity'])
        self.assertNotEqual(crlf['index_identity'], ingest.source_fingerprint('other', 'a\nb', 'p1')['index_identity'])

    def test_fingerprint_preserves_spaces_negation_and_invalid_identity(self):
        self.assertNotEqual(ingest.source_fingerprint('s', '-1', 'p')['normalized_text_sha256'],
                            ingest.source_fingerprint('s', '1', 'p')['normalized_text_sha256'])
        self.assertNotEqual(ingest.source_fingerprint('s', 'a b', 'p')['normalized_text_sha256'],
                            ingest.source_fingerprint('s', 'ab', 'p')['normalized_text_sha256'])
        for args in (('', 'text', 'p'), ('s', 'text', ''), ('s', None, 'p')):
            with self.assertRaises(ValueError):
                ingest.source_fingerprint(*args)

    def test_versions_classify_changes_missing_and_unavailable_separately(self):
        old, new = {'A': 'old', 'B': 'same', 'C': 'gone', 'D': 'unread'}, {'A': 'new', 'B': 'same', 'E': 'added'}
        before = copy.deepcopy((old, new))
        partial = ingest.classify_versions(old, new, {'D'})
        self.assertEqual(partial, {'added': ['E'], 'changed': ['A'], 'unchanged': ['B'],
                                  'removed': [], 'unobserved': ['C'], 'unavailable': ['D']})
        complete = ingest.classify_versions(old, new, {'D'}, True)
        self.assertEqual(complete['removed'], ['C'])
        self.assertEqual(complete['unobserved'], [])
        self.assertEqual(complete['unavailable'], ['D'])
        self.assertEqual((old, new), before)
        with self.assertRaises(ValueError):
            ingest.classify_versions(old, new, {'A'})

    def test_remaining_support_plans_rebuild_delete_and_unchanged(self):
        supports = {'entity': {'a', 'b'}, 'relation': {'a'}, 'other': {'c'}}
        before = copy.deepcopy(supports)
        self.assertEqual(ingest.reconcile_support(supports, {'a'}), {
            'unchanged': ['other'], 'rebuild': ['entity'], 'delete': ['relation'],
            'surviving_supports': {'entity': ['b'], 'relation': [], 'other': ['c']}})
        self.assertEqual(supports, before)
        self.assertEqual(ingest.reconcile_support(supports, {'unrelated'})['unchanged'], ['entity', 'other', 'relation'])
        with self.assertRaises(ValueError):
            ingest.reconcile_support({'unknown': set()}, set())

    def test_ingestion_demo_all_three_functions(self):
        result = ingest.demo()
        self.assertEqual(result['delta']['changed'], ['A'])
        self.assertEqual(result['delta']['removed'], [])
        self.assertEqual(result['support']['rebuild'], ['entity'])
        self.assertEqual(result['fingerprint']['normalized_text_sha256'], hashlib.sha256(b'a\nb').hexdigest())


class HybridSearchTests(unittest.TestCase):
    def test_bm25_idf_frequency_saturation_and_length_factor(self):
        idf = math.log(8 / 3)  # 三文档仅一篇含查询词。
        once = hybrid.bm25_scores(['rare'], [['rare', 'x'], ['common', 'x'], ['common', 'y']])
        twice = hybrid.bm25_scores(['rare'], [['rare', 'rare'], ['common', 'x'], ['common', 'y']])
        long = hybrid.bm25_scores(['rare'], [['rare', 'x', 'x', 'x'], ['x'], ['y']])
        self.assertAlmostEqual(once[0], idf)
        self.assertAlmostEqual(twice[0], idf * 1.375)
        self.assertAlmostEqual(long[0], idf * 2.2 / 3.1)
        self.assertLess(twice[0], 2 * once[0])
        self.assertEqual(once[1:], [0, 0])

    def test_bm25_binary_query_empty_documents_and_parameter_boundaries(self):
        docs = [['x'], ['x', 'x'], []]
        self.assertEqual(hybrid.bm25_scores(['x', 'x'], docs), hybrid.bm25_scores(['x'], docs))
        scores = hybrid.bm25_scores(['x'], docs, k1=0, b=0)
        self.assertAlmostEqual(scores[0], math.log(1.6))
        self.assertEqual(scores[0], scores[1])
        self.assertEqual(hybrid.bm25_scores([], docs), [0, 0, 0])
        self.assertEqual(hybrid.bm25_scores(['x'], []), [])
        self.assertEqual(hybrid.bm25_scores(['x'], [[], []]), [0, 0])
        with self.assertRaises(ValueError):
            hybrid.bm25_scores(['x'], docs, b=1.1)

    def test_rrf_rank_one_missing_contribution_weights_and_tie_order(self):
        self.assertEqual(hybrid.reciprocal_rank_fusion([['a', 'b'], ['b', 'c']], constant=0, weights=[2, 1]),
                         [('a', 2), ('b', 2), ('c', 0.5)])
        self.assertEqual(hybrid.reciprocal_rank_fusion([['a'], ['b']], weights=[0, 0]), [('a', 0), ('b', 0)])

    def test_rrf_does_not_apply_engine_specific_rank_bonus(self):
        result = hybrid.reciprocal_rank_fusion([['A', 'left', 'B'],
                                               ['x', 'y', 'B', 'd4', 'd5', 'd6', 'd7', 'd8', 'd9', 'A']])
        scores = dict(result)
        self.assertAlmostEqual(scores['A'], 1 / 61 + 1 / 70)
        self.assertAlmostEqual(scores['B'], 2 / 63)
        self.assertGreater(scores['B'], scores['A'])
        self.assertEqual(result[0][0], 'B')

    def test_rrf_rejects_repeated_documents_and_invalid_weights(self):
        for rankings, kwargs in (([['a', 'a']], {}), ([['a']], {'weights': []}),
                                  ([['a']], {'weights': [-1]}), ([['a']], {'constant': -1})):
            with self.assertRaises(ValueError):
                hybrid.reciprocal_rank_fusion(rankings, **kwargs)

    def test_rerank_preserves_funnel_and_explicit_fallback(self):
        result = hybrid.rerank_audit(['C', 'A'], {'A': 0.9, 'C': 0.1}, {'A', 'B'}, 1)
        self.assertEqual(result, {'selected': ['A'], 'mode': 'reranked', 'missing_from_candidates': ['B'],
                                  'candidate_recall': 0.5, 'selected_recall': 0.5})
        fallback = hybrid.rerank_audit(['C', 'A'], None, {'A', 'B'}, 1)
        self.assertEqual(fallback['selected'], ['C'])
        self.assertEqual(fallback['mode'], 'fallback')
        self.assertEqual(fallback['selected_recall'], 0)
        self.assertIsNone(hybrid.rerank_audit([], {}, set(), 1)['candidate_recall'])

    def test_rerank_rejects_added_missing_or_nonfinite_model_scores(self):
        for scores in ({}, {'A': 1, 'B': 2}, {'A': float('nan')}):
            with self.assertRaises(ValueError):
                hybrid.rerank_audit(['A'], scores, {'A'}, 1)
        with self.assertRaises(ValueError):
            hybrid.rerank_audit(['A', 'A'], None, {'A'}, 1)

    def test_hybrid_demo_all_three_functions(self):
        result = hybrid.demo()
        self.assertEqual(len(result['bm25']), 3)
        self.assertGreater(result['bm25'][0], result['bm25'][1])
        self.assertEqual(result['rrf'][0][0], 'B')
        self.assertEqual(result['rerank']['missing_from_candidates'], ['B'])


class GraphWikiTests(unittest.TestCase):
    def test_local_context_entity_priority_incident_edges_and_first_owner(self):
        relations = [{'source': 'B', 'target': 'A', 'chunks': {'b'}},
                     {'source': 'C', 'target': 'A', 'chunks': {'b'}},
                     {'source': 'B', 'target': 'D', 'chunks': {'c'}}]
        result = graph.local_graph_context(['A', 'B'], {'A': ['a', 'b'], 'B': ['b', 'c']}, relations)
        self.assertEqual(result, [{'chunk': 'b', 'entity_rank': 0, 'edge_count': 2},
                                 {'chunk': 'a', 'entity_rank': 0, 'edge_count': 0},
                                 {'chunk': 'c', 'entity_rank': 1, 'edge_count': 1}])
        self.assertEqual(graph.local_graph_context(['missing'], {}, relations), [])
        with self.assertRaises(ValueError):
            graph.local_graph_context(['A', 'A'], {}, [])

    def test_reduce_filters_zero_sorts_and_stops_at_first_over_budget(self):
        points = [{'text': 'b', 'score': 70, 'tokens': 3}, {'text': 'a', 'score': 80, 'tokens': 4},
                  {'text': 'zero', 'score': 0, 'tokens': 1}, {'text': 'small', 'score': 60, 'tokens': 1}]
        before = copy.deepcopy(points)
        self.assertEqual(graph.reduce_points(points, 5), {'selected': [points[1]], 'remaining_tokens': 1, 'status': 'ready'})
        self.assertEqual(points, before)
        self.assertEqual(graph.reduce_points([dict(points[1], tokens=7), points[0]], 5),
                         {'selected': [], 'remaining_tokens': 5, 'status': 'budget_exhausted'})

    def test_reduce_empty_zero_score_and_exact_budget(self):
        self.assertEqual(graph.reduce_points([], 2), {'selected': [], 'remaining_tokens': 2, 'status': 'no_data'})
        self.assertEqual(graph.reduce_points([{'score': 0, 'tokens': 1}], 2)['status'], 'no_data')
        self.assertEqual(graph.reduce_points([{'score': 100, 'tokens': 2}], 2)['remaining_tokens'], 0)
        with self.assertRaises(ValueError):
            graph.reduce_points([{'score': 101, 'tokens': 1}], 2)

    def test_wiki_impact_uses_reverse_typed_edges_not_related(self):
        links = {'claim': [('source', 'supported_by')], 'topic': [('claim', 'requires')],
                 'exercise': [('topic', 'requires')], 'neighbor': [('topic', 'related')]}
        before = copy.deepcopy(links)
        self.assertEqual(graph.wiki_impact(links, {'source'}), ['claim', 'exercise', 'topic'])
        self.assertEqual(graph.wiki_impact(links, {'topic'}), ['exercise'])
        self.assertEqual(graph.wiki_impact(links, {'topic'}, ('related',)), ['neighbor'])
        self.assertEqual(links, before)

    def test_wiki_impact_cycles_terminate_and_exclude_roots(self):
        links = {'a': [('b', 'requires')], 'b': [('a', 'requires')], 'c': [('a', 'requires')]}
        self.assertEqual(graph.wiki_impact(links, {'a'}), ['b', 'c'])
        self.assertEqual(graph.wiki_impact(links, set()), [])
        self.assertEqual(graph.wiki_impact(links, {'unknown'}), [])

    def test_graph_demo_all_three_functions(self):
        result = graph.demo()
        self.assertEqual([x['chunk'] for x in result['local']], ['b', 'a', 'c'])
        self.assertEqual(result['global']['remaining_tokens'], 1)
        self.assertEqual(result['impact'], ['claim', 'exercise', 'topic'])

from tests.v1_entrypoint_support import assert_cli_matches_demo, assert_quiet_import


class EntrypointTests(unittest.TestCase):
    def test_rag_cli(self):
        assert_cli_matches_demo(self, 'examples/knowledge/rag.py')

    def test_rag_quiet_import(self):
        assert_quiet_import(self, 'examples/knowledge/rag.py')

    def test_ingestion_cli(self):
        assert_cli_matches_demo(self, 'examples/knowledge/ingestion.py')

    def test_ingestion_quiet_import(self):
        assert_quiet_import(self, 'examples/knowledge/ingestion.py')

    def test_hybrid_search_cli(self):
        assert_cli_matches_demo(self, 'examples/knowledge/hybrid-search.py')

    def test_hybrid_search_quiet_import(self):
        assert_quiet_import(self, 'examples/knowledge/hybrid-search.py')

    def test_graph_wiki_cli(self):
        assert_cli_matches_demo(self, 'examples/knowledge/graph-wiki.py')

    def test_graph_wiki_quiet_import(self):
        assert_quiet_import(self, 'examples/knowledge/graph-wiki.py')
