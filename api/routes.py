"""
api/routes.py — All endpoints
"""
from typing import Optional
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from api.database import get_db
from api.models import Classification
from api.schemas import (
    ClassificationResponse,
    ClassificationListResponse,
    DeleteResponse,
    StatsResponse,
)
from api.classifier import get_classifier
from api.storage import get_storage

router = APIRouter(prefix="/api/v1", tags=["DocuLens"])

ALLOWED_TYPES = {"image/jpeg", "image/png", "image/bmp", "image/webp"}
MAX_SIZE      = 10 * 1024 * 1024  # 10MB


# ─── POST /classify ───────────────────────────────────────────────────────────
@router.post("/classify", response_model=ClassificationResponse, status_code=201)
async def classify(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(415, f"Unsupported type: {file.content_type}")

    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(400, "Empty file")
    if len(file_bytes) > MAX_SIZE:
        raise HTTPException(413, "File exceeds 10MB")

    # Upload to MinIO
    storage = get_storage()
    try:
        object_name, image_url = storage.upload(file_bytes, file.filename, file.content_type)
    except Exception as e:
        raise HTTPException(503, f"Storage error: {e}")

    # Classify
    try:
        result = get_classifier().predict(file_bytes)
    except Exception as e:
        storage.delete(object_name)
        raise HTTPException(500, f"Classification error: {e}")

    # Save to DB — ID is auto-assigned (1, 2, 3, 4...)
    ext = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else "unknown"
    record = Classification(
        image_name     = file.filename,
        image_url      = image_url,
        image_size     = len(file_bytes),
        image_type     = ext,
        classification = result["classification"],
        confidence     = result["confidence"],
        prob_aadhaar   = result["probabilities"]["aadhaar"],
        prob_pan       = result["probabilities"]["pan"],
        prob_other     = result["probabilities"]["other"],
        is_uncertain   = result["is_uncertain"],
        deleted        = False,
    )
    db.add(record)
    await db.flush()
    await db.refresh(record)

    return ClassificationResponse.from_db(record)


# ─── GET /classifications ─────────────────────────────────────────────────────
@router.get("/classifications", response_model=ClassificationListResponse)
async def list_classifications(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    label: Optional[str] = Query(None, description="aadhaar | pan | other"),
    include_deleted: bool = Query(False),
    db: AsyncSession = Depends(get_db),
):
    query = select(Classification)

    if not include_deleted:
        query = query.where(Classification.deleted == False)
    if label:
        if label not in ["aadhaar", "pan", "other"]:
            raise HTTPException(400, "label must be: aadhaar, pan, or other")
        query = query.where(Classification.classification == label)

    total = (await db.execute(
        select(func.count()).select_from(query.subquery())
    )).scalar()

    results = (await db.execute(
        query.order_by(Classification.id.asc()).offset(skip).limit(limit)
    )).scalars().all()

    return ClassificationListResponse(
        total=total,
        items=[ClassificationResponse.from_db(r) for r in results],
    )


# ─── GET /classifications/{id} ────────────────────────────────────────────────
@router.get("/classifications/{id}", response_model=ClassificationResponse)
async def get_classification(id: int, db: AsyncSession = Depends(get_db)):
    record = await db.get(Classification, id)
    if not record:
        raise HTTPException(404, f"No record found with ID {id}")
    if record.deleted:
        raise HTTPException(410, f"Record {id} has been deleted")
    return ClassificationResponse.from_db(record)


# ─── DELETE /classifications/{id} ────────────────────────────────────────────
@router.delete("/classifications/{id}", response_model=DeleteResponse)
async def delete_classification(id: int, db: AsyncSession = Depends(get_db)):
    record = await db.get(Classification, id)
    if not record:
        raise HTTPException(404, f"No record found with ID {id}")
    if record.deleted:
        raise HTTPException(410, f"Record {id} already deleted")

    record.deleted = True
    await db.flush()

    return DeleteResponse(
        id=record.id,
        deleted=True,
        message=f"Record {id} soft-deleted. Image still in MinIO.",
    )


# ─── GET /stats ───────────────────────────────────────────────────────────────
@router.get("/stats", response_model=StatsResponse)
async def stats(db: AsyncSession = Depends(get_db)):
    base = select(Classification).where(Classification.deleted == False)

    total = (await db.execute(
        select(func.count()).select_from(base.subquery())
    )).scalar()

    by_label = {}
    for label in ["aadhaar", "pan", "other"]:
        count = (await db.execute(
            select(func.count()).select_from(
                base.where(Classification.classification == label).subquery()
            )
        )).scalar()
        by_label[label] = count

    avg_conf = (await db.execute(
        select(func.avg(Classification.confidence)).where(Classification.deleted == False)
    )).scalar() or 0.0

    uncertain = (await db.execute(
        select(func.count()).select_from(
            base.where(Classification.is_uncertain == True).subquery()
        )
    )).scalar()

    return StatsResponse(
        total_classifications=total,
        by_label=by_label,
        average_confidence=round(float(avg_conf), 4),
        uncertain_count=uncertain,
    )
