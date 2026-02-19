"""巡邏管理 API：手機綁定、巡邏點、打點與巡邏紀錄匯出。"""
from __future__ import annotations

import hashlib
import hmac
import json
import secrets
import uuid
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from io import BytesIO
from urllib.parse import parse_qs, quote, urlparse

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request
from fastapi.responses import JSONResponse, StreamingResponse
from openpyxl import Workbook
from passlib.context import CryptContext
from sqlalchemy import Select, and_, or_, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app import models, schemas
from app.config import settings
from app.database import get_db

router = APIRouter(prefix="/api/patrol", tags=["patrol"])

_PATROL_QR_SECRET = "patrol-qr-secret-change-me"
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def _client_ip(request: Request) -> str | None:
    xfwd = request.headers.get("x-forwarded-for")
    if xfwd:
        return xfwd.split(",")[0].strip()
    return request.client.host if request.client else None


def _build_bind_url(code: str) -> str:
    base = settings.public_base_url.rstrip("/")
    return f"{base}/patrol/bind?code={quote(code)}"


def _build_point_checkin_url(public_id: str) -> str:
    base = settings.public_base_url.rstrip("/")
    return f"{base}/patrol/checkin/{quote(public_id)}"


def _build_permanent_bind_url(device_public_id: str) -> str:
    """永久裝置入口：掃碼後由此進入，依綁定狀態分流至登入或綁定頁，避免重複綁定。"""
    base = settings.public_base_url.rstrip("/")
    return f"{base}/patrol/entry/permanent/{quote(device_public_id)}"


def _extract_device_token(
    authorization: str | None,
    x_device_token: str | None,
) -> str:
    if x_device_token and x_device_token.strip():
        return x_device_token.strip()
    if authorization and authorization.startswith("Device "):
        token = authorization.replace("Device ", "", 1).strip()
        if token:
            return token
    raise HTTPException(status_code=401, detail="缺少設備憑證，請先完成手機綁定")


def _normalize_device_fingerprint(fingerprint: dict) -> str:
    data = dict(fingerprint or {})
    data.pop("ip", None)
    return json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _sign_point_payload(point_id: int, nonce: str) -> str:
    raw = f"{point_id}:{nonce}".encode("utf-8")
    return hmac.new(_PATROL_QR_SECRET.encode("utf-8"), raw, hashlib.sha256).hexdigest()[:20]


async def _get_device_by_token(db: AsyncSession, token: str) -> models.PatrolDevice:
    device = await db.scalar(select(models.PatrolDevice).where(models.PatrolDevice.device_token == token))
    if not device:
        raise HTTPException(status_code=401, detail="設備憑證無效，請重新綁定")
    if not device.is_active:
        raise HTTPException(status_code=401, detail="此設備已解除綁定，請重新綁定")
    return device


async def _resolve_point_from_qr(db: AsyncSession, qr_value: str) -> models.PatrolPoint:
    v = (qr_value or "").strip()
    if not v:
        raise HTTPException(status_code=422, detail="QR 內容不可為空")

    parsed = urlparse(v)
    if parsed.scheme:
        path_parts = [p for p in (parsed.path or "").split("/") if p]
        if len(path_parts) >= 3 and path_parts[-2] == "checkin":
            public_id = path_parts[-1].strip()
            if public_id:
                point = await db.scalar(select(models.PatrolPoint).where(models.PatrolPoint.public_id == public_id))
                if point:
                    return point
        q = parse_qs(parsed.query or "")
        point_id_raw = (q.get("point_id") or [None])[0]
        nonce = (q.get("nonce") or [None])[0]
        sig = (q.get("sig") or [None])[0]
        point_code_raw = (q.get("point_code") or [None])[0]
        if point_id_raw and nonce and sig:
            try:
                point_id = int(point_id_raw)
            except ValueError as exc:
                raise HTTPException(status_code=422, detail="QR point_id 格式錯誤") from exc
            expected = _sign_point_payload(point_id, nonce)
            if not hmac.compare_digest(expected, sig):
                raise HTTPException(status_code=400, detail="QR 驗章失敗，請使用系統產生之巡邏點 QR")
            point = await db.get(models.PatrolPoint, point_id)
            if not point:
                raise HTTPException(status_code=404, detail="巡邏點不存在")
            return point
        if point_code_raw:
            point = await db.scalar(select(models.PatrolPoint).where(models.PatrolPoint.point_code == point_code_raw.strip()))
            if point:
                return point
        raise HTTPException(status_code=400, detail="無法解析巡邏點 QR")

    point = await db.scalar(select(models.PatrolPoint).where(models.PatrolPoint.point_code == v))
    if point:
        return point
    point = await db.scalar(select(models.PatrolPoint).where(models.PatrolPoint.public_id == v))
    if point:
        return point
    raise HTTPException(status_code=404, detail="巡邏點不存在")


DEFAULT_PATROL_SITE_NAME = "未分類(舊資料)"


async def _get_default_patrol_site_id(db: AsyncSession) -> int | None:
    """取得預設案場「未分類(舊資料)」的 id，若不存在回傳 None。"""
    r = await db.scalar(
        select(models.Site.id).where(models.Site.name == DEFAULT_PATROL_SITE_NAME).limit(1)
    )
    return r


def _point_to_read(point: models.PatrolPoint) -> schemas.PatrolPointRead:
    return schemas.PatrolPointRead(
        id=point.id,
        public_id=point.public_id,
        point_code=point.point_code,
        point_name=point.point_name,
        site_id=point.site_id,
        site_name=point.site_name,
        location=point.location,
        is_active=point.is_active,
        qr_url=_build_point_checkin_url(point.public_id),
        created_at=point.created_at,
        updated_at=point.updated_at,
    )


