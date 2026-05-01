# SQLAlchemy クエリキャッシュデコレータ 詳細設計書

## 1. 概要

SQLAlchemy のクエリ結果を dogpile.cache + zstd 圧縮でキャッシュする汎用デコレータライブラリ。
リポジトリパターン・関数ベース両方で使用可能。

---

## 2. アーキテクチャ

```
┌─────────────────────────────────────────────────────────┐
│                    Application Layer                     │
│  UserRepository.get_by_id()  /  def get_user_by_id()    │
└────────────────────┬────────────────────────────────────┘
                     │ @query_cache(region, ...)
┌────────────────────▼────────────────────────────────────┐
│                  query_cache Decorator                   │
│  1. キャッシュキー生成 (KeyGenerator)                    │
│  2. キャッシュHIT → そのまま返す                         │
│  3. キャッシュMISS → 関数実行                            │
│  4. Session から expunge (SessionResolver)               │
│  5. キャッシュに保存                                     │
└────────────────────┬────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────┐
│                  dogpile.cache Region                    │
│  ZstdRedisBackend / ZstdMemoryBackend                   │
│  serialize: pickle → zstd compress                      │
│  deserialize: zstd decompress → pickle                  │
└─────────────────────────────────────────────────────────┘
```

---

## 3. モジュール構成

```
cache/
├── __init__.py          # 公開API
├── backends.py          # ZstdMemoryBackend / ZstdRedisBackend
├── decorator.py         # query_cache デコレータ本体
├── key_generator.py     # キャッシュキー生成ロジック
├── session_resolver.py  # Session 取得・expunge ロジック
└── region.py            # Region ファクトリ・NullCacheRegion
```

### 公開 API (`__init__.py`)

```python
from cache.decorator import query_cache
from cache.region import create_memory_region, create_redis_region, NullCacheRegion
from cache.backends import ZstdMemoryBackend, ZstdRedisBackend

__all__ = [
    "query_cache",
    "create_memory_region",
    "create_redis_region",
    "NullCacheRegion",
    "ZstdMemoryBackend",
    "ZstdRedisBackend",
]
```

---

## 4. 各コンポーネント詳細設計

### 4.1 `key_generator.py`

#### 責務
- 関数の引数からキャッシュキーを生成する

#### インターフェース

```python
KeyFunc = Callable[..., str]
```

#### クラス / 関数

```python
class KeyGenerator:
    @staticmethod
    def default(func: Callable, args: tuple, kwargs: dict) -> str:
        """
        デフォルトキー生成。
        フォーマット: "{module}.{qualname}:{args_repr}:{kwargs_repr}"
        - args: SessionまたはRepositoryインスタンス(args[0])は除外する
        - 値はreprで文字列化
        """

    @staticmethod
    def from_template(template: str, func: Callable) -> KeyFunc:
        """
        テンプレート文字列からキー生成関数を返す。
        関数シグネチャにバインドしてテンプレートを展開する。
        例: from_template("user:{user_id}", get_by_id) → lambda self, user_id, ...: f"user:{user_id}"
        """
```

#### デフォルトキー生成ルール

| 条件 | 除外対象 |
|---|---|
| args[0] が Session インスタンス | args[0] を除外 |
| args[0] が session_attr を持つオブジェクト | args[0] を除外 |
| それ以外 | args をすべて使用 |

---

### 4.2 `session_resolver.py`

#### 責務
- 関数引数から SQLAlchemy Session を取得する
- クエリ結果を Session から expunge する

#### インターフェース

```python
class SessionResolver:
    def __init__(self, session_attr: str = "session"):
        ...

    def resolve(self, args: tuple, kwargs: dict) -> Session | None:
        """
        以下の優先順位で Session を探す:
        1. args の中に Session インスタンスが直接あれば使用
        2. args[0] (self) が session_attr 属性を持つなら使用
        3. kwargs の中に Session インスタンスがあれば使用
        4. 見つからなければ None を返す（expunge スキップ）
        """

    def expunge(self, session: Session, result: Any) -> None:
        """
        result の型に応じて expunge する。
        - list / tuple: 各要素に対して expunge
        - DeclarativeBase サブクラス: 単体で expunge
        - それ以外 (int, str, dict 等): スキップ
        """
```

#### expunge 対象判定

```
result
  ├── list / tuple
  │     └── 各要素が DeclarativeBase サブクラス → expunge
  ├── DeclarativeBase サブクラス → expunge
  └── その他 (プリミティブ, dict, dataclass 等) → スキップ
```

---

### 4.3 `decorator.py`

#### 責務
- キャッシュの HIT/MISS 制御
- KeyGenerator・SessionResolver の呼び出し

