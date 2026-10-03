"""doctors.py — CRUD endpoints for /doctors"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from fastapi.encoders import jsonable_encoder

from app.db.database import get_db
from app.models.models import Admission, Doctor
from app.routers.audit import write_audit_log
from app.routers.auth import get_admin_user, get_current_user
from app.schemas.schemas import DoctorCreate, DoctorResponse, DoctorUpdate

router = APIRouter(prefix="/doctors", tags=["doctors"])


@router.get("/", response_model=list[DoctorResponse])
def list_doctors(
    limit:  int     = Query(100, ge=1, le=10000),
    offset: int     = Query(0, ge=0),
    db:     Session = Depends(get_db),
    _:      dict    = Depends(get_current_user),
):
    return db.query(Doctor).offset(offset).limit(limit).all()


@router.get("/count")
def count_doctors(
    db: Session = Depends(get_db),
    _:  dict    = Depends(get_current_user),
):
    return {"count": db.query(Doctor).count()}


@router.get("/search", response_model=list[DoctorResponse])
def search_doctors(
    name:           Optional[str] = Query(default=None),
    specialization: Optional[str] = Query(default=None),
    department_id:  Optional[int] = Query(default=None),
    limit:          int           = Query(default=100, ge=1, le=1000),
    db:             Session       = Depends(get_db),
    _:              dict          = Depends(get_current_user),
):
    query = db.query(Doctor)
    if name:
        query = query.filter(Doctor.name.ilike(f"%{name}%"))
    if specialization:
        query = query.filter(Doctor.specialization.ilike(f"%{specialization}%"))
    if department_id:
        query = query.filter(Doctor.department_id == department_id)
    return query.limit(limit).all()


@router.get("/{doctor_id}", response_model=DoctorResponse)
def get_doctor(
    doctor_id: int,
    db: Session = Depends(get_db),
    _:  dict    = Depends(get_current_user),
):
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    return doctor


@router.post("/", response_model=DoctorResponse, status_code=status.HTTP_201_CREATED)
def create_doctor(
    payload:      DoctorCreate,
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_admin_user),
):
    doctor = Doctor(**payload.model_dump())
    db.add(doctor)
    db.commit()
    db.refresh(doctor)
    write_audit_log(
        db=db, table_name="doctors", operation="INSERT",
        record_id=doctor.doctor_id, old_values=None,
        new_values=jsonable_encoder(doctor),
        changed_by=current_user["username"], endpoint="/doctors/",
    )
    return doctor


@router.put("/{doctor_id}", response_model=DoctorResponse)
def update_doctor(
    doctor_id:    int,
    payload:      DoctorUpdate,
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_admin_user),
):
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")
    old_record = jsonable_encoder(doctor)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(doctor, field, value)
    db.commit()
    db.refresh(doctor)
    write_audit_log(
        db=db, table_name="doctors", operation="UPDATE",
        record_id=doctor_id, old_values=old_record,
        new_values=jsonable_encoder(doctor),
        changed_by=current_user["username"], endpoint=f"/doctors/{doctor_id}",
    )
    return doctor


@router.delete("/{doctor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_doctor(
    doctor_id:    int,
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_admin_user),
):
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Doctor not found")

    active = (
        db.query(Admission)
        .filter(Admission.doctor_id == doctor_id, Admission.discharged_at.is_(None))
        .first()
    )
    if active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete doctor with active admissions",
        )

    old_record = jsonable_encoder(doctor)
    db.delete(doctor)
    db.commit()
    write_audit_log(
        db=db, table_name="doctors", operation="DELETE",
        record_id=doctor_id, old_values=old_record, new_values=None,
        changed_by=current_user["username"], endpoint=f"/doctors/{doctor_id}",
    )
