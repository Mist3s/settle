"""Pydantic schemas for Settings entity."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SettingResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    user_id: UUID
    key: str
    value: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime


class SettingItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(..., max_length=64)
    value: str
    description: str | None = None


class SettingsUpdate(BaseModel):
    """Batch update: list of key/value pairs."""

    model_config = ConfigDict(extra="forbid")

    items: list[SettingItem]
