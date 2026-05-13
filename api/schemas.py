"""
api/schemas.py
"""
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class Probabilities(BaseModel):
    aadhaar: float
    pan: float
    other: float


class ClassificationResponse(BaseModel):
    id: int
    image_name: str
    image_url: str
    image_size: Optional[int]
    image_type: Optional[str]
    classification: str
    confidence: float
    probabilities: Probabilities
    is_uncertain: bool
    deleted: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}

    @classmethod
    def from_db(cls, obj):
        return cls(
            id=obj.id,
            image_name=obj.image_name,
            image_url=obj.image_url,
            image_size=obj.image_size,
            image_type=obj.image_type,
            classification=obj.classification,
            confidence=obj.confidence,
            probabilities=Probabilities(
                aadhaar=obj.prob_aadhaar,
                pan=obj.prob_pan,
                other=obj.prob_other,
            ),
            is_uncertain=obj.is_uncertain,
            deleted=obj.deleted,
            created_at=obj.created_at,
            updated_at=obj.updated_at,
        )


class ClassificationListResponse(BaseModel):
    total: int
    items: list[ClassificationResponse]


class DeleteResponse(BaseModel):
    id: int
    deleted: bool
    message: str


class StatsResponse(BaseModel):
    total_classifications: int
    by_label: dict
    average_confidence: float
    uncertain_count: int
