-- Project Name : noname
-- Date/Time    : 2025/09/25 22:29:09
-- Author       : sosei
-- RDBMS Type   : Oracle Database
-- Application  : A5:SQL Mk-2

/*
  << 注意！！ >>
  BackupToTempTable, RestoreFromTempTable疑似命令が付加されています。
  これにより、drop table, create table 後もデータが残ります。
  この機能は一時的に $$TableName のような一時テーブルを作成します。
  この機能は A5:SQL Mk-2でのみ有効であることに注意してください。
*/

-- 店舗
-- * RestoreFromTempTable
create table stores (
  id serial not null
  , store_id uuid not null
  , store_name character varying(100) not null
  , address character varying(100) not null
  , content character varying(100) not null
  , lat double precision not null
  , lng double precision not null
  , created_at timestamp(6) without time zone default CURRENT_TIMESTAMP not null
  , updated_at timestamp(6) without time zone default CURRENT_TIMESTAMP not null
  , constraint stores_PKC primary key (id)
) ;

alter table stores add constraint stores_store_id_key
  unique (store_id) ;

-- 店舗とタグの中間テーブル
-- * RestoreFromTempTable
create table stores_tags (
  id serial not null
  , stores_tags_id uuid not null
  , store_id serial not null
  , tag_id serial not null
  , created_at timestamp(6) without time zone default CURRENT_TIMESTAMP not null
  , updated_at timestamp(6) without time zone default CURRENT_TIMESTAMP not null
  , constraint stores_tags_PKC primary key (id)
) ;

alter table stores_tags add constraint stores_tags_stores_tags_id_key
  unique (stores_tags_id) ;

-- タグ
-- * RestoreFromTempTable
create table tags (
  id serial not null
  , tag_id uuid not null
  , tag_name character varying(100) not null
  , created_at timestamp(6) without time zone default CURRENT_TIMESTAMP not null
  , updated_at timestamp(6) without time zone default CURRENT_TIMESTAMP not null
  , constraint tags_PKC primary key (id)
) ;

alter table tags add constraint tags_tag_id_key
  unique (tag_id) ;

comment on table stores is '店舗';
comment on column stores.id is 'ID';
comment on column stores.store_id is '店舗UUID';
comment on column stores.store_name is '店舗名';
comment on column stores.address is '住所';
comment on column stores.content is '店舗の説明・紹介文';
comment on column stores.lat is '緯度';
comment on column stores.lng is '経度';
comment on column stores.created_at is '作成日時';
comment on column stores.updated_at is '更新日時';

comment on table stores_tags is '店舗とタグの中間テーブル';
comment on column stores_tags.id is 'ID';
comment on column stores_tags.stores_tags_id is '関係UUID';
comment on column stores_tags.store_id is '店舗UUID';
comment on column stores_tags.tag_id is 'タグUUID';
comment on column stores_tags.created_at is '作成日時';
comment on column stores_tags.updated_at is '更新日時';

comment on table tags is 'タグ';
comment on column tags.id is 'ID';
comment on column tags.tag_id is '外部公開用のタグUUID';
comment on column tags.tag_name is 'タグ名';
comment on column tags.created_at is '作成日時';
comment on column tags.updated_at is '更新日時';

