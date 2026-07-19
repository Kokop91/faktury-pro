from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import TypPrzypomnienia


class KandydatPrzypomnieniaOut(BaseModel):
    faktura_id: int
    numer_faktury: str
    klient_id: int
    klient_nazwa: str
    klient_email: str | None
    typ: TypPrzypomnienia
    termin_platnosci: date
    kwota_pozostala_grosze: int
    waluta: str


class PozycjaDoWyslaniaPrzypomnienia(BaseModel):
    faktura_id: int
    typ: TypPrzypomnienia


class WyslijPrzypomnieniaIn(BaseModel):
    pozycje: list[PozycjaDoWyslaniaPrzypomnienia] = Field(min_length=1)


class WynikWyslaniaPrzypomnieniaOut(BaseModel):
    faktura_id: int
    typ: TypPrzypomnienia
    powodzenie: bool
    komunikat: str


class PrzypomnieniePlatnosciOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    typ: TypPrzypomnienia
    adres_email: str
    wyslano_o: datetime
