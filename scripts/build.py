#!/usr/bin/env python3
"""Build the static HTML site from the docs/ markdown manual.

Local-first, standard library only. Run:

    python3 scripts/build.py [--out site] [--check]

Output: a self-contained static site (index.html, one page per chapter,
styles.css). No network access, no external assets, prints cleanly.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

CHAPTERS = [
    ("00-introduction.md", "How to Use This Workbook"),
    ("01-bank-early-career.md", "Ch. 1 — Early-Career Question Bank"),
    ("02-bank-healthcare.md", "Ch. 2 — Healthcare Question Bank"),
    ("03-bank-small-business.md", "Ch. 3 — Small-Business Question Bank"),
    ("04-worksheets-calm-answers.md", "Ch. 4 — Calm-Answer Worksheets"),
    ("05-fairness-notes.md", "Ch. 5 — Fairness Notes"),
    ("06-ai-mock-sessions.md", "Ch. 6 — AI Mock Sessions"),
    ("07-score-sheets.md", "Ch. 7 — Score-Sheet Templates"),
    ("08-glossary.md", "Ch. 8 — Glossary"),
]

SITE_TITLE = "Interview Panel Question Bank Guide"
SUBTITLE = "Banked-and-reusable interview questions, for both sides of the table"


def esc(text: str) -> str:
    return html.escape(text, quote=False)


# ---------------------------------------------------------------- inline ---

INLINE_RE = re.compile(
    r"""
    (?P<code>`(?P<code_text>[^`]+)`)              |
    (?P<bold>\*\*(?P<bold_text>[^*]+)\*\*)        |
    (?P<em>\*(?P<em_text>[^*]+)\*)                |
    (?P<link>\[(?P<link_text>[^\]]+)\]\((?P<link_href>[^)\s]+)\))
    """,
    re.VERBOSE,
)


def inline(text: str) -> str:
    result = []
    pos = 0
    for m in INLINE_RE.finditer(text):
        result.append(esc(text[pos:m.start()]))
        if m.group("code"):
            result.append(f"<code>{esc(m.group("code_text"))}</code>")
        elif m.group("bold"):
            result.append(f"<strong>{esc(m.group("bold_text"))}</strong>")
        elif m.group("em"):
            result.append(f"<em>{esc(m.group("em_text"))}</em>")
        else:
            href = esc(m.group("link_href"))
            inner = esc(m.group("link_text"))
            if href.endswith(".md"):
                href = slug_from_name(href)
                result.append(f'<a href="{href}">{inner}</a>')
            else:
                result.append(
                    f'<span class="ext-link" title="{href}">{inner}</span>'
                )
        pos = m.end()
    result.append(esc(text[pos:]))
    return "".join(result)


def slug_from_name(name: str) -> str:
    stem = name.split("/")[-1].rsplit(".", 1)[0]
    return f"{stem}.html"


SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    s = SLUG_RE.sub("-", text.strip().lower()).strip("-")
    return s[:60] or "section"


def ids_for(text: str) -> str:
    return "s-" + slugify(text)


# ---------------------------------------------------------------- blocks ---


def indent_of(line: str) -> int:
    return len(line) - len(line.lstrip(" "))


class Renderer:
    """Convert the docs markdown subset into HTML."""

    def __init__(self) -> None:
        self.headings: list[tuple[int, str, str]] = []  # (level, id, text)
        self.questions: list[dict] = []

    def render(self, md: str) -> str:
        lines = md.splitlines()
        out: list[str] = []
        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]
            stripped = line.strip()
            if not stripped:
                i += 1
                continue
            if stripped.startswith("#"):
                level = len(stripped) - len(stripped.lstrip("#"))
                text = stripped.lstrip("#").strip()
                hid = ids_for(text)
                self.headings.append((level, hid, text))
                out.append(
                    f'<h{level} id="{hid}">{inline(text)}</h{level}>'
                )
                i += 1
                continue
            if stripped in ("---", "***", "___"):
                out.append("<hr>")
                i += 1
                continue
            if stripped.startswith("```"):
                i += 1
                code: list[str] = []
                while i < n and not lines[i].strip().startswith("```"):
                    code.append(lines[i])
                    i += 1
                i += 1  # closing fence
                out.append(f"<pre><code>{esc(chr(10).join(code))}</code></pre>")
                continue
            if stripped.startswith(">"):
                quote: list[str] = []
                while i < n and lines[i].strip().startswith(">"):
                    quote.append(lines[i].strip().lstrip(">").strip())
                    i += 1
                out.append(f"<blockquote><p>{inline(' '.join(quote))}</p></blockquote>")
                continue
            if stripped.startswith("|"):
                rows: list[list[str]] = []
                while i < n and lines[i].strip().startswith("|"):
                    cells = [c.strip() for c in lines[i].strip().strip("|").split("|")]
                    if not all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
                        rows.append(cells)
                    i += 1
                if rows:
                    head, *body = rows
                    thead = "<tr>" + "".join(f"<th>{inline(c)}</th>" for c in head) + "</tr>"
                    trs = [
                        "<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>"
                        for r in body
                    ]
                    out.append(
                        "<table><thead>" + thead + "</thead><tbody>"
                        + "".join(trs) + "</tbody></table>"
                    )
                continue
            if re.match(r"^([-*+])\s+", stripped):
                items, i = self._collect_list(lines, i, indent_of(line))
                out.append(self._render_list(items))
                continue
            if re.match(r"^\d+\.\s+", stripped):
                items, i = self._collect_ol(lines, i)
                out.append(
                    "<ol>"
                    + "".join(f"<li>{inline(t)}</li>" for t in items)
                    + "</ol>"
                )
                continue
            para: list[str] = []
            while i < n and lines[i].strip() and not re.match(
                r"^(#{1,6}\s|>|```|\||[-*+]\s|\d+\.\s|---|___|\*\*\*)",
                lines[i].strip(),
            ):
                para.append(lines[i].strip())
                i += 1
            out.append(f"<p>{inline(' '.join(para))}</p>")
        return "\n".join(out)

    # -- lists -----------------------------------------------------------

    def _collect_list(
        self, lines: list[str], start: int, base_indent: int
    ) -> tuple[list[dict], int]:
        """Collect a (possibly nested) bullet list starting at line *start*."""
        items: list[dict] = []
        i = start
        n = len(lines)
        while i < n:
            stripped = lines[i].strip()
            if not stripped:
                i += 1
                if i < n and lines[i].strip().startswith(("-", "*", "+")) and indent_of(lines[i]) >= base_indent:
                    continue
                break
            m = re.match(r"^([-*+])\s+(.*)$", stripped)
            if not m:
                break
            indent = indent_of(lines[i])
            if indent < base_indent:
                break
            text = m.group(2).strip()
            item: dict = {"text": text, "children": []}
            flat = indent == base_indent
            # continuation lines
            j = i + 1
            cont: list[str] = []
            while j < n:
                nxt = lines[j].strip()
                if nxt and not re.match(r"^([-*+]\s|\d+\.\s|#|>|```|\|)", nxt) and indent_of(lines[j]) > indent:
                    cont.append(nxt)
                    j += 1
                else:
                    break
            if cont:
                item["text"] = text + " " + " ".join(cont)
            i = j
            if flat or not items or indent == base_indent:
                items.append(item)
            else:
                items[-1]["children"].append(item)
        return items, i

    def _collect_ol(
        self, lines: list[str], start: int
    ) -> tuple[list[str], int]:
        items: list[str] = []
        i = start
        n = len(lines)
        base = indent_of(lines[start])
        while i < n:
            stripped = lines[i].strip()
            m = re.match(r"^\d+\.\s+(.*)$", stripped)
            if not m or indent_of(lines[i]) != base:
                break
            items.append(m.group(1).strip())
            i += 1
        return items, i

    Q_RE = re.compile(r"^\*\*?Q:\s*(.+?)\*?\*?$")

    def _render_list(self, items: list[dict]) -> str:
        parts = ["<ul>"]
        for item in items:
            text = item["text"]
            qm = self.Q_RE.match(text)
            if qm:
                card = self._card(qm)
                details = ""
                if item["children"]:
                    details = (
                        '<ul class="qdetails">'
                        + "".join(
                            f"<li>{inline(c['text'])}"
                            + (self._render_list(c["children"]) if c["children"] else "")
                            + "</li>"
                            for c in item["children"]
                        )
                        + "</ul>"
                    )
                parts.append(f'<li class="qcard-wrap">{card}{details}</li>')
            else:
                rendered = inline(text)
                if item["children"]:
                    rendered += self._render_list(item["children"])
                parts.append(f"<li>{rendered}</li>")
        parts.append("</ul>")
        return "".join(parts)

    def _card(self, qm: re.Match) -> str:
        question = qm.group(1)
        qid = f"q-{len(self.questions) + 1:03d}"
        self.questions.append({"id": qid, "q": question})
        return (
            f'<div class="qcard" id="{qid}">'
            f'<span class="qmark">Q{len(self.questions):02d}</span>'
            f'<span class="qtext">{inline(question)}</span>'
            "</div>"
        )


