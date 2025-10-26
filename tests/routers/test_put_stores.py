import pytest
from pytest_postgresql import factories
from sqlalchemy import create_engine, delete, insert
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.models.store import Store
from app.models.stores_tags_table import stores_tags_table
from app.models.tag import Tag
from database import get_db, get_session_local

postgresql_noproc = factories.postgresql_noproc()
postgresql_fixture = factories.postgresql(
    "postgresql_noproc",
)

@pytest.fixture()
def test_setup():
    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        #db初期化
        db_init(db)
        yield db

    finally:
        #db初期化
        db_init(db)
        db.close()

def db_init(db:Session):
    """
    DB初期化

    Args:
        db (Session): dbセッション
    """
    delete_stores_tags_table_stmt = delete(stores_tags_table)
    delete_tag_stmt = delete(Tag)
    delete_store_stmt = delete(Store)

    db.execute(delete_stores_tags_table_stmt)
    db.execute(delete_tag_stmt)
    db.execute(delete_store_stmt)
    db.commit()


