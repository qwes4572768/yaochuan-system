"""案場每月入帳 API：單筆更新、匯款證明 PDF 上傳/下載。"""
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app import crud, schemas
from app.services.upload_site_files import save_site_pdf, resolve_site_file_path

router = APIRouter(prefix="/api/monthly-receipts", tags=["monthly-receipts"])

RESPONSE_404 = {404: {"description": "資源不存在"}}
MAX_SIZE = settings.max_upload_size_mb * 1024 * 1024


@router.patch(
    "/{receipt_id}",
    response_model=schemas.SiteMonthlyReceiptRead,
    summary="更新每月入帳",
    responses={**RESPONSE_404},
)
async def update_monthly_receipt(
    receipt_id: int,
    data: schemas.SiteMonthlyReceiptUpdate,
    db: AsyncSession = Depends(get_db),
):
    rec = await crud.get_monthly_receipt(db, receipt_id)
    if not rec:
        raise HTTPException(status_code=404, detail="入帳紀錄不存在")
    rec = await crud.update_monthly_receipt(db, rec, data)
    return schemas.SiteMonthlyReceiptRead.model_validate(rec)


@router.post(
    "/{receipt_id}/proof",
    response_model=schemas.SiteMonthlyReceiptRead,
    summary="上傳匯款證明 PDF",
    responses={**RESPONSE_404},
)
async def upload_monthly_receipt_proof(
    receipt_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    rec = await crud.get_monthly_receipt(db, receipt_id)
    if not rec:
        raise HTTPException(status_code=404, detail="入帳紀錄不存在")
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="僅接受 PDF 檔案")
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"檔案大小不得超過 {settings.max_upload_size_mb} MB",
        )
    rel_path = save_site_pdf(
        rec.site_id,
        "monthly_receipts",
        receipt_id,
        content,
        file.filename or "proof.pdf",
    )
    rec = await crud.set_monthly_receipt_proof_path(db, receipt_id, rel_path)
    return schemas.SiteMonthlyReceiptRead.model_validate(rec)


@router.get(
    "/{receipt_id}/proof",
    summary="下載/預覽匯款證明 PDF",
    responses={**RESPONSE_404},
)
async def get_monthly_receipt_proof(
    receipt_id: int,
    db: AsyncSession = Depends(get_db),
):
    rec = await crud.get_monthly_receipt(db, receipt_id)
    if not rec or not rec.proof_pdf_path:
        raise HTTPException(status_code=404, detail="匯款證明檔案不存在")
    path = resolve_site_file_path(rec.proof_pdf_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="檔案已遺失")
    return FileResponse(
        path,
        filename=Path(rec.proof_pdf_path).name,
        media_type="application/pdf",
    )
