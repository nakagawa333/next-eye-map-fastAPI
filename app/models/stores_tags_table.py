import uuid
from sqlalchemy import Column, Integer, String, TIMESTAMP, ForeignKey, UniqueConstraint, Table
from sqlalchemy.dialects.postgresql import UUID, DOUBLE_PRECISION
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

# 中間テーブル
stores_tags_table = Table(
    "stores_tags",
    Base.metadata,
    Column("id", Integer, primary_key=True, index=True),
    Column("stores_tags_id", UUID(as_uuid=True), unique=True, nullable=False, default=uuid.uuid4),
    Column("store_id", Integer, ForeignKey("stores.id"), nullable=False),
    Column("tag_id", Integer, ForeignKey("tags.id"), nullable=False),
    Column("created_at", TIMESTAMP, nullable=False, server_default=func.now()),
    Column("updated_at", TIMESTAMP, nullable=False, server_default=func.now()),
    UniqueConstraint("store_id", "tag_id", name="uq_store_tag")
)
