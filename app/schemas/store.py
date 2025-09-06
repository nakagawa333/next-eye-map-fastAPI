import humps
from pydantic import BaseModel
from typing import List, Optional
from uuid import UUID

class StoreResponse(BaseModel):
    storeId: UUID
    storeName: str
    address: str
    content:str
    lat: float
    lng: float
    tags:Optional[List[str]]

    class Config:
        orm_mode = True
        alias_generator = humps.camelize
        allow_population_by_field_name = True
