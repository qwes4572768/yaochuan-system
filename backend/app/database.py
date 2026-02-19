"""
資料庫連線與 Session（Async SQLAlchemy）
- 強制使用 asyncpg driver（postgresql+asyncpg://）
- 正式環境不要在啟動時 create_all（交給 Alembic）
"""
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

db_url = str(settings.database_url or "").strip()

# Render / 其他環境常給 postgres:// 或 postgresql://
# Async 必須改成 postgresql+asyncpg://
if db_url.startswith("postgres://"):
    db_url = "postgresql+asyncpg://" + db_url[len("postgres://"):]
elif db_url.startswith("postgresql://"):
    db_url = "postgresql+asyncpg://" + db_url[len("postgresql://"):]
elif db_url.startswith("postgresql+psycopg2://"):
    db_url = "postgresql+asyncpg://" + db_url[len("postgresql+psycopg2://"):]

engine = create_async_engine(
    db_url,
    echo=settings.debug,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    pass


async def get_db():
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def init_db():
    # ✅ 正式環境不要在啟動時建表（避免 DuplicateTable）
    return