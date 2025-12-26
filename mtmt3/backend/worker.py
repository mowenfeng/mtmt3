import time
from sqlalchemy.orm import Session

try:
    from .db import SessionLocal, Task
    from .config import RESULT_DIR
    from .mtmt3_core.transcriber import run_mtmt3
except ImportError:
    from backend.db import SessionLocal, Task
    from backend.config import RESULT_DIR
    from backend.mtmt3_core.transcriber import run_mtmt3


def update_progress(db: Session, task_id: str, progress: float, status: str = None):
    """更新任务进度"""
    task = db.query(Task).filter(Task.id == task_id).first()
    if task:
        task.progress = progress
        if status:
            task.status = status
        task.touch()
        db.commit()
        db.refresh(task)


def process_one_task(db: Session):
    task = (
        db.query(Task)
        .filter(Task.status == "queued")
        .order_by(Task.created_at.asc())
        .first()
    )
    if not task:
        return False

    task.status = "processing"
    task.progress = 0.05  # 5% - 开始处理
    task.touch()
    db.commit()

    try:
        output_dir = RESULT_DIR / task.id
        
        # 使用回调函数更新进度
        def progress_callback(stage: str, progress: float):
            """进度回调函数"""
            db_session = SessionLocal()
            try:
                update_progress(db_session, task.id, progress, "processing")
            finally:
                db_session.close()
        
        result = run_mtmt3(
            audio_path=task.input_path,
            model=task.model,
            mode=task.mode,
            quantization=task.quantization,
            output_dir=str(output_dir),
            progress_callback=progress_callback,
        )

        task.midi_path = result["midi_path"]
        task.musicxml_path = result["musicxml_path"]
        task.duration = result.get("duration")
        task.note_count = result.get("note_count")
        task.status = "done"
        task.progress = 1.0
        task.touch()
        db.commit()

    except Exception as e:
        task.status = "failed"
        task.error_message = str(e)
        task.progress = 0.0
        task.touch()
        db.commit()

    return True


def worker_loop():
    while True:
        db = SessionLocal()
        try:
            processed = process_one_task(db)
        finally:
            db.close()

        if not processed:
            time.sleep(1)


if __name__ == "__main__":
    worker_loop()
