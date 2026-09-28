from harness.evaluation import summarize_runs


def test_evaluation_joins_calls_to_the_correct_attempt_and_preserves_missing_cost():
    runs = [{"run_id": "r", "attempts": [
        {"attempt_id": "a1", "state": "failed", "events": [{"status": "rejected"}]},
        {"attempt_id": "a2", "state": "complete", "result": {"pr_url": "https://github.com/o/r/pull/1"}},
    ]}]
    calls = [
        {"run_id": "r", "attempt_id": "a1", "estimated_cost_usd": "0.10"},
        {"run_id": "r", "attempt_id": "a2", "estimated_cost_usd": None},
        {"run_id": "other", "attempt_id": "a2", "estimated_cost_usd": "999"},
    ]
    result = summarize_runs(runs, calls)
    assert result["attempts"] == 2
    assert result["completed_prs"] == 1
    assert result["rejected_gates"] == 1
    assert result["model_calls"] == 2
    assert result["estimated_model_cost_usd"] == "0.10"
    assert result["estimated_cost_per_pr_usd"] is None
