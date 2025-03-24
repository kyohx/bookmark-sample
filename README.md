# ブックマーク API

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

- `docker/` : Docker関連
- `src/` : Web API ソースコード
- `compose.yaml` : docker compose 設定ファイル
- `pyproject.toml` : プロジェクト設定ファイル
- `uv.lock` : パッケージ依存関係ロックファイル

## 動作に必要なもの

- uv (Pythonパッケージマネージャ)
  - [インストール方法](https://github.com/astral-sh/uv/blob/main/README.md#installation)  
- Docker 環境
  - docker compose が使用可能なこと

## API仕様

後述の手順でコンテナを起動後に以下のURLを参照

- Swagger http://localhost:8000/docs
- Redoc http://localhost:8000/redoc

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

### 初期設定

```bash
uv sync
. .venv/bin/activate
```

### 通常開発時

#### 全コンテナの起動

```
docker compose up -d
```

#### 全コンテナの停止・削除

```
docker compose down
```

DB内容はコンテナを削除しても保持される。


#### DB内容を完全に削除

```
docker compose down -v
```

#### APIコンテナのビルド

```
task buildapp
```

#### ソースコードのフォーマット

```
task format
```

#### ソースコードのチェック(型チェック等)

```
task check
```

#### テスト実行

```
task test
```
