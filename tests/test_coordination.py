from concurrent.futures import ThreadPoolExecutor

from harness.coordination import DeltaRunCoordinator, SqliteRunCoordinator


class StatementAPI:
    def __init__(self, responses):
        self.responses = iter(responses)
        self.calls = []

    def do(self, method, path, body=None):
        self.calls.append((method, path, body))
        return next(self.responses)


def statement_row(version, stage="queued", owner=None, key=None):
    return {"status": {"state": "SUCCEEDED"}, "result": {"data_array": [[
        "run-1", "attempt-1", stage, str(version), owner, None, key, None,
    ]]}}


def test_expired_lease_can_be_claimed_by_only_one_worker(tmp_path):
    coordinator = SqliteRunCoordinator(tmp_path / "state.db")
    coordinator.create("run-1", "attempt-1", "queued")
    first = coordinator.claim("run-1", "attempt-1", expected_version=0, owner="worker-a", key="start-a", now=100, ttl_seconds=20)
    assert first["version"] == 1
    assert coordinator.claim("run-1", "attempt-1", expected_version=1, owner="worker-b", key="start-b", now=110, ttl_seconds=20) is None

    def recover(owner):
        return coordinator.claim("run-1", "attempt-1", expected_version=1, owner=owner, key=f"recover-{owner}", now=121, ttl_seconds=20)

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(recover, ("worker-b", "worker-c")))
    winners = [item for item in results if item is not None]
    assert len(winners) == 1
    assert winners[0]["version"] == 2


def test_transition_requires_live_lease_and_is_idempotent(tmp_path):
    coordinator = SqliteRunCoordinator(tmp_path / "state.db")
    coordinator.create("run-1", "attempt-1", "queued")
    coordinator.claim("run-1", "attempt-1", expected_version=0, owner="worker-a", key="start-a", now=100, ttl_seconds=20)
    assert coordinator.finish("run-1", "attempt-1", expected_version=1, owner="worker-b", key="pause", stage="awaiting_plan_review", checkpoint_id="cp1", now=101) is None
    finished = coordinator.finish("run-1", "attempt-1", expected_version=1, owner="worker-a", key="pause", stage="awaiting_plan_review", checkpoint_id="cp1", now=101)
    assert finished["version"] == 2
    assert finished["checkpoint_id"] == "cp1"
    assert coordinator.finish("run-1", "attempt-1", expected_version=1, owner="worker-a", key="pause", stage="awaiting_plan_review", checkpoint_id="cp1", now=101) == finished
    assert coordinator.finish("run-1", "attempt-1", expected_version=1, owner="worker-a", key="other", stage="publishing", checkpoint_id="cp2", now=101) is None


def test_delta_coordinator_uses_bound_values_and_rejects_lost_claim():
    api = StatementAPI([
        {"status": {"state": "SUCCEEDED"}},
        statement_row(2, owner="worker-b", key="other"),
    ])
    coordinator = DeltaRunCoordinator(
        api, "warehouse-1", "demo_harness_catalog.demo_harness_schema.demo_harness_run_state",
    )
    assert coordinator.claim("run-1", "attempt-1", expected_version=1, owner="worker-a", key="claim-a", now=100, ttl_seconds=20) is None
    statement = api.calls[0][2]["statement"]
    parameters = {item["name"]: item["value"] for item in api.calls[0][2]["parameters"]}
    assert "version = :expected_version" in statement
    assert "run-1" not in statement
    assert parameters["run_id"] == "run-1"


def test_delta_table_provisioning_targets_only_the_harness_table():
    api = StatementAPI([{"status": {"state": "SUCCEEDED"}}])
    coordinator = DeltaRunCoordinator(api, "warehouse-1", "demo_harness_catalog.demo_harness_schema.demo_harness_run_state")
    coordinator.provision()
    ddl = api.calls[0][2]["statement"]
    assert "CREATE TABLE IF NOT EXISTS `demo_harness_catalog`.`demo_harness_schema`.`demo_harness_run_state`" in ddl
    assert "USING DELTA" in ddl
    assert "PRIMARY KEY" not in ddl
