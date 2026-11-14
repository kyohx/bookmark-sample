# syntax=docker/dockerfile:1

ARG PYTHON_VER=3.14
ARG UV_VERSION=0.13.8

FROM ghcr.io/astral-sh/uv:${UV_VERSION} AS uv

# Use the same Python and Debian release for dependency installation and execution.
FROM python:${PYTHON_VER}-slim-trixie AS base
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH"
WORKDIR /opt/app

FROM base AS builder
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=0 \
    UV_PROJECT_ENVIRONMENT=/opt/venv

FROM builder AS production-deps
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project --compile-bytecode

FROM builder AS development-deps
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

FROM base AS runtime
RUN groupadd --gid 1000 app \
    && useradd --create-home --uid 1000 --gid app app \
    && chown app:app /opt/app
USER app

# Compose mounts the repository at /opt/app; keep the virtual environment outside it.
FROM runtime AS development
COPY --from=development-deps /opt/venv /opt/venv
EXPOSE 8000
CMD ["python", "-m", "uvicorn", "src.main:app", "--log-config", "config/logging.json", "--reload", "--host", "0.0.0.0", "--port", "8000"]

# The default target is the Render image, with only runtime dependencies and source.
FROM runtime AS app
COPY --from=production-deps /opt/venv /opt/venv
COPY src ./src
COPY config ./config
EXPOSE 10000
CMD ["python", "-m", "uvicorn", "src.main:app", "--log-config", "config/logging.json", "--workers", "2", "--host", "0.0.0.0", "--port", "10000"]
