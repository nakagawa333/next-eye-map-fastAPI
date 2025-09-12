from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError
from fastapi import APIRouter, Depends, HTTPException, Response
from typing import List, Union

import humps
from app.models.stores_tags_table import stores_tags_table
from sqlalchemy import func, insert, literal, select
from app.models.store import Store
from app.models.tag import Tag
from app.schemas.stores import StoreCreateRequest, StoreResponse, StoresResponse
from database import Base, SessionLocal,engine
import httpx
import uuid

router = APIRouter(prefix="/stores",tags=["stores"])

@router.get("/",response_model=StoresResponse)
def read_stores(serach_name: Union[str, None] = None):
    stores:List[str] = []
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
def read_store(store_id: str):
    store:StoreResponse = None

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

@router.post("/")
async def create_store(store:StoreCreateRequest):

    #TODO 認証処理を追加 Barser

    #国土地理院のAPIのURL
    url:str = f"https://msearch.gsi.go.jp/address-search/AddressSearch"

    params = {
        "q":store.address
    }

    async with httpx.AsyncClient() as client:
        #国土地理院のAPIから緯度と経度を取得
        resp = await client.get(url, params=params)
        resp.raise_for_status()
    
    if resp.status_code != 200:
        raise HTTPException(status_code=500, detail="国土地理院APIから応答がありません")
    
    data = resp.json()

    if not data:
        raise HTTPException(status_code=404,detail="該当する住所が見つかりません")
    
    geometry = data[0].get("geometry")
    if not geometry or not geometry.get("coordinates"):
        raise HTTPException(status_code=404,detail="該当する住所が見つかりません")
    
    lng,lat = geometry.get("coordinates")

    with SessionLocal() as db:
        #トランザクション開始
        with db.begin():
            select_tags:List[str] = []
            tag_stmt = (
                select(
                    Tag.tag_name
                )
                .where(Tag.tag_name.in_(store.tags))
            )

            #DB取得処理
            try:
                select_tags = db.execute(tag_stmt).mappings().all()
            except Exception as e:
                raise HTTPException(status_code=500, detail="サーバーエラーが発生しました")
            
            set_select_tags = {select_tag["tag_name"] for select_tag in select_tags}

            tag_ids:List[str] = []
            if store.tags:
                tags_values:List[Tag] = []

                for store_tag in store.tags:
                    #tagテーブルに存在しない場合、追加
                    if store_tag not in set_select_tags:
                        tag_id:uuid.UUID = uuid.uuid4()
                        tag:Tag = Tag(tag_id=tag_id,tag_name=store_tag)
                        tags_values.append(tag)

                tags_dicts = [{"tag_id": t.tag_id, "tag_name": t.tag_name} for t in tags_values]
                if tags_dicts:
                    try:
                        #タグテーブルに追加
                        insert_tag_stmt = insert(Tag).values(tags_dicts).returning(Tag.id)
                        tag_ids = db.execute(insert_tag_stmt).scalars().all()
                    except Exception as e:
                        raise HTTPException(status_code=500, detail="サーバーエラーが発生しました")    

            store_dicts = {
                "store_id":uuid.uuid4(),
                "store_name":store.storeName,
                "address":store.address,
                "content":store.content,
                "lat":lat,
                "lng":lng
            }

            store_id:str = None
            try:
                #店舗テーブルにデータを追加
                insert_store_stmt = insert(Store).values(store_dicts).returning(Store.id)
                store_id = db.execute(insert_store_stmt).scalar_one()
            except Exception as e:
                raise HTTPException(status_code=500, detail="サーバーエラーが発生しました")
            
            #中間テーブルにデータを追加
            if tag_ids:
                stores_tags = []
                for tag_id in tag_ids:
                    stores_tags_dicts = {
                        "stores_tags_id":uuid.uuid4(),
                        "store_id":store_id,
                        "tag_id":tag_id                    
                    }
                    stores_tags.append(stores_tags_dicts)
                try:
                    insert_stores_tags_stmt = insert(stores_tags_table).values(stores_tags)
                    db.execute(insert_stores_tags_stmt)
                except Exception as e:
                    print(e)
                    raise HTTPException(status_code=500, detail="サーバーエラーが発生しました")
    
    return Response(status_code=201)
