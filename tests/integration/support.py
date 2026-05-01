from sqlalchemy.orm import Session

from src.services.authorize import AuthorizeService

TEST_URL = "https://example.com/test"
TEST_TAG_NAME = "test_tag"
TEST_TAGS = ["test_tag1", "test_tag2"]
TEST_PASSWORD = "test_password"
TEST_HASHED_PASSWORD = AuthorizeService.get_hashed_password(TEST_PASSWORD)


class SessionForTest(Session):
    """
    テスト用セッション
    """

    def commit(self) -> None:
        # 実際にコミットしないようにする
        self.flush()
        self.expire_all()
