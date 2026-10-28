from datetime import date
from typing import Literal
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator

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

class UserRoleUpdate(BaseModel):
    role: Literal["Admin", "Partner", "Employee", "Manager"]

class UserOut(BaseModel):
    id: int
    # email: EmailStr
    email: str
    full_name: str
    role: str
    company: str|None = None
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

    # @field_validator("email")
    # @classmethod
    # def validate_email(cls, value: str) -> str:
    #     if value.endswith(".local"):
    #         if "@" not in value:
    #             raise ValueError("Invalid internal email address")

    #         local_part, domain = value.rsplit("@", 1)

    #         if not local_part or not domain or "." not in domain:
    #             raise ValueError("Invalid internal email address")

    #         return value

class EntryUpdate(BaseModel):
    actual: float|None = None
    employee_comments: str|None = None

class ReviewUpdate(BaseModel):
    status: str = Field(pattern="^(Approved|Rejected)$")
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

class KPICreate(BaseModel):
    code: str = Field(min_length=1, max_length=50)
    name: str = Field(min_length=1, max_length=500)
    perspective: str = Field(min_length=1, max_length=255)
    perspective_weight: float = Field(ge=0)
    kpi_weight: float = Field(ge=0)
    target: float = Field(ge=0)
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

class EmployeeKPIAssignment(BaseModel):
    kpi_id: int
    target: float

class EmployeeKPIAssignmentUpdate(BaseModel):
    assignments: list[EmployeeKPIAssignment]

class EntryOut(BaseModel):
    id: int
    employee_id: int
    employee_name: str|None = None
    kpi_id: int
    kpi_name: str|None = None
    month: date
    actual: float|None
    target: float|None = None
    performance_pct: float|None
    score: float|None
    final_score: float|None
    status: str
    employee_comments: str|None = None
    supervisor_comments: str|None = None
    has_context: bool = False
    context_filename: str|None = None
    model_config = ConfigDict(from_attributes=True)
