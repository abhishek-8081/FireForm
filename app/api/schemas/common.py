from pydantic import BaseModel
from typing import Any

class SuccessResponse(BaseModel):
    success: bool = True
    data: Any

class ErrorDetail(BaseModel):
    code: str
    message: str

class ErrorResponse(BaseModel):
    success: bool = False
    error: ErrorDetail