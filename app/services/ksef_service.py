import base64
import os
import time

import requests
from cryptography.hazmat.primitives import hashes, padding as sym_padding
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.x509 import load_der_x509_certificate
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Faktura, Klient, StatusFaktury, StatusKsef
from app.services import firma as firma_service
from app.services.ksef_fa3_builder import (
    Fa3WalidacjaError,
    KsefKwalifikowalnoscError,
    sha256_base64,
    waliduj_fa3_xml,
    zbuduj_fa3_xml,
)
from app.services.ksef_ustawienia import pobierz_dane_polaczenia_ksef

# Adresy bazowe API KSeF 2.0 - zweryfikowane 2026-07-15 wprost z oficjalnego
# repozytorium Ministerstwa Finansow (github.com/CIRFMF/ksef-api, plik
# srodowiska.md, tabela srodowisk aktualna na 16.03.2026).
# TESTOWE: host + sciezka "/v2" potwierdzone bezposrednio z pola "servers"
# pobranego live z https://api-test.ksef.mf.gov.pl/docs/v2/openapi.json.
# PRODUKCYJNE: host "api.ksef.mf.gov.pl" potwierdzony wprost w srodowiska.md
# (kolumna "Dokumentacja API": https://api.ksef.mf.gov.pl/docs/v2); sam
# przyrostek "/v2" (a nie np. "/api/v2") wyprowadzony przez analoge do
# potwierdzonego wzorca TESTOWEGO, bo produkcyjny openapi.json nie byl
# niezaleznie pobrany. Jesli pierwszy test polaczenia produkcyjnego zwroci
# 404 zaraz na starcie (GET /security/public-key-certificates), to sygnal,
# ze ten przyrostek wymaga korekty - zglos to.
ADRESY_BAZOWE = {
    "testowe": "https://api-test.ksef.mf.gov.pl/v2",
    "produkcyjne": "https://api.ksef.mf.gov.pl/v2",
}

TIMEOUT_S = 15.0
LIMIT_OCZEKIWANIA_S = 30.0
ODSTEP_ODPYTYWANIA_S = 1.5

# Status faktury w sesji interaktywnej moze potrwac dluzej niz uwierzytelnienie
# (asynchroniczna weryfikacja XML + semantyki, patrz faktury/weryfikacja-faktury.md) -
# stad wlasny, dluzszy limit odpytywania.
LIMIT_OCZEKIWANIA_FAKTURY_S = 60.0

# Kody statusu faktury w sesji interaktywnej (SessionInvoiceStatusResponse.status.code) -
# zweryfikowane wprost z opisu pola w openapi.json srodowiska testowego 2026-07-15.
KOD_STATUSU_FAKTURY_W_TOKU = frozenset({100, 150})
KOD_STATUSU_FAKTURY_SUKCES = 200


class KsefBlad(Exception):
    def __init__(self, komunikat: str):
        super().__init__(komunikat)
        self.komunikat = komunikat


def _adres_bazowy(srodowisko: str) -> str:
    return ADRESY_BAZOWE[srodowisko]


def _opisz_blad_http(odpowiedz: requests.Response) -> str:
    try:
        dane = odpowiedz.json()
    except ValueError:
        return f"KSeF zwrócił nieoczekiwaną odpowiedź (HTTP {odpowiedz.status_code})."

    wyjatek = dane.get("exception") if isinstance(dane, dict) else None
    if isinstance(wyjatek, dict):
        lista = wyjatek.get("exceptionDetailList") or []
        opisy = [
            str(w.get("exceptionDescription", "")).strip()
            for w in lista
            if w.get("exceptionDescription")
        ]
        if opisy:
            return "; ".join(opisy)

    return f"KSeF zwrócił błąd (HTTP {odpowiedz.status_code})."


def _wywolaj(metoda: str, url: str, **kwargs) -> requests.Response:
    try:
        odpowiedz = requests.request(metoda, url, timeout=TIMEOUT_S, **kwargs)
    except requests.exceptions.RequestException as e:
        raise KsefBlad(f"Brak połączenia z serwerem KSeF: {e}") from e

    if odpowiedz.status_code >= 400:
        raise KsefBlad(_opisz_blad_http(odpowiedz))

    return odpowiedz


