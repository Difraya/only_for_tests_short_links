from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime

class LinkBase(BaseModel):
    original_url: HttpUrl
    custom_alias: Optional[str] = None
    expires_at: Optional[datetime] = None

class LinkCreate(LinkBase):
    pass

class LinkUpdate(LinkBase):
    pass

class LinkResponse(LinkBase):
    id: int
    short_code: str
    original_url: str
    user_id: int
    clicks: Optional[int] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    short_url: Optional[str] = None

    class Config:
        from_attributes = True 