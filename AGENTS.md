# AGENTS.md

このファイルは、このリポジトリを扱う AI エージェント向けの短い実務メモです。

## リポジトリ概要

- Web URL を管理する **FastAPI 製のブックマーク API** サンプルです。
- **本番利用前提ではないサンプルコード**です。README にもその前提があります。
- 主な構成要素:
  - Web API: FastAPI + uvicorn
  - DB: MySQL
  - Cache / KVS: Redis
  - ORM: SQLAlchemy
  - Query cache: dogpile.cache + zstd 圧縮

## 主要ディレクトリ

- `src/controllers/`: FastAPI のエンドポイント
- `src/usecases/`: ユースケース層
- `src/repositories/`: リポジトリ層
- `src/dao/models/`: SQLAlchemy モデル
- `src/dao/operators/`: DAO 操作
- `src/dto/`: リクエスト/レスポンス DTO
- `src/entities/`: ドメイン寄りのエンティティ
- `src/services/`: 認可などのサービス層
- `src/libs/`: 共通ライブラリ
- `tests/integration/`: 結合テスト
- `tests/unit/`: 単体テスト
- `docs/query_cache_design.md`: クエリキャッシュ詳細設計

## アプリ構成の把握ポイント

- アプリ生成は `src/main.py` の `create_app()`。
- ルーティングは `auth`, `bookmark`, `user`, `version` の controller を `include_router()` しています。
- 実装の基本的な流れは **controller → usecase → repository → dao/operator** です。
- `dto` は API 入出力、`entities` は内部表現として使われています。
- 認証は JWT ベースで、`src/services/authorize.py` にトークン発行・検証の主要ロジックがあります。
- 権限制御は `AuthorityEnum` と `UserDepends` / usecase 側の `required_authority` で行われています。

## 開発コマンド

- 依存関係同期: `uv sync`
- 仮想環境有効化: `source .venv/bin/activate`
- コンテナ起動: `docker compose up -d`
- コンテナ停止: `docker compose down`
- フォーマット: `task format`
- 静的チェック: `task check`
- テスト: `task test`
- OpenAPI 生成: `task openapi`

## 開発時の注意

- `task test` は `docker compose exec api python -m pytest` を呼ぶため、通常は API コンテナ起動後に実行します。
- integration test は MySQL ベースで、FastAPI の dependency override を使って DB セッションや認証依存を差し替えています。
- Python は `3.13` 固定です。
- フォーマットは Ruff ベースで、文字列はダブルクォート設定です。
- OpenAPI の生成物はルートの `openapi.json` です。

## キャッシュまわり

- クエリキャッシュ実装は `src/libs/cache/` にあります。
- クエリキャッシュは実装済みですが、設定上は **デフォルト無効** です。`CACHE_ENABLED=1` かつ `CACHE_REDIS_URL` 設定時に有効化されます。
- `src/repositories/bookmark.py` では `@query_cache` を使っています。
- 一覧系キャッシュは **version bump による無効化**、詳細系は **キー直接削除** の方針です。
- integration test では共有キャッシュの影響を避けるため `NullCacheRegion` に差し替えています。
- 仕様を追う場合は `docs/query_cache_design.md` を先に読むと把握しやすいです。

## 変更時の実務メモ

- まず README と `pyproject.toml` を見ると、起動方法・主要コマンド・依存関係を把握できます。
- API 変更時は `src/controllers/`, `src/dto/`, `src/usecases/`, `src/repositories/` をまとめて確認してください。
- キャッシュや取得結果に関わる変更では `src/libs/cache/` と repository 実装、関連テストを合わせて確認してください。
