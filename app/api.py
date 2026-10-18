from datetime import date
import json
import mimetypes
from urllib.parse import quote
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session
from .database import get_db
from .models import User, Employee, KPI, Entry
from .schemas import Token, EmployeeSignup, EmployeeCreate, EmployeeOut, EntryUpdate, ReviewUpdate, GenerateRequest, EntryOut, KPIUpdate, KPIOut
from .auth import verify_password, hash_password, create_token, current_user, require_roles
from .services import calculate, generate_month

router = APIRouter(prefix="/api")
CONTEXT_MAGIC = b"HLBCTX1\n"
MAX_CONTEXT_SIZE = 10 * 1024 * 1024
ALLOWED_CONTEXT_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".txt", ".csv", ".png", ".jpg", ".jpeg"}

def _pack_context(filename: str, content_type: str, content: bytes) -> bytes:
    metadata = json.dumps({"filename": filename, "content_type": content_type}, ensure_ascii=False).encode("utf-8")
    return CONTEXT_MAGIC + len(metadata).to_bytes(4, "big") + metadata + content

def _unpack_context(value: bytes) -> tuple[str, str, bytes]:
    if value.startswith(CONTEXT_MAGIC) and len(value) >= len(CONTEXT_MAGIC) + 4:
        start = len(CONTEXT_MAGIC)
        header_size = int.from_bytes(value[start:start + 4], "big")
        header_start = start + 4
        header = json.loads(value[header_start:header_start + header_size].decode("utf-8"))
        return header["filename"], header["content_type"], value[header_start + header_size:]
    return "supporting-document", "application/octet-stream", value

def _check_entry_access(entry: Entry, user: User, db: Session):
    if user.role == "Employee":
        employee = db.query(Employee).filter(func.lower(Employee.email) == user.email.lower()).first()
        if not employee or employee.id != entry.employee_id:
            raise HTTPException(404, "Entry not found")
    elif user.role not in ("Admin", "Manager", "Partner"):
        raise HTTPException(403, "Insufficient permissions")

@router.post("/auth/signup", response_model=Token, status_code=201)
def signup(data: EmployeeSignup, db: Session = Depends(get_db)):
    email = data.email.lower()
    if db.query(User).filter(func.lower(User.email) == email).first():
        raise HTTPException(409, "An account with this email already exists")
    employee = db.query(Employee).filter(func.lower(Employee.email) == email).first()
    if not employee:
        raise HTTPException(403, "Your work email was not found. Ask your administrator to add your employee record first.")
    user = User(email=email, full_name=data.full_name.strip(), password_hash=hash_password(data.password), role="Employee")
    db.add(user)
    db.commit()
    return Token(access_token=create_token(user.email))

