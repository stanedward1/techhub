import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import settings

DATABASE_URL = os.getenv("DATABASE_URL", settings.DATABASE_URL)

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def run_migrations() -> None:
    """执行 Alembic 增量迁移（若尚无迁移记录则跳过，交由 create_all 建表）。"""
    try:
        from alembic import command
        from alembic.config import Config

        backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        cfg = Config(os.path.join(backend_dir, "alembic.ini"))
        cfg.set_main_option("script_location", os.path.join(backend_dir, "alembic"))
        cfg.set_main_option("sqlalchemy.url", DATABASE_URL)
        command.upgrade(cfg, "head")
    except Exception as e:  # noqa: BLE001 - 迁移失败不应阻断启动
        import logging

        logging.getLogger("techhub").warning(
            "Alembic migration skipped/failed (will rely on create_all): %s", e
        )


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

