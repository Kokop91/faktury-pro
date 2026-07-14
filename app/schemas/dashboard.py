from pydantic import BaseModel

from app.schemas.faktura import FakturaOut
from app.schemas.magazyn import StanMagazynowyOut


class KafelkiDashboarduOut(BaseModel):
    przychod_biezacy_miesiac_grosze: int
    liczba_faktur_biezacy_miesiac: int
    naleznosci_grosze: int
    liczba_faktur_po_terminie: int
    kwota_po_terminie_grosze: int


class PunktWykresuPrzychodowOut(BaseModel):
    rok: int
    miesiac: int
    suma_brutto_grosze: int


class DashboardOut(BaseModel):
    kafelki: KafelkiDashboarduOut
    wykres_przychodow: list[PunktWykresuPrzychodowOut]
    faktury_po_terminie: list[FakturaOut]
    ponizej_minimum: list[StanMagazynowyOut]
