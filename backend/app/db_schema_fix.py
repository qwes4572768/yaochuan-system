"""
PostgreSQL schema fix (minimal)
用於正式環境沒有 shell 時，補齊缺失欄位，避免 500
"""
import logging
from sqlalchemy import text
from app.database import engine

logger = logging.getLogger(__name__)

async def ensure_pg_schema():
    # 只針對 patrol_devices 補 site_id（先救急）
    async with engine.begin() as conn:
        # 確認 patrol_devices 表存在才處理
        exists = await conn.scalar(text("""
            SELECT EXISTS (
              SELECT 1
              FROM information_schema.tables
              WHERE table_schema='public' AND table_name='patrol_devices'
            )
        """))
        if not exists:
            logger.warning("patrol_devices table not found; skip pg schema fix")
            return

        # 檢查 site_id 欄位是否存在
        col_exists = await conn.scalar(text("""
            SELECT EXISTS (
              SELECT 1
              FROM information_schema.columns
              WHERE table_schema='public' AND table_name='patrol_devices' AND column_name='site_id'
            )
        """))
        if not col_exists:
            logger.warning("Adding missing column patrol_devices.site_id ...")
            await conn.execute(text("ALTER TABLE patrol_devices ADD COLUMN site_id INTEGER"))
