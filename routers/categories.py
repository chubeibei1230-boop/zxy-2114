from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from database import get_db
from models import Category, CategoryMoveLog, ProductMounting, ShelfSlot, DisplayStatus, Store
from schemas import (
    CategoryCreate, CategoryUpdate, CategoryMove, CategoryMerge,
    CategoryCopy, CategoryOut, CategoryTreeNode, CategoryRecursiveStats
)
from routers.auth import require_admin, require_executor
from sqlalchemy import func

router = APIRouter(prefix="/api/categories", tags=["类目树管理"])


def _build_tree(categories: List[Category], parent_id: Optional[int] = None) -> List[CategoryTreeNode]:
    nodes = []
    for cat in categories:
        if cat.parent_id == parent_id:
            product_count = len([pm for pm in cat.product_mountings if pm.is_active])
            vacancy_count = _count_vacancies_for_category(cat)
            node = CategoryTreeNode(
                id=cat.id,
                name=cat.name,
                code=cat.code,
                parent_id=cat.parent_id,
                level=cat.level,
                sort_order=cat.sort_order,
                is_active=cat.is_active,
                product_count=product_count,
                vacancy_count=vacancy_count,
                children=_build_tree(categories, cat.id)
            )
            nodes.append(node)
    nodes.sort(key=lambda x: x.sort_order)
    return nodes


def _count_vacancies_for_category(cat: Category) -> int:
    count = 0
    for slot in cat.shelf_slots:
        if not slot.is_active:
            continue
        latest_status = None
        for ds in slot.display_statuses:
            if latest_status is None or ds.check_date > latest_status.check_date:
                latest_status = ds
        if latest_status and latest_status.status in ("empty", "vacant"):
            count += 1
        elif not latest_status:
            count += 1
    return count


def _get_all_descendant_ids(db: Session, category_id: int) -> List[int]:
    result = [category_id]
    children = db.query(Category).filter(Category.parent_id == category_id).all()
    for child in children:
        result.extend(_get_all_descendant_ids(db, child.id))
    return result


def _compute_level(db: Session, parent_id: Optional[int]) -> int:
    if parent_id is None:
        return 1
    parent = db.query(Category).filter(Category.id == parent_id).first()
    if not parent:
        return 1
    return parent.level + 1


def _update_children_levels(db: Session, parent_id: int):
    children = db.query(Category).filter(Category.parent_id == parent_id).all()
    parent = db.query(Category).filter(Category.id == parent_id).first()
    for child in children:
        child.level = parent.level + 1
        _update_children_levels(db, child.id)


def _deep_copy_category(db: Session, source: Category, target_store_id: int, new_parent_id: Optional[int], new_level: int, operator_id: Optional[int]):
    new_cat = Category(
        name=source.name,
        code=f"{source.code}_copy_{target_store_id}",
        store_id=target_store_id,
        parent_id=new_parent_id,
        level=new_level,
        sort_order=source.sort_order,
        is_active=source.is_active,
        description=source.description,
    )
    db.add(new_cat)
    db.flush()
    for child in source.children:
        _deep_copy_category(db, child, target_store_id, new_cat.id, new_level + 1, operator_id)


@router.post("/", response_model=CategoryOut)
def create_category(data: CategoryCreate, operator_id: int = Query(...), db: Session = Depends(get_db)):
    require_admin(db, operator_id)
    store = db.query(Store).filter(Store.id == data.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")
    if data.parent_id:
        parent = db.query(Category).filter(Category.id == data.parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="父类目不存在")
        if parent.store_id != data.store_id:
            raise HTTPException(status_code=400, detail="父类目不属于该门店")
    existing = db.query(Category).filter(
        Category.code == data.code, Category.store_id == data.store_id
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="该门店下编码已存在")
    level = _compute_level(db, data.parent_id)
    cat = Category(**data.model_dump(), level=level)
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.get("/", response_model=List[CategoryOut])
def list_categories(
    store_id: Optional[int] = None,
    parent_id: Optional[int] = None,
    is_active: Optional[bool] = None,
    db: Session = Depends(get_db)
):
    query = db.query(Category)
    if store_id is not None:
        query = query.filter(Category.store_id == store_id)
    if parent_id is not None:
        query = query.filter(Category.parent_id == parent_id)
    if is_active is not None:
        query = query.filter(Category.is_active == is_active)
    return query.order_by(Category.sort_order).all()


@router.get("/tree/{store_id}", response_model=List[CategoryTreeNode])
def get_category_tree(store_id: int, db: Session = Depends(get_db)):
    categories = db.query(Category).filter(Category.store_id == store_id).all()
    return _build_tree(categories)


@router.get("/{category_id}", response_model=CategoryOut)
def get_category(category_id: int, db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="类目不存在")
    return cat


@router.put("/{category_id}", response_model=CategoryOut)
def update_category(category_id: int, data: CategoryUpdate, operator_id: int = Query(...), db: Session = Depends(get_db)):
    require_admin(db, operator_id)
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="类目不存在")
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(cat, key, value)
    db.commit()
    db.refresh(cat)
    return cat


