import json
import os

DEFAULT_STATE = {"clinicians": {}, "bandit": {}, "log": [], "cycle_count": 0}


class State:
    """The machine's own working memory. Distinct from intake: intake is the raw
    list handed to us; this is everything the machine has learned across cycles
    (who's been contacted, what's worked, who's come back)."""

    def __init__(self, path="state.json"):
        self.path = path
        if os.path.exists(path):
            with open(path) as f:
                self.data = json.load(f)
        else:
            self.data = json.loads(json.dumps(DEFAULT_STATE))

    def save(self):
        with open(self.path, "w") as f:
            json.dump(self.data, f, indent=2, default=str)

    def clinician(self, key):
        return self.data["clinicians"].setdefault(key, {
            "last_contacted": None,
            "cycles_contacted": 0,
            "reactivated": False,
            "reactivated_at": None,
            "reactivated_via": None,
        })

    def bandit_arms(self, segment_key, angles):
        seg = self.data["bandit"].setdefault(segment_key, {})
        for a in angles:
            seg.setdefault(a, {"sends": 0, "rejects": 0, "engagements": 0})
        return seg

    def record_bandit(self, segment_key, angle, outcome):
        arm = self.data["bandit"][segment_key][angle]
        if outcome == "sent":
            arm["sends"] += 1
        elif outcome == "rejected":
            arm["rejects"] += 1
        elif outcome == "engaged":
            arm["engagements"] += 1

    def log(self, entry):
        self.data["log"].append(entry)

    def find_by_token(self, token):
        for entry in reversed(self.data["log"]):
            if entry.get("token") == token and entry.get("type") == "sent":
                return entry
        return None
