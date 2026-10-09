from sqlalchemy import String, Integer, ForeignKey, DateTime, Boolean, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship
from datetime import datetime
from .database import Base

class Student(Base):
    __tablename__ = "students"
    id: Mapped[int] = mapped_column(primary_key=True)
    roll_number: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    branch: Mapped[str] = mapped_column(String(30), index=True)

class Room(Base):
    __tablename__ = "rooms"
    id: Mapped[int] = mapped_column(primary_key=True)
    room_name: Mapped[str] = mapped_column(String(80), unique=True)
    building: Mapped[str] = mapped_column(String(80), default="Main Block")
    rows: Mapped[int] = mapped_column(Integer)
    columns: Mapped[int] = mapped_column(Integer)
    capacity: Mapped[int] = mapped_column(Integer)
    notes: Mapped[str] = mapped_column(String(250), default="")

class Plan(Base):
    __tablename__ = "plans"
    id: Mapped[int] = mapped_column(primary_key=True)
    plan_name: Mapped[str] = mapped_column(String(120), default="Exam Seating Plan")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    total_students: Mapped[int] = mapped_column(Integer, default=0)
    total_rooms: Mapped[int] = mapped_column(Integer, default=0)
    validation_status: Mapped[str] = mapped_column(String(30), default="pending")
    assignments: Mapped[list["Assignment"]] = relationship(back_populates="plan", cascade="all, delete-orphan")

class Assignment(Base):
    __tablename__ = "assignments"
    id: Mapped[int] = mapped_column(primary_key=True)
    plan_id: Mapped[int] = mapped_column(ForeignKey("plans.id", ondelete="CASCADE"), index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id"))
    room_id: Mapped[int] = mapped_column(ForeignKey("rooms.id"))
    row_number: Mapped[int] = mapped_column(Integer)
    column_number: Mapped[int] = mapped_column(Integer)
    seat_number: Mapped[str] = mapped_column(String(20))
    plan: Mapped["Plan"] = relationship(back_populates="assignments")
    student: Mapped["Student"] = relationship()
    room: Mapped["Room"] = relationship()
    __table_args__ = (
        UniqueConstraint("plan_id", "student_id", name="uq_plan_student"),
        UniqueConstraint("plan_id", "room_id", "row_number", "column_number", name="uq_plan_seat"),
    )
