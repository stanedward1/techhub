from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.audit import audit
from app.database import get_db
from app.deps import get_current_user
from app.models import Classroom, User
from app.schemas import LoginRequest, PasswordRequest, RegisterRequest
from app.security import create_access_token, hash_password, verify_password
from app.utils import to_dict
import os
import uuid

router = APIRouter(prefix="/api/auth", tags=["认证"])


def public_user(db: Session, user: User) -> dict:
    data = to_dict(user)
    data.pop("password_hash", None)
    class_name = None
    if user.class_id:
        cls = db.get(Classroom, user.class_id)
        class_name = cls.name if cls else None
    data["class_name"] = class_name
    return data


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    if payload.class_id is not None:
        # 学生登录：班级 + 姓名 + 密码
        user = (
            db.query(User)
            .filter(
                User.role == "student",
                User.class_id == payload.class_id,
                User.name == payload.username,
            )
            .first()
        )
        if not user or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="班级、姓名或密码错误")
    else:
        # 教师/管理员登录：用户名 + 密码
        user = db.query(User).filter(User.username == payload.username).first()
        if not user or user.role == "student" or not verify_password(payload.password, user.password_hash):
            raise HTTPException(status_code=401, detail="用户名或密码错误")
    token = create_access_token(subject=str(user.id), role=user.role)
    return {"token": token, "user": public_user(db, user)}


@router.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    """学生自助注册（仅允许系统中尚不存在「班级+姓名」的学生）。"""
    if payload.class_id and not db.get(Classroom, payload.class_id):
        raise HTTPException(status_code=400, detail="所选班级不存在")

    # 校验是否已存在「班级 + 姓名」的学生账号
    exists = (
        db.query(User)
        .filter(
            User.role == "student",
            User.class_id == payload.class_id,
            User.name == payload.name,
        )
        .first()
    )
    if exists:
        raise HTTPException(status_code=409, detail="该学生已有账号，无需重复注册，请直接登录")

    user = User(
        username=payload.name,  # 用户名 = 姓名
        password_hash=hash_password(payload.password),
        name=payload.name,
        role="student",
        class_id=payload.class_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token(subject=str(user.id), role=user.role)
    return {"token": token, "user": public_user(db, user)}


@router.get("/me")
def me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return {"user": public_user(db, user)}


@router.put("/password")
def change_password(
    payload: PasswordRequest,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not verify_password(payload.old_password, user.password_hash):
        raise HTTPException(status_code=400, detail="原密码不正确")
    user.password_hash = hash_password(payload.new_password)
    audit(db, user, "change_password", target=user.username)
    db.commit()
    return {"ok": True}


_AVATAR_DIR = "uploads/avatars"
_AVATAR_MAX_SIZE = 2 * 1024 * 1024  # 2MB
_AVATAR_ALLOWED = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


@router.post("/avatar")
async def upload_avatar(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """学生 / 教师上传自己的头像。"""
    original = file.filename or "avatar"
    ext = os.path.splitext(original)[1].lower()
    if ext not in _AVATAR_ALLOWED:
        raise HTTPException(status_code=400, detail=f"仅支持图片格式：{'、'.join(sorted(_AVATAR_ALLOWED))}")

    name = f"avatar_{user.id}_{uuid.uuid4().hex[:8]}{ext}"
    os.makedirs(_AVATAR_DIR, exist_ok=True)
    dest = os.path.join(_AVATAR_DIR, name)

    size = 0
    chunk_size = 1024 * 1024
    try:
        with open(dest, "wb") as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                size += len(chunk)
                if size > _AVATAR_MAX_SIZE:
                    f.close()
                    os.remove(dest)
                    raise HTTPException(status_code=413, detail=f"头像文件不能超过 {_AVATAR_MAX_SIZE // (1024*1024)}MB")
                f.write(chunk)
    except HTTPException:
        raise
    except Exception:
        if os.path.exists(dest):
            os.remove(dest)
        raise

    # 删除旧头像文件
    if user.avatar:
        old_path = user.avatar.replace("/uploads/", "")
        old_full = os.path.join(old_path)
        if os.path.exists(old_full):
            os.remove(old_full)

    user.avatar = f"/uploads/avatars/{name}"
    db.commit()
    return {"avatar": user.avatar}
