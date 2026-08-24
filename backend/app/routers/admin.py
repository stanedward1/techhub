from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.audit import audit
from app.database import get_db
from app.deps import get_current_user, require_teacher
from app.models import (
    Assignment,
    Classroom,
    Communication,
    Exam,
    Leave,
    Resource,
    Score,
    Setting,
    Student,
    Submission,
    User,
    WorkLog,
)
from app.security import hash_password
from app.utils import to_dict

router = APIRouter(tags=["系统管理"])

admin_dep = require_teacher


def _user_out(db: Session, u: User) -> dict:
    d = to_dict(u)
    d.pop("password_hash", None)
    cls = db.get(Classroom, u.class_id) if u.class_id else None
    d["class_name"] = cls.name if cls else None
    return d


# ---------------- 账号管理 ----------------
@router.get("/api/admin/users")
def list_users(role: str = "", keyword: str = "", _=Depends(admin_dep), db: Session = Depends(get_db)):
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    if keyword:
        q = q.filter(User.name.contains(keyword) | User.username.contains(keyword))
    rows = q.order_by(User.id).all()
    return {"items": [_user_out(db, u) for u in rows], "total": len(rows)}


@router.post("/api/admin/users")
def create_user(payload: dict, _=Depends(admin_dep), db: Session = Depends(get_db)):
    username = (payload.get("username") or "").strip()
    password = payload.get("password") or "123456"
    name = (payload.get("name") or "").strip()
    role = payload.get("role", "teacher")
    if not username or not name:
        raise HTTPException(status_code=400, detail="用户名和姓名不能为空")
    if role not in ("teacher", "admin", "student"):
        raise HTTPException(status_code=400, detail="角色不合法")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="用户名已存在")
    u = User(
        username=username,
        password_hash=hash_password(password),
        name=name,
        role=role,
        phone=payload.get("phone"),
        class_id=payload.get("class_id") if role == "student" else None,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return _user_out(db, u)


@router.put("/api/admin/users/{user_id}")
def update_user(user_id: int, payload: dict, _=Depends(admin_dep), db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    for f in ("name", "phone", "role", "class_id"):
        if f in payload and payload[f] is not None:
            setattr(u, f, payload[f])
    db.commit()
    db.refresh(u)
    return _user_out(db, u)


@router.put("/api/admin/users/{user_id}/password")
def reset_password(user_id: int, payload: dict, user=Depends(admin_dep), db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    new_pwd = payload.get("password") or "123456"
    u.password_hash = hash_password(new_pwd)
    audit(db, user, "reset_password", target=f"{u.username} ({u.name})")
    db.commit()
    return {"ok": True}


@router.delete("/api/admin/users/{user_id}")
def delete_user(user_id: int, user=Depends(admin_dep), db: Session = Depends(get_db)):
    u = db.get(User, user_id)
    if not u:
        raise HTTPException(status_code=404, detail="用户不存在")
    if u.role == "admin" and db.query(User).filter(User.role == "admin").count() <= 1:
        raise HTTPException(status_code=400, detail="至少保留一个管理员账号")
    audit(db, user, "delete_user", target=f"{u.username} ({u.name})", detail=f"role={u.role}")
    db.delete(u)
    db.commit()
    return {"ok": True}


# ---------------- 系统设置 ----------------
@router.get("/api/settings")
def get_settings(_=Depends(admin_dep), db: Session = Depends(get_db)):
    rows = db.query(Setting).all()
    return {"items": [to_dict(s) for s in rows]}


@router.put("/api/settings/{key}")
def set_setting(key: str, payload: dict, _=Depends(admin_dep), db: Session = Depends(get_db)):
    s = db.query(Setting).filter(Setting.key == key).first()
    if not s:
        s = Setting(key=key, value=payload.get("value", ""))
        db.add(s)
    else:
        s.value = payload.get("value", s.value)
    db.commit()
    return {"ok": True}


@router.post("/api/settings/upgrade-grade")
def upgrade_grade(user=Depends(admin_dep), db: Session = Depends(get_db)):
    """年级升级：一年级→二年级……入学年份递增。"""
    classes = db.query(Classroom).all()
    order = {"一年级": 1, "二年级": 2, "三年级": 3, "四年级": 4, "五年级": 5, "六年级": 6}
    reverse = {v: k for k, v in order.items()}
    upgraded = 0
    for c in classes:
        cur = order.get(c.grade or "")
        if cur and cur < 6:
            c.grade = reverse[cur + 1]
            upgraded += 1
    audit(db, user, "upgrade_grade", detail=f"升级班级数={upgraded}")
    db.commit()
    return {"upgraded": upgraded}


# ---------------- 看板统计 ----------------
@router.get("/api/stats/dashboard")
def dashboard(_=Depends(admin_dep), db: Session = Depends(get_db)):
    student_count = db.query(Student).count()
    class_count = db.query(Classroom).count()
    assignment_count = db.query(Assignment).count()
    submission_count = db.query(Submission).count()
    resource_count = db.query(Resource).count()
    exam_count = db.query(Exam).count()
    leave_count = db.query(Leave).count()
    comm_count = db.query(Communication).count()

    today = datetime.now().strftime("%Y-%m-%d")
    today_leaves = db.query(Leave).filter(Leave.created_at >= today).count()

    # 近 7 天请假详情（含人员姓名、类型、时长）
    trend = []
    leave_details = []
    for i in range(6, -1, -1):
        day = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        day_leaves = (
            db.query(Leave)
            .filter(Leave.start_date == day)
            .all()
        )
        items = []
        for l in day_leaves:
            stu = db.get(Student, l.student_id)
            duration = 1
            if l.start_date and l.end_date:
                try:
                    s = datetime.strptime(l.start_date, "%Y-%m-%d")
                    e = datetime.strptime(l.end_date, "%Y-%m-%d")
                    duration = (e - s).days + 1
                except ValueError:
                    pass
            items.append({
                "name": stu.name if stu else "未知",
                "reason": l.reason or "未填写",
                "duration": duration,
                "start": l.start_date or "",
                "end": l.end_date or "",
            })
        trend.append({"date": day[5:], "count": len(day_leaves)})
        leave_details.append({"date": day[5:], "count": len(day_leaves), "items": items})

    # 成绩分布（含百分比）
    scores = [s.score for s in db.query(Score).all()]
    total_scores = len(scores) if scores else 1
    dist = {
        "优秀(90+)": {"count": sum(1 for x in scores if x >= 90), "percent": round(sum(1 for x in scores if x >= 90) / total_scores * 100, 1)},
        "良好(75-89)": {"count": sum(1 for x in scores if 75 <= x < 90), "percent": round(sum(1 for x in scores if 75 <= x < 90) / total_scores * 100, 1)},
        "中等(60-74)": {"count": sum(1 for x in scores if 60 <= x < 75), "percent": round(sum(1 for x in scores if 60 <= x < 75) / total_scores * 100, 1)},
        "待提高(<60)": {"count": sum(1 for x in scores if x < 60), "percent": round(sum(1 for x in scores if x < 60) / total_scores * 100, 1)},
    }

    # 最近动态（请假 + 工作日志）
    recent = []
    for l in db.query(Leave).order_by(Leave.id.desc()).limit(5).all():
        stu = db.get(Student, l.student_id)
        recent.append(
            {
                "type": "请假",
                "text": f"{stu.name if stu else '未知'} 请假：{l.reason or '未填写'}",
                "time": l.created_at.strftime("%Y-%m-%d %H:%M") if l.created_at else "",
            }
        )
    for w in db.query(WorkLog).order_by(WorkLog.id.desc()).limit(5).all():
        recent.append(
            {
                "type": "日志",
                "text": (w.content or "")[:30],
                "time": w.date or "",
            }
        )

    return {
        "counts": {
            "student": student_count,
            "class": class_count,
            "assignment": assignment_count,
            "submission": submission_count,
            "resource": resource_count,
            "exam": exam_count,
            "leave": leave_count,
            "communication": comm_count,
            "today_leave": today_leaves,
        },
        "leave_trend": trend,
        "leave_details": leave_details,
        "score_dist": dist,
        "recent": recent,
    }
