import inspect
from collections.abc import Callable

from sqlalchemy.orm import Session

type KeyFunc = Callable[..., str]


class KeyGenerator:
    @staticmethod
    def default(
        func: Callable[..., object],
        args: tuple[object, ...],
        kwargs: dict[str, object],
        session_attr: str = "session",
    ) -> str:
        """
        デフォルトルールでキャッシュキーを生成する。

        Args:
            func: 対象関数
            args: 位置引数
            kwargs: キーワード引数
            session_attr: Session を保持する属性名

        Returns:
            生成したキャッシュキー
        """
        filtered_args = KeyGenerator._filter_args(args, session_attr=session_attr)
        sorted_kwargs = dict(sorted(kwargs.items()))
        return f"{func.__module__}.{func.__qualname__}:{filtered_args!r}:{sorted_kwargs!r}"

    @staticmethod
    def from_template(template: str, func: Callable[..., object]) -> KeyFunc:
        """
        テンプレート文字列からキャッシュキー生成関数を生成する。

        Args:
            template: キーテンプレート
            func: 引数名解決に使う対象関数

        Returns:
            テンプレートベースのキー生成関数
        """

        def key_func(*args: object, **kwargs: object) -> str:
            return KeyGenerator._render_template(template, func, args, kwargs)

        return key_func

    @staticmethod
    def generate(
        key_func: KeyFunc | str | None,
        func: Callable[..., object],
        args: tuple[object, ...],
        kwargs: dict[str, object],
        session_attr: str = "session",
    ) -> str:
        """
        指定ルールに従ってキャッシュキーを生成する。

        Args:
            key_func: キー生成関数またはテンプレート
            func: 対象関数
            args: 位置引数
            kwargs: キーワード引数
            session_attr: Session を保持する属性名

        Returns:
            生成したキャッシュキー
        """
        if key_func is None:
            return KeyGenerator.default(func, args, kwargs, session_attr=session_attr)
        if isinstance(key_func, str):
            return KeyGenerator.from_template(key_func, func)(*args, **kwargs)
        return key_func(*args, **kwargs)

    @staticmethod
    def _filter_args(args: tuple[object, ...], session_attr: str) -> tuple[object, ...]:
        """
        キャッシュキー生成に不要な先頭引数を除外する。

        Args:
            args: 位置引数
            session_attr: Session を保持する属性名

        Returns:
            フィルタ後の位置引数
        """
        if args and KeyGenerator._exclude_first_arg(args[0], session_attr=session_attr):
            return args[1:]
        return args

    @staticmethod
    def _exclude_first_arg(value: object, session_attr: str) -> bool:
        """
        先頭引数をキー生成から除外すべきか判定する。

        Args:
            value: 判定対象の値
            session_attr: Session を保持する属性名

        Returns:
            除外対象なら True
        """
        return isinstance(value, Session) or hasattr(value, session_attr)

    @staticmethod
    def _render_template(
        template: str,
        func: Callable[..., object],
        args: tuple[object, ...],
        kwargs: dict[str, object],
    ) -> str:
        """
        関数シグネチャに引数を束縛してテンプレートを展開する。

        Args:
            template: キーテンプレート
            func: 対象関数
            args: 位置引数
            kwargs: キーワード引数

        Returns:
            展開済みキャッシュキー
        """
        bound_arguments = inspect.signature(func).bind_partial(*args, **kwargs)
        bound_arguments.apply_defaults()
        return template.format_map(bound_arguments.arguments)
