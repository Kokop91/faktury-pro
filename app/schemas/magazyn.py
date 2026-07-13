from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import StawkaVat, TypDokumentuMagazynowego


class ProduktBase(BaseModel):
    nazwa: str = Field(min_length=1, max_length=255)
    jednostka_miary: str = Field(min_length=1, max_length=20)
    cena_netto_grosze: int = Field(ge=0)
    domyslna_stawka_vat: StawkaVat = StawkaVat.STAWKA_23
    jest_magazynowy: bool


class ProduktCreate(ProduktBase):
    pass


class ProduktOut(ProduktBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    firma_id: int
    aktywny: bool
    utworzono: datetime
    zaktualizowano: datetime


class MagazynBase(BaseModel):
    nazwa: str = Field(min_length=1, max_length=255)
    lokalizacja: str | None = Field(default=None, max_length=500)


class MagazynCreate(MagazynBase):
    pass


class MagazynOut(MagazynBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    firma_id: int
    aktywny: bool
    utworzono: datetime
    zaktualizowano: datetime


class StanMagazynowyOut(BaseModel):
    """Budowany recznie w serwisie (nie przez from_attributes) - produkt_nazwa/
    jednostka_miary/magazyn_nazwa nie sa bezposrednimi atrybutami StanMagazynowy,
    tylko pochodza z zaladowanych relacji produkt/magazyn."""

    id: int
    produkt_id: int
    magazyn_id: int
    produkt_nazwa: str
    jednostka_miary: str
    magazyn_nazwa: str
    ilosc: Decimal
    stan_minimalny: Decimal | None
    ponizej_minimum: bool


class PozycjaDokumentuMagazynowegoCreate(BaseModel):
    produkt_id: int
    ilosc: Decimal = Field(gt=0)
    notatka: str | None = Field(default=None, max_length=500)


class PozycjaDokumentuMagazynowegoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    produkt_id: int
    ilosc: Decimal
    notatka: str | None


class DokumentMagazynowyCreate(BaseModel):
    typ: TypDokumentuMagazynowego
    data_dokumentu: date
    magazyn_zrodlowy_id: int | None = None
    magazyn_docelowy_id: int | None = None
    faktura_powiazana_id: int | None = None
    pozycje: list[PozycjaDokumentuMagazynowegoCreate] = Field(min_length=1)


class DokumentMagazynowyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    typ: TypDokumentuMagazynowego
    numer: str
    data_dokumentu: date
    magazyn_zrodlowy_id: int | None
    magazyn_docelowy_id: int | None
    faktura_powiazana_id: int | None
    pozycje: list[PozycjaDokumentuMagazynowegoOut]
    utworzono: datetime
    zaktualizowano: datetime


class UtworzenieDokumentuMagazynowegoOut(BaseModel):
    """Odpowiedz POST /dokumenty-magazynowe - poza utworzonym dokumentem zawiera
    ostrzezenia o zejsciu ponizej zera (tryb "ostrzegaj"), ktore nie maja sensu
    poza momentem tworzenia, wiec nie sa czescia DokumentMagazynowyOut (uzywanego
    tez przez GET)."""

    dokument: DokumentMagazynowyOut
    ostrzezenia: list[str] = Field(default_factory=list)


class RuchMagazynowyOut(BaseModel):
    dokument_id: int
    typ_dokumentu: TypDokumentuMagazynowego
    numer_dokumentu: str
    data_dokumentu: date
    produkt_id: int
    produkt_nazwa: str
    magazyn_id: int
    magazyn_nazwa: str
    zmiana_ilosci: Decimal
    notatka: str | None
    utworzono: datetime
