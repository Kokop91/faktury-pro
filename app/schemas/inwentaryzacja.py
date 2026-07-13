from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import StatusInwentaryzacji
from app.schemas.magazyn import DokumentMagazynowyOut


class InwentaryzacjaCreate(BaseModel):
    magazyn_id: int


class PozycjaInwentaryzacjiOut(BaseModel):
    """Budowany recznie w serwisie (nie przez from_attributes) - produkt_nazwa/
    jednostka_miary nie sa bezposrednimi atrybutami PozycjaInwentaryzacji, tylko
    pochodza z zaladowanej relacji produkt (mirror StanMagazynowyOut)."""

    id: int
    produkt_id: int
    produkt_nazwa: str
    jednostka_miary: str
    stan_systemowy: Decimal
    stan_faktyczny: Decimal | None


class InwentaryzacjaListOut(BaseModel):
    """Naglowek bez pozycji - do listy spisow, zeby nie ciagnac pelnej tabeli
    produktow przy kazdym GET /inwentaryzacje."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    magazyn_id: int
    numer: str
    data_rozpoczecia: date
    data_zakonczenia: date | None
    status: StatusInwentaryzacji
    utworzono: datetime
    zaktualizowano: datetime


class InwentaryzacjaOut(BaseModel):
    id: int
    magazyn_id: int
    numer: str
    data_rozpoczecia: date
    data_zakonczenia: date | None
    status: StatusInwentaryzacji
    pozycje: list[PozycjaInwentaryzacjiOut]
    utworzono: datetime
    zaktualizowano: datetime


class WpisStanuFaktycznego(BaseModel):
    produkt_id: int
    stan_faktyczny: Decimal = Field(ge=0)


class AktualizacjaPozycjiInwentaryzacji(BaseModel):
    pozycje: list[WpisStanuFaktycznego] = Field(min_length=1)


class ZamkniecieInwentaryzacjiOut(BaseModel):
    """Odpowiedz POST /inwentaryzacje/{id}/zamknij - poza zamknietym spisem
    zawiera dokumenty PW/RW wygenerowane z roznic i ewentualne ostrzezenia o
    ujemnym stanie (tryb "ostrzegaj"), analogicznie do
    UtworzenieDokumentuMagazynowegoOut."""

    inwentaryzacja: InwentaryzacjaOut
    dokumenty_utworzone: list[DokumentMagazynowyOut]
    ostrzezenia: list[str] = Field(default_factory=list)
