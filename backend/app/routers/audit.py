"""audit.py — Audit log endpoints and write helper."""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from fastapi.encoders import jsonable_encoder  # noqa: F401 (re-exported for callers)
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import AuditLog
from app.routers.auth import get_admin_user

router = APIRouter()


# ---------------------------------------------------------------------------
# Helper — called by other routers to record a change
# ---------------------------------------------------------------------------
def write_audit_log(
    db:         Session,
    table_name: str,
    operation:  str,
    record_id:  Optional[int],
    old_values: Optional[dict],
    new_values: Optional[dict],
    changed_by: str,
    endpoint:   Optional[str] = None,
) -> None:
    try:
        log = AuditLog(
            table_name=table_name,
            operation=operation,
            record_id=record_id,
            old_values=old_values,
            new_values=new_values,
            changed_by=changed_by,
            endpoint=endpoint,
        )
        db.add(log)
        db.commit()
    except Exception as e:
        db.rollback()
        print(f"Audit log error: {e}")


# ---------------------------------------------------------------------------
# GET /audit-log/
# ---------------------------------------------------------------------------
@router.get("/")
def get_audit_log(
    table_name:  Optional[str] = None,
    operation:   Optional[str] = None,
    changed_by:  Optional[str] = None,
    limit:       int           = Query(default=100, ge=1, le=1000),
    offset:      int           = Query(default=0, ge=0),
    db:          Session       = Depends(get_db),
    current_user: dict         = Depends(get_admin_user),
):
    query = db.query(AuditLog)
    if table_name:
        query = query.filter(AuditLog.table_name == table_name)
    if operation:
        query = query.filter(AuditLog.operation == operation)
    if changed_by:
        query = query.filter(AuditLog.changed_by == changed_by)
    return query.order_by(AuditLog.changed_at.desc()).offset(offset).limit(limit).all()


# ---------------------------------------------------------------------------
# GET /audit-log/summary
# ---------------------------------------------------------------------------
@router.get("/summary")
def get_audit_summary(
    db:           Session = Depends(get_db),
    current_user: dict    = Depends(get_admin_user),
):
    summary = (
        db.query(
            AuditLog.table_name,
            AuditLog.operation,
            func.count(AuditLog.log_id).label("count"),
        )
        .group_by(AuditLog.table_name, AuditLog.operation)
        .all()
    )
    return [{"table": s[0], "operation": s[1], "count": s[2]} for s in summary]
