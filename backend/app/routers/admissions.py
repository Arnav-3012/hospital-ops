"""
admissions.py — CRUD endpoints for /admissions.

POST  — atomic transaction: insert admission + set bed.status = 'occupied'
DELETE — resets bed.status back to 'available' for that bed
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from fastapi.encoders import jsonable_encoder

from app.db.database import get_db
from app.models.models import Admission, Bed, Doctor, Patient
from app.routers.audit import write_audit_log
from app.routers.auth import get_admin_user, get_current_user
from app.schemas.schemas import AdmissionCreate, AdmissionResponse, AdmissionUpdate

router = APIRouter(prefix="/admissions", tags=["admissions"])


@router.get("/", response_model=list[AdmissionResponse])
def list_admissions(
    limit:  int     = Query(100, ge=1, le=10000),
    offset: int     = Query(0, ge=0),
    db:     Session = Depends(get_db),
    _:      dict    = Depends(get_current_user),
):
    return db.query(Admission).offset(offset).limit(limit).all()


@router.get("/count")
def count_admissions(
    db: Session = Depends(get_db),
    _:  dict    = Depends(get_current_user),
):
    return {"count": db.query(Admission).count()}


@router.get("/search", response_model=list[AdmissionResponse])
def search_admissions(
    patient_id:  Optional[int]  = Query(default=None),
    doctor_id:   Optional[int]  = Query(default=None),
    active_only: Optional[bool] = Query(default=None),
    limit:       int            = Query(default=100, ge=1, le=1000),
    db:          Session        = Depends(get_db),
    _:           dict           = Depends(get_current_user),
):
    query = db.query(Admission)
    if patient_id:
        query = query.filter(Admission.patient_id == patient_id)
    if doctor_id:
        query = query.filter(Admission.doctor_id == doctor_id)
    if active_only:
        query = query.filter(Admission.discharged_at.is_(None))
    return query.limit(limit).all()


@router.get("/{admission_id}", response_model=AdmissionResponse)
def get_admission(
    admission_id: int,
    db: Session = Depends(get_db),
    _:  dict    = Depends(get_current_user),
):
    admission = db.query(Admission).filter(Admission.admission_id == admission_id).first()
    if not admission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admission not found")
    return admission


@router.post("/", response_model=AdmissionResponse, status_code=status.HTTP_201_CREATED)
def create_admission(
    payload:      AdmissionCreate,
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_admin_user),
):
    # Check 1 — bed exists
    bed = db.query(Bed).filter(Bed.bed_id == payload.bed_id).first()
    if not bed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Bed {payload.bed_id} does not exist",
        )

    # Check 2 — bed is available
    if bed.status != "available":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Bed {payload.bed_id} is currently '{bed.status}'. Only available beds can be assigned.",
        )

    # Check 3 — patient exists
    patient = db.query(Patient).filter(Patient.patient_id == payload.patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {payload.patient_id} does not exist",
        )

    # Check 4 — doctor exists
    doctor = db.query(Doctor).filter(Doctor.doctor_id == payload.doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor {payload.doctor_id} does not exist",
        )

    # Check 5 — patient not already admitted
    active = db.query(Admission).filter(
        Admission.patient_id == payload.patient_id,
        Admission.discharged_at == None,  # noqa: E711
    ).first()
    if active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Patient {payload.patient_id} is already admitted (admission_id: {active.admission_id}). Discharge first before re-admitting.",
        )

    # All checks passed — proceed with atomic transaction
    try:
        admission = Admission(**payload.model_dump())
        db.add(admission)
        db.flush()
        bed.status = "occupied"
        db.commit()
        db.refresh(admission)
    except Exception:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Admission transaction failed — rolled back",
        )
    write_audit_log(
        db=db, table_name="admissions", operation="INSERT",
        record_id=admission.admission_id, old_values=None,
        new_values=jsonable_encoder(admission),
        changed_by=current_user["username"], endpoint="/admissions/",
    )
    return admission


@router.put("/{admission_id}", response_model=AdmissionResponse)
def update_admission(
    admission_id: int,
    payload:      AdmissionUpdate,
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_admin_user),
):
    admission = db.query(Admission).filter(Admission.admission_id == admission_id).first()
    if not admission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admission not found")
    old_record = jsonable_encoder(admission)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(admission, field, value)
    db.commit()
    db.refresh(admission)
    write_audit_log(
        db=db, table_name="admissions", operation="UPDATE",
        record_id=admission_id, old_values=old_record,
        new_values=jsonable_encoder(admission),
        changed_by=current_user["username"], endpoint=f"/admissions/{admission_id}",
    )
    return admission


@router.delete("/{admission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_admission(
    admission_id: int,
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_admin_user),
):
    admission = db.query(Admission).filter(Admission.admission_id == admission_id).first()
    if not admission:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admission not found")

    old_record = jsonable_encoder(admission)
    bed = db.query(Bed).filter(Bed.bed_id == admission.bed_id).first()
    if bed:
        bed.status = "available"

    db.delete(admission)
    db.commit()
    write_audit_log(
        db=db, table_name="admissions", operation="DELETE",
        record_id=admission_id, old_values=old_record, new_values=None,
        changed_by=current_user["username"], endpoint=f"/admissions/{admission_id}",
    )
