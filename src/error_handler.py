import pymysql.constants.ER as errcode
from fastapi import FastAPI, Request, status
from fastapi.responses import ORJSONResponse
from sqlalchemy.exc import IntegrityError, OperationalError

from .libs.log import get_logger
from .repositories.base import BaseRepository
from .services.auth import AuthorizeService
from .usecases.base import UsecaseBase

logger = get_logger()


def add_error_handlers(app: FastAPI) -> None:
    """
    エラーハンドラ追加
    """

    @app.exception_handler(AuthorizeService.Error)
    async def auth_error_handler(request: Request, exc: AuthorizeService.Error):
        return ORJSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content={"detail": str(exc)},
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(UsecaseBase.AuthorityError)
    async def authority_error_handler(request: Request, exc: UsecaseBase.AuthorityError):
        return ORJSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": str(exc)},
        )

    @app.exception_handler(UsecaseBase.OperationError)
    async def operation_error_handler(request: Request, exc: UsecaseBase.OperationError):
        return ORJSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc)},
        )

    @app.exception_handler(BaseRepository.NotFoundError)
    async def not_found_handler(request: Request, exc: BaseRepository.NotFoundError):
        return ORJSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={"detail": str(exc)},
        )

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

        logger.exception(str(exc), exc_info=exc)
        return ORJSONResponse(status_code=status_code, content={"detail": message})

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

        logger.exception(str(exc), exc_info=exc)
        return ORJSONResponse(status_code=status_code, content={"detail": message})
