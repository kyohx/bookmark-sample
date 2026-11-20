import json

from fastapi import FastAPI

from .main import app


def generate_openapi_json(app: FastAPI) -> None:
    """
    アプリの OpenAPI スキーマを整形した JSON として標準出力に出力する。

    Args:
        app: スキーマの生成対象となる FastAPI アプリ
    """
    # OpenAPI JSON を標準出力へ出力
    print(json.dumps(app.openapi(), indent=2, ensure_ascii=False))


generate_openapi_json(app)