#### シグネチャ

```python
def query_cache(
    region: CacheRegion | None = None,
    key_func: KeyFunc | str | None = None,
    expiration_time: int | None = None,
    session_attr: str = "session",
    region_attr: str = "region",
    unless: Callable[..., bool] | None = None,
) -> Callable:
    ...
```

#### パラメータ仕様

| パラメータ | 型 | デフォルト | 説明 |
|---|---|---|---|
| `region` | `CacheRegion \| None` | `None` | dogpile.cache のリージョン。`None` の場合は `self.<region_attr>` を参照 |
| `key_func` | `Callable \| str \| None` | `None` | `None`=自動生成、`str`=テンプレート、`Callable`=カスタム関数 |
| `expiration_time` | `int \| None` | `None` | TTL秒。`None`の場合はregionのデフォルト値を使用 |
| `session_attr` | `str` | `"session"` | self からSessionを取得する属性名 |
| `region_attr` | `str` | `"region"` | `region=None` 時に self から Region を取得する属性名 |
| `unless` | `Callable \| None` | `None` | `True`を返すとキャッシュをスキップ。例: デバッグ時の無効化 |

#### Region の解決順序

1. デコレータ引数 `region` が指定されていればそれを使用
2. `None` の場合は `args[0].<region_attr>` (= `self.region`) を参照
3. どちらも取得できなければ `AttributeError` を raise

#### 処理フロー

```
wrapper(*args, **kwargs) が呼ばれる
    │
    ├─ region を解決 (デコレータ引数 or self.<region_attr>)
    │
    ├─ unless(*args, **kwargs) == True → キャッシュスキップ、関数をそのまま実行
    │
    ├─ cache_key = KeyGenerator.generate(key_func, func, args, kwargs)
    │
    ├─ cached = region.get(cache_key)
    │   ├─ HIT → return cached
    │   └─ MISS ↓
    │
    ├─ result = func(*args, **kwargs)
    │
    ├─ session = SessionResolver.resolve(args, kwargs)
    │   └─ session が None でなければ SessionResolver.expunge(session, result)
    │
    ├─ region.set(cache_key, result, expiration_time=...)
    │
    └─ return result
```

---

### 4.4 `backends.py`

#### ZstdMemoryBackend

| 項目 | 内容 |
|---|---|
| 用途 | 開発・テスト環境 |
| ベース | `dogpile.cache.backends.memory.MemoryBackend` |
| シリアライズ | `pickle.dumps` → `zstd.compress` |
| デシリアライズ | `zstd.decompress` → `pickle.loads` |

#### ZstdRedisBackend

| 項目 | 内容 |
|---|---|
| 用途 | 本番環境 |
| ベース | `dogpile.cache.api.CacheBackend` |
| シリアライズ | `pickle.dumps` → `zstd.compress` |
| デシリアライズ | `zstd.decompress` → `pickle.loads` |
| TTL管理 | `SETEX` コマンド |
| パイプライン | `get_multi` / `set_multi` は Redis Pipeline を使用 |

#### バックエンド共通 arguments

| キー | 型 | デフォルト | 説明 |
|---|---|---|---|
| `zstd_level` | `int` | `3` | zstd 圧縮レベル (1〜22) |

#### ZstdRedisBackend 固有 arguments

| キー | 型 | デフォルト | 説明 |
|---|---|---|---|
| `host` | `str` | `"localhost"` | Redis ホスト |
| `port` | `int` | `6379` | Redis ポート |
| `db` | `int` | `0` | Redis DB 番号 |
| `expiration_time` | `int` | `3600` | デフォルト TTL 秒 |

---

### 4.5 `region.py`

#### 責務
- Region の生成を簡素化するファクトリ関数を提供
- キャッシュを完全に無効化する `NullCacheRegion` を提供

#### ファクトリ関数

```python
def create_memory_region(
    expiration_time: int = 300,
    zstd_level: int = 3,
) -> CacheRegion: ...

def create_redis_region(
    host: str = "localhost",
    port: int = 6379,
    db: int = 0,
    expiration_time: int = 3600,
    zstd_level: int = 3,
) -> CacheRegion: ...
```

#### NullCacheRegion

`CacheRegion` と同じインターフェースを持つが、何もしないダミー実装（Null Object パターン）。

| メソッド | 挙動 |
|---|---|
| `get(key)` | 常に `NO_VALUE` を返す（常にキャッシュMISSとして振る舞う） |
| `set(key, value, ...)` | no-op |
| `delete(key)` | no-op |

