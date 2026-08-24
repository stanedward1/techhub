import json
import os
from io import BytesIO

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from openpyxl import Workbook, load_workbook
from sqlalchemy.orm import Session

from app.database import get_db
from app.deps import require_teacher
from app.models import (
    Classroom,
    Communication,
    Exam,
    ImportHistory,
    Leave,
    Point,
    Resource,
    Score,
    Seat,
    Student,
    StudentProfileTag,
    User,
    WeeklyReport,
)
from app.audit import attach_student, serialize_list_with_students
from app.config import settings
from app.utils import safe_filename, to_dict
import uuid

router = APIRouter(tags=["教师工作台"])

dep = require_teacher


# ---------------- 成绩 ----------------
@router.get("/api/scores")
def list_scores(
    page: int = 1,
    page_size: int = 20,
    student_id: int | None = None,
    subject: str = "",
    _=Depends(dep),
    db: Session = Depends(get_db),
):
    q = db.query(Score)
    if student_id:
        q = q.filter(Score.student_id == student_id)
    if subject:
        q = q.filter(Score.subject == subject)
    total = q.count()
    rows = q.order_by(Score.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = serialize_list_with_students(db, rows)
    return {"items": items, "total": total}


@router.post("/api/scores")
def create_score(payload: dict, _=Depends(dep), db: Session = Depends(get_db)):
    if not payload.get("student_id") or payload.get("score") is None:
        raise HTTPException(status_code=400, detail="请选择学生并填写成绩")
    s = Score(
        student_id=payload["student_id"],
        subject=payload.get("subject", "未分类"),
        score=payload["score"],
        exam_name=payload.get("exam_name"),
    )
    db.add(s)
    db.commit()
    db.refresh(s)
    return attach_student(db, to_dict(s), s.student_id)


@router.put("/api/scores/{score_id}")
def update_score(score_id: int, payload: dict, _=Depends(dep), db: Session = Depends(get_db)):
    s = db.get(Score, score_id)
    if not s:
        raise HTTPException(status_code=404, detail="记录不存在")
    for f in ("student_id", "subject", "score", "exam_name"):
        if f in payload and payload[f] is not None:
            setattr(s, f, payload[f])
    db.commit()
    db.refresh(s)
    return attach_student(db, to_dict(s), s.student_id)


@router.delete("/api/scores/{score_id}")
def delete_score(score_id: int, _=Depends(dep), db: Session = Depends(get_db)):
    s = db.get(Score, score_id)
    if s:
        db.delete(s)
        db.commit()
    return {"ok": True}


@router.get("/api/scores/export")
def export_scores(student_id: int | None = None, _=Depends(dep), db: Session = Depends(get_db)):
    q = db.query(Score)
    if student_id:
        q = q.filter(Score.student_id == student_id)
    rows = q.order_by(Score.student_id).all()
    wb = Workbook()
    ws = wb.active
    ws.title = "成绩单"
    ws.append(["学号", "姓名", "科目", "成绩", "考试名称"])
    for s in rows:
        stu = db.get(Student, s.student_id)
        ws.append([stu.student_no if stu else "", stu.name if stu else "", s.subject, s.score, s.exam_name or ""])
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=scores.xlsx"},
    )


