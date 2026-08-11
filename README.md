# JotPsych Re-engagement Machine

A machine that works the list of clinicians who signed up for JotPsych but
never converted -- not because they said no, but because the timing was
wrong (contract still running, practice not ready, pain not felt yet). It
keeps a light, on-brand touch going until the timing turns, and traces it
when it does.

Live instance: https://jotpsych-case-study.onrender.com
(`/`, `/run-cycle`, `/metrics`, `/webhook/engagement` -- see below)

## The loop

```
data/sample_clinicians.csv (name, email, mobile -- exactly what the real list has)
        |
        v
  machine/intake.py     -- reads the CSV
  machine/decision.py   -- validates rows, derives segment + region from
                            email domain / area code alone, checks cooldown
                            + already-reactivated eligibility, picks a message
                            angle via an epsilon-greedy bandit
        |
        v
  machine/content.py    -- fills a segment/angle-aware template, stamps a
                            unique ref token
        |
        v
  machine/quality_gate.py -- grounding, length, banned-phrase/AI-tell,
                              exclamation-point checks. Fails closed: nothing
                              that fails ever reaches mailer.py
        |
        v
  machine/mailer.py     -- real SMTP send (Gmail app password)
        |
        v
  machine/state.py      -- the machine's own memory: who's been contacted,
                            bandit arm scores, full event log
        |
        v
  machine/engine.py     -- orchestrates one cycle, computes /metrics,
                            handles the engagement webhook (attribution)
```

Trigger: `app.py` exposes `POST /run-cycle` as the thing a schedule hits.
An in-process APScheduler job is wired up but disabled by default
(`SCHEDULER_ENABLED=true` to turn it on) so an idle deploy doesn't fire
real sends unattended. Production version: point an external cron
(Render Cron Job, cron-job.org, anything) at `/run-cycle` monthly.

## Rerun it with different data

This is the one thing to know: **swap the CSV, rerun, get different output.**

```bash
python3 run_cycle.py path/to/your_real_list.csv
```

`your_real_list.csv` needs exactly the columns `name,email,mobile` -- that's
all the real system hands us too. Nothing else in the pipeline changes.
Same thing via HTTP: `POST /run-cycle?csv=path/to/file.csv`.

Add `--dry-run` (or `?dry_run=true`) to exercise the full decision +
quality-gate logic without sending real email -- useful for testing
cooldown/eligibility behavior without spamming an inbox.

## What's real vs. sketched

**Built for real, runs end to end:**
- Intake, validation, segmentation (derived entirely from email/mobile --
  no enriched fields exist in the real data, so none are assumed here)
- Eligibility + cooldown (won't re-contact within 21 days or after
  reactivation)
- Epsilon-greedy bandit choosing a message angle per segment, updated from
  real outcomes each cycle
- Quality gate (fails closed, logs the reason)
- Real SMTP send + real IMAP-confirmed delivery
- `/metrics`, full event log, `/webhook/engagement` attribution

**Sketched / stubbed, documented not built:**
- **Recipient**: every send currently lands in one throwaway inbox
  (`jotpsychcasejl@gmail.com`) with a "would go to X" banner, standing in
  for each clinician's real inbox. Swapping in real per-clinician delivery
  is a one-line change in `mailer.py` (the `To` address).
- **SMS channel**: mobile number is only used to derive region/timezone
  right now. A second channel (e.g., Twilio) behind the same quality gate
  is a week-2 item, not built.
- **Reply parsing**: `/webhook/engagement` is called with a ref token to
  simulate a reply/click. Wiring it to real IMAP polling of the inbox for
  replies matching `ref: JP-xxxxxxxx` is straightforward but not built.
- **Human review surface**: rejected/needs-review items exist in the state
  log and are queryable, but there's no UI beyond that.

## Known limitation

The bandit's tie-breaking always favors the first angle in `ANGLES` when
scores are equal (i.e. at cold start), which biases early cycles toward
`time_savings`. Fine for a prototype; a real version would use optimistic
initialization or Thompson sampling instead of epsilon-greedy.

## Local setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GMAIL_ADDRESS / GMAIL_APP_PASSWORD
python3 run_cycle.py data/sample_clinicians.csv
```

`GMAIL_APP_PASSWORD` is a Gmail-generated app password (not the account
password) -- requires 2-Step Verification on the sending account.

See [PROOF.md](PROOF.md) for a captured full pass, and
[ONE_PAGER.md](ONE_PAGER.md) for the recommendation and numbers.
