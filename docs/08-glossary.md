# Chapter 8 — Glossary

Plain-English definitions, Dylan-style: like a friend would explain it,
step by step, never condescending.

- **OpenAI-compatible API** — a web service that speaks the same request
  format as OpenAI's chat API, whether or not OpenAI runs it. Lets one small
  tool (like the mock-session script here) talk to Ollama, LM Studio, vLLM,
  or a cloud provider without code changes.
- **Base URL** — the address of the model server, e.g.
  `http://localhost:11434/v1` for Ollama. The only config this tool needs
  besides a model name.
- **Behavioral question** — an interview question about a *past* behavior
  ("Tell me about a time…"), on the theory that past behavior predicts
  future behavior better than hypotheticals do.
- **Banked question** — a question written down, tested, and reused for
  every candidate in a pool, so comparison is possible. The core idea of
  this workbook.
- **Calm answer** — this workbook's term for a short, specific answer that
  stops early: one true sentence, one detail, one action, one ending. See
  Chapter 4.
- **Instruct-tuned model** — a language model trained to follow one
  instruction at a time and answer back politely, as opposed to a raw
  next-word predictor. You need an instruct-tuned model for mock interviews.
- **Inter-rater reliability** — the degree to which two scorers agree on the
  same answer. Low agreement means your anchors (not necessarily your
  panelists) need work.
- **Interview panel** — two or more people interviewing together, usually
  scoring independently on the same sheet. The independent-scoring part is
  what makes it useful.
- **Job-relevant** — the fairness test: a question measures a task, a
  judgment, or a behavior that the *posted job* actually requires.
- **Listen-for** — the thing an interviewer is actually watching for inside
  an answer (a specific example, an escalation step, an owned mistake).
  Every bank question in this workbook has one written down.
- **Local model** — a language model running on your own machine, e.g. via
  Ollama or LM Studio. No API key, no network dependency, nothing leaves
  your disk.
- **Ollama** — free software that downloads and serves local models on your
  own computer behind an OpenAI-compatible endpoint (default
  `http://localhost:11434/v1`). See `ollama pull llama3.1`.
- **OpenAI-compatible endpoint** — any HTTP endpoint that accepts
  `/v1/chat/completions` requests in the OpenAI request/response JSON
  shape, local or remote.
- **Prompt** — the text you send to a model to get a response. In the
  mock-session tool, a system prompt holds the interviewer's character and
  the bank's tone, and the history is re-sent each round.
- **Question bank** — a curated list of questions with notes on why to ask
  and what to listen for. What Chapters 1–3 are.
- **Red flag (interviewer side)** — an answer detail that predicts trouble,
  e.g. "fixed the mistake without reporting it." Distinguish from *weak*
  answers, which are fixable with practice.
- **Redirection (candidate side)** — a calm one-liner that steers back to
  job-relevant ground when a question is unfair or off-limits. See
  Worksheet D.
- **Rubric** — the anchored scale: what a 2 looks like, what a 4 looks
  like, written down before the interviews start.
- **STAR answer (soft version)** — the classic Situation / Task / Action /
  Result structure. This workbook deliberately softens it into the calm
  shape (scene, detail, action, ending, stop) so it doesn't read like a
  memorized form.
- **Structured interview** — an interview where everyone gets the same
  questions and scores land on the same sheet. For twenty years of
  research summarized in two words: it predicts better and it's fairer.
- **System prompt** — the standing instructions a model receives before any
  conversation starts; in this project, the interviewer's persona and rules
  ("ask one question, wait, never grade").
- **Context window** — the maximum amount of text a model can
  consider at once. Long transcripts overflow small local models; that's
  why the debrief summarizes instead of quoting everything.
