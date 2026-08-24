from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.security import decode_token

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=401, detail="未登录")
    try:
        payload = decode_token(credentials.credentials)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="无效的凭证")
    except Exception:
        raise HTTPException(status_code=401, detail="登录已过期，请重新登录")

    user = db.get(User, int(user_id))
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


def require_roles(*roles: str):
    def checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="无权限访问该资源")
        return user

    return checker


# 学生：仅能访问作业提交平台相关接口
require_student = require_roles("student")
# 教师/管理员：可访问后台全部功能
require_teacher = require_roles("teacher", "admin")
