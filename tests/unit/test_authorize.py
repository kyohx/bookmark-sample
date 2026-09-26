from datetime import UTC, datetime
from unittest.mock import Mock

import jwt
import pytest

from src.services.authorize import AccessTokenPayload, AuthorizeService, RefreshTokenPayload


@pytest.fixture
def service() -> AuthorizeService:
    return AuthorizeService(session=Mock())


def encode(service: AuthorizeService, payload: dict) -> str:
    return jwt.encode(payload, service.jwt_secret_key, algorithm=service.ALGORITHM)


def claims(kind: str) -> dict:
    payload = {
        "sub": "test_user",
        "exp": int(datetime.now(UTC).timestamp()) + 3600,
        "type": kind,
    }
    if kind == "refresh":
        payload.update(jti="test-jti", fam="test-family")
    return payload


@pytest.mark.parametrize("kind", ["access", "refresh"])
def test_valid_token(service: AuthorizeService, kind: str) -> None:
    """正しい署名とクレームを持つ JWT は型付きモデルになる。"""
    model = AccessTokenPayload if kind == "access" else RefreshTokenPayload
    payload = claims(kind)
    decoded = service._decode_token(encode(service, payload), model)
    assert isinstance(decoded, model)
    assert decoded.model_dump() == payload


@pytest.mark.parametrize(
    "kind,field,value",
    [
        (kind, field, value)
        for kind, fields in (
            ("access", ("sub", "exp", "type")),
            ("refresh", ("sub", "exp", "type", "jti", "fam")),
        )
        for field in fields
        for value in (None, "", [], {}, True, 1.5, "9999999999", 9999999999.5)
        if not (field in {"sub", "jti", "fam"} and value == "9999999999")
    ],
)
def test_invalid_claim(service: AuthorizeService, kind: str, field: str, value: object) -> None:
    """不正な型は、DB・Redis に到達する前に認証エラーになる。"""
    payload = claims(kind)
    payload[field] = value
    service.get_user = Mock()
    service.blacklist_service = Mock()
    with pytest.raises(AuthorizeService.Error, match="Could not validate credentials"):
        if kind == "access":
            service.get_current_user_from_token(encode(service, payload))
        else:
            service.refresh(encode(service, payload))
    service.get_user.assert_not_called()
    assert service.blacklist_service.mock_calls == []


@pytest.mark.parametrize(
    "kind,field",
    [
        (kind, field)
        for kind, fields in (
            ("access", ("sub", "exp", "type")),
            ("refresh", ("sub", "exp", "type", "jti", "fam")),
        )
        for field in fields
    ],
)
def test_missing_claim(service: AuthorizeService, kind: str, field: str) -> None:
    """必須クレームの欠落を拒否する。"""
    payload = claims(kind)
    del payload[field]
    model = AccessTokenPayload if kind == "access" else RefreshTokenPayload
    with pytest.raises(AuthorizeService.Error):
        service._decode_token(encode(service, payload), model)


@pytest.mark.parametrize("kind", ["access", "refresh"])
@pytest.mark.parametrize("invalid", ["wrong_type", "expired", "signature", "malformed"])
def test_invalid_token(service: AuthorizeService, kind: str, invalid: str) -> None:
    """種別不一致・期限切れ・署名不正・壊れた JWT を拒否する。"""
    payload = claims(kind)
    model = AccessTokenPayload if kind == "access" else RefreshTokenPayload
    if invalid == "wrong_type":
        payload["type"] = "refresh" if kind == "access" else "access"
    elif invalid == "expired":
        payload["exp"] = 1
    token = encode(service, payload)
    if invalid == "signature":
        token = jwt.encode(payload, "invalid-key-for-signature-test-12345", algorithm="HS256")
    elif invalid == "malformed":
        token = "invalid"
    with pytest.raises(AuthorizeService.Error):
        service._decode_token(token, model)
