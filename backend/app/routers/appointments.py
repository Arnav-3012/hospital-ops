"""appointments.py — CRUD endpoints for /appointments"""

from datetime import timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Appointment, Doctor, Patient
from app.routers.auth import get_admin_user, get_current_user
from app.schemas.schemas import AppointmentCreate, AppointmentResponse, AppointmentUpdate

router = APIRouter(prefix="/appointments", tags=["appointments"])


@router.get("/", response_model=list[AppointmentResponse])
def list_appointments(
    limit:  int     = Query(100, ge=1, le=1000),
    offset: int     = Query(0, ge=0),
    db:     Session = Depends(get_db),
    _:      dict    = Depends(get_current_user),
):
    return db.query(Appointment).offset(offset).limit(limit).all()


@router.get("/count")
def count_appointments(
    db: Session = Depends(get_db),
    _:  dict    = Depends(get_current_user),
):
    return {"count": db.query(Appointment).count()}


@router.get("/search", response_model=list[AppointmentResponse])
def search_appointments(
    patient_id: Optional[int] = Query(default=None),
    doctor_id:  Optional[int] = Query(default=None),
    status:     Optional[str] = Query(default=None),
    date_from:  Optional[str] = Query(default=None),
    date_to:    Optional[str] = Query(default=None),
    limit:      int           = Query(default=100, ge=1, le=1000),
    db:         Session       = Depends(get_db),
    _:          dict          = Depends(get_current_user),
):
    query = db.query(Appointment)
    if patient_id:
        query = query.filter(Appointment.patient_id == patient_id)
    if doctor_id:
        query = query.filter(Appointment.doctor_id == doctor_id)
    if status:
        query = query.filter(Appointment.status == status)
    if date_from:
        query = query.filter(Appointment.scheduled_at >= date_from)
    if date_to:
        query = query.filter(Appointment.scheduled_at <= date_to)
    return query.limit(limit).all()


@router.get("/{appointment_id}", response_model=AppointmentResponse)
def get_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    _:  dict    = Depends(get_current_user),
):
    appt = db.query(Appointment).filter(Appointment.appointment_id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    return appt


@router.post("/", response_model=AppointmentResponse, status_code=status.HTTP_201_CREATED)
def create_appointment(
    payload: AppointmentCreate,
    db:      Session = Depends(get_db),
    _:       dict    = Depends(get_admin_user),
):
    # Check 1 — patient exists
    patient = db.query(Patient).filter(Patient.patient_id == payload.patient_id).first()
    if not patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Patient {payload.patient_id} does not exist",
        )

    # Check 2 — doctor exists
    doctor = db.query(Doctor).filter(Doctor.doctor_id == payload.doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Doctor {payload.doctor_id} does not exist",
        )

    # Check 3 — doctor time conflict (30 minute window)
    scheduled     = payload.scheduled_at
    window_start  = scheduled - timedelta(minutes=30)
    window_end    = scheduled + timedelta(minutes=30)

    doctor_conflict = db.query(Appointment).filter(
        Appointment.doctor_id    == payload.doctor_id,
        Appointment.scheduled_at >= window_start,
        Appointment.scheduled_at <= window_end,
        Appointment.status       != "cancelled",
    ).first()
    if doctor_conflict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Doctor {payload.doctor_id} already has an appointment at {doctor_conflict.scheduled_at}. Please choose a different time slot (minimum 30 minutes gap required).",
        )

    # Check 4 — patient time conflict
    patient_conflict = db.query(Appointment).filter(
        Appointment.patient_id   == payload.patient_id,
        Appointment.scheduled_at >= window_start,
        Appointment.scheduled_at <= window_end,
        Appointment.status       != "cancelled",
    ).first()
    if patient_conflict:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Patient {payload.patient_id} already has an appointment at {patient_conflict.scheduled_at}. Cannot book two appointments within 30 minutes.",
        )

    # All checks passed — create appointment
    appt = Appointment(**payload.model_dump())
    db.add(appt)
    db.commit()
    db.refresh(appt)
    return appt


@router.put("/{appointment_id}", response_model=AppointmentResponse)
def update_appointment(
    appointment_id: int,
    payload:        AppointmentUpdate,
    db:             Session = Depends(get_db),
    _:              dict    = Depends(get_admin_user),
):
    appt = db.query(Appointment).filter(Appointment.appointment_id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(appt, field, value)
    db.commit()
    db.refresh(appt)
    return appt


@router.delete("/{appointment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_appointment(
    appointment_id: int,
    db: Session = Depends(get_db),
    _:  dict    = Depends(get_admin_user),
):
    appt = db.query(Appointment).filter(Appointment.appointment_id == appointment_id).first()
    if not appt:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found")
    db.delete(appt)
    db.commit()
