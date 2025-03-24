def test_update_bookmark(client: TestClient, db_session: Session):
    """
    ブックマーク更新のテスト
    """

    # 事前条件: データベースにブックマークが存在することを確認
    initial_bookmark = BookmarkDao(
        url="https://example.com", title="Example", hashed_id=get_hashed_id("https://example.com")
    )
    db_session.add(initial_bookmark)
    db_session.commit()

    tag1 = TagDao(name="tag1")
    tag2 = TagDao(name="tag2")
    db_session.add_all([tag1, tag2])
    db_session.commit()

    bookmark_tag1 = BookmarkTagDao(bookmark_id=initial_bookmark.id, tag_id=tag1.id)
    bookmark_tag2 = BookmarkTagDao(bookmark_id=initial_bookmark.id, tag_id=tag2.id)
    db_session.add_all([bookmark_tag1, bookmark_tag2])
    db_session.commit()

    assert len(db_session.execute(select(BookmarkDao)).scalars().all()) == 1
    assert len(db_session.execute(select(TagDao)).scalars().all()) == 2
    assert len(db_session.execute(select(BookmarkTagDao)).scalars().all()) == 2

    # リクエストボディの作成
    request_body = RequestForUpdateBookmark(
        url="https://updated.com", title="Updated", tags=["tag3", "tag4"]
    )

    # リクエストの送信
    response = client.patch(
        f"/bookmarks/{initial_bookmark.hashed_id}", json=request_body.model_dump()
    )

    # レスポンスの検証
    assert response.status_code == 200
    response_body = response.json()
    assert "updated_bookmark" in response_body
    updated_bookmark = response_body["updated_bookmark"]
    assert updated_bookmark["url"] == request_body.url
    assert updated_bookmark["title"] == request_body.title
    assert updated_bookmark["hashed_id"] == initial_bookmark.hashed_id

    # データベースの検証
    bookmarks = db_session.execute(select(BookmarkDao)).scalars().all()
    assert len(bookmarks) == 1
    bookmark = bookmarks[0]
    assert bookmark.url == request_body.url
    assert bookmark.title == request_body.title
    assert bookmark.hashed_id == initial_bookmark.hashed_id

    tags = db_session.execute(select(TagDao)).scalars().all()
    assert len(tags) == 2
    assert set([tag.name for tag in tags]) == set(request_body.tags)

    bookmark_tags = db_session.execute(select(BookmarkTagDao)).scalars().all()
    assert len(bookmark_tags) == 2
    assert set([bookmark_tag.tag_id for bookmark_tag in bookmark_tags]) == set(
        [tag.id for tag in tags]
    )
    assert set([bookmark_tag.bookmark_id for bookmark_tag in bookmark_tags]) == set([bookmark.id])


def test_delete_bookmark(client: TestClient, db_session: Session):
    """
    ブックマーク削除のテスト
    """

    # 事前条件: データベースにブックマークが存在することを確認
    initial_bookmark = BookmarkDao(
        url="https://example.com", title="Example", hashed_id=get_hashed_id("https://example.com")
    )
    db_session.add(initial_bookmark)
    db_session.commit()
    assert len(db_session.execute(select(BookmarkDao)).scalars().all()) == 1

    # リクエストの送信
    response = client.delete(f"/bookmarks/{initial_bookmark.hashed_id}")

    # レスポンスの検証
    assert response.status_code == 200

    # データベースの検証
    assert len(db_session.execute(select(BookmarkDao)).scalars().all()) == 0


def test_get_bookmark(client: TestClient, db_session: Session):
    """
    ブックマーク取得のテスト
    """

    # 事前条件: データベースにブックマークが存在することを確認
    initial_bookmark = BookmarkDao(
        url="https://example.com", title="Example", hashed_id=get_hashed_id("https://example.com")
    )
    db_session.add(initial_bookmark)
    db_session.commit()

    tag1 = TagDao(name="tag1")
    tag2 = TagDao(name="tag2")
    db_session.add_all([tag1, tag2])
    db_session.commit()

    bookmark_tag1 = BookmarkTagDao(bookmark_id=initial_bookmark.id, tag_id=tag1.id)
    bookmark_tag2 = BookmarkTagDao(bookmark_id=initial_bookmark.id, tag_id=tag2.id)
    db_session.add_all([bookmark_tag1, bookmark_tag2])
    db_session.commit()

    assert len(db_session.execute(select(BookmarkDao)).scalars().all()) == 1
    assert len(db_session.execute(select(TagDao)).scalars().all()) == 2
    assert len(db_session.execute(select(BookmarkTagDao)).scalars().all()) == 2

    # リクエストの送信
    response = client.get(f"/bookmarks/{initial_bookmark.hashed_id}")

    # レスポンスの検証
    assert response.status_code == 200
    response_body = response.json()
    assert "bookmark" in response_body
    bookmark = response_body["bookmark"]
    assert bookmark["url"] == initial_bookmark.url
    assert bookmark["title"] == initial_bookmark.title
    assert bookmark["hashed_id"] == initial_bookmark.hashed_id
    assert set(bookmark["tags"]) == set(["tag1", "tag2"])


