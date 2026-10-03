from pydantic import BaseModel

from ...entities.session import RefreshSession


class ResponseForGetSessions(BaseModel):
    sessions: list[RefreshSession]
