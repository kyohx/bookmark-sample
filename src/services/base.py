from ..libs.config import get_config
from ..entities.user import UserEntity


class ServiceError(Exception):
    pass


class ServiceBase:
    """
    サービス基底クラス
    """

    config = get_config()
