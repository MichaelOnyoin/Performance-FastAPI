from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from .config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

class Base(DeclarativeBase):
    pass

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def ensure_schema():
    """Apply the small additive migrations needed by existing development databases."""
    from .models import Entry

    inspector = inspect(engine)
    if not inspector.has_table("entries") or not inspector.has_table("kpis") or not inspector.has_table("employee_kpis"):
        return
    existing_columns = {column["name"] for column in inspector.get_columns("entries")}
    required_columns = {
        "context": Entry.__table__.c.context.type,
        "target_snapshot": Entry.__table__.c.target_snapshot.type,
    }
    with engine.begin() as connection:
        for column_name, column_type in required_columns.items():
            if column_name not in existing_columns:
                compiled_type = column_type.compile(dialect=engine.dialect)
                connection.execute(text(f"ALTER TABLE entries ADD COLUMN {column_name} {compiled_type}"))

        # Existing employee/KPI pairs become their initial assignments at the old catalog target.
        connection.execute(text("""
            INSERT INTO employee_kpis (employee_id, kpi_id, target, is_active)
            SELECT DISTINCT entries.employee_id, entries.kpi_id, kpis.target, 1
            FROM entries JOIN kpis ON kpis.id = entries.kpi_id
            WHERE NOT EXISTS (
                SELECT 1 FROM employee_kpis
                WHERE employee_kpis.employee_id = entries.employee_id
                  AND employee_kpis.kpi_id = entries.kpi_id
            )
        """))
        connection.execute(text("""
            UPDATE entries
            SET target_snapshot = COALESCE(
                (SELECT employee_kpis.target FROM employee_kpis
                 WHERE employee_kpis.employee_id = entries.employee_id
                   AND employee_kpis.kpi_id = entries.kpi_id),
                (SELECT kpis.target FROM kpis WHERE kpis.id = entries.kpi_id)
            )
            WHERE target_snapshot IS NULL
        """))



