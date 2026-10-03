"""prescriptions.py — CRUD endpoints for /prescriptions"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Prescription
from app.routers.auth import get_admin_user, get_current_user
from app.schemas.schemas import PrescriptionCreate, PrescriptionResponse, PrescriptionUpdate

router = APIRouter(prefix="/prescriptions", tags=["prescriptions"])


@router.get("/", response_model=list[PrescriptionResponse])
def list_prescriptions(
    limit:  int     = Query(100, ge=1, le=1000),
    offset: int     = Query(0, ge=0),
    db:     Session = Depends(get_db),
    _:      dict    = Depends(get_current_user),
):
    return db.query(Prescription).offset(offset).limit(limit).all()


@router.get("/count")
def count_prescriptions(
    db: Session = Depends(get_db),
    _:  dict    = Depends(get_current_user),
):
    return {"count": db.query(Prescription).count()}


@router.get("/{prescription_id}", response_model=PrescriptionResponse)
def get_prescription(
    prescription_id: int,
    db: Session = Depends(get_db),
    _:  dict    = Depends(get_current_user),
):
    rx = db.query(Prescription).filter(Prescription.prescription_id == prescription_id).first()
    if not rx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")
    return rx


@router.post("/", response_model=PrescriptionResponse, status_code=status.HTTP_201_CREATED)
def create_prescription(
    payload: PrescriptionCreate,
    db:      Session = Depends(get_db),
    _:       dict    = Depends(get_admin_user),
):
    rx = Prescription(**payload.model_dump())
    db.add(rx)
    db.commit()
    db.refresh(rx)
    return rx


@router.put("/{prescription_id}", response_model=PrescriptionResponse)
def update_prescription(
    prescription_id: int,
    payload:         PrescriptionUpdate,
    db:              Session = Depends(get_db),
    _:               dict    = Depends(get_admin_user),
):
    rx = db.query(Prescription).filter(Prescription.prescription_id == prescription_id).first()
    if not rx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(rx, field, value)
    db.commit()
    db.refresh(rx)
    return rx


@router.delete("/{prescription_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prescription(
    prescription_id: int,
    db: Session = Depends(get_db),
    _:  dict    = Depends(get_admin_user),
):
    rx = db.query(Prescription).filter(Prescription.prescription_id == prescription_id).first()
    if not rx:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prescription not found")
    db.delete(rx)
    db.commit()
