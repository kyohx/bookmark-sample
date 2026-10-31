import json
from datetime import UTC, datetime
from logging import Formatter, LogRecord

from .request_context import get_exception_request_id, get_request_id


class JsonFormatter(Formatter):
    """改行や例外を含むログを1行のJSONとして出力する。"""

    def format(self, record: LogRecord) -> str:
        entry = {
            "timestamp": datetime.fromtimestamp(record.created, UTC).isoformat(
                timespec="milliseconds"
            ),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": get_request_id()
            or get_exception_request_id(record.exc_info[1] if record.exc_info else None),
        }
        if record.exc_info:
            entry["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            entry["stack_info"] = self.formatStack(record.stack_info)
        return json.dumps(entry, ensure_ascii=False)
