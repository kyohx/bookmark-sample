import asyncio
import io
import json
import logging
from threading import Barrier, get_ident
from unittest.mock import AsyncMock
from uuid import UUID

import httpx2
import pytest
from fastapi import HTTPException, Request
from fastapi.testclient import TestClient
from starlette.background import BackgroundTask
from starlette.responses import StreamingResponse

from src.libs.log_formatter import JsonFormatter
from src.libs.request_context import get_request_id, request_id_context
from src.libs.request_id import RequestIdMiddleware
from src.main import create_app


@pytest.fixture
def app_and_logs():
    output = io.StringIO()
    logger = logging.Logger("test.request_id", logging.INFO)
    handler = logging.StreamHandler(output)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    app = create_app()

    @app.get("/inspect")
    def inspect_request(request: Request):
        logger.info("sync endpoint")
        return {"request_id": get_request_id(), "state_id": request.state.request_id}

    @app.get("/typed")
    def typed(number: int):
        return number

    @app.get("/unauthorized")
    def unauthorized():
        logger.warning("unauthorized")
        raise HTTPException(status_code=401)

    @app.get("/failure")
    def failure():
        logger.error("before failure")
        raise RuntimeError("test failure")

    @app.get("/stream")
    async def stream():
        async def body():
            logger.info("stream start")
            yield f"{get_request_id()}:first\n"
            await asyncio.sleep(0)
            logger.info("stream end")
            yield f"{get_request_id()}:last\n"

        return StreamingResponse(body(), background=BackgroundTask(logger.info, "background"))

    return app, output, logger


def entries(output):
    return [json.loads(line) for line in output.getvalue().splitlines()]


def test_request_id_matches_header_state_and_sync_log(app_and_logs):
    app, output, logger = app_and_logs
    with TestClient(app) as client:
        first = client.get("/inspect", headers={"X-Request-ID": "client-supplied"})
        second = client.get("/inspect")
    ids = [response.headers["X-Request-ID"] for response in (first, second)]
    assert len(set(ids)) == 2
    for response, request_id in zip((first, second), ids, strict=True):
        assert response.status_code == 200
        assert len(request_id) == 32
        assert UUID(request_id).version == 4
        assert response.json() == {"request_id": request_id, "state_id": request_id}
    assert [entry["request_id"] for entry in entries(output)] == ids
    assert get_request_id() is None
    logger.info("outside request")
    assert entries(output)[-1]["request_id"] is None


@pytest.mark.parametrize(
    "path,status",
    [("/missing", 404), ("/typed?number=bad", 422), ("/unauthorized", 401), ("/failure", 500)],
)
def test_error_responses_include_request_id(app_and_logs, path, status):
    app, output, _ = app_and_logs
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(path)
        next_response = client.get("/inspect")
    assert response.status_code == status
    request_id = response.headers["X-Request-ID"]
    assert UUID(request_id).version == 4
    assert request_id != next_response.headers["X-Request-ID"]
    for entry in entries(output):
        if entry["message"] in ("before failure", "unauthorized"):
            assert entry["request_id"] == request_id
    assert get_request_id() is None


def test_stream_and_background_logs_keep_request_id(app_and_logs):
    app, output, _ = app_and_logs
    with TestClient(app) as client:
        response = client.get("/stream")
    assert response.status_code == 200
    request_id = response.headers["X-Request-ID"]
    assert response.text == f"{request_id}:first\n{request_id}:last\n"
    logs = entries(output)
    assert [entry["message"] for entry in logs] == ["stream start", "stream end", "background"]
    assert all(entry["request_id"] == request_id for entry in logs)


