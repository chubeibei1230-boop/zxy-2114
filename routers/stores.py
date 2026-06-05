from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from models import Store
from schemas import StoreCreate, StoreUpdate, StoreOut
from routers.auth import require_admin

router = APIRouter(prefix="/api/stores", tags=["门店管理"])


@router.post("/", response_model=StoreOut)
def create_store(data: StoreCreate, operator_id: int = Query(...), db: Session = Depends(get_db)):
    require_admin(db, operator_id)
    existing = db.query(Store).filter(
        (Store.name == data.name) | (Store.code == data.code)
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="门店名称或编码已存在")
    store = Store(**data.model_dump())
    db.add(store)
    db.commit()
    db.refresh(store)
    return store


@router.get("/", response_model=List[StoreOut])
def list_stores(is_active: Optional[bool] = None, db: Session = Depends(get_db)):
    query = db.query(Store)
    if is_active is not None:
        query = query.filter(Store.is_active == is_active)
    return query.all()


@router.get("/{store_id}", response_model=StoreOut)
def get_store(store_id: int, db: Session = Depends(get_db)):
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")
    return store


@router.put("/{store_id}", response_model=StoreOut)
def update_store(store_id: int, data: StoreUpdate, operator_id: int = Query(...), db: Session = Depends(get_db)):
    require_admin(db, operator_id)
    store = db.query(Store).filter(Store.id == store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(store, key, value)
    db.commit()
    db.refresh(store)
    return store
