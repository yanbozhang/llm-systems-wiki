import assert from 'node:assert/strict';
import { performance } from 'node:perf_hooks';
import { buildSearchIndex } from '../src/lib/content';
import { createTopicSearch, parseSearchIndex, searchTopics } from '../src/lib/navigation';

const items = parseSearchIndex(buildSearchIndex());
const queries = ['KV cache', 'attention', 'RAG 检索', '工具 状态', '不存在的词', ''];
const started = performance.now();
const search = createTopicSearch(items);
const preparationMs = performance.now() - started;
for (const query of queries) {
  assert.deepEqual(search(query), searchTopics(items, query));
}
const iterations = 1200;
function measure(run: (query: string) => unknown): number {
  for (let iteration = 0; iteration < 60; iteration++) run(queries[iteration % queries.length]);
  const start = performance.now();
  for (let iteration = 0; iteration < iterations; iteration++) run(queries[iteration % queries.length]);
  return performance.now() - start;
}
const uncachedMs = measure(query => searchTopics(items, query));
const preparedMs = measure(search);
console.log(JSON.stringify({
  topics: items.length, iterations, preparationMs,
  uncachedMs, preparedMs, speedup: uncachedMs / preparedMs,
  note: 'Local search microbenchmark; excludes fetching, DOM rendering and user input latency.'
}, null, 2));
