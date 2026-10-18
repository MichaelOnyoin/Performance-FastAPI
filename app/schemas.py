from datetime import date
from pydantic import BaseModel, ConfigDict, EmailStr, Field

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class EmployeeSignup(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)

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

class KPIUpdate(BaseModel):
    name: str|None = Field(default=None, min_length=1, max_length=500)
    perspective: str|None = Field(default=None, min_length=1, max_length=255)
    perspective_weight: float|None = Field(default=None, ge=0)
    kpi_weight: float|None = Field(default=None, ge=0)
    target: float|None = None
    unit_notes: str|None = Field(default=None, max_length=255)

class KPIOut(BaseModel):
    id: int
    code: str
    name: str
    perspective: str
    perspective_weight: float
    kpi_weight: float
    target: float
    unit_notes: str|None
    model_config = ConfigDict(from_attributes=True)

class EntryOut(BaseModel):
    id: int
    employee_id: int
    employee_name: str|None = None
    kpi_id: int
    kpi_name: str|None = None
    month: date
    actual: float|None
    performance_pct: float|None
    score: float|None
    final_score: float|None
    status: str
    has_context: bool = False
    context_filename: str|None = None
    model_config = ConfigDict(from_attributes=True)