# ---------------- 请假/考勤 ----------------
@router.get("/api/leaves")
def list_leaves(
    page: int = 1,
    page_size: int = 20,
    student_id: int | None = None,
    status: str = "",
    _=Depends(dep),
    db: Session = Depends(get_db),
):
    q = db.query(Leave)
    if student_id:
        q = q.filter(Leave.student_id == student_id)
    if status:
        q = q.filter(Leave.status == status)
    total = q.count()
    rows = q.order_by(Leave.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": serialize_list_with_students(db, rows), "total": total}


@router.post("/api/leaves")
def create_leave(payload: dict, _=Depends(dep), db: Session = Depends(get_db)):
    if not payload.get("student_id"):
        raise HTTPException(status_code=400, detail="请选择学生")
    x = Leave(
        student_id=payload["student_id"],
        reason=payload.get("reason"),
        start_date=payload.get("start_date"),
        end_date=payload.get("end_date"),
        status=payload.get("status", "登记"),
        image=payload.get("image"),
    )
    db.add(x)
    db.commit()
    db.refresh(x)
    return attach_student(db, to_dict(x), x.student_id)


@router.put("/api/leaves/{leave_id}")
def update_leave(leave_id: int, payload: dict, _=Depends(dep), db: Session = Depends(get_db)):
    x = db.get(Leave, leave_id)
    if not x:
        raise HTTPException(status_code=404, detail="记录不存在")
    for f in ("reason", "start_date", "end_date", "status", "image"):
        if f in payload and payload[f] is not None:
            setattr(x, f, payload[f])
    db.commit()
    db.refresh(x)
    return attach_student(db, to_dict(x), x.student_id)


@router.delete("/api/leaves/{leave_id}")
def delete_leave(leave_id: int, _=Depends(dep), db: Session = Depends(get_db)):
    x = db.get(Leave, leave_id)
    if x:
        db.delete(x)
        db.commit()
    return {"ok": True}


# ---------------- 积分 ----------------
@router.get("/api/points")
def list_points(page: int = 1, page_size: int = 20, student_id: int | None = None, _=Depends(dep), db: Session = Depends(get_db)):
    q = db.query(Point)
    if student_id:
        q = q.filter(Point.student_id == student_id)
    total = q.count()
    rows = q.order_by(Point.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": serialize_list_with_students(db, rows), "total": total}


@router.post("/api/points")
def create_point(payload: dict, _=Depends(dep), db: Session = Depends(get_db)):
    if not payload.get("student_id") or payload.get("points") is None:
        raise HTTPException(status_code=400, detail="请选择学生并填写积分")
    x = Point(
        student_id=payload["student_id"],
        points=payload["points"],
        reason=payload.get("reason"),
    )
    db.add(x)
    db.commit()
    db.refresh(x)
    return attach_student(db, to_dict(x), x.student_id)


@router.delete("/api/points/{point_id}")
def delete_point(point_id: int, _=Depends(dep), db: Session = Depends(get_db)):
    x = db.get(Point, point_id)
    if x:
        db.delete(x)
        db.commit()
    return {"ok": True}


# ---------------- 家校沟通 ----------------
@router.get("/api/communications")
def list_communications(page: int = 1, page_size: int = 20, student_id: int | None = None, _=Depends(dep), db: Session = Depends(get_db)):
    q = db.query(Communication)
    if student_id:
        q = q.filter(Communication.student_id == student_id)
    total = q.count()
    rows = q.order_by(Communication.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return {"items": serialize_list_with_students(db, rows), "total": total}


@router.post("/api/communications")
def create_communication(payload: dict, _=Depends(dep), db: Session = Depends(get_db)):
    if not payload.get("student_id"):
        raise HTTPException(status_code=400, detail="请选择学生")
    x = Communication(
        student_id=payload["student_id"],
        method=payload.get("method", "电话"),
        content=payload.get("content"),
        feedback=payload.get("feedback"),
    )
    db.add(x)
    db.commit()
    db.refresh(x)
    return attach_student(db, to_dict(x), x.student_id)


@router.delete("/api/communications/{communication_id}")
def delete_communication(communication_id: int, _=Depends(dep), db: Session = Depends(get_db)):
    x = db.get(Communication, communication_id)
    if x:
        db.delete(x)
        db.commit()
    return {"ok": True}


# ---------------- 资源 ----------------
@router.get("/api/resources")
def list_resources(keyword: str = "", _=Depends(dep), db: Session = Depends(get_db)):
    q = db.query(Resource)
    if keyword:
        q = q.filter(Resource.name.contains(keyword))
    rows = q.order_by(Resource.id.desc()).all()
    return {"items": [to_dict(x) for x in rows], "total": len(rows)}


@router.post("/api/resources")
def create_resource(payload: dict, _=Depends(dep), db: Session = Depends(get_db)):
    name = (payload.get("name") or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="资源名称不能为空")
    x = Resource(
        name=name,
        category=payload.get("category", "其他"),
        filename=payload.get("filename"),
        filepath=payload.get("filepath"),
    )
    db.add(x)
    db.commit()
    db.refresh(x)
    return to_dict(x)


@router.delete("/api/resources/{resource_id}")
def delete_resource(resource_id: int, _=Depends(dep), db: Session = Depends(get_db)):
    x = db.get(Resource, resource_id)
    if x:
        db.delete(x)
        db.commit()
    return {"ok": True}


# ---------------- 试卷（文件上传管理） ----------------
@router.get("/api/exams")
def list_exams(keyword: str = "", _=Depends(dep), db: Session = Depends(get_db)):
    q = db.query(Exam)
    if keyword:
        q = q.filter(Exam.title.contains(keyword))
    rows = q.order_by(Exam.id.desc()).all()
    return {"items": [to_dict(x) for x in rows], "total": len(rows)}


@router.post("/api/exams/upload")
async def upload_exam(
    title: str = "未命名试卷",
    exam_type: str = "单元测验",
    file: UploadFile = File(None),
    _=Depends(dep),
    db: Session = Depends(get_db),
):
    """上传试卷文件：支持 .docx / .pdf / .doc 等格式。"""
    if not file:
        raise HTTPException(status_code=400, detail="请选择试卷文件")

    original = file.filename or "exam"
    ext = os.path.splitext(original)[1].lower()
    allowed = {".pdf", ".doc", ".docx"}
    if ext not in allowed:
        raise HTTPException(status_code=400, detail=f"仅支持 PDF/Word 格式，当前文件类型：{ext}")

    name = safe_filename(os.path.splitext(original)[0]) + "_" + uuid.uuid4().hex[:8] + ext
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    dest = os.path.join(settings.UPLOAD_DIR, name)

    size = 0
    chunk_size = 1024 * 1024
    try:
        with open(dest, "wb") as f:
            while True:
                chunk = await file.read(chunk_size)
                if not chunk:
                    break
                size += len(chunk)
                if size > settings.MAX_UPLOAD_SIZE:
                    f.close()
                    os.remove(dest)
                    raise HTTPException(status_code=413, detail=f"文件过大，最大 {settings.MAX_UPLOAD_SIZE // (1024*1024)}MB")
                f.write(chunk)
    except HTTPException:
        raise
    except Exception:
        if os.path.exists(dest):
            os.remove(dest)
        raise

    x = Exam(
        title=title.strip() or "未命名试卷",
        exam_type=exam_type,
        filename=original,
        filepath=name,
        filesize=size,
        filetype=ext,
    )
    db.add(x)
    db.commit()
    db.refresh(x)
    return to_dict(x)


@router.put("/api/exams/{exam_id}")
def update_exam(exam_id: int, payload: dict, _=Depends(dep), db: Session = Depends(get_db)):
    x = db.get(Exam, exam_id)
    if not x:
        raise HTTPException(status_code=404, detail="试卷不存在")
    for f in ("title", "exam_type"):
        if f in payload and payload[f] is not None:
            setattr(x, f, payload[f])
    db.commit()
    db.refresh(x)
    return to_dict(x)


@router.get("/api/exams/{exam_id}/download")
def download_exam(exam_id: int, _=Depends(dep), db: Session = Depends(get_db)):
    x = db.get(Exam, exam_id)
    if not x or not x.filepath:
        raise HTTPException(status_code=404, detail="文件不存在")
    file_path = os.path.join(settings.UPLOAD_DIR, x.filepath)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="文件不存在")
    return FileResponse(file_path, filename=x.filename or x.filepath, media_type="application/octet-stream")


@router.delete("/api/exams/{exam_id}")
def delete_exam(exam_id: int, _=Depends(dep), db: Session = Depends(get_db)):
    x = db.get(Exam, exam_id)
    if x:
        # 删除关联文件
        if x.filepath:
            fp = os.path.join(settings.UPLOAD_DIR, x.filepath)
            if os.path.exists(fp):
                os.remove(fp)
        db.delete(x)
        db.commit()
    return {"ok": True}


# ---------------- 座位表 ----------------
@router.get("/api/seats")
def get_seat(class_id: int, _=Depends(dep), db: Session = Depends(get_db)):
    s = db.query(Seat).filter(Seat.class_id == class_id).first()
    if not s:
        return {"layout": [], "columns": 6}
    return {"layout": json.loads(s.layout) if s.layout else [], "columns": s.columns}


@router.put("/api/seats")
def save_seat(payload: dict, _=Depends(dep), db: Session = Depends(get_db)):
    class_id = payload.get("class_id")
    if not class_id:
        raise HTTPException(status_code=400, detail="缺少班级")
    s = db.query(Seat).filter(Seat.class_id == class_id).first()
    if not s:
        s = Seat(class_id=class_id)
        db.add(s)
    s.layout = json.dumps(payload.get("layout", []), ensure_ascii=False)
    s.columns = payload.get("columns", 6)
    db.commit()
    return {"ok": True}


# ---------------- 数据导入 ----------------
_EXCEL_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _validate_student_row(row_data: dict, row_num: int) -> list[str]:
    """校验学生导入行数据，返回错误列表。"""
    errors = []
    if not row_data.get("name", "").strip():
        errors.append(f"第{row_num}行：姓名不能为空")
    if not row_data.get("student_no", "").strip():
        errors.append(f"第{row_num}行：学号不能为空")
    if not row_data.get("class_name", "").strip():
        errors.append(f"第{row_num}行：班级不能为空")
    return errors


def _validate_score_row(row_data: dict, row_num: int) -> list[str]:
    """校验成绩导入行数据，返回错误列表。"""
    errors = []
    if not row_data.get("student_no", "").strip():
        errors.append(f"第{row_num}行：学号不能为空")
    if not row_data.get("subject", "").strip():
        errors.append(f"第{row_num}行：科目不能为空")
    try:
        float(row_data.get("score", 0))
    except (ValueError, TypeError):
        errors.append(f"第{row_num}行：成绩必须是数字")
    return errors


@router.get("/api/students/template")
def download_student_template(_=Depends(dep)):
    """下载学生导入模板。"""
    wb = Workbook()
    ws = wb.active
    ws.title = "学生导入模板"
    ws.append(["学号", "姓名", "性别", "班级", "专业", "出生日期", "家长姓名", "家长电话", "学生类型"])
    ws.append(["2024001", "张三", "男", "2024级1班", "计算机", "2008-05-12", "张父", "13800000000", "通学生"])
    # 设置列宽
    for col, w in enumerate([12, 10, 6, 14, 14, 12, 10, 14, 10], 1):
        ws.column_dimensions[ws.cell(1, col).column_letter].width = w
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(buf, media_type=_EXCEL_MIME, headers={"Content-Disposition": "attachment; filename=student_template.xlsx"})


@router.get("/api/scores/template")
def download_score_template(_=Depends(dep)):
    """下载成绩导入模板。"""
    wb = Workbook()
    ws = wb.active
    ws.title = "成绩导入模板"
    ws.append(["学号", "姓名", "科目", "成绩", "考试名称"])
    ws.append(["2024001", "张三", "语文", "85", "期中考试"])
    for col, w in enumerate([12, 10, 10, 8, 14], 1):
        ws.column_dimensions[ws.cell(1, col).column_letter].width = w
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    return StreamingResponse(buf, media_type=_EXCEL_MIME, headers={"Content-Disposition": "attachment; filename=score_template.xlsx"})


@router.post("/api/students/import")
async def import_students(
    file: UploadFile = File(...),
    user=Depends(dep),
    db: Session = Depends(get_db),
):
    """批量导入学生数据。"""
    ext = os.path.splitext(file.filename or "" )[1].lower()
    if ext not in {".xlsx", ".xls"}:
        raise HTTPException(status_code=400, detail="仅支持 .xlsx / .xls 格式")

    contents = await file.read()
    wb = load_workbook(BytesIO(contents))
    ws = wb.active

    rows = list(ws.iter_rows(min_row=2, values_only=True))
    if not rows:
        raise HTTPException(status_code=400, detail="文件中没有数据行")

    all_errors = []
    success = 0
    total = 0

    # 预加载班级映射：class_name -> class_id
    classrooms = {c.name: c.id for c in db.query(Classroom).all()}

    for row_num, row in enumerate(rows, start=2):
        if not any(row):
            continue
        total += 1
        data = {
            "student_no": str(row[0] or "").strip(),
            "name": str(row[1] or "").strip(),
            "gender": str(row[2] or "").strip() or "男",
            "class_name": str(row[3] or "").strip(),
            "major": str(row[4] or "").strip(),
            "birth_date": str(row[5] or "").strip(),
            "parent_name": str(row[6] or "").strip(),
            "parent_phone": str(row[7] or "").strip(),
            "student_type": str(row[8] or "").strip() or "day",
        }
        data["student_type"] = data["student_type"] if data["student_type"] in ("day", "boarding") else "day"

        errors = _validate_student_row(data, row_num)
        if errors:
            all_errors.extend(errors)
            continue

        # 检查学号是否重复
        if db.query(Student).filter(Student.student_no == data["student_no"]).first():
            all_errors.append(f"第{row_num}行：学号 {data['student_no']} 已存在")
            continue

        class_id = classrooms.get(data["class_name"])
        if not class_id:
            all_errors.append(f"第{row_num}行：班级「{data['class_name']}」不存在")
            continue

        try:
            s = Student(
                student_no=data["student_no"],
                name=data["name"],
                gender=data["gender"],
                class_id=class_id,
                major=data["major"],
                birth_date=data["birth_date"],
                parent_name=data["parent_name"],
                parent_phone=data["parent_phone"],
                student_type=data["student_type"],
            )
            db.add(s)
            db.flush()
            # 自动创建学生账号
            from app.security import hash_password
            exists_user = db.query(User).filter(
                User.role == "student", User.class_id == class_id, User.name == data["name"]
            ).first()
            if not exists_user:
                db.add(User(
                    username=data["name"],
                    password_hash=hash_password("123456"),
                    name=data["name"],
                    role="student",
                    class_id=class_id,
                ))
            success += 1
        except Exception as e:
            all_errors.append(f"第{row_num}行：导入失败 - {str(e)}")

    db.commit()

    # 记录导入历史
    db.add(ImportHistory(
        import_type="student",
        filename=file.filename or "",
        total_rows=total,
        success_rows=success,
        error_rows=len(all_errors),
        errors=json.dumps(all_errors[:100], ensure_ascii=False),
        user_id=user.id,
    ))
    db.commit()

    return {"success": success, "total": total, "errors": all_errors[:50]}


@router.post("/api/scores/import")
async def import_scores(
    file: UploadFile = File(...),
    user=Depends(dep),
    db: Session = Depends(get_db),
):
    """批量导入成绩数据。"""
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in {".xlsx", ".xls"}:
        raise HTTPException(status_code=400, detail="仅支持 .xlsx / .xls 格式")

    contents = await file.read()
    wb = load_workbook(BytesIO(contents))
    ws = wb.active

    rows = list(ws.iter_rows(min_row=2, values_only=True))
    if not rows:
        raise HTTPException(status_code=400, detail="文件中没有数据行")

    all_errors = []
    success = 0
    total = 0

    # 预加载学号映射
    student_map = {s.student_no: s for s in db.query(Student).all()}

    for row_num, row in enumerate(rows, start=2):
        if not any(row):
            continue
        total += 1
        data = {
            "student_no": str(row[0] or "").strip(),
            "name": str(row[1] or "").strip(),
            "subject": str(row[2] or "").strip(),
            "score": row[3],
            "exam_name": str(row[4] or "").strip(),
        }

        errors = _validate_score_row(data, row_num)
        if errors:
            all_errors.extend(errors)
            continue

        student = student_map.get(data["student_no"])
        if not student:
            all_errors.append(f"第{row_num}行：学号 {data['student_no']} 不存在")
            continue

        try:
            db.add(Score(
                student_id=student.id,
                subject=data["subject"],
                score=float(data["score"]),
                exam_name=data["exam_name"],
            ))
            success += 1
        except Exception as e:
            all_errors.append(f"第{row_num}行：导入失败 - {str(e)}")

    db.commit()

    db.add(ImportHistory(
        import_type="score",
        filename=file.filename or "",
        total_rows=total,
        success_rows=success,
        error_rows=len(all_errors),
        errors=json.dumps(all_errors[:100], ensure_ascii=False),
        user_id=user.id,
    ))
    db.commit()

    return {"success": success, "total": total, "errors": all_errors[:50]}


@router.get("/api/import-history")
def list_import_history(
    import_type: str = "",
    page: int = 1,
    page_size: int = 20,
    _=Depends(dep),
    db: Session = Depends(get_db),
):
    """查询导入历史记录。"""
    q = db.query(ImportHistory)
    if import_type:
        q = q.filter(ImportHistory.import_type == import_type)
    total = q.count()
    rows = q.order_by(ImportHistory.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = []
    for r in rows:
        d = to_dict(r)
        if r.errors:
            try:
                d["error_list"] = json.loads(r.errors)
            except (json.JSONDecodeError, TypeError):
                d["error_list"] = []
        else:
            d["error_list"] = []
        items.append(d)
    return {"items": items, "total": total}


# ---------------- 学生数字画像 ----------------
@router.get("/api/students/{student_id}/profile")
def get_student_profile(student_id: int, _=Depends(dep), db: Session = Depends(get_db)):
    """获取学生综合数字画像数据。"""
    student = db.get(Student, student_id)
    if not student:
        raise HTTPException(status_code=404, detail="学生不存在")

    # 成绩统计
    scores = db.query(Score).filter(Score.student_id == student_id).order_by(Score.created_at).all()
    score_summary = {
        "total": len(scores),
        "avg": round(sum(s.score for s in scores) / len(scores), 1) if scores else 0,
        "max": max((s.score for s in scores), default=0),
        "min": min((s.score for s in scores), default=0),
        "by_subject": {},
        "trend": [],
    }
    for s in scores:
        score_summary["by_subject"].setdefault(s.subject, []).append({"score": s.score, "exam": s.exam_name or "", "date": str(s.created_at)[:10]})
        score_summary["trend"].append({"subject": s.subject, "score": s.score, "exam": s.exam_name or "", "date": str(s.created_at)[:10]})

    # 积分统计
    points = db.query(Point).filter(Point.student_id == student_id).all()
    point_summary = {
        "total": sum(p.points for p in points),
        "positive": sum(p.points for p in points if p.points > 0),
        "negative": sum(p.points for p in points if p.points < 0),
        "count": len(points),
        "timeline": [{"points": p.points, "reason": p.reason, "date": str(p.created_at)[:10]} for p in sorted(points, key=lambda x: x.created_at, reverse=True)[:20]],
    }

    # 考勤统计
    leaves = db.query(Leave).filter(Leave.student_id == student_id).all()
    leave_summary = {
        "total": len(leaves),
        "recent": [{"reason": l.reason, "start": l.start_date, "end": l.end_date, "status": l.status} for l in leaves[:10]],
    }

    # 表现统计
    from app.models import Performance
    performances = db.query(Performance).filter(Performance.student_id == student_id).all()
    performance_summary = {
        "positive": sum(1 for p in performances if p.ptype == "积极"),
        "negative": sum(1 for p in performances if p.ptype == "消极"),
        "total": len(performances),
        "recent": [{"ptype": p.ptype, "content": p.content, "date": str(p.created_at)[:10]} for p in sorted(performances, key=lambda x: x.created_at, reverse=True)[:10]],
    }

    # 作业统计
    from app.models import Submission, ExcellentWork
    # Submission.student_id 引用 users.id，需通过学生姓名+班级查找对应 user
    student_user = db.query(User).filter(
        User.role == "student", User.name == student.name, User.class_id == student.class_id
    ).first()
    user_id = student_user.id if student_user else None
    if user_id:
        submissions = db.query(Submission).filter(Submission.student_id == user_id).all()
        excellent_ids = {ew.submission_id for ew in db.query(ExcellentWork.submission_id).filter(
            ExcellentWork.submission_id.in_([s.id for s in submissions])
        ).all()}
        excellent_count = sum(1 for s in submissions if s.id in excellent_ids)
        submission_summary = {
            "total": len(submissions),
            "excellent": excellent_count,
            "rate": round(excellent_count / len(submissions) * 100, 1) if submissions else 0,
        }
    else:
        submission_summary = {"total": 0, "excellent": 0, "rate": 0}

    # 标签
    tags = db.query(StudentProfileTag).filter(StudentProfileTag.student_id == student_id).all()
    tag_list = [{"id": t.id, "tag": t.tag, "category": t.category} for t in tags]

    # 五维雷达得分
    radar = {
        "academic": min(100, round(score_summary["avg"] if scores else 50, 1)),
        "moral": min(100, round(50 + point_summary["total"] * 2, 1)) if points else 50,
        "attendance": min(100, round(100 - leave_summary["total"] * 5, 1)),
        "activity": min(100, round(50 + performance_summary["positive"] * 5, 1)),
        "skill": min(100, round(submission_summary["rate"], 1)),
    }

    return {
        "student": _student_out(db, student),
        "radar": radar,
        "score_summary": score_summary,
        "point_summary": point_summary,
        "leave_summary": leave_summary,
        "performance_summary": performance_summary,
        "submission_summary": submission_summary,
        "tags": tag_list,
    }


def _student_out(db: Session, s: Student) -> dict:
    from app.models import Classroom
    d = to_dict(s)
    cls = db.get(Classroom, s.class_id) if s.class_id else None
    d["class_name"] = cls.name if cls else None
    return d


@router.post("/api/students/{student_id}/tags")
def add_student_tag(student_id: int, payload: dict, _=Depends(dep), db: Session = Depends(get_db)):
    tag = (payload.get("tag") or "").strip()
    if not tag:
        raise HTTPException(status_code=400, detail="标签不能为空")
    t = StudentProfileTag(
        student_id=student_id,
        tag=tag,
        category=payload.get("category", "自定义"),
    )
    db.add(t)
    db.commit()
    db.refresh(t)
    return to_dict(t)


@router.delete("/api/students/{student_id}/tags/{tag_id}")
def remove_student_tag(student_id: int, tag_id: int, _=Depends(dep), db: Session = Depends(get_db)):
    t = db.get(StudentProfileTag, tag_id)
    if t and t.student_id == student_id:
        db.delete(t)
        db.commit()
    return {"ok": True}


# ---------------- 班级周报 ----------------
@router.get("/api/reports/weekly-data")
def get_weekly_data(class_id: int, week_start: str = "", week_end: str = "", _=Depends(dep), db: Session = Depends(get_db)):
    students = db.query(Student).filter(Student.class_id == class_id).all()
    student_ids = [s.id for s in students]
    student_map = {s.id: s.name for s in students}  # id → name 映射，避免重复查询
    total_students = len(students)
    if not student_ids:
        return {"error": "该班级无学生"}

    leave_q = db.query(Leave).filter(Leave.student_id.in_(student_ids))
    if week_start and week_end:
        leave_q = leave_q.filter(Leave.start_date >= week_start, Leave.start_date <= week_end)
    leaves = leave_q.all()

    from app.models import Performance
    perf_q = db.query(Performance).filter(Performance.student_id.in_(student_ids))
    if week_start and week_end:
        perf_q = perf_q.filter(Performance.created_at >= week_start, Performance.created_at <= week_end)
    performances = perf_q.all()
    positive_count = sum(1 for p in performances if p.ptype == "积极")
    negative_count = sum(1 for p in performances if p.ptype == "消极")

    from sqlalchemy import func as sqlfunc
    point_ranking = (
        db.query(Point.student_id, sqlfunc.sum(Point.points).label("total"))
        .filter(Point.student_id.in_(student_ids))
        .group_by(Point.student_id)
        .order_by(sqlfunc.sum(Point.points).desc())
        .all()
    )
    top5 = []
    bottom5 = []
    for pr in point_ranking[:5]:
        name = student_map.get(pr.student_id, "")
        if name:
            top5.append({"name": name, "points": pr.total})
    for pr in point_ranking[-5:]:
        name = student_map.get(pr.student_id, "")
        if name:
            bottom5.append({"name": name, "points": pr.total})

    score_q = db.query(Score).filter(Score.student_id.in_(student_ids))
    if week_start and week_end:
        score_q = score_q.filter(Score.created_at >= week_start, Score.created_at <= week_end)
    recent_scores = score_q.all()
    score_avg = round(sum(s.score for s in recent_scores) / len(recent_scores), 1) if recent_scores else 0

    # 批量查询：一次查询获取所有学生的积分/考勤/表现，避免 N+1
    all_points = db.query(Point).filter(Point.student_id.in_(student_ids)).all()
    all_leaves = db.query(Leave).filter(Leave.student_id.in_(student_ids)).all()
    all_perfs = db.query(Performance).filter(Performance.student_id.in_(student_ids)).all()

    # 按 student_id 分组聚合
    point_map = {}
    for p in all_points:
        point_map.setdefault(p.student_id, 0)
        point_map[p.student_id] += p.points
    leave_map = {}
    for l in all_leaves:
        leave_map[l.student_id] = leave_map.get(l.student_id, 0) + 1
    perf_map = {}
    for p in all_perfs:
        perf_map.setdefault(p.student_id, {"positive": 0, "negative": 0})
        if p.ptype == "积极":
            perf_map[p.student_id]["positive"] += 1
        else:
            perf_map[p.student_id]["negative"] += 1

    profile_summaries = []
    for s in students[:10]:
        profile_summaries.append({
            "name": s.name,
            "student_no": s.student_no,
            "points": point_map.get(s.id, 0),
            "leave_count": leave_map.get(s.id, 0),
            "positive": perf_map.get(s.id, {}).get("positive", 0),
            "negative": perf_map.get(s.id, {}).get("negative", 0),
        })

    return {
        "class_id": class_id,
        "total_students": total_students,
        "leave_count": len(leaves),
        "attendance_rate": round((total_students * 5 - len(leaves)) / (total_students * 5) * 100, 1) if total_students else 0,
        "positive_count": positive_count,
        "negative_count": negative_count,
        "score_avg": score_avg,
        "score_count": len(recent_scores),
        "top5": top5,
        "bottom5": bottom5,
        "profile_summaries": profile_summaries,
        "recent_performances": [
            {"student_name": student_map.get(p.student_id, ""), "ptype": p.ptype, "content": p.content}
            for p in sorted(performances, key=lambda x: x.created_at, reverse=True)[:15]
        ],
    }


@router.get("/api/reports")
def list_reports(class_id: int | None = None, _=Depends(dep), db: Session = Depends(get_db)):
    q = db.query(WeeklyReport)
    if class_id:
        q = q.filter(WeeklyReport.class_id == class_id)
    rows = q.order_by(WeeklyReport.id.desc()).all()
    items = []
    for r in rows:
        d = to_dict(r)
        cls = db.get(Classroom, r.class_id)
        d["class_name"] = cls.name if cls else ""
        if r.data_snapshot:
            try:
                d["snapshot"] = json.loads(r.data_snapshot)
            except (json.JSONDecodeError, TypeError):
                d["snapshot"] = {}
        items.append(d)
    return {"items": items, "total": len(rows)}


@router.post("/api/reports")
def save_report(payload: dict, user=Depends(dep), db: Session = Depends(get_db)):
    report_id = payload.get("id")
    title = payload.get("title", "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="报告标题不能为空")
    if report_id:
        r = db.get(WeeklyReport, report_id)
        if not r:
            raise HTTPException(status_code=404, detail="报告不存在")
        r.title = title
        r.content = payload.get("content", "")
        r.data_snapshot = json.dumps(payload.get("data_snapshot", {}), ensure_ascii=False)
    else:
        r = WeeklyReport(
            class_id=payload.get("class_id"),
            title=title,
            week_start=payload.get("week_start"),
            week_end=payload.get("week_end"),
            content=payload.get("content", ""),
            data_snapshot=json.dumps(payload.get("data_snapshot", {}), ensure_ascii=False),
            created_by=user.id,
        )
        db.add(r)
    db.commit()
    db.refresh(r)
    return to_dict(r)


@router.delete("/api/reports/{report_id}")
def delete_report(report_id: int, _=Depends(dep), db: Session = Depends(get_db)):
    r = db.get(WeeklyReport, report_id)
    if r:
        db.delete(r)
        db.commit()
    return {"ok": True}
