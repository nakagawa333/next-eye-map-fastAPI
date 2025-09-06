from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from fastapi import APIRouter, Depends, HTTPException
from typing import Union

import humps
from app.models.stores_tags_table import stores_tags_table
from sqlalchemy import func, literal, select
from app.models.store import Store
from app.models.tag import Tag
from app.schemas.store import StoreResponse
from app.schemas.stores import StoresResponse
from database import Base, SessionLocal,engine

router = APIRouter(prefix="/stores",tags=["stores"])

@router.get("/",response_model=StoresResponse)
def read_root(serach_name: Union[str, None] = None):
    stores = []
    with SessionLocal() as db:

        stmt = (
            select(
                Store.store_id,
                Store.store_name,
                Store.address,
                Store.content,
                Store.lat,
                Store.lng,
                func.coalesce(
                    func.array_agg(Tag.tag_name).filter(Tag.tag_name != None),
                    literal([])
                ).label("tags")
            )   
            .outerjoin(stores_tags_table, stores_tags_table.c.store_id == Store.id)
            .outerjoin(Tag, stores_tags_table.c.tag_id == Tag.id)
            .group_by(Store.id)
        )
        
        #検索文字あり   
        if serach_name:
            stmt = stmt.where(
                Store.store_name.ilike(f"%{serach_name}%")
            )

        #DB取得処理
        try:
            stores = db.execute(stmt).mappings().all()
        except ProgrammingError as e:
            raise HTTPException(status_code=500, detail="データベースの構造に問題があります")
        except OperationalError as e:
            raise HTTPException(status_code=503, detail="データベースに接続できません")
        except IntegrityError as e:
            raise HTTPException(status_code=400, detail="データ整合性の問題が発生しました")
        except Exception as e:
            raise HTTPException(status_code=500, detail="サーバーエラーが発生しました")
        
    return {
        "stores":humps.camelize(stores)
    }
    
@router.get("/{store_id}", response_model=StoreResponse)
def read_item(store_id: str):
    store = None

    with SessionLocal() as db:
        stmt = (
            select(
                Store.store_id,
                Store.store_name,
                Store.address,
                Store.content,
                Store.lat,
                Store.lng,
                func.coalesce(
                    func.array_agg(Tag.tag_name).filter(Tag.tag_name != None),
                    literal([])
                ).label("tags")
            )   
            .outerjoin(stores_tags_table, stores_tags_table.c.store_id == Store.id)
            .outerjoin(Tag, stores_tags_table.c.tag_id == Tag.id)
            .where(Store.store_id == store_id)
            .group_by(Store.id)
        )
        
        #DB取得処理
        try:
            store = db.execute(stmt).mappings().first()
        except ProgrammingError as e:
            raise HTTPException(status_code=500, detail="データベースの構造に問題があります")
        except OperationalError as e:   
            raise HTTPException(status_code=503, detail="データベースに接続できません")
        except IntegrityError as e:
            raise HTTPException(status_code=400, detail="データ整合性の問題が発生しました")
        except Exception as e:
            raise HTTPException(status_code=500, detail="サーバーエラーが発生しました")
 
    if store is None:
        raise HTTPException(status_code=404,detail="該当する店舗が存在しません")
        
    return humps.camelize(store)    