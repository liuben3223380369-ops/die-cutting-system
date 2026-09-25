"""pytest 公共 fixtures：内存 SQLite + 建表"""
import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

pytest.importorskip("sqlalchemy")
pytest.importorskip("pytest_asyncio")


@pytest_asyncio.fixture
async def db_session():
    from app.core.database import Base
    import app.models  # noqa: F401 — 注册全部模型

    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with Session() as session:
        yield session
        await session.rollback()

    await engine.dispose()
