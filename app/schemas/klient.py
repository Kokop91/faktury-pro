import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

NIP_REGEX = re.compile(r"^\d{10}$")


def waliduj_nip(nip: str | None) -> str | None:
    if nip is not None and not NIP_REGEX.match(nip):
        raise ValueError("NIP musi się składać z dokładnie 10 cyfr")
    return nip


class KlientBase(BaseModel):
    nazwa: str = Field(min_length=1, max_length=255)
    nip: str | None = Field(default=None, max_length=10)
    ulica: str | None = Field(default=None, max_length=255)
    kod_pocztowy: str | None = Field(default=None, max_length=10)
    miejscowosc: str | None = Field(default=None, max_length=255)
    kraj: str = Field(default="Polska", max_length=100)
    email: str | None = Field(default=None, max_length=255)
    telefon: str | None = Field(default=None, max_length=30)
    domyslna_waluta: str = Field(default="PLN", min_length=3, max_length=3)
    domyslny_termin_platnosci_dni: int = Field(default=14, ge=0)

    _waliduj_nip = field_validator("nip")(waliduj_nip)


class KlientCreate(KlientBase):
    pass


class KlientUpdate(BaseModel):
    nazwa: str | None = Field(default=None, min_length=1, max_length=255)
    nip: str | None = Field(default=None, max_length=10)
    ulica: str | None = Field(default=None, max_length=255)
    kod_pocztowy: str | None = Field(default=None, max_length=10)
    miejscowosc: str | None = Field(default=None, max_length=255)
    kraj: str | None = Field(default=None, max_length=100)
    email: str | None = Field(default=None, max_length=255)
    telefon: str | None = Field(default=None, max_length=30)
    domyslna_waluta: str | None = Field(default=None, min_length=3, max_length=3)
    domyslny_termin_platnosci_dni: int | None = Field(default=None, ge=0)
    aktywny: bool | None = None

    _waliduj_nip = field_validator("nip")(waliduj_nip)


class KlientOut(KlientBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
    firma_id: int
    aktywny: bool
    utworzono: datetime
    zaktualizowano: datetime


class KlientImportWiersz(BaseModel):
    """Jeden wiersz importu CSV (Faza 26) - wszystkie pola oprocz numer_wiersza
    sa opcjonalne (w odroznieniu od KlientCreate), bo kazdy wiersz jest
    walidowany NIEZALEZNIE w warstwie serwisowej (klienci_service.importuj_klientow) -
    brakujace/bledne pole ma skutkowac pominieciem TEGO wiersza z czytelnym
    powodem, a nie odrzuceniem calego zadania przez FastAPI/pydantic (co
    zablokowaloby import pozostalych, poprawnych wierszy). GUI (gui/windows/
    dialog_importu_klientow.py) juz przeksztalcilo surowy tekst z pliku CSV na
    wlasciwe typy (np. termin platnosci na int) - ten schemat tylko przenosi
    dane, nie odpowiada za parsowanie formatu pliku."""

    numer_wiersza: int
    nazwa: str | None = None
    nip: str | None = None
    ulica: str | None = None
    kod_pocztowy: str | None = None
    miejscowosc: str | None = None
    kraj: str | None = None
    email: str | None = None
    telefon: str | None = None
    domyslna_waluta: str | None = None
    domyslny_termin_platnosci_dni: int | None = None


class KlientImportWynik(BaseModel):
    """Wynik przetworzenia jednego wiersza importu - `sukces=False` niesie
    czytelny powod w `komunikat` (albo z walidacji KlientCreate, albo z
    wykrycia duplikatu NIP), zeby GUI mogl pokazac pelne podsumowanie
    zaimportowane/pominiete zamiast cichego czesciowego niepowodzenia."""

    numer_wiersza: int
    sukces: bool
    komunikat: str | None = None
    klient: KlientOut | None = None
