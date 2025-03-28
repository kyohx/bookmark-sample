import json

from fastapi import FastAPI

from .main import app


def generate_openapi_json(app: FastAPI):
    # OpenAPIファイルを生成・保存
    with open("openapi.json", "w") as f:
        json.dump(app.openapi(), f, indent=2, ensure_ascii=False)


generate_openapi_json(app)
