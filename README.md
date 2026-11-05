# Interview Panel Question Bank Guide

A workbook-style manual of **interview question banks for both sides of the
table** — banked-and-reusable, fairness-first, with calm-answer worksheets
and AI-assisted mock-session practice that runs **keyless and local-first**.

Built by **Asdale Dynamics, LLC** — beginner-friendly AI education, plain
English, never condescending.

> Not standard interview-prep advice. This is a working manual: fill-in
> worksheets, printable score sheets, and question banks you can copy,
> adapt, and reuse — plus a privacy-preserving practice tool.

## What's inside

| | |
|---|---|
| **3 question banks** (early-career, healthcare, small-business), each written for hiring and candidate sides | `docs/01…03` |
| **Calm-answer worksheets** — fill-in outlines, not scripts | `docs/04` |
| **Fairness notes** — same questions, same order, same score sheet; what to ask instead of legally risky questions | `docs/05` |
| **AI mock sessions** — terminal practice interviews against any OpenAI-compatible endpoint. Local Ollama by default. **No API key, ever.** | `docs/06` + `scripts/mock_session.py` |
| **Score-sheet templates** and a **glossary** | `docs/07–08` |
| **Static site** — chapter pages, question cards, printable score sheets | `site/` (built by `scripts/build.py`) |

## How to use it

Read the markdown directly (start at `docs/00-introduction.md`), or build
and open the static site:

```bash
python3 scripts/build.py           # writes ./site
open site/index.html               # or just double-click it
```

Local-first: standard library only, no dependencies, no network calls in
the builder.

### Mock interview practice (local AI, no key)

You need a local model server such as [Ollama](https://ollama.com):

```bash
ollama pull llama3.1 && ollama serve
python3 scripts/mock_session.py --list-models
python3 scripts/mock_session.py --model llama3.1 --bank healthcare
```

- Any OpenAI-compatible endpoint works via `--base-url` (Ollama, LM
  Studio, llama.cpp server, vLLM…).
- **There is no `--api-key` flag, on purpose.** No Authorization header is
  sent; there is no key to leak, commit, or screenshot.
- `--bank` options: `early-career`, `healthcare`, `small-business`,
  `runthrough` (mix of all three).
- Session history is appended to `mock_history.txt` on your machine only.

### Run the tests

```bash
python3 -m unittest discover tests
python3 scripts/build.py --check   # CI-friendly smoke build
```

All tests pass offline — the mock-session tests run against a tiny local
fake endpoint, so no model server is required.

## Repo layout

```
docs/     the manual (markdown, 9 chapters)
scripts/  build.py (site builder), mock_session.py (practice tool)
site/     generated static site (open site/index.html)
tests/    unittest suite, offline
```

## Points of view

This workbook is for both interviewers and candidates. Interviewers get
banked questions with *listen-for* notes and score sheets that survive a
complaint-free year of hiring. Candidates get the exact calm-answer shapes
those questions reward — one true sentence, one specific detail, and stop.

**Healthcare content is education only — never medical or legal advice.**
Check your local employment law; this book's fairness notes explain the
U.S. federal baseline and why structure beats gut feel, not jurisdiction.

## License

MIT — copyright (c) 2026 Asdale Dynamics, LLC. See `LICENSE`.
