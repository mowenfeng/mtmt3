import uuid
import python_multipart
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from .config import UPLOAD_DIR, RESULT_DIR
from .db import SessionLocal, init_db, Task

init_db()

app = FastAPI()

# 简单 CORS，方便前端直接访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@app.post("/api/tasks")
async def create_task(
    file: UploadFile = File(...),
    model: str = Form("mtmt3_piano_vocal"),
    mode: str = Form("with_accompaniment"),
    quantization: str = Form("none"),
):
    task_id = str(uuid.uuid4())
    ext = file.filename.split(".")[-1]
    input_path = UPLOAD_DIR / f"{task_id}.{ext}"

    data = await file.read()
    with open(input_path, "wb") as f:
        f.write(data)

    db: Session = next(get_db())

    task = Task(
        id=task_id,
        status="queued",
        progress=0.0,
        model=model,
        mode=mode,
        quantization=quantization,
        input_path=str(input_path),
    )
    task.touch()
    db.add(task)
    db.commit()

    return {"task_id": task_id, "status": task.status}


@app.get("/api/tasks/{task_id}")
def get_task(task_id: str):
    db: Session = next(get_db())
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    result = None
    if task.status == "done":
        result = {
            "midi_url": f"/download/{task.id}.mid",
            "musicxml_url": f"/download/{task.id}.musicxml",
            "duration": task.duration,
            "note_count": task.note_count,
        }

    return {
        "task_id": task.id,
        "status": task.status,
        "progress": task.progress,
        "created_at": task.created_at,
        "updated_at": task.updated_at,
        "result": result,
        "error_message": task.error_message,
    }


@app.get("/download/{task_id}.{ext}")
def download_file(task_id: str, ext: str):
    db: Session = next(get_db())
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    if ext == "mid":
        path = task.midi_path
    elif ext == "musicxml":
        path = task.musicxml_path
    else:
        raise HTTPException(status_code=400, detail="Unsupported ext")

    if not path:
        raise HTTPException(status_code=404, detail="Result not ready")

    return FileResponse(path, filename=f"{task_id}.{ext}")
