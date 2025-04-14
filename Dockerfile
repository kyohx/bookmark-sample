## Dockerfile for Heroku

## ----- Stage for building python packages base
FROM python:3.13-slim AS builder

# uv(Pythonパッケージマネージャ)インストール
RUN pip3 install uv
ENV UV_PROJECT_ENVIRONMENT="/usr/local/"
ENV UV_COMPILE_BYTECODE=1

# Pythonモジュールのインストール
COPY pyproject.toml uv.lock ./
RUN uv sync --no-dev --frozen

## ----- Stage for web app base
FROM python:3.13-slim AS app

# Webアプリのパス指定
ARG APP_HOME=/opt/app
# Webアプリディレクトリ作成
RUN mkdir -p ${APP_HOME} &&\
    chmod 777 ${APP_HOME}
WORKDIR ${APP_HOME}
# 実行ユーザー名指定
ARG USER=app
# app ユーザー/グループの作成
RUN groupadd -o -g 1000 ${USER} &&\
    useradd --create-home -u 1000 -g ${USER} ${USER}

# ubuntuパッケージインストール
RUN apt-get update &&\
    apt-get upgrade -y &&\
    apt-get install -y\
        default-libmysqlclient-dev\
    &&\
    apt-get clean &&\
    rm -rf /var/lib/apt/lists/*

# ビルド済みのpythonモジュールをコピー
COPY --from=builder /usr/local/lib/python3.13/site-packages /usr/local/lib/python3.13/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# 実行ユーザ指定
USER ${USER}
# Pythonの標準出力内容をバッファリングせずにリアルタイムに反映させる
ENV PYTHONUNBUFFERED=1
# Pythonのコンパイル済みファイル(*.pyc)を作成しない
ENV PYTHONDONTWRITEBYTECODE=1

COPY . ${APP_HOME}

# デフォルトの起動コマンド設定
CMD uvicorn src.main:app --workers 2 --host 0.0.0.0 --port $PORT
