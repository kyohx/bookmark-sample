from dataclasses import dataclass, field
from threading import Lock
from typing import Any, Protocol
from uuid import uuid4

from sqlalchemy import event
from sqlalchemy.orm import Session

_PENDING_INVALIDATIONS_SESSION_KEY = "bookmark.pending_cache_invalidations"
_LISTENERS_INSTALLED = False
_LISTENERS_LOCK = Lock()


class _CacheRegionLike(Protocol):
    """
    commit 後無効化で必要な最小限のキャッシュリージョン操作を表す Protocol。
    """

    def set(self, key: str, value: Any) -> None: ...

    def delete(self, key: str) -> None: ...


@dataclass
class _PendingInvalidation:
    """
    1 つのキャッシュリージョンに対して保留中の無効化内容をまとめるデータ。
    """

    region: _CacheRegionLike
    keys: set[str] = field(default_factory=set)
    version_keys: set[str] = field(default_factory=set)


@dataclass
class _PendingTransactionInvalidation:
    """
    1 つのトランザクションに紐づく保留中無効化をリージョン単位で保持するデータ。
    """

    parent_key: int | None
    pending_by_region: dict[int, _PendingInvalidation] = field(default_factory=dict)


def new_cache_version() -> str:
    """
    キャッシュバージョン用の一意なトークンを生成する。

    Returns:
        新しいバージョン文字列
    """
    return uuid4().hex


def schedule_cache_key_deletes(
    session: Session,
    region: _CacheRegionLike,
    *keys: str,
) -> None:
    """
    commit 完了後に実行するキャッシュキー削除を予約する。

    Args:
        session: 対象セッション
        region: 削除対象のキャッシュリージョン
        keys: 削除対象のキャッシュキー一覧
    """
    pending = _get_pending_invalidation(session, region)
    pending.keys.update(keys)


def schedule_cache_version_bumps(
    session: Session,
    region: _CacheRegionLike,
    *version_keys: str,
) -> None:
    """
    commit 完了後に実行するキャッシュバージョン更新を予約する。

    Args:
        session: 対象セッション
        region: 更新対象のキャッシュリージョン
        version_keys: 更新対象のバージョン管理キー一覧
    """
    pending = _get_pending_invalidation(session, region)
    pending.version_keys.update(version_keys)


def has_pending_cache_invalidation(
    session: Session | None,
    region: object | None = None,
) -> bool:
    """
    セッションに保留中のキャッシュ無効化があるか判定する。

    Args:
        session: 判定対象のセッション
        region: 判定対象のキャッシュリージョン。省略時は任意リージョンを対象とする

    Returns:
        保留中の無効化があれば True
    """
    if session is None:
        return False

    pending_by_transaction = _get_pending_invalidations(session)
    if region is None:
        return any(
            pending.keys or pending.version_keys
            for transaction_pending in pending_by_transaction.values()
            for pending in transaction_pending.pending_by_region.values()
        )

    region_key = id(region)
    return any(
        region_key in transaction_pending.pending_by_region
        and bool(
            transaction_pending.pending_by_region[region_key].keys
            or transaction_pending.pending_by_region[region_key].version_keys
        )
        for transaction_pending in pending_by_transaction.values()
    )


def install_session_cache_invalidation_listeners() -> None:
    """
    Session の commit / rollback に連動するキャッシュ無効化リスナーを登録する。
    """
    global _LISTENERS_INSTALLED
    with _LISTENERS_LOCK:
        if _LISTENERS_INSTALLED:
            return

        event.listen(Session, "after_commit", _after_commit)
        event.listen(Session, "after_soft_rollback", _after_soft_rollback)
        _LISTENERS_INSTALLED = True


def _after_commit(session: Session) -> None:
    """
    commit 完了後に予約済みのキャッシュ無効化を実行する。

    Args:
        session: commit 済みセッション
    """
    pending_by_transaction = _pop_pending_invalidations(session)
    pending_by_region = _merge_pending_invalidations(pending_by_transaction)
    for pending in pending_by_region.values():
        region = pending.region
        for key in pending.keys:
            region.delete(key)
        for version_key in pending.version_keys:
            region.set(version_key, new_cache_version())


