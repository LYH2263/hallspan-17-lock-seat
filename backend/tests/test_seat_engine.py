from app.services.seat_engine import (SeatAssign, check_locked, find_violations,
                                      locked_from_plan, manhattan, place_candidates)

def test_manhattan():
    assert manhattan((0, 0), (2, 1)) == 3

def test_min_distance_placement():
    cands = [{"id": i, "name": f"C{i}", "ticket_no": f"T{i}", "paper_id": 1 + (i % 2)} for i in range(4)]
    assigns, unplaced = place_candidates(4, 4, 2, cands)
    assert len(assigns) + len(unplaced) == 4
    for i, a in enumerate(assigns):
        for b in assigns[i+1:]:
            assert manhattan((a.row, a.col), (b.row, b.col)) >= 2

def test_same_paper_not_adjacent_in_result():
    # Force two same paper — engine should avoid 4-neigh
    cands = [
        {"id": 1, "name": "A", "ticket_no": "T1", "paper_id": 1},
        {"id": 2, "name": "B", "ticket_no": "T2", "paper_id": 1},
        {"id": 3, "name": "C", "ticket_no": "T3", "paper_id": 2},
    ]
    assigns, _ = place_candidates(3, 3, 1, cands)
    viols = find_violations(3, 3, 1, assigns)
    assert not any(v.kind == "same_paper_adjacent" for v in viols)

def test_violation_detection():
    assigns = [
        SeatAssign(1, "A", "T1", 1, 0, 0),
        SeatAssign(2, "B", "T2", 1, 0, 1),
    ]
    viols = find_violations(2, 2, 2, assigns)
    kinds = {v.kind for v in viols}
    assert "distance" in kinds
    assert "same_paper_adjacent" in kinds

def test_locked_seat_is_pinned():
    cands = [{"id": i, "name": f"C{i}", "ticket_no": f"T{i}", "paper_id": i} for i in range(1, 4)]
    locked = [SeatAssign(1, "C1", "T1", 1, 3, 3, True)]
    assigns, _ = place_candidates(4, 4, 1, cands, locked=locked)
    a1 = next(a for a in assigns if a.candidate_id == 1)
    assert (a1.row, a1.col) == (3, 3) and a1.locked
    # 锁位不被别人占用
    assert sum(1 for a in assigns if (a.row, a.col) == (3, 3)) == 1

def test_locked_not_moved_even_if_greedy_would():
    # 无锁时 1 号考生会落在 (0,0)；锁在 (1,1) 必须原地保留，禁止拆锁硬排
    cands = [{"id": 1, "name": "A", "ticket_no": "T1", "paper_id": 1}]
    locked = [SeatAssign(1, "A", "T1", 1, 1, 1, True)]
    assigns, _ = place_candidates(3, 3, 1, cands, locked=locked)
    assert (assigns[0].row, assigns[0].col) == (1, 1)

def test_locked_placement_respects_locks_as_obstacles():
    # 新排考生与锁位保持最小间距
    cands = [{"id": i, "name": f"C{i}", "ticket_no": f"T{i}", "paper_id": i} for i in range(2, 6)]
    locked = [SeatAssign(1, "C1", "T1", 99, 1, 1, True)]
    assigns, _ = place_candidates(4, 4, 2, cands, locked=locked)
    for a in assigns:
        if a.candidate_id == 1:
            continue
        assert manhattan((a.row, a.col), (1, 1)) >= 2

def test_check_locked_detects_distance_violation():
    locked = [SeatAssign(1, "A", "T1", 1, 0, 0, True), SeatAssign(2, "B", "T2", 2, 0, 2, True)]
    assert check_locked(5, 6, 2, locked) == []
    viols = check_locked(5, 6, 3, locked)
    assert any(v.kind == "distance" for v in viols)

def test_check_locked_out_of_bounds_and_overlap():
    v1 = check_locked(2, 2, 1, [SeatAssign(1, "A", "T1", 1, 5, 5, True)])
    assert v1 and v1[0].kind == "locked_out_of_bounds"
    v2 = check_locked(3, 3, 1, [SeatAssign(1, "A", "T1", 1, 0, 0, True),
                                SeatAssign(2, "B", "T2", 2, 0, 0, True)])
    assert any(v.kind == "locked_overlap" for v in v2)

def test_locked_from_plan_carries_only_present_candidates():
    plan_assigns = [
        {"candidate_id": 1, "row": 0, "col": 0, "locked": True},
        {"candidate_id": 2, "row": 0, "col": 2, "locked": True},   # 已不在考场
        {"candidate_id": 3, "row": 1, "col": 1, "locked": False},  # 未锁
    ]
    cands = [{"id": 1, "name": "A", "ticket_no": "T1", "paper_id": 7},
             {"id": 3, "name": "C", "ticket_no": "T3", "paper_id": 9}]
    locked = locked_from_plan(plan_assigns, cands)
    assert [a.candidate_id for a in locked] == [1]
    assert locked[0].paper_id == 7  # 用考生当前试卷，不用方案里的旧数据
    assert (locked[0].row, locked[0].col) == (0, 0)
