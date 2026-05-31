"""SQLite database — agent runs, logs, stock snapshots, email history."""
from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Float,
    DateTime, Text, Boolean, JSON
)
from sqlalchemy.orm import DeclarativeBase, sessionmaker, Session
from contextlib import contextmanager
from config import DATABASE_URL


def _set_wal(dbapi_con, _):
    dbapi_con.execute("PRAGMA journal_mode=WAL")
    dbapi_con.execute("PRAGMA busy_timeout=5000")

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    pool_size=10,
    max_overflow=20,
)
from sqlalchemy import event as _sa_event
_sa_event.listen(engine, "connect", _set_wal)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class AgentRun(Base):
    __tablename__ = "agent_runs"
    id         = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(64), index=True)
    status     = Column(String(16))   # running | success | failed | skipped
    started_at = Column(DateTime, default=datetime.utcnow)
    finished_at= Column(DateTime, nullable=True)
    duration_s = Column(Float, nullable=True)
    message    = Column(Text, nullable=True)
    meta       = Column(JSON, nullable=True)


class AgentLog(Base):
    __tablename__ = "agent_logs"
    id         = Column(Integer, primary_key=True, index=True)
    agent_name = Column(String(64), index=True)
    level      = Column(String(8))    # INFO | WARN | ERROR
    message    = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class StockSnapshot(Base):
    __tablename__ = "stock_snapshots"
    id          = Column(Integer, primary_key=True, index=True)
    ticker      = Column(String(16), index=True)
    price       = Column(Float)
    change_pct  = Column(Float)
    volume      = Column(Float)
    market_cap  = Column(Float, nullable=True)
    llm_comment = Column(Text, nullable=True)
    captured_at = Column(DateTime, default=datetime.utcnow)


class EmailRecord(Base):
    __tablename__ = "email_records"
    id          = Column(Integer, primary_key=True, index=True)
    agent_name  = Column(String(64))
    subject     = Column(String(256))
    recipient   = Column(String(128))
    sent_at     = Column(DateTime, default=datetime.utcnow)
    success     = Column(Boolean, default=True)


class SystemMetric(Base):
    __tablename__ = "system_metrics"
    id          = Column(Integer, primary_key=True, index=True)
    cpu_pct     = Column(Float)
    ram_pct     = Column(Float)
    disk_pct    = Column(Float)
    ram_used_gb = Column(Float)
    captured_at = Column(DateTime, default=datetime.utcnow)


class MailmanRecord(Base):
    __tablename__ = "mailman_records"
    id           = Column(Integer, primary_key=True, index=True)
    gmail_msg_id = Column(String(64), unique=True, index=True)
    subject      = Column(String(512))
    sender       = Column(String(256))
    category     = Column(String(64))
    priority     = Column(String(16))
    llm_summary  = Column(Text, nullable=True)
    starred      = Column(Boolean, default=False)
    labeled      = Column(Boolean, default=False)
    processed_at = Column(DateTime, default=datetime.utcnow)


def init_db():
    Base.metadata.create_all(bind=engine)


@contextmanager
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def log_agent(db: Session, agent: str, level: str, message: str):
    db.add(AgentLog(agent_name=agent, level=level, message=message))
    db.commit()
