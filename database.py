from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base,Session
from dotenv import load_dotenv
load_dotenv()

import os

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL, echo=True)
SessionLocal:Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()