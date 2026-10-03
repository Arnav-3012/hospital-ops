"""inventory.py — CRUD endpoints for /inventory"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.models import Inventory
from app.routers.auth import get_admin_user, get_current_user
from app.schemas.schemas import InventoryCreate, InventoryResponse, InventoryUpdate

router = APIRouter(prefix="/inventory", tags=["inventory"])


@router.get("/", response_model=list[InventoryResponse])
def list_inventory(
    limit:  int     = Query(100, ge=1, le=1000),
    offset: int     = Query(0, ge=0),
    db:     Session = Depends(get_db),
    _:      dict    = Depends(get_current_user),
):
    return db.query(Inventory).offset(offset).limit(limit).all()


@router.get("/count")
def count_inventory(
    db: Session = Depends(get_db),
    _:  dict    = Depends(get_current_user),
):
    return {"count": db.query(Inventory).count()}


@router.get("/search", response_model=list[InventoryResponse])
def search_inventory(
    item_name:     Optional[str]  = Query(default=None),
    category:      Optional[str]  = Query(default=None),
    department_id: Optional[int]  = Query(default=None),
    low_stock:     Optional[bool] = Query(default=None),
    limit:         int            = Query(default=100, ge=1, le=1000),
    db:            Session        = Depends(get_db),
    _:             dict           = Depends(get_current_user),
):
    query = db.query(Inventory)
    if item_name:
        query = query.filter(Inventory.item_name.ilike(f"%{item_name}%"))
    if category:
        query = query.filter(Inventory.category == category)
    if department_id:
        query = query.filter(Inventory.department_id == department_id)
    if low_stock:
        query = query.filter(Inventory.quantity < Inventory.reorder_level)
    return query.limit(limit).all()


@router.get("/{item_id}", response_model=InventoryResponse)
def get_inventory_item(
    item_id: int,
    db: Session = Depends(get_db),
    _:  dict    = Depends(get_current_user),
):
    item = db.query(Inventory).filter(Inventory.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")
    return item


@router.post("/", response_model=InventoryResponse, status_code=status.HTTP_201_CREATED)
def create_inventory_item(
    payload: InventoryCreate,
    db:      Session = Depends(get_db),
    _:       dict    = Depends(get_admin_user),
):
    item = Inventory(**payload.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}", response_model=InventoryResponse)
def update_inventory_item(
    item_id: int,
    payload: InventoryUpdate,
    db:      Session = Depends(get_db),
    _:       dict    = Depends(get_admin_user),
):
    item = db.query(Inventory).filter(Inventory.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_inventory_item(
    item_id: int,
    db: Session = Depends(get_db),
    _:  dict    = Depends(get_admin_user),
):
    item = db.query(Inventory).filter(Inventory.item_id == item_id).first()
    if not item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Inventory item not found")
    db.delete(item)
    db.commit()
