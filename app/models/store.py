import uuid
from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, UniqueConstraint, Table
from sqlalchemy.dialects.postgresql import UUID, DOUBLE_PRECISION
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.stores_tags_table import stores_tags_table
from database import Base

class Store(Base):
    __tablename__ = "stores"

    id = Column(Integer, primary_key=True, index=True)
    store_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    store_name = Column(String(100), nullable=False)
    address = Column(String(100), nullable=False)
    content = Column(String(100), nullable=False)
    lat = Column(DOUBLE_PRECISION, nullable=False)
    lng = Column(DOUBLE_PRECISION, nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    # Tagオブジェクトとの多対多リレーション
    tags = relationship("Tag", secondary=stores_tags_table, back_populates="stores")