"""
PostgreSQL schema fix
用於 Render 無法進入 shell 時，自動補缺欄位
"""
import logging
from sqlalchemy import text
from app.database import engine

logger = logging.getLogger(__name__)


async def ensure_pg_schema():
    async with engine.begin() as conn:
        # 檢查 patrol_devices 表是否存在
        table_exists = await conn.scalar(text("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.tables
                WHERE table_schema='public'
                AND table_name='patrol_devices'
            )
        """))

        if not table_exists:
            logger.warning("patrol_devices table not found, skip")
            return

        # 檢查 site_id 欄位是否存在
        col_exists = await conn.scalar(text("""
            SELECT EXISTS (
                SELECT 1
                FROM information_schema.columns
                WHERE table_schema='public'
                AND table_name='patrol_devices'
                AND column_name='site_id'
            )
        """))

        if not col_exists:
            logger.warning("Adding missing column patrol_devices.site_id")
            await conn.execute(text("""
                ALTER TABLE patrol_devices
                ADD COLUMN site_id INTEGER
            """))
