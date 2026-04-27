import uuid
import python_multipart
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pathlib import Path
from pydantic import BaseModel

try:
    from .config import UPLOAD_DIR, RESULT_DIR, WORKER_TOKEN
    from .db import SessionLocal, init_db, Task
except ImportError:
    # 如果相对导入失败，使用绝对导入
    from backend.config import UPLOAD_DIR, RESULT_DIR, WORKER_TOKEN
    from backend.db import SessionLocal, init_db, Task

init_db()

app = FastAPI(title="音乐转谱服务", description="基于MR-MT3模型的音乐转谱API")

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


def verify_worker_token(x_worker_token: str = Header(default="")):
    if not WORKER_TOKEN or WORKER_TOKEN == "change-me":
        raise HTTPException(status_code=500, detail="Worker token not configured on server")
    if x_worker_token != WORKER_TOKEN:
        raise HTTPException(status_code=401, detail="Invalid worker token")


class ProgressUpdate(BaseModel):
    progress: float
    status: str = "processing"


class FailureUpdate(BaseModel):
    error_message: str


@app.post("/api/tasks")
async def create_task(
    file: UploadFile = File(...),
    model: str = Form("mtmt3_piano_vocal"),
    mode: str = Form("with_accompaniment"),
    quantization: str = Form("none"),
    db: Session = Depends(get_db),
):
    task_id = str(uuid.uuid4())
    ext = file.filename.split(".")[-1]
    input_path = UPLOAD_DIR / f"{task_id}.{ext}"

    data = await file.read()
    with open(input_path, "wb") as f:
        f.write(data)

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
def get_task(task_id: str, db: Session = Depends(get_db)):
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
def download_file(task_id: str, ext: str, db: Session = Depends(get_db)):
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


@app.post("/api/worker/tasks/claim")
def claim_task(
    _: None = Depends(verify_worker_token),
    db: Session = Depends(get_db),
):
    task = (
        db.query(Task)
        .filter(Task.status == "queued")
        .order_by(Task.created_at.asc())
        .first()
    )
    if not task:
        return {"task": None}

    task.status = "processing"
    task.progress = max(task.progress or 0.0, 0.02)
    task.error_message = None
    task.touch()
    db.commit()
    db.refresh(task)

    input_name = Path(task.input_path).name if task.input_path else f"{task.id}.audio"
    return {
        "task": {
            "task_id": task.id,
            "model": task.model,
            "mode": task.mode,
            "quantization": task.quantization,
            "input_filename": input_name,
            "input_url": f"/api/worker/tasks/{task.id}/input",
        }
    }


@app.get("/api/worker/tasks/{task_id}/input")
def worker_download_input(
    task_id: str,
    _: None = Depends(verify_worker_token),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if not task.input_path or not Path(task.input_path).exists():
        raise HTTPException(status_code=404, detail="Input file not found")
    return FileResponse(task.input_path, filename=Path(task.input_path).name)


@app.post("/api/worker/tasks/{task_id}/progress")
def worker_update_progress(
    task_id: str,
    payload: ProgressUpdate,
    _: None = Depends(verify_worker_token),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.status in ("done", "failed"):
        return {"ok": True}

    task.progress = max(0.0, min(payload.progress, 0.99))
    task.status = payload.status or "processing"
    task.touch()
    db.commit()
    return {"ok": True}


@app.post("/api/worker/tasks/{task_id}/complete")
async def worker_complete_task(
    task_id: str,
    midi_file: UploadFile = File(...),
    musicxml_file: UploadFile = File(...),
    duration: float = Form(0.0),
    note_count: float = Form(0.0),
    _: None = Depends(verify_worker_token),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    output_dir = RESULT_DIR / task_id
    output_dir.mkdir(parents=True, exist_ok=True)

    midi_path = output_dir / "result.mid"
    musicxml_path = output_dir / "result.musicxml"

    with open(midi_path, "wb") as f:
        f.write(await midi_file.read())
    with open(musicxml_path, "wb") as f:
        f.write(await musicxml_file.read())

    task.midi_path = str(midi_path)
    task.musicxml_path = str(musicxml_path)
    task.duration = duration
    task.note_count = note_count
    task.status = "done"
    task.progress = 1.0
    task.error_message = None
    task.touch()
    db.commit()

    return {"ok": True}


@app.post("/api/worker/tasks/{task_id}/fail")
def worker_fail_task(
    task_id: str,
    payload: FailureUpdate,
    _: None = Depends(verify_worker_token),
    db: Session = Depends(get_db),
):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task.status = "failed"
    task.progress = 0.0
    task.error_message = payload.error_message
    task.touch()
    db.commit()
    return {"ok": True}


# 挂载前端静态文件（放在最后，避免拦截API路由）
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
