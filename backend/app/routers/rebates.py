"""案場回饋 API：單筆更新/刪除、回饋依據 PDF 上傳/下載。"""
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app import crud, schemas
from app.services.upload_site_files import save_site_pdf, resolve_site_file_path

router = APIRouter(prefix="/api/rebates", tags=["rebates"])

RESPONSE_404 = {404: {"description": "資源不存在"}}
MAX_SIZE = settings.max_upload_size_mb * 1024 * 1024


@router.patch(
    "/{rebate_id}",
    response_model=schemas.SiteRebateRead,
    summary="更新案場回饋",
    responses={**RESPONSE_404},
)
async def update_rebate(
    rebate_id: int,
    data: schemas.SiteRebateUpdate,
    db: AsyncSession = Depends(get_db),
):
    rebate = await crud.get_rebate(db, rebate_id)
    if not rebate:
        raise HTTPException(status_code=404, detail="回饋紀錄不存在")
    rebate = await crud.update_rebate(db, rebate, data)
    return schemas.SiteRebateRead.model_validate(rebate)


@router.delete(
    "/{rebate_id}",
    status_code=204,
    summary="刪除案場回饋",
    responses={**RESPONSE_404},
)
async def delete_rebate(
    rebate_id: int,
    db: AsyncSession = Depends(get_db),
):
    rebate = await crud.get_rebate(db, rebate_id)
    if not rebate:
        raise HTTPException(status_code=404, detail="回饋紀錄不存在")
    await crud.delete_rebate(db, rebate)


@router.post(
    "/{rebate_id}/receipt",
    response_model=schemas.SiteRebateRead,
    summary="上傳回饋依據 PDF",
    responses={**RESPONSE_404},
)
async def upload_rebate_receipt(
    rebate_id: int,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    rebate = await crud.get_rebate(db, rebate_id)
    if not rebate:
        raise HTTPException(status_code=404, detail="回饋紀錄不存在")
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="僅接受 PDF 檔案")
    content = await file.read()
    if len(content) > MAX_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"檔案大小不得超過 {settings.max_upload_size_mb} MB",
        )
    rel_path = save_site_pdf(
        rebate.site_id,
        "rebates",
        rebate_id,
        content,
        file.filename or "receipt.pdf",
    )
    rebate = await crud.set_rebate_receipt_path(db, rebate_id, rel_path)
    return schemas.SiteRebateRead.model_validate(rebate)


@router.get(
    "/{rebate_id}/receipt",
    summary="下載/預覽回饋依據 PDF",
    responses={**RESPONSE_404},
)
async def get_rebate_receipt(
    rebate_id: int,
    db: AsyncSession = Depends(get_db),
):
    rebate = await crud.get_rebate(db, rebate_id)
    if not rebate or not rebate.receipt_pdf_path:
        raise HTTPException(status_code=404, detail="回饋依據檔案不存在")
    path = resolve_site_file_path(rebate.receipt_pdf_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="檔案已遺失")
    return FileResponse(
        path,
        filename=Path(rebate.receipt_pdf_path).name,
        media_type="application/pdf",
    )
