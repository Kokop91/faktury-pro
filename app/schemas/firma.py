from datetime import date, datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import TrybBlokadyStanu, TypPodatnika
from app.schemas.klient import waliduj_nip


class FirmaBase(BaseModel):
    nazwa: str = Field(min_length=1, max_length=255)
    nip: str = Field(max_length=10)
    ulica: str | None = Field(default=None, max_length=255)
    kod_pocztowy: str | None = Field(default=None, max_length=10)
    miejscowosc: str | None = Field(default=None, max_length=255)
    kraj: str = Field(default="Polska", max_length=100)
    email: str | None = Field(default=None, max_length=255)
    telefon: str | None = Field(default=None, max_length=30)
    bank_nazwa: str | None = Field(default=None, max_length=255)
    bank_numer_konta: str | None = Field(default=None, max_length=34)
    tryb_blokady_ujemnego_stanu: TrybBlokadyStanu = TrybBlokadyStanu.OSTRZEGAJ

    # Faza 13 (JPK_V7) - patrz komentarz przy modelu Firma.
    typ_podatnika: TypPodatnika = TypPodatnika.OSOBA_NIEFIZYCZNA
    imie_pierwsze: str | None = Field(default=None, max_length=30)
    nazwisko: str | None = Field(default=None, max_length=81)
    data_urodzenia: date | None = None
    kod_urzedu_skarbowego: str | None = Field(default=None, min_length=4, max_length=4)

    _waliduj_nip = field_validator("nip")(waliduj_nip)


class FirmaCreate(FirmaBase):
    pass


class FirmaUpdate(BaseModel):
    nazwa: str | None = Field(default=None, min_length=1, max_length=255)
    nip: str | None = Field(default=None, max_length=10)
    ulica: str | None = Field(default=None, max_length=255)
    kod_pocztowy: str | None = Field(default=None, max_length=10)
    miejscowosc: str | None = Field(default=None, max_length=255)
    kraj: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    telefon: str | None = Field(default=None, max_length=30)
    bank_nazwa: str | None = Field(default=None, max_length=255)
    bank_numer_konta: str | None = Field(default=None, max_length=34)
    tryb_blokady_ujemnego_stanu: TrybBlokadyStanu | None = None
    typ_podatnika: TypPodatnika | None = None
    imie_pierwsze: str | None = Field(default=None, max_length=30)
    nazwisko: str | None = Field(default=None, max_length=81)
    data_urodzenia: date | None = None
    kod_urzedu_skarbowego: str | None = Field(default=None, min_length=4, max_length=4)

    _waliduj_nip = field_validator("nip")(waliduj_nip)


class FirmaOut(FirmaBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    utworzono: datetime
    zaktualizowano: datetime
