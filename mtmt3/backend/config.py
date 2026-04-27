import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
RESULT_DIR = DATA_DIR / "results"

for d in [DATA_DIR, UPLOAD_DIR, RESULT_DIR]:
    d.mkdir(parents=True, exist_ok=True)

DATABASE_URL = f"sqlite:///{BASE_DIR / 'db.sqlite3'}"

# 远程 worker 鉴权令牌（云端与本地 GPU worker 保持一致）
WORKER_TOKEN = os.getenv("WORKER_TOKEN", "change-me")
