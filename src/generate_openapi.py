import orjson
from fastapi import FastAPI

from .main import app


def generate_openapi_json(app: FastAPI) -> None:
    # OpenAPI JSON を標準出力へ出力
    print(orjson.dumps(app.openapi(), option=orjson.OPT_INDENT_2).decode("utf-8"))


generate_openapi_json(app)
