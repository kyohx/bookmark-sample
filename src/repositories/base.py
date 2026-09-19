from collections.abc import Mapping, Sequence
from typing import TypeVar

from dogpile.cache.region import CacheRegion
from sqlalchemy.orm.session import Session

from ..libs.cache import NullCacheRegion, get_query_cache_region
from ..libs.cache.invalidation import (
    install_session_cache_invalidation_listeners,
    new_cache_version,
    schedule_cache_key_deletes,
    schedule_cache_version_bumps,
)
from ..libs.page import Page

install_session_cache_invalidation_listeners()

TValue = TypeVar("TValue")


class RepositoryError(Exception):
    pass


class BaseRepository:
    """
    レポジトリベースクラス
    外部データ(DB等)に対し操作する
    """

    class Error(RepositoryError):
        """
        レポジトリエラー
        """

        pass

    class NotFoundError(RepositoryError):
        """
        データが見つからない
        """

        pass

    def __init__(
        self,
        session: Session,
        page: Page | None = None,
        region: CacheRegion | NullCacheRegion | None = None,
    ) -> None:
        """
        初期化処理

        Args:
            session: データベースセッション
            page: ページ情報
        """
        self.session = session
        "セッション"
        self.page = page
        "ページ情報"
        self.region = region if region is not None else get_query_cache_region()
        "クエリキャッシュリージョン"

    def _page_cache_fragment(self) -> str:
        """
        現在のページ条件をキャッシュキー向けの文字列に変換する。

        Returns:
            ページ条件を表す文字列
        """
        if self.page is None:
            return "page:none:size:none"
        return f"page:{self.page.number}:size:{self.page.size}"

    def _cache_version_key(self, namespace: str) -> str:
        """
        指定 namespace のキャッシュバージョン管理キーを返す。

        Args:
            namespace: キャッシュの論理グループ名

        Returns:
            バージョン管理キー
        """
        return f"{self.__class__.__module__}.{self.__class__.__qualname__}:version:{namespace}"

    def _get_cache_version(self, namespace: str) -> str:
        """
        指定 namespace の現在バージョンを取得する。

        Args:
            namespace: キャッシュの論理グループ名

        Returns:
            現在のバージョン文字列
        """
        version_key = self._cache_version_key(namespace)
        # 初回生成も複数リクエストで競合し得るため、get+set ではなく region 側の排他に寄せる。
        version = self.region.get_or_create(version_key, self._new_cache_version)
        return str(version)

    def _bump_cache_versions(self, *namespaces: str) -> None:
        """
        指定 namespace 群のキャッシュバージョンを進める。

        Args:
            namespaces: 更新対象の namespace 一覧
        """
        schedule_cache_version_bumps(
            self.session,
            self.region,
            *(self._cache_version_key(namespace) for namespace in namespaces),
        )

    def _delete_cache_keys(self, *keys: str) -> None:
        """
        指定されたキャッシュキー群を削除する。

        Args:
            keys: 削除対象のキャッシュキー一覧
        """
        schedule_cache_key_deletes(self.session, self.region, *keys)

    def _invalidate_detail_and_list_caches(
        self,
        *,
        detail_keys: Sequence[str],
        list_namespaces: Sequence[str],
    ) -> None:
        """
        詳細キャッシュ削除と一覧キャッシュ version 更新をまとめて行う。

        Args:
            detail_keys: 削除対象の詳細キャッシュキー一覧
            list_namespaces: 更新対象の一覧 namespace 一覧
        """
        self._delete_cache_keys(*detail_keys)
        self._bump_cache_versions(*list_namespaces)

    def _require_found(self, value: TValue | None) -> TValue:
        """
        値の存在を保証し、未存在なら NotFoundError を送出する。

        Args:
            value: 存在を必須とする値

        Returns:
            存在が確認できた値

        Raises:
            NotFoundError: 値が None の場合
        """
        if value is None:
            raise self.NotFoundError("Not found specified data.")
        return value

    @staticmethod
    def _assign_attributes(target: object, values: Mapping[str, object]) -> None:
        """
        指定された値群をオブジェクトへ代入する。

        Args:
            target: 代入先オブジェクト
            values: 属性名と値の対応
        """
        for key, value in values.items():
            setattr(target, key, value)

    @staticmethod
    def _new_cache_version() -> str:
        """
        キャッシュバージョン用の一意なトークンを生成する。

        Returns:
            新しいバージョン文字列
        """
        return new_cache_version()
