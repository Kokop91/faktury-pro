from datetime import date

from pydantic import BaseModel


class UstawieniaGusOut(BaseModel):
    srodowisko: str
    ma_klucz_produkcyjny: bool


class UstawieniaGusIn(BaseModel):
    srodowisko: str | None = None
    klucz_produkcyjny: str | None = None


class GusPodmiotOut(BaseModel):
    regon: str | None
    nazwa: str | None
    ulica: str | None
    kod_pocztowy: str | None
    miejscowosc: str | None


class KursWalutyOut(BaseModel):
    waluta: str
    kurs: str
    data_efektywna: date