PAGE_TMPL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} — {site}</title>
<link rel="stylesheet" href="styles.css">
</head>
<body>
<nav class="topnav">
  <a class="brand" href="index.html">{site}</a>
  <div class="chapters">
    {navlinks}
  </div>
</nav>
<main class="chapter">
<article>
{body}
</article>
<div class="pager">{pager}</div>
</main>
<footer>
  <p>{site} — {subtitle}</p>
  <p>Copyright (c) 2026 Asdale Dynamics, LLC · MIT License · Local-first, no
  API keys, no cloud requirement.</p>
</footer>
</body>
</html>
"""

INDEX_TMPL = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="stylesheet" href="styles.css">
</head>
<body>
<header class="hero">
  <h1>{site}</h1>
  <p class="tagline">{subtitle}</p>
  <p class="credit">A workbook by <strong>Asdale Dynamics, LLC</strong> —
  beginner-friendly guides, plain English, never condescending.</p>
</header>
<nav class="topnav">
  <div class="chapters">
    {navlinks}
  </div>
</nav>
<main class="home">
<section class="intro">
<h2>Start here</h2>
{intro}
</section>
<section class="cards">
<h2>Question bank cards ({nq} questions)</h2>
<p>Every `**Q:**` line from Chapters 1–3 collapsed into review cards. The
full question text, its <em>why</em>, and its <em>listen-for</em> live in the
chapter pages; these cards are for the ten-minute pre-interview skim.
<a href="00-introduction.html">Read the intro &rarr;</a></p>
<ol class="qcards">
{cards}
</ol>
</section>
<section class="quicklinks">
<h2>Quick tools</h2>
<ul>
<li><a href="07-score-sheets.html">Printable score sheets (Ch. 7)</a></li>
<li><a href="08-glossary.html">Glossary (Ch. 8)</a></li>
<li>Mock-interview practice: <code>python3 scripts/mock_session.py --list-models</code> —
runs against a local model, no API key required. <a href="06-ai-mock-sessions.html">How it works &rarr;</a></li>
</ul>
</section>
</main>
<footer>
  <p>{site} — {subtitle}</p>
  <p>Copyright (c) 2026 Asdale Dynamics, LLC · MIT License · Local-first, no
  API keys, no cloud requirement.</p>
</footer>
</body>
</html>
"""

