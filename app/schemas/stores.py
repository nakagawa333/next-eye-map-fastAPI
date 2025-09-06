import humps
from pydantic import BaseModel
from typing import List

from app.schemas.store import StoreResponse

class StoresResponse(BaseModel):
    stores:List[StoreResponse]
    class Config:
        orm_mode = True
        alias_generator = humps.camelize
        allow_population_by_field_name = True