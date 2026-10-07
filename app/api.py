from datetime import date
from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import func
from sqlalchemy.orm import Session
from .database import get_db
from .models import User, Employee, KPI, Entry
from .schemas import Token, EmployeeSignup, EmployeeCreate, EmployeeOut, EntryUpdate, ReviewUpdate, GenerateRequest, EntryOut
from .auth import verify_password, hash_password, create_token, current_user, require_roles
from .services import calculate, generate_month

router = APIRouter(prefix="/api")

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
