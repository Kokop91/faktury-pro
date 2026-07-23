import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator

NIP_REGEX = re.compile(r"^\d{10}$")
KOD_POCZTOWY_REGEX = re.compile(r"^\d{2}-\d{3}$")
# Cyfry, spacje, myslniki, nawiasy, opcjonalny "+" na poczatku - swiadomie
# szeroko, zeby zaakceptowac zarowno numer kierunkowy kraju (+48 123 456 789),
# jak i krajowy numer kierunkowy stacjonarny w nawiasie ((22) 123 45 67).
TELEFON_REGEX = re.compile(r"^\+?[\d\s()-]{7,30}$")
# Celowo liberalna (nie pelny RFC 5322) - odrzuca tylko oczywiste smieci (brak
# "@", spacje w srodku), ten sam poziom rygoru co TELEFON_REGEX powyzej.
EMAIL_REGEX = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


def waliduj_nip(nip: str | None) -> str | None:
    """Akceptuje NIP zapisany z myslnikami/spacjami (np. '525-239-98-25',
    '525 239 98 25') - popularne formaty kopiowane z pism urzedowych/faktur -
    obok golego ciagu 10 cyfr. Ten sam wzorzec co kod pocztowy/telefon
    (Faza 27): appka usuwa separatory zamiast twardo odrzucac oczywisty,
    latwy do naprawienia przypadek."""
    if nip is None:
        return None
    nip = nip.strip()
    if not nip:
        return None
    same_cyfry = re.sub(r"[\s-]", "", nip)
    if not NIP_REGEX.match(same_cyfry):
        raise ValueError("NIP musi się składać z dokładnie 10 cyfr")
    return same_cyfry


def waliduj_email(email: str | None) -> str | None:
    """Celowo liberalna walidacja (jak telefon powyzej) - odrzuca tylko
    oczywiste smieci (brak '@', brak domeny), nie probuje wymuszac pelnego
    RFC 5322. Uzywana wszedzie tam, gdzie appka faktycznie wysyla na ten
    adres (przypomnienia o platnosciach, Faza 23) - bledny format
    wykryty od razu przy zapisie, nie dopiero przy nieudanej probie wysylki."""
    if email is None:
        return None
    email = email.strip()
    if not email:
        return None
    if not EMAIL_REGEX.match(email):
        raise ValueError("Nieprawidłowy format adresu email (oczekiwano np. jan@firma.pl)")
    return email


NUMER_KONTA_REGEX = re.compile(r"^[A-Za-z]{0,2}[\d\s-]{6,34}$")


def waliduj_numer_konta(numer: str | None) -> str | None:
    """Numer konta bankowego / IBAN - celowo liberalna walidacja (jak telefon
    powyzej), zeby nie odrzucac zapisu ze spacjami co 4 znaki (popularny
    sposob grupowania, np. 'PL61 1090 1014 0000 0712 1981 2874') ani bez
    dwuliterowego prefiksu kraju (zwykly polski NRB, 26 cyfr). Appka
    przechowuje oryginalne formatowanie (drukowane na fakturze do zaplaty),
    walidacja tylko odrzuca oczywiste smieci - litery poza prefiksem kraju,
    zbyt krotki/dlugi ciag. Sprawdzenie w Bialej Liscie VAT
    (app/services/biala_lista_service.py) i tak usuwa spacje przed
    zapytaniem, wiec nie robimy tego tutaj ponownie."""
    if numer is None:
        return None
    numer = numer.strip()
    if not numer:
        return None
    if not NUMER_KONTA_REGEX.match(numer):
        raise ValueError(
            "Numer konta bankowego może zawierać tylko cyfry, spacje, "
            "myślniki i opcjonalny dwuliterowy kod kraju na początku "
            "(np. PL61 1090 1014 0000 0712 1981 2874)"
        )
    same_cyfry = re.sub(r"\D", "", numer)
    if not (6 <= len(same_cyfry) <= 32):
        raise ValueError("Numer konta bankowego ma nieprawidłową długość")
    return numer


def waliduj_kod_pocztowy(kod: str | None) -> str | None:
    """Akceptuje polski format XX-XXX. Jesli uzytkownik wpisze 5 cyfr bez
    myslnika (np. wklejone z innego zrodla, albo po prostu bez separatora),
    myslnik jest dostawiany automatycznie zamiast odrzucania calego pola -
    mniej frustrujace niz twardy blad przy oczywistym, latwym do naprawienia
    przypadku."""
    if kod is None:
        return None
    kod = kod.strip()
    if not kod:
        return None
    if KOD_POCZTOWY_REGEX.match(kod):
        return kod
    same_cyfry = re.sub(r"\D", "", kod)
    if len(same_cyfry) == 5:
        return f"{same_cyfry[:2]}-{same_cyfry[2:]}"
    raise ValueError("Kod pocztowy musi być w formacie XX-XXX (np. 00-950)")


def waliduj_telefon(telefon: str | None) -> str | None:
    """Celowo liberalna walidacja - odrzuca tylko oczywiste smieci (litery,
    zbyt krotki ciag), nie wymusza jednego sztywnego formatu. Akceptuje
    numer kierunkowy kraju (+48...) i krajowy numer kierunkowy stacjonarny
    w nawiasie, ze spacjami/myslnikami jako separatorami cyfr."""
    if telefon is None:
        return None
    telefon = telefon.strip()
    if not telefon:
        return None
    if not TELEFON_REGEX.match(telefon):
        raise ValueError(
            "Numer telefonu może zawierać tylko cyfry, spacje, myślniki, "
            "nawiasy i znak '+' na początku (np. +48 123 456 789)"
        )
    same_cyfry = re.sub(r"\D", "", telefon)
    if len(same_cyfry) < 7:
        raise ValueError("Numer telefonu jest za krótki")
    return telefon


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

    _waliduj_nip = field_validator("nip", mode="before")(waliduj_nip)
    _waliduj_kod_pocztowy = field_validator("kod_pocztowy")(waliduj_kod_pocztowy)
    _waliduj_telefon = field_validator("telefon")(waliduj_telefon)
    _waliduj_email = field_validator("email")(waliduj_email)


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

    _waliduj_nip = field_validator("nip", mode="before")(waliduj_nip)
    _waliduj_kod_pocztowy = field_validator("kod_pocztowy")(waliduj_kod_pocztowy)
    _waliduj_telefon = field_validator("telefon")(waliduj_telefon)
    _waliduj_email = field_validator("email")(waliduj_email)


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
