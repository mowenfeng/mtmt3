import uuid
import python_multipart
from fastapi import FastAPI, UploadFile, File, Form, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pathlib import Path

try:
    from .config import UPLOAD_DIR, RESULT_DIR
    from .db import SessionLocal, init_db, Task
except ImportError:
    # 如果相对导入失败，使用绝对导入
    from backend.config import UPLOAD_DIR, RESULT_DIR
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


# 挂载前端静态文件（放在最后，避免拦截API路由）
frontend_dir = Path(__file__).parent.parent / "frontend"
if frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dir), html=True), name="frontend")