def _binding_to_status(binding: models.PatrolDeviceBinding, device_public_id: str) -> schemas.PatrolDeviceStatusResponse:
    return schemas.PatrolDeviceStatusResponse(
        device_public_id=device_public_id,
        is_bound=bool(binding.is_bound),
        employee_name=binding.employee_name,
        site_name=binding.site_name,
        ua=binding.user_agent,
        platform=binding.platform,
        browser=binding.browser,
        language=binding.language,
        screen=binding.screen_size,
        timezone=binding.timezone,
        password_set=bool(binding.password_hash),
        bound_at=binding.bound_at,
        device_info={
            "ua": binding.user_agent,
            "platform": binding.platform,
            "browser": binding.browser,
            "lang": binding.language,
            "screen": binding.screen_size,
            "tz": binding.timezone,
        },
    )


async def _upsert_active_patrol_device(
    db: AsyncSession,
    *,
    device_public_id: str,
    employee_name: str,
    site_name: str,
    fingerprint: dict,
    fingerprint_json: str,
    password_hash: str,
    client_ip: str | None,
) -> models.PatrolDevice:
    now = datetime.utcnow()
    device = await db.scalar(
        select(models.PatrolDevice)
        .where(
            models.PatrolDevice.device_public_id == device_public_id,
            models.PatrolDevice.device_fingerprint == fingerprint_json,
            models.PatrolDevice.is_active.is_(True),
        )
        .order_by(models.PatrolDevice.id.desc())
    )
    if not device:
        device = models.PatrolDevice(
            binding_code_id=None,
            device_public_id=device_public_id,
            device_token=secrets.token_urlsafe(48),
            employee_name=employee_name,
            site_name=site_name,
            device_fingerprint=fingerprint_json,
            user_agent=fingerprint.get("userAgent"),
            platform=fingerprint.get("platform"),
            browser=fingerprint.get("browser"),
            language=fingerprint.get("language"),
            screen_size=fingerprint.get("screen"),
            timezone=fingerprint.get("timezone"),
            ip_address=client_ip,
            password_hash=password_hash,
            is_active=True,
            bound_at=now,
            unbound_at=None,
        )
        db.add(device)
        await db.flush()
        return device

    device.employee_name = employee_name
    device.site_name = site_name
    device.user_agent = fingerprint.get("userAgent")
    device.platform = fingerprint.get("platform")
    device.browser = fingerprint.get("browser")
    device.language = fingerprint.get("language")
    device.screen_size = fingerprint.get("screen")
    device.timezone = fingerprint.get("timezone")
    device.ip_address = client_ip
    device.password_hash = password_hash
    device.is_active = True
    device.unbound_at = None
    return device


def _binding_to_admin_item(
    binding: models.PatrolDeviceBinding,
    device: models.PatrolDevice | None = None,
) -> schemas.PatrolDeviceBindingAdminItem:
    return schemas.PatrolDeviceBindingAdminItem(
        id=binding.id,
        binding_id=binding.id,
        device_public_id=binding.device_public_id,
        is_active=binding.is_active,
        employee_name=binding.employee_name,
        site_name=binding.site_name,
        bound_at=binding.bound_at,
        unbound_at=device.unbound_at if device else None,
        last_seen_at=binding.last_seen_at,
        ua=binding.user_agent,
        platform=binding.platform,
        browser=binding.browser,
        language=binding.language,
        timezone=binding.timezone,
        screen=binding.screen_size,
        screen_size=binding.screen_size,
        ip_address=device.ip_address if device else None,
        password_set=bool(binding.password_hash),
        device_info={
            "ua": binding.user_agent,
            "platform": binding.platform,
            "browser": binding.browser,
            "lang": binding.language,
            "screen": binding.screen_size,
            "tz": binding.timezone,
        },
    )


@router.post("/binding-codes", response_model=schemas.PatrolBindingCodeRead, summary="產生手機綁定 QR code")
async def create_binding_code(
    body: schemas.PatrolBindingCodeCreate,
    db: AsyncSession = Depends(get_db),
):
    now = datetime.utcnow()
    code = secrets.token_urlsafe(24)
    expires_at = now + timedelta(minutes=body.expire_minutes)
    row = models.PatrolBindingCode(code=code, expires_at=expires_at)
    db.add(row)
    await db.flush()
    bind_url = _build_bind_url(code)
    return schemas.PatrolBindingCodeRead(
        code=code,
        expires_at=expires_at,
        bind_url=bind_url,
        qr_value=bind_url,
    )


