from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from database import get_db
from models import User
from schemas import UserCreate, UserOut

router = APIRouter(prefix="/api/users", tags=["用户与权限"])


def require_role(db: Session, user_id: int, roles: List[str]):
    user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    if user.role not in roles:
        raise HTTPException(status_code=403, detail=f"权限不足，需要角色: {','.join(roles)}")
    return user


def require_admin(db: Session, user_id: int):
    return require_role(db, user_id, ["admin"])


def require_executor(db: Session, user_id: int):
    return require_role(db, user_id, ["admin", "executor"])


def require_supervisor(db: Session, user_id: int):
    return require_role(db, user_id, ["admin", "supervisor"])


@router.post("/", response_model=UserOut)
def create_user(data: UserCreate, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="用户名已存在")
    user = User(**data.model_dump())
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/", response_model=List[UserOut])
def list_users(role: str = None, db: Session = Depends(get_db)):
    query = db.query(User).filter(User.is_active == True)
    if role:
        query = query.filter(User.role == role)
    return query.all()


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="用户不存在")
    return user
