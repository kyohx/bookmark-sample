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
    return int(datetime.now(UTC).timestamp())


def rotate(blacklist: TokenBlacklistService, **overrides) -> bool:
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
        barrier.wait(timeout=10)
        return original_rotate(self, **kwargs)

    monkeypatch.setattr(TokenBlacklistService, "rotate_refresh_token", simultaneous_rotate)

    def refresh():
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
    assert not rotate(blacklist, **{expired: now() - 1})
    assert blacklist.get_current_jti("user", "family") is None
    assert not blacklist.is_jti_denied("old")
    assert blacklist.list_sessions("user") == []


def test_rotation_then_revocation_rejects_new_token(blacklist: TokenBlacklistService) -> None:
    assert rotate(blacklist)
    assert blacklist.revoke_session("user", "family")
    assert not rotate(blacklist, old_jti="new", new_jti="next")
    assert blacklist.get_current_jti("user", "family") == "new"
    assert blacklist.list_sessions("user")[0].revoked