def _after_soft_rollback(session: Session, previous_transaction: object) -> None:
    """
    rollback 後に予約済みのキャッシュ無効化を破棄する。

    Args:
        session: rollback 済みセッション
        previous_transaction: rollback 対象のトランザクション
    """
    _discard_pending_invalidations(session, previous_transaction)


def _get_pending_invalidations(session: Session) -> dict[int, _PendingTransactionInvalidation]:
    """
    セッションに紐づく保留中キャッシュ無効化一覧を取得する。

    Args:
        session: 対象セッション

    Returns:
        トランザクションごとの保留中無効化情報
    """
    pending = session.info.setdefault(_PENDING_INVALIDATIONS_SESSION_KEY, {})
    return pending


def _get_pending_invalidation(
    session: Session,
    region: _CacheRegionLike,
) -> _PendingInvalidation:
    """
    指定リージョン向けの保留中キャッシュ無効化情報を取得する。

    Args:
        session: 対象セッション
        region: 対象キャッシュリージョン

    Returns:
        対象リージョン向けの保留中無効化情報

    Raises:
        RuntimeError: 保留中無効化を紐づけるトランザクションが見つからない
    """
    current_transaction = _get_current_transaction(session)
    if current_transaction is None:
        raise RuntimeError("cache invalidation must be scheduled within an active transaction")

    pending_by_transaction = _get_pending_invalidations(session)
    transaction_key = id(current_transaction)
    parent = getattr(current_transaction, "parent", None)
    pending_by_region = pending_by_transaction.setdefault(
        transaction_key,
        _PendingTransactionInvalidation(parent_key=id(parent) if parent is not None else None),
    ).pending_by_region
    region_key = id(region)
    if region_key not in pending_by_region:
        pending_by_region[region_key] = _PendingInvalidation(region=region)
    return pending_by_region[region_key]


def _pop_pending_invalidations(session: Session) -> dict[int, _PendingTransactionInvalidation]:
    """
    セッションに紐づく保留中キャッシュ無効化一覧を取り出して削除する。

    Args:
        session: 対象セッション

    Returns:
        取り出した保留中無効化情報
    """
    pending = session.info.pop(_PENDING_INVALIDATIONS_SESSION_KEY, {})
    return pending


def _discard_pending_invalidations(session: Session, transaction: object) -> None:
    """
    指定トランザクション配下に紐づく保留中無効化だけを破棄する。

    Args:
        session: 対象セッション
        transaction: 破棄対象のトランザクション
    """
    pending_by_transaction = _get_pending_invalidations(session)
    target_keys = [id(transaction)]
    while target_keys:
        target_key = target_keys.pop()
        pending_by_transaction.pop(target_key, None)
        target_keys.extend(
            transaction_key
            for transaction_key, pending in tuple(pending_by_transaction.items())
            if pending.parent_key == target_key
        )

    if not pending_by_transaction:
        session.info.pop(_PENDING_INVALIDATIONS_SESSION_KEY, None)


def _merge_pending_invalidations(
    pending_by_transaction: dict[int, _PendingTransactionInvalidation],
) -> dict[int, _PendingInvalidation]:
    """
    トランザクション単位の保留中無効化をリージョン単位へ集約する。

    Args:
        pending_by_transaction: トランザクションごとの保留中無効化情報

    Returns:
        リージョンごとに集約した保留中無効化情報
    """
    pending_by_region: dict[int, _PendingInvalidation] = {}
    for transaction_pending in pending_by_transaction.values():
        for region_key, pending in transaction_pending.pending_by_region.items():
            if region_key not in pending_by_region:
                pending_by_region[region_key] = _PendingInvalidation(region=pending.region)
            pending_by_region[region_key].keys.update(pending.keys)
            pending_by_region[region_key].version_keys.update(pending.version_keys)
    return pending_by_region


def _get_current_transaction(session: Session) -> object | None:
    """
    現在の論理トランザクションを返す。

    Args:
        session: 対象セッション

    Returns:
        nested transaction があればそれを、なければ root transaction を返す
    """
    nested_transaction = session.get_nested_transaction()
    if nested_transaction is not None:
        return nested_transaction
    return session.get_transaction()
