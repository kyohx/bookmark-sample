from sqlalchemy import select
from sqlalchemy.orm import Session

from src.dao.models.bookmark import BookmarkDao
from src.dao.models.bookmark_tag import BookmarkTagDao
from src.dao.models.tag import TagDao
from src.dao.models.user import UserDao
from src.libs.enum import AuthorityEnum
from src.libs.util import get_hashed_id

_UNIT_TEST_HASHED_PASSWORD = "hashed-password"


class UnitDataFactory:
    """
    unit テスト用データ作成クラス
    """

    def __init__(self, session: Session):
        self.session = session

    def create_user(
        self,
        name: str,
        disabled: bool = False,
        authority: AuthorityEnum = AuthorityEnum.READWRITE,
    ) -> UserDao:
        user = UserDao(
            name=name,
            hashed_password=_UNIT_TEST_HASHED_PASSWORD,
            disabled=disabled,
            authority=authority.value,
        )
        self.session.add(user)
        self.session.flush()
        return user

    def create_bookmark(self, url: str, memo: str, tag_names: list[str]) -> BookmarkDao:
        bookmark = BookmarkDao(url=url, memo=memo, hashed_id=get_hashed_id(url))
        self.session.add(bookmark)
        self.session.flush()

        for tag_name in tag_names:
            tag = self._get_or_create_tag(tag_name)
            self.session.add(BookmarkTagDao(bookmark_id=bookmark.id, tag_id=tag.id))
        self.session.flush()
        return bookmark

    def _get_or_create_tag(self, name: str) -> TagDao:
        # タグは bookmark 間で共有されるので、同名タグは再利用する。
        tag = self.session.execute(select(TagDao).where(TagDao.name == name)).scalar_one_or_none()
        if tag is not None:
            return tag

        tag = TagDao(name=name)
        self.session.add(tag)
        self.session.flush()
        return tag
