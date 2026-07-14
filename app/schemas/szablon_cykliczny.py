from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import (
    DOZWOLONE_TYPY_SZABLONU_CYKLICZNEGO,
    CzestotliwoscCykliczna,
    StatusSzablonuCyklicznego,
    StawkaVat,
    TypDokumentu,
)


class PozycjaSzablonuCyklicznegoCreate(BaseModel):
    nazwa: str = Field(min_length=1, max_length=500)
    ilosc: Decimal = Field(gt=0)
    jednostka_miary: str = Field(min_length=1, max_length=20)
    cena_netto_grosze: int = Field(gt=0)
    stawka_vat: StawkaVat


class PozycjaSzablonuCyklicznegoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    nazwa: str
    ilosc: Decimal
    jednostka_miary: str
    cena_netto_grosze: int
    stawka_vat: StawkaVat


def _zwaliduj_ksztalt_szablonu(
    typ_dokumentu: TypDokumentu,
    pozycje: list,
    data_poczatku: date,
    data_konca: date | None,
) -> str | None:
    """Reguly ksztaltu szablonu (bez dostepu do bazy) - wspoldzielone przez
    schemat (szybki 422) i serwis (zrodlo prawdy przy edycji, patrz
    app/services/faktury_cykliczne.py)."""
    if typ_dokumentu not in DOZWOLONE_TYPY_SZABLONU_CYKLICZNEGO:
        return (
            f"Dokument typu '{typ_dokumentu.value}' nie może być szablonem cyklicznym - "
            "korekty/noty/faktury końcowe odnoszą się zawsze do jednego, konkretnego "
            "wcześniejszego dokumentu."
        )
    if not pozycje:
        return "Szablon musi mieć co najmniej jedną pozycję."
    if typ_dokumentu == TypDokumentu.RACHUNEK and any(
        p.stawka_vat != StawkaVat.ZW for p in pozycje
    ):
        return (
            "Rachunek może zawierać wyłącznie pozycje ze stawką VAT 'zw' - "
            "wystawca rachunku jest zwolniony z VAT."
        )
    if data_konca is not None and data_konca < data_poczatku:
        return "Data zakończenia nie może być wcześniejsza niż data początku."
    return None


class SzablonCyklicznyCreate(BaseModel):
    klient_id: int
    typ_dokumentu: TypDokumentu = TypDokumentu.FAKTURA_VAT
    waluta: str | None = Field(default=None, min_length=3, max_length=3)
    czestotliwosc: CzestotliwoscCykliczna
    dzien_generowania: int = Field(ge=1, le=31)
    data_poczatku: date
    data_konca: date | None = None
    pozycje: list[PozycjaSzablonuCyklicznegoCreate] = Field(default_factory=list)

    @model_validator(mode="after")
    def _sprawdz_ksztalt(self) -> "SzablonCyklicznyCreate":
        blad = _zwaliduj_ksztalt_szablonu(
            self.typ_dokumentu, self.pozycje, self.data_poczatku, self.data_konca
        )
        if blad is not None:
            raise ValueError(blad)
        return self


class SzablonCyklicznyUpdate(BaseModel):
    klient_id: int | None = None
    typ_dokumentu: TypDokumentu | None = None
    waluta: str | None = Field(default=None, min_length=3, max_length=3)
    czestotliwosc: CzestotliwoscCykliczna | None = None
    dzien_generowania: int | None = Field(default=None, ge=1, le=31)
    data_poczatku: date | None = None
    data_konca: date | None = None
    pozycje: list[PozycjaSzablonuCyklicznegoCreate] | None = None


class SzablonCyklicznyStatusUpdate(BaseModel):
    status: StatusSzablonuCyklicznego


class SzablonCyklicznyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    klient_id: int
    typ_dokumentu: TypDokumentu
    waluta: str
    czestotliwosc: CzestotliwoscCykliczna
    dzien_generowania: int
    data_poczatku: date
    data_konca: date | None
    status: StatusSzablonuCyklicznego
    pozycje: list[PozycjaSzablonuCyklicznegoOut]
    suma_brutto_szacowana_grosze: int
    nastepny_termin: date | None
    utworzono: datetime
    zaktualizowano: datetime


class ZaleglaFakturaCykliczna(BaseModel):
    szablon_id: int
    klient_id: int
    klient_nazwa: str
    typ_dokumentu: TypDokumentu
    okres: date
    waluta: str
    kwota_brutto_szacowana_grosze: int


class PozycjaDoWygenerowania(BaseModel):
    szablon_id: int
    okres: date


class WygenerujFakturyCyklicznieIn(BaseModel):
    # None = wygeneruj wszystkie aktualnie zalegle terminy dla wszystkich
    # aktywnych szablonow ("Wygeneruj wszystkie" w oknie startowym).
    pozycje: list[PozycjaDoWygenerowania] | None = None
