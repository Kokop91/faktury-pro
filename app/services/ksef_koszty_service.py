"""Pobieranie faktur kosztowych (zakupowych) z KSeF - Faza 12C.

ZRODLO: github.com/CIRFMF/ksef-api, plik pobieranie-faktur/pobieranie-faktur.md
i pobieranie-faktur/przyrostowe-pobieranie-faktur.md, zweryfikowane wprost z
opisow endpointow w openapi.json srodowiska testowego 2026-07-15.

Ministerstwo Finansow rekomenduje dla CIĄGŁEJ synchronizacji mechanizm
eksportu paczek (POST /invoices/exports) z High Water Mark - zaprojektowany
dla systemow dzialajacych 24/7, ktore musza gwarantowac zero pominietych
faktur przy duzych wolumenach. Ta appka jest desktopowa i sprawdza faktury
WYLACZNIE na zadanie uzytkownika (przycisk) lub opcjonalnie raz przy starcie -
dla takiego, niskoczestotliwosciowego uzycia dokumentacja opisuje prostsze,
synchroniczne zapytanie POST /invoices/query/metadata jako w pelni
wystarczajaca alternatywe (rowniez oficjalnie udokumentowana, nie obejscie).
Uzywamy wylacznie tego drugiego mechanizmu - bez szyfrowania/ZIP/HWM
wlasciwych eksportowi paczek.

Punkt startowy kolejnego sprawdzenia: MAX(data_trwalego_zapisu) z juz
pobranych dokumentow w naszej bazie (permanentStorageDate - jedyny typ daty
zalecany przez MF do przyrostowego pobierania, odporny na asynchroniczne
opoznienia przetwarzania). Brak wlasnych rekordow -> pierwsze sprawdzenie
cofa sie 30 dni.
"""
from datetime import date, datetime, timedelta, timezone
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import DokumentKosztowy, StatusDokumentuKosztowego
from app.services import firma as firma_service
from app.services.ksef_service import KsefBlad, _adres_bazowy, _uzyskaj_access_token, _wywolaj
from app.services.ksef_ustawienia import pobierz_dane_polaczenia_ksef

DOMYSLNE_OKNO_PIERWSZE_SPRAWDZENIE_DNI = 30
# KSeF: maksymalny dozwolony zakres jednego zapytania metadanych to 3 miesiace.
MAX_DNI_OKNA_ZAPYTANIA = 89
ROZMIAR_STRONY = 100
# Zabezpieczenie przed nieskonczona petla, nie realistyczny limit biznesowy.
MAX_STRON_NA_OKNO = 200


