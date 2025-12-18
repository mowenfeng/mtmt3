# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Environment and setup

- This repository contains a Python backend service built with FastAPI and SQLAlchemy.
- All backend code lives under the `backend` package.
- Dependencies are defined in `backend/requirements.txt`.

From the repository root:

- Install dependencies:
  - `pip install -r backend/requirements.txt`

## Common commands

All commands assume you are in the repository root and that `backend` is importable as a Python package.

### Run the API server (development)

- Start the FastAPI app with auto-reload:
  - `uvicorn backend.main:app --reload --port 8000`

The API exposes:
- `POST /api/tasks` — upload an audio file and enqueue a transcription task
- `GET /api/tasks/{task_id}` — poll task status and (when done) get URLs for MIDI/MusicXML
- `GET /download/{task_id}.{ext}` — download generated result files (`ext` is `mid` or `musicxml`)

### Run the background worker

Transcription work happens in a separate long-running worker process that polls the database for queued tasks.

- Run the worker loop:
  - `python -m backend.worker`

The worker should be running concurrently with the API server for end-to-end functionality.

### Database initialization

- The SQLite database is located at `backend/db.sqlite3` (configured in `backend/config.py`).
- Tables are automatically created on API startup via `init_db()` in `backend/db.py`, which is invoked at import time in `backend/main.py`.

### Linting and testing

- There is currently no dedicated lint or test tooling configured in this repository (no `pytest`/`unittest` setup or lint configs are present).
- If you add linters (e.g., `ruff`, `flake8`, `black`) or tests, prefer to document their commands here.

## High-level architecture

### Data and configuration (`backend/config.py`)

- Defines base paths relative to `backend`:
  - `DATA_DIR` — root data directory under `backend/data`.
  - `UPLOAD_DIR` — where uploaded audio files are stored.
  - `RESULT_DIR` — where transcription outputs are stored.
- Ensures these directories exist at import time.
- Configures `DATABASE_URL` to use a local SQLite file `db.sqlite3` under `backend`.

### Persistence layer (`backend/db.py`)

- Sets up the SQLAlchemy engine and `SessionLocal` bound to the SQLite database.
- Declares the `Task` ORM model, which represents a transcription job with fields such as:
  - `id` — UUID string identifying the task.
  - `status` — `queued` / `processing` / `done` / `failed`.
  - `progress` — float between 0 and 1.
  - `model`, `mode`, `quantization` — parameters for the transcription run.
  - `input_path` — uploaded audio file path.
  - `midi_path`, `musicxml_path` — generated output file paths.
  - `duration`, `note_count` — basic metadata about the transcription result.
  - `error_message` — error details when a task fails.
  - `created_at`, `updated_at` — timestamps, with `touch()` updating `updated_at`.
- `init_db()` creates all tables based on the ORM metadata and is invoked from `backend/main.py`.

### API layer (`backend/main.py`)

- Initializes the FastAPI application and applies permissive CORS (all origins, methods, and headers) to make frontends easy to integrate.
- Uses `init_db()` at import time to ensure database tables exist.
- Provides a simple `get_db()` generator that yields a `SessionLocal` for request handlers.

Endpoints:
- `POST /api/tasks`:
  - Accepts an uploaded audio file (`file`) and optional form fields `model`, `mode`, and `quantization`.
  - Saves the file to `UPLOAD_DIR` with a generated UUID-based filename.
  - Creates a `Task` row with status `queued` and progress `0.0` and commits it.
  - Returns the `task_id` and initial status.

- `GET /api/tasks/{task_id}`:
  - Looks up the `Task` by ID.
  - When status is `done`, includes a `result` payload with URLs for MIDI and MusicXML downloads plus `duration`/`note_count`.
  - Always returns core task metadata including status, progress, timestamps, and any `error_message`.

- `GET /download/{task_id}.{ext}`:
  - Validates the task exists and that `ext` is either `mid` or `musicxml`.
  - Maps `mid` -> `midi_path` and `musicxml` -> `musicxml_path` on the `Task`.
  - Returns a `FileResponse` streaming the corresponding file if available.

### Background worker (`backend/worker.py`)

- Implements a simple polling worker for queued tasks:
  - `process_one_task(db)`:
    - Picks the oldest `Task` with `status == "queued"`.
    - Marks it as `processing` and sets a small initial `progress`.
    - Invokes the transcription core (`run_mtmt3`) to perform the work.
    - On success, updates output paths, duration, note count, sets status to `done` and `progress` to `1.0`.
    - On failure, sets status to `failed`, records `error_message`, and resets `progress` to `0.0`.
  - `worker_loop()`:
    - Runs an infinite loop, creating a new `SessionLocal` each iteration.
    - Calls `process_one_task`; if no task is processed, sleeps briefly before trying again.
- The module’s `__main__` guard runs `worker_loop()` when executed as a script, making it suitable for `python -m backend.worker`.

### Transcription core stub (`backend/mtmt3_core/transcriber.py`)

- Defines `run_mtmt3(audio_path, model, mode, quantization, output_dir)` as the abstraction point for transcription.
- Current implementation is a stub used to validate the architecture:
  - Ensures the output directory exists.
  - Simulates work with `time.sleep(...)`.
  - Writes dummy `result.mid` and `result.musicxml` files.
  - Returns file paths and fake `duration`/`note_count`.
- This function is the primary integration point for plugging in the real MT-MT3 (or MR-MT3) model logic without changing the API or worker flow.

## Agent-specific guidance

- When modifying the `Task` model (adding/removing fields), ensure that:
  - The database schema is kept in sync (either by recreating the DB locally or adding Alembic migrations if you introduce them).
  - All usages in `backend/main.py` (API responses) and `backend/worker.py` are updated consistently.
- Keep long-running or CPU/GPU-intensive work inside the worker process. The FastAPI handlers should only enqueue work and read results, not perform heavy inference directly.
- To change where data is stored (uploads/results or the SQLite file), update `backend/config.py` and verify that both the API and worker still agree on the same directories and database URL.
