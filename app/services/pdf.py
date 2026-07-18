from decimal import Decimal
from pathlib import Path

from fastapi import HTTPException, status
from jinja2 import Environment, FileSystemLoader, select_autoescape
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload
from weasyprint import HTML

from app.models import Faktura, Klient
from app.models.enums import StawkaVat, TypDokumentu
from app.sciezki import katalog_bazowy
from app.services.faktury import podsumowanie_wg_stawek

TEMPLATES_DIR = katalog_bazowy() / "app" / "templates"

TYTULY_DOKUMENTU: dict[TypDokumentu, str] = {
    TypDokumentu.FAKTURA_VAT: "Faktura VAT",
    TypDokumentu.PROFORMA: "Faktura pro forma",
    TypDokumentu.FAKTURA_ZALICZKOWA: "Faktura zaliczkowa",
    TypDokumentu.FAKTURA_KONCOWA: "Faktura rozliczeniowa (końcowa)",
    TypDokumentu.FAKTURA_KORYGUJACA: "Faktura korygująca",
    TypDokumentu.NOTA_KORYGUJACA: "Nota korygująca",
    TypDokumentu.RACHUNEK: "Rachunek",
}

ETYKIETY_STAWEK_VAT: dict[StawkaVat, str] = {
    StawkaVat.STAWKA_23: "23%",
    StawkaVat.STAWKA_8: "8%",
    StawkaVat.STAWKA_5: "5%",
    StawkaVat.STAWKA_0: "0%",
    StawkaVat.ZW: "zw.",
}

# Typy, dla ktorych sekcja "podsumowanie wg stawek VAT" nie ma sensu: RACHUNEK bo wystawca
# jest zwolniony z VAT (wszystkie pozycje to i tak "zw."), NOTA_KORYGUJACA bo w ogole nie ma
# pozycji z cenami (koryguje bledy formalne, nie kwoty).
TYPY_BEZ_PODSUMOWANIA_VAT = {TypDokumentu.RACHUNEK, TypDokumentu.NOTA_KORYGUJACA}


def _grosze_na_zlote(grosze: int) -> str:
    zlote = Decimal(grosze) / Decimal(100)
    tekst = f"{zlote:,.2f}"
    return tekst.replace(",", " ").replace(".", ",")


def _etykieta_stawki_vat(stawka: StawkaVat) -> str:
    return ETYKIETY_STAWEK_VAT[stawka]


_jinja_env = Environment(
    loader=FileSystemLoader(str(TEMPLATES_DIR)),
    autoescape=select_autoescape(["html"]),
)
_jinja_env.filters["grosze_na_zlote"] = _grosze_na_zlote
_jinja_env.filters["etykieta_stawki_vat"] = _etykieta_stawki_vat


def _logo_uri(logo_path: str | None) -> str | None:
    if not logo_path:
        return None
    try:
        return Path(logo_path).resolve(strict=True).as_uri()
    except (OSError, ValueError):
        # Brakujacy/nieprawidlowy plik logo - PDF generuje sie bez logo, nie wywala sie.
        return None


def _pobierz_fakture_do_pdf(db: Session, faktura_id: int) -> Faktura:
    """Dedykowany loader (nie pobierz_fakture z faktury.py) - PDF potrzebuje dodatkowo
    danych sprzedawcy (Faktura.klient.firma) i, gdy ustawione, pozycji dokumentu
    powiazanego (do wyliczenia sum na fakturze koncowej/korygujacej).
    """
    zapytanie = (
        select(Faktura)
        .options(
            selectinload(Faktura.pozycje),
            joinedload(Faktura.klient).joinedload(Klient.firma),
            joinedload(Faktura.dokument_powiazany).selectinload(Faktura.pozycje),
        )
        .where(Faktura.id == faktura_id)
    )
    faktura = db.execute(zapytanie).unique().scalar_one_or_none()
    if faktura is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nie znaleziono faktury o podanym id.",
        )
    return faktura


def _zbuduj_kontekst(faktura: Faktura) -> dict:
    typ = faktura.typ_dokumentu
    pokaz_tabele_pozycji = typ != TypDokumentu.NOTA_KORYGUJACA
    pokaz_kolumny_vat = typ != TypDokumentu.RACHUNEK
    pokaz_podsumowanie_vat = typ not in TYPY_BEZ_PODSUMOWANIA_VAT

    zaliczka_wplacona_grosze = None
    pozostalo_do_zaplaty_grosze = None
    if typ == TypDokumentu.FAKTURA_KONCOWA and faktura.dokument_powiazany is not None:
        zaliczka_wplacona_grosze = faktura.dokument_powiazany.suma_brutto_grosze
        pozostalo_do_zaplaty_grosze = (
            faktura.suma_brutto_grosze - zaliczka_wplacona_grosze
        )

    return {
        "faktura": faktura,
        "firma": faktura.klient.firma,
        "klient": faktura.klient,
        "tytul_dokumentu": TYTULY_DOKUMENTU[typ],
        "pokaz_tabele_pozycji": pokaz_tabele_pozycji,
        "pokaz_kolumny_vat": pokaz_kolumny_vat,
        "pokaz_podsumowanie_vat": pokaz_podsumowanie_vat,
        "podsumowanie_vat": (
            podsumowanie_wg_stawek(faktura.pozycje) if pokaz_podsumowanie_vat else []
        ),
        "pokaz_dokument_powiazany": faktura.dokument_powiazany is not None,
        "pokaz_przyczyne_korekty": bool(faktura.przyczyna_korekty),
        "zaliczka_wplacona_grosze": zaliczka_wplacona_grosze,
        "pozostalo_do_zaplaty_grosze": pozostalo_do_zaplaty_grosze,
        "logo_uri": _logo_uri(faktura.klient.firma.logo_path),
    }


def generuj_pdf_faktury(
    db: Session, faktura_id: int, wariant: str = "klasyczny"
) -> tuple[bytes, str]:
    faktura = _pobierz_fakture_do_pdf(db, faktura_id)
    kontekst = _zbuduj_kontekst(faktura)
    szablon = _jinja_env.get_template(f"warianty/{wariant}.html")
    html = szablon.render(**kontekst)
    pdf_bytes = HTML(string=html, base_url=str(TEMPLATES_DIR)).write_pdf()
    return pdf_bytes, faktura.numer
