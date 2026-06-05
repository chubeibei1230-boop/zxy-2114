from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from database import get_db
from models import (
    RectificationTask, Store, Category, ShelfSlot, ShelfZone,
    DisplayStatus, Product, ProductMounting, User
)
from schemas import (
    RectificationTaskCreate, RectificationTaskProcess,
    RectificationTaskComplete, RectificationTaskClose,
    RectificationTaskOut, RectificationTaskDetailOut,
    StoreRectificationStatsOut
)
from routers.auth import require_admin, require_executor, require_supervisor

router = APIRouter(prefix="/api/rectifications", tags=["门店陈列整改任务"])


def _build_category_path(db: Session, category_id: int) -> str:
    parts = []
    current = db.query(Category).filter(Category.id == category_id).first()
    visited = set()
    while current and current.id not in visited:
        visited.add(current.id)
        parts.append(current.name)
        if current.parent_id is None:
            break
        current = db.query(Category).filter(Category.id == current.parent_id).first()
    return " > ".join(reversed(parts))


def _get_slot_store_id(db: Session, slot_id: int) -> Optional[int]:
    slot = db.query(ShelfSlot).filter(ShelfSlot.id == slot_id).first()
    if not slot:
        return None
    zone = db.query(ShelfZone).filter(ShelfZone.id == slot.zone_id).first()
    return zone.store_id if zone else None


def _check_creation_validity(db: Session, data: RectificationTaskCreate):
    store = db.query(Store).filter(Store.id == data.store_id).first()
    if not store:
        raise HTTPException(status_code=404, detail="门店不存在")
    if not store.is_active:
        raise HTTPException(status_code=400, detail="门店已停用，无法创建整改任务")

    if data.category_id is not None:
        cat = db.query(Category).filter(Category.id == data.category_id).first()
        if not cat:
            raise HTTPException(status_code=404, detail="类目不存在")
        if cat.store_id != data.store_id:
            raise HTTPException(status_code=400, detail="类目不属于该门店")
        if not cat.is_active:
            raise HTTPException(status_code=400, detail="类目已停用，无法创建整改任务")

    if data.slot_id is not None:
        slot = db.query(ShelfSlot).filter(ShelfSlot.id == data.slot_id).first()
        if not slot:
            raise HTTPException(status_code=404, detail="货架位不存在")
        slot_store_id = _get_slot_store_id(db, data.slot_id)
        if slot_store_id and slot_store_id != data.store_id:
            raise HTTPException(status_code=400, detail="货架位不属于该门店")
        if not slot.is_active:
            raise HTTPException(status_code=400, detail="货架位已失效，无法创建整改任务")
        if data.category_id is not None and slot.category_id is not None:
            if slot.category_id != data.category_id:
                raise HTTPException(status_code=400, detail="货架位绑定的类目与任务类目不一致")

    if data.display_status_id is not None:
        ds = db.query(DisplayStatus).filter(DisplayStatus.id == data.display_status_id).first()
        if not ds:
            raise HTTPException(status_code=404, detail="陈列状态记录不存在")
        ds_store_id = _get_slot_store_id(db, ds.slot_id)
        if ds_store_id and ds_store_id != data.store_id:
            raise HTTPException(status_code=400, detail="陈列状态所属门店与任务门店不一致")
        if data.slot_id is not None and ds.slot_id != data.slot_id:
            raise HTTPException(status_code=400, detail="陈列状态所属货架位与任务货架位不一致")
        if ds.product_id is not None:
            product = db.query(Product).filter(Product.id == ds.product_id).first()
            if product and not product.is_active:
                raise HTTPException(status_code=400, detail="关联商品已下架，无法创建整改任务")


