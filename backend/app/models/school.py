from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class School(Base):
    __tablename__ = "schools"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    code = Column(String(50), nullable=False, unique=True)
    address = Column(String(255))
    phone = Column(String(20))
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Classroom(Base):
    __tablename__ = "classrooms"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"))
    name = Column(String(100), nullable=False)
    code = Column(String(50), nullable=False, unique=True)
    major = Column(String(100))
    grade = Column(String(50))
    teacher_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Student(Base):
    __tablename__ = "students"

    id = Column(Integer, primary_key=True, index=True)
    school_id = Column(Integer, ForeignKey("schools.id"), nullable=True)
    class_id = Column(Integer, ForeignKey("classrooms.id"), nullable=True)
    name = Column(String(50), nullable=False)
    gender = Column(String(10), default="男")
    birth_date = Column(String(50))
    student_no = Column(String(50), unique=True, nullable=False, index=True)
    major = Column(String(100))
    parent_name = Column(String(50))
    parent_phone = Column(String(20))
    student_type = Column(String(20), default="day")  # day 通学生 / boarding 寄宿生
    avatar = Column(String(255))
    status = Column(String(20), default="active")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
