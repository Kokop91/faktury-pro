from datetime import date
from decimal import Decimal

from pydantic import BaseModel


class MarzaOkresuOut(BaseModel):
    przychod_netto_grosze: int
    koszty_ksef_grosze: int
    koszty_reczne_grosze: int
    koszty_razem_grosze: int
    marza_grosze: int
    # None gdy ma_dane_kosztowe=False - nie ma sensu liczyc marzy/procentu bez
    # zadnych danych kosztowych w okresie (patrz rentownosc_service.marza_okresu).
    marza_procent: float | None
    ma_dane_kosztowe: bool


class PunktWykresuPrzychodKosztOut(BaseModel):
    rok: int
    miesiac: int
    przychod_netto_grosze: int
    koszty_grosze: int


class KubelekPrognozyOut(BaseModel):
    etykieta: str
    kwota_grosze: int


class PozycjaPrognozyOut(BaseModel):
    faktura_id: int
    numer: str
    klient_nazwa: str
    kwota_pozostala_grosze: int
    waluta: str
    termin_bazowy: date
    termin_skorygowany: date


class PrognozaWplywowOut(BaseModel):
    kubelki_podstawowe: list[KubelekPrognozyOut]
    kubelki_skorygowane: list[KubelekPrognozyOut]
    pozycje: list[PozycjaPrognozyOut]


class RentownoscProduktuOut(BaseModel):
    produkt_id: int
    nazwa: str
    jednostka_miary: str
    ilosc_sprzedana: Decimal
    przychod_netto_grosze: int
    koszt_grosze: int
    marza_grosze: int
    marza_procent: float | None
