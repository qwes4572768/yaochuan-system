"""員工檔案上傳：安全查核 PDF、84-1 PDF"""
import os
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app import crud
from app.schemas import DocumentRead

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_TYPES = {"security_check", "84_1"}
MAX_SIZE = settings.max_upload_size_mb * 1024 * 1024


@router.get("/employee/{employee_id}", response_model=list[DocumentRead])
async def list_employee_documents(employee_id: int, db: AsyncSession = Depends(get_db)):
    emp = await crud.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="員工不存在")
    return await crud.list_documents_by_employee(db, employee_id)


@router.post("/employee/{employee_id}/upload", response_model=DocumentRead, status_code=201)
async def upload_document(
    employee_id: int,
    document_type: str = Form(..., description="security_check 或 84_1"),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if document_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="document_type 須為 security_check 或 84_1")
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="僅接受 PDF 檔案")
    allowed_content = ("application/pdf", "application/octet-stream")
    if file.content_type and file.content_type.lower() not in allowed_content:
        raise HTTPException(status_code=400, detail="僅接受 application/pdf")

    emp = await crud.get_employee(db, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="員工不存在")

    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(status_code=400, detail=f"檔案大小不得超過 {settings.max_upload_size_mb} MB")

    upload_dir = settings.upload_dir / str(employee_id)
    upload_dir.mkdir(parents=True, exist_ok=True)
    ext = Path(file.filename or "file").suffix
    safe_name = f"{document_type}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = upload_dir / safe_name
    with open(file_path, "wb") as f:
        f.write(content)

    doc = await crud.add_document(
        db,
        employee_id=employee_id,
        document_type=document_type,
        file_name=file.filename or safe_name,
        file_path=str(file_path),
        file_size=len(content),
    )
    return doc


@router.get("/{doc_id}/download")
async def download_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    doc = await crud.get_document(db, doc_id)
    if not doc:
        raise HTTPException(status_code=404, detail="檔案不存在")
    path = Path(doc.file_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="檔案已遺失")
    return FileResponse(path, filename=doc.file_name, media_type="application/pdf")
