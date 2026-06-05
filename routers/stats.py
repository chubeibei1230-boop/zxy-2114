from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from database import get_db
from models import (
    Category, CategoryMoveLog, ShelfSlot, ShelfZone, DisplayStatus,
    ProductMounting, Store
)
from schemas import VacancyCategoryOut, HighFrequencyMoveNode, StoreCoverageOut
from routers.auth import require_supervisor, require_admin

router = APIRouter(prefix="/api/stats", tags=["统计报表"])


@router.get("/vacancy-categories", response_model=List[VacancyCategoryOut])
def get_vacancy_categories(
    store_id: Optional[int] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    operator_id: int = Query(...),
    db: Session = Depends(get_db)
):
    require_supervisor(db, operator_id)
    query = db.query(Category).filter(Category.is_active == True)
    if store_id:
        query = query.filter(Category.store_id == store_id)
    categories = query.all()
    results = []
    for cat in categories:
        slots = db.query(ShelfSlot).filter(
            ShelfSlot.category_id == cat.id,
            ShelfSlot.is_active == True
        ).all()
        if not slots:
            continue
        total_slots = len(slots)
        vacant_slots = 0
        for slot in slots:
            status_query = db.query(DisplayStatus).filter(DisplayStatus.slot_id == slot.id)
            if date_from:
                status_query = status_query.filter(DisplayStatus.check_date >= date_from)
            if date_to:
                status_query = status_query.filter(DisplayStatus.check_date <= date_to)
            latest = status_query.order_by(DisplayStatus.check_date.desc()).first()
            if not latest or latest.status in ("empty", "vacant"):
                vacant_slots += 1
        if vacant_slots > 0:
            store = db.query(Store).filter(Store.id == cat.store_id).first()
            results.append(VacancyCategoryOut(
                category_id=cat.id,
                category_name=cat.name,
                store_id=cat.store_id,
                store_name=store.name if store else "",
                total_slots=total_slots,
                vacant_slots=vacant_slots,
                vacancy_rate=round(vacant_slots / total_slots, 4) if total_slots > 0 else 0
            ))
    return results


@router.get("/high-frequency-moves", response_model=List[HighFrequencyMoveNode])
def get_high_frequency_moves(
    store_id: Optional[int] = None,
    top_n: int = Query(10, ge=1, le=100),
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    operator_id: int = Query(...),
    db: Session = Depends(get_db)
):
    require_admin(db, operator_id)
    query = db.query(CategoryMoveLog)
    if date_from:
        query = query.filter(CategoryMoveLog.operated_at >= date_from)
    if date_to:
        query = query.filter(CategoryMoveLog.operated_at <= date_to)
    logs = query.all()
    if store_id:
        cat_ids = [c.id for c in db.query(Category).filter(Category.store_id == store_id).all()]
        logs = [l for l in logs if l.category_id in cat_ids]
    move_counts = {}
    for log in logs:
        if log.category_id not in move_counts:
            move_counts[log.category_id] = {"count": 0, "latest": None}
        move_counts[log.category_id]["count"] += 1
        if move_counts[log.category_id]["latest"] is None or log.operated_at > move_counts[log.category_id]["latest"]:
            move_counts[log.category_id]["latest"] = log.operated_at
    sorted_moves = sorted(move_counts.items(), key=lambda x: x[1]["count"], reverse=True)[:top_n]
    results = []
    for cat_id, info in sorted_moves:
        cat = db.query(Category).filter(Category.id == cat_id).first()
        results.append(HighFrequencyMoveNode(
            category_id=cat_id,
            category_name=cat.name if cat else f"已删除({cat_id})",
            move_count=info["count"],
            latest_move_at=info["latest"]
        ))
    return results


@router.get("/store-coverage", response_model=List[StoreCoverageOut])
def get_store_coverage(
    operator_id: int = Query(...),
    db: Session = Depends(get_db)
):
    require_supervisor(db, operator_id)
    stores = db.query(Store).filter(Store.is_active == True).all()
    results = []
    for store in stores:
        total_categories = db.query(Category).filter(Category.store_id == store.id).count()
        active_categories = db.query(Category).filter(
            Category.store_id == store.id, Category.is_active == True
        ).count()
        categories_with_products = db.query(ProductMounting).filter(
            ProductMounting.store_id == store.id,
            ProductMounting.is_active == True
        ).with_entities(ProductMounting.category_id).distinct().count()
        coverage_rate = round(categories_with_products / active_categories, 4) if active_categories > 0 else 0
        results.append(StoreCoverageOut(
            store_id=store.id,
            store_name=store.name,
            total_categories=total_categories,
            active_categories=active_categories,
            covered_categories=categories_with_products,
            coverage_rate=coverage_rate
        ))
    return results
