from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class WeryfikacjaBialejListyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    klient_id: int | None
    faktura_id: int | None
    nip: str
    numer_konta: str | None
    data_na_dzien: date
    znaleziono: bool
    status_vat: str | None
    nazwa_podmiotu: str | None
    konto_zgodne: bool | None
    sprawdzono_o: datetime


class SprawdzBialaListeIn(BaseModel):
    nip: str
    numer_konta: str | None = None
    klient_id: int | None = None
    faktura_id: int | None = None
