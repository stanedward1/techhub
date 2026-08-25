from io import BytesIO
import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_teacher, get_current_user
from app.audit import audit
from app.models import Classroom, School, Student, StudentBoardHistory, User
from app.security import hash_password
from app.utils import to_dict
from app.permissions import (
    get_teacher_class_ids,
    is_teacher_class_owner,
    is_student_in_teacher_classes,
    filter_classrooms_by_teacher,
    filter_students_by_teacher,
)

router = APIRouter(tags=["基础数据"])

admin_dep = require_teacher  # 教师/管理员均可管理基础数据


def _student_out(db: Session, s: Student) -> dict:
    d = to_dict(s)
    cls = db.get(Classroom, s.class_id) if s.class_id else None
    d["class_name"] = cls.name if cls else None
    # 附加学生头像（从 User 表获取）
    user = (
        db.query(User)
        .filter(User.role == "student", User.class_id == s.class_id, User.name == s.name)
        .first()
    )
    d["avatar"] = user.avatar if user else None
    return d


# ---------------- 学校 ----------------
@router.get("/api/schools")
def list_schools(_=Depends(admin_dep), db: Session = Depends(get_db)):
    rows = db.query(School).order_by(School.id).all()
    return {"items": [to_dict(s) for s in rows], "total": len(rows)}


