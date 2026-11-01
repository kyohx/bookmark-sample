from sqlalchemy.orm import Session

TEST_URL = "https://example.com/test"
TEST_TAG_NAME = "test_tag"
TEST_TAGS = ["test_tag1", "test_tag2"]
TEST_PASSWORD = "test_password"
# TEST_PASSWORDを本番既定のbcrypt cost=12で事前生成し、import時の再計算を避ける。
TEST_HASHED_PASSWORD = "$2b$12$sJFxqs2JQk.6zbWbVW.3HeUfRFePtLmlZXLLIK8/sJfG1BO8vUB3."


class SessionForTest(Session):
    """
    テスト用セッション
    """

    def commit(self) -> None:
        # 実際にコミットしないようにする
        self.flush()
        self.expire_all()
