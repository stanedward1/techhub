"""学生考勤点名。"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.audit import audit
from app.database import get_db
from app.deps import get_current_user
from app.models import Attendance, Student, User
from app.permissions import ensure_class_operable, is_teacher_class_owner

router = APIRouter(tags=["考勤"])

ATTENDANCE_STATUS = ("出勤", "缺勤", "请假", "迟到")


@router.get("/api/attendance")
def list_attendance(
    class_id: int,
    date: str,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """查询某班级某日的考勤：返回该班在籍学生及其状态（未点名默认出勤）。"""
    if user.role != "admin" and not is_teacher_class_owner(db, user.id, class_id):
        raise HTTPException(status_code=403, detail="无权查看该班级考勤")

    students = (
        db.query(Student)
        .filter(Student.class_id == class_id, Student.is_dropped_out.is_(False))
        .order_by(Student.id)
        .all()
    )
    records = (
        db.query(Attendance)
        .filter(Attendance.class_id == class_id, Attendance.date == date)
        .all()
    )
    record_map = {r.student_id: r.status for r in records}

    items = [
        {
            "student_id": s.id,
            "name": s.name,
            "student_no": s.student_no,
            "status": record_map.get(s.id, "出勤"),
        }
        for s in students
    ]
    return {"items": items, "total": len(items), "class_id": class_id, "date": date}


@router.post("/api/attendance/checkin")
def checkin(payload: dict, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """批量提交点名结果（存在则更新，不存在则新增）。"""
    class_id = payload.get("class_id")
    date = (payload.get("date") or "").strip()
    records = payload.get("records") or []
    if not class_id or not date or not records:
        raise HTTPException(status_code=400, detail="请提供班级、日期和点名记录")

    # 毕业班级不可再点名
    ensure_class_operable(db, class_id)
    if user.role != "admin" and not is_teacher_class_owner(db, user.id, class_id):
        raise HTTPException(status_code=403, detail="无权为该班级点名")

    saved = 0
    for r in records:
        student_id = r.get("student_id")
        status = r.get("status", "出勤")
        if status not in ATTENDANCE_STATUS:
            continue
        # 仅接受本班在籍学生
        student = db.get(Student, student_id)
        if not student or student.class_id != class_id or student.is_dropped_out:
            continue

        existing = (
            db.query(Attendance)
            .filter(
                Attendance.class_id == class_id,
                Attendance.student_id == student_id,
                Attendance.date == date,
            )
            .first()
        )
        if existing:
            existing.status = status
        else:
            db.add(Attendance(class_id=class_id, student_id=student_id, date=date, status=status))
        saved += 1

    audit(db, user, "attendance_checkin", target=f"班级#{class_id} {date} 考勤点名", detail=f"记录 {saved} 条")
    db.commit()
    return {"ok": True, "count": saved}
