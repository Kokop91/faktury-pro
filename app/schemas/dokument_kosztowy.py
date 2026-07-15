from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models.enums import StatusDokumentuKosztowego


class DokumentKosztowyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    kontrahent_nazwa: str | None
    kontrahent_nip: str | None
    numer_faktury: str
    numer_ksef: str
    data_wystawienia: date
    waluta: str
    netto_grosze: int
    brutto_grosze: int
    vat_grosze_pln: int
    status: StatusDokumentuKosztowego
    pobrano_o: datetime


class DokumentKosztowySzczegolyOut(DokumentKosztowyOut):
    xml_oryginalny: str


class DokumentKosztowyStatusUpdate(BaseModel):
    status: StatusDokumentuKosztowego


class LiczbaNowychOut(BaseModel):
    liczba_nowych: int
