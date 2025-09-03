import uuid
from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, UniqueConstraint, Table
from sqlalchemy.dialects.postgresql import UUID, DOUBLE_PRECISION
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.models.stores_tags_table import stores_tags_table
from database import Base


class Tag(Base):
    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    tag_id = Column(UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4)
    tag_name = Column(String(100), nullable=False)
    created_at = Column(TIMESTAMP, nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP, nullable=False, server_default=func.now())

    # Storeオブジェクトとの多対多リレーション
    stores = relationship("Store", secondary=stores_tags_table, back_populates="tags")