import hashlib
import random

# Grounded in what JotPsych actually says about itself (jotpsych.com / jotpsych.ai):
# AI scribe + notes + billing/coding for behavioral health, ~30 hrs/month back,
# fewer denials/downcodes via 150+ payer-rule checks, modular ("just the parts you want").
VALUE_PROPS = {
    "time_savings": (
        "clinicians on JotPsych are getting roughly 30 hours of documentation "
        "time back a month"
    ),
    "revenue_protection": (
        "JotPsych checks notes against 150+ payer rules before you submit, so "
        "fewer claims come back downcoded or denied"
    ),
    "practice_growth": (
        "practices are using it to standardize notes across every clinician on "
        "the team without adding admin headcount"
    ),
    "no_pressure": (
        "no pitch here -- just flagging that a lot has changed on our end since "
        "you first looked"
    ),
}

SEGMENT_CONTEXT = {
    "group": "for a group like yours",
    "solo": "for an independent practice like yours",
}

CLOSERS_SAFE = [
    "If it's still not the right moment, no need to reply.",
    "Happy to send a two-minute walkthrough if that's easier than a call.",
    "Either way, hope the next few weeks are a little lighter on paperwork.",
]

# Deliberately off-brand -- lets the quality gate demonstrate it actually catches
# something, rather than only ever seeing clean output.
CLOSERS_RISKY = [
    "This is a total game changer, don't miss out this quarter!",
]

RISKY_CLOSER_RATE = 0.15


def build_token(key, cycle, angle):
    raw = f"{key}:{cycle}:{angle}".encode()
    return "JP-" + hashlib.sha1(raw).hexdigest()[:8]


def first_name(record):
    tokens = [t.strip(".,") for t in (record.get("name") or "").split()
              if t.lower() not in ("dr.", "dr", "")]
    return tokens[0] if tokens else "there"


def generate(record, seg, angle, cycle, key):
    name = first_name(record)
    value_prop = VALUE_PROPS[angle]
    context = SEGMENT_CONTEXT.get(seg["practice_type"], "for your practice")
    token = build_token(key, cycle, angle)

    closer = random.choice(CLOSERS_RISKY) if random.random() < RISKY_CLOSER_RATE \
        else random.choice(CLOSERS_SAFE)

    body = (
        f"Hi {name},\n\n"
        f"You looked at JotPsych a while back, and {value_prop} {context}.\n\n"
        f"{closer}\n\n"
        f"Reply any time this feels newly relevant (ref: {token}).\n\n"
        f"-- The JotPsych team"
    )
    subject = f"{name}, a quick JotPsych update"
    return {"subject": subject, "body": body, "token": token}
