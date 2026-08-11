BANNED_PHRASES = [
    "game changer", "game-changer", "don't miss out", "act now", "limited time",
    "unlock", "seamless", "i hope this email finds you well",
    "in today's fast-paced world", "cutting-edge", "revolutionize", "supercharge",
]

MIN_WORDS = 35
MAX_WORDS = 160


def run(record, draft):
    """Every draft passes through here before it's allowed to send. Anything
    that fails never reaches an inbox -- it's logged with the reason instead."""
    reasons = []
    body = draft["body"]
    lower = body.lower()

    name_tokens = [t.strip(".,") for t in (record.get("name") or "").split()
                   if t.lower() not in ("dr.", "dr", "")]
    fname = name_tokens[0] if name_tokens else None
    if not fname or fname.lower() not in lower:
        reasons.append("missing_personalization")

    word_count = len(body.split())
    if word_count < MIN_WORDS:
        reasons.append("too_short")
    if word_count > MAX_WORDS:
        reasons.append("too_long")

    for phrase in BANNED_PHRASES:
        if phrase in lower:
            reasons.append(f"banned_phrase:{phrase}")

    if "jotpsych" not in lower:
        reasons.append("missing_brand_grounding")

    if body.count("!") > 1:
        reasons.append("excess_exclamation")

    return (len(reasons) == 0), reasons
