from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from threading import Barrier
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from src.entities.user import UserEntity
from src.libs.enum import AuthorityEnum
from src.main import app
from src.services.authorize import AuthorizeService, RefreshTokenPayload
from src.services.token_blacklist import TokenBlacklistService


@pytest.fixture
def blacklist(monkeypatch: pytest.MonkeyPatch) -> Iterator[TokenBlacklistService]:
    """実Redis上のLuaを検証し、テスト専用キーだけを後始末する。"""
    prefix = f"test-rotation:{uuid4().hex}"
    monkeypatch.setattr(TokenBlacklistService, "KEY_PREFIX", prefix)
    service = TokenBlacklistService()
    assert service.redis is not None
    service.redis.ping()
    yield service
    keys = list(service.redis.scan_iter(match=f"{prefix}:*"))
    if keys:
        service.redis.delete(*keys)


def now() -> int:
    """現在の UTC 時刻を秒単位の Unix タイムスタンプで返す。"""
    return int(datetime.now(UTC).timestamp())


def rotate(blacklist: TokenBlacklistService, **overrides) -> bool:
    """テスト用の既定値に上書き指定を反映してトークンを更新する。"""
    params = {
        "user": "user",
        "family": "family",
        "old_jti": "old",
        "new_jti": "new",
        "old_expires_at": now() + 60,
        "new_expires_at": now() + 3600,
    }
    return blacklist.rotate_refresh_token(**(params | overrides))


def test_rotation_updates_tokens_and_session(blacklist: TokenBlacklistService) -> None:
    """更新後のトークン状態、セッション情報、各キーの有効期限を確認する。"""
    timestamp = now()
    blacklist.record_session("user", "family", timestamp + 60, "device")
    blacklist.set_current_jti("user", "family", "old", 60)
    created_at = blacklist.list_sessions("user")[0].created_at

    assert rotate(blacklist, old_expires_at=timestamp + 60, new_expires_at=timestamp + 3600)
    assert blacklist.get_current_jti("user", "family") == "new"
    assert blacklist.is_jti_denied("old")
    session = blacklist.list_sessions("user")[0]
    assert session.user_agent == "device"
    assert session.created_at == created_at
    assert session.last_used_at >= session.created_at
    assert session.expires_at.timestamp() == timestamp + 3600
    assert session.revoked is False
    redis = blacklist.redis
    assert redis is not None
    assert redis.expiretime(blacklist._deny_jti_key("old")) == timestamp + 60
    assert redis.expiretime(blacklist._family_current_key("user", "family")) == timestamp + 3600
    assert redis.expiretime(blacklist._session_key("user", "family")) == timestamp + 3600


@pytest.mark.parametrize("registered", [False, True])
def test_concurrent_refresh_has_only_one_success(
    blacklist: TokenBlacklistService,
    monkeypatch: pytest.MonkeyPatch,
    registered: bool,
) -> None:
    """既存・未登録セッションとも、同じJWTの同時更新は1件だけ成功する。"""
    user = UserEntity(
        name="user", hashed_password="unused", authority=AuthorityEnum.READWRITE, disabled=False
    )
    monkeypatch.setattr(AuthorizeService, "get_user", lambda self, name: user)
    service = AuthorizeService(Mock())
    token = service.create_refresh_token(
        {"sub": "user", "jti": "old", "fam": "family"}, timedelta(seconds=60)
    )
    if registered:
        blacklist.record_session("user", "family", now() + 60, "device")
        blacklist.set_current_jti("user", "family", "old", 60)

    # 両リクエストがJWT/ユーザー検証を終えてから、実Redisの更新に進ませる。
    barrier = Barrier(2)
    original_rotate = TokenBlacklistService.rotate_refresh_token

    def simultaneous_rotate(self, **kwargs):
        """両リクエストがそろってから実際のトークン更新を呼び出す。"""
        barrier.wait(timeout=10)
        return original_rotate(self, **kwargs)

    monkeypatch.setattr(TokenBlacklistService, "rotate_refresh_token", simultaneous_rotate)

    def refresh():
        """共有トークンで更新 API を1回呼び出す。"""
        with TestClient(app) as client:
            return client.post(app.url_path_for("refresh_token"), json={"refresh_token": token})

    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: refresh(), range(2)))
    assert sorted(response.status_code for response in responses) == [200, 401]
    assert blacklist.is_family_denied("user", "family")
    assert blacklist.is_jti_denied("old")
    assert blacklist.list_sessions("user")[0].revoked

    # 再利用検知の既存方針に従い、成功した側の新トークンもfamily単位で拒否する。
    monkeypatch.setattr(TokenBlacklistService, "rotate_refresh_token", original_rotate)
    winner = next(response for response in responses if response.status_code == 200)
    next_token = winner.json()["refresh_token"]
    payload = service._decode_token(next_token, RefreshTokenPayload)
    redis = blacklist.redis
    assert redis is not None
    assert redis.expiretime(blacklist._family_deny_key("user", "family")) >= payload.exp
    with TestClient(app) as client:
        response = client.post(
            app.url_path_for("refresh_token"), json={"refresh_token": next_token}
        )
    assert response.status_code == 401


