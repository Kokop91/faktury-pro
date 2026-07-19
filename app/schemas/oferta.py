from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import StatusOferty, StawkaVat


class PozycjaOfertyCreate(BaseModel):
    nazwa: str = Field(min_length=1, max_length=500)
    ilosc: Decimal = Field(gt=0)
    jednostka_miary: str = Field(min_length=1, max_length=20)
    cena_netto_grosze: int = Field(gt=0)
    stawka_vat: StawkaVat


class PozycjaOfertyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nazwa: str
    ilosc: Decimal
    jednostka_miary: str
    cena_netto_grosze: int
    stawka_vat: StawkaVat
    wartosc_netto_grosze: int
    wartosc_vat_grosze: int
    wartosc_brutto_grosze: int


class OfertaCreate(BaseModel):
    klient_id: int
    data_wystawienia: date
    data_waznosci: date
    waluta: str | None = Field(default=None, min_length=3, max_length=3)
    kurs_waluty: Decimal = Field(default=Decimal("1"), gt=0)
    pozycje: list[PozycjaOfertyCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def _sprawdz_pozycje(self) -> "OfertaCreate":
        if not self.pozycje:
            raise ValueError("Oferta musi mieć co najmniej jedną pozycję.")
        return self


class OfertaUpdate(BaseModel):
    klient_id: int | None = None
    data_wystawienia: date | None = None
    data_waznosci: date | None = None
    waluta: str | None = Field(default=None, min_length=3, max_length=3)
    kurs_waluty: Decimal | None = Field(default=None, gt=0)
    pozycje: list[PozycjaOfertyCreate] | None = None


class OfertaStatusUpdate(BaseModel):
    status: StatusOferty


class OfertaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numer: str
    klient_id: int
    data_wystawienia: date
    data_waznosci: date
    waluta: str
    kurs_waluty: Decimal
    status: StatusOferty
    status_efektywny: StatusOferty
    faktura_wygenerowana_id: int | None
    pozycje: list[PozycjaOfertyOut]
    suma_netto_grosze: int
    suma_vat_grosze: int
    suma_brutto_grosze: int
    utworzono: datetime
    zaktualizowano: datetime
