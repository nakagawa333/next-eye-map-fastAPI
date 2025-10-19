# @pytest.fixture()
# def test_setup():
#     #DB初期化
#     DATABASE_URL = os.getenv("DATABASE_URL_TEST")
#     engine = create_engine(DATABASE_URL, echo=True)
#     SessionLocal: Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
#     Base = declarative_base()
#     Base.metadata.drop_all(engine)
#     Base.metadata.create_all(engine)
#     SessionFactory = sessionmaker(autocommit=False, autoflush=False, bind=engine)

#     db: Session = None
#     try:
#         db = SessionFactory()
#         db.commit()

#         yield db
#         # db.commit()
#     except Exception:
#         db.rollback()
#     finally:
#         # teardown
#         db.close()
