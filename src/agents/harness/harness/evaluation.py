"""Metrics over canonical run and model-call contracts."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal


def summarize_runs(runs: list[dict], calls: list[dict]) -> dict:
    attempts = [
        (run, attempt)
        for run in runs
        for attempt in run.get("attempts", [])
    ]
    successful = [attempt for _, attempt in attempts if attempt.get("state") == "complete" and (attempt.get("result") or {}).get("pr_url")]
    keyset = {(run["run_id"], attempt["attempt_id"]) for run, attempt in attempts}
    joined_calls = [call for call in calls if (call.get("run_id"), call.get("attempt_id")) in keyset]
    cost = sum((Decimal(str(call["estimated_cost_usd"])) for call in joined_calls if call.get("estimated_cost_usd") is not None), Decimal(0))
    measured = sum(call.get("estimated_cost_usd") is not None for call in joined_calls)
    durations = [
        (datetime.fromisoformat(attempt["finished_at"]) - datetime.fromisoformat(attempt["started_at"])).total_seconds()
        for _, attempt in attempts if attempt.get("finished_at") and attempt.get("started_at")
    ]
    return {
        "attempts": len(attempts),
        "completed_prs": len(successful),
        "failed": sum(attempt.get("state") == "failed" for _, attempt in attempts),
        "cancelled": sum(attempt.get("state") == "cancelled" for _, attempt in attempts),
        "rejected_gates": sum(event.get("status") == "rejected" for _, attempt in attempts for event in attempt.get("events", [])),
        "model_calls": len(joined_calls),
        "calls_with_estimated_cost": measured,
        "estimated_model_cost_usd": str(cost),
        "estimated_cost_per_pr_usd": str(cost / len(successful)) if successful and joined_calls and measured == len(joined_calls) else None,
        "mean_attempt_duration_seconds": sum(durations) / len(durations) if durations else None,
    }
