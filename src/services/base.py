from ..libs.config import get_config


class ServiceError(Exception):
    pass


class ServiceBase:
    """
    サービス基底クラス
    """

    config = get_config()
