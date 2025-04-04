from pydantic import BaseModel


class User(BaseModel):
    name: str
    hashed_password: str
    disabled: bool = False
