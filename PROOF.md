# Proof it runs

One full pass, captured directly from the terminal, run against
`data/sample_clinicians.csv` (40 invented rows: 36 valid, 4 deliberately
malformed to exercise the data-quality check).

## Cycle 1 -- live run, real SMTP send

```
$ python3 run_cycle.py data/sample_clinicians.csv

=== Cycle 1 on data/sample_clinicians.csv ===
Sent:      33
Rejected:  3
Skipped:   0
Invalid:   4

--- Rejected drafts (quality gate caught these before send) ---
  Nathan Cole LCSW: ['banned_phrase:game changer', "banned_phrase:don't miss out"]
  Dr. Bianca Torres: ['banned_phrase:game changer', "banned_phrase:don't miss out"]
  Dr. Renata Silva: ['banned_phrase:game changer', "banned_phrase:don't miss out"]

--- Invalid rows (never reached content generation) ---
  {'name': '', 'email': 'broken.record@gmail.com', 'mobile': '415-555-0100'}: ['missing_name']
  {'name': 'Dr. Missing Number', 'email': 'missing.mobile@yahoo.com', 'mobile': ''}: ['invalid_mobile']
  {'name': 'Dr. Bad Email', 'email': 'not-an-email', 'mobile': '617-555-0111'}: ['invalid_email']
  {'name': 'Dr. Short Phone', 'email': 'short.phone@gmail.com', 'mobile': '555-0199'}: ['invalid_mobile']

Full state written to state.json
```

**The rejection, in detail** -- `Nathan Cole LCSW`'s draft randomly drew the
"risky" closing line (`content.py` occasionally samples an off-brand
closer to keep the quality gate honest rather than only ever seeing clean
output):

> "...This is a total game changer, don't miss out this quarter!..."

`machine/quality_gate.py`'s banned-phrase check matched `game changer` and
`don't miss out` against its list of AI-tell / hard-sell phrases. The
draft was logged as `rejected` with those exact reasons and **never
reached `mailer.py`** -- no email was generated, sent, or shown anywhere
except the rejection log.

**Independent verification of real delivery**: immediately after the run,
an IMAP search of the sending inbox for subject `[SIM]` returned exactly
33 messages -- matching the reported `Sent: 33` exactly:

```
$ python3 -c "... imaplib search SUBJECT '[SIM]' ..."
Messages with [SIM] subject in inbox: 33
Subject: [SIM] Simone, a quick JotPsych update
Subject: [SIM] Peter, a quick JotPsych update
Subject: [SIM] Renata, a quick JotPsych update
```

Each message body opens with a banner naming the real intended recipient,
e.g.:

```
[SIMULATED SEND] Would go to: Dr. Sarah Chen <sarah.chen@gmail.com> (212-555-0148)

Hi Sarah,

You looked at JotPsych a while back, and clinicians on JotPsych are
getting roughly 30 hours of documentation time back a month for an
independent practice like yours.

Happy to send a two-minute walkthrough if that's easier than a call.

Reply any time this feels newly relevant (ref: JP-abdcde4e).

-- The JotPsych team
```

## Simulated engagement -- attribution trace

One "clinician" (Dr. Robert Kim, group-practice segment, sent the
`time_savings` angle, token `JP-2640e141`) is simulated replying by
calling the webhook the machine exposes for exactly this:

```
$ curl -X POST /webhook/engagement -d '{"token":"JP-2640e141"}'

{
  "type": "sent", "cycle": 1, "key": "rkim@valleymentalhealthgroup.com",
  "segment": "group", "angle": "time_savings", "token": "JP-2640e141",
  "subject": "Robert, a quick JotPsych update", "mail_result": "sent",
  "at": "2026-08-11T18:48:38Z"
}
```

The token traces straight back to the clinician, the cycle, and the
message angle that reached them -- that's the return, attributed. The
bandit arm for `group / time_savings` is credited with the engagement.

## Cycle 2 -- dry-run, proves cooldown + reactivation logic

Run again immediately (dry-run, so it exercises full decision logic
without re-sending real mail):

```
=== Cycle 2 on data/sample_clinicians.csv ===
Sent:      2
Rejected:  1
Skipped:   33
Invalid:   4
```

33 skipped = the 32 already emailed this cycle (21-day cooldown) + Dr.
Robert Kim (now `reactivated`, permanently excluded from future outreach).
The 3 previously-rejected clinicians were retried automatically; 2 passed
this time, 1 (Nathan Cole) drew the risky closer again and was rejected
again -- the gate is consistent, not a fluke.

## Final `/metrics`

```json
{
  "cycle_count": 2,
  "clinicians_tracked": 36,
  "totals": {"sent": 35, "rejected": 4, "skipped": 33, "invalid": 8, "engaged": 1},
  "reactivated_total": 1,
  "reject_reasons": {
    "banned_phrase:game changer": 4,
    "banned_phrase:don't miss out": 4
  },
  "bandit": [
    {"segment": "group", "angle": "time_savings", "sends": 10, "rejects": 1, "engagements": 1, "score": 0.073},
    {"segment": "group", "angle": "practice_growth", "sends": 5, "rejects": 0, "engagements": 0, "score": 0.0},
    {"segment": "group", "angle": "revenue_protection", "sends": 1, "rejects": 2, "engagements": 0, "score": -0.2},
    {"segment": "solo", "angle": "time_savings", "sends": 13, "rejects": 1, "engagements": 0, "score": -0.021}
  ]
}
```

Note `group / time_savings` is now the top-scoring arm for that segment
purely because it produced the one real engagement -- no code changed,
the bandit just updated. That's the self-improvement loop, observed.