def _grosze(kwota: float) -> int:
    return int((Decimal(str(kwota)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _ostatnia_data_trwalego_zapisu(db: Session) -> datetime | None:
    return db.execute(select(func.max(DokumentKosztowy.data_trwalego_zapisu))).scalar_one_or_none()


def _pobierz_strone_metadanych(
    base_url: str, naglowki: dict, od: datetime, do: datetime, page_offset: int
) -> dict:
    return _wywolaj(
        "POST",
        f"{base_url}/invoices/query/metadata",
        headers=naglowki,
        params={"pageOffset": page_offset, "pageSize": ROZMIAR_STRONY, "sortOrder": "Asc"},
        json={
            "subjectType": "Subject2",
            "dateRange": {
                "dateType": "PermanentStorage",
                "from": od.isoformat(),
                "to": do.isoformat(),
            },
        },
    ).json()


def pobierz_nowe_faktury_kosztowe(db: Session) -> dict:
    """Sprawdza w KSeF nowe faktury kosztowe (wystawione na NIP naszej firmy
    jako Podmiot2/nabywca) od ostatniego sprawdzenia i zapisuje je lokalnie
    (status NOWA). Wolane recznie (przycisk) albo opcjonalnie raz przy
    starcie appki (ustawienie sprawdzaj_koszty_przy_starcie) - NIGDY w tle
    cyklicznie, appka desktopowa nie dziala 24/7."""
    firma = firma_service.pobierz_firme(db)

    token, srodowisko = pobierz_dane_polaczenia_ksef()
    if not token:
        raise HTTPException(
            status_code=400,
            detail="Brak zapisanego tokena KSeF - wprowadź go w Ustawieniach.",
        )
    base_url = _adres_bazowy(srodowisko)

    try:
        access_token = _uzyskaj_access_token(base_url, token, firma.nip)
    except KsefBlad as e:
        return {"powodzenie": False, "komunikat": e.komunikat, "liczba_nowych": 0}

    naglowki = {"Authorization": f"Bearer {access_token}"}

    okno_od = _ostatnia_data_trwalego_zapisu(db)
    if okno_od is None:
        okno_od = datetime.now(timezone.utc) - timedelta(days=DOMYSLNE_OKNO_PIERWSZE_SPRAWDZENIE_DNI)
    do_docelowe = datetime.now(timezone.utc)

    istniejace_numery_ksef = set(db.execute(select(DokumentKosztowy.numer_ksef)).scalars().all())
    nowe_metadane: list[dict] = []

    try:
        while okno_od < do_docelowe:
            okno_do = min(okno_od + timedelta(days=MAX_DNI_OKNA_ZAPYTANIA), do_docelowe)
            page_offset = 0
            for _ in range(MAX_STRON_NA_OKNO):
                odp = _pobierz_strone_metadanych(base_url, naglowki, okno_od, okno_do, page_offset)
                for metadana in odp.get("invoices", []):
                    numer_ksef = metadana["ksefNumber"]
                    if numer_ksef not in istniejace_numery_ksef:
                        nowe_metadane.append(metadana)
                        istniejace_numery_ksef.add(numer_ksef)
                if odp.get("isTruncated"):
                    raise KsefBlad(
                        "Zbyt dużo faktur kosztowych w jednym oknie czasowym "
                        "(osiągnięto limit KSeF: 10 000 rekordów) - skontaktuj się, "
                        "żeby zawęzić zakres sprawdzania ręcznie."
                    )
                if not odp.get("hasMore"):
                    break
                page_offset += ROZMIAR_STRONY
            okno_od = okno_do

        for metadana in nowe_metadane:
            sprzedawca = metadana.get("seller") or {}
            db.add(
                DokumentKosztowy(
                    firma_id=firma.id,
                    kontrahent_nazwa=sprzedawca.get("name"),
                    kontrahent_nip=sprzedawca.get("nip"),
                    numer_faktury=metadana["invoiceNumber"],
                    numer_ksef=metadana["ksefNumber"],
                    data_wystawienia=date.fromisoformat(metadana["issueDate"]),
                    data_trwalego_zapisu=datetime.fromisoformat(metadana["permanentStorageDate"]),
                    waluta=metadana["currency"],
                    netto_grosze=_grosze(metadana["netAmount"]),
                    brutto_grosze=_grosze(metadana["grossAmount"]),
                    vat_grosze_pln=_grosze(metadana["vatAmount"]),
                    xml_oryginalny=_wywolaj(
                        "GET",
                        f"{base_url}/invoices/ksef/{metadana['ksefNumber']}",
                        headers=naglowki,
                    ).text,
                    status=StatusDokumentuKosztowego.NOWA,
                )
            )
        db.commit()
    except KsefBlad as e:
        db.rollback()
        return {"powodzenie": False, "komunikat": e.komunikat, "liczba_nowych": 0}
    except (KeyError, TypeError) as e:
        db.rollback()
        return {
            "powodzenie": False,
            "komunikat": f"Nieoczekiwana odpowiedź KSeF (brak pola {e}).",
            "liczba_nowych": 0,
        }

    liczba = len(nowe_metadane)
    komunikat = (
        f"Znaleziono {liczba} nowych faktur kosztowych."
        if liczba
        else "Brak nowych faktur kosztowych."
    )
    return {"powodzenie": True, "komunikat": komunikat, "liczba_nowych": liczba}
