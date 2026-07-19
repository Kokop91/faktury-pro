from pydantic import BaseModel


class UstawieniaEmailOut(BaseModel):
    host: str | None = None
    port: int
    uzytkownik: str | None = None
    ma_haslo: bool
    szyfrowanie: str
    nadawca_adres: str | None = None
    nadawca_nazwa: str | None = None


class UstawieniaEmailIn(BaseModel):
    host: str | None = None
    port: int | None = None
    uzytkownik: str | None = None
    haslo: str | None = None
    szyfrowanie: str | None = None
    nadawca_adres: str | None = None
    nadawca_nazwa: str | None = None


class TestEmailOut(BaseModel):
    powodzenie: bool
    komunikat: str