@router.post("/api/schools")
def create_school(payload: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 只有管理员可以创建学校
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以创建学校")
    name = (payload.get("name") or "").strip()
    code = (payload.get("code") or "").strip()
    if not name or not code:
        raise HTTPException(status_code=400, detail="学校名称和代码不能为空")
    s = School(name=name, code=code, address=payload.get("address"), phone=payload.get("phone"))
    db.add(s)
    audit(db, user, "create_school", target=f"新增学校")
    db.commit()
    db.refresh(s)
    return to_dict(s)


@router.put("/api/schools/{school_id}")
def update_school(school_id: int, payload: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 只有管理员可以修改学校
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以修改学校")
    s = db.get(School, school_id)
    if not s:
        raise HTTPException(status_code=404, detail="学校不存在")
    for f in ("name", "code", "address", "phone"):
        if f in payload and payload[f] is not None:
            setattr(s, f, payload[f])
    audit(db, user, "update_school", target=f"学校#{school_id}")
    db.commit()
    return to_dict(s)


@router.delete("/api/schools/{school_id}")
def delete_school(school_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 只有管理员可以删除学校
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以删除学校")
    s = db.get(School, school_id)
    if s:
        db.delete(s)
        audit(db, user, "delete_school", target=f"学校#{school_id}")
        db.commit()
    return {"ok": True}


# ---------------- 班级 ----------------
@router.get("/api/classrooms")
def list_classrooms(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 管理员看所有班级，教师只看自己负责的班级
    is_admin = user.role == "admin"
    query = filter_classrooms_by_teacher(db, user.id, is_admin)
    rows = query.all()
    items = []
    for c in rows:
        d = to_dict(c)
        # 附加班主任姓名
        teacher = db.get(User, c.teacher_id) if c.teacher_id else None
        d["teacher_name"] = teacher.name if teacher else None
        items.append(d)
    return {"items": items, "total": len(items)}


@router.post("/api/classrooms")
def create_classroom(payload: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 只有管理员可以创建班级
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以创建班级")
    name = (payload.get("name") or "").strip()
    code = (payload.get("code") or "").strip()
    if not name or not code:
        raise HTTPException(status_code=400, detail="班级名称和代码不能为空")
    if db.query(Classroom).filter(Classroom.code == code).first():
        raise HTTPException(status_code=400, detail="班级代码已存在")
    c = Classroom(
        school_id=payload.get("school_id"),
        name=name,
        code=code,
        major=payload.get("major"),
        grade=payload.get("grade"),
        teacher_id=payload.get("teacher_id"),
    )
    db.add(c)
    audit(db, user, "create_classroom", target=f"新增班级")
    db.commit()
    db.refresh(c)
    return to_dict(c)


@router.put("/api/classrooms/{class_id}")
def update_classroom(class_id: int, payload: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    c = db.get(Classroom, class_id)
    if not c:
        raise HTTPException(status_code=404, detail="班级不存在")
    # 教师只能修改自己负责的班级
    if user.role != "admin" and c.teacher_id != user.id:
        raise HTTPException(status_code=403, detail="无权修改该班级")
    # 教师不能修改班级对应的教师（teacher_id 仅管理员可编辑）
    if user.role != "admin" and "teacher_id" in payload and payload["teacher_id"] is not None:
        raise HTTPException(status_code=403, detail="教师无权修改班级对应的教师")
    # 管理员修改 teacher_id 时校验目标必须是教师角色
    if user.role == "admin" and "teacher_id" in payload and payload["teacher_id"] is not None:
        t = db.get(User, payload["teacher_id"])
        if not t or t.role != "teacher":
            raise HTTPException(status_code=400, detail="所选教师不存在或不是教师角色")
    for f in ("name", "code", "major", "grade", "teacher_id"):
        if f in payload and payload[f] is not None:
            setattr(c, f, payload[f])
    audit(db, user, "update_classroom", target=f"班级#{class_id}")
    db.commit()
    return to_dict(c)


@router.delete("/api/classrooms/{class_id}")
def delete_classroom(class_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    # 只有管理员可以删除班级
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="只有管理员可以删除班级")
    c = db.get(Classroom, class_id)
    if c:
        db.delete(c)
        audit(db, user, "delete_classroom", target=f"班级#{class_id}")
        db.commit()
    return {"ok": True}


# ---------------- 学生 ----------------
@router.get("/api/students")
def list_students(
    class_id: int = None,
    keyword: str = "",
    page: int = 1,
    page_size: int = 20,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # 管理员看所有学生，教师只看自己负责班级的学生
    is_admin = user.role == "admin"
    query = filter_students_by_teacher(db, user.id, is_admin)
    if class_id:
        # 教师只能查看自己负责班级的学生
        if not is_admin and not is_teacher_class_owner(db, user.id, class_id):
            raise HTTPException(status_code=403, detail="无权查看该班级的学生")
        query = query.filter(Student.class_id == class_id)
    if keyword:
        query = query.filter(Student.name.contains(keyword) | Student.student_no.contains(keyword))
    total = query.count()
    rows = (
        query.order_by(Student.id)
        .offset((max(page, 1) - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": [_student_out(db, s) for s in rows], "total": total}


@router.post("/api/students")
def create_student(payload: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    name = (payload.get("name") or "").strip()
    student_no = (payload.get("student_no") or "").strip()
    class_id = payload.get("class_id")
    if not name or not student_no:
        raise HTTPException(status_code=400, detail="姓名和学号不能为空")
    # 教师只能在自己负责的班级添加学生
    if user.role != "admin" and class_id and not is_teacher_class_owner(db, user.id, class_id):
        raise HTTPException(status_code=403, detail="无权在该班级添加学生")
    if db.query(Student).filter(Student.student_no == student_no).first():
        raise HTTPException(status_code=400, detail="学号已存在")
    s = Student(
        school_id=payload.get("school_id"),
        class_id=class_id,
        name=name,
        gender=payload.get("gender", "男"),
        birth_date=payload.get("birth_date"),
        student_no=student_no,
        major=payload.get("major"),
        parent_name=payload.get("parent_name"),
        parent_phone=payload.get("parent_phone"),
        student_type=payload.get("student_type", "day"),
    )
    db.add(s)
    audit(db, user, "create_student", target=f"新增学生-{s.name} ({s.student_no})")
    db.commit()
    db.refresh(s)
    return _student_out(db, s)


@router.put("/api/students/{student_id}")
def update_student(student_id: int, payload: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.get(Student, student_id)
    if not s:
        raise HTTPException(status_code=404, detail="学生不存在")
    # 教师只能修改自己负责班级的学生
    if user.role != "admin" and not is_student_in_teacher_classes(db, user.id, student_id):
        raise HTTPException(status_code=403, detail="无权修改该学生")
    for f in ("name", "gender", "birth_date", "class_id", "major", "parent_name", "parent_phone", "student_type"):
        if f in payload and payload[f] is not None:
            # 教师不能修改学生的班级归属
            if f == "class_id" and user.role != "admin":
                raise HTTPException(status_code=403, detail="教师无权修改学生班级")
            setattr(s, f, payload[f])
    audit(db, user, "update_student", target=f"学生#{student_id}-{s.name}")
    db.commit()
    db.refresh(s)
    return _student_out(db, s)


@router.delete("/api/students/{student_id}")
def delete_student(student_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.get(Student, student_id)
    if not s:
        raise HTTPException(status_code=404, detail="学生不存在")
    # 教师只能删除自己负责班级的学生
    if user.role != "admin" and not is_student_in_teacher_classes(db, user.id, student_id):
        raise HTTPException(status_code=403, detail="无权删除该学生")
    db.delete(s)
    audit(db, user, "delete_student", target=f"学生#{student_id}")
    db.commit()
    return {"ok": True}
    items = []
    for c in rows:
        d = to_dict(c)
        d["student_count"] = db.query(Student).filter(Student.class_id == c.id).count()
        items.append(d)
    return {"items": items, "total": len(rows)}


@router.post("/api/classrooms")
def create_classroom(payload: dict, _=Depends(admin_dep), db: Session = Depends(get_db)):
    name = (payload.get("name") or "").strip()
    code = (payload.get("code") or "").strip()
    if not name or not code:
        raise HTTPException(status_code=400, detail="班级名称和代码不能为空")
    if db.query(Classroom).filter(Classroom.code == code).first():
        raise HTTPException(status_code=400, detail="班级代码已存在")
    c = Classroom(
        school_id=payload.get("school_id"),
        name=name,
        code=code,
        major=payload.get("major"),
        grade=payload.get("grade"),
        teacher_id=payload.get("teacher_id"),
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    return to_dict(c)


@router.put("/api/classrooms/{classroom_id}")
def update_classroom(classroom_id: int, payload: dict, _=Depends(admin_dep), db: Session = Depends(get_db)):
    c = db.get(Classroom, classroom_id)
    if not c:
        raise HTTPException(status_code=404, detail="班级不存在")
    for f in ("name", "code", "major", "grade", "teacher_id", "school_id"):
        if f in payload and payload[f] is not None:
            setattr(c, f, payload[f])
    db.commit()
    return to_dict(c)


@router.delete("/api/classrooms/{classroom_id}")
def delete_classroom(classroom_id: int, user=Depends(admin_dep), db: Session = Depends(get_db)):
    c = db.get(Classroom, classroom_id)
    if c:
        audit(db, user, "delete_classroom", target=f"{c.name} ({c.code})")
        db.delete(c)
        db.commit()
    return {"ok": True}


# ---------------- 学生 ----------------
@router.get("/api/students")
def list_students(
    page: int = 1,
    page_size: int = 20,
    keyword: str = "",
    class_id: int | None = None,
    _=Depends(admin_dep),
    db: Session = Depends(get_db),
):
    q = db.query(Student)
    if class_id:
        q = q.filter(Student.class_id == class_id)
    if keyword:
        q = q.filter(Student.name.contains(keyword) | Student.student_no.contains(keyword))
    total = q.count()
    rows = (
        q.order_by(Student.id)
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {"items": [_student_out(db, s) for s in rows], "total": total}


@router.post("/api/students")
def create_student(payload: dict, _=Depends(admin_dep), db: Session = Depends(get_db)):
    name = (payload.get("name") or "").strip()
    student_no = (payload.get("student_no") or "").strip()
    if not name or not student_no:
        raise HTTPException(status_code=400, detail="姓名和学号不能为空")
    if db.query(Student).filter(Student.student_no == student_no).first():
        raise HTTPException(status_code=400, detail="学号已存在")
    class_id = payload.get("class_id")
    s = Student(
        name=name,
        student_no=student_no,
        gender=payload.get("gender", "男"),
        birth_date=payload.get("birth_date"),
        class_id=class_id,
        school_id=payload.get("school_id"),
        major=payload.get("major"),
        parent_name=payload.get("parent_name"),
        parent_phone=payload.get("parent_phone"),
        student_type=payload.get("student_type", "day"),
    )
    db.add(s)
    db.flush()

    # 自动同步生成学生登录账号（班级 + 姓名，默认密码 123456）
    exists_user = (
        db.query(User)
        .filter(User.role == "student", User.class_id == class_id, User.name == name)
        .first()
    )
    if not exists_user:
        db.add(
            User(
                username=name,
                password_hash=hash_password("123456"),
                name=name,
                role="student",
                class_id=class_id,
            )
        )

    db.commit()
    db.refresh(s)
    return _student_out(db, s)


@router.put("/api/students/{student_id}")
def update_student(student_id: int, payload: dict, user=Depends(admin_dep), db: Session = Depends(get_db)):
    s = db.get(Student, student_id)
    if not s:
        raise HTTPException(status_code=404, detail="学生不存在")
    old_type = s.student_type
    for f in (
        "name", "gender", "birth_date", "class_id", "school_id", "major",
        "parent_name", "parent_phone", "student_type", "status", "student_no",
    ):
        if f in payload and payload[f] is not None:
            setattr(s, f, payload[f])
    # 记录寄宿/通学状态变更
    new_type = payload.get("student_type")
    if new_type and new_type != old_type:
        db.add(StudentBoardHistory(
            student_id=s.id,
            old_type=old_type,
            new_type=new_type,
            changed_by=user.id,
        ))
    db.commit()
    db.refresh(s)
    return _student_out(db, s)


@router.delete("/api/students/{student_id}")
def delete_student(student_id: int, user=Depends(admin_dep), db: Session = Depends(get_db)):
    s = db.get(Student, student_id)
    if s:
        audit(db, user, "delete_student", target=f"{s.name} ({s.student_no})")
        db.delete(s)
        db.commit()
    return {"ok": True}


@router.put("/api/students/{student_id}/password")
def reset_student_password(student_id: int, payload: dict, user=Depends(admin_dep), db: Session = Depends(get_db)):
    """教师重置/修改学生密码（默认 123456）。"""
    s = db.get(Student, student_id)
    if not s:
        raise HTTPException(status_code=404, detail="学生不存在")
    new_pwd = payload.get("password") or "123456"
    u = (
        db.query(User)
        .filter(User.role == "student", User.class_id == s.class_id, User.name == s.name)
        .first()
    )
    if not u:
        u = User(
            username=s.name,
            password_hash=hash_password(new_pwd),
            name=s.name,
            role="student",
            class_id=s.class_id,
        )
        db.add(u)
    else:
        u.password_hash = hash_password(new_pwd)
    audit(db, user, "reset_student_password", target=f"{s.name} ({s.student_no})")
    db.commit()
    return {"ok": True}


_AVATAR_DIR = "uploads/avatars"
_AVATAR_MAX_SIZE = 2 * 1024 * 1024
_AVATAR_ALLOWED = {".jpg", ".jpeg", ".png", ".gif", ".webp"}


@router.post("/api/students/{student_id}/avatar")
async def upload_student_avatar(
    student_id: int,
    file: UploadFile = File(...),
    user=Depends(admin_dep),
    db: Session = Depends(get_db),
):
    """教师为学生上传头像。"""
    s = db.get(Student, student_id)
    if not s:
        raise HTTPException(status_code=404, detail="学生不存在")

    original = file.filename or "avatar"
    ext = os.path.splitext(original)[1].lower()
    if ext not in _AVATAR_ALLOWED:
        raise HTTPException(status_code=400, detail=f"仅支持图片格式：{'、'.join(sorted(_AVATAR_ALLOWED))}")

    # 查找学生对应的 User
    student_user = (
        db.query(User)
        .filter(User.role == "student", User.class_id == s.class_id, User.name == s.name)
        .first()
    )
    if not student_user:
        raise HTTPException(status_code=404, detail="学生账号不存在，请先创建学生档案")

    name = f"avatar_{student_user.id}_{uuid.uuid4().hex[:8]}{ext}"
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

    if student_user.avatar:
        old_path = student_user.avatar.replace("/uploads/", "")
        if os.path.exists(old_path):
            os.remove(old_path)

    student_user.avatar = f"/uploads/avatars/{name}"
    audit(db, user, "upload_student_avatar", target=f"{s.name} ({s.student_no})")
    db.commit()
    return {"avatar": student_user.avatar}


@router.get("/api/students/board-type-stats")
def board_type_stats(class_id: int | None = None, _=Depends(admin_dep), db: Session = Depends(get_db)):
    """通学生 / 寄宿生人数对比及明细名单。"""
    q = db.query(Student)
    if class_id:
        q = q.filter(Student.class_id == class_id)
    students = q.all()
    day = [s for s in students if s.student_type == "day"]
    boarding = [s for s in students if s.student_type == "boarding"]
    return {
        "day_count": len(day),
        "boarding_count": len(boarding),
        "day": [_student_out(db, s) for s in day],
        "boarding": [_student_out(db, s) for s in boarding],
    }


def _board_label(t):
    """住宿类型 -> 中文标签。"""
    if t == "day":
        return "通学生"
    if t == "boarding":
        return "寄宿生"
    return "初始"


def _fmt_dt(dt):
    """datetime -> 展示用字符串，None 返回 None。"""
    if dt is None:
        return None
    return dt.strftime("%Y-%m-%d %H:%M:%S")


@router.get("/api/students/{student_id}/board-history")
def get_board_history(student_id: int, _=Depends(admin_dep), db: Session = Depends(get_db)):
    """获取学生寄宿/通学状态：当前状态、各时间段（含起始/结束时间）与变更日志。"""
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")

    changes = (
        db.query(StudentBoardHistory)
        .filter(StudentBoardHistory.student_id == student_id)
        .order_by(StudentBoardHistory.created_at.asc())
        .all()
    )

    # 变更日志（倒序，最新在前）
    items = []
    for r in reversed(changes):
        d = to_dict(r)
        d["old_label"] = _board_label(r.old_type)
        d["new_label"] = _board_label(r.new_type)
        d["changed_at"] = _fmt_dt(r.created_at)
        if r.changed_by:
            u = db.get(User, r.changed_by)
            d["changed_by_name"] = u.name if u else ""
        items.append(d)

    # 时间段（正序，从最早到当前，每段含起始/结束时间，最后一段 end=None 表示"至今"）
    base_start = _fmt_dt(student.created_at) or "建档"
    periods = []
    if not changes:
        periods.append({
            "type": student.student_type,
            "label": _board_label(student.student_type),
            "start": base_start,
            "end": None,
        })
    else:
        # 首段：初始类型（首次变更前）
        periods.append({
            "type": changes[0].old_type,
            "label": _board_label(changes[0].old_type),
            "start": base_start,
            "end": _fmt_dt(changes[0].created_at),
        })
        for i, r in enumerate(changes):
            end = _fmt_dt(changes[i + 1].created_at) if i + 1 < len(changes) else None
            periods.append({
                "type": r.new_type,
                "label": _board_label(r.new_type),
                "start": _fmt_dt(r.created_at),
                "end": end,
            })

    # 当前状态
    current = {
        "type": student.student_type,
        "label": _board_label(student.student_type),
        "since": _fmt_dt(changes[-1].created_at) if changes else base_start,
    }

    return {"current": current, "periods": periods, "items": items}


@router.get("/api/students/export")
def export_students(class_id: int | None = None, _=Depends(admin_dep), db: Session = Depends(get_db)):
    q = db.query(Student)
    if class_id:
        q = q.filter(Student.class_id == class_id)
    rows = q.order_by(Student.id).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "学生花名册"
    headers = ["学号", "姓名", "性别", "出生日期", "专业", "家长姓名", "家长电话", "类型"]
    ws.append(headers)
    for s in rows:
        ws.append(
            [
                s.student_no,
                s.name,
                s.gender,
                s.birth_date,
                s.major,
                s.parent_name,
                s.parent_phone,
                "通学生" if s.student_type == "day" else "寄宿生",
            ]
        )
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=students.xlsx"},
    )
