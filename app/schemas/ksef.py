from pydantic import BaseModel


class UstawieniaKsefOut(BaseModel):
    srodowisko: str
    ma_token: bool
    token_podglad: str | None = None
    sprawdzaj_koszty_przy_starcie: bool
    ostatnie_sprawdzenie_kosztow: str | None = None


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
