from enum import IntEnum


class AuthorityEnum(IntEnum):
    """
    権限
    [権限なし: 0]
    [読み取り可: 1]
    [読み書き可: 2]
    [管理者権限: 9]
    """

    NONE = 0
    READ = 1
    READWRITE = 2
    ADMIN = 9

    def __str__(self) -> str:
        return self.name.lower()