def _pobierz_klucz_szyfrowania(base_url: str, usage: str) -> tuple[str, str]:
    """Zwraca (certyfikat_der_b64, publicKeyId) klucza publicznego KSeF o
    podanym przeznaczeniu (`usage` = "KsefTokenEncryption" przy uwierzytelnianiu
    tokenem, "SymmetricKeyEncryption" przy szyfrowaniu faktury w sesji
    interaktywnej), patrz GET /security/public-key-certificates."""
    odpowiedz = _wywolaj("GET", f"{base_url}/security/public-key-certificates")
    certyfikaty = odpowiedz.json()
    for cert in certyfikaty:
        if usage in (cert.get("usage") or []):
            return cert["certificate"], cert["publicKeyId"]
    raise KsefBlad(f"KSeF nie zwrócił klucza publicznego do szyfrowania ({usage}).")


def _szyfruj_rsa_oaep_sha256(tresc: bytes, certyfikat_der_b64: str) -> str:
    certyfikat = load_der_x509_certificate(base64.b64decode(certyfikat_der_b64))
    klucz_publiczny = certyfikat.public_key()
    szyfrogram = klucz_publiczny.encrypt(
        tresc,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return base64.b64encode(szyfrogram).decode("ascii")


def _uwierzytelnij_tokenem(base_url: str, token: str, nip: str) -> str:
    """Pelny cykl uwierzytelnienia tokenem KSeF: challenge, zaszyfrowanie
    tokena, /auth/ksef-token, odpytywanie statusu, /auth/token/redeem. Zwraca
    swiezy `authenticationToken` (tymczasowy JWT operacji uwierzytelnienia,
    NIE accessToken) wraz z numerem referencyjnym - do uzycia w
    _uzyskaj_access_token pon izej. Rzuca KsefBlad przy kazdym niepowodzeniu."""
    certyfikat_der_b64, public_key_id = _pobierz_klucz_szyfrowania(
        base_url, "KsefTokenEncryption"
    )

    challenge_odp = _wywolaj("POST", f"{base_url}/auth/challenge").json()
    challenge = challenge_odp["challenge"]
    timestamp_ms = challenge_odp["timestampMs"]

    encrypted_token = _szyfruj_rsa_oaep_sha256(
        f"{token}|{timestamp_ms}".encode("utf-8"), certyfikat_der_b64
    )

    inicjacja = _wywolaj(
        "POST",
        f"{base_url}/auth/ksef-token",
        json={
            "challenge": challenge,
            "contextIdentifier": {"type": "Nip", "value": nip},
            "encryptedToken": encrypted_token,
            "publicKeyId": public_key_id,
        },
    ).json()

    reference_number = inicjacja["referenceNumber"]
    auth_token = inicjacja["authenticationToken"]["token"]
    naglowki = {"Authorization": f"Bearer {auth_token}"}

    uplynelo_s = 0.0
    status_info = None
    while uplynelo_s < LIMIT_OCZEKIWANIA_S:
        status_odp = _wywolaj(
            "GET", f"{base_url}/auth/{reference_number}", headers=naglowki
        ).json()
        status_info = status_odp["status"]
        if status_info["code"] != 100:
            break
        time.sleep(ODSTEP_ODPYTYWANIA_S)
        uplynelo_s += ODSTEP_ODPYTYWANIA_S
    else:
        raise KsefBlad(
            "Przekroczono czas oczekiwania na potwierdzenie uwierzytelnienia przez KSeF."
        )

    if status_info["code"] != 200:
        szczegoly = "; ".join(status_info.get("details") or [])
        opis = status_info.get("description", "Uwierzytelnianie nieudane.")
        raise KsefBlad(opis + (f" ({szczegoly})" if szczegoly else ""))

    return auth_token


def _uzyskaj_access_token(base_url: str, token: str, nip: str) -> str:
    """Uwierzytelnia sie tokenem KSeF i od razu wymienia wynik na accessToken
    (/auth/token/redeem). accessToken zyje tylko na czas tego wywolania -
    Faza 12B nie zarzadza sesjami dlugozyciowymi, kazda wysylka/test uzyskuje
    swiezy token."""
    auth_token = _uwierzytelnij_tokenem(base_url, token, nip)
    odpowiedz = _wywolaj(
        "POST",
        f"{base_url}/auth/token/redeem",
        headers={"Authorization": f"Bearer {auth_token}"},
    ).json()
    return odpowiedz["accessToken"]["token"]


def testuj_polaczenie(db: Session) -> dict:
    """Pelny cykl uwierzytelnienia tokenem KSeF - Faza 12A. Ma jedynie
    POTWIERDZIC, ze zapisany token dziala - accessToken/refreshToken NIE sa
    nigdzie zapisywane (wysylka faktur, Faza 12B, uzyskuje wlasny, swiezy
    token przy kazdej wysylce - patrz wyslij_fakture_do_ksef)."""
    firma = firma_service.pobierz_firme(db)  # zglasza czytelny HTTPException, jesli brak danych firmy

    token, srodowisko = pobierz_dane_polaczenia_ksef()
    if not token:
        raise HTTPException(
            status_code=400,
            detail="Brak zapisanego tokena KSeF - wprowadź go w Ustawieniach.",
        )

    base_url = _adres_bazowy(srodowisko)

    try:
        _uzyskaj_access_token(base_url, token, firma.nip)
    except KsefBlad as e:
        return {"powodzenie": False, "komunikat": e.komunikat, "srodowisko": srodowisko}
    except (KeyError, TypeError) as e:
        return {
            "powodzenie": False,
            "komunikat": f"Nieoczekiwana odpowiedź KSeF (brak pola {e}).",
            "srodowisko": srodowisko,
        }

    return {
        "powodzenie": True,
        "komunikat": "Połączono poprawnie - token KSeF jest aktywny.",
        "srodowisko": srodowisko,
    }


# -- Faza 12B: wysylka faktury (sesja interaktywna) --------------------------

STATUSY_FAKTURY_NIEWYSYLALNE = frozenset({StatusFaktury.ROBOCZA, StatusFaktury.ANULOWANA})


def _pobierz_fakture_z_relacjami(db: Session, faktura_id: int) -> Faktura:
    zapytanie = (
        select(Faktura)
        .options(
            selectinload(Faktura.pozycje),
            selectinload(Faktura.klient).selectinload(Klient.firma),
            selectinload(Faktura.dokument_powiazany),
        )
        .where(Faktura.id == faktura_id)
    )
    faktura = db.execute(zapytanie).scalar_one_or_none()
    if faktura is None:
        raise HTTPException(status_code=404, detail="Nie znaleziono faktury o podanym id.")
    return faktura


def _zaszyfruj_aes256_cbc(dane: bytes, klucz: bytes, iv: bytes) -> bytes:
    """AES-256-CBC z dopelnieniem PKCS#7, zgodnie z dokumentacja MF
    (sesja-interaktywna.md) - uzywane do szyfrowania tresci faktury XML."""
    dopelniacz = sym_padding.PKCS7(algorithms.AES.block_size).padder()
    dane_dopelnione = dopelniacz.update(dane) + dopelniacz.finalize()
    szyfr = Cipher(algorithms.AES(klucz), modes.CBC(iv)).encryptor()
    return szyfr.update(dane_dopelnione) + szyfr.finalize()


def _pobierz_upo(base_url: str, naglowki: dict, session_ref: str, invoice_ref: str) -> str:
    odpowiedz = _wywolaj(
        "GET",
        f"{base_url}/sessions/{session_ref}/invoices/{invoice_ref}/upo",
        headers=naglowki,
    )
    return odpowiedz.text


def wyslij_fakture_do_ksef(
    db: Session,
    faktura_id: int,
    *,
    access_token: str | None = None,
    base_url: str | None = None,
) -> dict:
    """Wysyla pojedyncza fakture do KSeF sesja interaktywna: buduje i waliduje
    FA(3) (ksef_fa3_builder), otwiera sesje, szyfruje i wysyla dokument,
    zamyka sesje, odpytuje status pojedynczej faktury i - jesli przyjeta -
    pobiera UPO. Wynik (numer KSeF / UPO / przyczyna odrzucenia) jest
    zapisywany na rekordzie Faktura niezaleznie od wyniku.

    `access_token`/`base_url` - jesli podane (wysylka zbiorcza, patrz
    wyslij_faktury_zbiorczo), pomija wlasne uwierzytelnienie i uzywa
    JUZ uzyskanego accessToken - zeby wysylka wielu faktur naraz nie
    uwierzytelniala sie od nowa dla kazdej z osobna."""
    faktura = _pobierz_fakture_z_relacjami(db, faktura_id)

    if faktura.status in STATUSY_FAKTURY_NIEWYSYLALNE:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Nie można wysłać do KSeF faktury w statusie '{faktura.status.value}'."
            ),
        )
    if faktura.status_ksef == StatusKsef.PRZYJETA:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Faktura została już przyjęta przez KSeF (numer {faktura.numer_ksef})."
            ),
        )

    try:
        xml_bytes = zbuduj_fa3_xml(faktura)
        waliduj_fa3_xml(xml_bytes)
    except KsefKwalifikowalnoscError as e:
        return {"powodzenie": False, "komunikat": str(e), "status_ksef": faktura.status_ksef.value}
    except Fa3WalidacjaError as e:
        komunikat = "Dokument nie przeszedł walidacji względem schematu FA(3): " + "; ".join(e.bledy)
        return {"powodzenie": False, "komunikat": komunikat, "status_ksef": faktura.status_ksef.value}

    token = firma = None
    if access_token is None:
        token, srodowisko = pobierz_dane_polaczenia_ksef()
        if not token:
            raise HTTPException(
                status_code=400,
                detail="Brak zapisanego tokena KSeF - wprowadź go w Ustawieniach.",
            )
        firma = firma_service.pobierz_firme(db)
        base_url = _adres_bazowy(srodowisko)

    faktura.status_ksef = StatusKsef.WYSYLANIE_W_TOKU
    db.commit()

    try:
        if access_token is None:
            access_token = _uzyskaj_access_token(base_url, token, firma.nip)
        naglowki = {"Authorization": f"Bearer {access_token}"}

        klucz_symetryczny = os.urandom(32)
        iv = os.urandom(16)
        cert_sym_b64, sym_key_id = _pobierz_klucz_szyfrowania(base_url, "SymmetricKeyEncryption")
        encrypted_symmetric_key = _szyfruj_rsa_oaep_sha256(klucz_symetryczny, cert_sym_b64)

        sesja = _wywolaj(
            "POST",
            f"{base_url}/sessions/online",
            headers=naglowki,
            json={
                "formCode": {"systemCode": "FA (3)", "schemaVersion": "1-0E", "value": "FA"},
                "encryption": {
                    "encryptedSymmetricKey": encrypted_symmetric_key,
                    "initializationVector": base64.b64encode(iv).decode("ascii"),
                    "publicKeyId": sym_key_id,
                },
            },
        ).json()
        session_ref = sesja["referenceNumber"]

        zaszyfrowana_faktura = _zaszyfruj_aes256_cbc(xml_bytes, klucz_symetryczny, iv)

        wyslanie = _wywolaj(
            "POST",
            f"{base_url}/sessions/online/{session_ref}/invoices",
            headers=naglowki,
            json={
                "invoiceHash": sha256_base64(xml_bytes),
                "invoiceSize": len(xml_bytes),
                "encryptedInvoiceHash": sha256_base64(zaszyfrowana_faktura),
                "encryptedInvoiceSize": len(zaszyfrowana_faktura),
                "encryptedInvoiceContent": base64.b64encode(zaszyfrowana_faktura).decode("ascii"),
            },
        ).json()
        invoice_ref = wyslanie["referenceNumber"]

        # Dokument dotarl juz do KSeF - zapisujemy numery referencyjne od razu,
        # zeby nawet przy dalszej awarii (timeout odpytywania, brak sieci przy
        # pobieraniu UPO) nie zgubic sladu, ze wysylka faktycznie sie odbyla.
        faktura.ksef_numer_ref_sesji = session_ref
        faktura.ksef_numer_ref_faktury = invoice_ref
        db.commit()

        _wywolaj("POST", f"{base_url}/sessions/online/{session_ref}/close", headers=naglowki)

        uplynelo_s = 0.0
        status_info = None
        while uplynelo_s < LIMIT_OCZEKIWANIA_FAKTURY_S:
            status_odp = _wywolaj(
                "GET",
                f"{base_url}/sessions/{session_ref}/invoices/{invoice_ref}",
                headers=naglowki,
            ).json()
            status_info = status_odp["status"]
            if status_info["code"] not in KOD_STATUSU_FAKTURY_W_TOKU:
                break
            time.sleep(ODSTEP_ODPYTYWANIA_S)
            uplynelo_s += ODSTEP_ODPYTYWANIA_S
        else:
            raise KsefBlad(
                "Faktura została wysłana do KSeF, ale przekroczono czas oczekiwania na "
                "wynik przetwarzania. Spróbuj sprawdzić status ponownie za chwilę."
            )

        if status_info["code"] == KOD_STATUSU_FAKTURY_SUKCES:
            numer_ksef = status_odp.get("ksefNumber")
            upo_xml = _pobierz_upo(base_url, naglowki, session_ref, invoice_ref)

            faktura.status_ksef = StatusKsef.PRZYJETA
            faktura.numer_ksef = numer_ksef
            faktura.upo_xml = upo_xml
            faktura.przyczyna_odrzucenia_ksef = None
            db.commit()

            return {
                "powodzenie": True,
                "komunikat": f"Faktura przyjęta przez KSeF (numer {numer_ksef}).",
                "status_ksef": faktura.status_ksef.value,
                "numer_ksef": numer_ksef,
            }

        szczegoly = "; ".join(status_info.get("details") or [])
        opis = status_info.get("description", "Faktura odrzucona przez KSeF.")
        komunikat = opis + (f" ({szczegoly})" if szczegoly else "")

        faktura.status_ksef = StatusKsef.ODRZUCONA
        faktura.przyczyna_odrzucenia_ksef = komunikat
        db.commit()

        return {
            "powodzenie": False,
            "komunikat": komunikat,
            "status_ksef": faktura.status_ksef.value,
        }

    except (KsefBlad, KeyError, TypeError) as e:
        komunikat = e.komunikat if isinstance(e, KsefBlad) else f"Nieoczekiwana odpowiedź KSeF (brak pola {e})."
        if faktura.ksef_numer_ref_faktury:
            # Dokument juz dotarl do KSeF, tylko nie znamy ostatecznego wyniku -
            # status pozostaje WYSYLANIE_W_TOKU (NIE nie_wyslana/odrzucona),
            # zeby nie zasugerowac czegos, czego nie wiemy na pewno.
            db.commit()
            return {
                "powodzenie": False,
                "komunikat": (
                    f"{komunikat} Faktura mogła już dotrzeć do KSeF (numer referencyjny "
                    f"{faktura.ksef_numer_ref_faktury}) - sprawdź status później."
                ),
                "status_ksef": faktura.status_ksef.value,
            }
        faktura.status_ksef = StatusKsef.NIE_WYSLANA
        db.commit()
        return {"powodzenie": False, "komunikat": komunikat, "status_ksef": faktura.status_ksef.value}


