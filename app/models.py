from datetime import date, datetime
from sqlalchemy import String, Float, ForeignKey, Date, DateTime, Text, LargeBinary, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(30), default="Employee")
    is_active: Mapped[bool] = mapped_column(default=True)
    company: Mapped[str] = mapped_column(String(255))

class Employee(Base):
    __tablename__ = "employees"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    email: Mapped[str|None] = mapped_column(String(255), unique=True, nullable=True)
    team: Mapped[str] = mapped_column(String(255), index=True)
    service_line: Mapped[str] = mapped_column(String(255), index=True)
    reviewer: Mapped[str|None] = mapped_column(String(255), nullable=True)
    entries: Mapped[list["Entry"]] = relationship(back_populates="employee")

class KPI(Base):
    __tablename__ = "kpis"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(500))
    perspective: Mapped[str] = mapped_column(String(255))
    perspective_weight: Mapped[float] = mapped_column(Float)
    kpi_weight: Mapped[float] = mapped_column(Float)
    target: Mapped[float] = mapped_column(Float)
    unit_notes: Mapped[str|None] = mapped_column(String(255), nullable=True)
    #context: Mapped[str|None] = mapped_column(blob, nullable=True)

class EmployeeKPI(Base):
    __tablename__ = "employee_kpis"
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), primary_key=True)
    kpi_id: Mapped[int] = mapped_column(ForeignKey("kpis.id"), primary_key=True)
    target: Mapped[float] = mapped_column(Float)
    is_active: Mapped[bool] = mapped_column(default=True, index=True)

class Entry(Base):
    __tablename__ = "entries"
    __table_args__ = (UniqueConstraint("employee_id", "month", "kpi_id", name="uq_employee_month_kpi"),)
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int] = mapped_column(ForeignKey("employees.id"), index=True)
    kpi_id: Mapped[int] = mapped_column(ForeignKey("kpis.id"), index=True)
    month: Mapped[date] = mapped_column(Date, index=True)
    actual: Mapped[float|None] = mapped_column(Float, nullable=True)
    performance_pct: Mapped[float|None] = mapped_column(Float, nullable=True)
    score: Mapped[float|None] = mapped_column(Float, nullable=True)
    final_score: Mapped[float|None] = mapped_column(Float, nullable=True)
    target_snapshot: Mapped[float|None] = mapped_column(Float, nullable=True)
    employee_comments: Mapped[str|None] = mapped_column(Text, nullable=True)
    supervisor_comments: Mapped[str|None] = mapped_column(Text, nullable=True)
    context: Mapped[bytes|None] = mapped_column(LargeBinary, nullable=True)
    status: Mapped[str] = mapped_column(String(30), default="Draft", index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    employee: Mapped[Employee] = relationship(back_populates="entries")
    kpi: Mapped[KPI] = relationship()
