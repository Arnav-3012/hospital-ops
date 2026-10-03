"""beds.py — CRUD endpoints for /beds"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Bed
from app.routers.auth import get_admin_user, get_current_user
from app.schemas.schemas import BedCreate, BedResponse, BedUpdate

router = APIRouter(prefix="/beds", tags=["beds"])


@router.get("/", response_model=list[BedResponse])
def list_beds(
    limit:  int     = Query(100, ge=1, le=10000),
    offset: int     = Query(0, ge=0),
    db:     Session = Depends(get_db),
    _:      dict    = Depends(get_current_user),
):
    return db.query(Bed).offset(offset).limit(limit).all()


@router.get("/count")
def count_beds(
    db: Session = Depends(get_db),
    _:  dict    = Depends(get_current_user),
):
    return {"count": db.query(Bed).count()}


@router.get("/{bed_id}", response_model=BedResponse)
def get_bed(
    bed_id: int,
    db: Session = Depends(get_db),
    _:  dict    = Depends(get_current_user),
):
    bed = db.query(Bed).filter(Bed.bed_id == bed_id).first()
    if not bed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bed not found")
    return bed


@router.post("/", response_model=BedResponse, status_code=status.HTTP_201_CREATED)
def create_bed(
    payload: BedCreate,
    db:      Session = Depends(get_db),
    _:       dict    = Depends(get_admin_user),
):
    bed = Bed(**payload.model_dump())
    db.add(bed)
    db.commit()
    db.refresh(bed)
    return bed


@router.put("/{bed_id}", response_model=BedResponse)
def update_bed(
    bed_id:  int,
    payload: BedUpdate,
    db:      Session = Depends(get_db),
    _:       dict    = Depends(get_admin_user),
):
    bed = db.query(Bed).filter(Bed.bed_id == bed_id).first()
    if not bed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bed not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(bed, field, value)
    db.commit()
    db.refresh(bed)
    return bed


@router.delete("/{bed_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_bed(
    bed_id: int,
    db: Session = Depends(get_db),
    _:  dict    = Depends(get_admin_user),
):
    bed = db.query(Bed).filter(Bed.bed_id == bed_id).first()
    if not bed:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bed not found")

    if bed.status == "occupied":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete an occupied bed",
        )

    db.delete(bed)
    db.commit()
