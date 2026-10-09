import csv, io
from datetime import datetime
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import select
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from .database import get_db
from .models import Student, Room, Plan, Assignment
from .schemas import RoomCreate
from .seating import generate, validate

router = APIRouter(prefix="/api")

@router.get("/health")
def health():
    return {"status": "ok", "service": "SeatWise AI"}

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db)):
    students = db.query(Student).count()
    rooms = db.query(Room).all()
    plan = db.query(Plan).order_by(Plan.id.desc()).first()
    assigned = plan.total_students if plan and plan.validation_status == "valid" else 0
    return {"students": students, "branches": db.query(Student.branch).distinct().count(),
            "rooms": len(rooms), "capacity": sum(min(r.capacity, r.rows*r.columns) for r in rooms),
            "assigned": assigned, "plans": db.query(Plan).count()}

@router.post("/students/import-csv")
async def import_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(400, "Please upload a .csv file.")
    raw = await file.read()
    if len(raw) > 5_000_000:
        raise HTTPException(413, "CSV must be smaller than 5 MB.")
    try:
        text = raw.decode("utf-8-sig")
        reader = csv.DictReader(io.StringIO(text))
        required = {"roll_number", "name", "branch"}
        if not reader.fieldnames or not required.issubset(set(reader.fieldnames)):
            raise HTTPException(400, "CSV must contain roll_number,name,branch headers.")
        rows = list(reader)
    except UnicodeDecodeError:
        raise HTTPException(400, "CSV must use UTF-8 encoding.")
    added, skipped, errors = 0, 0, []
    seen = set()
    for i, row in enumerate(rows, start=2):
        roll, name, branch = (row.get(k, "").strip() for k in ("roll_number", "name", "branch"))
        if not roll or not name or not branch:
            errors.append({"row": i, "error": "Missing roll_number, name, or branch"}); continue
        if roll in seen or db.query(Student).filter_by(roll_number=roll).first():
            skipped += 1; errors.append({"row": i, "error": f"Duplicate roll number: {roll}"}); continue
        seen.add(roll)
        db.add(Student(roll_number=roll, name=name, branch=branch.upper()))
        added += 1
    db.commit()
    return {"added": added, "skipped": skipped, "errors": errors}

@router.get("/students")
def list_students(db: Session = Depends(get_db)):
    return [{"roll_number": s.roll_number, "name": s.name, "branch": s.branch}
            for s in db.query(Student).order_by(Student.roll_number).all()]

@router.get("/rooms")
def list_rooms(db: Session = Depends(get_db)):
    return [{"id": r.id, "room_name": r.room_name, "building": r.building, "rows": r.rows,
             "columns": r.columns, "capacity": r.capacity, "usable_capacity": min(r.capacity, r.rows*r.columns)}
            for r in db.query(Room).order_by(Room.id).all()]

@router.post("/rooms")
def create_room(payload: RoomCreate, db: Session = Depends(get_db)):
    if payload.capacity > payload.rows * payload.columns:
        raise HTTPException(400, "Capacity cannot exceed rows × columns.")
    if db.query(Room).filter_by(room_name=payload.room_name).first():
        raise HTTPException(409, "Room name already exists.")
    room = Room(**payload.model_dump())
    db.add(room); db.commit(); db.refresh(room)
    return {"id": room.id, "room_name": room.room_name}

@router.delete("/rooms/{room_id}")
def delete_room(room_id: int, db: Session = Depends(get_db)):
    room = db.get(Room, room_id)
    if not room: raise HTTPException(404, "Room not found.")
    if db.query(Assignment).filter_by(room_id=room_id).first():
        raise HTTPException(409, "Room is referenced by a saved seating plan.")
    db.delete(room); db.commit()
    return {"deleted": True}

@router.post("/demo/load")
def load_demo(db: Session = Depends(get_db)):
    if db.query(Student).count() == 0:
        branches = ["CSE", "ECE", "IT", "EEE"]
        for i in range(24):
            branch = branches[i % len(branches)]
            prefix = {"CSE":"CS", "ECE":"EC", "IT":"IT", "EEE":"EE"}[branch]
            db.add(Student(roll_number=f"{prefix}{i+1:03}", name=f"Student {i+1:02}", branch=branch))
    if db.query(Room).count() == 0:
        db.add_all([
            Room(room_name="A-101", building="Main Block", rows=4, columns=4, capacity=16),
            Room(room_name="A-102", building="Main Block", rows=3, columns=4, capacity=12),
            Room(room_name="B-201", building="Science Block", rows=3, columns=4, capacity=12),
        ])
    db.commit()
    return {"message": "Demo data is ready.", "students": db.query(Student).count(), "rooms": db.query(Room).count()}

@router.post("/seating/generate")
def generate_plan(db: Session = Depends(get_db)):
    students = db.query(Student).order_by(Student.branch, Student.roll_number).all()
    rooms = db.query(Room).order_by(Room.id).all()
    if not students: raise HTTPException(400, "Import students or load demo data first.")
    if not rooms: raise HTTPException(400, "Create at least one room first.")
    try:
        assignments = generate(students, rooms)
    except ValueError as e:
        raise HTTPException(422, str(e))
    plan = Plan(plan_name=f"Seating Plan {datetime.now().strftime('%Y-%m-%d %H:%M')}",
                total_students=len(assignments), total_rooms=len({a["room"].id for a in assignments}),
                validation_status="valid")
    db.add(plan); db.flush()
    for a in assignments:
        db.add(Assignment(plan_id=plan.id, student_id=a["student"].id, room_id=a["room"].id,
                          row_number=a["row"], column_number=a["column"], seat_number=a["seat_number"]))
    db.commit(); db.refresh(plan)
    return {"plan_id": plan.id, "students_assigned": len(assignments), "rooms_used": plan.total_rooms,
            "violations": 0, "status": "valid"}

