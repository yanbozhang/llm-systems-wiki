"""网站依赖排除与受管文档链接检查；依据 schema/维护工具契约.md。
沿用既有 TempCase，所有文件写入隔离的 TemporaryDirectory。
"""
from scripts import wiki_tool as wiki
from tests.test_wiki_tool import TempCase


class WebScopeTests(TempCase):
    def setUp(self):
        super().setUp()
        self.fixture()

    def write_markdown(self, relative, body):
        path = self.root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body, encoding="utf-8")

    def assert_broken_paths(self, *paths):
        errors = wiki.check(self.root)
        self.assertEqual(len(errors), len(paths), errors)
        for path in paths:
            matches = [error for error in errors if error.startswith(path + ":")]
            self.assertEqual(len(matches), 1, errors)
            self.assertIn("断链", matches[0])
        return errors

    def test_node_modules_markdown_is_excluded(self):
        self.write_markdown("web/node_modules/package/README.md", "[第三方](missing.md)")
        self.assertEqual(wiki.check(self.root), [])

    def test_dist_markdown_is_excluded(self):
        self.write_markdown("web/dist/guide/index.md", "[产物](missing.md)")
        self.assertEqual(wiki.check(self.root), [])

    def test_astro_markdown_is_excluded(self):
        self.write_markdown("web/.astro/generated/README.md", "[生成内容](missing.md)")
        self.assertEqual(wiki.check(self.root), [])

    def test_managed_web_readme_broken_link_is_reported(self):
        self.write_markdown("web/README.md", "[开发说明](missing.md)")
        self.assert_broken_paths("web/README.md")

    def test_managed_web_readme_valid_link_is_allowed(self):
        self.write_markdown("web/docs/setup.md", "# 开发环境")
        self.write_markdown("web/README.md", "[开发说明](docs/setup.md#开发环境)")
        self.assertEqual(wiki.check(self.root), [])

    def test_nested_managed_web_markdown_remains_checked(self):
        self.write_markdown("web/src/docs/guide.md", "[开发说明](missing.md)")
        self.assert_broken_paths("web/src/docs/guide.md")

    def test_similar_directory_names_are_not_excluded(self):
        paths = ("web/node_modules-notes/README.md", "web/distribution/README.md", "web/.astro-notes/README.md")
        for path in paths:
            self.write_markdown(path, "[受管正文](missing.md)")
        self.assert_broken_paths(*paths)

    def test_excluded_markdown_is_not_read_as_utf8(self):
        for directory in ("node_modules", "dist", ".astro"):
            path = self.root / "web" / directory / "README.md"
            path.parent.mkdir(parents=True)
            path.write_bytes(b"\xff\xfe")
        self.assertEqual(wiki.check(self.root), [])

    def test_ignored_errors_do_not_hide_managed_readme_error(self):
        for directory in ("node_modules", "dist", ".astro"):
            self.write_markdown("web/" + directory + "/README.md", "[忽略](generated-missing.md)")
        self.write_markdown("web/README.md", "[应检查](managed-missing.md)")
        errors = self.assert_broken_paths("web/README.md")
        self.assertIn("managed-missing.md", errors[0])
        self.assertNotIn("generated-missing.md", errors[0])

    def test_source_evidence_checks_remain_active(self):
        self.write_markdown("web/node_modules/demo/README.md", "[忽略](missing.md)")
        self.claims[0]["evidence"][0]["source_version"] = "wrong-version"
        self.persist_fixture()
        errors = wiki.check(self.root)
        self.assertEqual(len(errors), 1, errors)
        self.assertIn("来源版本无效", errors[0])

    def test_existing_generated_directory_exclusions_are_preserved(self):
        for directory in (".git", ".venv", "flux", "site"):
            self.write_markdown(directory + "/README.md", "[原有排除](missing.md)")
        self.assertEqual(wiki.check(self.root), [])

    def test_generated_directories_outside_web_are_also_excluded(self):
        for directory in ("node_modules", "dist", ".astro"):
            self.write_markdown(directory + "/package/README.md", "[忽略](missing.md)")
        self.assertEqual(wiki.check(self.root), [])