def wyslij_faktury_zbiorczo(db: Session, faktura_ids: list[int]) -> list[dict]:
    """Wysyla wiele faktur w jednym wywolaniu (Faza 12D) - uwierzytelnia sie
    RAZ (jeden accessToken wspoldzielony miedzy wszystkimi fakturami), zamiast
    wywolywac wyslij_fakture_do_ksef() osobno dla kazdej, co przy wiekszej
    liczbie faktur oznaczaloby tyle samo pelnych cykli uwierzytelnienia."""
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
        # Nie wiadomo, ktorej konkretnie faktury dotyczy blad uwierzytelnienia -
        # ten sam komunikat dla kazdej z zadanych pozycji, status bez zmian.
        return [
            {
                "faktura_id": faktura_id,
                "powodzenie": False,
                "komunikat": e.komunikat,
                "status_ksef": None,
                "numer_ksef": None,
            }
            for faktura_id in faktura_ids
        ]

    wyniki = []
    for faktura_id in faktura_ids:
        try:
            wynik = wyslij_fakture_do_ksef(
                db, faktura_id, access_token=access_token, base_url=base_url
            )
        except HTTPException as e:
            wynik = {"powodzenie": False, "komunikat": str(e.detail), "status_ksef": None}
        wynik["faktura_id"] = faktura_id
        wyniki.append(wynik)
    return wyniki
