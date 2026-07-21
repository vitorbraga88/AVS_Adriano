"""Engine SQLite + SessionLocal + Base (SQLAlchemy 2.0).

App único (AVS): sem Postgres, sem DATABASE_URL obrigatória. O arquivo do
banco fica em avs-admin/database/avs.db e é criado no startup (create_all).
"""
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

DB_DIR = Path(__file__).parent.parent / "database"
DB_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = DB_DIR / "avs.db"

engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass
