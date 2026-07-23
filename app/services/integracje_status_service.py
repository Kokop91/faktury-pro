"""Zbiorczy test dostepnosci czterech integracji zewnetrznych appki (NBP, Biala
Lista VAT, GUS, KSeF) - panel 'Sprawdz integracje' w Ustawieniach. Powstalo po
tym, jak integracja z GUS przestala dzialac CICHO (nikt sie nie dowiedzial, az
uzytkownik zglosil problem) - zamiast czekac na kolejne takie zgloszenie, appka
(i deweloper) moze to sprawdzic jednym klikniedziem/wywolaniem, zamiast czekac
az cos przestanie dzialac w praktyce.

Kazdy test jest LEKKI i NIE zapisuje nic do bazy (w odroznieniu od zwyklego
uzycia tych serwisow - np. sprawdz_nip normalnie tworzy wpis w historii
Bialej Listy) - to tylko sygnal "czy API w ogole odpowiada zgodnie z
oczekiwanym ksztaltem", nie prawdziwa operacja biznesowa."""

from datetime import date

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.schemas.integracje import StatusIntegracjiOut
from app.services import biala_lista_service, firma as firma_service, gus_service, ksef_service, nbp_service

# NIP Ministerstwa Finansow - stabilny, zawsze aktywny podmiot publiczny, uzywany
# WYLACZNIE jako fallback do testu polaczenia z Biala Lista, gdy appka nie ma
# jeszcze skonfigurowanych danych firmy (a wiec wlasnego NIP do przetestowania).
NIP_TESTOWY_BIALA_LISTA = "5260250274"

WALUTA_TESTOWA_NBP = "EUR"


def _status_nbp() -> StatusIntegracjiOut:
    try:
        kurs, data_efektywna = nbp_service.pobierz_kurs_przed_data(WALUTA_TESTOWA_NBP, date.today())
    except HTTPException as e:
        return StatusIntegracjiOut(nazwa="NBP (kursy walut)", dziala=False, komunikat=str(e.detail))
    return StatusIntegracjiOut(
        nazwa="NBP (kursy walut)",
        dziala=True,
        komunikat=f"Kurs {WALUTA_TESTOWA_NBP} z {data_efektywna.isoformat()}: {kurs}",
    )


def _status_biala_lista(db: Session) -> StatusIntegracjiOut:
    try:
        firma = firma_service.pobierz_firme(db)
        nip = firma.nip
    except HTTPException:
        nip = NIP_TESTOWY_BIALA_LISTA

    try:
        wynik = biala_lista_service.sprawdz_polaczenie(nip)
    except HTTPException as e:
        return StatusIntegracjiOut(nazwa="Biała Lista VAT (MF)", dziala=False, komunikat=str(e.detail))

    if not wynik["znaleziono"]:
        return StatusIntegracjiOut(
            nazwa="Biała Lista VAT (MF)",
            dziala=False,
            komunikat=f"Wykaz odpowiedział, ale nie znalazł podmiotu o NIP {nip}.",
        )
    return StatusIntegracjiOut(
        nazwa="Biała Lista VAT (MF)",
        dziala=True,
        komunikat=f"Zweryfikowano NIP {nip} ({wynik['nazwa_podmiotu']}).",
    )


def _status_gus() -> StatusIntegracjiOut:
    try:
        srodowisko = gus_service.sprawdz_polaczenie()
    except HTTPException as e:
        return StatusIntegracjiOut(nazwa="GUS / REGON", dziala=False, komunikat=str(e.detail))
    return StatusIntegracjiOut(
        nazwa="GUS / REGON", dziala=True, komunikat=f"Zalogowano poprawnie (środowisko {srodowisko})."
    )


def _status_ksef(db: Session) -> StatusIntegracjiOut:
    try:
        wynik = ksef_service.testuj_polaczenie(db)
    except HTTPException as e:
        # Brak danych firmy / brak zapisanego tokena - odrebny stan od "nie dziala",
        # bo appka jeszcze nie ma czego testowac, nie jest to usterka integracji.
        return StatusIntegracjiOut(nazwa="KSeF", dziala=None, komunikat=str(e.detail))
    return StatusIntegracjiOut(
        nazwa=f"KSeF (środowisko {wynik['srodowisko']})",
        dziala=wynik["powodzenie"],
        komunikat=wynik["komunikat"],
    )


def sprawdz_wszystkie(db: Session) -> list[StatusIntegracjiOut]:
    return [
        _status_nbp(),
        _status_biala_lista(db),
        _status_gus(),
        _status_ksef(db),
    ]
