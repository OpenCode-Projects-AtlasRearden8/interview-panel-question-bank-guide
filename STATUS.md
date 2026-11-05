# STATUS

Project: **Interview Panel Question Bank Guide**
Owner: Asdale Dynamics, LLC · MIT License · Local-first
Date: 2026-11-05

## What was built

A workbook-style manual of interview question banks for both sides of the
table, plus the two tools around it:

1. **Markdown manual** (`docs/`, 9 chapters):
   - `00-introduction.md` — how to use the workbook, calm-answer concept,
     page-structure conventions, privacy note.
   - `01-bank-early-career.md` — 10 hiring-side + 6 candidate-side questions
     (Intern / Junior / New Grad / First Job), in stage order
     (Opening → Reliability → Teamwork → Close).
   - `02-bank-healthcare.md` — 9 hiring-side + 5 candidate-side questions
     (CNA / MA / LPN-RN / Front Desk / Tech), safety-and-scope centric.
     Education only; explicitly not medical or legal advice.
   - `03-bank-small-business.md` — 6 hiring-side + 4 candidate-side
     questions (retail / café / office assistant / bookkeeper), built for a
     20-minute counter interview.
   - `04-worksheets-calm-answers.md` — 4 fill-in worksheets (Calm Answer,
     Adapt-a-Question, Panel Pick, Red-Flag Softener) + fairness pre-check.
   - `05-fairness-notes.md` — why structure beats gut feel, table of
     risky questions with safer replacements, 3-step anchored scoring.
   - `06-ai-mock-sessions.md` — 3-minute Ollama setup, session walkthrough,
     debrief format, troubleshooting table. Keyless by design.
   - `07-score-sheets.md` — two printable templates (panel + small business).
   - `08-glossary.md` — 20 plain-English terms.

2. **Static-site builder** (`scripts/build.py`) — dependency-free
   (standard library only). Renders the docs' markdown subset (headings,
   paragraphs, nested lists, tables, blockquotes, fenced code, inline
   bold/italic/code/links) into a self-contained site in `site/`:
   chapter pages styled for both screen and print, an index with **40
   extracted question cards**, a color-coded per-side accent, and no
   external assets. `--check` runs a CI-friendly smoke build.

3. **Mock-session practice tool** (`scripts/mock_session.py`) — terminal
   mock interviews against **any OpenAI-compatible endpoint** (default:
   local Ollama at `http://localhost:11434/v1`; works with LM Studio,
   llama.cpp server, vLLM via `--base-url`). **No API key support by
   design — no Authorization header is ever sent.** Pulls questions from
   the bank docs, runs N rounds with commands (`:help`, `:redo`, `:skip`,
   `:quit`), then asks the model for a structured 3-part debrief
   (KEPT / PRACTICE / RERUN). History appends to local `mock_history.txt`.

4. **Tests** (`tests/`, 26 tests, all passing offline):
   `test_build.py` (12) covers page generation, card extraction, link
   rewriting, escaping, glossary/score-sheet content, license credit;
   `test_mock.py` (14) covers model listing + chat against a local fake
   endpoint (threaded `http.server`), asserts **no Authorization header
   is sent**, request shape, bank parsing, prompt/debrief parsing, and
   absence of a `--api-key` flag.

## How to run it

```bash
python3 scripts/build.py          # build site/ (open site/index.html)
python3 scripts/build.py --check  # CI smoke build
python3 -m unittest discover tests
# mock sessions need a local model server, e.g.:
ollama pull llama3.1 && ollama serve
python3 scripts/mock_session.py --list-models
python3 scripts/mock_session.py --model llama3.1 --bank healthcare
```

No other dependencies; Python 3.10+ (tested on 3.13.5).

## Verification results

- `python3 scripts/build.py` → 10 pages, 40 question cards, builds clean.
- `python3 scripts/build.py --check` → OK (10 pages, 40 cards).
- `python3 -m unittest discover tests` → **Ran 26 tests, OK** (offline).
- HTML tag balance check across all 10 pages → balanced.
- Secrets scan (`rg` for keys/passwords/DSA blocks) → clean; repo contains
  no secrets, no API keys, no personal data.
- End-to-end mock session run against a fake local endpoint → 2 rounds
  answered, debrief parsed (KEPT / PRACTICE / RERUN).

## Known gaps

- The mock-session tool is interactive-only; there is no batch/non-TTY
  mode yet (useful for CI demos and accessibility).
- Streaming (SSE) responses are not handled — large local models may look
  slow between turns since the tool waits for the full reply.
- The debrief format is enforced by prompt only; a stubborn model can
  drift from the KEPT/PRACTICE/RERUN shape (parse falls back to raw text).
- Markdown subset only: image syntax and arbitrary inline HTML are not
  supported by the builder (not needed by the current docs).
- Fairness notes summarize the U.S. federal baseline; per-state and
  international rules are out of scope and flagged as such in Chapter 5.
- `mock_history.txt` grows unbounded in the working directory (gitignored).