@router.post("/bind", response_model=schemas.PatrolBindResponse, summary="以綁定碼綁定手機設備")
async def bind_device(
    body: schemas.PatrolBindRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    now = datetime.utcnow()
    fingerprint_json = _normalize_device_fingerprint(body.device_fingerprint.model_dump())
    existing_active = await db.scalar(
        select(models.PatrolDevice)
        .where(
            models.PatrolDevice.device_fingerprint == fingerprint_json,
            models.PatrolDevice.is_active.is_(True),
        )
        .order_by(models.PatrolDevice.id.desc())
    )
    bind = await db.scalar(select(models.PatrolBindingCode).where(models.PatrolBindingCode.code == body.code.strip()))
    if not bind:
        raise HTTPException(status_code=404, detail="綁定碼不存在")
    if bind.used_at is not None:
        if existing_active:
            raise HTTPException(status_code=400, detail="此裝置已綁定，請用「已綁定開始巡邏」登入")
        raise HTTPException(status_code=400, detail="綁定碼已使用，請重新產生")
    if bind.expires_at < now:
        raise HTTPException(status_code=400, detail="綁定碼已過期，請重新產生")
    if existing_active:
        raise HTTPException(status_code=409, detail="此裝置已綁定，請先解除綁定或直接登入")

    fingerprint = body.device_fingerprint.model_dump()
    client_ip = _client_ip(request)
    fingerprint.pop("ip", None)
    device_public_id = (body.device_public_id or "").strip() or str(uuid.uuid4())
    password_hash = _pwd_context.hash(body.password.strip())
    employee_name = body.employee_name.strip()
    site_name = body.site_name.strip()

    device = models.PatrolDevice(
        binding_code_id=bind.id,
        device_public_id=device_public_id,
        device_token=secrets.token_urlsafe(48),
        employee_name=employee_name,
        site_name=site_name,
        device_fingerprint=fingerprint_json,
        user_agent=fingerprint.get("userAgent"),
        platform=fingerprint.get("platform"),
        browser=fingerprint.get("browser"),
        language=fingerprint.get("language"),
        screen_size=fingerprint.get("screen"),
        timezone=fingerprint.get("timezone"),
        ip_address=client_ip,
        password_hash=password_hash,
        is_active=True,
        bound_at=now,
        unbound_at=None,
    )
    bind.used_at = now
    db.add(device)
    await db.flush()

    # 同步寫入 patrol_device_bindings，讓管理頁 GET /device-bindings 與綁定頁看到同一份資料
    existing_binding = await db.scalar(
        select(models.PatrolDeviceBinding).where(
            models.PatrolDeviceBinding.device_public_id == device_public_id
        )
    )
    if existing_binding:
        existing_binding.employee_name = employee_name
        existing_binding.site_name = site_name
        existing_binding.password_hash = password_hash
        existing_binding.device_fingerprint_json = fingerprint_json
        existing_binding.is_bound = True
        existing_binding.is_active = True
        existing_binding.bound_at = now
        existing_binding.last_seen_at = now
        existing_binding.user_agent = fingerprint.get("userAgent")
        existing_binding.platform = fingerprint.get("platform")
        existing_binding.browser = fingerprint.get("browser")
        existing_binding.language = fingerprint.get("language")
        existing_binding.screen_size = fingerprint.get("screen")
        existing_binding.timezone = fingerprint.get("timezone")
        existing_binding.device_info = {
            "ua": existing_binding.user_agent,
            "platform": existing_binding.platform,
            "browser": existing_binding.browser,
            "lang": existing_binding.language,
            "screen": existing_binding.screen_size,
            "tz": existing_binding.timezone,
        }
    else:
        binding_row = models.PatrolDeviceBinding(
            device_public_id=device_public_id,
            employee_name=employee_name,
            site_name=site_name,
            password_hash=password_hash,
            device_fingerprint_json=fingerprint_json,
            is_bound=True,
            is_active=True,
            bound_at=now,
            last_seen_at=now,
            user_agent=fingerprint.get("userAgent"),
            platform=fingerprint.get("platform"),
            browser=fingerprint.get("browser"),
            language=fingerprint.get("language"),
            screen_size=fingerprint.get("screen"),
            timezone=fingerprint.get("timezone"),
            device_info={
                "ua": fingerprint.get("userAgent"),
                "platform": fingerprint.get("platform"),
                "browser": fingerprint.get("browser"),
                "lang": fingerprint.get("language"),
                "screen": fingerprint.get("screen"),
                "tz": fingerprint.get("timezone"),
            },
        )
        db.add(binding_row)
    await db.flush()

    return schemas.PatrolBindResponse(
        device_public_id=device_public_id,
        is_bound=True,
        device_token=device.device_token,
        employee_name=device.employee_name,
        site_name=device.site_name,
        bound_at=device.bound_at,
    )


@router.get("/me/device", response_model=schemas.PatrolDeviceRead, summary="取得目前設備綁定資訊")
async def get_bound_device(
    authorization: str | None = Header(None, alias="Authorization"),
    x_device_token: str | None = Header(None, alias="X-Device-Token"),
    db: AsyncSession = Depends(get_db),
):
    token = _extract_device_token(authorization, x_device_token)
    device = await _get_device_by_token(db, token)
    return schemas.PatrolDeviceRead(
        id=device.id,
        employee_name=device.employee_name,
        site_name=device.site_name,
        is_active=device.is_active,
        password_set=bool(device.password_hash),
        bound_at=device.bound_at,
        unbound_at=device.unbound_at,
        device_fingerprint=device.device_fingerprint,
    )


@router.get("/binding-status", response_model=schemas.PatrolBindingStatusResponse, summary="查詢目前裝置是否已綁定")
async def get_binding_status(
    device_fingerprint: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    if not device_fingerprint:
        return schemas.PatrolBindingStatusResponse(is_bound=False)
    try:
        raw = json.loads(device_fingerprint)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=422, detail="device_fingerprint 格式錯誤") from exc
    fingerprint_json = _normalize_device_fingerprint(raw)
    device = await db.scalar(
        select(models.PatrolDevice)
        .where(
            models.PatrolDevice.device_fingerprint == fingerprint_json,
            models.PatrolDevice.is_active.is_(True),
        )
        .order_by(models.PatrolDevice.id.desc())
    )
    if not device:
        return schemas.PatrolBindingStatusResponse(is_bound=False)
    return schemas.PatrolBindingStatusResponse(
        is_bound=True,
        device_public_id=device.device_public_id,
        employee_name=device.employee_name,
        site_name=device.site_name,
        ua=device.user_agent,
        platform=device.platform,
        browser=device.browser,
        language=device.language,
        screen=device.screen_size,
        timezone=device.timezone,
        password_set=bool(device.password_hash),
        bound_at=device.bound_at,
        device_info={
            "ua": device.user_agent,
            "platform": device.platform,
            "browser": device.browser,
            "lang": device.language,
            "screen": device.screen_size,
            "tz": device.timezone,
        },
    )


@router.post("/device/permanent-qr", response_model=schemas.PatrolPermanentQrResponse, summary="產生永久綁定 QR")
async def create_permanent_bind_qr(
    db: AsyncSession = Depends(get_db),
):
    device_public_id = str(uuid.uuid4()).strip()
    row = models.PatrolDeviceBinding(
        device_public_id=device_public_id,
        is_bound=False,
        is_active=False,
        bound_at=None,
    )
    db.add(row)
    await db.flush()
    qr_url = _build_permanent_bind_url(device_public_id)
    return schemas.PatrolPermanentQrResponse(
        device_public_id=device_public_id,
        qr_url=qr_url,
        qr_value=qr_url,
    )


@router.get("/device/{device_public_id}", response_model=schemas.PatrolDeviceStatusResponse, summary="查詢永久裝置綁定狀態")
async def get_device_status(
    device_public_id: str,
    db: AsyncSession = Depends(get_db),
):
    normalized_public_id = device_public_id.strip()
    binding = await db.scalar(
        select(models.PatrolDeviceBinding).where(models.PatrolDeviceBinding.device_public_id == normalized_public_id)
    )
    if not binding:
        raise HTTPException(status_code=404, detail="device not found")
    return _binding_to_status(binding, normalized_public_id)


@router.post("/device/{device_public_id}/bind", response_model=schemas.PatrolBindResponse, summary="永久裝置綁定")
async def bind_device_by_public_id(
    device_public_id: str,
    body: schemas.PatrolDeviceBindRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    now = datetime.utcnow()
    normalized_public_id = device_public_id.strip()
    fingerprint_json = _normalize_device_fingerprint(body.device_fingerprint.model_dump())
    fingerprint = body.device_fingerprint.model_dump()
    fingerprint.pop("ip", None)
    client_ip = _client_ip(request)
    password_hash = _pwd_context.hash(body.password.strip())

    binding = await db.scalar(
        select(models.PatrolDeviceBinding).where(models.PatrolDeviceBinding.device_public_id == normalized_public_id)
    )
    if not binding:
        raise HTTPException(status_code=404, detail="device not found")
    if binding.is_bound:
        raise HTTPException(status_code=400, detail="device already bound")

    binding.employee_name = body.employee_name.strip()
    binding.site_name = body.site_name.strip()
    binding.password_hash = password_hash
    binding.device_fingerprint_json = fingerprint_json
    binding.is_bound = True
    binding.is_active = True
    binding.bound_at = now
    binding.last_seen_at = now
    binding.user_agent = fingerprint.get("userAgent")
    binding.platform = fingerprint.get("platform")
    binding.browser = fingerprint.get("browser")
    binding.language = fingerprint.get("language")
    binding.screen_size = fingerprint.get("screen")
    binding.timezone = fingerprint.get("timezone")
    binding.device_info = {
        "ua": binding.user_agent,
        "platform": binding.platform,
        "browser": binding.browser,
        "lang": binding.language,
        "screen": binding.screen_size,
        "tz": binding.timezone,
    }

    device = await _upsert_active_patrol_device(
        db,
        device_public_id=normalized_public_id,
        employee_name=binding.employee_name,
        site_name=binding.site_name,
        fingerprint=fingerprint,
        fingerprint_json=fingerprint_json,
        password_hash=password_hash,
        client_ip=client_ip,
    )
    return schemas.PatrolBindResponse(
        device_public_id=normalized_public_id,
        is_bound=True,
        device_token=device.device_token,
        employee_name=device.employee_name,
        site_name=device.site_name,
        bound_at=device.bound_at,
    )


@router.post("/bound-login", response_model=schemas.PatrolBoundLoginResponse, summary="已綁定裝置登入巡邏")
async def bound_login(
    body: schemas.PatrolBoundLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    fingerprint_json = _normalize_device_fingerprint(body.device_fingerprint.model_dump())
    device = await db.scalar(
        select(models.PatrolDevice)
        .where(
            models.PatrolDevice.employee_name == body.employee_name.strip(),
            models.PatrolDevice.device_fingerprint == fingerprint_json,
            models.PatrolDevice.is_active.is_(True),
        )
        .order_by(models.PatrolDevice.id.desc())
    )
    if not device:
        raise HTTPException(status_code=404, detail="此裝置尚未綁定，請先完成綁定")
    if not device.password_hash or not _pwd_context.verify(body.password.strip(), device.password_hash):
        raise HTTPException(status_code=401, detail="密碼錯誤")
    return schemas.PatrolBoundLoginResponse(
        device_token=device.device_token,
        employee_name=device.employee_name,
        site_name=device.site_name,
        bound_at=device.bound_at,
    )


@router.post("/device/{device_public_id}/login", response_model=schemas.PatrolBoundLoginResponse, summary="永久裝置登入巡邏")
async def login_by_device_public_id(
    device_public_id: str,
    body: schemas.PatrolDeviceLoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    now = datetime.utcnow()
    normalized_public_id = device_public_id.strip()
    fingerprint_json = _normalize_device_fingerprint(body.device_fingerprint.model_dump())
    binding = await db.scalar(
        select(models.PatrolDeviceBinding).where(models.PatrolDeviceBinding.device_public_id == normalized_public_id)
    )
    if not binding or not binding.is_bound:
        raise HTTPException(status_code=404, detail="此永久裝置尚未綁定，請先綁定")
    if not binding.password_hash or not _pwd_context.verify(body.password.strip(), binding.password_hash):
        raise HTTPException(status_code=401, detail="密碼錯誤")
    if body.employee_name and binding.employee_name and body.employee_name.strip() != binding.employee_name:
        raise HTTPException(status_code=401, detail="員工姓名與綁定資料不符")

    fingerprint = body.device_fingerprint.model_dump()
    fingerprint.pop("ip", None)
    client_ip = _client_ip(request)
    device = await _upsert_active_patrol_device(
        db,
        device_public_id=normalized_public_id,
        employee_name=binding.employee_name or "",
        site_name=binding.site_name or "",
        fingerprint=fingerprint,
        fingerprint_json=fingerprint_json,
        password_hash=binding.password_hash,
        client_ip=client_ip,
    )
    binding.last_seen_at = now
    binding.user_agent = fingerprint.get("userAgent")
    binding.platform = fingerprint.get("platform")
    binding.browser = fingerprint.get("browser")
    binding.language = fingerprint.get("language")
    binding.screen_size = fingerprint.get("screen")
    binding.timezone = fingerprint.get("timezone")
    binding.device_info = {
        "ua": binding.user_agent,
        "platform": binding.platform,
        "browser": binding.browser,
        "lang": binding.language,
        "screen": binding.screen_size,
        "tz": binding.timezone,
    }
    return schemas.PatrolBoundLoginResponse(
        device_token=device.device_token,
        employee_name=device.employee_name,
        site_name=device.site_name,
        bound_at=device.bound_at,
    )


@router.post("/device/{device_public_id}/start", response_model=schemas.PatrolBoundLoginResponse, summary="永久裝置開始巡邏（相容舊路由）")
async def start_by_device_public_id(
    device_public_id: str,
    body: schemas.PatrolDeviceStartRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    login_payload = schemas.PatrolDeviceLoginRequest(
        employee_name=body.employee_name,
        password=body.password,
        device_fingerprint=body.device_fingerprint,
    )
    return await login_by_device_public_id(
        device_public_id=device_public_id,
        body=login_payload,
        request=request,
        db=db,
    )


@router.patch("/device/{device_public_id}/password", response_model=schemas.PatrolDevicePasswordUpdateResponse, summary="永久裝置修改密碼")
async def update_device_password_by_public_id(
    device_public_id: str,
    body: schemas.PatrolDevicePasswordUpdateRequest,
    db: AsyncSession = Depends(get_db),
):
    normalized_public_id = device_public_id.strip()
    binding = await db.scalar(
        select(models.PatrolDeviceBinding).where(models.PatrolDeviceBinding.device_public_id == normalized_public_id)
    )
    if not binding:
        raise HTTPException(status_code=404, detail="device not found")
    if not binding.is_bound:
        raise HTTPException(status_code=404, detail="此永久裝置尚未綁定，請先綁定")
    if not binding.password_hash or not _pwd_context.verify(body.current_password.strip(), binding.password_hash):
        raise HTTPException(status_code=401, detail="目前密碼錯誤")
    if body.employee_name and binding.employee_name and body.employee_name.strip() != binding.employee_name:
        raise HTTPException(status_code=401, detail="員工姓名與綁定資料不符")

    now = datetime.utcnow()
    new_hash = _pwd_context.hash(body.new_password.strip())
    binding.password_hash = new_hash
    binding.last_seen_at = now
    await db.execute(
        models.PatrolDevice.__table__.update()
        .where(
            models.PatrolDevice.device_public_id == normalized_public_id,
            models.PatrolDevice.is_active.is_(True),
        )
        .values(password_hash=new_hash)
    )
    await db.flush()
    return schemas.PatrolDevicePasswordUpdateResponse(
        success=True,
        message="密碼修改成功",
        updated_at=now,
    )


@router.post("/device/{device_public_id}/unbind", response_model=schemas.PatrolUnbindResponse, summary="永久裝置解除綁定")
async def unbind_by_device_public_id(
    device_public_id: str,
    body: schemas.PatrolDeviceUnbindRequest,
    db: AsyncSession = Depends(get_db),
):
    normalized_public_id = device_public_id.strip()
    binding = await db.scalar(
        select(models.PatrolDeviceBinding).where(models.PatrolDeviceBinding.device_public_id == normalized_public_id)
    )
    if not binding:
        raise HTTPException(status_code=404, detail="device not found")
    if not binding.is_bound:
        raise HTTPException(status_code=404, detail="找不到有效綁定紀錄")
    if not binding.password_hash or not _pwd_context.verify(body.password.strip(), binding.password_hash):
        raise HTTPException(status_code=401, detail="密碼錯誤，無法解除綁定")
    if body.employee_name and binding.employee_name and body.employee_name.strip() != binding.employee_name:
        raise HTTPException(status_code=401, detail="員工姓名與綁定資料不符")
    now = datetime.utcnow()
    binding.is_bound = False
    binding.is_active = False
    await db.execute(
        models.PatrolDevice.__table__.update()
        .where(
            models.PatrolDevice.device_public_id == normalized_public_id,
            models.PatrolDevice.is_active.is_(True),
        )
        .values(is_active=False, unbound_at=now)
    )
    return schemas.PatrolUnbindResponse(success=True, message="解除綁定成功", unbound_at=now)


@router.post("/unbind", response_model=schemas.PatrolUnbindResponse, summary="解除裝置綁定")
async def unbind_device(
    body: schemas.PatrolUnbindRequest,
    db: AsyncSession = Depends(get_db),
):
    fingerprint_json = _normalize_device_fingerprint(body.device_fingerprint.model_dump())
    device = await db.scalar(
        select(models.PatrolDevice)
        .where(
            models.PatrolDevice.employee_name == body.employee_name.strip(),
            models.PatrolDevice.device_fingerprint == fingerprint_json,
            models.PatrolDevice.is_active.is_(True),
        )
        .order_by(models.PatrolDevice.id.desc())
    )
    if not device:
        raise HTTPException(status_code=404, detail="找不到有效綁定紀錄")
    if not device.password_hash or not _pwd_context.verify(body.password.strip(), device.password_hash):
        raise HTTPException(status_code=401, detail="密碼錯誤，無法解除綁定")
    now = datetime.utcnow()
    device.is_active = False
    device.unbound_at = now
    await db.flush()
    return schemas.PatrolUnbindResponse(success=True, message="解除綁定成功", unbound_at=now)


@router.get("/device-bindings", response_model=schemas.PatrolDeviceBindingAdminListResponse, summary="後台查詢裝置綁定列表")
async def list_device_bindings(
    query: str | None = Query(None),
    employee_name: str | None = Query(None),
    site_name: str | None = Query(None),
    status: str | None = Query(None, description="active/inactive/all"),
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    stmt: Select[tuple[models.PatrolDeviceBinding]] = select(models.PatrolDeviceBinding)
    count_stmt = select(func.count(models.PatrolDeviceBinding.id))

    conds = []
    if query and query.strip():
        q = f"%{query.strip()}%"
        conds.append(
            or_(
                models.PatrolDeviceBinding.device_public_id.ilike(q),
                models.PatrolDeviceBinding.employee_name.ilike(q),
                models.PatrolDeviceBinding.site_name.ilike(q),
            )
        )
    if employee_name and employee_name.strip():
        conds.append(models.PatrolDeviceBinding.employee_name.ilike(f"%{employee_name.strip()}%"))
    if site_name and site_name.strip():
        conds.append(models.PatrolDeviceBinding.site_name.ilike(f"%{site_name.strip()}%"))
    normalized_status = (status or "all").strip().lower()
    if normalized_status == "active":
        conds.append(models.PatrolDeviceBinding.is_active.is_(True))
    elif normalized_status == "inactive":
        conds.append(models.PatrolDeviceBinding.is_active.is_(False))

    if conds:
        stmt = stmt.where(and_(*conds))
        count_stmt = count_stmt.where(and_(*conds))

    stmt = stmt.order_by(models.PatrolDeviceBinding.bound_at.desc(), models.PatrolDeviceBinding.id.desc()).limit(limit).offset(offset)
    items = (await db.scalars(stmt)).all()
    total = int(await db.scalar(count_stmt) or 0)
    latest_device_map: dict[str, models.PatrolDevice] = {}
    for item in items:
        device = await db.scalar(
            select(models.PatrolDevice)
            .where(models.PatrolDevice.device_public_id == item.device_public_id)
            .order_by(models.PatrolDevice.id.desc())
        )
        if device:
            latest_device_map[item.device_public_id] = device
    return schemas.PatrolDeviceBindingAdminListResponse(
        items=[_binding_to_admin_item(i, latest_device_map.get(i.device_public_id)) for i in items],
        total=total,
    )


@router.patch("/device-bindings/{binding_id}/password", response_model=schemas.PatrolDeviceBindingAdminItem, summary="後台重設裝置密碼")
async def admin_reset_device_binding_password(
    binding_id: int,
    body: schemas.PatrolDeviceBindingPasswordResetRequest,
    db: AsyncSession = Depends(get_db),
):
    binding = await db.get(models.PatrolDeviceBinding, binding_id)
    if not binding:
        raise HTTPException(status_code=404, detail="裝置綁定不存在")
    hashed = _pwd_context.hash(body.password.strip())
    binding.password_hash = hashed
    if not binding.bound_at:
        binding.bound_at = datetime.utcnow()
    await db.execute(
        models.PatrolDevice.__table__.update()
        .where(
            models.PatrolDevice.device_public_id == binding.device_public_id,
            models.PatrolDevice.is_active.is_(True),
        )
        .values(password_hash=hashed)
    )
    await db.flush()
    return _binding_to_admin_item(binding)


@router.post("/device-bindings/{binding_id}/unbind", response_model=schemas.PatrolUnbindResponse, summary="後台解除裝置綁定")
async def admin_unbind_device_binding(
    binding_id: int,
    db: AsyncSession = Depends(get_db),
):
    binding = await db.get(models.PatrolDeviceBinding, binding_id)
    if not binding:
        raise HTTPException(status_code=404, detail="裝置綁定不存在")
    if not binding.is_active:
        return schemas.PatrolUnbindResponse(success=True, message="裝置已是解除狀態", unbound_at=datetime.utcnow())
    now = datetime.utcnow()
    binding.is_bound = False
    binding.is_active = False
    await db.execute(
        models.PatrolDevice.__table__.update()
        .where(
            models.PatrolDevice.device_public_id == binding.device_public_id,
            models.PatrolDevice.is_active.is_(True),
        )
        .values(is_active=False, unbound_at=now)
    )
    await db.flush()
    return schemas.PatrolUnbindResponse(success=True, message="後台解除綁定成功", unbound_at=now)


@router.get("/points", response_model=list[schemas.PatrolPointRead], summary="巡邏點列表")
async def list_points(
    site_name: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt: Select[tuple[models.PatrolPoint]] = select(models.PatrolPoint).order_by(models.PatrolPoint.id.desc())
    if site_name and site_name.strip():
        stmt = stmt.where(models.PatrolPoint.site_name.ilike(f"%{site_name.strip()}%"))
    points = (await db.scalars(stmt)).all()
    return [_point_to_read(p) for p in points]


@router.post("/points", response_model=schemas.PatrolPointRead, status_code=201, summary="新增巡邏點")
async def create_point(
    body: schemas.PatrolPointCreate,
    db: AsyncSession = Depends(get_db),
):
    point_name = (body.name or body.point_name or "").strip()
    if not point_name:
        raise HTTPException(status_code=422, detail="巡邏點名稱不可為空")
    site_id = body.site_id
    if site_id is None:
        site_id = await _get_default_patrol_site_id(db)
    point = models.PatrolPoint(
        public_id=str(uuid.uuid4()),
        point_code=body.point_code.strip(),
        point_name=point_name,
        site_id=site_id,
        site_name=(body.site_name or "").strip() or None,
        location=(body.location or "").strip() or None,
        is_active=bool(body.is_active),
    )
    db.add(point)
    try:
        await db.flush()
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="巡邏點編號已存在") from exc
    return _point_to_read(point)


@router.patch("/points/{point_id}", response_model=schemas.PatrolPointRead, summary="更新巡邏點")
async def update_point(
    point_id: int,
    body: schemas.PatrolPointUpdate,
    db: AsyncSession = Depends(get_db),
):
    point = await db.get(models.PatrolPoint, point_id)
    if not point:
        raise HTTPException(status_code=404, detail="巡邏點不存在")
    data = body.model_dump(exclude_unset=True)
    if "point_code" in data and data["point_code"] is not None:
        point.point_code = data["point_code"].strip()
    if "point_name" in data and data["point_name"] is not None:
        point.point_name = data["point_name"].strip()
    if "site_id" in data:
        point.site_id = data["site_id"]
    if "site_name" in data:
        point.site_name = (data["site_name"] or "").strip() or None
    if "location" in data:
        point.location = (data["location"] or "").strip() or None
    if "is_active" in data and data["is_active"] is not None:
        point.is_active = bool(data["is_active"])
    try:
        await db.flush()
    except IntegrityError as exc:
        raise HTTPException(status_code=409, detail="巡邏點編號已存在") from exc
    return _point_to_read(point)


@router.delete("/points/{point_id}", status_code=204, summary="刪除巡邏點")
async def delete_point(
    point_id: int,
    db: AsyncSession = Depends(get_db),
):
    point = await db.get(models.PatrolPoint, point_id)
    if not point:
        raise HTTPException(status_code=404, detail="巡邏點不存在")
    await db.delete(point)


@router.get("/points/{public_id}/qr", response_model=schemas.PatrolPointQrRead, summary="取得巡邏點固定 QR URL")
async def get_point_qr(
    public_id: str,
    db: AsyncSession = Depends(get_db),
):
    point = await db.scalar(select(models.PatrolPoint).where(models.PatrolPoint.public_id == public_id.strip()))
    if not point and public_id.isdigit():
        point = await db.get(models.PatrolPoint, int(public_id))
    if not point:
        raise HTTPException(status_code=404, detail="巡邏點不存在")
    qr_url = _build_point_checkin_url(point.public_id)
    return schemas.PatrolPointQrRead(
        public_id=point.public_id,
        point_code=point.point_code,
        qr_url=qr_url,
        qr_value=qr_url,
    )


@router.post("/checkin/{public_id}", response_model=schemas.PatrolCheckinResponse, summary="固定 public_id 掃碼打卡")
async def checkin_by_public_id(
    public_id: str,
    body: schemas.PatrolPublicCheckinRequest,
    db: AsyncSession = Depends(get_db),
):
    point = await db.scalar(select(models.PatrolPoint).where(models.PatrolPoint.public_id == public_id.strip()))
    if not point:
        raise HTTPException(status_code=404, detail="巡邏點不存在")
    if not point.is_active:
        raise HTTPException(status_code=400, detail="此巡邏點已停用")

    employee_id = body.employee_id
    employee_name = (body.employee_name or "").strip()
    if employee_id is not None:
        employee = await db.get(models.Employee, employee_id)
        if not employee:
            raise HTTPException(status_code=404, detail="員工不存在")
        employee_name = employee.name
    if not employee_name:
        raise HTTPException(status_code=422, detail="請提供 employee_id 或 employee_name")

    when_taipei = body.timestamp or _now_taipei()
    if when_taipei.tzinfo is None:
        when_taipei = when_taipei.replace(tzinfo=TAIPEI)
    else:
        when_taipei = when_taipei.astimezone(TAIPEI)
    when_utc = when_taipei.astimezone(timezone.utc)
    dup = await _check_duplicate_scan(
        db, device_id=None, employee_id=employee_id, employee_name=employee_name,
        point_id=point.id, now_utc=when_utc,
    )
    if dup:
        return JSONResponse(status_code=429, content=dup)
    ampm = "早上" if when_taipei.hour < 12 else ("下午" if when_taipei.hour < 18 else "晚上")
    qr_url = _build_point_checkin_url(point.public_id)
    log = models.PatrolLog(
        device_id=None,
        employee_id=employee_id,
        point_id=point.id,
        site_id=point.site_id,
        employee_name=employee_name,
        site_name=point.site_name or "",
        point_code=point.point_code,
        point_name=point.point_name,
        checkin_date=when_utc.date(),
        checkin_time=when_utc.time().replace(microsecond=0),
        checkin_ampm=ampm,
        qr_value=qr_url,
        device_info=body.device_info,
        created_at=when_utc.replace(tzinfo=None),
    )
    db.add(log)
    await db.flush()
    return schemas.PatrolCheckinResponse(
        id=log.id,
        employee_id=log.employee_id,
        employee_name=log.employee_name,
        site_name=log.site_name,
        point_code=log.point_code,
        point_name=log.point_name,
        checkin_date=log.checkin_date,
        checkin_time=log.checkin_time,
        checkin_ampm=log.checkin_ampm,
        created_at=log.created_at,
    )


@router.post("/checkin", response_model=schemas.PatrolCheckinResponse, summary="巡邏打點")
async def checkin(
    body: schemas.PatrolCheckinRequest,
    authorization: str | None = Header(None, alias="Authorization"),
    x_device_token: str | None = Header(None, alias="X-Device-Token"),
    db: AsyncSession = Depends(get_db),
):
    token = _extract_device_token(authorization, x_device_token)
    device = await _get_device_by_token(db, token)
    point = await _resolve_point_from_qr(db, body.qr_value)

    now_taipei = _now_taipei()
    now_utc = now_taipei.astimezone(timezone.utc)
    dup = await _check_duplicate_scan(
        db, device_id=device.id, employee_id=None, employee_name=device.employee_name,
        point_id=point.id, now_utc=now_utc,
    )
    if dup:
        return JSONResponse(status_code=429, content=dup)
    ampm = "早上" if now_taipei.hour < 12 else ("下午" if now_taipei.hour < 18 else "晚上")
    log = models.PatrolLog(
        device_id=device.id,
        employee_id=None,
        point_id=point.id,
        site_id=point.site_id,
        employee_name=device.employee_name,
        site_name=device.site_name,
        point_code=point.point_code,
        point_name=point.point_name,
        checkin_date=now_utc.date(),
        checkin_time=now_utc.time().replace(microsecond=0),
        checkin_ampm=ampm,
        qr_value=body.qr_value,
        device_info=device.device_fingerprint,
        created_at=now_utc.replace(tzinfo=None),
    )
    db.add(log)
    await db.flush()
    return schemas.PatrolCheckinResponse(
        id=log.id,
        employee_id=log.employee_id,
        employee_name=log.employee_name,
        site_name=log.site_name,
        point_code=log.point_code,
        point_name=log.point_name,
        checkin_date=log.checkin_date,
        checkin_time=log.checkin_time,
        checkin_ampm=log.checkin_ampm,
        created_at=log.created_at,
    )


def _apply_log_filters(
    stmt: Select[tuple[models.PatrolLog]],
    date_from: date | None,
    date_to: date | None,
    employee_name: str | None,
    site_name: str | None,
    point_code: str | None,
) -> Select[tuple[models.PatrolLog]]:
    conds = []
    if date_from:
        conds.append(models.PatrolLog.checkin_date >= date_from)
    if date_to:
        conds.append(models.PatrolLog.checkin_date <= date_to)
    if employee_name and employee_name.strip():
        conds.append(models.PatrolLog.employee_name.ilike(f"%{employee_name.strip()}%"))
    if site_name and site_name.strip():
        conds.append(models.PatrolLog.site_name.ilike(f"%{site_name.strip()}%"))
    if point_code and point_code.strip():
        conds.append(models.PatrolLog.point_code.ilike(f"%{point_code.strip()}%"))
    if conds:
        stmt = stmt.where(and_(*conds))
    return stmt


TAIPEI = ZoneInfo("Asia/Taipei")


def _now_taipei() -> datetime:
    """目前時間（Asia/Taipei）。"""
    return datetime.now(TAIPEI)


def _log_checkin_at_taiwan(log: models.PatrolLog) -> datetime:
    """將 checkin_date + checkin_time 視為 UTC 轉成 Asia/Taipei 的 datetime（查詢／匯出用）。"""
    dt_naive = datetime.combine(log.checkin_date, log.checkin_time)
    utc_dt = dt_naive.replace(tzinfo=timezone.utc)
    return utc_dt.astimezone(TAIPEI)


COOLDOWN_SECONDS = 300  # 5 分鐘內同人同一巡邏點不可重複掃碼


async def _check_duplicate_scan(
    db: AsyncSession,
    *,
    device_id: int | None,
    employee_id: int | None,
    employee_name: str,
    point_id: int,
    now_utc: datetime,
) -> dict | None:
    """若 5 分鐘內有同人同一巡邏點紀錄，回傳錯誤內容 dict；否則回傳 None。"""
    stmt = select(models.PatrolLog).where(models.PatrolLog.point_id == point_id)
    if device_id is not None:
        stmt = stmt.where(models.PatrolLog.device_id == device_id)
    else:
        stmt = stmt.where(models.PatrolLog.device_id.is_(None))
        if employee_id is not None:
            stmt = stmt.where(models.PatrolLog.employee_id == employee_id)
        else:
            stmt = stmt.where(
                models.PatrolLog.employee_id.is_(None),
                models.PatrolLog.employee_name == employee_name,
            )
    stmt = stmt.order_by(models.PatrolLog.created_at.desc()).limit(1)
    last = await db.scalar(stmt)
    if not last or not last.created_at:
        return None
    delta = (now_utc.replace(tzinfo=None) - last.created_at).total_seconds()
    if delta >= COOLDOWN_SECONDS:
        return None
    remaining = int(COOLDOWN_SECONDS - delta)
    last_utc = last.created_at
    if last_utc.tzinfo is None:
        last_utc = last_utc.replace(tzinfo=timezone.utc)
    return {
        "detail": "重複掃碼：請於 5 分鐘後再掃同一巡邏點",
        "cooldown_seconds": max(1, remaining),
        "last_scan_at": last_utc.isoformat(),
    }


def _period_and_time_12h(dt: datetime) -> tuple[str, str]:
    """依 Asia/Taipei 回傳 (早上/下午/晚上, 12 小時制 hh:mm:ss)。"""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=TAIPEI)
    else:
        dt = dt.astimezone(TAIPEI)
    h = dt.hour
    if h < 12:
        period = "早上"
    elif h < 18:
        period = "下午"
    else:
        period = "晚上"
    h12 = h % 12
    if h12 == 0:
        h12 = 12
    time_12h = f"{h12:02d}:{dt.minute:02d}:{dt.second:02d}"
    return period, time_12h


@router.get("/logs", response_model=list[schemas.PatrolLogRead], summary="巡邏紀錄列表")
async def list_logs(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    employee_name: str | None = Query(None),
    site_name: str | None = Query(None),
    point_code: str | None = Query(None),
    limit: int = Query(500, ge=1, le=5000),
    db: AsyncSession = Depends(get_db),
):
    stmt: Select[tuple[models.PatrolLog]] = select(models.PatrolLog).order_by(models.PatrolLog.created_at.desc()).limit(limit)
    stmt = _apply_log_filters(stmt, date_from, date_to, employee_name, site_name, point_code)
    items = (await db.scalars(stmt)).all()
    result = []
    for r in items:
        checkin_at = _log_checkin_at_taiwan(r)
        result.append(
            schemas.PatrolLogRead(
                id=r.id,
                employee_name=r.employee_name,
                site_name=r.site_name,
                point_code=r.point_code,
                point_name=r.point_name,
                checkin_date=r.checkin_date,
                checkin_time=r.checkin_time,
                checkin_ampm=r.checkin_ampm,
                created_at=r.created_at,
                checkin_at=checkin_at,
            )
        )
    return result


@router.get("/logs/export/excel", summary="匯出巡邏紀錄 Excel")
async def export_logs_excel(
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    employee_name: str | None = Query(None),
    site_name: str | None = Query(None),
    point_code: str | None = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt: Select[tuple[models.PatrolLog]] = select(models.PatrolLog).order_by(models.PatrolLog.created_at.desc()).limit(100000)
    stmt = _apply_log_filters(stmt, date_from, date_to, employee_name, site_name, point_code)
    items = (await db.scalars(stmt)).all()

    wb = Workbook()
    ws = wb.active
    ws.title = "巡邏紀錄"
    ws.append(["員工名稱", "日期", "時段", "時間(12小時制)", "案場", "巡邏點編號", "巡邏點名稱"])
    for r in items:
        checkin_at = _log_checkin_at_taiwan(r)
        period, time_12h = _period_and_time_12h(checkin_at)
        ws.append([
            r.employee_name,
            r.checkin_date.isoformat(),
            period,
            time_12h,
            r.site_name,
            r.point_code,
            r.point_name,
        ])
    for col in ws.columns:
        ws.column_dimensions[col[0].column_letter].width = 18
    buf = BytesIO()
    wb.save(buf)
    buf.seek(0)
    filename = f"patrol_logs_{date.today().isoformat()}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
