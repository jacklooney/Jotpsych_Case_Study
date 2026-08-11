from datetime import datetime, timezone

from . import content, decision, intake, mailer, quality_gate
from .state import State


def run_cycle(csv_path, state_path="state.json", live=True):
    state = State(state_path)
    rows = intake.load(csv_path)
    cycle = state.data["cycle_count"] + 1
    now = datetime.now(timezone.utc)

    report = {"cycle": cycle, "sent": [], "rejected": [], "skipped": [], "invalid": []}

    for record in rows:
        errors, digits = decision.validate(record)
        if errors:
            report["invalid"].append({"record": record, "reasons": errors})
            state.log({"type": "invalid", "cycle": cycle, "record": record,
                       "reasons": errors, "at": now.isoformat()})
            continue

        key = decision.clinician_key(record)
        c_state = state.clinician(key)

        ok, why = decision.eligible(c_state, now)
        if not ok:
            report["skipped"].append({"record": record, "reason": why})
            state.log({"type": "skipped", "cycle": cycle, "key": key,
                       "reason": why, "at": now.isoformat()})
            continue

        seg = decision.segment(record, digits)
        segment_key = seg["practice_type"]
        angle = decision.choose_angle(state, segment_key)
        draft = content.generate(record, seg, angle, cycle, key)

        passed, reasons = quality_gate.run(record, draft)
        if not passed:
            state.record_bandit(segment_key, angle, "rejected")
            report["rejected"].append({
                "record": record, "angle": angle, "segment": segment_key,
                "reasons": reasons, "draft": draft,
            })
            state.log({"type": "rejected", "cycle": cycle, "key": key,
                       "segment": segment_key, "angle": angle, "reasons": reasons,
                       "subject": draft["subject"], "at": now.isoformat()})
            continue

        result = mailer.send(record, draft["subject"], draft["body"], dry_run=not live)
        state.record_bandit(segment_key, angle, "sent")
        c_state["last_contacted"] = now.isoformat()
        c_state["cycles_contacted"] += 1
        report["sent"].append({
            "record": record, "angle": angle, "segment": segment_key,
            "token": draft["token"], "subject": draft["subject"], "result": result,
        })
        state.log({"type": "sent", "cycle": cycle, "key": key, "segment": segment_key,
                   "angle": angle, "token": draft["token"], "subject": draft["subject"],
                   "mail_result": result["status"], "at": now.isoformat()})

    state.data["cycle_count"] = cycle
    state.save()
    return report, state


def record_engagement(token, state_path="state.json"):
    """Simulated inbound signal: a dormant clinician replied/clicked. Traces the
    token straight back to the clinician, cycle, and angle that brought them back,
    and feeds a positive reward into the bandit that chose that angle."""
    state = State(state_path)
    entry = state.find_by_token(token)
    if not entry:
        return None

    c_state = state.clinician(entry["key"])
    already = c_state.get("reactivated")
    c_state["reactivated"] = True
    c_state["reactivated_at"] = datetime.now(timezone.utc).isoformat()
    c_state["reactivated_via"] = token

    if not already:
        state.record_bandit(entry["segment"], entry["angle"], "engaged")

    state.log({"type": "engaged", "token": token, "key": entry["key"],
               "segment": entry["segment"], "angle": entry["angle"],
               "cycle": entry["cycle"], "at": c_state["reactivated_at"]})
    state.save()
    return entry


def metrics(state_path="state.json"):
    state = State(state_path)
    log = state.data["log"]
    counts = {"sent": 0, "rejected": 0, "skipped": 0, "invalid": 0, "engaged": 0}
    reject_reasons = {}
    for entry in log:
        t = entry["type"]
        counts[t] = counts.get(t, 0) + 1
        if t == "rejected":
            for r in entry["reasons"]:
                reject_reasons[r] = reject_reasons.get(r, 0) + 1

    bandit_table = []
    for segment_key, arms in state.data["bandit"].items():
        for angle, arm in arms.items():
            bandit_table.append({
                "segment": segment_key, "angle": angle,
                **arm,
                "score": round(decision.arm_score(arm), 3),
            })

    reactivated = sum(1 for c in state.data["clinicians"].values() if c.get("reactivated"))

    return {
        "cycle_count": state.data["cycle_count"],
        "clinicians_tracked": len(state.data["clinicians"]),
        "totals": counts,
        "reactivated_total": reactivated,
        "reject_reasons": reject_reasons,
        "bandit": sorted(bandit_table, key=lambda r: (r["segment"], -r["score"])),
    }
