# Chapter 6 — AI Mock Sessions

This is the chapter where you get to fail interviews in private, with an
audience of one machine. No mistypings in front of a panel. No shaking
hands. The interviewer never gets tired and never holds a grudge, because
it isn't a person — it is a local AI model you (optionally) run on your own
computer, and **nobody outside the room sees anything**, because *no API
key is required and nothing has to leave your machine*.

## Why "no API key" is a feature, not a limitation

- A key is a *credential that can leak*. Without one, there's nothing to
  leak — not an accidentally committed `.env`, not a secret in a screenshot.
- A cloud call is a *copy of your words on someone else's server*. A local
  call is a copy on your own disk that you can delete.
- Ollama, LM Studio, llama.cpp server, and vLLM all speak the same
  **OpenAI-compatible** REST dialect; the mock-session tool in this
  directory works with any of them. Change the base URL, done.

> You *may* run against a paid cloud endpoint if your employer set one up
> and policy allows. If you do, never paste candidate names, real
> interview notes, or anything you'd be embarrassed to see forwarded. The
> default configuration here is **local or nothing**.

## Chapter overview

Practice interviews work as a **loop** (door → warm-up → rounds →
debrief → practice), scripted in `scripts/mock_session.py` with a bank and
session state that survives a restart.

## Setup in three minutes

1. Install and start a local model server. With Ollama, the whole
   installation is: `ollama pull llama3.1` (or any instruct-tuned model),
   then `ollama serve`. That's it — no key file, no account. If the
   command `ollama list` shows your model, step 2 will see it too.
2. From the project folder, run:

   ```bash
   python3 scripts/mock_session.py --list-models
   ```

   You should see your pulled model's ID, e.g. `llama3.1`. (Using LM
   Studio? Tick "Enable local server," then run the same command — the
   tool accepts any base URL whose `/v1/models` answers.)

3. Start a practice session:

   ```bash
   python3 scripts/mock_session.py --model llama3.1 --bank early-career
   ```

   Other banks: `healthcare`, `small-business`, or `runthrough` (a mix).
   Add `--rounds 4` (default 5), `--base-url http://localhost:11434/v1`
   if you are not on the default port, and `--candidate "<your name or
   persona>"` when you want the debrief to address a role, e.g. the RN
   persona from Chapter 2 on the healthcare bank.

## The session, line by line

The tool runs a **written interview**. The AI plays the interviewer, sends
you questions one at a time in your terminal, you type answers, and the
session ends with a calm three-part debrief. At any prompt you can type:

- `:help` — reminder of this list.
- `:redo` — rewrite your last answer; the tool keeps the better one.
- `:skip` — take the next question now.
- `:quit` — end early. You still get a debrief on what happened so far.
- Anything else — it's your answer; press Enter to send it.

## The debrief

When the last round is done, the model gets one more prompt: a summary of
your answers. It returns three short sections:

1. **Two things you did that would land with a panel** — keep doing them.
2. **One thing to practice this week** — one item, not a lecture.
3. **The question to re-run first** — the model picks the weakest round.

Save the debrief: copy it into your Chapter 4 worksheet under
"calm-close line" or "energy check," whichever needs the edit. The history
of your session is kept in `mock_history.txt` in your working folder —
your machine, your file, delete it whenever.

## Sample session shape

```text
$ python3 scripts/mock_session.py --model llama3.1 --bank healthcare
You'll answer 5 questions. Type your answer, then press Enter.
[Interviewer] Q. Walk me through your last shift.
You: 7 to 7, fourteen patie— (typo — fix with :redo)
[You typed] "7 to 7, fourte..."
: redo
You: 7 to 7 on a med-surg unit — bedside report, morning meds batching, one
admitted mid-shift. The hard part: family questions at 4 p.m. on top of discharge
paperwork.
[Interviewer] Q. What would make you quit in the first month?
You: (your calm answer here)
--- DEBRIEF ---
1. You kept both answers to two sentences and named a real person to
   escalate to on day one — panels remember that.
2. Practice the mistake story: you narrated the outcome before the notice
   point. Add what you *noticed*.
3. Re-run: the mistake question round.
```

## Practice variants

- **The panel-of-two:** run the tool twice with two different banks and
  answer as if you couldn't see your own first answers. Debriefs disagree?
  That's a real question-consistency gap: most interviews do this.
- **Hire-side drills:** with another person playing the candidate, answer
  off the hiring-side bank (Chapters 1–3) from the other side of the table.
  The tool doesn't replace a live panel — it gives you reps. It
  **never should be** an automated final-decision judge: Chapter 5's
  fairness rules are for humans; the model is a sparring partner.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `connection refused` on start | The model server isn't running (`ollama serve`). | Start it, re-run `--list-models`. |
| `No model flagged for chat` | Pulled a base (non-instruct) model. | Pull an instruct model: `llama3.1`, `mistral`, `qwen2.5:7b`. |
| Answers are slow but fine | Large model, small GPU/CPU. | Pull a smaller quant (`llama3.1:8b-q4_K_M`). |
| Debrief is generic | Answer rounds were one-line answers. | Answer with 2–4 sentences; the debrief has more material to hold onto. |

If you're asked for an API key at any point, the tool is misconfigured:
the whole design runs **keyless local**. Delete the key, and point the
base URL at your local server instead.