@router.put("/{category_id}/move", response_model=CategoryOut)
def move_category(category_id: int, data: CategoryMove, db: Session = Depends(get_db)):
    require_admin(db, data.operated_by or 0)
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="类目不存在")
    if data.new_parent_id == category_id:
        raise HTTPException(status_code=400, detail="不能将类目移动到自身下")
    if data.new_parent_id is not None:
        new_parent = db.query(Category).filter(Category.id == data.new_parent_id).first()
        if not new_parent:
            raise HTTPException(status_code=404, detail="目标父类目不存在")
        if new_parent.store_id != cat.store_id:
            raise HTTPException(status_code=400, detail="不能跨门店移动类目")
        descendant_ids = _get_all_descendant_ids(db, category_id)
        if data.new_parent_id in descendant_ids:
            raise HTTPException(status_code=400, detail="不能将类目移动到其子类目下")
    old_parent_id = cat.parent_id
    cat.parent_id = data.new_parent_id
    cat.level = _compute_level(db, data.new_parent_id)
    _update_children_levels(db, cat.id)
    log = CategoryMoveLog(
        category_id=category_id,
        old_parent_id=old_parent_id,
        new_parent_id=data.new_parent_id,
        operated_by=data.operated_by,
        move_type="move"
    )
    db.add(log)
    db.commit()
    db.refresh(cat)
    return cat


@router.put("/{category_id}/disable", response_model=CategoryOut)
def disable_category(category_id: int, operator_id: int = Query(...), cascade: bool = Query(False), db: Session = Depends(get_db)):
    require_admin(db, operator_id)
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="类目不存在")
    cat.is_active = False
    if cascade:
        descendant_ids = _get_all_descendant_ids(db, category_id)
        db.query(Category).filter(Category.id.in_(descendant_ids[1:])).update(
            {Category.is_active: False}, synchronize_session=False
        )
    db.commit()
    db.refresh(cat)
    return cat


@router.put("/{category_id}/enable", response_model=CategoryOut)
def enable_category(category_id: int, operator_id: int = Query(...), db: Session = Depends(get_db)):
    require_admin(db, operator_id)
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="类目不存在")
    cat.is_active = True
    db.commit()
    db.refresh(cat)
    return cat


@router.post("/merge", response_model=CategoryOut)
def merge_categories(data: CategoryMerge, db: Session = Depends(get_db)):
    require_admin(db, data.operated_by or 0)
    source = db.query(Category).filter(Category.id == data.source_id).first()
    target = db.query(Category).filter(Category.id == data.target_id).first()
    if not source or not target:
        raise HTTPException(status_code=404, detail="源类目或目标类目不存在")
    if source.store_id != target.store_id:
        raise HTTPException(status_code=400, detail="不能跨门店合并类目")
    if data.target_id in _get_all_descendant_ids(db, data.source_id):
        raise HTTPException(status_code=400, detail="不能合并到自身的子类目")
    db.query(ProductMounting).filter(ProductMounting.category_id == source.id).update(
        {ProductMounting.category_id: target.id}
    )
    db.query(ShelfSlot).filter(ShelfSlot.category_id == source.id).update(
        {ShelfSlot.category_id: target.id}
    )
    for child in source.children:
        child.parent_id = target.id
        child.level = target.level + 1
        _update_children_levels(db, child.id)
    source.move_logs.clear()
    source.is_active = False
    source.name = f"{source.name}(已合并至{target.name})"
    db.commit()
    db.refresh(target)
    return target


@router.post("/copy", response_model=dict)
def copy_category_to_store(data: CategoryCopy, db: Session = Depends(get_db)):
    require_admin(db, data.operated_by or 0)
    source = db.query(Category).filter(Category.id == data.source_category_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="源类目不存在")
    target_store = db.query(Store).filter(Store.id == data.target_store_id).first()
    if not target_store:
        raise HTTPException(status_code=404, detail="目标门店不存在")
    if source.store_id == data.target_store_id:
        raise HTTPException(status_code=400, detail="不能复制到同一门店")
    level = _compute_level(db, data.target_parent_id)
    _deep_copy_category(db, source, data.target_store_id, data.target_parent_id, level, data.operated_by)
    log = CategoryMoveLog(
        category_id=source.id,
        old_parent_id=source.parent_id,
        new_parent_id=data.target_parent_id,
        operated_by=data.operated_by,
        move_type="copy"
    )
    db.add(log)
    db.commit()
    return {"detail": "类目树已跨门店复制"}


@router.get("/{category_id}/recursive", response_model=CategoryRecursiveStats)
def get_recursive_stats(category_id: int, db: Session = Depends(get_db)):
    cat = db.query(Category).filter(Category.id == category_id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="类目不存在")
    descendant_ids = _get_all_descendant_ids(db, category_id)
    total_products = db.query(ProductMounting).filter(
        ProductMounting.category_id.in_(descendant_ids),
        ProductMounting.is_active == True
    ).count()
    slots = db.query(ShelfSlot).filter(
        ShelfSlot.category_id.in_(descendant_ids),
        ShelfSlot.is_active == True
    ).all()
    total_vacancies = 0
    for slot in slots:
        latest = db.query(DisplayStatus).filter(
            DisplayStatus.slot_id == slot.id
        ).order_by(DisplayStatus.check_date.desc()).first()
        if not latest or latest.status in ("empty", "vacant"):
            total_vacancies += 1
    descendants = db.query(Category).filter(Category.id.in_(descendant_ids[1:])).all()
    return CategoryRecursiveStats(
        category_id=cat.id,
        category_name=cat.name,
        total_children=len(descendant_ids) - 1,
        total_products=total_products,
        total_vacancies=total_vacancies,
        descendants=descendants
    )
