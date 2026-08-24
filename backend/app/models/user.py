from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    # 学生账号 username = 姓名（可重名），教师/管理员账号需唯一（由创建逻辑保证）
    username = Column(String(50), nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(50), nullable=False)
    role = Column(String(20), nullable=False, default="student")  # student / teacher / admin
    avatar = Column(String(255))
    phone = Column(String(20))
    class_id = Column(Integer, ForeignKey("classrooms.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