def test_get_bookmarks(client: TestClient, db_session: Session):
    """
    ブックマークリスト取得のテスト
    """

    # 事前条件: データベースにブックマークが複数存在することを確認
    bookmark1 = BookmarkDao(
        url="https://example.com/1",
        title="Example1",
        hashed_id=get_hashed_id("https://example.com/1"),
    )
    bookmark2 = BookmarkDao(
        url="https://example.com/2",
        title="Example2",
        hashed_id=get_hashed_id("https://example.com/2"),
    )
    db_session.add_all([bookmark1, bookmark2])
    db_session.commit()

    tag1 = TagDao(name="tag1")
    tag2 = TagDao(name="tag2")
    tag3 = TagDao(name="tag3")
    db_session.add_all([tag1, tag2, tag3])
    db_session.commit()

    bookmark_tag1 = BookmarkTagDao(bookmark_id=bookmark1.id, tag_id=tag1.id)
    bookmark_tag2 = BookmarkTagDao(bookmark_id=bookmark1.id, tag_id=tag2.id)
    bookmark_tag3 = BookmarkTagDao(bookmark_id=bookmark2.id, tag_id=tag2.id)
    bookmark_tag4 = BookmarkTagDao(bookmark_id=bookmark2.id, tag_id=tag3.id)
    db_session.add_all([bookmark_tag1, bookmark_tag2, bookmark_tag3, bookmark_tag4])
    db_session.commit()

    assert len(db_session.execute(select(BookmarkDao)).scalars().all()) == 2
    assert len(db_session.execute(select(TagDao)).scalars().all()) == 3
    assert len(db_session.execute(select(BookmarkTagDao)).scalars().all()) == 4

    # リクエストの送信 (タグなし)
    response = client.get("/bookmarks")

    # レスポンスの検証
    assert response.status_code == 200
    response_body = response.json()
    assert "bookmarks" in response_body
    bookmarks = response_body["bookmarks"]
    assert len(bookmarks) == 2
    assert {bookmark["url"] for bookmark in bookmarks} == {bookmark1.url, bookmark2.url}

    # リクエストの送信 (タグあり)
    response = client.get("/bookmarks?tag=tag2")

    # レスポンスの検証
    assert response.status_code == 200
    response_body = response.json()
    assert "bookmarks" in response_body
    bookmarks = response_body["bookmarks"]
    assert len(bookmarks) == 2
    assert {bookmark["url"] for bookmark in bookmarks} == {bookmark1.url, bookmark2.url}

    # リクエストの送信 (タグあり)
    response = client.get("/bookmarks?tag=tag1&tag=tag3")

    # レスポンスの検証
    assert response.status_code == 200
    response_body = response.json()
    assert "bookmarks" in response_body
    bookmarks = response_body["bookmarks"]
    assert len(bookmarks) == 2
    assert {bookmark["url"] for bookmark in bookmarks} == {bookmark1.url, bookmark2.url}

    # リクエストの送信 (タグあり)
    response = client.get("/bookmarks?tag=tag1")

    # レスポンスの検証
    assert response.status_code == 200
    response_body = response.json()
    assert "bookmarks" in response_body
    bookmarks = response_body["bookmarks"]
    assert len(bookmarks) == 1
    assert {bookmark["url"] for bookmark in bookmarks} == {bookmark1.url}

    # リクエストの送信 (タグあり)
    response = client.get("/bookmarks?tag=tag3")

    # レスポンスの検証
    assert response.status_code == 200
    response_body = response.json()
    assert "bookmarks" in response_body
    bookmarks = response_body["bookmarks"]
    assert len(bookmarks) == 1
    assert {bookmark["url"] for bookmark in bookmarks} == {bookmark2.url}
