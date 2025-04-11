# 制約定義
from typing import Annotated

from fastapi import Path, Query
from pydantic import AfterValidator, Field, HttpUrl, SecretStr, StringConstraints, UrlConstraints


def is_unique(values):
    if len(values) != len(set(values)):
        raise ValueError("values must be unique")
    return values


FIELD_STRING_USERNAME = Annotated[
    str, StringConstraints(min_length=1, max_length=32, pattern="^[a-zA-Z0-9_]+$")
]
FIELD_STRING_PASSWORD = Annotated[SecretStr, Field(min_length=8, max_length=64)]
FIELD_STRING_MAX400 = Annotated[str, StringConstraints(max_length=400)]
FIELD_TAGS = Annotated[
    Annotated[
        list[Annotated[str, StringConstraints(min_length=1, max_length=100)]],
        Field(min_length=1, max_length=10),
    ],
    AfterValidator(is_unique),
]
FIELD_URL = Annotated[HttpUrl, UrlConstraints(max_length=400)]
FIELD_HASHED_ID = Annotated[
    str, StringConstraints(min_length=64, max_length=64, pattern="[0-9a-f]+")
]
FIELD_STRING_DATETIME = Annotated[
    str,
    StringConstraints(
        min_length=19, max_length=19, pattern=r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$"
    ),
]
PATH_HASHED_ID = Annotated[str, Path(min_length=64, max_length=64, pattern="[0-9a-f]+")]
QUERY_TAGS = Annotated[
    Annotated[
        list[Annotated[str, StringConstraints(min_length=1, max_length=100)]] | None, Query()
    ],
    AfterValidator(is_unique),
]
