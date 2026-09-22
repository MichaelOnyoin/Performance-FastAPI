import sys, pandas as pd
from pathlib import Path
from .database import Base, engine, SessionLocal
from .models import Employee, KPI, Entry

def clean(v): return None if pd.isna(v) else v

def run(path):
    path=Path(path); Base.metadata.create_all(bind=engine); db=SessionLocal()
    try:
        employees=pd.read_excel(path,sheet_name="Employees",engine="openpyxl")
        kpis=pd.read_excel(path,sheet_name="KPI_Definitions",engine="openpyxl")
        entries=pd.read_excel(path,sheet_name="Entries",engine="openpyxl")
        for _,r in employees.iterrows():
            #name=str(r["Employee_ID"]).strip(); obj=db.query(Employee).filter_by(name=name).first()
            name=str(clean(r.get("name"))); obj=db.query(Employee).filter_by(name=name).first()
            vals=dict(email=str(clean(r.get("email"))),team=str(clean(r.get("team")) or "Unassigned"),service_line=str(clean(r.get("service_line")) or "Unassigned"),reviewer=clean(r.get("reviewer")))
            if obj:
                for k,v in vals.items(): setattr(obj,k,v)
            else: db.add(Employee(name=name,**vals))
        db.flush()
        for _,r in kpis.iterrows():
            code=str(r["KPI_ID"]).strip(); obj=db.query(KPI).filter_by(code=code).first()
            vals=dict(name=str(r["KPI"]),perspective=str(r["Perspective"]),perspective_weight=float(r["PerspectiveWeight"]),kpi_weight=float(r["KPIWeight"]),target=float(r["Target"]),unit_notes=clean(r.get("Unit/Notes")))
            if obj:
                for k,v in vals.items(): setattr(obj,k,v)
            else: db.add(KPI(code=code,**vals))
        db.flush()
        for _,r in entries.iterrows():
            emp=db.query(Employee).filter_by(name=str(r["Employee"]).strip()).first(); kpi=db.query(KPI).filter_by(code=str(r["KPI_ID"]).strip()).first()
            if not emp or not kpi or pd.isna(r["Month"]): continue
            month=pd.to_datetime(r["Month"]).date(); obj=db.query(Entry).filter_by(employee_id=emp.id,kpi_id=kpi.id,month=month).first()
            vals=dict(actual=clean(r.get("Actual")),performance_pct=clean(r.get("Performance %")),score=clean(r.get("Score (1-5)")),final_score=clean(r.get("Final Score")),employee_comments=clean(r.get("Employee Comments")),supervisor_comments=clean(r.get("Supervisor Comments")),status=str(clean(r.get("Status")) or "Draft"))
            if obj:
                for k,v in vals.items(): setattr(obj,k,v)
            else: db.add(Entry(employee_id=emp.id,kpi_id=kpi.id,month=month,**vals))
        db.commit(); print("Workbook import complete.")
    finally: db.close()

if __name__=="__main__":
    if len(sys.argv)!=2: raise SystemExit("Usage: python -m app.import_excel workbook.xlsx")
    run(sys.argv[1])
