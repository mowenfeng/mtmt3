import time
from sqlalchemy.orm import Session

from .db import SessionLocal, Task
from .config import RESULT_DIR
from .mtmt3_core.transcriber import run_mtmt3


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
    task.progress = 0.01
    task.touch()
    db.commit()

    try:
        output_dir = RESULT_DIR / task.id
        result = run_mtmt3(
            audio_path=task.input_path,
            model=task.model,
            mode=task.mode,
            quantization=task.quantization,
            output_dir=str(output_dir),
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
