# app/db/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os

# 从环境变量或配置读取连接字符串，默认为本地 SQLite
# 未来切换 MySQL 只需修改这个 URL 即可
SQLALCHEMY_DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./study_engine.db")

# check_same_thread 仅用于 SQLite
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# 获取数据库 Session 的依赖
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()