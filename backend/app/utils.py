import re
from datetime import datetime


def to_dict(obj):
    """把 SQLAlchemy 模型实例转为字典（不含关系字段与内部状态）。"""
    if obj is None:
        return None
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def serialize_datetime(value):
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M:%S")
    return value


def safe_filename(name: str) -> str:
    """过滤文件名中的非法字符，防止路径穿越。"""
    name = re.sub(r"[^\w.\-\u4e00-\u9fff]", "_", name or "")
    name = name.strip("._")
    return name or "file"
