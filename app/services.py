from sqlalchemy.orm import Session
from .models import Entry, Employee, KPI

def calculate(entry: Entry, kpi: KPI):
    if entry.actual is None or not kpi.target:
        entry.performance_pct = entry.score = entry.final_score = None
        return
    entry.performance_pct = entry.actual / kpi.target * 100
    ratio = entry.actual / kpi.target
    entry.score = 5 if ratio >= 1.2 else 4 if ratio >= 1.0 else 3 if ratio >= .8 else 2 if ratio >= .6 else 1
    entry.final_score = entry.score * kpi.perspective_weight * kpi.kpi_weight

def generate_month(db: Session, month):
    created = 0
    for emp in db.query(Employee).all():
        for kpi in db.query(KPI).all():
            exists = db.query(Entry).filter_by(employee_id=emp.id, kpi_id=kpi.id, month=month).first()
            if not exists:
                db.add(Entry(employee_id=emp.id, kpi_id=kpi.id, month=month, status="Draft")); created += 1
    db.commit()
    return created
