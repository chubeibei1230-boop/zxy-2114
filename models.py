from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Float
from sqlalchemy.orm import relationship
from datetime import datetime
from database import Base


class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(50), nullable=False, unique=True)
    address = Column(String(255))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    categories = relationship("Category", back_populates="store")
    shelf_zones = relationship("ShelfZone", back_populates="store")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    parent_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    level = Column(Integer, default=1)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    description = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    store = relationship("Store", back_populates="categories")
    parent = relationship("Category", remote_side=[id], backref="children")
    product_mountings = relationship("ProductMounting", back_populates="category")
    shelf_slots = relationship("ShelfSlot", back_populates="category")
    move_logs = relationship("CategoryMoveLog", back_populates="category", cascade="all, delete-orphan")


class ShelfZone(Base):
    __tablename__ = "shelf_zones"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    code = Column(String(50), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    zone_type = Column(String(50))
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    store = relationship("Store", back_populates="shelf_zones")
    slots = relationship("ShelfSlot", back_populates="zone")


class ShelfSlot(Base):
    __tablename__ = "shelf_slots"

    id = Column(Integer, primary_key=True, index=True)
    zone_id = Column(Integer, ForeignKey("shelf_zones.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    slot_code = Column(String(50), nullable=False)
    position = Column(Integer, default=0)
    capacity = Column(Integer, default=1)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    zone = relationship("ShelfZone", back_populates="slots")
    category = relationship("Category", back_populates="shelf_slots")
    display_statuses = relationship("DisplayStatus", back_populates="slot")


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    sku = Column(String(50), nullable=False, unique=True)
    barcode = Column(String(50))
    spec = Column(String(100))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product_mountings = relationship("ProductMounting", back_populates="product")
    display_statuses = relationship("DisplayStatus", back_populates="product")


class ProductMounting(Base):
    __tablename__ = "product_mountings"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=False)
    quantity = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    mounted_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    product = relationship("Product", back_populates="product_mountings")
    category = relationship("Category", back_populates="product_mountings")


class DisplayStatus(Base):
    __tablename__ = "display_statuses"

    id = Column(Integer, primary_key=True, index=True)
    slot_id = Column(Integer, ForeignKey("shelf_slots.id"), nullable=False)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=True)
    status = Column(String(20), nullable=False, default="empty")
    checked_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    check_date = Column(DateTime, default=datetime.utcnow)
    remark = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

    slot = relationship("ShelfSlot", back_populates="display_statuses")
    product = relationship("Product", back_populates="display_statuses")
    checker = relationship("User", back_populates="display_checks")


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False, unique=True)
    display_name = Column(String(100))
    role = Column(String(20), nullable=False, default="executor")
    store_id = Column(Integer, ForeignKey("stores.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    display_checks = relationship("DisplayStatus", back_populates="checker")


class CategoryMoveLog(Base):
    __tablename__ = "category_move_logs"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=False)
    old_parent_id = Column(Integer, nullable=True)
    new_parent_id = Column(Integer, nullable=True)
    operated_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    operated_at = Column(DateTime, default=datetime.utcnow)
    move_type = Column(String(30), default="move")

    category = relationship("Category", back_populates="move_logs")
