# ブックマーク API

[![Check and Tests](https://github.com/kyohx/bookmark-sample/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/kyohx/bookmark-sample/actions/workflows/ci.yml)
[![Deploy](https://github.com/kyohx/bookmark-sample/actions/workflows/deploy.yml/badge.svg)](https://github.com/kyohx/bookmark-sample/actions/workflows/deploy.yml)
[![security: bandit](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![License: MIT](https://img.shields.io/badge/License-MIT-brightgreen.svg)](https://opensource.org/licenses/MIT)

## 概要

Web URL ブックマーク管理API (サンプルコード)

## 免責条項・ライセンス

本リポジトリ(`bookmark-sample.git`)の内容は**本格的な使用を想定していないサンプル**であることを理解した方のみ閲覧・使用をしてください。

ライセンスはMITライセンスです。

## システム構成

- Web API: FastAPI + uvicorn
- DB: MySQL 8.4
- KVS: Redis 8.6

## ディレクトリ/ファイル構成

- `docker/` : ローカル環境向け Docker関連ファイル
- `src/` : Web API ソースコード
- `tests/` : テストコード
- `compose.yaml` : ローカル環境向け docker compose 設定ファイル
- `Dockerfile` : Render SaaS環境向け Dockerfile
- `openapi.json` : OpenAPI(API仕様)ファイル
- `pyproject.toml` : プロジェクト設定ファイル
- `uv.lock` : パッケージ依存関係ロックファイル

## ローカル環境での動作に必要なもの

- uv (Pythonパッケージマネージャ)
  - [インストール方法](https://docs.astral.sh/uv/getting-started/installation/)
- Docker 環境
  - docker compose が使用可能なこと

## API仕様

### ファイル

- JSON形式
  - [openapi.json](https://github.com/kyohx/bookmark-sample/blob/main/openapi.json)

### GUI

後述の手順でコンテナを起動後に以下のURLを参照

- Swagger形式
  - http://localhost:8000/docs
- Redoc形式
  - http://localhost:8000/redoc

### セッション管理

管理者は `GET /users/{name}/sessions` でユーザーのリフレッシュセッションを確認できます。レスポンスにはセッション ID（リフレッシュトークンの `fam`）、作成・最終利用・有効期限、失効状態、ログイン時の User-Agent が含まれます。日時は UTC の `YYYY-MM-DD HH:MM:SS` 形式です。トークン本体は返しません。User-Agent はクライアントが送る値であり、端末の確実な識別情報ではありません。

対象セッションを止めるには `DELETE /users/{name}/sessions/{session_id}` を使用します。対象の family をブラックリストに登録し、そのセッションのリフレッシュトークンを拒否します。再ログインで作られる別セッションには影響しません。旧 `/auth/blacklist/*` 管理 API は廃止しました。トークンのローテーションと再利用検知に使うブラックリストの内部処理は継続します。

発行済みアクセストークンはセッション失効後も有効期限まで使えます（標準設定で最大20分）。即時に API アクセスを止める場合は、管理者が `PATCH /users/{name}` で `disabled=true` にしてください。再有効化する前に、再利用させたくないセッションを失効させてください。

セッション台帳は blacklist 用 Redis に保存します。ログイン、一覧取得、失効操作には `BLACKLIST_REDIS_URL` が必要です。Redis が利用できない場合、これらの操作は 503 を返します。既存のリフレッシュ処理は `BLACKLIST_REDIS_FAIL_OPEN` の設定に従い、標準設定では Redis 障害時にブラックリスト照会を通過します。失効の強制を優先する運用では `BLACKLIST_REDIS_FAIL_OPEN=0` にしてください。導入前に発行されたセッションは、次のリフレッシュ後から一覧に現れます。

## 接続情報

### WebAPI

http://localhost:8000

#### API認証

- ユーザ名: testuser
- パスワード: n3#7%$tB5T

### DB

- ホスト名: localhost
- ポート: 3306
- ユーザ名: root
- パスワード: root
- DB名: app

#### TiDB Cloud (Starter / Essential) 利用時

TiDB Cloud は TLS 接続必須のため、以下を環境変数で設定してください。

- `DATABASE_SSL_ENABLED=1`
- `DATABASE_SSL_VERIFY_CERT=1`
- `DATABASE_SSL_VERIFY_IDENTITY=1`
- `DATABASE_SSL_CA_CERTS=/etc/ssl/certs/ca-certificates.crt` (Debian/Ubuntu系の例)

## 手順

### 開発作業開始時

```bash
uv sync
source .venv/bin/activate
```

### 通常開発時

#### 全コンテナの起動

```bash
docker compose up -d
```

#### 全コンテナの停止・削除

```bash
docker compose down
```

DB内容はコンテナを削除しても保持される。


#### DB内容を完全に削除

```bash
docker compose down -v
```

#### APIコンテナのビルド

```bash
task build_app
```

#### ソースコードのフォーマット

```bash
task format
```

#### ソースコードのチェック(型チェック等)

```bash
task check
```

#### テスト実行

```bash
task test
```

#### OpenAPIファイル生成

```bash
task openapi
```

#### Pythonパッケージ更新

```bash
task update_packages
```
