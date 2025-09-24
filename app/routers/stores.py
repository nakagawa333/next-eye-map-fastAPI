import traceback
import uuid
from logging import getLogger
from typing import List, Union
from uuid import UUID

import httpx
import humps
from fastapi import (APIRouter, Depends, HTTPException, Query, Request,
                     Response, status)
from sqlalchemy import delete, func, insert, literal, select, update
from sqlalchemy.exc import IntegrityError, OperationalError, ProgrammingError

from app.config.constants import GSIAPI, EndPoints
from app.models.store import Store
from app.models.stores_tags_table import stores_tags_table
from app.models.tag import Tag
from app.schemas.stores import (StoreCreateRequest, StoreResponse,
                                StoresResponse, StoreUpdateRequest)
from app.services.gsi_api import fetch_coordinates_from_gsi
from app.utils.db_exceptions import handle_db_exception
from config.logging_config import setup_logger
from database import Base, SessionLocal, engine

router = APIRouter(prefix=EndPoints.STORES,tags=["stores"])

logger = getLogger("app")

# GETで店舗一覧を取得
@router.get("/",response_model=StoresResponse)
def read_stores(serach_name: Union[str] = Query(None,max_length=100),tag_name: Union[str] = Query(None,max_length=100)):
    """
    店舗一覧を取得する

    Args:
        serach_name (Union[str, None], optional): 検索文字
        tag_name (Union[str, None], optional): タグ名

    Returns:
        _type_: 複数店舗レスポンスモデル
    """

    logger.info(f"店舗一覧取得リクエスト")

    with SessionLocal() as db:
        try:
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

            #検索条件リスト
            conditions:List[str] = []
            
            #検索文字あり   
            if serach_name:
                conditions.append(Store.store_name.ilike(f"%{serach_name}%"))

            if tag_name:
                subquery = (
                    select(stores_tags_table.c.store_id)
                    .join(Tag, stores_tags_table.c.tag_id == Tag.id)
                    .where(Tag.tag_name == tag_name)
                )
                conditions.append(Store.id.in_(subquery))

            #検索条件が指定されている場合、where句に条件を追加
            if conditions:
                stmt = stmt.where(*conditions)

            stores = db.execute(stmt).mappings().all()
        except Exception as e:
            logger.error(f"DB処理失敗: {e.__class__.__name__}: {e}")
            handle_db_exception(e)
        finally:
            logger.info("DB処理終了")
        
    return {
        "stores":humps.camelize(stores)
    }

