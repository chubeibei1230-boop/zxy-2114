from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from models import ShelfZone, ShelfSlot, Store
from schemas import ShelfZoneCreate, ShelfZoneUpdate, ShelfZoneOut, ShelfSlotCreate, ShelfSlotUpdate, ShelfSlotOut
from routers.auth import require_admin, require_executor

router = APIRouter(prefix="/api/shelves", tags=["货架分区管理"])


@router.post("/zones/", response_model=ShelfZoneOut)
def create_zone(data: ShelfZoneCreate, operator_id: int = Query(...), db: Session = Depends(get_db)):
    require_admin(db, operator_id)
    store = db.query(Store).filter(Store.id == data.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")
    existing = db.query(ShelfZone).filter(
        ShelfZone.code == data.code, ShelfZone.store_id == data.store_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该门店下分区编码已存在")
    zone = ShelfZone(**data.model_dump())
    db.add(zone)
    db.commit()
    db.refresh(zone)
    return zone


@router.get("/zones/", response_model=List[ShelfZoneOut])
def list_zones(
    store_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(ShelfZone)
    if store_id is not None:
        query = query.filter(ShelfZone.store_id == store_id)
    if is_active is not None:
        query = query.filter(ShelfZone.is_active == is_active)
    return query.order_by(ShelfZone.sort_order).all()


@router.get("/zones/{zone_id}", response_model=ShelfZoneOut)
def get_zone(zone_id: int, db: Session = Depends(get_db)):
    zone = db.query(ShelfZone).filter(ShelfZone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="货架分区不存在")
    return zone


@router.put("/zones/{zone_id}", response_model=ShelfZoneOut)
def update_zone(zone_id: int, data: ShelfZoneUpdate, operator_id: int = Query(...), db: Session = Depends(get_db)):
    require_admin(db, operator_id)
    zone = db.query(ShelfZone).filter(ShelfZone.id == zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="货架分区不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(zone, key, value)
    db.commit()
    db.refresh(zone)
    return zone


@router.post("/slots/", response_model=ShelfSlotOut)
def create_slot(data: ShelfSlotCreate, operator_id: int = Query(...), db: Session = Depends(get_db)):
    require_admin(db, operator_id)
    zone = db.query(ShelfZone).filter(ShelfZone.id == data.zone_id).first()
    if not zone:
        raise HTTPException(status_code=404, detail="货架分区不存在")
    slot = ShelfSlot(**data.model_dump())
    db.add(slot)
    db.commit()
    db.refresh(slot)
    return slot


@router.get("/slots/", response_model=List[ShelfSlotOut])
def list_slots(
    zone_id: Optional[int] = None,
    category_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(ShelfSlot)
    if zone_id is not None:
        query = query.filter(ShelfSlot.zone_id == zone_id)
    if category_id is not None:
        query = query.filter(ShelfSlot.category_id == category_id)
    if is_active is not None:
        query = query.filter(ShelfSlot.is_active == is_active)
    return query.order_by(ShelfSlot.position).all()


@router.get("/slots/{slot_id}", response_model=ShelfSlotOut)
def get_slot(slot_id: int, db: Session = Depends(get_db)):
    slot = db.query(ShelfSlot).filter(ShelfSlot.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="货架槽位不存在")
    return slot


@router.put("/slots/{slot_id}", response_model=ShelfSlotOut)
def update_slot(slot_id: int, data: ShelfSlotUpdate, operator_id: int = Query(...), db: Session = Depends(get_db)):
    require_executor(db, operator_id)
    slot = db.query(ShelfSlot).filter(ShelfSlot.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="货架槽位不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(slot, key, value)
    db.commit()
    db.refresh(slot)
    return slot
