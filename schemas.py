from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class StoreCreate(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=50)
    address: Optional[str] = None


class StoreUpdate(BaseModel):
    name: Optional[str] = None
    address: Optional[str] = None
    is_active: Optional[bool] = None


class StoreOut(BaseModel):
    id: int
    name: str
    code: str
    address: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CategoryCreate(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=50)
    store_id: int
    parent_id: Optional[int] = None
    sort_order: Optional[int] = 0
    description: Optional[str] = None


class CategoryMove(BaseModel):
    new_parent_id: Optional[int] = None
    operated_by: Optional[int] = None


class CategoryMerge(BaseModel):
    source_id: int
    target_id: int
    operated_by: Optional[int] = None


class CategoryCopy(BaseModel):
    source_category_id: int
    target_store_id: int
    target_parent_id: Optional[int] = None
    operated_by: Optional[int] = None


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None
    description: Optional[str] = None


class CategoryOut(BaseModel):
    id: int
    name: str
    code: str
    store_id: int
    parent_id: Optional[int]
    level: int
    sort_order: int
    is_active: bool
    description: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CategoryTreeNode(BaseModel):
    id: int
    name: str
    code: str
    parent_id: Optional[int]
    level: int
    sort_order: int
    is_active: bool
    product_count: int = 0
    vacancy_count: int = 0
    children: List["CategoryTreeNode"] = []


CategoryTreeNode.model_rebuild()


class CategoryRecursiveStats(BaseModel):
    category_id: int
    category_name: str
    total_children: int
    total_products: int
    total_vacancies: int
    descendants: List[CategoryOut] = []


class ShelfZoneCreate(BaseModel):
    name: str = Field(..., max_length=100)
    code: str = Field(..., max_length=50)
    store_id: int
    zone_type: Optional[str] = None
    sort_order: Optional[int] = 0


class ShelfZoneUpdate(BaseModel):
    name: Optional[str] = None
    zone_type: Optional[str] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class ShelfZoneOut(BaseModel):
    id: int
    name: str
    code: str
    store_id: int
    zone_type: Optional[str]
    sort_order: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ShelfSlotCreate(BaseModel):
    zone_id: int
    category_id: Optional[int] = None
    slot_code: str = Field(..., max_length=50)
    position: Optional[int] = 0
    capacity: Optional[int] = 1


class ShelfSlotUpdate(BaseModel):
    category_id: Optional[int] = None
    position: Optional[int] = None
    capacity: Optional[int] = None
    is_active: Optional[bool] = None


class ShelfSlotOut(BaseModel):
    id: int
    zone_id: int
    category_id: Optional[int]
    slot_code: str
    position: int
    capacity: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ProductCreate(BaseModel):
    name: str = Field(..., max_length=200)
    sku: str = Field(..., max_length=50)
    barcode: Optional[str] = None
    spec: Optional[str] = None


class ProductUpdate(BaseModel):
    name: Optional[str] = None
    barcode: Optional[str] = None
    spec: Optional[str] = None
    is_active: Optional[bool] = None


class ProductOut(BaseModel):
    id: int
    name: str
    sku: str
    barcode: Optional[str]
    spec: Optional[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ProductMountingCreate(BaseModel):
    product_id: int
    category_id: int
    store_id: int
    quantity: Optional[int] = 0


class ProductMountingOut(BaseModel):
    id: int
    product_id: int
    category_id: int
    store_id: int
    quantity: int
    is_active: bool
    mounted_at: datetime

    class Config:
        from_attributes = True


class DisplayStatusCreate(BaseModel):
    slot_id: int
    product_id: Optional[int] = None
    status: str = Field(..., pattern="^(empty|occupied|vacant|abnormal)$")
    checked_by: Optional[int] = None
    remark: Optional[str] = None


class DisplayStatusUpdate(BaseModel):
    product_id: Optional[int] = None
    status: Optional[str] = None
    remark: Optional[str] = None


class DisplayStatusOut(BaseModel):
    id: int
    slot_id: int
    product_id: Optional[int]
    status: str
    checked_by: Optional[int]
    check_date: datetime
    remark: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str = Field(..., max_length=50)
    display_name: Optional[str] = None
    role: str = Field(..., pattern="^(admin|executor|supervisor)$")
    store_id: Optional[int] = None


class UserOut(BaseModel):
    id: int
    username: str
    display_name: Optional[str]
    role: str
    store_id: Optional[int]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class VacancyCategoryOut(BaseModel):
    category_id: int
    category_name: str
    store_id: int
    store_name: str
    total_slots: int
    vacant_slots: int
    vacancy_rate: float


class HighFrequencyMoveNode(BaseModel):
    category_id: int
    category_name: str
    move_count: int
    latest_move_at: Optional[datetime]


class StoreCoverageOut(BaseModel):
    store_id: int
    store_name: str
    total_categories: int
    active_categories: int
    covered_categories: int
    coverage_rate: float


class RectificationTaskCreate(BaseModel):
    store_id: int
    category_id: Optional[int] = None
    slot_id: Optional[int] = None
    display_status_id: Optional[int] = None
    assignee_id: int
    title: str = Field(..., max_length=200)
    description: Optional[str] = None
    deadline: Optional[datetime] = None


class RectificationTaskProcess(BaseModel):
    pass


class RectificationTaskComplete(BaseModel):
    rectification_note: str
    rectified_at: Optional[datetime] = None


class RectificationTaskClose(BaseModel):
    pass


class RectificationTaskOut(BaseModel):
    id: int
    store_id: int
    category_id: Optional[int]
    slot_id: Optional[int]
    display_status_id: Optional[int]
    assignee_id: int
    creator_id: int
    title: str
    description: Optional[str]
    status: str
    rectification_note: Optional[str]
    rectified_at: Optional[datetime]
    deadline: Optional[datetime]
    closed_by: Optional[int]
    closed_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RectificationTaskDetailOut(BaseModel):
    id: int
    store_id: int
    store_name: Optional[str] = None
    category_id: Optional[int]
    category_path: Optional[str] = None
    slot_id: Optional[int]
    slot_code: Optional[str] = None
    display_status_id: Optional[int]
    original_display_status: Optional[str] = None
    original_display_remark: Optional[str] = None
    current_display_status: Optional[str] = None
    assignee_id: int
    assignee_name: Optional[str] = None
    creator_id: int
    creator_name: Optional[str] = None
    title: str
    description: Optional[str]
    status: str
    rectification_note: Optional[str]
    rectified_at: Optional[datetime]
    deadline: Optional[datetime]
    closed_by: Optional[int]
    closer_name: Optional[str] = None
    closed_at: Optional[datetime]
    is_overdue: bool = False
    created_at: datetime
    updated_at: datetime


class StoreRectificationStatsOut(BaseModel):
    store_id: int
    store_name: str
    pending_count: int
    processing_count: int
    overdue_count: int


class FilterParams(BaseModel):
    store_id: Optional[int] = None
    category_id: Optional[int] = None
    shelf_zone_id: Optional[int] = None
    status: Optional[str] = None
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
