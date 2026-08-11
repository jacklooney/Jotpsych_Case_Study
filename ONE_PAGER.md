# Recommendation

Build an unattended monthly re-engagement machine over the lapsed-signup
list (name, email, mobile -- nothing more). It segments each clinician
purely from what's derivable from those three fields (email domain →
solo vs. group practice; area code → region/timezone), picks one of four
JotPsych-grounded message angles per segment via a self-adjusting bandit,
generates and quality-gates a short, low-pressure note, and sends it. A
unique ref token on every send means a reply traces straight back to the
exact clinician, cycle, and angle that worked -- that's how JotPsych
notices the moment timing turns, without anyone watching a dashboard.

**Why this over alternatives**: the honest constraint is we only have
name/email/mobile -- no specialty, no practice size, no reason they
lapsed. A machine that pretends otherwise (fake enrichment, hallucinated
personal details) would be the thing that "smells like AI." Deriving
real signal from what we actually have, and letting outcomes (not a human)
decide what to say more of, is the sane answer for this data shape.

## The numbers it reports (`/metrics`, from the captured proof run)

| Metric | Cycle 1 | After cycle 2 |
|---|---|---|
| Sent | 33 | 35 |
| Rejected by quality gate | 3 | 4 |
| Skipped (cooldown/reactivated) | 0 | 33 |
| Invalid rows (bad data, never touched) | 4 | 4 |
| Reactivated (attributed) | 0 | **1** |

North-star metric: **reactivations attributed per cycle** (a reply/click
traced via ref token back to a specific send). Secondary: reject rate by
reason (brand-safety health check) and bandit score per segment/angle
(is it actually learning what works).

## Where the 1-2 human hours a month go

- **~45 min**: skim the `needs_review` log (everything the quality gate
  rejected) -- confirm it's catching real problems, not being too strict
  or too loose. Adjust the banned-phrase list or angle copy if a pattern
  shows up.
- **~30 min**: spot-check ~10 random *sent* messages for tone, independent
  of the gate, since the gate can't catch everything a human would.
- **~15-30 min**: review the reactivated list. These are warm -- hand them
  to sales/CS directly rather than letting the machine keep emailing them
  (it already stops on its own once `reactivated`, but a human confirms
  the handoff actually happened).

Nothing in that hour involves reading or approving outbound copy before
it sends -- that's what the gate is for. At thousands of clinicians, a
human in that loop is the thing that makes the "1-2 hours" number a lie.

## Week two

1. **Real recipient delivery**: swap the throwaway-inbox stand-in for
   real per-clinician `To` addresses (one line in `mailer.py`) once
   sending domain/reputation is set up (SPF/DKIM, a real sending domain
   -- not a personal Gmail, at scale).
2. **Real reply parsing**: replace the manual webhook simulation with
   IMAP polling (or a proper inbound-email service) matching `ref:
   JP-xxxxxxxx` in real replies -- the attribution logic underneath
   doesn't change.
3. **SMS channel**: mobile number is currently only used for
   timezone/region. Add a second channel behind the same quality gate
   for clinicians who don't open email -- same bandit, one more arm
   dimension.
4. **Fix bandit cold-start bias**: current epsilon-greedy always
   tie-breaks toward the first-listed angle at zero engagement. Swap
   for optimistic initialization or Thompson sampling so early cycles
   explore more evenly.
5. **Expand the angle library** using cycle-1/2 signal instead of the
   four starting guesses -- more angles, segmented further (specialty
   hints already extracted from email/domain but not yet used to
   branch messaging).
