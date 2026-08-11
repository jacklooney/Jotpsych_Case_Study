import random
import re

COOLDOWN_DAYS = 21

ANGLES = ["time_savings", "revenue_protection", "practice_growth", "no_pressure"]

AREA_CODE_MAP = {
    "212": ("NY", "America/New_York"), "646": ("NY", "America/New_York"),
    "617": ("MA", "America/New_York"), "704": ("NC", "America/New_York"),
    "404": ("GA", "America/New_York"), "305": ("FL", "America/New_York"),
    "614": ("OH", "America/New_York"),
    "312": ("IL", "America/Chicago"), "773": ("IL", "America/Chicago"),
    "512": ("TX", "America/Chicago"), "469": ("TX", "America/Chicago"),
    "214": ("TX", "America/Chicago"), "713": ("TX", "America/Chicago"),
    "913": ("KS", "America/Chicago"), "847": ("IL", "America/Chicago"),
    "303": ("CO", "America/Denver"), "720": ("CO", "America/Denver"),
    "602": ("AZ", "America/Phoenix"),
    "310": ("CA", "America/Los_Angeles"), "415": ("CA", "America/Los_Angeles"),
    "619": ("CA", "America/Los_Angeles"), "510": ("CA", "America/Los_Angeles"),
    "206": ("WA", "America/Los_Angeles"), "503": ("OR", "America/Los_Angeles"),
    "702": ("NV", "America/Los_Angeles"),
}

SPECIALTY_HINTS = {
    "psych": "psychiatry",
    "behavioral": "behavioral health",
    "mental": "mental health",
    "wellness": "wellness-focused care",
    "mind": "mental health",
    "counsel": "counseling",
}

PERSONAL_DOMAINS = {"gmail.com", "yahoo.com", "outlook.com", "icloud.com", "hotmail.com"}


def clinician_key(record):
    email = (record.get("email") or "").strip().lower()
    if email:
        return email
    return f"{(record.get('name') or '').strip().lower()}|{(record.get('mobile') or '').strip()}"


def validate(record):
    """The only fields the real system gives us: name, email, mobile.
    Anything malformed gets flagged here and never reaches content generation."""
    errors = []
    name = (record.get("name") or "").strip()
    email = (record.get("email") or "").strip()
    mobile = (record.get("mobile") or "").strip()

    if not name:
        errors.append("missing_name")
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email):
        errors.append("invalid_email")

    digits = re.sub(r"\D", "", mobile)
    if len(digits) != 10:
        errors.append("invalid_mobile")

    return errors, digits


def segment(record, digits):
    """Everything below is derived from name/email/mobile alone -- no enriched
    fields exist in the real system, so the decision layer can't lean on them."""
    email = (record.get("email") or "").strip().lower()
    domain = email.split("@")[-1] if "@" in email else ""
    domain_type = "institutional" if domain not in PERSONAL_DOMAINS else "personal"
    practice_type = "group" if domain_type == "institutional" else "solo"

    haystack = f"{email} {record.get('name', '')}".lower()
    specialty_hint = "general behavioral health"
    for key, label in SPECIALTY_HINTS.items():
        if key in haystack:
            specialty_hint = label
            break

    area_code = digits[:3] if len(digits) == 10 else None
    state, tz = AREA_CODE_MAP.get(area_code, (None, "America/New_York"))

    return {
        "domain_type": domain_type,
        "practice_type": practice_type,
        "specialty_hint": specialty_hint,
        "state": state,
        "timezone": tz,
    }


def arm_score(arm):
    sends = arm["sends"]
    if sends == 0:
        return 0.0
    reject_rate = arm["rejects"] / (sends + arm["rejects"])
    return (arm["engagements"] / sends) - (0.3 * reject_rate)


def choose_angle(state_store, segment_key, epsilon=0.2):
    """Epsilon-greedy: mostly exploit the best-scoring angle for this segment,
    occasionally explore another so the bandit keeps learning instead of locking in early."""
    arms = state_store.bandit_arms(segment_key, ANGLES)
    if random.random() < epsilon or all(a["sends"] == 0 for a in arms.values()):
        return random.choice(ANGLES)
    return max(ANGLES, key=lambda a: arm_score(arms[a]))


def eligible(clinician_state, now):
    if clinician_state.get("reactivated"):
        return False, "already_reactivated"
    last = clinician_state.get("last_contacted")
    if last:
        from datetime import datetime
        elapsed = (now - datetime.fromisoformat(last)).days
        if elapsed < COOLDOWN_DAYS:
            return False, "cooldown_active"
    return True, None
