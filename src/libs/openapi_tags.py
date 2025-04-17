# OpenAPI 用タグ定義
from enum import Enum


class TagNameEnum(Enum):
    """
    OpenAPI用タグ名
    """

    AUTH = "auth"
    BOOKMARK = "bookmark"
    USER = "user"
    VERSION = "version"


OPENAPI_TAGS = [
    {
        "name": TagNameEnum.AUTH.value,
        "description": "Authentication operations",
    },
    {
        "name": TagNameEnum.BOOKMARK.value,
        "description": "Bookmark operations",
    },
    {
        "name": TagNameEnum.USER.value,
        "description": "User operations",
    },
    {
        "name": TagNameEnum.VERSION.value,
        "description": "API version",
    },
]
