"""
analytics.py — Read-only analytics endpoints.

Endpoints:
  GET /analytics/bed-occupancy    — bed counts by department and status
  GET /analytics/revenue-trend    — monthly billing totals
  GET /analytics/doctor-load      — appointments + admissions per doctor
  GET /analytics/inventory-alerts — items below reorder level

All endpoints require JWT auth.
"""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.routers.auth import get_current_user

router = APIRouter(tags=["analytics"])


# ---------------------------------------------------------------------------
# GET /analytics/bed-occupancy
# ---------------------------------------------------------------------------
@router.get("/bed-occupancy")
def bed_occupancy(
    db: Session = Depends(get_db),
    _:  str     = Depends(get_current_user),
):
    sql = text("""
        SELECT d.name AS department, b.status, COUNT(*) AS count
        FROM beds b
        JOIN departments d ON b.department_id = d.department_id
        GROUP BY d.name, b.status
        ORDER BY d.name
    """)
    rows = db.execute(sql).fetchall()
    return [
        {"department": r.department, "status": r.status, "count": int(r.count)}
        for r in rows
    ]


# ---------------------------------------------------------------------------
# GET /analytics/revenue-trend
# ---------------------------------------------------------------------------
@router.get("/revenue-trend")
def revenue_trend(
    db: Session = Depends(get_db),
    _:  str     = Depends(get_current_user),
):
    sql = text("""
        SELECT
            TO_CHAR(billed_at, 'YYYY-MM') AS month,
            SUM(total_amount)             AS total_billed,
            SUM(paid_amount)              AS total_paid,
            SUM(total_amount - paid_amount) AS outstanding
        FROM billing
        GROUP BY TO_CHAR(billed_at, 'YYYY-MM')
        ORDER BY month
    """)
    rows = db.execute(sql).fetchall()
    return [
        {
            "month":        r.month,
            "total_billed": float(r.total_billed or 0),
            "total_paid":   float(r.total_paid   or 0),
            "outstanding":  float(r.outstanding  or 0),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# GET /analytics/doctor-load
# ---------------------------------------------------------------------------
@router.get("/doctor-load")
def doctor_load(
    db: Session = Depends(get_db),
    _:  str     = Depends(get_current_user),
):
    sql = text("""
        SELECT
            d.name                              AS doctor_name,
            d.specialization,
            dept.name                           AS department,
            COUNT(DISTINCT a.appointment_id)    AS total_appointments,
            COUNT(DISTINCT adm.admission_id)    AS total_admissions
        FROM doctors d
        LEFT JOIN departments dept ON d.department_id = dept.department_id
        LEFT JOIN appointments  a  ON d.doctor_id = a.doctor_id
        LEFT JOIN admissions    adm ON d.doctor_id = adm.doctor_id
        GROUP BY d.doctor_id, d.name, d.specialization, dept.name
        ORDER BY total_appointments DESC
    """)
    rows = db.execute(sql).fetchall()
    return [
        {
            "doctor_name":        r.doctor_name,
            "specialization":     r.specialization,
            "department":         r.department,
            "total_appointments": int(r.total_appointments),
            "total_admissions":   int(r.total_admissions),
        }
        for r in rows
    ]


# ---------------------------------------------------------------------------
# GET /analytics/inventory-alerts
# ---------------------------------------------------------------------------
@router.get("/inventory-alerts")
def inventory_alerts(
    db: Session = Depends(get_db),
    _:  str     = Depends(get_current_user),
):
    sql = text("""
        SELECT
            i.item_name,
            i.category,
            d.name                          AS department,
            i.quantity,
            i.reorder_level,
            i.unit_cost,
            (i.reorder_level - i.quantity)  AS shortage
        FROM inventory i
        JOIN departments d ON i.department_id = d.department_id
        WHERE i.quantity < i.reorder_level
        ORDER BY shortage DESC
    """)
    rows = db.execute(sql).fetchall()
    return [
        {
            "item_name":     r.item_name,
            "category":      r.category,
            "department":    r.department,
            "quantity":      int(r.quantity),
            "reorder_level": int(r.reorder_level),
            "unit_cost":     float(r.unit_cost or 0),
            "shortage":      int(r.shortage),
        }
        for r in rows
    ]
