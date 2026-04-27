import os
import time
import tempfile
from pathlib import Path

import requests

try:
    from .mtmt3_core.transcriber import run_mtmt3
except ImportError:
    from backend.mtmt3_core.transcriber import run_mtmt3


API_BASE = os.getenv("REMOTE_API_BASE", "http://127.0.0.1:8000").rstrip("/")
WORKER_TOKEN = os.getenv("WORKER_TOKEN", "")
POLL_SECONDS = float(os.getenv("REMOTE_WORKER_POLL_SECONDS", "2"))
REQUEST_TIMEOUT = int(os.getenv("REMOTE_WORKER_TIMEOUT", "120"))


def _headers():
    return {"x-worker-token": WORKER_TOKEN}


def _url(path: str) -> str:
    if path.startswith("http://") or path.startswith("https://"):
        return path
    return API_BASE + path


def _post_json(path: str, payload: dict):
    requests.post(
        _url(path),
        json=payload,
        headers=_headers(),
        timeout=REQUEST_TIMEOUT,
    )


def _download_file(url_path: str, target_path: Path):
    with requests.get(
        _url(url_path),
        headers=_headers(),
        timeout=REQUEST_TIMEOUT,
        stream=True,
    ) as r:
        r.raise_for_status()
        with open(target_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 512):
                if chunk:
                    f.write(chunk)


def _upload_result(task_id: str, midi_path: Path, musicxml_path: Path, duration: float, note_count: float):
    with open(midi_path, "rb") as mf, open(musicxml_path, "rb") as xf:
        files = {
            "midi_file": ("result.mid", mf, "audio/midi"),
            "musicxml_file": ("result.musicxml", xf, "application/xml"),
        }
        data = {"duration": str(duration), "note_count": str(note_count)}
        resp = requests.post(
            _url(f"/api/worker/tasks/{task_id}/complete"),
            headers=_headers(),
            files=files,
            data=data,
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()


def claim_task():
    resp = requests.post(
        _url("/api/worker/tasks/claim"),
        headers=_headers(),
        timeout=REQUEST_TIMEOUT,
    )
    resp.raise_for_status()
    data = resp.json()
    return data.get("task")


def process_task(task: dict):
    task_id = task["task_id"]
    input_filename = task.get("input_filename", f"{task_id}.audio")
    suffix = Path(input_filename).suffix or ".audio"

    print(f"[worker] claimed task={task_id}")

    with tempfile.TemporaryDirectory(prefix=f"task_{task_id}_") as temp_dir:
        temp_dir_path = Path(temp_dir)
        input_path = temp_dir_path / f"input{suffix}"
        output_dir = temp_dir_path / "result"
        output_dir.mkdir(parents=True, exist_ok=True)

        _post_json(f"/api/worker/tasks/{task_id}/progress", {"progress": 0.05, "status": "processing"})
        _download_file(task["input_url"], input_path)
        _post_json(f"/api/worker/tasks/{task_id}/progress", {"progress": 0.10, "status": "processing"})

        def progress_callback(_stage: str, progress: float):
            try:
                _post_json(
                    f"/api/worker/tasks/{task_id}/progress",
                    {"progress": float(progress), "status": "processing"},
                )
            except Exception:
                pass

        result = run_mtmt3(
            audio_path=str(input_path),
            model=task.get("model", "mtmt3_piano_vocal"),
            mode=task.get("mode", "with_accompaniment"),
            quantization=task.get("quantization", "none"),
            output_dir=str(output_dir),
            progress_callback=progress_callback,
        )

        midi_path = Path(result["midi_path"])
        musicxml_path = Path(result["musicxml_path"])
        _upload_result(
            task_id,
            midi_path,
            musicxml_path,
            float(result.get("duration") or 0.0),
            float(result.get("note_count") or 0.0),
        )
        print(f"[worker] task done={task_id}")


def worker_loop():
    if not WORKER_TOKEN:
        raise RuntimeError("WORKER_TOKEN is required for remote_worker")

    print(f"[worker] start remote worker, api={API_BASE}")
    while True:
        try:
            task = claim_task()
            if not task:
                time.sleep(POLL_SECONDS)
                continue
            try:
                process_task(task)
            except Exception as e:
                err_msg = f"{type(e).__name__}: {e}"
                _post_json(f"/api/worker/tasks/{task['task_id']}/fail", {"error_message": err_msg})
                print(f"[worker] task failed={task['task_id']} error={err_msg}")
        except Exception as e:
            print(f"[worker] poll error: {e}")
            time.sleep(max(POLL_SECONDS, 3))


if __name__ == "__main__":
    worker_loop()
