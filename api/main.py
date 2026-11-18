from pathlib import Path

from fastapi import FastAPI, HTTPException

app = FastAPI(
    title="PathSnap API",
    description="Map Matching and Route Reconstruction",
    version="1.0.0"
)

@app.get("/health")
def health_check():
    return {
        "status": "running",
        "project": "PathSnap",
        "message": "Backend is working!"
    }


@app.get("/trips")
def list_trips():
    student_test_dir = Path(__file__).resolve().parent.parent / "data" / "student_test"

    if not student_test_dir.is_dir():
        raise HTTPException(
            status_code=404,
            detail="Student-test dataset directory not found"
        )

    trip_ids = sorted(
        entry.name
        for entry in student_test_dir.iterdir()
        if entry.is_dir() and len(entry.name) == 8 and entry.name.isdigit()
    )

    if not trip_ids:
        raise HTTPException(
            status_code=404,
            detail="No valid trip folders found in the student-test dataset"
        )

    return {
        "trips": trip_ids,
        "total": len(trip_ids)
    }
