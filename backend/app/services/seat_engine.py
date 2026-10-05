"""Exam seating: min Manhattan distance; same paper_id cannot be 4-neighbor adjacent.

Locked seats: a previous plan may mark some assignments as locked. Locked
candidates are pinned to their original (row, col) and are placed before
everyone else; the greedy pass never moves them ("保锁", never "拆锁硬排").
If the locked set itself is illegal under the current constraints, the whole
run must fail — check_locked() reports why and the caller aborts.
"""
from __future__ import annotations
from dataclasses import asdict, dataclass

@dataclass
class SeatAssign:
    candidate_id: int
    name: str
    ticket_no: str
    paper_id: int
    row: int
    col: int
    locked: bool = False

@dataclass
class Violation:
    kind: str
    a_id: int
    b_id: int
    detail: str

def manhattan(a: tuple[int, int], b: tuple[int, int]) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

def neighbors4(r: int, c: int, rows: int, cols: int) -> list[tuple[int, int]]:
    out = []
    for dr, dc in ((0, 1), (0, -1), (1, 0), (-1, 0)):
        nr, nc = r + dr, c + dc
        if 0 <= nr < rows and 0 <= nc < cols:
            out.append((nr, nc))
    return out

def locked_from_plan(assignments: list[dict], candidates: list[dict]) -> list[SeatAssign]:
    """Carry locks from a previous plan's assignments.

    Only candidates still in the hall keep their lock; seat (row, col) comes
    from the plan, name/paper come from the current candidate table.
    """
    by_id = {c["id"]: c for c in candidates}
    locked: list[SeatAssign] = []
    for a in assignments:
        if not a.get("locked"):
            continue
        cand = by_id.get(a.get("candidate_id"))
        if cand is None:
            continue
        locked.append(SeatAssign(cand["id"], cand["name"], cand["ticket_no"],
                                 cand["paper_id"], a["row"], a["col"], True))
    return locked

def check_locked(rows: int, cols: int, min_dist: int, locked: list[SeatAssign]) -> list[Violation]:
    """Validate the locked set alone: in bounds, no overlap, pairwise legal."""
    viols: list[Violation] = []
    seen: dict[tuple[int, int], SeatAssign] = {}
    for a in locked:
        if not (0 <= a.row < rows and 0 <= a.col < cols):
            viols.append(Violation("locked_out_of_bounds", a.candidate_id, a.candidate_id,
                                   f"锁定位 ({a.row},{a.col}) 超出考场 {rows}x{cols}"))
            continue
        pos = (a.row, a.col)
        if pos in seen:
            viols.append(Violation("locked_overlap", seen[pos].candidate_id, a.candidate_id,
                                   f"锁定位 ({a.row},{a.col}) 被重复锁定"))
        else:
            seen[pos] = a
    viols.extend(find_violations(rows, cols, min_dist, locked))
    return viols

def place_candidates(rows: int, cols: int, min_dist: int, candidates: list[dict],
                     locked: list[SeatAssign] | None = None) -> tuple[list[SeatAssign], list[dict]]:
    """Greedy: locked seats first (fixed), then row-major; accept if
    manhattan >= min_dist to all placed AND no same paper 4-neigh."""
    occupied: dict[tuple[int, int], SeatAssign] = {}
    for a in locked or []:
        occupied[(a.row, a.col)] = a
    locked_ids = {a.candidate_id for a in locked or []}
    unplaced: list[dict] = []
    for cand in candidates:
        if cand["id"] in locked_ids:
            continue
        placed = False
        for r in range(rows):
            for c in range(cols):
                if (r, c) in occupied:
                    continue
                ok = True
                for pos, other in occupied.items():
                    if manhattan((r, c), pos) < min_dist:
                        ok = False
                        break
                    if other.paper_id == cand["paper_id"] and (r, c) in neighbors4(pos[0], pos[1], rows, cols):
                        ok = False
                        break
                if not ok:
                    continue
                # also check 4-neigh same paper against current neighbors
                for nr, nc in neighbors4(r, c, rows, cols):
                    if (nr, nc) in occupied and occupied[(nr, nc)].paper_id == cand["paper_id"]:
                        ok = False
                        break
                if not ok:
                    continue
                assign = SeatAssign(cand["id"], cand["name"], cand["ticket_no"], cand["paper_id"], r, c)
                occupied[(r, c)] = assign
                placed = True
                break
            if placed:
                break
        if not placed:
            unplaced.append(cand)
    return list(occupied.values()), unplaced

def find_violations(rows: int, cols: int, min_dist: int, assigns: list[SeatAssign]) -> list[Violation]:
    viols: list[Violation] = []
    for i, a in enumerate(assigns):
        for b in assigns[i + 1:]:
            d = manhattan((a.row, a.col), (b.row, b.col))
            if d < min_dist:
                viols.append(Violation("distance", a.candidate_id, b.candidate_id,
                                       f"曼哈顿距离 {d} < 最小要求 {min_dist}"))
            if a.paper_id == b.paper_id and (b.row, b.col) in neighbors4(a.row, a.col, rows, cols):
                viols.append(Violation("same_paper_adjacent", a.candidate_id, b.candidate_id,
                                       f"同试卷套 {a.paper_id} 四邻相邻"))
    return viols

def plan_to_dict(assigns: list[SeatAssign], unplaced: list[dict], viols: list[Violation], rows: int, cols: int) -> dict:
    return {
        "rows": rows,
        "cols": cols,
        "assignments": [asdict(a) for a in assigns],
        "unplaced": unplaced,
        "violations": [asdict(v) for v in viols],
        "stats": {
            "seated": len(assigns),
            "unplaced": len(unplaced),
            "violations": len(viols),
            "capacity": rows * cols,
            "locked": sum(1 for a in assigns if a.locked),
        },
    }
