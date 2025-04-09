from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse

from .controllers import auth, bookmark, user, version
from .error_handler import add_error_handlers
from .libs.version import APP_VERSION


def create_app() -> FastAPI:
    """
    WebAPP インスタンス生成
    """
    app = FastAPI(
        title="Bookmark API",
        description="API for bookmarking web page URL",
        openapi_tags=[
            {
                "name": "auth",
                "description": "Authentication operations",
            },
            {
                "name": "bookmark",
                "description": "Bookmark operations",
            },
            {
                "name": "user",
                "description": "User operations",
            },
            {
                "name": "version",
                "description": "API version",
            },
        ],
        version=APP_VERSION,
        default_response_class=ORJSONResponse,
    )

    # gzip圧縮
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # ルーティング設定
    for router in (
        auth.router,
        bookmark.router,
        user.router,
        version.router,
    ):
        app.include_router(router)

    add_error_handlers(app)

    return app


app = create_app()
