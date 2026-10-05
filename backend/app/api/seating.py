import json
from dataclasses import asdict
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Candidate, Hall, SeatPlan
from app.services.seat_engine import (check_locked, find_violations, locked_from_plan,
                                      place_candidates, plan_to_dict)
router = APIRouter(prefix="/seating", tags=["seating"])

def _latest_plan(db: Session, hall_id: int) -> SeatPlan | None:
    return db.scalars(select(SeatPlan).where(SeatPlan.hall_id == hall_id)
                      .order_by(SeatPlan.id.desc())).first()

def _candidates(db: Session, hall_id: int) -> list[dict]:
    return [{"id": c.id, "name": c.name, "ticket_no": c.ticket_no, "paper_id": c.paper_id}
            for c in db.scalars(select(Candidate).where(Candidate.hall_id == hall_id)).all()]

@router.post("/run")
def run_seating(hall_id: int = 1, db: Session = Depends(get_db)):
    hall = db.get(Hall, hall_id)
    if not hall: raise HTTPException(404, "考室不存在")
    cands = _candidates(db, hall_id)
    # 保锁：沿用最新方案上的锁标记；历史方案只读，绝不被本次新排回刷
    locked = []
    prev = _latest_plan(db, hall_id)
    if prev:
        locked = locked_from_plan(json.loads(prev.result_json).get("assignments", []), cands)
    lock_viols = check_locked(hall.rows, hall.cols, hall.min_manhattan, locked)
    if lock_viols:
        # 锁位在新约束下已不合法：整场失败且不增方案，禁止拆锁硬排
        raise HTTPException(409, detail={
            "msg": "锁定位在当前约束下不合法，未生成新方案",
            "violations": [asdict(v) for v in lock_viols],
        })
    assigns, unplaced = place_candidates(hall.rows, hall.cols, hall.min_manhattan, cands, locked=locked)
    viols = find_violations(hall.rows, hall.cols, hall.min_manhattan, assigns)
    result = plan_to_dict(assigns, unplaced, viols, hall.rows, hall.cols)
    result["hall"] = {"id": hall.id, "name": hall.name, "min_manhattan": hall.min_manhattan}
    plan = SeatPlan(hall_id=hall_id, created_at=datetime.utcnow(), result_json=json.dumps(result, ensure_ascii=False))
    db.add(plan); db.commit(); db.refresh(plan)
    return {"id": plan.id, **result}

class LockIn(BaseModel):
    hall_id: int = 1
    candidate_id: int
    locked: bool = True

@router.post("/lock")
def set_lock(body: LockIn, db: Session = Depends(get_db)):
    """在当前（最新）方案上锁定/解锁一名已座考生；只改最新方案，历史方案不动。"""
    plan = _latest_plan(db, body.hall_id)
    if not plan: raise HTTPException(404, "当前无方案，请先排座")
    data = json.loads(plan.result_json)
    hit = False
    for a in data.get("assignments", []):
        if a.get("candidate_id") == body.candidate_id:
            a["locked"] = body.locked
            hit = True
    if not hit: raise HTTPException(404, "考生未在当前方案中落座")
    data.setdefault("stats", {})["locked"] = sum(1 for a in data["assignments"] if a.get("locked"))
    plan.result_json = json.dumps(data, ensure_ascii=False)
    db.commit()
    return {"id": plan.id, **data}

@router.get("/plans")
def list_plans(hall_id: int = 1, db: Session = Depends(get_db)):
    out = []
    for p in db.scalars(select(SeatPlan).where(SeatPlan.hall_id == hall_id).order_by(SeatPlan.id)).all():
        data = json.loads(p.result_json)
        out.append({"id": p.id, "hall_id": p.hall_id,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                    "stats": data.get("stats", {})})
    return out

@router.get("/plans/{plan_id}")
def get_plan(plan_id: int, db: Session = Depends(get_db)):
    plan = db.get(SeatPlan, plan_id)
    if not plan: raise HTTPException(404, "方案不存在")
    return {"id": plan.id, **json.loads(plan.result_json)}

@router.get("/latest")
def latest(hall_id: int = 1, db: Session = Depends(get_db)):
    plan = _latest_plan(db, hall_id)
    if not plan:
        return run_seating(hall_id=hall_id, db=db)
    data = json.loads(plan.result_json)
    return {"id": plan.id, **data}

@router.get("/violations")
def violations(hall_id: int = 1, db: Session = Depends(get_db)):
    data = latest(hall_id=hall_id, db=db)
    return {"hall_id": hall_id, "violations": data.get("violations", []), "unplaced": data.get("unplaced", [])}

@router.get("/stats")
def stats(hall_id: int = 1, db: Session = Depends(get_db)):
    data = latest(hall_id=hall_id, db=db)
    return {"hall_id": hall_id, **data.get("stats", {})}
