import re
from xml.etree import ElementTree as ET

import requests
from fastapi import HTTPException, status

from app.services.integracje_ustawienia import pobierz_dane_polaczenia_gus

WSDL_TESTOWE = "https://wyszukiwarkaregontest.stat.gov.pl/wsBIR/UslugaBIRzewnPubl.svc"
WSDL_PRODUKCYJNE = "https://wyszukiwarkaregon.stat.gov.pl/wsBIR/UslugaBIRzewnPubl.svc"
NS = "http://CIS/BIR/PUBL/2014/07"
TIMEOUT_S = 10.0
NIP_REGEX = re.compile(r"^\d{10}$")


def _adres_uslugi(srodowisko: str) -> str:
    return WSDL_PRODUKCYJNE if srodowisko == "produkcyjne" else WSDL_TESTOWE


def _wytnij_koperte(surowa_tresc: str) -> str:
    """Odpowiedz GUS przychodzi opakowana w MTOM (multipart/related), nie jako
    goly SOAP - zamiast parsowac naglowki MIME/granice multipart, wycinamy
    sama koperte SOAP (zawsze zaczyna sie od '<jakisPrefiks:Envelope' i
    konczy na 'Envelope>', niezaleznie od opakowania). Zweryfikowane na
    zywo przeciwko srodowisku testowemu GUS 2026-07-14."""
    poczatek_slowa = surowa_tresc.find("Envelope")
    znacznik_poczatku = surowa_tresc.rfind("<", 0, poczatek_slowa)
    koniec = surowa_tresc.rfind("Envelope>")
    if poczatek_slowa == -1 or znacznik_poczatku == -1 or koniec == -1:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Nieoczekiwana odpowiedź serwisu GUS.",
        )
    return surowa_tresc[znacznik_poczatku : koniec + len("Envelope>")]

def _wyslij_soap(url: str, action: str, cialo_body: str, sid: str | None = None) -> str:
    koperta = (
        f'<soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope" '
        f'xmlns:ns="{NS}" xmlns:dat="{NS}/DataContract">'
        f'<soap:Header xmlns:wsa="http://www.w3.org/2005/08/addressing">'
        f"<wsa:To>{url}</wsa:To>"
        f"<wsa:Action>{NS}/IUslugaBIRzewnPubl/{action}</wsa:Action>"
        f"</soap:Header>"
        f"<soap:Body>{cialo_body}</soap:Body>"
        f"</soap:Envelope>"
    )
    naglowki = {"Content-Type": "application/soap+xml; charset=utf-8"}
    if sid:
        naglowki["sid"] = sid

    try:
        odpowiedz = requests.post(
            url, data=koperta.encode("utf-8"), headers=naglowki, timeout=TIMEOUT_S
        )
    except requests.exceptions.RequestException as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Brak połączenia z serwisem GUS: {e}",
        ) from e

    if odpowiedz.status_code >= 400:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Serwis GUS zwrócił błąd ({odpowiedz.status_code}).",
        )

    # requests zgaduje kodowanie po naglowkach multipart, co przy MTOM czasem
    # wychodzi zle - dekodujemy surowe bajty jako UTF-8 recznie (GUS zawsze
    # zwraca UTF-8), zeby polskie znaki w nazwie/adresie nie byly uszkodzone.
    return _wytnij_koperte(odpowiedz.content.decode("utf-8"))


def _zaloguj(url: str, klucz: str) -> str:
    cialo = (
        f"<ns:Zaloguj><ns:pKluczUzytkownika>{klucz}</ns:pKluczUzytkownika></ns:Zaloguj>"
    )
    tekst = _wyslij_soap(url, "Zaloguj", cialo)
    root = ET.fromstring(tekst)
    element = root.find(f".//{{{NS}}}ZalogujResult")
    if element is None or not element.text:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Logowanie do GUS nie powiodło się (nieprawidłowy klucz API?).",
        )
    return element.text


def _pole(dane_el, nazwa: str) -> str | None:
    element = dane_el.find(nazwa)
    return element.text if element is not None and element.text else None


def _zbuduj_ulice(dane_el) -> str | None:
    ulica = _pole(dane_el, "Ulica")
    nr_nieruchomosci = _pole(dane_el, "NrNieruchomosci")
    nr_lokalu = _pole(dane_el, "NrLokalu")

    if not ulica and not nr_nieruchomosci:
        return None
    czesci = " ".join(czesc for czesc in (ulica, nr_nieruchomosci) if czesc)
    if nr_lokalu:
        czesci += f"/{nr_lokalu}"
    return czesci or None


def szukaj_po_nip(nip: str) -> dict | None:
    """Zwraca dane podmiotu z rejestru REGON gotowe do wypelnienia formularza
    (nazwa, ulica, kod_pocztowy, miejscowosc) albo None, jesli GUS nie
    znalazl podmiotu dla tego NIP. Srodowisko/klucz brane z lokalnych
    ustawien integracji (testowe domyslnie, patrz integracje_ustawienia.py)."""
    if not NIP_REGEX.match(nip):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="NIP musi się składać z dokładnie 10 cyfr.",
        )

    klucz, srodowisko = pobierz_dane_polaczenia_gus()
    url = _adres_uslugi(srodowisko)

    sid = _zaloguj(url, klucz)
    cialo = (
        "<ns:DaneSzukajPodmioty><ns:pParametryWyszukiwania>"
        f"<dat:Nip>{nip}</dat:Nip>"
        "</ns:pParametryWyszukiwania></ns:DaneSzukajPodmioty>"
    )
    tekst = _wyslij_soap(url, "DaneSzukajPodmioty", cialo, sid=sid)
    root = ET.fromstring(tekst)
    wynik_el = root.find(f".//{{{NS}}}DaneSzukajPodmiotyResult")
    if wynik_el is None or not wynik_el.text:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Nieoczekiwana odpowiedź serwisu GUS.",
        )

    wynik_root = ET.fromstring(wynik_el.text)
    dane_el = wynik_root.find("dane")
    if dane_el is None or dane_el.find("ErrorCode") is not None:
        return None

    return {
        "regon": _pole(dane_el, "Regon"),
        "nazwa": _pole(dane_el, "Nazwa"),
        "ulica": _zbuduj_ulice(dane_el),
        "kod_pocztowy": _pole(dane_el, "KodPocztowy"),
        "miejscowosc": _pole(dane_el, "Miejscowosc") or _pole(dane_el, "MiejscowoscPoczty"),
    }