@pytest.mark.parametrize("denied", ["family", "jti", "revoked"])
def test_denied_rotation_does_not_change_current_token(
    blacklist: TokenBlacklistService, denied: str
) -> None:
    """拒否された更新が現在のトークンとセッションを変更しないことを確認する。"""
    blacklist.record_session("user", "family", now() + 60)
    blacklist.set_current_jti("user", "family", "old", 60)
    if denied == "family":
        blacklist.deny_family("user", "family", 60)
    elif denied == "jti":
        blacklist.deny_jti("old", 60)
    else:
        assert blacklist.revoke_session("user", "family")
    before = blacklist.list_sessions("user")[0]

    assert not rotate(blacklist)
    assert blacklist.get_current_jti("user", "family") == "old"
    assert blacklist.list_sessions("user")[0] == before


@pytest.mark.parametrize("expired", ["old_expires_at", "new_expires_at"])
def test_expired_rotation_does_not_create_state(
    blacklist: TokenBlacklistService, expired: str
) -> None:
    """旧トークンまたは新トークンが期限切れなら、Redis に更新状態を作らない。"""
    assert not rotate(blacklist, **{expired: now() - 1})
    assert blacklist.get_current_jti("user", "family") is None
    assert not blacklist.is_jti_denied("old")
    assert blacklist.list_sessions("user") == []


def test_rotation_then_revocation_rejects_new_token(blacklist: TokenBlacklistService) -> None:
    """セッション失効後は直前に更新したトークンも更新できないことを確認する。"""
    assert rotate(blacklist)
    assert blacklist.revoke_session("user", "family")
    assert not rotate(blacklist, old_jti="new", new_jti="next")
    assert blacklist.get_current_jti("user", "family") == "new"
    assert blacklist.list_sessions("user")[0].revoked


def test_list_sessions_cleans_index_without_removing_concurrent_refresh(
    blacklist: TokenBlacklistService, monkeypatch: pytest.MonkeyPatch
) -> None:
    """欠損や期限切れを整理し、並行する更新で再登録されたセッションを保持する。"""
    redis = blacklist.redis
    assert redis is not None
    timestamp = now()
    blacklist.record_session("user", "older", timestamp + 3600, "older device")
    blacklist.record_session("user", "newer", timestamp + 60, "newer device")
    redis.hset(blacklist._session_key("user", "older"), "created_at", timestamp - 1)
    index_key = blacklist._sessions_key("user")
    redis.zadd(
        index_key, {"expired": timestamp, "missing": timestamp + 60, "family": timestamp + 60}
    )

    original_eval = redis.eval

    def refresh_before_cleanup(*args):
        """欠損インデックスを整理する直前にトークンを更新する。"""
        # ハッシュ取得後、欠損インデックスの削除直前に同じfamilyが再登録される。
        with monkeypatch.context() as refresh_patch:
            refresh_patch.setattr(redis, "eval", original_eval)
            assert rotate(blacklist)
        return original_eval(*args)

    monkeypatch.setattr(redis, "eval", refresh_before_cleanup)
    sessions = blacklist.list_sessions("user")

    assert [(session.id, session.user_agent) for session in sessions] == [
        ("newer", "newer device"),
        ("older", "older device"),
    ]
    assert redis.zscore(index_key, "expired") is None
    assert redis.zscore(index_key, "missing") is None
    assert redis.zscore(index_key, "family") is not None
    assert {session.id for session in blacklist.list_sessions("user")} == {
        "older",
        "newer",
        "family",
    }
