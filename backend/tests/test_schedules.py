"""
排班 P0 單元測試。
覆蓋：有效指派限制、批量建立、統計正確性。
"""
from datetime import date, time
from decimal import Decimal
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.models import (
    Employee, Site, SiteEmployeeAssignment, Schedule, ScheduleShift, ScheduleAssignment,
)
from app import crud
from app.schemas import (
    ScheduleCreate, ScheduleShiftCreate, ScheduleShiftBatchCreate, ScheduleAssignmentCreate,
)
from app.crud import ScheduleAssignmentNotEligibleError, _shift_duration_hours


# 純函數：工時計算（不需 DB）
def test_shift_duration_hours_basic():
    """start_time/end_time 同一天：工時 = 結束 - 開始"""
    assert _shift_duration_hours(time(8, 0), time(17, 0)) == Decimal("9")
    assert _shift_duration_hours(time(0, 0), time(8, 0)) == Decimal("8")


def test_shift_duration_hours_night_cross_midnight():
    """夜班跨日：end < start 時視為跨日，工時 = 24 - start + end"""
    # 22:00 ~ 06:00 => 8 小時
    assert _shift_duration_hours(time(22, 0), time(6, 0)) == Decimal("8")


def test_shift_duration_hours_missing_time():
    """缺 start 或 end 回傳 0"""
    assert _shift_duration_hours(None, time(17, 0)) == Decimal("0")
    assert _shift_duration_hours(time(8, 0), None) == Decimal("0")