@pytest.mark.parametrize("fail_one", [False, True])
def test_parallel_sync_workers_keep_ids_separate_and_reset_on_reuse(app_and_logs, fail_one):
    """defエンドポイントを別スレッドで同時実行し、再利用時もIDが混ざらない。"""
    app, output, logger = app_and_logs
    barrier = Barrier(2, timeout=5)
    workers = {}
    event_loop_thread = get_ident()

    @app.get("/parallel/{index}")
    def parallel(index: int, request: Request):
        request_id = get_request_id()
        assert request_id is not None
        assert request_id == request.state.request_id
        workers[index] = (get_ident(), request_id)
        logger.info("worker %s before barrier", index)
        # asyncioのイベントループではなく、2つの同期ワーカーが同時に到達する必要がある。
        barrier.wait()
        logger.info("worker %s after barrier", index)
        assert get_request_id() == request_id
        if fail_one and index == 1:
            raise RuntimeError("worker failure")
        return {"request_id": request_id}

    @app.get("/reuse")
    def reuse():
        logger.info("reused worker")
        return {"request_id": get_request_id(), "thread_id": get_ident()}

    async def exercise():
        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app, raise_app_exceptions=False),
            base_url="http://test",
        ) as client:
            responses = await asyncio.gather(client.get("/parallel/0"), client.get("/parallel/1"))
            # 同じイベントループのAnyIOプールを再利用する。
            reused = [await client.get("/reuse") for _ in range(3)]
            assert get_request_id() is None
            return responses, reused

    responses, reused = asyncio.run(exercise())
    assert [response.status_code for response in responses] == [200, 500 if fail_one else 200]
    worker_threads = {thread_id for thread_id, _ in workers.values()}
    assert len(worker_threads) == 2
    assert event_loop_thread not in worker_threads
    ids = []
    logs = entries(output)
    for index, response in enumerate(responses):
        request_id = response.headers["X-Request-ID"]
        ids.append(request_id)
        assert request_id == workers[index][1]
        if response.status_code == 200:
            assert response.json()["request_id"] == request_id
        worker_logs = [entry for entry in logs if entry["message"].startswith(f"worker {index} ")]
        assert [entry["message"] for entry in worker_logs] == [
            f"worker {index} before barrier",
            f"worker {index} after barrier",
        ]
        assert all(entry["request_id"] == request_id for entry in worker_logs)
    for response in reused:
        assert response.status_code == 200
        request_id = response.headers["X-Request-ID"]
        ids.append(request_id)
        assert response.json()["request_id"] == request_id
        assert response.json()["thread_id"] in worker_threads
    assert len(set(ids)) == 5
    assert [entry["request_id"] for entry in logs if entry["message"] == "reused worker"] == ids[2:]
    assert get_request_id() is None
    logger.info("outside request")
    assert entries(output)[-1]["request_id"] is None


def test_concurrent_async_requests_do_not_share_ids(app_and_logs):
    app, output, logger = app_and_logs

    async def exercise():
        both_started = asyncio.Event()
        started = 0

        @app.get("/concurrent")
        async def concurrent():
            nonlocal started
            request_id = get_request_id()
            logger.info("before await")
            started += 1
            if started == 2:
                both_started.set()
            await asyncio.wait_for(both_started.wait(), timeout=5)
            logger.info("after await")
            assert get_request_id() == request_id
            return {"request_id": request_id}

        async with httpx2.AsyncClient(
            transport=httpx2.ASGITransport(app=app), base_url="http://test"
        ) as client:
            return await asyncio.gather(client.get("/concurrent"), client.get("/concurrent"))

    responses = asyncio.run(exercise())
    ids = {response.headers["X-Request-ID"] for response in responses}
    assert len(ids) == 2
    for response in responses:
        assert response.status_code == 200
        assert response.json()["request_id"] == response.headers["X-Request-ID"]
    logs = entries(output)
    for request_id in ids:
        assert [entry["message"] for entry in logs if entry["request_id"] == request_id] == [
            "before await",
            "after await",
        ]
    assert get_request_id() is None


@pytest.mark.parametrize("scope_type", ["lifespan", "websocket"])
def test_non_http_scopes_pass_through_without_request_id(scope_type):
    seen = []

    async def inner(scope, receive, send):
        seen.append((scope, get_request_id()))

    scope = {"type": scope_type}
    asyncio.run(RequestIdMiddleware(inner)(scope, AsyncMock(), AsyncMock()))
    assert seen == [(scope, None)]
    assert "state" not in scope


@pytest.mark.parametrize("error", [None, RuntimeError, asyncio.CancelledError])
def test_context_is_restored_after_response_exception_or_cancellation(error):
    async def inner(scope, receive, send):
        assert get_request_id() != "parent-context"
        if error:
            raise error("test")

    async def exercise():
        token = request_id_context.set("parent-context")
        try:
            middleware = RequestIdMiddleware(inner)
            if error:
                with pytest.raises(error):
                    await middleware({"type": "http"}, AsyncMock(), AsyncMock())
            else:
                await middleware({"type": "http"}, AsyncMock(), AsyncMock())
            assert get_request_id() == "parent-context"
        finally:
            request_id_context.reset(token)

    asyncio.run(exercise())
    assert get_request_id() is None
