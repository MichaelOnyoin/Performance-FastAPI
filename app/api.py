from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session
from .database import get_db
from .models import User, Employee, KPI, Entry
from .schemas import Token, EmployeeCreate, EmployeeOut, EntryUpdate, ReviewUpdate, GenerateRequest, EntryOut
from .auth import verify_password, create_token, current_user, require_roles
from .services import calculate, generate_month

router = APIRouter(prefix="/api")

@router.post("/auth/token", response_model=Token)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form.username).first()
    if not user or not verify_password(form.password, user.password_hash): raise HTTPException(401, "Incorrect credentials")
    return Token(access_token=create_token(user.email))

@router.get("/employees", response_model=list[EmployeeOut])
def employees(db: Session=Depends(get_db),
               _=Depends(current_user)
               ): return db.query(Employee).all()


@router.post("/employees", response_model=EmployeeOut)
# def add_employee(data: EmployeeCreate, db: Session=Depends(get_db), _=Depends(require_roles("Admin","Partner"))):
def add_employee(data: EmployeeCreate, db: Session=Depends(get_db), _=Depends(current_user)):
    obj=Employee(**data.model_dump()); db.add(obj); db.commit(); db.refresh(obj); return obj

@router.get("/entries", response_model=list[EntryOut])
def entries(month: str|None=None, employee_id: int|None=None, db: Session=Depends(get_db), _=Depends(current_user)):
    q=db.query(Entry)
    if month: q=q.filter(Entry.month==month)
    if employee_id: q=q.filter(Entry.employee_id==employee_id)
    return q.all()

@router.patch("/entries/{entry_id}", response_model=EntryOut)
def update_entry(entry_id:int, data:EntryUpdate, db:Session=Depends(get_db), _=Depends(current_user)):
    obj=db.get(Entry, entry_id)
    if not obj or obj.status not in ("Draft","Rejected"): raise HTTPException(400,"Entry unavailable for editing")
    for k,v in data.model_dump(exclude_unset=True).items(): setattr(obj,k,v)
    calculate(obj, db.get(KPI,obj.kpi_id)); db.commit(); db.refresh(obj); return obj

@router.post("/entries/{entry_id}/submit", response_model=EntryOut)
def submit(entry_id:int, db:Session=Depends(get_db), _=Depends(current_user)):
    obj=db.get(Entry,entry_id)
    if not obj or obj.actual is None: raise HTTPException(400,"Actual is required")
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
    people=(db.query(Employee.name,Employee.team,func.sum(Entry.final_score)).join(Entry).filter(Entry.month==month).group_by(Employee.id).all())
    return {"month":month,"teams":[{"team":x,"average_score":y or 0} for x,y in team_rows],"employees":[{"employee":x,"team":t,"total_score":s or 0} for x,t,s in people]}
