from datetime import datetime
from sqlalchemy import (
    create_engine, Column, String, DateTime, Float, Text
)
from sqlalchemy.orm import declarative_base, sessionmaker

try:
    from .config import DATABASE_URL
except ImportError:
    from backend.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_size=20,  # 增加连接池大小
    max_overflow=40,  # 允许的额外连接数
    pool_timeout=30,  # 连接超时时间
    pool_recycle=3600,  # 连接回收时间（秒）
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

class Task(Base):
    __tablename__ = "tasks"

    id = Column(String, primary_key=True, index=True)
    status = Column(String, default="queued", index=True)   # queued / processing / done / failed
    progress = Column(Float, default=0.0)

    model = Column(String, default="mtmt3_piano_vocal")
    mode = Column(String, default="with_accompaniment")
    quantization = Column(String, default="none")

    input_path = Column(String)
    midi_path = Column(String, nullable=True)
    musicxml_path = Column(String, nullable=True)

    duration = Column(Float, nullable=True)
    note_count = Column(Float, nullable=True)

    error_message = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow)

    def touch(self):
        self.updated_at = datetime.utcnow()


def init_db():
    Base.metadata.create_all(bind=engine)
