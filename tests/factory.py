from sqlalchemy.orm import Session

from src.dao.models.bookmark import BookmarkDao
from src.dao.models.bookmark_tag import BookmarkTagDao
from src.dao.models.tag import TagDao
from src.dao.models.user import UserDao
from src.libs.enum import AuthorityEnum
from src.libs.util import get_hashed_id

from .conftest import TEST_HASHED_PASSWORD


class DataFactory:
    """
    データ作成クラス
    """

    def __init__(self, session: Session):
        self.session = session

    def create_bookmark(self, url: str, memo: str, tagnames: list[str]) -> BookmarkDao:
        bookmark = BookmarkDao(
            url=url,
            memo=memo,
            hashed_id=get_hashed_id(url),
        )
        self.session.add(bookmark)
        self.session.flush()

        already_exsist_tag_names = [
            tag for tag in self.session.query(TagDao).filter(TagDao.name.in_(tagnames)).all()
        ]
        if already_exsist_tag_names:
            tags = already_exsist_tag_names
        else:
            tags = [TagDao(name=tag) for tag in tagnames]
            self.session.add_all(tags)
            self.session.flush()

        for tag in tags:
            self.session.add(BookmarkTagDao(bookmark_id=bookmark.id, tag_id=tag.id))

        self.session.flush()
        return bookmark

    def create_user(
        self,
        name: str,
        disabled: bool = False,
        authority: AuthorityEnum = AuthorityEnum.READWRITE,
    ) -> UserDao:
        user = UserDao(
            name=name,
            hashed_password=TEST_HASHED_PASSWORD,
            disabled=disabled,
            authority=authority.value,
        )
        self.session.add(user)
        self.session.flush()
        return user
