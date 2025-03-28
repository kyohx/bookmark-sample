import json

from fastapi import FastAPI

from .main import app


def generate_openapi_json(app: FastAPI) -> None:
    # OpenAPIファイルを生成・標準出力へ出力
    print(json.dumps(app.openapi(), indent=2, ensure_ascii=False))


generate_openapi_json(app)
