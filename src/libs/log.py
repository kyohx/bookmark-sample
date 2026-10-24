import sys
from logging import DEBUG, ERROR, INFO, Logger, StreamHandler, getLogger
from typing import Final

from ..libs.config import get_config
from .log_formatter import JsonFormatter

_config = get_config()

_LOGLEVEL_TABLE: Final[dict[str, int]] = {
    "DEBUG": DEBUG,
    "INFO": INFO,
    "ERROR": ERROR,
}

_level = _config.log_level
_logger = getLogger("API")
_handler = StreamHandler(sys.stdout)
_handler.setLevel(_LOGLEVEL_TABLE[_level])
_handler.setFormatter(JsonFormatter())
_logger.addHandler(_handler)
_logger.setLevel(_LOGLEVEL_TABLE[_level])
_logger.propagate = False


def get_logger() -> Logger:
    """
    ロガー取得

    Returns:
        ロガー
    """
    return _logger
