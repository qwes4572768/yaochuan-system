"""登入與權限：簡易帳密驗證，回傳 access_token；供前端 Bearer 帶入。"""
import os
import secrets
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/api/auth", tags=["auth"])

# 預設 demo：admin123 / admin456；上線可改環境變數 ADMIN_USERNAME / ADMIN_PASSWORD
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin123")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin456")


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str


class MeResponse(BaseModel):
    username: str
    role: str = "admin"


@router.post("/login", response_model=LoginResponse)
async def login(body: LoginRequest):
    """帳密驗證：admin123 / admin456 回傳 access_token，否則 401。"""
    if body.username.strip() == ADMIN_USERNAME and body.password == ADMIN_PASSWORD:
        token = secrets.token_urlsafe(32)
        return LoginResponse(access_token=token)
    raise HTTPException(status_code=401, detail="帳號或密碼錯誤")


@router.get("/me", response_model=MeResponse)
async def me():
    """目前登入者資訊（前端可選用；後端可後續改為驗證 Bearer token 回傳對應使用者）。"""
    return MeResponse(username=ADMIN_USERNAME, role="admin")
