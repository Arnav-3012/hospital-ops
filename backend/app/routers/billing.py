"""billing.py — CRUD endpoints for /billing"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from fastapi.encoders import jsonable_encoder

from app.db.database import get_db
from app.models.models import Billing
from app.routers.audit import write_audit_log
from app.routers.auth import get_admin_user, get_current_user
from app.schemas.schemas import BillingCreate, BillingResponse, BillingUpdate

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/", response_model=list[BillingResponse])
def list_billing(
    limit:  int     = Query(100, ge=1, le=1000),
    offset: int     = Query(0, ge=0),
    db:     Session = Depends(get_db),
    _:      dict    = Depends(get_current_user),
):
    return db.query(Billing).offset(offset).limit(limit).all()


@router.get("/count")
def count_billing(
    db: Session = Depends(get_db),
    _:  dict    = Depends(get_current_user),
):
    return {"count": db.query(Billing).count()}


@router.get("/search", response_model=list[BillingResponse])
def search_billing(
    patient_id:     Optional[int]   = Query(default=None),
    payment_status: Optional[str]   = Query(default=None),
    min_amount:     Optional[float] = Query(default=None),
    max_amount:     Optional[float] = Query(default=None),
    limit:          int             = Query(default=100, ge=1, le=1000),
    db:             Session         = Depends(get_db),
    _:              dict            = Depends(get_current_user),
):
    query = db.query(Billing)
    if patient_id:
        query = query.filter(Billing.patient_id == patient_id)
    if payment_status:
        query = query.filter(Billing.payment_status == payment_status)
    if min_amount:
        query = query.filter(Billing.total_amount >= min_amount)
    if max_amount:
        query = query.filter(Billing.total_amount <= max_amount)
    return query.limit(limit).all()


@router.get("/{bill_id}", response_model=BillingResponse)
def get_bill(
    bill_id: int,
    db: Session = Depends(get_db),
    _:  dict    = Depends(get_current_user),
):
    bill = db.query(Billing).filter(Billing.bill_id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    return bill


@router.post("/", response_model=BillingResponse, status_code=status.HTTP_201_CREATED)
def create_billing(
    payload:      BillingCreate,
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_admin_user),
):
    bill = Billing(**payload.model_dump())
    db.add(bill)
    db.commit()
    db.refresh(bill)
    write_audit_log(
        db=db, table_name="billing", operation="INSERT",
        record_id=bill.bill_id, old_values=None,
        new_values=jsonable_encoder(bill),
        changed_by=current_user["username"], endpoint="/billing/",
    )
    return bill


@router.put("/{bill_id}", response_model=BillingResponse)
def update_billing(
    bill_id:      int,
    payload:      BillingUpdate,
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_admin_user),
):
    bill = db.query(Billing).filter(Billing.bill_id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    old_record = jsonable_encoder(bill)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(bill, field, value)
    db.commit()
    db.refresh(bill)
    write_audit_log(
        db=db, table_name="billing", operation="UPDATE",
        record_id=bill_id, old_values=old_record,
        new_values=jsonable_encoder(bill),
        changed_by=current_user["username"], endpoint=f"/billing/{bill_id}",
    )
    return bill


@router.delete("/{bill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_billing(
    bill_id:      int,
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_admin_user),
):
    bill = db.query(Billing).filter(Billing.bill_id == bill_id).first()
    if not bill:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Bill not found")
    old_record = jsonable_encoder(bill)
    db.delete(bill)
    db.commit()
    write_audit_log(
        db=db, table_name="billing", operation="DELETE",
        record_id=bill_id, old_values=old_record, new_values=None,
        changed_by=current_user["username"], endpoint=f"/billing/{bill_id}",
    )
