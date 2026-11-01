import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("NEUROADAPT_DB", os.path.join(DB_DIR, "neuroadapt.db"))
DATABASE_URL = f"sqlite:///{DB_PATH}"

# SQLite requires check_same_thread=False for multi-threaded FastAPI workers
engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
