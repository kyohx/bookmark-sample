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
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        message = "Internal Server Error"
        if exc.orig is not None and hasattr(exc.orig, "args"):
            match exc.orig.args[0]:
                case errcode.DUP_KEY | errcode.DUP_ENTRY:
                    # キー重複
                    status_code = status.HTTP_409_CONFLICT
                    message = "Duplicate error"
                case errcode.NO_REFERENCED_ROW | errcode.NO_REFERENCED_ROW_2:
                    # 外部キー制約違反
                    status_code = status.HTTP_424_FAILED_DEPENDENCY
                    message = "Foreign key constraint error"

        return _database_error_response(exc, status_code=status_code, message=message)

    @app.exception_handler(OperationalError)
    async def operational_error_handler(request: Request, exc: OperationalError):
        status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        message = "Internal Server Error"
        if exc.orig is not None and hasattr(exc.orig, "args"):
            match exc.orig.args[0]:
                case errcode.LOCK_DEADLOCK:
                    # デッドロック
                    status_code = status.HTTP_409_CONFLICT
                    message = "Deadlock error"

        return _database_error_response(exc, status_code=status_code, message=message)
