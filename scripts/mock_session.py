#!/usr/bin/env python3
"""AI-assisted mock interview practice, against any OpenAI-compatible endpoint.

Designed local-first and keyless: the default target is a local Ollama
server (http://localhost:11434/v1). There is no --api-key option on purpose:
no Authorization header is ever sent, so there is no key to lose, leak, or
commit. To talk to a different server (LM Studio, llama.cpp, vLLM, a cloud
gateway your employer runs), pass --base-url.

Examples
--------
  python3 scripts/mock_session.py --list-models
  python3 scripts/mock_session.py --model llama3.1 --bank healthcare
  python3 scripts/mock_session.py --base-url http://localhost:1234/v1 \\
      --model local-model --rounds 3
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DOCS = ROOT / "docs"

DEFAULT_BASE_URL = "http://localhost:11434/v1"
TIMEOUT = 60

BANKS = {
    "early-career": "01-bank-early-career.md",
    "healthcare": "02-bank-healthcare.md",
    "small-business": "03-bank-small-business.md",
}

COMMANDS = {
    ":help": "show this list",
    ":redo": "rewrite your last answer",
    ":skip": "jump to the next question",
    ":quit": "end the session and get a debrief on what you have so far",
}

SYSTEM_PROMPT = (
    "You are a warm, plain-spoken interviewer named Dana running a mock "
    "interview in a terminal. You are practicing with one candidate, who is "
    "answering in writing.\n"
    "Rules you never break:\n"
    "1. Ask exactly ONE short interview question (one sentence if possible), "
    "then stop and wait. No greeting, no commentary, no follow-up essay.\n"
    "2. Never grade, never reassure, never coach mid-session. The debrief at "
    "the end handles all of that.\n"
    "3. Prefer plain, calm, human wording — no corporate jargon, no numbered "
    "sub-parts in a single turn.\n"
    "4. If the candidate answers in one short sentence or less, follow up "
    "once with 'Can you give me one specific detail about that?' — but only "
    "once per topic.\n"
    "5. All interview topics must stay job-relevant: tasks, judgment, "
    "reliability, teamwork. Never ask about family, health, age, religion, "
    "national origin, or anything an interviewer shouldn't ask."
)

DEBRIEF_SYSTEM = (
    "You are the same friendly interviewer (Dana) giving a short end-of-"
    "session debrief in a terminal. You are coaching, not scoring, and you "
    "are not deciding anything about real hiring. Reply with EXACTLY this "
    "shape and nothing else:\n"
    "KEPT: <two specific things the candidate did well, one short line each>\n"
    "PRACTICE: <one thing to practice this week, one short line>\n"
    "RERUN: <the question number to repeat first>\n"
    "Keep every line under 110 characters. Use plain words. If an answer "
    "was very short, mention it once here, kindly, and move on."
)

INTRO_TMPL = (
    "Mock interview — bank: {bank}. {rounds} questions, then a debrief.\n"
    "Type an answer and press Enter. {commands}\n"
    "No API key is used and no data leaves this machine unless you pointed "
    "--base-url elsewhere.\n"
)


def bank_path(bank: str) -> Path | None:
    if bank not in BANKS:
        return None
    return DOCS / BANKS[bank]


def parse_bank_questions(md_text: str) -> list[str]:
    """Extract candidate-facing + hiring-side question lines from a bank doc."""
    qs: list[str] = []
    for line in md_text.splitlines():
        m = re.match(r"\s*[-*+]\s+\*\*Q:\s*(.+?)\s*\*\*\s*$", line)
        if m:
            q = m.group(1).strip()
            if q and not q.lower().startswith("candidate entry"):
                qs.append(q)
    # de-dup the deliberate overlap between the two sides of each bank
    seen: set[str] = set()
    deduped: list[str] = []
    for q in qs:
        key = re.sub(r"^Q\d+\.\s*", "", q)
        key = re.sub(r"[^a-z0-9]", "", key.lower())
        if key not in seen:
            seen.add(key)
            deduped.append(q)
    return deduped


def load_banks(bank: str) -> list[str]:
    if bank == "runthrough":
        out: list[str] = []
        for name in BANKS.values():
            path = DOCS / name
            if path.exists():
                out.extend(parse_bank_questions(path.read_text(encoding="utf-8")))
        return out
    path = bank_path(bank)
    if path is None or not path.exists():
        return []
    return parse_bank_questions(path.read_text(encoding="utf-8"))


# ------------------------------------------------------------------- HTTP ---


class EndpointError(RuntimeError):
    pass


def _request(base_url: str, method: str, path: str, body: dict | None = None) -> dict:
    """POST/GET a JSON request. Never attaches an Authorization header."""
    url = base_url.rstrip("/") + path
    data = json.dumps(body).encode("utf-8") if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:300]
        raise EndpointError(f"{method} {url} -> HTTP {e.code}: {detail}") from e
    except urllib.error.URLError as e:
        raise EndpointError(
            f"cannot reach {url} ({e.reason}). "
            "Is your local server running? Try: ollama serve"
        ) from e


def list_models(base_url: str) -> list[str]:
    data = _request(base_url, "GET", "/models")
    return [m.get("id", "") for m in data.get("data", [])]


def chat(
    base_url: str,
    model: str,
    messages: list[dict],
    temperature: float = 0.6,
    max_tokens: int = 220,
) -> str:
    data = _request(
        base_url,
        "POST",
        "/chat/completions",
        {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        },
    )
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as e:
        raise EndpointError(f"unexpected response shape from {base_url}: {e}") from e


# ---------------------------------------------------------------- session ---


DEBRIEF_RE = re.compile(
    r"(?is)KEPT:\s*(?P<kept>.*?)\s*PRACTICE:\s*(?P<practice>.*?)\s*"
    r"RERUN:\s*(?P<rerun>.*)"
)


def parse_debrief(text: str) -> tuple[str, str, str]:
    m = DEBRIEF_RE.search(text)
    if not m:
        return (text.strip(), "", "?")
    kept = re.sub(r"\s*\n\s*", " | ", m.group("kept").strip())
    practice = m.group("practice").strip().splitlines()[0]
    return kept, practice.strip(), m.group("rerun").strip()


def format_history(
    questions: list[str], answers: list[str], persona: str = ""
) -> list[dict]:
    """Build chat messages for the interviewer turn by turn."""
    history: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    opener = "Begin with an easy, open first question. One question only."
    if persona:
        opener = f"You are interviewing {persona}. {opener}"
    if questions:
        opener = (
            "Starter questions you may reuse verbatim (do not announce the "
            "source, just ask one):\n"
            + "\n".join(f"- {q}" for q in questions[:14])
            + "\n\n" + opener
        )
    history.append({"role": "user", "content": opener})
    for q, a in zip(questions, answers):
        history.append({"role": "assistant", "content": q})
        history.append({"role": "user", "content": a})
    return history


def build_debrief(
    base_url: str, model: str, transcript: list[tuple[str, str]]
) -> str:
    lines = []
    for i, (q, a) in enumerate(transcript, 1):
        lines.append(f"Q{i}: {q}\nA{i}: {a}")
    messages = [
        {"role": "system", "content": DEBRIEF_SYSTEM},
        {"role": "user", "content": "Transcript:\n" + "\n".join(lines)},
    ]
    try:
        return chat(base_url, model, messages, temperature=0.4, max_tokens=280)
    except EndpointError as e:
        print(f"(debrief skipped: {e})")
        return ""


def run_session(
    base_url: str, model: str, bank: str, rounds: int, persona: str
) -> tuple[list[tuple[str, str]], tuple[str, str, str] | None]:
    """Interactive session. Returns (transcript, debrief-or-None)."""
    questions = load_banks(bank)
    if not questions:
        sys.exit(
            f"bank '{bank}' produced no questions — check that the "
            "bank doc contains **Q:** entries"
        )
    print(INTRO_TMPL.format(
        bank=bank,
        rounds=rounds,
        commands="Type " + ", ".join(sorted(COMMANDS)) + " for commands.",
    ))
    transcript: list[tuple[str, str]] = []
    while len(transcript) < rounds:
        history = format_history(
            questions, [a for _, a in transcript], persona=persona
        )
        try:
            q = chat(base_url, model, history, temperature=0.7)
        except EndpointError as e:
            sys.exit(f"error: {e}")
        if not q:
            sys.exit("error: empty reply from the model server")
        print(f"\n[Interviewer] {q}")
        answer = ""
        quit_session = False
        while True:
            try:
                line = input("You: ")
            except (EOFError, KeyboardInterrupt):
                print()
                quit_session = True
                break
            cmd = line.strip()
            if not cmd:
                print("  (type your answer, or :help)")
                continue
            low = cmd.lower()
            if low in (":help", "h", "help"):
                for k, v in COMMANDS.items():
                    print(f"  {k} — {v}")
                continue
            if low in (":redo", "r", "redo"):
                print("  (rewrite your answer: type the better version now)")
                continue
            if low in (":skip", "s", "skip"):
                answer = "(skipped this question)"
                break
            if low in (":quit", "q", "quit", "!q"):
                quit_session = True
                break
            answer = cmd
            break
        if quit_session:
            break
        transcript.append((q, answer))
    debrief: tuple[str, str, str] | None = None
    if transcript:
        debrief_text = build_debrief(base_url, model, transcript)
        debrief = parse_debrief(debrief_text or "")
    return transcript, debrief


def main() -> None:
    ap = argparse.ArgumentParser(
        description="Local-first AI mock interview (no API key)."
    )
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL,
                    help="OpenAI-compatible endpoint (default: local Ollama)")
    ap.add_argument("--model", help="model ID; see --list-models")
    ap.add_argument("--bank", choices=list(BANKS) + ["runthrough"],
                    default="early-career")
    ap.add_argument("--rounds", type=int, default=5)
    ap.add_argument("--candidate", default="",
                    help="persona label used in the debrief (e.g. 'RN, 3 yoe')")
    ap.add_argument("--list-models", action="store_true")
    ap.add_argument("--dry-run", action="store_true",
                    help="show the first interviewer prompt and exit")
    args = ap.parse_args()

    if args.list_models:
        try:
            models = list_models(args.base_url)
        except EndpointError as e:
            sys.exit(f"error: {e}")
        if not models:
            sys.exit("no models found — try: ollama pull llama3.1")
        print("\n".join(models))
        return

    if not args.model:
        ap.error("--model is required for a mock session (or use --list-models)")
    if args.rounds < 1 or args.rounds > 12:
        ap.error("--rounds must be between 1 and 12")

    if args.dry_run:
        qs = load_banks(args.bank)
        history = format_history(qs, [])
        json.dump(history, sys.stdout, indent=2)
        return

    transcript, debrief = run_session(
        args.base_url, args.model, args.bank, args.rounds, args.candidate
    )
    if debrief:
        kept, practice, rerun = debrief
        print("\n--- DEBRIEF ---")
        print(f"KEPT:     {kept}")
        print(f"PRACTICE: {practice}")
        print(f"RERUN:    {rerun}")
        print("\nCopy the PRACTICE line into a Chapter 4 worksheet and run the")
        print("same bank again this week.")
    history_path = Path.cwd() / "mock_history.txt"
    with history_path.open("a", encoding="utf-8") as fh:
        for q, a in transcript:
            fh.write(f"Q: {q}\nA: {a}\n---\n")
    print(f"(session appended to {history_path} on this machine)")


if __name__ == "__main__":
    main()
