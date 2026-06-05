from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from database import get_db
from models import Product, ProductMounting, DisplayStatus, ShelfSlot, ShelfZone, Category, Store
from schemas import (
    ProductCreate, ProductUpdate, ProductOut,
    ProductMountingCreate, ProductMountingOut,
    DisplayStatusCreate, DisplayStatusUpdate, DisplayStatusOut
)
from routers.auth import require_admin, require_executor, require_supervisor

router = APIRouter(prefix="/api/displays", tags=["商品挂载与陈列状态"])


@router.post("/products/", response_model=ProductOut)
def create_product(data: ProductCreate, operator_id: int = Query(...), db: Session = Depends(get_db)):
    require_admin(db, operator_id)
    existing = db.query(Product).filter(Product.sku == data.sku).first()
    if existing:
        raise HTTPException(status_code=400, detail="SKU已存在")
    product = Product(**data.model_dump())
    db.add(product)
    db.commit()
    db.refresh(product)
    return product


@router.get("/products/", response_model=List[ProductOut])
def list_products(is_active: Optional[bool] = None, db: Session = Depends(get_db)):
    query = db.query(Product)
    if is_active is not None:
        query = query.filter(Product.is_active == is_active)
    return query.all()


@router.get("/products/{product_id}", response_model=ProductOut)
def get_product(product_id: int, db: Session = Depends(get_db)):
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    return product


@router.put("/products/{product_id}", response_model=ProductOut)
def update_product(product_id: int, data: ProductUpdate, operator_id: int = Query(...), db: Session = Depends(get_db)):
    require_admin(db, operator_id)
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(product, key, value)
    db.commit()
    db.refresh(product)
    return product


@router.post("/mountings/", response_model=ProductMountingOut)
def create_mounting(data: ProductMountingCreate, operator_id: int = Query(...), db: Session = Depends(get_db)):
    require_executor(db, operator_id)
    product = db.query(Product).filter(Product.id == data.product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="商品不存在")
    category = db.query(Category).filter(Category.id == data.category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="类目不存在")
    store = db.query(Store).filter(Store.id == data.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")
    if category.store_id != data.store_id:
        raise HTTPException(status_code=400, detail="类目不属于该门店，不能跨门店挂载")
    mounting = ProductMounting(**data.model_dump())
    db.add(mounting)
    db.commit()
    db.refresh(mounting)
    return mounting


@router.get("/mountings/", response_model=List[ProductMountingOut])
def list_mountings(
    store_id: Optional[int] = None,
    category_id: Optional[int] = None,
    product_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(ProductMounting)
    if store_id is not None:
        query = query.filter(ProductMounting.store_id == store_id)
    if category_id is not None:
        query = query.filter(ProductMounting.category_id == category_id)
    if product_id is not None:
        query = query.filter(ProductMounting.product_id == product_id)
    if is_active is not None:
        query = query.filter(ProductMounting.is_active == is_active)
    return query.all()


@router.delete("/mountings/{mounting_id}")
def delete_mounting(mounting_id: int, operator_id: int = Query(...), db: Session = Depends(get_db)):
    require_executor(db, operator_id)
    mounting = db.query(ProductMounting).filter(ProductMounting.id == mounting_id).first()
    if not mounting:
        raise HTTPException(status_code=404, detail="挂载记录不存在")
    mounting.is_active = False
    db.commit()
    return {"detail": "已解除挂载"}


@router.post("/statuses/", response_model=DisplayStatusOut)
def create_display_status(data: DisplayStatusCreate, operator_id: int = Query(...), db: Session = Depends(get_db)):
    require_executor(db, operator_id)
    slot = db.query(ShelfSlot).filter(ShelfSlot.id == data.slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="货架槽位不存在")
    if data.product_id:
        product = db.query(Product).filter(Product.id == data.product_id).first()
        if not product:
            raise HTTPException(status_code=404, detail="商品不存在")
    create_data = data.model_dump(exclude={"checked_by"})
    status = DisplayStatus(**create_data, checked_by=operator_id)
    db.add(status)
    db.commit()
    db.refresh(status)
    return status


@router.get("/statuses/", response_model=List[DisplayStatusOut])
def list_display_statuses(
    store_id: Optional[int] = None,
    zone_id: Optional[int] = None,
    category_id: Optional[int] = None,
    status: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    query = db.query(DisplayStatus)
    if zone_id is not None:
        slot_ids = db.query(ShelfSlot.id).filter(ShelfSlot.zone_id == zone_id).subquery()
        query = query.filter(DisplayStatus.slot_id.in_(slot_ids))
    if store_id is not None:
        zone_ids = db.query(ShelfZone.id).filter(ShelfZone.store_id == store_id).subquery()
        slot_ids = db.query(ShelfSlot.id).filter(ShelfSlot.zone_id.in_(zone_ids)).subquery()
        query = query.filter(DisplayStatus.slot_id.in_(slot_ids))
    if category_id is not None:
        slot_ids = db.query(ShelfSlot.id).filter(ShelfSlot.category_id == category_id).subquery()
        query = query.filter(DisplayStatus.slot_id.in_(slot_ids))
    if status is not None:
        query = query.filter(DisplayStatus.status == status)
    if date_from is not None:
        query = query.filter(DisplayStatus.check_date >= date_from)
    if date_to is not None:
        query = query.filter(DisplayStatus.check_date <= date_to)
    return query.order_by(DisplayStatus.check_date.desc()).all()


@router.put("/statuses/{status_id}", response_model=DisplayStatusOut)
def update_display_status(status_id: int, data: DisplayStatusUpdate, operator_id: int = Query(...), db: Session = Depends(get_db)):
    require_supervisor(db, operator_id)
    ds = db.query(DisplayStatus).filter(DisplayStatus.id == status_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="陈列状态记录不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(ds, key, value)
    db.commit()
    db.refresh(ds)
    return ds


@router.get("/statuses/check/{slot_id}", response_model=DisplayStatusOut)
def check_slot_status(slot_id: int, db: Session = Depends(get_db)):
    slot = db.query(ShelfSlot).filter(ShelfSlot.id == slot_id).first()
    if not slot:
        raise HTTPException(status_code=404, detail="货架槽位不存在")
    latest = db.query(DisplayStatus).filter(
        DisplayStatus.slot_id == slot_id
    ).order_by(DisplayStatus.check_date.desc()).first()
    if not latest:
        raise HTTPException(status_code=404, detail="该槽位尚无陈列状态记录")
    return latest
