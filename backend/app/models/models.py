"""
models.py — SQLAlchemy ORM models for all 9 hospital_db tables.
"""

from datetime import datetime

from sqlalchemy import (
    JSON,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)

from app.db.database import Base


# ---------------------------------------------------------------------------
# 1. Department
# ---------------------------------------------------------------------------
class Department(Base):
    __tablename__ = "departments"

    department_id = Column(Integer, primary_key=True, index=True)
    name          = Column(String(100), nullable=False)
    head_doctor   = Column(String(100))
    floor_number  = Column(Integer)


# ---------------------------------------------------------------------------
# 2. Doctor
# ---------------------------------------------------------------------------
class Doctor(Base):
    __tablename__ = "doctors"

    doctor_id        = Column(Integer, primary_key=True, index=True)
    name             = Column(String(100), nullable=False)
    department_id    = Column(Integer, ForeignKey("departments.department_id"))
    specialization   = Column(String(100))
    contact          = Column(String(20))
    years_experience = Column(Integer)


# ---------------------------------------------------------------------------
# 3. Patient
# ---------------------------------------------------------------------------
class Patient(Base):
    __tablename__ = "patients"

    patient_id = Column(Integer, primary_key=True, index=True)
    name       = Column(String(100), nullable=False)
    dob        = Column(Date)
    gender     = Column(String(10))
    blood_type = Column(String(5))
    contact    = Column(String(20))
    address    = Column(Text)


# ---------------------------------------------------------------------------
# 4. Bed
# ---------------------------------------------------------------------------
class Bed(Base):
    __tablename__ = "beds"

    bed_id        = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.department_id"))
    ward_type     = Column(String(50))
    status        = Column(String(20), default="available")


# ---------------------------------------------------------------------------
# 5. Appointment
# ---------------------------------------------------------------------------
class Appointment(Base):
    __tablename__ = "appointments"

    appointment_id = Column(Integer, primary_key=True, index=True)
    patient_id     = Column(Integer, ForeignKey("patients.patient_id"))
    doctor_id      = Column(Integer, ForeignKey("doctors.doctor_id"))
    scheduled_at   = Column(DateTime, nullable=False)
    status         = Column(String(20), default="scheduled")
    notes          = Column(Text)


# ---------------------------------------------------------------------------
# 6. Admission
# ---------------------------------------------------------------------------
class Admission(Base):
    __tablename__ = "admissions"

    admission_id  = Column(Integer, primary_key=True, index=True)
    patient_id    = Column(Integer, ForeignKey("patients.patient_id"))
    doctor_id     = Column(Integer, ForeignKey("doctors.doctor_id"))
    bed_id        = Column(Integer, ForeignKey("beds.bed_id"))
    admitted_at   = Column(DateTime, default=datetime.now)
    discharged_at = Column(DateTime)
    diagnosis     = Column(Text)


# ---------------------------------------------------------------------------
# 7. Prescription
# ---------------------------------------------------------------------------
class Prescription(Base):
    __tablename__ = "prescriptions"

    prescription_id = Column(Integer, primary_key=True, index=True)
    admission_id    = Column(Integer, ForeignKey("admissions.admission_id"))
    doctor_id       = Column(Integer, ForeignKey("doctors.doctor_id"))
    medication      = Column(String(200), nullable=False)
    dosage          = Column(String(100))
    duration_days   = Column(Integer)
    prescribed_at   = Column(DateTime, default=datetime.now)


# ---------------------------------------------------------------------------
# 8. Billing
# ---------------------------------------------------------------------------
class Billing(Base):
    __tablename__ = "billing"

    bill_id        = Column(Integer, primary_key=True, index=True)
    patient_id     = Column(Integer, ForeignKey("patients.patient_id"))
    admission_id   = Column(Integer, ForeignKey("admissions.admission_id"))
    total_amount   = Column(Numeric(10, 2))
    paid_amount    = Column(Numeric(10, 2), default=0)
    payment_status = Column(String(20), default="pending")
    billed_at      = Column(DateTime, default=datetime.now)


# ---------------------------------------------------------------------------
# 9. Inventory
# ---------------------------------------------------------------------------
class Inventory(Base):
    __tablename__ = "inventory"

    item_id       = Column(Integer, primary_key=True, index=True)
    department_id = Column(Integer, ForeignKey("departments.department_id"))
    item_name     = Column(String(200), nullable=False)
    category      = Column(String(100))
    quantity      = Column(Integer, default=0)
    reorder_level = Column(Integer, default=10)
    unit_cost     = Column(Numeric(10, 2))


# ---------------------------------------------------------------------------
# 10. AuditLog
# ---------------------------------------------------------------------------
class AuditLog(Base):
    __tablename__ = "audit_log"

    log_id     = Column(Integer, primary_key=True, index=True)
    table_name = Column(String(100), nullable=False)
    operation  = Column(String(20),  nullable=False)
    record_id  = Column(Integer,     nullable=True)
    old_values = Column(JSON,        nullable=True)
    new_values = Column(JSON,        nullable=True)
    changed_by = Column(String(100), nullable=True)
    changed_at = Column(DateTime,    default=datetime.utcnow)
    endpoint   = Column(String(200), nullable=True)
    ip_address = Column(String(50),  nullable=True)
