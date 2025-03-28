# 制約定義
from typing import Annotated

from fastapi import Path, Query
from pydantic import AfterValidator, Field, HttpUrl, StringConstraints, UrlConstraints


def is_unique(values):
    if len(values) != len(set(values)):
        raise ValueError("values must be unique")
    return values


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
PATH_HASHED_ID = Annotated[str, Path(min_length=64, max_length=64, pattern="[0-9a-f]+")]
QUERY_TAGS = Annotated[
    Annotated[
        list[Annotated[str, StringConstraints(min_length=1, max_length=100)]] | None, Query()
    ],
    AfterValidator(is_unique),
]
