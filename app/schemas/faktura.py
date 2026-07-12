from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import StatusFaktury, StawkaVat, TypDokumentu


class PozycjaFakturyCreate(BaseModel):
    nazwa: str = Field(min_length=1, max_length=500)
    ilosc: Decimal = Field(gt=0)
    jednostka_miary: str = Field(min_length=1, max_length=20)
    cena_netto_grosze: int = Field(gt=0)
    stawka_vat: StawkaVat


class PozycjaFakturyOut(BaseModel):
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


class FakturaCreate(BaseModel):
    typ_dokumentu: TypDokumentu = TypDokumentu.FAKTURA_VAT
    klient_id: int
    data_wystawienia: date
    data_sprzedazy: date
    termin_platnosci: date | None = None
    waluta: str | None = Field(default=None, min_length=3, max_length=3)
    kurs_waluty: Decimal = Field(default=Decimal("1"), gt=0)
    pozycje: list[PozycjaFakturyCreate] = Field(min_length=1)


class FakturaUpdate(BaseModel):
    typ_dokumentu: TypDokumentu | None = None
    klient_id: int | None = None
    data_wystawienia: date | None = None
    data_sprzedazy: date | None = None
    termin_platnosci: date | None = None
    waluta: str | None = Field(default=None, min_length=3, max_length=3)
    kurs_waluty: Decimal | None = Field(default=None, gt=0)
    pozycje: list[PozycjaFakturyCreate] | None = Field(default=None, min_length=1)


class FakturaStatusUpdate(BaseModel):
    status: StatusFaktury


class FakturaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    numer: str
    typ_dokumentu: TypDokumentu
    klient_id: int
    data_wystawienia: date
    data_sprzedazy: date
    termin_platnosci: date
    waluta: str
    kurs_waluty: Decimal
    status: StatusFaktury
    pozycje: list[PozycjaFakturyOut]
    suma_netto_grosze: int
    suma_vat_grosze: int
    suma_brutto_grosze: int
    utworzono: datetime
    zaktualizowano: datetime
