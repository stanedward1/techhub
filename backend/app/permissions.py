"""班级权限检查模块"""
from typing import List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Classroom, Student, User


def ensure_student_operable(db: Session, student_id: int) -> Student:
    """校验学生是否可被教师/管理员操作。

    规则：
    - 学生不存在 -> 404
    - 学生已退学 -> 403（不可再对该生进行各项操作）
    - 学生所在班级已毕业 -> 403（不可再对该班所有学生进行各项操作）

    返回对应的 Student 实例，供调用方复用。
    """
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")
    if student.is_dropped_out:
        raise HTTPException(status_code=403, detail="该学生已退学，无法进行操作")
    if student.class_id:
        cls = db.get(Classroom, student.class_id)
        if cls and cls.is_graduated:
            raise HTTPException(status_code=403, detail="该学生所在班级已毕业，无法进行操作")
    return student


def ensure_class_operable(db: Session, class_id: int) -> Classroom:
    """校验班级是否可被教师/管理员操作（未毕业）。

    班级已毕业 -> 403；班级不存在 -> 404。返回 Classroom 实例。
    """
    cls = db.get(Classroom, class_id)
    if not cls:
        raise HTTPException(status_code=404, detail="班级不存在")
    if cls.is_graduated:
        raise HTTPException(status_code=403, detail="该班级已毕业，无法进行操作")
    return cls


def get_teacher_class_ids(db: Session, teacher_id: int) -> List[int]:
    """获取教师负责的班级ID列表"""
    classrooms = db.query(Classroom).filter(Classroom.teacher_id == teacher_id).all()
    return [c.id for c in classrooms]


def get_student_ids_in_class(db: Session, class_id: int) -> List[int]:
    """获取某班级的学生ID列表"""
    return [s.id for s in db.query(Student).filter(Student.class_id == class_id).all()]


def apply_student_class_filter(db: Session, user: User, q, class_id: Optional[int], model=None):
    """在班级筛选上叠加权限控制。

    返回 (query, 是否被拒绝)。teacher 访问非自己班级时返回 (q, True) 应直接返回空。

    注意：调用方必须传入 model 参数（SQLAlchemy 模型类，如 Score），
    因为函数内部需要用 model.student_id 做过滤。
    """
    if model is None:
        raise ValueError("apply_student_class_filter 需要传入 model 参数")
    if user.role != "admin":
        if class_id and not is_teacher_class_owner(db, user.id, class_id):
            return q, True
        class_ids = get_teacher_class_ids(db, user.id)
        if class_ids:
            student_ids = [s.id for s in db.query(Student).filter(Student.class_id.in_(class_ids)).all()]
            q = q.filter(model.student_id.in_(student_ids))
        else:
            return q.filter(False), False
    if class_id:
        student_ids = get_student_ids_in_class(db, class_id)
        q = q.filter(model.student_id.in_(student_ids))
    return q, False


def is_teacher_class_owner(db: Session, teacher_id: int, class_id: int) -> bool:
    """检查教师是否是某班级的班主任"""
    classroom = db.query(Classroom).filter(
        Classroom.id == class_id,
        Classroom.teacher_id == teacher_id
    ).first()
    return classroom is not None


def is_student_in_teacher_classes(db: Session, teacher_id: int, student_id: int) -> bool:
    """检查学生是否在教师负责的班级中"""
    student = db.query(Student).filter(Student.id == student_id).first()
    if not student or not student.class_id:
        return False
    return is_teacher_class_owner(db, teacher_id, student.class_id)


def filter_classrooms_by_teacher(db: Session, teacher_id: int, is_admin: bool):
    """根据教师身份过滤班级查询"""
    query = db.query(Classroom)
    if not is_admin:
        query = query.filter(Classroom.teacher_id == teacher_id)
    return query.order_by(Classroom.id)


def filter_students_by_teacher(db: Session, teacher_id: int, is_admin: bool):
    """根据教师身份过滤学生查询"""
    query = db.query(Student)
    if not is_admin:
        # 获取教师负责的班级ID列表
        class_ids = get_teacher_class_ids(db, teacher_id)
        if class_ids:
            query = query.filter(Student.class_id.in_(class_ids))
        else:
            # 教师没有负责任何班级，返回空查询
            query = query.filter(False)
    return query.order_by(Student.id)