STYLES = """:root {
  --ink: #1c2430;
  --paper: #fbfaf7;
  --accent: #0f6e5c;
  --accent-soft: #e3f0ec;
  --rule: #d8d2c4;
  --muted: #6b6459;
}
* { box-sizing: border-box; }
html { scroll-behavior: smooth; }
body {
  margin: 0;
  font-family: Georgia, "Times New Roman", serif;
  color: var(--ink);
  background: var(--paper);
  line-height: 1.6;
}
nav.topnav {
  background: var(--ink);
  color: #fff;
  padding: 0.6rem 1rem;
  display: flex;
  gap: 1rem;
  align-items: center;
  border-bottom: 4px solid var(--accent);
  flex-wrap: wrap;
}
nav.topnav .brand { color: #fff; font-weight: bold; text-decoration: none; }
nav.topnav .chapters { display: flex; flex-wrap: wrap; gap: 0.4rem; }
nav.topnav .chapters a {
  color: #dfe5e9;
  text-decoration: none;
  font-size: 0.8rem;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
  font-family: system-ui, sans-serif;
}
nav.topnav .chapters a:hover { background: var(--accent); color: #fff; }
main { max-width: 46rem; margin: 0 auto; padding: 1rem 1.2rem 3rem; }
header.hero {
  max-width: 46rem; margin: 0 auto; padding: 2rem 1.2rem 0.5rem;
}
header.hero h1 { margin: 0 0 0.3rem; font-size: 2.1rem; }
header.hero .tagline { color: var(--muted); margin: 0; font-style: italic; }
header.hero .credit { font-size: 0.9rem; color: var(--muted); }
h1, h2, h3, h4 { line-height: 1.25; margin: 1.6rem 0 0.6rem; }
h1 { font-size: 1.9rem; border-bottom: 2px solid var(--rule); padding-bottom: 0.3rem; }
h2 { font-size: 1.4rem; color: var(--accent); }
h3 { font-size: 1.1rem; }
table {
  border-collapse: collapse; width: 100%; margin: 1rem 0;
  font-family: system-ui, sans-serif; font-size: 0.92rem;
}
th, td { border: 1px solid var(--rule); padding: 0.4rem 0.55rem; text-align: left; vertical-align: top; }
th { background: var(--accent-soft); }
blockquote {
  margin: 1rem 0; padding: 0.7rem 1rem;
  border-left: 4px solid var(--accent); background: var(--accent-soft);
}
blockquote p { margin: 0; font-style: italic; }
pre {
  background: #f0ede4; border: 1px solid var(--rule); padding: 0.7rem 0.9rem;
  overflow-x: auto; font-size: 0.88rem;
}
code { font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace; font-size: 0.9em; background: #f0ede4; padding: 0.1em 0.3em; border-radius: 3px; }
pre code { background: none; padding: 0; }
ul.qcards { list-style: none; padding-left: 0; margin: 0.6rem 0 1.4rem; display: grid; gap: 0.45rem; }
li.qcard-wrap > div.qcard { margin: 0; }
.qmark {
  font-family: system-ui, sans-serif; font-weight: 700; color: #fff;
  background: var(--accent); border-radius: 6px; padding: 0.05rem 0.45rem;
  font-size: 0.78rem; white-space: nowrap; flex-shrink: 0;
}
.qtext { flex: 1; }
ul.qdetails {
  list-style: none; padding: 0.3rem 0 0; margin: 0.4rem 0 0.1rem;
  font-size: 0.9rem; color: var(--muted); display: grid; gap: 0.3rem;
}
ul.qdetails ul { list-style: circle; margin: 0.3rem 0 0; padding-left: 1.1rem; }
li.qcard-wrap { padding: 0; border: 0; background: none; display: block; }
div.qcard {
  border: 1px solid var(--rule); border-radius: 8px; background: #fff;
  padding: 0.55rem 0.8rem; display: flex; gap: 0.6rem; align-items: baseline;
  break-inside: avoid;
}
a.qlink { text-decoration: none; color: var(--muted); flex-shrink: 0; }
.pager { margin-top: 2.5rem; font-family: system-ui, sans-serif; font-size: 0.9rem; display: flex; justify-content: space-between; gap: 1rem; }
footer {
  border-top: 3px solid var(--rule); margin: 2rem auto 0; max-width: 46rem;
  padding: 1rem 1.2rem 2.5rem; color: var(--muted); font-size: 0.85rem;
}
a { color: var(--accent); }
section.cards, section.quicklinks, section.intro { margin-bottom: 2.2rem; }
@media print {
  nav.topnav, footer, a.qlink { display: none; }
  body { background: #fff; }
  main { max-width: none; padding: 0; }
  table, blockquote, pre, div.qcard { break-inside: avoid; }
  a { color: inherit; text-decoration: none; }
}
"""


