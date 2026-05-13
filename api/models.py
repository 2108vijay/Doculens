"""
api/models.py — Auto-increment integer ID (1, 2, 3, 4...)
"""
from datetime import datetime, timezone
from sqlalchemy import String, Float, Boolean, DateTime, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column
from api.database import Base


class Classification(Base):
    __tablename__ = "classifications"

    # Auto-increment integer ID — 1, 2, 3, 4...
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # Image details
    image_name: Mapped[str]   = mapped_column(String(255), nullable=False)
    image_url: Mapped[str]    = mapped_column(Text, nullable=False)
    image_size: Mapped[int]   = mapped_column(Integer, nullable=True)
    image_type: Mapped[str]   = mapped_column(String(20), nullable=True)

    # Classification result
    classification: Mapped[str]  = mapped_column(String(20), nullable=False)
    confidence: Mapped[float]    = mapped_column(Float, nullable=False)

    # Per-class probabilities
    prob_aadhaar: Mapped[float]  = mapped_column(Float, default=0.0)
    prob_pan: Mapped[float]      = mapped_column(Float, default=0.0)
    prob_other: Mapped[float]    = mapped_column(Float, default=0.0)

    # Flags
    is_uncertain: Mapped[bool]   = mapped_column(Boolean, default=False)
    deleted: Mapped[bool]        = mapped_column(Boolean, default=False)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )
