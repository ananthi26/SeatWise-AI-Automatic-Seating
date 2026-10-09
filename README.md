# SeatWise AI - Exam Seating Arrangement Generator

A hackathon-ready full-stack prototype for assigning students from multiple branches to exam rooms while preventing same-branch students from sitting directly adjacent horizontally or vertically. Diagonal neighbours are allowed.

## Requirements covered

- Import student lists from CSV (`roll_number,name,branch`).
- Configure rooms, building, rows, columns and usable capacity.
- Automatically generate a seating plan and validate branch adjacency.
- View room-wise visual seating charts.
- Find a student's room and seat by roll number.
- Export the whole plan to CSV and each room chart to printable PDF.
- Store students, rooms, plans and assignments in a local SQLite database.

## Prerequisites

- Python 3.10 or newer (Python 3.11/3.12 recommended).
- Node.js 20 or newer and npm.

## Run on Windows (easiest)

1. Extract the ZIP fully. Open the extracted `SeatWise_AI` folder.
2. Double-click `START_BACKEND.bat`. Wait until the terminal says Uvicorn is running at `http://127.0.0.1:8000`.
3. Double-click `START_FRONTEND.bat` in another terminal. Open the Vite URL it prints, usually `http://localhost:5173`.
4. API health check: `http://127.0.0.1:8000/api/health`. API docs: `http://127.0.0.1:8000/docs`.

If Windows blocks script execution, the batch files use `activate.bat` rather than PowerShell activation. Keep both terminal windows open while using the app.

## Run manually

Backend terminal:
```powershell
cd backend
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend terminal:
```powershell
cd frontend
npm install
npm run dev
```

## First-time demo

- Click **Load demo data** on Overview to create sample students and rooms, or use **Students → Import CSV**.
- CSV must contain these exact header names: `roll_number,name,branch`. Example: `CS001,Aarun,CSE`.
- Add rooms in **Rooms**. Capacity must be no greater than rows × columns.
- Click **Generate seating** to automatically allocate students across configured rooms.
- Open **Seating chart**, select a room, and use **Room PDF**.
- Open **Find My Seat** and search a roll number such as `CS001`.
- Use **Exports** to download the complete seating plan CSV or any room's PDF.

## Seating rule and limitations

The generator checks horizontal and vertical neighbours within each room; diagonal neighbours are allowed. If the requested constraints cannot be satisfied within the configured room layouts or the bounded search limit is reached, the app returns an error instead of saving an invalid plan. Add capacity or adjust room layouts and retry. Always review the chart before using it for a real examination.

This is a local hackathon prototype, not a deployed production service. SQLite data is stored locally in `backend/seatwise.db` and is not shared automatically with another computer or GitHub.
