from sqlalchemy import Column, DateTime, Integer, String, Text
from sqlalchemy.sql import func

from app.database import Base


class OperationLog(Base):
    """操作审计日志：记录关键写操作（删除、改密、重置密码等）。"""

    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    username = Column(String(50))
    role = Column(String(20))
    action = Column(String(50), index=True)  # 如 delete_student / change_password
    target = Column(String(255))  # 操作对象描述
    detail = Column(Text)  # 补充信息
    created_at = Column(DateTime(timezone=True), server_default=func.now())
