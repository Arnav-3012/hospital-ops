"""
patients.py — CRUD endpoints for /patients.

DELETE cascades: prescriptions → billing → appointments → admissions → patient.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from fastapi.encoders import jsonable_encoder

from app.db.database import get_db
from app.models.models import Admission, Appointment, Billing, Patient, Prescription
from app.routers.audit import write_audit_log
from app.routers.auth import get_admin_user, get_current_user
from app.schemas.schemas import PatientCreate, PatientResponse, PatientUpdate

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("/", response_model=list[PatientResponse])
def list_patients(
    limit:  int  = Query(100, ge=1, le=10000),
    offset: int  = Query(0, ge=0),
    db:     Session = Depends(get_db),
    _:      dict    = Depends(get_current_user),
):
    return db.query(Patient).offset(offset).limit(limit).all()


@router.get("/count")
def count_patients(
    db: Session = Depends(get_db),
    _:  dict    = Depends(get_current_user),
):
    return {"count": db.query(Patient).count()}


@router.get("/search", response_model=list[PatientResponse])
def search_patients(
    name:       Optional[str] = Query(default=None),
    gender:     Optional[str] = Query(default=None),
    blood_type: Optional[str] = Query(default=None),
    limit:      int           = Query(default=100, ge=1, le=1000),
    db:         Session       = Depends(get_db),
    _:          dict          = Depends(get_current_user),
):
    query = db.query(Patient)
    if name:
        query = query.filter(Patient.name.ilike(f"%{name}%"))
    if gender:
        query = query.filter(Patient.gender == gender)
    if blood_type:
        query = query.filter(Patient.blood_type == blood_type)
    return query.limit(limit).all()


@router.get("/{patient_id}", response_model=PatientResponse)
def get_patient(
    patient_id: int,
    db: Session = Depends(get_db),
    _:  dict    = Depends(get_current_user),
):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    return patient


@router.post("/", response_model=PatientResponse, status_code=status.HTTP_201_CREATED)
def create_patient(
    payload:      PatientCreate,
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_admin_user),
):
    patient = Patient(**payload.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    write_audit_log(
        db=db, table_name="patients", operation="INSERT",
        record_id=patient.patient_id, old_values=None,
        new_values=jsonable_encoder(patient),
        changed_by=current_user["username"], endpoint="/patients/",
    )
    return patient


@router.put("/{patient_id}", response_model=PatientResponse)
def update_patient(
    patient_id:   int,
    payload:      PatientUpdate,
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_admin_user),
):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    old_record = jsonable_encoder(patient)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)
    db.commit()
    db.refresh(patient)
    write_audit_log(
        db=db, table_name="patients", operation="UPDATE",
        record_id=patient_id, old_values=old_record,
        new_values=jsonable_encoder(patient),
        changed_by=current_user["username"], endpoint=f"/patients/{patient_id}",
    )
    return patient


@router.delete("/{patient_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_patient(
    patient_id:   int,
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_admin_user),
):
    patient = db.query(Patient).filter(Patient.patient_id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Patient not found")
    old_record = jsonable_encoder(patient)

    admission_ids = [
        row.admission_id
        for row in db.query(Admission.admission_id)
        .filter(Admission.patient_id == patient_id)
        .all()
    ]

    if admission_ids:
        db.query(Prescription).filter(Prescription.admission_id.in_(admission_ids)).delete(
            synchronize_session=False
        )

    db.query(Billing).filter(
        (Billing.patient_id == patient_id) | Billing.admission_id.in_(admission_ids or [])
    ).delete(synchronize_session=False)

    db.query(Appointment).filter(Appointment.patient_id == patient_id).delete(
        synchronize_session=False
    )

    db.query(Admission).filter(Admission.patient_id == patient_id).delete(
        synchronize_session=False
    )

    db.delete(patient)
    db.commit()
    write_audit_log(
        db=db, table_name="patients", operation="DELETE",
        record_id=patient_id, old_values=old_record, new_values=None,
        changed_by=current_user["username"], endpoint=f"/patients/{patient_id}",
    )
