# create_tables.py
from flask import app
from .database import engine, Base
from . import models

# アプリ起動時にテーブル作成
@app.on_event("startup")
def on_startup():
    Base.metadata.create_all(bind=engine)