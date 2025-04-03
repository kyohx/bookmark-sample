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

## 実装予定

- [ ] テストコードの拡充
- [ ] ページネーション

## システム構成

- Web API: FastAPI + uvicorn
- DB: MySQL 8.4

## ディレクトリ/ファイル構成

- `docker/` : ローカル環境向け Docker関連ファイル
- `src/` : Web API ソースコード
- `tests/` : テストコード
- `compose.yaml` : ローカル環境向け docker compose 設定ファイル
- `Dockerfile` : Heroku環境向け Dockerfile
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

## 接続情報

### WebAPI

http://localhost:8000

### DB

- ホスト名: localhost
- ポート: 3306
- ユーザ名: root
- パスワード: root
- DB名: app

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
task buildapp
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