# GETで特定の店舗を取得
@router.get("/{store_id}", response_model=StoreResponse)
def read_store(store_id: UUID):
    """
    指定した店舗IDの情報を取得する
    
    Args:
        store_id (UUID): 取得対象の店舗ID

    Raises:
        HTTPException: 店舗が存在しない場合 (404 Not Found)

    Returns:
        _type_: 単一店舗レスポンスモデル
    """

    logger.info(f"店舗取得リクエスト: {store_id}")

    with SessionLocal() as db:
        logger.info("DB処理開始")
        try:
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
            store = db.execute(stmt).mappings().first()
        except Exception as e:
            logger.error(f"DB処理失敗: {e.__class__.__name__}: {e}")
            handle_db_exception(e)
        finally:
            logger.info("DB処理終了")
 
    if store is None:
        logger.warning(f"該当する店舗が存在しませんでした:{store_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="該当する店舗が存在しませんでした")
        
    return humps.camelize(store)

# POSTで店舗を作成
@router.post("/")
async def create_store(store:StoreCreateRequest):
    """
    新しい店舗情報を登録する

    Args:
        store (StoreCreateRequest): 店舗作成用のリクエストモデル

    Raises:
        HTTPException: 国土地理院APIに接続できない場合 (400 Bad Request)
        HTTPException: 国土地理院APIが不正なステータスコードを返した場合 (400 Bad Request)
        HTTPException: 国土地理院APIへのリクエストが失敗した場合 (500 Internal Server Error)
        HTTPException: 指定した住所が存在しない場合 (404 Not Found)
        HTTPException: DB処理に失敗した場合 (500 Internal Server Error)

    Returns:
        Response: ステータスコード201を返却（店舗登録成功時）
    """

    logger.info(f"新規店舗作成リクエスト: {store.storeName}")
    
    params = {
        "q":store.address
    }

    try:
        #国土地理院のAPIから緯度と経度を取得
        resp = await fetch_coordinates_from_gsi(params)
        data = resp.json()
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception("外部API呼び出し失敗")
        raise HTTPException(status_code=500, detail="サーバー内部エラー")
    
    data = resp.json()

    if not data:
        logger.warning(f"該当する住所が存在しませんでした:{store.address}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="該当する住所が見つかりません")
    
    geometry = data[0].get("geometry")
    if not geometry or not geometry.get("coordinates"):
        logger.warning(f"該当する住所が存在しませんでした:{store.address}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="該当する住所が見つかりません")
    
    #緯度、経度
    lng,lat = geometry.get("coordinates")

    #DBセッション開始
    with SessionLocal() as db:
        logger.info("トランザクション開始")

        try:
            #トランザクション開始
            with db.begin():
                select_tags:List[str] = []
                tag_stmt = (
                    select(
                        Tag.id,
                        Tag.tag_name
                    )
                    .where(Tag.tag_name.in_(store.tags))
                )

                #DB取得処理
                select_tags = db.execute(tag_stmt).mappings().all()
                
                set_select_tags = {select_tag.get("tag_name") for select_tag in select_tags}

                tag_ids:List[str] = []

                if select_tags:
                    tag_ids = [select_tag.get("id") for select_tag in select_tags]

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
                        logger.info(f"新規タグ追加: {[t['tag_name'] for t in tags_dicts]}")
                        insert_tag_stmt = insert(Tag).values(tags_dicts).returning(Tag.id)
                        res_tags_ids = db.execute(insert_tag_stmt).scalars().all()
                        if res_tags_ids:
                            tag_ids.extend(res_tags_ids)

                store_dicts = {
                    "store_id":uuid.uuid4(),
                    "store_name":store.storeName,
                    "address":store.address,
                    "content":store.content,
                    "lat":lat,
                    "lng":lng
                }

                store_id:str = None

                #店舗テーブルにデータを追加
                insert_store_stmt = insert(Store).values(store_dicts).returning(Store.id)
                store_id = db.execute(insert_store_stmt).scalar_one()

                logger.info(f"店舗登録成功: store_id={store_id}, name={store.storeName}")
                
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

                    logger.debug(f"中間テーブル登録データ: {stores_tags}")
                    insert_stores_tags_stmt = insert(stores_tags_table).values(stores_tags)
                    db.execute(insert_stores_tags_stmt)
                    
        except Exception as e:
            logger.error("トランザクション失敗")
            handle_db_exception(e)
        logger.info("トランザクション終了")

    return Response(status_code=status.HTTP_201_CREATED)

# DELETEで店舗を作成
@router.delete("/")
def delete_store(store_id: UUID):
    """
    店舗情報を削除する
    Args:
        store_id (UUID): 店舗ID

    Raises:
        HTTPException: 店舗が存在しない場合 (404 Not Found)

    Returns:
       Response: ステータスコード204を返却（店舗削除成功時）
    """
    logger.info(f"店舗削除リクエスト: {store_id}")

    with SessionLocal() as db:
        logger.info("トランザクション開始")

        try:
            with db.begin():
                store_stmt = (
                    select(
                        Store.id
                    )
                    .where(Store.store_id == store_id)
                )

                select_store_id = db.execute(store_stmt).scalar()

                if not select_store_id:
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="該当する店舗が存在しませんでした")

                #中間テーブル削除
                delete_stmt = delete(stores_tags_table).where(stores_tags_table.c.store_id == select_store_id)
                db.execute(delete_stmt)
                
                logger.debug(f"中間テーブル削除成功: {store_id}")

                #店舗を削除
                delete_store_stmt = delete(Store).where(Store.store_id == store_id)
                db.execute(delete_store_stmt)
                logger.info(f"店舗削除成功: {store_id}")

        except Exception as e:
            logger.error("トランザクション失敗")
            handle_db_exception(e)

        logger.info("トランザクション終了")
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    
@router.patch("/")
async def update_store(store:StoreUpdateRequest):
    """
    店舗情報を更新するAPI

    Args:
        store (StoreUpdateRequest): 店舗更新リクエストモデル

    Raises:
        HTTPException: 国土地理院APIが応答しない場合
        HTTPException: 指定住所が存在しない場合
        HTTPException: 該当店舗が存在しない場合
        HTTPException: データベース例外（整合性・接続等）が発生した場合

    Returns:
        Response: HTTP 204 NO CONTENT（更新成功）
    """

    update_values = {}
    #リクエストに店舗名が含まれている場合
    if store.storeName is not None:
        update_values["store_name"] = store.storeName

    #リクエストに住所が含まれている場合
    if store.address is not None:
        params = {
            "q":store.address
        }

    try:
        #国土地理院のAPIから緯度と経度を取得
        resp = await fetch_coordinates_from_gsi(params)
        data = resp.json()
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.exception("外部API呼び出し失敗")
        raise HTTPException(status_code=500, detail="サーバー内部エラー")
    
    data = resp.json()

    if not data:
        logger.warning(f"該当する住所が存在しませんでした:{store.address}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="該当する住所が見つかりません")
    
    geometry = data[0].get("geometry")
    if not geometry or not geometry.get("coordinates"):
        logger.warning(f"該当する住所が存在しませんでした:{store.address}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="該当する住所が見つかりません")
        
    update_values["address"] = store.address

    if store.content is not None:
        update_values["content"] = store.content

    #DBセッション開始
    with SessionLocal() as db:
        try:
            with db.begin():

                #店舗名、住所、内容が更新される場合、DBを更新
                if update_values:
                    update_stmt = update(Store).where(Store.store_id == store.storeId).values(update_values)
                    db.execute(update_stmt)

                store_stmt = (
                    select(
                        Store.id
                    )
                    .where(Store.store_id == store.storeId)                    
                )

                #店舗IDからPKを取得
                select_store_id = db.execute(store_stmt).scalar()

                if not select_store_id:
                    logger.info(f"該当する店舗が存在しませんでした:{store.storeId}")
                    raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="該当する店舗が存在しませんでした")
                
                #既存タグの取得
                select_stores_tags_stmt = (
                    select(
                        stores_tags_table.c.stores_tags_id,
                        Tag.tag_name,
                    )
                    .select_from(stores_tags_table)
                    .where(stores_tags_table.c.store_id == select_store_id)
                    .outerjoin(Tag, stores_tags_table.c.tag_id == Tag.id)
                )

                logger.info("店舗情報の取得開始")
                select_stores_tags = db.execute(select_stores_tags_stmt).mappings().all()
                logger.info("店舗情報の取得完了")

                # 辞書形式で整理 {tag_name: {stores_tags_id, tag_name}}
                select_stores_tags_objs = {

                }
                for select_stores_tag in select_stores_tags:
                    tag_name = select_stores_tag.get("tag_name")
                    select_stores_tags_objs[tag_name] = select_stores_tag

                #タグの差分更新
                if store.tags:
                    tags:set[str] = set(store.tags)
                    if select_stores_tags_objs:
                        select_stores_tags_names = set(select_stores_tags_objs.keys())
                        #削除するタグ名
                        delete_tags_names = select_stores_tags_names - tags
                        #追加するタグ名
                        add_tags_names = tags - select_stores_tags_names

                        #削除処理
                        if delete_tags_names:
                            select_stores_tags_ids = []
                            
                            for delete_tags_name in delete_tags_names:
                                select_stores_tags_obj = select_stores_tags_objs.get(delete_tags_name)
                                if select_stores_tags_obj:
                                    select_stores_tags_ids.append(select_stores_tags_obj.get("stores_tags_id"))

                            #差分のあるタグを削除
                            delete_stores_tags_stmt = delete(stores_tags_table).where(stores_tags_table.c.stores_tags_id.in_(select_stores_tags_ids))
                            db.execute(delete_stores_tags_stmt)
                        
                        #追加処理
                        if add_tags_names:
                            tags_stmt = (
                                select(
                                    Tag.tag_name,
                                    Tag.id
                            )
                                .where(Tag.tag_name.in_(add_tags_names))                    
                            )

                            select_tags = db.execute(tags_stmt).mappings().all()

                            #タグテーブルに存在しない場合、追加
                            if not select_tags:
                                tags_dicts = []
                                for add_tags_name in add_tags_names:
                                    tags_dict = {
                                        "tag_id":uuid.uuid4(),
                                        "tag_name":add_tags_name
                                    }
                                    tags_dicts.append(tags_dict)

                                logger.info("新規タグ作成開始")
                                insert_tag_stmt = insert(Tag).values(tags_dicts).returning(Tag.id,Tag.tag_name)
                                res_tags = db.execute(insert_tag_stmt).mappings().all()
                                logger.info("新規タグ作成完了")
                                select_tags.extend(res_tags)

                            # 中間テーブルに追加（空リスト防止のためチェック）
                            if select_tags:
                                stores_tags_table_dicts = []
                                for select_tag in select_tags:
                                    stores_tags_table_dict = {
                                        "stores_tags_id":uuid.uuid4(),
                                        "store_id":select_store_id,
                                        "tag_id":select_tag.get("id")
                                    }

                                    stores_tags_table_dicts.append(stores_tags_table_dict)

                                logger.info("中間テーブル更新開始")
                                insert_stores_tags_table_stmt = insert(stores_tags_table).values(stores_tags_table_dicts)
                                db.execute(insert_stores_tags_table_stmt)
                                logger.info("中間テーブル更新成功")

        except Exception as e:
            logger.error("トランザクション失敗")
            handle_db_exception(e)

        return Response(status_code=status.HTTP_204_NO_CONTENT)

                