@router.post("/", response_model=RectificationTaskOut)
def create_rectification_task(
    data: RectificationTaskCreate,
    operator_id: int = Query(...),
    db: Session = Depends(get_db)
):
    require_admin(db, operator_id)

    assignee = db.query(User).filter(User.id == data.assignee_id, User.is_active == True).first()
    if not assignee:
        raise HTTPException(status_code=404, detail="负责人不存在或已停用")

    _check_creation_validity(db, data)

    task = RectificationTask(
        store_id=data.store_id,
        category_id=data.category_id,
        slot_id=data.slot_id,
        display_status_id=data.display_status_id,
        assignee_id=data.assignee_id,
        creator_id=operator_id,
        title=data.title,
        description=data.description,
        status="pending",
        deadline=data.deadline,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@router.get("/", response_model=List[RectificationTaskOut])
def list_rectification_tasks(
    store_id: Optional[int] = None,
    assignee_id: Optional[int] = None,
    status: Optional[str] = None,
    date_from: Optional[datetime] = None,
    date_to: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    query = db.query(RectificationTask)
    if store_id is not None:
        query = query.filter(RectificationTask.store_id == store_id)
    if assignee_id is not None:
        query = query.filter(RectificationTask.assignee_id == assignee_id)
    if status is not None:
        query = query.filter(RectificationTask.status == status)
    if date_from is not None:
        query = query.filter(RectificationTask.created_at >= date_from)
    if date_to is not None:
        query = query.filter(RectificationTask.created_at <= date_to)
    return query.order_by(RectificationTask.created_at.desc()).all()


@router.get("/stats", response_model=List[StoreRectificationStatsOut])
def get_rectification_stats(
    operator_id: int = Query(...),
    db: Session = Depends(get_db)
):
    require_supervisor(db, operator_id)
    stores = db.query(Store).filter(Store.is_active == True).all()
    now = datetime.utcnow()
    results = []
    for store in stores:
        pending_count = db.query(RectificationTask).filter(
            RectificationTask.store_id == store.id,
            RectificationTask.status == "pending"
        ).count()
        processing_count = db.query(RectificationTask).filter(
            RectificationTask.store_id == store.id,
            RectificationTask.status == "processing"
        ).count()
        overdue_count = db.query(RectificationTask).filter(
            RectificationTask.store_id == store.id,
            RectificationTask.status.in_(["pending", "processing"]),
            RectificationTask.deadline.isnot(None),
            RectificationTask.deadline < now
        ).count()
        results.append(StoreRectificationStatsOut(
            store_id=store.id,
            store_name=store.name,
            pending_count=pending_count,
            processing_count=processing_count,
            overdue_count=overdue_count
        ))
    return results


@router.get("/{task_id}", response_model=RectificationTaskDetailOut)
def get_rectification_task_detail(task_id: int, db: Session = Depends(get_db)):
    task = db.query(RectificationTask).filter(RectificationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="整改任务不存在")

    store = db.query(Store).filter(Store.id == task.store_id).first()
    store_name = store.name if store else None

    effective_slot_id = task.slot_id
    effective_category_id = task.category_id

    if task.display_status_id is not None and effective_slot_id is None:
        ds = db.query(DisplayStatus).filter(DisplayStatus.id == task.display_status_id).first()
        if ds:
            effective_slot_id = ds.slot_id

    if effective_slot_id is not None and effective_category_id is None:
        slot = db.query(ShelfSlot).filter(ShelfSlot.id == effective_slot_id).first()
        if slot and slot.category_id is not None:
            effective_category_id = slot.category_id

    category_path = None
    if effective_category_id is not None:
        category_path = _build_category_path(db, effective_category_id)

    slot_code = None
    if effective_slot_id is not None:
        slot = db.query(ShelfSlot).filter(ShelfSlot.id == effective_slot_id).first()
        if slot:
            slot_code = slot.slot_code

    original_display_status = None
    original_display_remark = None
    if task.display_status_id is not None:
        orig_ds = db.query(DisplayStatus).filter(DisplayStatus.id == task.display_status_id).first()
        if orig_ds:
            original_display_status = orig_ds.status
            original_display_remark = orig_ds.remark

    current_display_status = None
    if effective_slot_id is not None:
        latest_ds = db.query(DisplayStatus).filter(
            DisplayStatus.slot_id == effective_slot_id
        ).order_by(DisplayStatus.check_date.desc()).first()
        if latest_ds:
            current_display_status = latest_ds.status

    assignee = db.query(User).filter(User.id == task.assignee_id).first()
    assignee_name = assignee.display_name or assignee.username if assignee else None

    creator = db.query(User).filter(User.id == task.creator_id).first()
    creator_name = creator.display_name or creator.username if creator else None

    closer_name = None
    if task.closed_by is not None:
        closer = db.query(User).filter(User.id == task.closed_by).first()
        closer_name = closer.display_name or closer.username if closer else None

    now = datetime.utcnow()
    is_overdue = (
        task.deadline is not None
        and task.status in ("pending", "processing")
        and task.deadline < now
    )

    return RectificationTaskDetailOut(
        id=task.id,
        store_id=task.store_id,
        store_name=store_name,
        category_id=effective_category_id,
        category_path=category_path,
        slot_id=effective_slot_id,
        slot_code=slot_code,
        display_status_id=task.display_status_id,
        original_display_status=original_display_status,
        original_display_remark=original_display_remark,
        current_display_status=current_display_status,
        assignee_id=task.assignee_id,
        assignee_name=assignee_name,
        creator_id=task.creator_id,
        creator_name=creator_name,
        title=task.title,
        description=task.description,
        status=task.status,
        rectification_note=task.rectification_note,
        rectified_at=task.rectified_at,
        deadline=task.deadline,
        closed_by=task.closed_by,
        closer_name=closer_name,
        closed_at=task.closed_at,
        is_overdue=is_overdue,
        created_at=task.created_at,
        updated_at=task.updated_at,
    )


@router.put("/{task_id}/process", response_model=RectificationTaskOut)
def start_processing(
    task_id: int,
    data: RectificationTaskProcess,
    operator_id: int = Query(...),
    db: Session = Depends(get_db)
):
    require_executor(db, operator_id)
    task = db.query(RectificationTask).filter(RectificationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="整改任务不存在")
    if task.status != "pending":
        raise HTTPException(status_code=400, detail=f"当前状态为{task.status}，无法开始处理")
    if task.assignee_id != operator_id:
        user = db.query(User).filter(User.id == operator_id).first()
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="仅负责人或管理员可处理此任务")
    task.status = "processing"
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return task


@router.put("/{task_id}/complete", response_model=RectificationTaskOut)
def complete_task(
    task_id: int,
    data: RectificationTaskComplete,
    operator_id: int = Query(...),
    db: Session = Depends(get_db)
):
    require_executor(db, operator_id)
    task = db.query(RectificationTask).filter(RectificationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="整改任务不存在")
    if task.status != "processing":
        raise HTTPException(status_code=400, detail=f"当前状态为{task.status}，无法完成")
    if task.assignee_id != operator_id:
        user = db.query(User).filter(User.id == operator_id).first()
        if user.role != "admin":
            raise HTTPException(status_code=403, detail="仅负责人或管理员可完成此任务")
    task.status = "completed"
    task.rectification_note = data.rectification_note
    task.rectified_at = data.rectified_at or datetime.utcnow()
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return task


@router.put("/{task_id}/close", response_model=RectificationTaskOut)
def close_task(
    task_id: int,
    data: RectificationTaskClose,
    operator_id: int = Query(...),
    db: Session = Depends(get_db)
):
    require_supervisor(db, operator_id)
    task = db.query(RectificationTask).filter(RectificationTask.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="整改任务不存在")
    if task.status != "completed":
        raise HTTPException(status_code=400, detail=f"当前状态为{task.status}，仅已完成任务可被关闭")
    task.status = "closed"
    task.closed_by = operator_id
    task.closed_at = datetime.utcnow()
    task.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(task)
    return task
