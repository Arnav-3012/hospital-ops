"""
schemas.py — Pydantic v2 schemas for request validation and response serialisation.

Pattern per resource:
  <Resource>Base    — shared field definitions
  <Resource>Create  — POST body (no auto-generated IDs / timestamps)
  <Resource>Update  — PUT body (all fields Optional for partial updates)
  <Resource>Response — GET response (all fields, ORM-mode enabled)
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict


# ===========================================================================
# 1. Department
# ===========================================================================

class DepartmentBase(BaseModel):
    name:         str
    head_doctor:  Optional[str] = None
    floor_number: Optional[int] = None


class DepartmentCreate(DepartmentBase):
    pass


class DepartmentUpdate(BaseModel):
    name:         Optional[str] = None
    head_doctor:  Optional[str] = None
    floor_number: Optional[int] = None


class DepartmentResponse(DepartmentBase):
    department_id: int

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# 2. Doctor
# ===========================================================================

class DoctorBase(BaseModel):
    name:             str
    department_id:    Optional[int] = None
    specialization:   Optional[str] = None
    contact:          Optional[str] = None
    years_experience: Optional[int] = None


class DoctorCreate(DoctorBase):
    pass


class DoctorUpdate(BaseModel):
    name:             Optional[str] = None
    department_id:    Optional[int] = None
    specialization:   Optional[str] = None
    contact:          Optional[str] = None
    years_experience: Optional[int] = None


class DoctorResponse(DoctorBase):
    doctor_id: int

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# 3. Patient
# ===========================================================================

class PatientBase(BaseModel):
    name:       str
    dob:        Optional[date] = None
    gender:     Optional[str]  = None
    blood_type: Optional[str]  = None
    contact:    Optional[str]  = None
    address:    Optional[str]  = None


class PatientCreate(PatientBase):
    pass


class PatientUpdate(BaseModel):
    name:       Optional[str]  = None
    dob:        Optional[date] = None
    gender:     Optional[str]  = None
    blood_type: Optional[str]  = None
    contact:    Optional[str]  = None
    address:    Optional[str]  = None


class PatientResponse(PatientBase):
    patient_id: int

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# 4. Bed
# ===========================================================================

class BedBase(BaseModel):
    department_id: Optional[int] = None
    ward_type:     Optional[str] = None
    status:        Optional[str] = "available"


class BedCreate(BedBase):
    pass


class BedUpdate(BaseModel):
    department_id: Optional[int] = None
    ward_type:     Optional[str] = None
    status:        Optional[str] = None


class BedResponse(BedBase):
    bed_id: int

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# 5. Appointment
# ===========================================================================

class AppointmentBase(BaseModel):
    patient_id:   int
    doctor_id:    int
    scheduled_at: datetime
    status:       Optional[str] = "scheduled"
    notes:        Optional[str] = None


class AppointmentCreate(AppointmentBase):
    pass


class AppointmentUpdate(BaseModel):
    patient_id:   Optional[int]      = None
    doctor_id:    Optional[int]      = None
    scheduled_at: Optional[datetime] = None
    status:       Optional[str]      = None
    notes:        Optional[str]      = None


class AppointmentResponse(AppointmentBase):
    appointment_id: int

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# 6. Admission
# ===========================================================================

class AdmissionBase(BaseModel):
    patient_id:    int
    doctor_id:     int
    bed_id:        int
    admitted_at:   Optional[datetime] = None
    discharged_at: Optional[datetime] = None
    diagnosis:     Optional[str]      = None


class AdmissionCreate(AdmissionBase):
    pass


class AdmissionUpdate(BaseModel):
    patient_id:    Optional[int]      = None
    doctor_id:     Optional[int]      = None
    bed_id:        Optional[int]      = None
    admitted_at:   Optional[datetime] = None
    discharged_at: Optional[datetime] = None
    diagnosis:     Optional[str]      = None


class AdmissionResponse(AdmissionBase):
    admission_id: int

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# 7. Prescription
# ===========================================================================

class PrescriptionBase(BaseModel):
    admission_id:  int
    doctor_id:     int
    medication:    str
    dosage:        Optional[str] = None
    duration_days: Optional[int] = None
    prescribed_at: Optional[datetime] = None


class PrescriptionCreate(PrescriptionBase):
    pass


class PrescriptionUpdate(BaseModel):
    admission_id:  Optional[int]      = None
    doctor_id:     Optional[int]      = None
    medication:    Optional[str]      = None
    dosage:        Optional[str]      = None
    duration_days: Optional[int]      = None
    prescribed_at: Optional[datetime] = None


class PrescriptionResponse(PrescriptionBase):
    prescription_id: int

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# 8. Billing
# ===========================================================================

class BillingBase(BaseModel):
    patient_id:     int
    admission_id:   int
    total_amount:   Optional[Decimal] = None
    paid_amount:    Optional[Decimal] = Decimal("0")
    payment_status: Optional[str]     = "pending"
    billed_at:      Optional[datetime] = None


class BillingCreate(BillingBase):
    pass


class BillingUpdate(BaseModel):
    patient_id:     Optional[int]      = None
    admission_id:   Optional[int]      = None
    total_amount:   Optional[Decimal]  = None
    paid_amount:    Optional[Decimal]  = None
    payment_status: Optional[str]      = None
    billed_at:      Optional[datetime] = None


class BillingResponse(BillingBase):
    bill_id: int

    model_config = ConfigDict(from_attributes=True)


# ===========================================================================
# 9. Inventory
# ===========================================================================

class InventoryBase(BaseModel):
    department_id: Optional[int]     = None
    item_name:     str
    category:      Optional[str]     = None
    quantity:      Optional[int]     = 0
    reorder_level: Optional[int]     = 10
    unit_cost:     Optional[Decimal] = None


class InventoryCreate(InventoryBase):
    pass


class InventoryUpdate(BaseModel):
    department_id: Optional[int]     = None
    item_name:     Optional[str]     = None
    category:      Optional[str]     = None
    quantity:      Optional[int]     = None
    reorder_level: Optional[int]     = None
    unit_cost:     Optional[Decimal] = None


class InventoryResponse(InventoryBase):
    item_id: int

    model_config = ConfigDict(from_attributes=True)
