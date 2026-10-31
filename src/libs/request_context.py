from contextvars import ContextVar

# AnyIOが同期エンドポイントを実行するワーカースレッドにも引き継がれる。
request_id_context: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    """現在処理中のHTTPリクエストID。リクエスト外ではNone。"""
    return request_id_context.get()


def get_exception_request_id(exc: BaseException | None) -> str | None:
    """コンテキスト解放後にサーバーがログ出力する例外のIDを取得する。"""
    return getattr(exc, "_bookmark_request_id", None)
