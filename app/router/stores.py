from collections import defaultdict
from fastapi import APIRouter, Depends
from typing import Optional, Union
from app.models.stores_tags_table import stores_tags_table
from sqlalchemy import select
from app.models.store import Store
from app.models.tag import Tag
from database import Base, SessionLocal,engine # 追加

router = APIRouter()

@router.get("/stores")
def read_root(serach_name: Union[str, None] = None):
    with SessionLocal() as db:
        stores = []
        stmt = (
            select(
                Store.store_id,
                Store.store_name,
                Store.address,
                Store.content,
                Store.lat,
                Store.lng,
                Tag.tag_name,
            )
            .outerjoin(stores_tags_table, stores_tags_table.c.store_id == Store.id)
            .outerjoin(Tag, stores_tags_table.c.tag_id == Tag.id)
        )
        #検索文字あり   
        if serach_name:
            stmt = stmt.where(
                Store.store_name.ilike(f"%{serach_name}%")
            )

        #DB取得処理 
        result = db.execute(stmt).mappings().all()

        stores_dict = defaultdict(lambda: {
            "storeId":None,
            "storeName":None,
            "address":None,
            "content":None,
            "lat":None,
            "lng":None,
            "tags":[]
        })

        for row in result:
            store = stores_dict[row["store_id"]]
            store["storeId"] = row["store_id"]
            store["storeName"] = row["store_name"]
            store["address"] = row["address"]
            store["content"] = row["content"]
            store["lat"] = row["lat"]
            store["lng"] = row["lng"]

            tag_name = row.get("tag_name")
            if tag_name:
                store["tags"].append(row["tag_name"])

        stores = list(stores_dict.values())
        return {
            "stores":stores
        }