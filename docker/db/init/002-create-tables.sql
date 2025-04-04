-- ---------------------------------------------------------------------------
use app;
-- ---------------------------------------------------------------------------

-- ブックマーク情報
create table if not exists `bookmark` (
	`id`				integer primary key auto_increment not null comment "ID",
	`hashed_id`			varchar(64) unique not null comment "ハッシュID",
	`url`				varchar(400) not null comment "URL",
	`memo`				varchar(400) not null comment "メモ",
	`created_at`		datetime not null default current_timestamp comment "登録日時",
	`updated_at`		datetime not null default current_timestamp on update current_timestamp comment "更新日時"
) comment 'ブックマーク情報';

-- タグ情報
create table if not exists `tag` (
	`id`				integer primary key auto_increment not null comment "ID",
	`name`				varchar(100) unique not null comment "タグ名",
	`created_at`		datetime not null default current_timestamp comment "登録日時",
	`updated_at`		datetime not null default current_timestamp on update current_timestamp comment "更新日時"
) comment 'タグ情報';

-- ブックマークとタグの関連情報
create table if not exists `bookmark_tag` (
	`id`				integer primary key auto_increment not null comment "ID",
	`bookmark_id`		integer not null comment "ブックマークID",
	foreign key(bookmark_id) references `bookmark`(id) on delete cascade,
	`tag_id`			integer not null comment "タグID",
	foreign key(tag_id) references `tag`(id) on delete cascade,
	`created_at`		datetime not null default current_timestamp comment "登録日時",
	`updated_at`		datetime not null default current_timestamp on update current_timestamp comment "更新日時",
	unique (bookmark_id, tag_id)
) comment 'ブックマークとタグの関連情報';

-- ユーザ情報
create table if not exists `user` (
	`id`				integer primary key auto_increment not null comment "ID",
	`name`				varchar(32) unique not null comment "ユーザ名",
	`hashed_password`	varchar(64) not null comment "パスワードハッシュ",
	`disabled`			tinyint(1) not null default 0 comment "無効フラグ",
	`authority`			tinyint(1) not null default 1 comment "権限",
	`created_at`		datetime not null default current_timestamp comment "登録日時",
	`updated_at`		datetime not null default current_timestamp on update current_timestamp comment "更新日時"
) comment 'ユーザ情報';
