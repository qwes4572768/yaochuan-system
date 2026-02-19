"""
PostgreSQL schema fix
用於 Render 無法進入 shell 時，自動補缺欄位（只補欄位，不建表）
"""
import logging
from sqlalchemy import text
from app.database import engine

logger = logging.getLogger(__name__)


async def _table_exists(conn, table_name: str) -> bool:
    return bool(
        await conn.scalar(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.tables
                    WHERE table_schema='public'
                    AND table_name=:t
                )
                """
            ),
            {"t": table_name},
        )
    )


async def _column_exists(conn, table_name: str, column_name: str) -> bool:
    return bool(
        await conn.scalar(
            text(
                """
                SELECT EXISTS (
                    SELECT 1
                    FROM information_schema.columns
                    WHERE table_schema='public'
                    AND table_name=:t
                    AND column_name=:c
                )
                """
            ),
            {"t": table_name, "c": column_name},
        )
    )


async def ensure_pg_schema():
    async with engine.begin() as conn:
        # ---------------------------------------------------------
        # patrol_devices.site_id
        # ---------------------------------------------------------
        if await _table_exists(conn, "patrol_devices"):
            if not await _column_exists(conn, "patrol_devices", "site_id"):
                logger.warning("Adding missing column patrol_devices.site_id")
                await conn.execute(text("ALTER TABLE patrol_devices ADD COLUMN site_id INTEGER"))
        else:
            logger.warning("patrol_devices table not found, skip patrol_devices fix")

        # ---------------------------------------------------------
        # patrol_logs.site_id
        # ---------------------------------------------------------
        if await _table_exists(conn, "patrol_logs"):
            if not await _column_exists(conn, "patrol_logs", "site_id"):
                logger.warning("Adding missing column patrol_logs.site_id")
                await conn.execute(text("ALTER TABLE patrol_logs ADD COLUMN site_id INTEGER"))
        else:
            logger.warning("patrol_logs table not found, skip patrol_logs fix")
