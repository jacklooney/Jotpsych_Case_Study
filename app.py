import os

from dotenv import load_dotenv
from flask import Flask, jsonify, request

load_dotenv()

from machine.engine import metrics, record_engagement, run_cycle  # noqa: E402

app = Flask(__name__)

CSV_PATH = os.environ.get("INTAKE_CSV", "data/sample_clinicians.csv")
STATE_PATH = os.environ.get("STATE_PATH", "state.json")


@app.get("/")
def health():
    return {"status": "ok", "service": "jotpsych-reengagement-machine"}


@app.post("/run-cycle")
def trigger_cycle():
    """The trigger surface: a schedule (see _maybe_start_scheduler) or an
    external cron hits this. Swap ?csv= to point at a different list entirely."""
    dry_run = request.args.get("dry_run", "false").lower() == "true"
    csv_path = request.args.get("csv", CSV_PATH)
    report, _ = run_cycle(csv_path, state_path=STATE_PATH, live=not dry_run)
    return jsonify({
        "cycle": report["cycle"],
        "sent": len(report["sent"]),
        "rejected": len(report["rejected"]),
        "skipped": len(report["skipped"]),
        "invalid": len(report["invalid"]),
        "rejected_detail": [
            {"name": r["record"].get("name"), "reasons": r["reasons"]}
            for r in report["rejected"]
        ],
    })


@app.get("/metrics")
def get_metrics():
    return jsonify(metrics(STATE_PATH))


@app.post("/webhook/engagement")
def engagement_webhook():
    """Stand-in for a real reply/click handler: pass the ref token from a sent
    email and the machine traces it back to the exact clinician/cycle/angle."""
    payload = request.get_json(silent=True) or {}
    token = payload.get("token") or request.args.get("token")
    if not token:
        return jsonify({"error": "missing token"}), 400
    entry = record_engagement(token, STATE_PATH)
    if not entry:
        return jsonify({"matched": False}), 404
    return jsonify({"matched": True, "attributed_to": entry})


def _maybe_start_scheduler():
    if os.environ.get("SCHEDULER_ENABLED", "false").lower() != "true":
        return
    from apscheduler.schedulers.background import BackgroundScheduler

    minutes = int(os.environ.get("SCHEDULER_INTERVAL_MINUTES", "43200"))  # ~monthly
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: run_cycle(CSV_PATH, state_path=STATE_PATH, live=True),
        "interval", minutes=minutes, id="reengagement_cycle",
    )
    scheduler.start()


_maybe_start_scheduler()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
