import base64
import time

import requests
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509 import load_der_x509_certificate
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.services import firma as firma_service
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


def _pobierz_klucz_szyfrowania_tokena(base_url: str) -> tuple[str, str]:
    """Zwraca (certyfikat_der_b64, publicKeyId) klucza publicznego KSeF
    uzywanego do szyfrowania tokena przy uwierzytelnianiu
    (usage="KsefTokenEncryption", patrz GET /security/public-key-certificates)."""
    odpowiedz = _wywolaj("GET", f"{base_url}/security/public-key-certificates")
    certyfikaty = odpowiedz.json()
    for cert in certyfikaty:
        if "KsefTokenEncryption" in (cert.get("usage") or []):
            return cert["certificate"], cert["publicKeyId"]
    raise KsefBlad("KSeF nie zwrócił klucza publicznego do szyfrowania tokena.")


def _zaszyfruj_token(token: str, timestamp_ms: int, certyfikat_der_b64: str) -> str:
    """Format zgodny z dokumentacja MF (uwierzytelnianie.md): ciag
    "token|timestampMs" zaszyfrowany RSA-OAEP z SHA-256 (MGF1), zakodowany
    Base64."""
    certyfikat = load_der_x509_certificate(base64.b64decode(certyfikat_der_b64))
    klucz_publiczny = certyfikat.public_key()
    tresc = f"{token}|{timestamp_ms}".encode("utf-8")
    szyfrogram = klucz_publiczny.encrypt(
        tresc,
        padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None,
        ),
    )
    return base64.b64encode(szyfrogram).decode("ascii")


def testuj_polaczenie(db: Session) -> dict:
    """Pelny cykl uwierzytelnienia tokenem KSeF: pobranie klucza publicznego,
    challenge, zaszyfrowanie tokena, /auth/ksef-token, odpytywanie statusu,
    /auth/token/redeem. Faza 12A ma jedynie POTWIERDZIC, ze zapisany token
    dziala - accessToken/refreshToken z redeem NIE sa nigdzie zapisywane
    (wysylka faktur to kolejna faza, patrz ETAP_2_ROZWOJU.md)."""
    firma = firma_service.pobierz_firme(db)  # zglasza czytelny HTTPException, jesli brak danych firmy

    token, srodowisko = pobierz_dane_polaczenia_ksef()
    if not token:
        raise HTTPException(
            status_code=400,
            detail="Brak zapisanego tokena KSeF - wprowadź go w Ustawieniach.",
        )

    base_url = _adres_bazowy(srodowisko)

    try:
        certyfikat_der_b64, public_key_id = _pobierz_klucz_szyfrowania_tokena(base_url)

        challenge_odp = _wywolaj("POST", f"{base_url}/auth/challenge").json()
        challenge = challenge_odp["challenge"]
        timestamp_ms = challenge_odp["timestampMs"]

        encrypted_token = _zaszyfruj_token(token, timestamp_ms, certyfikat_der_b64)

        inicjacja = _wywolaj(
            "POST",
            f"{base_url}/auth/ksef-token",
            json={
                "challenge": challenge,
                "contextIdentifier": {"type": "Nip", "value": firma.nip},
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

        _wywolaj("POST", f"{base_url}/auth/token/redeem", headers=naglowki)

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
