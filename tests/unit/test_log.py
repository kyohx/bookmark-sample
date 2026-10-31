import io
import json
import logging
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import pytest

from src.libs.log_formatter import JsonFormatter

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture
def json_logger():
    output = io.StringIO()
    handler = logging.StreamHandler(output)
    handler.setFormatter(JsonFormatter())
    logger = logging.Logger("test.json", logging.DEBUG)
    logger.addHandler(handler)
    return logger, output


@pytest.mark.parametrize("level", [logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR])
def test_log_is_one_json_line_with_interpolated_message(json_logger, level):
    logger, output = json_logger
    message = '日本語 "quoted" \\path\n次の行\r\n\tタブ'
    before = datetime.now(UTC)
    logger.log(level, "message: %s (%d)", message, 42)
    after = datetime.now(UTC)

    lines = output.getvalue().splitlines()
    assert len(lines) == 1
    assert "日本語" in lines[0]
    entry = json.loads(lines[0])
    timestamp = datetime.fromisoformat(entry.pop("timestamp"))
    assert timestamp.tzinfo == UTC
    assert before.replace(microsecond=before.microsecond // 1000 * 1000) <= timestamp <= after
    assert entry == {
        "level": logging.getLevelName(level),
        "logger": "test.json",
        "message": f"message: {message} (42)",
        "request_id": None,
    }


def test_exception_chain_and_stack_info_stay_in_one_json_line(json_logger):
    logger, output = json_logger
    try:
        try:
            raise ValueError("元の例外\n詳細")
        except ValueError as cause:
            raise RuntimeError("処理失敗") from cause
    except RuntimeError:
        logger.exception("保存に失敗: %s", "bookmark", stack_info=True)

    lines = output.getvalue().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["message"] == "保存に失敗: bookmark"
    assert "Traceback (most recent call last)" in entry["exception"]
    assert "ValueError: 元の例外\n詳細" in entry["exception"]
    assert "RuntimeError: 処理失敗" in entry["exception"]
    assert "direct cause" in entry["exception"]
    assert "Stack (most recent call last)" in entry["stack_info"]
    assert "test_exception_chain_and_stack_info" in entry["stack_info"]


@pytest.mark.parametrize(
    ("level", "expected_levels"),
    [
        ("DEBUG", ["DEBUG", "INFO", "WARNING", "ERROR"]),
        ("INFO", ["INFO", "WARNING", "ERROR"]),
        ("ERROR", ["ERROR"]),
    ],
)
@pytest.mark.parametrize("sql_debug", [False, True])
def test_runtime_logging_config_outputs_json_without_duplicates(level, expected_levels, sql_debug):
    # 別プロセスでUvicornの実設定を使い、pytest自身のログ設定への影響を避ける。
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import logging
import os

from uvicorn import Config
from sqlalchemy import create_engine, text

Config('src.main:app', log_config='config/logging.json')
from src.libs.log import get_logger

logger = get_logger()
assert logger is get_logger()
for level in (logging.DEBUG, logging.INFO, logging.WARNING, logging.ERROR):
    logger.log(level, 'アプリ %s', logging.getLevelName(level))
logging.getLogger('uvicorn.error').info('サーバ起動 %s', 'ready')
logging.getLogger('uvicorn.access').info(
    '%s - "%s %s HTTP/%s" %d', '127.0.0.1:12345', 'GET', '/version', '1.1', 200
)
logging.getLogger('third_party').warning('ライブラリ警告')
engine = create_engine('sqlite://', echo=os.environ['DATABASE_DEBUG'] == '1')
with engine.connect() as connection:
    connection.execute(text('SELECT 1'))
engine.dispose()
""",
        ],
        cwd=ROOT,
        env={**os.environ, "LOG_LEVEL": level, "DATABASE_DEBUG": str(int(sql_debug))},
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert result.stderr == ""
    entries = [json.loads(line) for line in result.stdout.splitlines()]
    assert all(entry["request_id"] is None for entry in entries)
    app_entries = [entry for entry in entries if entry["logger"] == "API"]
    assert [entry["level"] for entry in app_entries] == expected_levels
    assert [entry["message"] for entry in app_entries] == [
        f"アプリ {level}" for level in expected_levels
    ]
    for name, message in (
        ("uvicorn.error", "サーバ起動 ready"),
        ("uvicorn.access", '127.0.0.1:12345 - "GET /version HTTP/1.1" 200'),
        ("third_party", "ライブラリ警告"),
    ):
        assert [entry["message"] for entry in entries if entry["logger"] == name] == [message]
    sql_entries = [entry for entry in entries if entry["logger"] == "sqlalchemy.engine.Engine"]
    assert [entry["message"] for entry in sql_entries].count("SELECT 1") == int(sql_debug)
    assert bool(sql_entries) == sql_debug


def test_real_uvicorn_access_error_and_sql_logs_share_response_request_id():
    """ソケットを使わず実UvicornのHTTP処理を動かし、サーバーログまで検証する。"""
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            """
import asyncio
import json
from unittest.mock import Mock

from sqlalchemy import create_engine, text
from uvicorn import Config
from uvicorn.protocols.http.h11_impl import H11Protocol
from uvicorn.server import ServerState

config = Config('src.main:app', log_config='config/logging.json', lifespan='off', http='h11')
from src.libs.log import get_logger
from src.libs.request_context import get_request_id
from src.main import create_app

app = create_app()
config.app = app

@app.get('/ok')
def ok():
    get_logger().info('sync endpoint')
    engine = create_engine('sqlite://', echo=True)
    with engine.connect() as connection:
        connection.execute(text('SELECT 1'))
    engine.dispose()
    return {'ok': True}

@app.get('/failure')
def failure():
    get_logger().error('before failure')
    raise RuntimeError('test unhandled error')

async def main():
    for path, status in (('/ok', 200), ('/failure', 500)):
        state = ServerState()
        protocol = H11Protocol(config, state, {})
        transport = Mock(spec=asyncio.Transport)
        transport.get_extra_info.return_value = None
        transport.is_closing.return_value = False
        protocol.connection_made(transport)
        protocol.data_received(f'GET {path} HTTP/1.1\\r\\nHost: test\\r\\n\\r\\n'.encode())
        await asyncio.gather(*list(state.tasks))
        response = b''.join(call.args[0] for call in transport.write.call_args_list)
        assert response.startswith(f'HTTP/1.1 {status}'.encode()), response
        headers = dict(
            line.split(b': ', 1)
            for line in response.split(b'\\r\\n\\r\\n', 1)[0].split(b'\\r\\n')[1:]
        )
        print(json.dumps({'response': path, 'request_id': headers[b'x-request-id'].decode()}))
        protocol.connection_lost(None)
        assert get_request_id() is None
    get_logger().info('outside request')

asyncio.run(main())
""",
        ],
        cwd=ROOT,
        env={**os.environ, "LOG_LEVEL": "INFO"},
        capture_output=True,
        text=True,
        check=True,
        timeout=30,
    )
    assert result.stderr == ""
    entries = [json.loads(line) for line in result.stdout.splitlines()]
    responses = {entry["response"]: entry["request_id"] for entry in entries if "response" in entry}
    assert set(responses) == {"/ok", "/failure"}
    assert responses["/ok"] != responses["/failure"]
    logs = [entry for entry in entries if "logger" in entry]
    for path in ("/ok", "/failure"):
        access = [
            entry
            for entry in logs
            if entry["logger"] == "uvicorn.access" and f"GET {path} HTTP" in entry["message"]
        ]
        assert len(access) == 1
        assert access[0]["request_id"] == responses[path]
    for message, path in (("sync endpoint", "/ok"), ("before failure", "/failure")):
        app_logs = [
            entry for entry in logs if entry["logger"] == "API" and entry["message"] == message
        ]
        assert len(app_logs) == 1
        assert app_logs[0]["request_id"] == responses[path]
    sql_logs = [entry for entry in logs if entry["logger"] == "sqlalchemy.engine.Engine"]
    assert sql_logs
    assert all(entry["request_id"] == responses["/ok"] for entry in sql_logs)
    error_logs = [entry for entry in logs if entry["logger"] == "uvicorn.error"]
    assert len(error_logs) == 1
    assert error_logs[0]["request_id"] == responses["/failure"]
    assert "RuntimeError: test unhandled error" in error_logs[0]["exception"]
    outside = [entry for entry in logs if entry["message"] == "outside request"]
    assert len(outside) == 1
    assert outside[0]["request_id"] is None
