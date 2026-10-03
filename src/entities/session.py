from datetime import datetime

from pydantic import BaseModel


class RefreshSession(BaseModel):
    """管理者に表示するリフレッシュセッション。"""

    id: str
    created_at: datetime
    last_used_at: datetime
    expires_at: datetime
    revoked: bool
    user_agent: str | None
