import humps
from pydantic import BaseModel, Field
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


class StoresResponse(BaseModel):
    stores:List[StoreResponse]
    class Config:
        orm_mode = True
        alias_generator = humps.camelize
        allow_population_by_field_name = True

class StoreCreateRequest(BaseModel):
    storeName: str = Field(min_length=1,max_length=100)
    address: str = Field(min_length=1,max_length=100)
    content: str = Field(min_length=1,max_length=100)
    tags:List[str] = Field(min_length=1,max_length=100)