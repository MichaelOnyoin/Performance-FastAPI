from sqlalchemy.orm import Session
from .models import Entry, KPI, EmployeeKPI, Employee

def calculate(entry: Entry, kpi: KPI, assignment: EmployeeKPI|None=None):
    target = entry.target_snapshot if entry.target_snapshot is not None else kpi.target
    if entry.actual is None or target is None or target == 0:
        entry.performance_pct = entry.score = entry.final_score = None
        return
    entry.performance_pct = entry.actual / target * 100
    #entry.score = 5 if ratio >= 1.2 else 4 if ratio >= 1.0 else 3 if ratio >= .8 else 2 if ratio >= .6 else 1
    entry.score = (
    1 if entry.performance_pct <= 25 else
    2 if 25 < entry.performance_pct <= 50 else
    3 if 50 < entry.performance_pct <= 75 else
    4 if 75 < entry.performance_pct < 90 else
    5 if entry.performance_pct >= 90 else
    None
    )
    perspective_weight = assignment.perspective_weight if assignment and assignment.perspective_weight is not None else kpi.perspective_weight
    kpi_weight = assignment.kpi_weight if assignment and assignment.kpi_weight is not None else kpi.kpi_weight
    entry.final_score = entry.score * perspective_weight * kpi_weight

def generate_month(db: Session, month):
    created = 0
    assignments = (db.query(EmployeeKPI).join(Employee, EmployeeKPI.employee_id == Employee.id)
                   .filter(EmployeeKPI.is_active.is_(True), Employee.is_active.is_(True)).all())
    for assignment in assignments:
        exists = db.query(Entry).filter_by(employee_id=assignment.employee_id, kpi_id=assignment.kpi_id, month=month).first()
        if not exists:
            db.add(Entry(employee_id=assignment.employee_id, kpi_id=assignment.kpi_id, month=month,
                         target_snapshot=assignment.target, status="Draft"))
            created += 1
        elif exists.target_snapshot is None and exists.status in ("Draft", "Rejected"):
            exists.target_snapshot = assignment.target
            calculate(exists, db.get(KPI, assignment.kpi_id), assignment)
    db.commit()
    return created
