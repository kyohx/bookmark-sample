from pydantic import BaseModel, ConfigDict

from ..libs.version import APP_VERSION


class ResponseForGetVersion(BaseModel):
    version: str

    model_config = ConfigDict(json_schema_extra={"examples": [{"version": APP_VERSION}]})
