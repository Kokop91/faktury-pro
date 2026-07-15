from pydantic import BaseModel


class UstawieniaKsefOut(BaseModel):
    srodowisko: str
    ma_token: bool
    sprawdzaj_koszty_przy_starcie: bool


class UstawieniaKsefIn(BaseModel):
    srodowisko: str | None = None
    token: str | None = None
    sprawdzaj_koszty_przy_starcie: bool | None = None


class TestKsefOut(BaseModel):
    powodzenie: bool
    komunikat: str
    srodowisko: str


class PobierzKosztyOut(BaseModel):
    powodzenie: bool
    komunikat: str
    liczba_nowych: int
