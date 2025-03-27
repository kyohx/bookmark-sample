from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse

from .controllers import bookmark, version
from .libs.version import APP_VERSION


def create_app() -> FastAPI:
    """
    WebAPP インスタンス生成
    """
    app = FastAPI(
        title="Bookmark API",
        description="API for bookmarking web page URL",
        version=APP_VERSION,
        default_response_class=ORJSONResponse,
    )

    # gzip圧縮
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # ルーティング設定
    for router in (
        bookmark.router,
        version.router,
    ):
        app.include_router(router)

    return app


app = create_app()
