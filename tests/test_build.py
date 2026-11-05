"""Tests for scripts/build.py — the static site builder."""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build  # noqa: E402


class BuildTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        out = Path(cls.tmp.name)
        cls.info = build.build(out)
        cls.out = out

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_all_pages_written(self):
        for name in self.info["pages"]:
            p = self.out / name
            self.assertTrue(p.exists(), f"missing {p}")
            self.assertGreater(p.stat().st_size, 500, f"{name} suspiciously small")

    def test_every_page_is_plain_html_skeleton(self):
        for name in self.info["pages"]:
            t = (self.out / name).read_text(encoding="utf-8")
            for needle in ("<!DOCTYPE html>", 'charset="utf-8"', "</html>"):
                self.assertIn(needle, t, f"{name} lacks {needle}")

    def test_index_links_to_all_chapters(self):
        t = (self.out / "index.html").read_text(encoding="utf-8")
        for slug, _ in build.CHAPTERS:
            self.assertIn(slug.replace(".md", ".html"), t)

    def test_question_cards_found(self):
        qs = self.info["questions"]
        self.assertGreaterEqual(len(qs), 30, "expected a real question bank haul")
        self.assertTrue(all(q["q"].strip() for q in qs))
        # every card id is unique
        ids = [q["id"] for q in qs]
        self.assertEqual(len(ids), len(set(ids)))

    def test_index_shows_card_count_and_cards(self):
        t = (self.out / "index.html").read_text(encoding="utf-8")
        self.assertIn(f'Question bank cards ({len(self.info["questions"])} questions)', t)
        self.assertIn('class="question"', t)

    def test_bank_pages_render_card_structure(self):
        t = (self.out / "01-bank-early-career.html").read_text(encoding="utf-8")
        self.assertIn('class="qdetails"', t)
        self.assertIn("Listen for:", t)
        self.assertIn("Why it's included:", t)

    def test_glossary_terms_present(self):
        t = (self.out / "08-glossary.html").read_text(encoding="utf-8")
        for term in ("Ollama", "OpenAI-compatible", "Structured interview"):
            self.assertIn(term, t)

    def test_score_sheet_table_rendered(self):
        t = (self.out / "07-score-sheets.html").read_text(encoding="utf-8")
        self.assertIn("<table>", t)
        self.assertIn("<th>", t)

    def test_internal_md_links_rewrite_to_html(self):
        t = (self.out / "00-introduction.html").read_text(encoding="utf-8")
        self.assertNotIn(".md\"", t)
        self.assertIn('href="08-glossary.html"', t)

    def test_char_escaping(self):
        t = (self.out / "08-glossary.html").read_text(encoding="utf-8")
        self.assertNotIn("<script", t.lower())

    def test_licence_credit_visible(self):
        for name in ("index.html", "01-bank-early-career.html"):
            t = (self.out / name).read_text(encoding="utf-8")
            self.assertIn("2026 Asdale Dynamics, LLC", t)


class RendererUnitTest(unittest.TestCase):
    def test_inline_bold_em_code_link(self):
        self.assertEqual(
            build.inline("**b** and *i* and `c`"),
            "<strong>b</strong> and <em>i</em> and <code>c</code>",
        )

    def test_inline_escapes_html(self):
        self.assertEqual(build.inline("a < b"), "a &lt; b")

    def test_md_link_becomes_html(self):
        self.assertEqual(
            build.inline("[Glossary](08-glossary.md)"),
            '<a href="08-glossary.html">Glossary</a>',
        )

    def test_table_round_trip(self):
        md = "| a | b |\n|---|---|\n| 1 | 2 |\n"
        html = build.Renderer().render(md)
        self.assertIn("<table>", html)
        self.assertIn("<td>", html)

    def test_nested_bullet_list(self):
        md = "- top\n  - child\n"
        html = build.Renderer().render(md)
        self.assertIn("<ul>", html)
        inner_blocks = html.count("<ul>")
        self.assertGreaterEqual(inner_blocks, 2)


if __name__ == "__main__":
    unittest.main()