```python
class NullCacheRegion:
    """キャッシュを完全に無効化するダミーRegion。"""
    def get(self, key: str) -> Any:
        return NO_VALUE

    def set(self, key: str, value: Any, expiration_time: int | None = None) -> None:
        pass

    def delete(self, key: str) -> None:
        pass
```

`@query_cache` デコレータ側の変更は不要。Region を差し替えるだけでキャッシュをOFFにできる。

```python
# 本番: Redisキャッシュ有効
region = create_redis_region(host="redis-host")

# 開発・テスト: キャッシュ無効
region = NullCacheRegion()
```

---

## 5. 使用例

### 5.1 FastAPI + DI パターン（推奨）

`region` をコンストラクタで注入し、FastAPI の `Depends` で Repository を提供する。

```python
# dependencies.py
from cache import create_redis_region, NullCacheRegion
from config import settings

def get_cache_region() -> CacheRegion:
    if settings.CACHE_ENABLED:
        return create_redis_region(host=settings.REDIS_HOST)
    return NullCacheRegion()

def get_user_repository(
    session: Session = Depends(get_db),
    region: CacheRegion = Depends(get_cache_region),
) -> UserRepository:
    return UserRepository(session=session, region=region)
```

```python
# repository.py
from cache import query_cache

class UserRepository:
    def __init__(self, session: Session, region: CacheRegion):
        self.session = session
        self.region = region  # デコレータが self.region を参照

    @query_cache(key_func="user:{user_id}")
    def get_by_id(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)

    @query_cache(key_func=lambda self, name: f"users:name:{name}")
    def get_by_name(self, name: str) -> list[User]:
        return self.session.query(User).filter(User.name == name).all()

    @query_cache(expiration_time=60)
    def get_active_users(self) -> list[User]:
        return self.session.query(User).filter(User.is_active == True).all()
```

```python
# router.py
@router.get("/users/{user_id}")
def get_user(
    user_id: int,
    repo: UserRepository = Depends(get_user_repository),
):
    return repo.get_by_id(user_id)
```

### 5.2 region_attr のカスタマイズ

`region` 以外の属性名を使う場合は `region_attr` で指定する。

```python
class UserRepository:
    def __init__(self, session: Session, cache: CacheRegion):
        self.session = session
        self.cache = cache

    @query_cache(key_func="user:{user_id}", region_attr="cache")
    def get_by_id(self, user_id: int) -> User | None:
        return self.session.get(User, user_id)
```

### 5.3 関数ベース (region を直接渡す場合)

```python
region = create_redis_region(host="localhost")

# Session が args[0] として渡される場合も SessionResolver が自動検出
@query_cache(region=region, key_func=lambda session, user_id: f"user:{user_id}")
def get_user_by_id(session: Session, user_id: int) -> User | None:
    return session.get(User, user_id)
```

### 5.4 session_attr のカスタマイズ

```python
class OrderRepository:
    def __init__(self, db: Session, region: CacheRegion):
        self.db = db  # 属性名が "session" でない
        self.region = region

    @query_cache(key_func="order:{order_id}", session_attr="db")
    def get_by_id(self, order_id: int) -> Order | None:
        return self.db.get(Order, order_id)
```

### 5.5 unless による条件付きスキップ

```python
import os

@query_cache(unless=lambda *a, **kw: os.getenv("DISABLE_CACHE") == "1")
def get_by_id(self, user_id: int) -> User | None:
    return self.session.get(User, user_id)
```

---

## 6. キャッシュ削除

デコレータはキャッシュ削除を自動では行わない。
削除は呼び出し元が明示的に行う。

```python
# SQLAlchemy イベントで自動削除
from sqlalchemy import event

@event.listens_for(Session, "after_flush")
def after_flush(session, flush_context):
    for obj in session.dirty | session.deleted:
        if isinstance(obj, User):
            region.delete(f"user:{obj.id}")
```

---

## 7. エラーハンドリング方針

| ケース | 挙動 |
|---|---|
| Redisへの接続失敗 | キャッシュをスキップし、クエリを実行して結果を返す (フォールスルー) |
| シリアライズ失敗 | 例外をそのまま raise |
| expunge 失敗 (既にdetached等) | `InvalidRequestError` を握りつぶしてログ出力し処理継続 |
| キャッシュキー衝突 | 呼び出し側の責任。テンプレートや key_func で一意性を担保する |

---

## 8. 非機能要件

| 項目 | 方針 |
|---|---|
| スレッドセーフ | dogpile.cache の dogpile lock に依存 |
| 型安全 | `Callable` の型ヒントを付与。mypy 対応 |
| ログ | `logging` モジュールを使用。キャッシュHIT/MISS を DEBUG レベルで出力 |
| テスト | `ZstdMemoryBackend` を使って単体テスト可能 |
