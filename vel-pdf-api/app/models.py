"""
Pydantic models for API request/response.
"""

from pydantic import BaseModel
from typing import Optional


class UploadResponse(BaseModel):
    session_id: str
    message: str
    total_files: int


class ProgressMessage(BaseModel):
    current: int
    total: int
    status: str
    message: str
    elapsed_time: Optional[float] = None


class DownloadInfo(BaseModel):
    filename: str
    total_records: int