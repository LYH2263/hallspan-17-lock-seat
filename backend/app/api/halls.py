from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.models import Hall
router = APIRouter(prefix="/halls", tags=["halls"])

@router.get("")
def list_halls(db: Session = Depends(get_db)):
    return [{"id": r.id, "code": r.code, "name": r.name, "rows": r.rows, "cols": r.cols, "min_manhattan": r.min_manhattan}
            for r in db.scalars(select(Hall).order_by(Hall.id)).all()]

class HallIn(BaseModel):
    rows: int | None = None
    cols: int | None = None
    min_manhattan: int | None = None

@router.put("/{hall_id}")
def update_hall(hall_id: int, body: HallIn, db: Session = Depends(get_db)):
    hall = db.get(Hall, hall_id)
    if not hall: raise HTTPException(404, "考室不存在")
    if body.rows is not None: hall.rows = body.rows
    if body.cols is not None: hall.cols = body.cols
    if body.min_manhattan is not None: hall.min_manhattan = body.min_manhattan
    db.commit()
    return {"id": hall.id, "code": hall.code, "name": hall.name, "rows": hall.rows,
            "cols": hall.cols, "min_manhattan": hall.min_manhattan}
