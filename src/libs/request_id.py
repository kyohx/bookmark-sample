from uuid import uuid4

from starlette.datastructures import MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from .request_context import request_id_context


class RequestIdMiddleware:
    """HTTPリクエストごとのIDをログとレスポンスヘッダーに引き継ぐ。"""

    def __init__(self, app: ASGIApp) -> None:
        """
        リクエストIDを付与するミドルウェアを初期化する。

        Args:
            app: 呼び出しを委譲する内側の ASGI アプリ
        """
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        """
        HTTP リクエストの ID を発行し、ログのコンテキストとレスポンスに引き継ぐ。

        Args:
            scope: 接続またはリクエストの ASGI スコープ
            receive: ASGI メッセージを受信する関数
            send: ASGI メッセージを送信する関数
        """
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        # クライアントの値を流用せず、リクエストごとに新しいIDを発行する。
        request_id = uuid4().hex
        scope.setdefault("state", {})["request_id"] = request_id
        token = request_id_context.set(request_id)

        async def send_with_request_id(message: Message) -> None:
            """HTTP レスポンスの開始メッセージにリクエストIDを付けて送信する。"""
            if message["type"] == "http.response.start":
                MutableHeaders(scope=message)["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_with_request_id)
        except Exception as exc:
            # Uvicornはこのミドルウェアを抜けた後に例外をログ出力する。
            exc.__dict__["_bookmark_request_id"] = request_id
            raise
        finally:
            request_id_context.reset(token)
