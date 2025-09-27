## Dockerfile for Heroku

ARG PYTHON_VER=3.13

## ----- Stage for building python packages
FROM ghcr.io/astral-sh/uv:python${PYTHON_VER}-trixie-slim AS builder
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --no-dev --frozen

## ----- Stage for web app
FROM python:${PYTHON_VER}-slim AS app

ARG PYTHON_VER

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
COPY --from=builder /usr/local/lib/python${PYTHON_VER}/site-packages /usr/local/lib/python${PYTHON_VER}/site-packages

# 実行ユーザ指定
USER ${USER}
# Pythonの標準出力内容をバッファリングせずにリアルタイムに反映させる
ENV PYTHONUNBUFFERED=1
# Pythonのコンパイル済みファイル(*.pyc)を作成しない
ENV PYTHONDONTWRITEBYTECODE=1

COPY . ${APP_HOME}

# デフォルトの起動コマンド設定
CMD python -m uvicorn src.main:app --workers 2 --host 0.0.0.0 --port $PORT