@router.post("/auth/token", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(func.lower(User.email) == form.username.lower()).first()
    if not user or not verify_password(form.password, user.password_hash): raise HTTPException(401, "Incorrect credentials")
    return Token(access_token=create_token(user.email))

@router.get("/auth/me")
def me(user: User = Depends(current_user)):
    return {"id": user.id, "email": user.email, "full_name": user.full_name, "role": user.role}

@router.get("/profile")
def employee_profile(user: User = Depends(current_user), db: Session = Depends(get_db)):
    employee = db.query(Employee).filter(func.lower(Employee.email) == user.email.lower()).first()
    if not employee:
        raise HTTPException(404, "No employee profile is linked to this account")
    total_score, actual_sum = (db.query(func.sum(Entry.final_score), func.sum(Entry.actual))
                               .filter(Entry.employee_id == employee.id).one())
    rows = (db.query(Entry.month, func.sum(Entry.final_score), func.sum(Entry.actual))
            .filter(Entry.employee_id == employee.id)
            .group_by(Entry.month).order_by(Entry.month).all())
    return {"employee": {"id": employee.id, "name": employee.name, "email": employee.email,
                          "team": employee.team, "service_line": employee.service_line},
            "total_score": total_score or 0, "actual_sum": actual_sum or 0,
            "points": [{"month": month.isoformat(), "total_score": score or 0, "actual_sum": actual or 0}
                       for month, score, actual in rows]}

@router.get("/employees", response_model=list[EmployeeOut])
def employees(db: Session=Depends(get_db),
               _=Depends(current_user)
               ): return db.query(Employee).all()

@router.get("/kpis", response_model=list[KPIOut])
def list_kpis(db: Session=Depends(get_db), _=Depends(require_roles("Admin"))):
    return db.query(KPI).order_by(KPI.code).all()

@router.patch("/kpis/{kpi_id}", response_model=KPIOut)
def update_kpi(kpi_id: int, data: KPIUpdate, db: Session=Depends(get_db), _=Depends(require_roles("Admin"))):
    kpi = db.get(KPI, kpi_id)
    if not kpi:
        raise HTTPException(404, "KPI not found")
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(400, "No KPI changes provided")
    if any(value is None for field, value in changes.items() if field != "unit_notes"):
        raise HTTPException(422, "KPI name, perspective, weights, and target cannot be empty")
    for field in ("name", "perspective", "unit_notes"):
        if field in changes and changes[field] is not None:
            changes[field] = changes[field].strip() or (None if field == "unit_notes" else "")
    if not changes.get("name", kpi.name).strip() or not changes.get("perspective", kpi.perspective).strip():
        raise HTTPException(422, "KPI name and perspective cannot be blank")
    for field, value in changes.items():
        setattr(kpi, field, value)
    for entry in db.query(Entry).filter(Entry.kpi_id == kpi.id).all():
        calculate(entry, kpi)
    db.commit()
    db.refresh(kpi)
    return kpi

@router.get("/my/entries")
def my_entries(month: date|None=None, user: User=Depends(current_user), db: Session=Depends(get_db)):
    employee = db.query(Employee).filter(func.lower(Employee.email) == user.email.lower()).first()
    if not employee:
        raise HTTPException(404, "No employee profile is linked to this account")
    query = db.query(Entry, KPI).join(KPI, Entry.kpi_id == KPI.id).filter(Entry.employee_id == employee.id)
    if month:
        query = query.filter(Entry.month == month)
    return [{"id": entry.id, "employee_id": entry.employee_id, "kpi_id": entry.kpi_id,
             "month": entry.month, "actual": entry.actual, "performance_pct": entry.performance_pct,
             "score": entry.score, "final_score": entry.final_score, "status": entry.status,
             "employee_comments": entry.employee_comments, "supervisor_comments": entry.supervisor_comments,
             "kpi_name": kpi.name, "kpi_code": kpi.code, "target": kpi.target,
             "unit_notes": kpi.unit_notes, "perspective": kpi.perspective,
             "has_context": entry.context is not None,
             "context_filename": _unpack_context(entry.context)[0] if entry.context else None}
            for entry, kpi in query.order_by(KPI.perspective, KPI.name).all()]


@router.post("/employees", response_model=EmployeeOut)
def add_employee(data: EmployeeCreate, db: Session=Depends(get_db), _=Depends(require_roles("Admin","Partner"))):
#def add_employee(data: EmployeeCreate, db: Session=Depends(get_db), _=Depends(current_user)):
    obj=Employee(**data.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@router.get("/entries", response_model=list[EntryOut])
def entries(month: str|None=None, employee_id: int|None=None, db: Session=Depends(get_db), user:User=Depends(current_user)):
    q=db.query(Entry, Employee.name, KPI.name).join(Employee, Entry.employee_id==Employee.id).join(KPI, Entry.kpi_id==KPI.id)
    if month: q=q.filter(Entry.month==month)
    if user.role == "Employee":
        employee = db.query(Employee).filter(func.lower(Employee.email) == user.email.lower()).first()
        if not employee: raise HTTPException(404, "No employee profile is linked to this account")
        q=q.filter(Entry.employee_id==employee.id)
    elif employee_id:
        q=q.filter(Entry.employee_id==employee_id)
    return [{"id": entry.id, "employee_id": entry.employee_id, "employee_name": employee_name,
             "kpi_id": entry.kpi_id, "kpi_name": kpi_name, "month": entry.month,
             "actual": entry.actual, "performance_pct": entry.performance_pct, "score": entry.score,
             "final_score": entry.final_score, "status": entry.status,
             "has_context": entry.context is not None,
             "context_filename": _unpack_context(entry.context)[0] if entry.context else None}
            for entry, employee_name, kpi_name in q.all()]

@router.post("/entries/{entry_id}/context")
def upload_entry_context(entry_id: int, file: UploadFile=File(...), db: Session=Depends(get_db), user: User=Depends(current_user)):
    entry = db.get(Entry, entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")
    _check_entry_access(entry, user, db)
    if entry.status not in ("Draft", "Rejected"):
        raise HTTPException(400, "Documents can only be added to draft or rejected entries")
    filename = (file.filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    extension = "." + filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if not filename or extension not in ALLOWED_CONTEXT_EXTENSIONS:
        raise HTTPException(415, "Attach a PDF, DOCX, XLSX, TXT, CSV, PNG, or JPG document")
    content = file.file.read(MAX_CONTEXT_SIZE + 1)
    if not content:
        raise HTTPException(400, "The selected document is empty")
    if len(content) > MAX_CONTEXT_SIZE:
        raise HTTPException(413, "Documents must be 10 MB or smaller")
    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
    entry.context = _pack_context(filename, content_type, content)
    db.commit()
    return {"has_context": True, "context_filename": filename, "size": len(content)}

@router.get("/entries/{entry_id}/context")
def download_entry_context(entry_id: int, db: Session=Depends(get_db), user: User=Depends(current_user)):
    entry = db.get(Entry, entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")
    _check_entry_access(entry, user, db)
    if not entry.context:
        raise HTTPException(404, "No document is attached to this entry")
    filename, content_type, content = _unpack_context(entry.context)
    safe_filename = quote(filename, safe="")
    return Response(content=content, media_type=content_type,
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{safe_filename}",
                             "X-Content-Type-Options": "nosniff"})

@router.delete("/entries/{entry_id}/context", status_code=204)
def delete_entry_context(entry_id: int, db: Session=Depends(get_db), user: User=Depends(current_user)):
    entry = db.get(Entry, entry_id)
    if not entry:
        raise HTTPException(404, "Entry not found")
    _check_entry_access(entry, user, db)
    if entry.status not in ("Draft", "Rejected"):
        raise HTTPException(400, "Documents can only be removed from draft or rejected entries")
    entry.context = None
    db.commit()

@router.patch("/entries/{entry_id}", response_model=EntryOut)
def update_entry(entry_id:int, data:EntryUpdate, db:Session=Depends(get_db), user:User=Depends(current_user)):
    obj=db.get(Entry, entry_id)
    if not obj or obj.status not in ("Draft","Rejected"): raise HTTPException(400,"Entry unavailable for editing")
    if user.role == "Employee":
        employee = db.query(Employee).filter(func.lower(Employee.email) == user.email.lower()).first()
        if not employee or obj.employee_id != employee.id: raise HTTPException(404, "Entry not found")
    for k,v in data.model_dump(exclude_unset=True).items(): setattr(obj,k,v)
    calculate(obj, db.get(KPI,obj.kpi_id)); db.commit(); db.refresh(obj); return obj

@router.post("/entries/{entry_id}/submit", response_model=EntryOut)
def submit(entry_id:int, db:Session=Depends(get_db), user:User=Depends(current_user)):
    obj=db.get(Entry,entry_id)
    if not obj or obj.actual is None: raise HTTPException(400,"Actual is required")
    if user.role == "Employee":
        employee = db.query(Employee).filter(func.lower(Employee.email) == user.email.lower()).first()
        if not employee or obj.employee_id != employee.id: raise HTTPException(404, "Entry not found")
    if obj.status not in ("Draft", "Rejected"): raise HTTPException(400, "Entry unavailable for submission")
    obj.status="Submitted"; db.commit(); db.refresh(obj); return obj

@router.patch("/entries/{entry_id}/review", response_model=EntryOut)
def review(entry_id:int, data:ReviewUpdate, db:Session=Depends(get_db), _=Depends(require_roles("Manager","Partner","Admin"))):
    obj=db.get(Entry,entry_id)
    if not obj: raise HTTPException(404,"Entry not found")
    obj.status=data.status; obj.supervisor_comments=data.supervisor_comments; db.commit(); db.refresh(obj); return obj

@router.post("/admin/generate-month")
def generate(data:GenerateRequest, db:Session=Depends(get_db), _=Depends(require_roles("Admin","Partner"))): return {"created":generate_month(db,data.month)}

@router.get("/dashboard")
def dashboard(month:str, db:Session=Depends(get_db), _=Depends(require_roles("Manager","Partner","Admin"))):
    team_rows=(db.query(Employee.team,func.avg(Entry.final_score)).join(Entry).filter(Entry.month==month).group_by(Employee.team).all())
    people=(db.query(Employee.id, Employee.name, Employee.team, func.sum(Entry.final_score), func.sum(Entry.actual))
            .join(Entry).filter(Entry.month==month).group_by(Employee.id).all())
    return {"month":month,"teams":[{"team":x,"average_score":y or 0} for x,y in team_rows],"employees":[{"employee_id":employee_id,"employee":name,"team":team,"total_score":total_score or 0,"sum_actual":sum_actual or 0} for employee_id,name,team,total_score,sum_actual in people]}

@router.get("/dashboard/employee-trend")
def employee_trend(employee_id:int, year:int, db:Session=Depends(get_db), _=Depends(require_roles("Manager","Partner","Admin"))):
    employee = db.get(Employee, employee_id)
    if not employee: raise HTTPException(404, "Employee not found")
    start, end = date(year, 1, 1), date(year + 1, 1, 1)
    rows = (db.query(Entry.month, func.sum(Entry.actual))
              .filter(Entry.employee_id == employee_id, Entry.month >= start, Entry.month < end)
              .group_by(Entry.month).order_by(Entry.month).all())
    actual_by_month = {month.month: actual or 0 for month, actual in rows}
    return {"employee_id":employee.id,"employee":employee.name,"year":year,
            "points":[{"month":date(year, month, 1).isoformat(), "sum_actual":actual_by_month.get(month, 0)} for month in range(1, 13)]}
