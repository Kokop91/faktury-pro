from pydantic import BaseModel

from app.schemas.faktura import FakturaOut
from app.schemas.magazyn import StanMagazynowyOut
from app.schemas.rentownosc import MarzaOkresuOut, PunktWykresuPrzychodKosztOut


class KafelkiDashboarduOut(BaseModel):
    przychod_biezacy_miesiac_grosze: int
    liczba_faktur_biezacy_miesiac: int
    naleznosci_grosze: int
    liczba_faktur_po_terminie: int
    kwota_po_terminie_grosze: int
    # Faza 12D - podsumowanie integracji KSeF na dashboardzie.
    liczba_faktur_oczekujacych_ksef: int
    liczba_faktur_odrzuconych_ksef: int
    liczba_dokumentow_kosztowych_nowych: int


class PunktWykresuPrzychodowOut(BaseModel):
    rok: int
    miesiac: int
    suma_brutto_grosze: int


class DashboardOut(BaseModel):
    kafelki: KafelkiDashboarduOut
    wykres_przychodow: list[PunktWykresuPrzychodowOut]
    faktury_po_terminie: list[FakturaOut]
    faktury_odrzucone_ksef: list[FakturaOut]
    ponizej_minimum: list[StanMagazynowyOut]
    # Faza 25 - marza i wykres przychody/koszty, zawsze biezacy miesiac /
    # ostatnie 12 miesiecy (ta sama "bez konfiguracji" filozofia co reszta
    # dashboardu - GET /dashboard nie przyjmuje zadnych parametrow).
    marza_biezacy_miesiac: MarzaOkresuOut
    wykres_przychodow_kosztow: list[PunktWykresuPrzychodKosztOut]
