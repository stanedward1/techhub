"""Docker 容器启动入口：迁移数据库 → 首次初始化演示数据 → 启动 uvicorn。"""
import sys


def main() -> None:
    # 1. 数据库迁移到最新版本（alembic 为 schema 唯一来源）
    import subprocess

    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        check=True,
    )

    # 2. 首次启动（库为空）时初始化演示数据
    from app.database import SessionLocal
    from app.models import User

    db = SessionLocal()
    try:
        if db.query(User).count() == 0:
            from app.seed import seed_all

            seed_all()
    finally:
        db.close()

    # 3. 启动 uvicorn
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
