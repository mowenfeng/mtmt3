import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.db import SessionLocal, Task, Base, engine
from backend.config import RESULT_DIR


@pytest.fixture(autouse=True)
def clean_db():
    """Ensure a clean database for each test."""
    # Drop all tables then recreate so tests don't interfere with each other
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client():
    return TestClient(app)


def test_create_task_creates_db_record(client):
    # 1. POST /api/tasks successfully creates a new task in the database
    file_content = b"fake audio content"

    response = client.post(
        "/api/tasks",
        files={"file": ("test.wav", file_content, "audio/wav")},
    )

    assert response.status_code == 200
    data = response.json()
    assert "task_id" in data
    assert data["status"] == "queued"

    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == data["task_id"]).first()
        assert task is not None
        assert task.status == "queued"
        assert task.model == "mtmt3_piano_vocal"
        assert task.mode == "with_accompaniment"
        assert task.quantization == "none"
        assert os.path.exists(task.input_path)
    finally:
        db.close()


def test_get_task_returns_correct_status_and_details(client):
    # 2. GET /api/tasks/{task_id} returns the correct task status and details
    db = SessionLocal()
    try:
        task_id = "task-get-details"
        task = Task(
            id=task_id,
            status="done",
            progress=1.0,
            model="mtmt3_piano_vocal",
            mode="with_accompaniment",
            quantization="none",
            input_path="some_input.wav",
            midi_path=str(RESULT_DIR / f"{task_id}.mid"),
            musicxml_path=str(RESULT_DIR / f"{task_id}.musicxml"),
            duration=12.3,
            note_count=456,
        )
        db.add(task)
        db.commit()
    finally:
        db.close()

    response = client.get(f"/api/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()

    assert data["task_id"] == task_id
    assert data["status"] == "done"
    assert data["progress"] == 1.0
    assert data["result"] == {
        "midi_url": f"/download/{task_id}.mid",
        "musicxml_url": f"/download/{task_id}.musicxml",
        "duration": pytest.approx(12.3),
        "note_count": pytest.approx(456),
    }
    assert data["error_message"] is None


def test_get_task_nonexistent_returns_404(client):
    # 3. GET /api/tasks/{task_id} returns a 404 for a non-existent task
    response = client.get("/api/tasks/non-existent-task-id")

    assert response.status_code == 404
    data = response.json()
    assert data["detail"] == "Task not found"


@pytest.mark.parametrize("ext, attr_name", [("mid", "midi_path"), ("musicxml", "musicxml_path")])
def test_download_serves_generated_file(client, ext, attr_name):
    # 4. GET /download/{task_id}.{ext} successfully serves the generated file
    task_id = f"download-{ext}-task"
    file_path = RESULT_DIR / f"{task_id}.{ext}"
    file_path.parent.mkdir(parents=True, exist_ok=True)

    file_content = f"dummy {ext} content".encode()
    file_path.write_bytes(file_content)

    db = SessionLocal()
    try:
        task = Task(
            id=task_id,
            status="done",
            progress=1.0,
            model="mtmt3_piano_vocal",
            mode="with_accompaniment",
            quantization="none",
            input_path="some_input.wav",
        )
        setattr(task, attr_name, str(file_path))
        db.add(task)
        db.commit()
    finally:
        db.close()

    response = client.get(f"/download/{task_id}.{ext}")

    assert response.status_code == 200
    assert response.content == file_content
    content_disposition = response.headers.get("content-disposition", "")
    assert f"{task_id}.{ext}" in content_disposition


def test_process_one_task_processes_queued_task(monkeypatch):
    # 5. The background worker's process_one_task correctly processes a queued task
    from backend import worker

    db = SessionLocal()
    try:
        task_id = "worker-queued-task"
        task = Task(
            id=task_id,
            status="queued",
            progress=0.0,
            model="mtmt3_piano_vocal",
            mode="with_accompaniment",
            quantization="none",
            input_path="input.wav",
        )
        db.add(task)
        db.commit()
        db.refresh(task)

        def fake_run_mtmt3(audio_path, model, mode, quantization, output_dir):
            return {
                "midi_path": str(RESULT_DIR / f"{task_id}.mid"),
                "musicxml_path": str(RESULT_DIR / f"{task_id}.musicxml"),
                "duration": 10.0,
                "note_count": 123,
            }

        monkeypatch.setattr(worker, "run_mtmt3", fake_run_mtmt3)

        processed = worker.process_one_task(db)
        assert processed is True

        db.refresh(task)
        assert task.status == "done"
        assert task.progress == 1.0
        assert task.midi_path.endswith(f"{task_id}.mid")
        assert task.musicxml_path.endswith(f"{task_id}.musicxml")
        assert task.duration == 10.0
        assert task.note_count == 123
        assert task.error_message is None
    finally:
        db.close()