@router.get("/seating/plans")
def plans(db: Session = Depends(get_db)):
    return [{"id": p.id, "plan_name": p.plan_name, "created_at": p.created_at.isoformat(),
             "total_students": p.total_students, "total_rooms": p.total_rooms,
             "validation_status": p.validation_status}
            for p in db.query(Plan).order_by(Plan.id.desc()).all()]

@router.get("/seating/plans/{plan_id}")
def plan_detail(plan_id: int, db: Session = Depends(get_db)):
    plan = db.get(Plan, plan_id)
    if not plan: raise HTTPException(404, "Plan not found.")
    return {"id": plan.id, "plan_name": plan.plan_name, "validation_status": plan.validation_status,
            "assignments": assignment_rows(db, plan_id)}

def assignment_rows(db, plan_id, room_id=None):
    q = db.query(Assignment).filter_by(plan_id=plan_id)
    if room_id is not None: q = q.filter_by(room_id=room_id)
    out = []
    for a in q.all():
        out.append({"roll_number": a.student.roll_number, "name": a.student.name, "branch": a.student.branch,
                    "room_id": a.room.id, "room": a.room.room_name, "building": a.room.building,
                    "row": a.row_number, "column": a.column_number, "seat_number": a.seat_number})
    return out

@router.get("/seating/plans/{plan_id}/rooms/{room_id}")
def room_chart(plan_id: int, room_id: int, db: Session = Depends(get_db)):
    room = db.get(Room, room_id)
    if not room: raise HTTPException(404, "Room not found.")
    rows = assignment_rows(db, plan_id, room_id)
    return {"room": {"id": room.id, "room_name": room.room_name, "building": room.building,
                     "rows": room.rows, "columns": room.columns, "capacity": room.capacity}, "assignments": rows}

@router.get("/seating/find/{roll_number}")
def find_seat(roll_number: str, db: Session = Depends(get_db)):
    plan = db.query(Plan).order_by(Plan.id.desc()).first()
    student = db.query(Student).filter_by(roll_number=roll_number).first()
    if not student: raise HTTPException(404, "Roll number not found.")
    if not plan: raise HTTPException(404, "No seating plan has been generated yet.")
    a = db.query(Assignment).filter_by(plan_id=plan.id, student_id=student.id).first()
    if not a: raise HTTPException(404, "This student is not assigned in the latest seating plan.")
    return {"roll_number": student.roll_number, "name": student.name, "branch": student.branch,
            "room": a.room.room_name, "building": a.room.building, "row": a.row_number,
            "column": a.column_number, "seat_number": a.seat_number, "plan_id": plan.id}

@router.get("/seating/plans/{plan_id}/export.csv")
def export_csv(plan_id: int, db: Session = Depends(get_db)):
    if not db.get(Plan, plan_id): raise HTTPException(404, "Plan not found.")
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=["roll_number","name","branch","room","building","row","column","seat_number"])
    writer.writeheader(); writer.writerows(assignment_rows(db, plan_id))
    return StreamingResponse(iter([output.getvalue()]), media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="seatwise-plan-{plan_id}.csv"'})

@router.get("/seating/plans/{plan_id}/rooms/{room_id}/export.pdf")
def export_pdf(plan_id: int, room_id: int, db: Session = Depends(get_db)):
    room = db.get(Room, room_id)
    if not room or not db.get(Plan, plan_id): raise HTTPException(404, "Room or plan not found.")
    assignments = assignment_rows(db, plan_id, room_id)
    buffer = io.BytesIO()
    c = canvas.Canvas(buffer, pagesize=landscape(A4))
    width, height = landscape(A4)
    c.setFont("Helvetica-Bold", 18); c.drawString(40, height-42, "SeatWise AI - Room Seating Chart")
    c.setFont("Helvetica", 11); c.drawString(40, height-62, f"Room: {room.room_name} | Building: {room.building} | Assigned: {len(assignments)}")
    lookup = {(a["row"], a["column"]): a for a in assignments}
    left, top = 45, height-105
    cell_w = min(95, (width-90)/room.columns)
    cell_h = min(48, (height-145)/room.rows)
    for r in range(1, room.rows+1):
        for col in range(1, room.columns+1):
            x, y = left+(col-1)*cell_w, top-r*cell_h
            c.rect(x, y, cell_w-4, cell_h-4)
            a = lookup.get((r,col))
            if a:
                c.setFont("Helvetica-Bold", 8); c.drawString(x+4,y+cell_h-15,a["roll_number"][:18])
                c.setFont("Helvetica", 7); c.drawString(x+4,y+cell_h-27,a["branch"][:16])
            else:
                c.setFont("Helvetica", 8); c.drawString(x+4,y+cell_h-18,"Empty")
    c.showPage(); c.save(); buffer.seek(0)
    return StreamingResponse(buffer, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="room-{room.room_name}.pdf"'})
