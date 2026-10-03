"""departments.py — CRUD endpoints for /departments"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Department
from app.routers.auth import get_admin_user, get_current_user
from app.schemas.schemas import DepartmentCreate, DepartmentResponse, DepartmentUpdate

router = APIRouter(prefix="/departments", tags=["departments"])


@router.get("/", response_model=list[DepartmentResponse])
def list_departments(
    limit:  int     = Query(100, ge=1, le=1000),
    offset: int     = Query(0, ge=0),
    db:     Session = Depends(get_db),
    _:      dict    = Depends(get_current_user),
):
    return db.query(Department).offset(offset).limit(limit).all()


@router.get("/count")
def count_departments(
    db: Session = Depends(get_db),
    _:  dict    = Depends(get_current_user),
):
    return {"count": db.query(Department).count()}


@router.get("/{department_id}", response_model=DepartmentResponse)
def get_department(
    department_id: int,
    db: Session = Depends(get_db),
    _:  dict    = Depends(get_current_user),
):
    dept = db.query(Department).filter(Department.department_id == department_id).first()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    return dept


@router.post("/", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreate,
    db:      Session = Depends(get_db),
    _:       dict    = Depends(get_admin_user),
):
    dept = Department(**payload.model_dump())
    db.add(dept)
    db.commit()
    db.refresh(dept)
    return dept


@router.put("/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: int,
    payload:       DepartmentUpdate,
    db:            Session = Depends(get_db),
    _:             dict    = Depends(get_admin_user),
):
    dept = db.query(Department).filter(Department.department_id == department_id).first()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(dept, field, value)
    db.commit()
    db.refresh(dept)
    return dept


@router.delete("/{department_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_department(
    department_id: int,
    db: Session = Depends(get_db),
    _:  dict    = Depends(get_admin_user),
):
    dept = db.query(Department).filter(Department.department_id == department_id).first()
    if not dept:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Department not found")
    db.delete(dept)
    db.commit()
