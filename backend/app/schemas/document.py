from datetime import datetime
from pydantic import BaseModel
from typing import Literal


class DocumentBase(BaseModel):
    id: int
    original_filename: str
    content_type: str
    status: Literal["uploaded", "processing", "processed", "failed"]
    created_at: datetime

    class Config:
        orm_mode = True
