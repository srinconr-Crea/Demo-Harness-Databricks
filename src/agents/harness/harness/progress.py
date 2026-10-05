"""Evidence-derived progress; no success inferred from a later phase."""

PHASES = ["explore", "propose", "update", "apply", "verify", "sync", "archive", "PR"]
STAGES = {
    "exploring": "explore",
    "awaiting_clarification": "explore",
    "proposing": "propose",
    "awaiting_plan_review": "propose",
    "updating": "update",
    "applying": "apply",
    "verifying": "verify",
    "preparing_final_diff": "archive",
    "publishing": "PR",
}


def checklist(attempt):
    events = attempt.get("timeline", [])
    base_reset = max(
        (e["seq"] for e in events if e["kind"] == "base_advanced"), default=0
    )
    revision = attempt.get("revision", 0)
    rows = []
    for phase in PHASES:
        kinds = (
            {"publication_complete", "pr_created"}
            if phase == "PR"
            else ({"propose", "update"} if phase == "propose" else {phase})
        )
        candidates = [
            e
            for e in events
            if e["seq"] > base_reset
            and e["kind"] in kinds
            and (e["revision"] == revision or phase == "explore")
        ]
        event = candidates[-1] if candidates else None
        active = STAGES.get(attempt.get("stage")) == phase
        state = "ok" if event else ("running" if active else "pending")
        if phase == "update" and not any(e["kind"] == "update" for e in events):
            state = "not_applicable" if not active else "running"
        errors = [
            e
            for e in events
            if e["seq"] > base_reset
            and e["kind"] in {"error", "verify_failed", "verify_findings"}
            and e["revision"] == revision
            and STAGES.get(e.get("stage")) == phase
        ]
        if errors and (event is None or errors[-1]["seq"] > event["seq"]):
            state, event = "failed", errors[-1]
        failure = attempt.get('failure') or {}
        if attempt.get('stage') == 'failed' and STAGES.get(failure.get('failed_stage')) == phase:
            state = 'failed'
        if active and attempt.get("stage", "").startswith("awaiting_"):
            state = "blocked"
        rows.append(
            {
                "phase": phase,
                "status": state,
                "at": event.get("at") if event else None,
                "revision": event.get("revision", revision) if event else revision,
            }
        )
    return rows
