from sqlalchemy import insert, select
from sqlalchemy.orm import Session

from src.dao.models.bookmark import BookmarkDao
from src.dao.models.bookmark_tag import BookmarkTagDao
from src.dao.models.tag import TagDao
from src.dao.models.user import UserDao
from src.libs.enum import AuthorityEnum
from src.libs.util import get_hashed_id

from .support import TEST_HASHED_PASSWORD


class DataFactory:
    """
    データ作成クラス
    """

    def __init__(self, session: Session):
        self.session = session

    def create_bookmark(self, url: str, memo: str, tagnames: list[str]) -> BookmarkDao:
        return self.create_bookmarks([(url, memo, tagnames)])[0]

    def create_bookmarks(self, entries: list[tuple[str, str, list[str]]]) -> list[BookmarkDao]:
        """タグの取得と関連の登録をまとめ、入力順でブックマークを返す。"""
        if not entries:
            return []

        bookmarks = [
            BookmarkDao(url=url, memo=memo, hashed_id=get_hashed_id(url))
            for url, memo, _ in entries
        ]
        # autoflush=Falseのセッションでも、登録待ちのタグを後続の検索に反映する。
        self.session.add_all(bookmarks)
        self.session.flush()

        tagnames = dict.fromkeys(name for _, _, names in entries for name in names)
        tags = (
            {
                tag.name: tag
                for tag in self.session.scalars(select(TagDao).where(TagDao.name.in_(tagnames)))
            }
            if tagnames
            else {}
        )
        for name in tagnames:
            if name not in tags:
                tags[name] = TagDao(name=name)

        # IDを取得してから関連を一括登録する。タグはこの呼び出し内で共有する。
        self.session.add_all(tags.values())
        self.session.flush()

        associations = [
            {"bookmark_id": bookmark.id, "tag_id": tags[name].id}
            for bookmark, (_, _, names) in zip(bookmarks, entries, strict=True)
            for name in names
        ]
        if associations:
            self.session.execute(insert(BookmarkTagDao), associations)

        return bookmarks

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
