from datetime import date, datetime
from decimal import Decimal
from typing import Protocol, Sequence

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.models.enums import (
    TYPY_WYMAGAJACE_DOKUMENTU_POWIAZANEGO,
    TYPY_WYMAGAJACE_PRZYCZYNY_KOREKTY,
    StatusFaktury,
    StatusKsef,
    StawkaVat,
    TypDokumentu,
)


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


class _MaStawkeVat(Protocol):
    stawka_vat: StawkaVat


def znajdz_blad_zgodnosci_typu_dokumentu(
    typ_dokumentu: TypDokumentu,
    pozycje: Sequence[_MaStawkeVat],
    dokument_powiazany_id: int | None,
    przyczyna_korekty: str | None,
) -> str | None:
    """Sprawdza reguly ksztaltu dokumentu wynikajace z typ_dokumentu (bez dostepu do bazy -
    referencje do innych faktur sprawdza dopiero serwis). Zwraca komunikat bledu albo None.

    Wspoldzielone przez FakturaCreate (szybki 422) i serwis (app/services/faktury.py,
    zrodlo prawdy - FakturaUpdate to czesciowy PATCH i tylko serwis widzi efektywny stan
    po scaleniu ze stanem w bazie), zeby regul nie utrzymywac w dwoch miejscach.
    """
    if typ_dokumentu == TypDokumentu.RACHUNEK and any(
        p.stawka_vat != StawkaVat.ZW for p in pozycje
    ):
        return (
            "Rachunek może zawierać wyłącznie pozycje ze stawką VAT 'zw' - "
            "wystawca rachunku jest zwolniony z VAT."
        )

    if typ_dokumentu != TypDokumentu.NOTA_KORYGUJACA and not pozycje:
        return f"Faktura typu '{typ_dokumentu.value}' musi mieć co najmniej jedną pozycję."

    wymaga_dokumentu = typ_dokumentu in TYPY_WYMAGAJACE_DOKUMENTU_POWIAZANEGO
    if wymaga_dokumentu and dokument_powiazany_id is None:
        return (
            f"Dla dokumentu typu '{typ_dokumentu.value}' wymagane jest "
            "wskazanie dokumentu powiązanego (dokument_powiazany_id)."
        )
    if not wymaga_dokumentu and dokument_powiazany_id is not None:
        return (
            f"Dokument typu '{typ_dokumentu.value}' nie może mieć wskazanego "
            "dokumentu powiązanego."
        )

    if typ_dokumentu in TYPY_WYMAGAJACE_PRZYCZYNY_KOREKTY and not (
        przyczyna_korekty and przyczyna_korekty.strip()
    ):
        return (
            f"Dla dokumentu typu '{typ_dokumentu.value}' wymagane jest "
            "podanie przyczyny korekty (przyczyna_korekty)."
        )

    return None


class FakturaCreate(BaseModel):
    typ_dokumentu: TypDokumentu = TypDokumentu.FAKTURA_VAT
    klient_id: int
    data_wystawienia: date
    data_sprzedazy: date
    termin_platnosci: date | None = None
    waluta: str | None = Field(default=None, min_length=3, max_length=3)
    kurs_waluty: Decimal = Field(default=Decimal("1"), gt=0)
    dokument_powiazany_id: int | None = None
    przyczyna_korekty: str | None = Field(default=None, max_length=2000)
    pozycje: list[PozycjaFakturyCreate] = Field(default_factory=list)
    # Faza 21 (split payment) - None = pozwol serwisowi wykryc obowiazek MPP
    # automatycznie (app/services/mpp_service.py); True/False = swiadome
    # reczne nadpisanie sugestii (dobrowolne MPP jest dozwolone).
    wymaga_mpp: bool | None = None

    @model_validator(mode="after")
    def _sprawdz_zgodnosc_typu_dokumentu(self) -> "FakturaCreate":
        blad = znajdz_blad_zgodnosci_typu_dokumentu(
            self.typ_dokumentu,
            self.pozycje,
            self.dokument_powiazany_id,
            self.przyczyna_korekty,
        )
        if blad is not None:
            raise ValueError(blad)
        return self


class FakturaUpdate(BaseModel):
    typ_dokumentu: TypDokumentu | None = None
    klient_id: int | None = None
    data_wystawienia: date | None = None
    data_sprzedazy: date | None = None
    termin_platnosci: date | None = None
    waluta: str | None = Field(default=None, min_length=3, max_length=3)
    kurs_waluty: Decimal | None = Field(default=None, gt=0)
    dokument_powiazany_id: int | None = None
    przyczyna_korekty: str | None = Field(default=None, max_length=2000)
    pozycje: list[PozycjaFakturyCreate] | None = None
    # Faza 21 - patrz komentarz przy FakturaCreate.wymaga_mpp. Klucz nieobecny
    # w zadaniu (model_fields_set) = przelicz sugestie na nowo, jesli pozycje/
    # klient sie zmienily; podana wartosc bool = reczne nadpisanie.
    wymaga_mpp: bool | None = None


class FakturaStatusUpdate(BaseModel):
    status: StatusFaktury


class PlatnoscCreate(BaseModel):
    data_platnosci: date
    kwota_grosze: int = Field(gt=0)
    notatka: str | None = Field(default=None, max_length=500)


class PlatnoscOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    faktura_id: int
    data_platnosci: date
    kwota_grosze: int
    notatka: str | None
    utworzono: datetime


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
    status_efektywny: StatusFaktury
    dokument_powiazany_id: int | None
    przyczyna_korekty: str | None
    szablon_cykliczny_id: int | None
    okres_cykliczny: date | None
    status_ksef: StatusKsef
    numer_ksef: str | None
    przyczyna_odrzucenia_ksef: str | None
    ma_upo: bool
    wymaga_mpp: bool
    pozycje: list[PozycjaFakturyOut]
    suma_netto_grosze: int
    suma_vat_grosze: int
    suma_brutto_grosze: int
    suma_wplat_grosze: int
    kwota_pozostala_grosze: int
    utworzono: datetime
    zaktualizowano: datetime


class NaleznosciOut(BaseModel):
    suma_naleznosci_grosze: int
    faktury: list[FakturaOut]


class WyslijKsefOut(BaseModel):
    powodzenie: bool
    komunikat: str
    status_ksef: StatusKsef
    numer_ksef: str | None = None


class WyslijZbiorczoIn(BaseModel):
    faktura_ids: list[int] = Field(min_length=1)


class WyslijKsefZbiorczoWynikOut(BaseModel):
    faktura_id: int
    powodzenie: bool
    komunikat: str
    # W odroznieniu od WyslijKsefOut - opcjonalne, bo przy bledzie
    # uwierzytelnienia (wspolnym dla calej paczki) status konkretnej faktury
    # mogl sie w ogole nie zmienic (patrz ksef_service.wyslij_faktury_zbiorczo).
    status_ksef: StatusKsef | None = None
    numer_ksef: str | None = None
