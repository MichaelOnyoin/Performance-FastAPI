from datetime import date
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class EmployeeCreate(BaseModel):
    name: str
    email: EmailStr|None = None
    team: str
    service_line: str
    reviewer: str|None = None

class EmployeeOut(EmployeeCreate):
    id: int
    model_config = ConfigDict(from_attributes=True)

class EntryUpdate(BaseModel):
    actual: float|None = None
    employee_comments: str|None = None

class ReviewUpdate(BaseModel):
    status: str = Field(pattern="^(Reviewed|Approved|Rejected)$")
    supervisor_comments: str|None = None

class GenerateRequest(BaseModel):
    month: date

class EntryOut(BaseModel):
    id: int
    employee_id: int
    kpi_id: int
    month: date
    actual: float|None
    performance_pct: float|None
    score: float|None
    final_score: float|None
    status: str
    model_config = ConfigDict(from_attributes=True)