# Async DB 測試
@pytest.fixture
async def async_engine_and_session():
    engine = create_async_engine(
        "sqlite+aiosqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    yield engine, async_session
    await engine.dispose()


@pytest.mark.asyncio
async def test_eligible_employee_can_be_assigned(async_engine_and_session):
    """有效指派限制：在案場有效期間內的員工可以指派到該日班別"""
    engine, async_session = async_engine_and_session
    async with async_session() as db:
        site = Site(name="測試案場", client_name="客戶", address="地址", contract_start=date(2025, 1, 1),
                    contract_end=date(2025, 12, 31), monthly_amount=Decimal("100000"), payment_method="transfer",
                    receivable_day=10, is_84_1=False)
        db.add(site)
        await db.flush()
        emp = Employee(name="王小明", birth_date=date(1990, 1, 1), national_id="A123456789",
                       reg_address="台北", live_address="台北", live_same_as_reg=True)
        db.add(emp)
        await db.flush()
        sea = SiteEmployeeAssignment(site_id=site.id, employee_id=emp.id, effective_from=date(2025, 1, 1), effective_to=date(2025, 1, 31))
        db.add(sea)
        await db.flush()
        sched = Schedule(site_id=site.id, year=2025, month=1, status="draft")
        db.add(sched)
        await db.flush()
        shift = ScheduleShift(schedule_id=sched.id, date=date(2025, 1, 15), shift_code="day", start_time=time(8, 0), end_time=time(17, 0), required_headcount=1)
        db.add(shift)
        await db.flush()
        await db.commit()

    async with async_session() as db:
        eligible = await crud.is_employee_eligible_for_site_on_date(db, site.id, emp.id, date(2025, 1, 15))
        assert eligible is True
        a = await crud.create_schedule_assignment(db, shift.id, ScheduleAssignmentCreate(employee_id=emp.id, role="normal", confirmed=False))
        assert a.id is not None
        assert a.employee_id == emp.id


@pytest.mark.asyncio
async def test_ineligible_employee_raises(async_engine_and_session):
    """有效指派限制：不在案場有效期間內的員工指派會拋出 ScheduleAssignmentNotEligibleError"""
    engine, async_session = async_engine_and_session
    async with async_session() as db:
        site = Site(name="案場B", client_name="客戶B", address="地址B", contract_start=date(2025, 1, 1),
                    contract_end=date(2025, 12, 31), monthly_amount=Decimal("100000"), payment_method="transfer",
                    receivable_day=10, is_84_1=False)
        db.add(site)
        await db.flush()
        emp = Employee(name="李小華", birth_date=date(1992, 5, 5), national_id="A234567890",
                       reg_address="桃園", live_address="桃園", live_same_as_reg=True)
        db.add(emp)
        await db.flush()
        # 指派期間僅 2025/1/1 ~ 2025/1/10，1/15 已不在期間內
        sea = SiteEmployeeAssignment(site_id=site.id, employee_id=emp.id, effective_from=date(2025, 1, 1), effective_to=date(2025, 1, 10))
        db.add(sea)
        await db.flush()
        sched = Schedule(site_id=site.id, year=2025, month=1, status="draft")
        db.add(sched)
        await db.flush()
        shift = ScheduleShift(schedule_id=sched.id, date=date(2025, 1, 15), shift_code="day", start_time=time(8, 0), end_time=time(17, 0), required_headcount=1)
        db.add(shift)
        await db.flush()
        shift_id = shift.id
        await db.commit()

    async with async_session() as db:
        with pytest.raises(ScheduleAssignmentNotEligibleError):
            await crud.create_schedule_assignment(db, shift_id, ScheduleAssignmentCreate(employee_id=emp.id, role="normal"))


@pytest.mark.asyncio
async def test_batch_create_shifts_for_month(async_engine_and_session):
    """批量建立：為某月建立班別時，該月幾天就幾筆 shift"""
    engine, async_session = async_engine_and_session
    async with async_session() as db:
        site = Site(name="案場C", client_name="客戶C", address="地址C", contract_start=date(2025, 1, 1),
                    contract_end=None, monthly_amount=Decimal("100000"), payment_method="transfer",
                    receivable_day=10, is_84_1=True)
        db.add(site)
        await db.flush()
        sched = Schedule(site_id=site.id, year=2025, month=1, status="draft")
        db.add(sched)
        await db.flush()
        await db.commit()

    async with async_session() as db:
        sched_refresh = await crud.get_schedule(db, sched.id)
        assert sched_refresh is not None
        template = ScheduleShiftBatchCreate(shift_code="day", start_time=time(8, 0), end_time=time(16, 0), required_headcount=2)
        created = await crud.batch_create_shifts_for_month(db, sched.id, 2025, 1, template)
        # 2025/1 有 31 天
        assert len(created) == 31
        assert all(sh.shift_code == "day" for sh in created)
        assert created[0].date == date(2025, 1, 1)
        assert created[30].date == date(2025, 1, 31)


@pytest.mark.asyncio
async def test_monthly_shift_stats_correctness(async_engine_and_session):
    """統計正確性：總班數、總工時、夜班數、84-1 標記"""
    engine, async_session = async_engine_and_session
    async with async_session() as db:
        site = Site(name="案場D", client_name="客戶D", address="地址D", contract_start=date(2025, 1, 1),
                    contract_end=None, monthly_amount=Decimal("100000"), payment_method="transfer",
                    receivable_day=10, is_84_1=True)
        db.add(site)
        await db.flush()
        emp = Employee(name="張三", birth_date=date(1988, 3, 3), national_id="A111111111",
                       reg_address="新北", live_address="新北", live_same_as_reg=True)
        db.add(emp)
        await db.flush()
        sea = SiteEmployeeAssignment(site_id=site.id, employee_id=emp.id, effective_from=date(2025, 1, 1), effective_to=None)
        db.add(sea)
        await db.flush()
        sched = Schedule(site_id=site.id, year=2025, month=1, status="draft")
        db.add(sched)
        await db.flush()
        # 2 個日班 8-17（9h）、1 個夜班 22-6（8h）
        sh1 = ScheduleShift(schedule_id=sched.id, date=date(2025, 1, 5), shift_code="day", start_time=time(8, 0), end_time=time(17, 0), required_headcount=1)
        sh2 = ScheduleShift(schedule_id=sched.id, date=date(2025, 1, 6), shift_code="day", start_time=time(8, 0), end_time=time(17, 0), required_headcount=1)
        sh3 = ScheduleShift(schedule_id=sched.id, date=date(2025, 1, 7), shift_code="night", start_time=time(22, 0), end_time=time(6, 0), required_headcount=1)
        db.add_all([sh1, sh2, sh3])
        await db.flush()
        a1 = ScheduleAssignment(shift_id=sh1.id, employee_id=emp.id, role="normal", confirmed=True)
        a2 = ScheduleAssignment(shift_id=sh2.id, employee_id=emp.id, role="normal", confirmed=True)
        a3 = ScheduleAssignment(shift_id=sh3.id, employee_id=emp.id, role="normal", confirmed=True)
        db.add_all([a1, a2, a3])
        await db.commit()

    async with async_session() as db:
        stats = await crud.get_employee_monthly_shift_stats(db, 202501, employee_id=emp.id)
        assert len(stats) == 1
        row = stats[0]
        assert row["employee_id"] == emp.id
        assert row["year_month"] == 202501
        assert row["total_shifts"] == 3
        assert row["total_hours"] == Decimal("9") + Decimal("9") + Decimal("8")  # 26
        assert row["night_shift_count"] == 1
        assert row["is_84_1_site"] is True
        assert site.id in row["site_ids"]
