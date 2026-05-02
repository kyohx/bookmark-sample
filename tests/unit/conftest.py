from collections.abc import Callable, Iterator
from contextlib import contextmanager
import sys
from pathlib import Path

import pytest
from dogpile.cache.region import CacheRegion
from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import Session, sessionmaker

from src.libs.cache import create_memory_region

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@contextmanager
def _session_scope(metadata: MetaData) -> Iterator[Session]:
    engine = create_engine("sqlite:///:memory:")
    metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as db_session:
        yield db_session


@pytest.fixture
def sqlite_session_factory() -> Callable[[MetaData], Iterator[Session]]:
    # テストごとに独立した in-memory SQLite を組み立てる。
    return _session_scope


@pytest.fixture
def memory_region() -> CacheRegion:
    # unit テストでは副作用の少ないメモリキャッシュを共通利用する。
    return create_memory_region()
