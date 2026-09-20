import json
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


def _database_url():
    """Postgres when the deployment supplies one, SQLite otherwise.

    DB_SECRET carries the Secrets Manager JSON that ECS injects into the task
    ({username, password, dbname}); DB_HOST is the RDS endpoint. Neither is present
    when running locally, so local development stays on SQLite with no setup.
    """
    host = os.getenv("DB_HOST")
    secret = os.getenv("DB_SECRET")
    if not host:
        return "sqlite:///./incidents.db", {"check_same_thread": False}

    if secret:
        creds = json.loads(secret)
        user = creds.get("username", "aisre")
        password = creds.get("password", "")
        dbname = creds.get("dbname", "aisre")
    else:
        user = os.getenv("DB_USER", "aisre")
        password = os.getenv("DB_PASSWORD", "")
        dbname = os.getenv("DB_NAME", "aisre")

    port = os.getenv("DB_PORT", "5432")
    return f"postgresql+psycopg://{user}:{password}@{host}:{port}/{dbname}", {}


SQLALCHEMY_DATABASE_URL, _connect_args = _database_url()

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args=_connect_args,
    pool_pre_ping=True,
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
