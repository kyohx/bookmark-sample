from fastapi import FastAPI
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import ORJSONResponse

from .controllers import auth, bookmark, user, version
from .error_handler import add_error_handlers
from .libs.openapi_tags import OPENAPI_TAGS
from .libs.version import APP_VERSION


def create_app() -> FastAPI:
    """
    WebAPP インスタンス生成
    """
    app = FastAPI(
        title="Bookmark API",
        description="API for bookmarking web page URL",
        openapi_tags=OPENAPI_TAGS,
        version=APP_VERSION,
        default_response_class=ORJSONResponse,
    )

    # gzip圧縮
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # ルーティング設定
    for controller in (auth, bookmark, user, version):
        app.include_router(controller.router, tags=[controller.tagname])

    # エラーハンドラ追加
    add_error_handlers(app)

    return app


app = create_app()
