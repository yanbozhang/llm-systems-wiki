import { defineConfig } from 'astro/config';
export default defineConfig({
  site: 'https://yanbozhang.github.io',
  base: '/llm-systems-wiki',
  trailingSlash: 'always',
  publicDir: '../assets',
  output: 'static',
  build: { concurrency: 1 },
  vite: { build: { minify: false, cssMinify: false, rollupOptions: { maxParallelFileOps: 1 } } }
});
