from sqlmodel import Session, create_engine

from app.core.config import DATABASE_URL, DB_ECHO

engine = create_engine(
    DATABASE_URL,
    echo=DB_ECHO,
    connect_args={"check_same_thread": False},
)


def get_session():
    with Session(engine) as session:
        yield session
