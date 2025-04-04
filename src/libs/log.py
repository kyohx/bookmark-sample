import sys
from logging import DEBUG, ERROR, INFO, Formatter, StreamHandler, getLogger

from ..libs.config import get_config

_config = get_config()

_LOGLEVEL_TABLE = {
    "DEBUG": DEBUG,
    "INFO": INFO,
    "ERROR": ERROR,
}

_level = _config.log_level
_logger = getLogger("API")
_handler = StreamHandler(sys.stdout)
_handler.setLevel(_LOGLEVEL_TABLE[_level])
_handler.setFormatter(Formatter("[%(asctime)s][%(levelname)s]%(message)s"))
_logger.addHandler(_handler)
_logger.setLevel(_LOGLEVEL_TABLE[_level])


def get_logger():
    return _logger
