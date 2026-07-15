from pydantic import BaseModel


class UstawieniaKsefOut(BaseModel):
    srodowisko: str
    ma_token: bool


class UstawieniaKsefIn(BaseModel):
    srodowisko: str | None = None
    token: str | None = None


class TestKsefOut(BaseModel):
    powodzenie: bool
    komunikat: str
    srodowisko: str