def page(slug: str, title: str, body_html: str, navlinks: str, pager: str) -> str:
    return PAGE_TMPL.format(
        title=esc(title),
        site=esc(SITE_TITLE),
        subtitle=SUBTITLE,
        navlinks=navlinks,
        body=body_html,
        pager=pager,
    )


def build(out_dir: Path) -> dict:
    out_dir.mkdir(parents=True, exist_ok=True)
    renderer = Renderer()
    pages: list[tuple[str, str, str]] = []  # slug, title, rendered body
    plain: dict[str, str] = {}

    for fname, title in CHAPTERS:
        md_path = DOCS / fname
        if not md_path.exists():
            raise SystemExit(f"missing doc: {md_path}")
        md_text = md_path.read_text(encoding="utf-8")
        body = renderer.render(md_text)
        slug = slug_from_name(fname)
        pages.append((slug, title, body))
        plain[slug] = md_text

    (out_dir / "styles.css").write_text(STYLES, encoding="utf-8")

    navlinks = []
    for slug, title, _ in pages:
        navlinks.append(f'<a href="{slug}">{esc(title.split("—")[-1].strip().split(" Question Bank")[0])}</a>')
    navlinks_html = "\n    ".join(navlinks)

    for idx, (slug, title, body) in enumerate(pages):
        prev_page = pages[idx - 1] if idx > 0 else None
        next_page = pages[idx + 1] if idx + 1 < len(pages) else None
        prev_html = (
            f'<a href="{prev_page[0]}">&larr; {esc(prev_page[1])}</a>'
            if prev_page
            else "<span></span>"
        )
        next_html = (
            f'<a href="{next_page[0]}">{esc(next_page[1])} &rarr;</a>'
            if next_page
            else "<span></span>"
        )
        pager = " ".join((prev_html, next_html))
        (out_dir / slug).write_text(
            page(slug, title, body, navlinks_html, pager), encoding="utf-8"
        )

    # index ------------------------------------------------------------
    intro_md = (DOCS / CHAPTERS[0][0]).read_text(encoding="utf-8")
    # reorder for the home page: hero copy, then intro, then cards
    body_copy = (
        "<p><strong>Most interview advice is either generic or for the person "
        "already in charge. This workbook is different: it hands you the "
        "actual question banks, for both sides of the table, in plain "
        "English, and then walks you through adapting them calmly.</strong></p>"
    )
    cards_html = "".join(
        f'<li class="question" id="card-{i:03d}">{inline(q["q"])}</li>'
        for i, q in enumerate(renderer.questions, 1)
    )
    index_html = INDEX_TMPL.format(
        title=SITE_TITLE,
        site=SITE_TITLE,
        subtitle=SUBTITLE,
        navlinks=navlinks_html,
        intro=body_copy + intro_md,
        nq=len(renderer.questions),
        cards=cards_html,
    )
    (out_dir / "index.html").write_text(index_html, encoding="utf-8")

    return {
        "pages": [p[0] for p in pages] + ["index.html"],
        "questions": renderer.questions,
        "plain": plain,
    }


def main() -> None:
    ap = argparse.ArgumentParser(description="Build the static site.")
    ap.add_argument("--out", default="site", help="output directory (default: site)")
    ap.add_argument(
        "--check",
        action="store_true",
        help="build to a temp dir and exit 0 on success (CI smoke test)",
    )
    args = ap.parse_args()
    out_dir = Path(args.out)
    if not out_dir.is_absolute():
        out_dir = (Path.cwd() / out_dir).resolve()
    info = build(out_dir)
    if args.check:
        print(f"OK: built {len(info['pages'])} pages, {len(info['questions'])} question cards")
        return
    print(f"Built {len(info['pages'])} pages into {out_dir}/")
    print(f"Question cards: {len(info['questions'])}")


if __name__ == "__main__":
    main()
