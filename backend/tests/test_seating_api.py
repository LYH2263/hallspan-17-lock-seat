"""锁定位的端到端验收：保锁 / 锁位违法整场失败 / 解锁重排 / 历史方案不回刷。"""
import pytest
from fastapi.testclient import TestClient
from app.main import app

HALL = 1


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


@pytest.fixture(autouse=True)
def reset_state(client):
    """每个用例前后：最小间距复位为 2，并清掉最新方案上的所有锁。"""
    def _reset():
        client.put(f"/api/halls/{HALL}", json={"min_manhattan": 2})
        latest = client.get(f"/api/seating/latest?hall_id={HALL}").json()
        for a in latest.get("assignments", []):
            if a.get("locked"):
                client.post("/api/seating/lock",
                            json={"hall_id": HALL, "candidate_id": a["candidate_id"], "locked": False})
    _reset()
    yield
    _reset()


def _run(client):
    r = client.post(f"/api/seating/run?hall_id={HALL}")
    assert r.status_code == 200, r.text
    return r.json()


def _lock(client, cid, locked=True):
    r = client.post("/api/seating/lock", json={"hall_id": HALL, "candidate_id": cid, "locked": locked})
    assert r.status_code == 200, r.text
    return r.json()


def _plan_count(client):
    return len(client.get(f"/api/seating/plans?hall_id={HALL}").json())


def test_lock_corner_candidate_keeps_seat_after_rerun(client):
    plan1 = _run(client)
    corner = next(a for a in plan1["assignments"] if (a["row"], a["col"]) == (0, 0))
    _lock(client, corner["candidate_id"])
    plan2 = _run(client)
    again = next(a for a in plan2["assignments"] if a["candidate_id"] == corner["candidate_id"])
    assert (again["row"], again["col"]) == (0, 0)  # 行列不变
    assert again["locked"] is True                 # 锁标记带入新方案
    assert plan2["stats"]["locked"] == 1           # 统计与锁位一致


def test_illegal_lock_fails_whole_run_without_new_plan(client):
    plan = _run(client)
    # 锁一对曼哈顿距离恰好为 2 的已座考生
    by_id = {a["candidate_id"]: a for a in plan["assignments"]}
    pair = None
    ids = list(by_id)
    for i, x in enumerate(ids):
        for y in ids[i + 1:]:
            if abs(by_id[x]["row"] - by_id[y]["row"]) + abs(by_id[x]["col"] - by_id[y]["col"]) == 2:
                pair = (x, y)
                break
        if pair:
            break
    assert pair, "种子方案里应存在距离为 2 的座位对"
    _lock(client, pair[0])
    _lock(client, pair[1])
    # 把最小距改到锁位违法
    r = client.put(f"/api/halls/{HALL}", json={"min_manhattan": 3})
    assert r.status_code == 200
    before = _plan_count(client)
    r = client.post(f"/api/seating/run?hall_id={HALL}")
    assert r.status_code == 409                      # 整场失败
    assert "violations" in r.json()["detail"]
    assert _plan_count(client) == before             # 列表不增


def test_unlock_allows_next_run_to_rearrange(client):
    plan = _run(client)
    corner = next(a for a in plan["assignments"] if (a["row"], a["col"]) == (0, 0))
    _lock(client, corner["candidate_id"])
    _run(client)
    _lock(client, corner["candidate_id"], locked=False)  # 解锁
    plan_next = _run(client)                              # 下一次排座允许重排原格
    assert plan_next["stats"]["locked"] == 0
    assert all(not a.get("locked") for a in plan_next["assignments"])


def test_historical_plan_lock_marks_not_rewritten(client):
    plan1 = _run(client)
    corner = next(a for a in plan1["assignments"] if (a["row"], a["col"]) == (0, 0))
    locked_plan1 = _lock(client, corner["candidate_id"])
    snapshot = locked_plan1["assignments"]
    _run(client)  # 新排一轮
    r = client.get(f"/api/seating/plans/{plan1['id']}")
    assert r.status_code == 200
    assert r.json()["assignments"] == snapshot  # 历史方案锁标记与座位均未回刷


def test_lock_requires_seated_candidate(client):
    plan = _run(client)
    seated = {a["candidate_id"] for a in plan["assignments"]}
    r = client.post("/api/seating/lock", json={"hall_id": HALL, "candidate_id": 999999, "locked": True})
    assert r.status_code == 404
    assert seated  # 种子数据应全部落座
