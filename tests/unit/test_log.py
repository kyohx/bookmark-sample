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
