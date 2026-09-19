from collections.abc import Mapping
from typing import Final

import pymysql.constants.ER as errcode
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError

from .libs.log import get_logger
from .repositories.base import BaseRepository
from .services.authority import AuthorityService
from .services.authorize import AuthorizeService
from .services.token_blacklist import TokenBlacklistService
from .usecases.base import UsecaseBase

logger: Final = get_logger()

DatabaseErrorRule = tuple[int, str]


def _detail_response(
    status_code: int,
    detail: str,
    *,
    headers: dict[str, str] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={"detail": detail},
        headers=headers,
    )


def _database_error_response(
    exc: IntegrityError | OperationalError,
    *,
    status_code: int,
    message: str,
) -> JSONResponse:
    # 異常系エラーはログにスタックトレースを出す
    if status_code == status.HTTP_500_INTERNAL_SERVER_ERROR:
        logger.exception(str(exc), exc_info=exc)
    return _detail_response(status_code, message)


def _resolve_database_error(
    exc: IntegrityError | OperationalError,
    *,
    rules: Mapping[int, DatabaseErrorRule],
) -> DatabaseErrorRule:
    status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
    message = "Internal Server Error"
    if exc.orig is not None and hasattr(exc.orig, "args"):
        rule = rules.get(exc.orig.args[0])
        if rule is not None:
            return rule
    return status_code, message


def add_error_handlers(app: FastAPI) -> None:
    """
    エラーハンドラ追加
    """

    @app.exception_handler(AuthorizeService.Error)
    async def auth_error_handler(request: Request, exc: AuthorizeService.Error):
        return _detail_response(
            status.HTTP_401_UNAUTHORIZED,
            str(exc),
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(TokenBlacklistService.Error)
    async def blacklist_error_handler(request: Request, exc: TokenBlacklistService.Error):
        return _detail_response(status.HTTP_503_SERVICE_UNAVAILABLE, str(exc))

    @app.exception_handler(AuthorityService.Error)
    async def authority_error_handler(request: Request, exc: AuthorityService.Error):
        return _detail_response(status.HTTP_403_FORBIDDEN, str(exc))

    @app.exception_handler(UsecaseBase.OperationError)
    async def operation_error_handler(request: Request, exc: UsecaseBase.OperationError):
        return _detail_response(status.HTTP_400_BAD_REQUEST, str(exc))

    @app.exception_handler(BaseRepository.NotFoundError)
    async def not_found_handler(request: Request, exc: BaseRepository.NotFoundError):
        return _detail_response(status.HTTP_404_NOT_FOUND, str(exc))

    @app.exception_handler(IntegrityError)
    async def integrity_error_handler(request: Request, exc: IntegrityError):
        status_code, message = _resolve_database_error(
            exc,
            rules={
                errcode.DUP_KEY: (status.HTTP_409_CONFLICT, "Duplicate error"),
                errcode.DUP_ENTRY: (status.HTTP_409_CONFLICT, "Duplicate error"),
                errcode.NO_REFERENCED_ROW: (
                    status.HTTP_424_FAILED_DEPENDENCY,
                    "Foreign key constraint error",
                ),
                errcode.NO_REFERENCED_ROW_2: (
                    status.HTTP_424_FAILED_DEPENDENCY,
                    "Foreign key constraint error",
                ),
            },
        )

        return _database_error_response(exc, status_code=status_code, message=message)

    @app.exception_handler(OperationalError)
    async def operational_error_handler(request: Request, exc: OperationalError):
        status_code, message = _resolve_database_error(
            exc,
            rules={
                errcode.LOCK_DEADLOCK: (status.HTTP_409_CONFLICT, "Deadlock error"),
            },
        )

        return _database_error_response(exc, status_code=status_code, message=message)
