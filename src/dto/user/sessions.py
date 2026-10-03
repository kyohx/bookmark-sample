from typing import Self

from pydantic import BaseModel

from ...entities.session import RefreshSession
from ...libs.constraints import FIELD_STRING_DATETIME
from ...libs.util import datetime_to_str


class SessionDetail(BaseModel):
    id: str
    created_at: FIELD_STRING_DATETIME
    last_used_at: FIELD_STRING_DATETIME
    expires_at: FIELD_STRING_DATETIME
    revoked: bool
    user_agent: str | None

    @classmethod
    def from_entity(cls, session: RefreshSession) -> Self:
        return cls(
            id=session.id,
            created_at=datetime_to_str(session.created_at),
            last_used_at=datetime_to_str(session.last_used_at),
            expires_at=datetime_to_str(session.expires_at),
            revoked=session.revoked,
            user_agent=session.user_agent,
        )


class ResponseForGetSessions(BaseModel):
    sessions: list[SessionDetail]

    @classmethod
    def from_entities(cls, sessions: list[RefreshSession]) -> Self:
        return cls(sessions=[SessionDetail.from_entity(session) for session in sessions])
