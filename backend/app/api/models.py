from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Any


class QueryRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    question: str = Field(min_length=1, max_length=2000)
    schema_name: str = Field(default="ecommerce", min_length=1, max_length=100)
    max_attempts: int = Field(default=3, ge=1, le=5)

class QueryResponse(BaseModel):
    sql: Optional[str]
    success: bool
    attempts: int
    first_attempt_success: bool
    latency_ms: float
    schema_tables_used: list[str]
    correction_applied: bool
    rows: Optional[list[Any]]
    columns: list[str] = Field(default_factory=list)
    row_count: int
    error_type: Optional[str]
    error_message: Optional[str]

   
