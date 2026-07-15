import requests

BASE_URL = "http://127.0.0.1:8000"
TIMEOUT_ODCZYT = 5.0
TIMEOUT_ZAPIS = 10.0
TIMEOUT_PDF = 30.0


class ApiError(Exception):
    def __init__(self, komunikat: str, status_code: int | None = None):
        super().__init__(komunikat)
        self.komunikat = komunikat
        self.status_code = status_code


def _sformatuj_blad(odpowiedz: requests.Response) -> str:
    try:
        dane = odpowiedz.json()
    except ValueError:
        return f"Serwer zwrócił błąd ({odpowiedz.status_code})."

    detail = dane.get("detail") if isinstance(dane, dict) else None

    if isinstance(detail, str):
        return detail

    if isinstance(detail, list):
        komunikaty = []
        for blad in detail:
            if not isinstance(blad, dict):
                komunikaty.append(str(blad))
                continue
            komunikat = str(blad.get("msg", blad))
            # Pydantic v2 dokleja "Value error, " przed komunikatem z ValueError
            # rzucanym w field_validator/model_validator - usuwamy dla czytelnosci.
            if komunikat.startswith("Value error, "):
                komunikat = komunikat[len("Value error, ") :]
            lokalizacja = [
                str(czesc) for czesc in blad.get("loc", []) if czesc != "body"
            ]
            if lokalizacja:
                komunikaty.append(f"{'.'.join(lokalizacja)}: {komunikat}")
            else:
                komunikaty.append(komunikat)
        if komunikaty:
            return "\n".join(komunikaty)

    return f"Serwer zwrócił błąd ({odpowiedz.status_code})."


def _wykonaj(metoda: str, sciezka: str, timeout: float, **kwargs) -> requests.Response:
    try:
        odpowiedz = requests.request(
            metoda, f"{BASE_URL}{sciezka}", timeout=timeout, **kwargs
        )
    except requests.exceptions.ConnectionError as e:
        raise ApiError(
            "Nie można połączyć się z serwerem aplikacji. "
            "Sprawdź, czy aplikacja działa poprawnie."
        ) from e
    except requests.exceptions.Timeout as e:
        raise ApiError(
            "Serwer aplikacji nie odpowiedział w wyznaczonym czasie."
        ) from e
    except requests.exceptions.RequestException as e:
        raise ApiError(f"Błąd komunikacji z serwerem aplikacji: {e}") from e

    if odpowiedz.status_code >= 400:
        raise ApiError(_sformatuj_blad(odpowiedz), status_code=odpowiedz.status_code)

    return odpowiedz


def pobierz_faktury(
    status: str | None = None,
    klient_id: int | None = None,
    skip: int = 0,
    limit: int = 200,
) -> list[dict]:
    parametry = {"skip": skip, "limit": limit}
    if status:
        parametry["status"] = status
    if klient_id is not None:
        parametry["klient_id"] = klient_id
    return _wykonaj(
        "GET", "/faktury", TIMEOUT_ODCZYT, params=parametry
    ).json()


def pobierz_fakture(faktura_id: int) -> dict:
    return _wykonaj("GET", f"/faktury/{faktura_id}", TIMEOUT_ODCZYT).json()


def pobierz_klientow(
    tylko_aktywni: bool = True, skip: int = 0, limit: int = 200
) -> list[dict]:
    parametry = {"tylko_aktywni": tylko_aktywni, "skip": skip, "limit": limit}
    return _wykonaj(
        "GET", "/klienci", TIMEOUT_ODCZYT, params=parametry
    ).json()


def pobierz_klienta(klient_id: int) -> dict:
    return _wykonaj("GET", f"/klienci/{klient_id}", TIMEOUT_ODCZYT).json()


def utworz_klienta(dane: dict) -> dict:
    return _wykonaj("POST", "/klienci", TIMEOUT_ZAPIS, json=dane).json()


def aktualizuj_klienta(klient_id: int, dane: dict) -> dict:
    return _wykonaj("PUT", f"/klienci/{klient_id}", TIMEOUT_ZAPIS, json=dane).json()


def usun_klienta(klient_id: int) -> None:
    # DELETE zwraca 204 bez tresci - nie wolno wolac .json() na tej odpowiedzi.
    _wykonaj("DELETE", f"/klienci/{klient_id}", TIMEOUT_ZAPIS)


def utworz_fakture(dane: dict) -> dict:
    return _wykonaj("POST", "/faktury", TIMEOUT_ZAPIS, json=dane).json()


def aktualizuj_fakture(faktura_id: int, dane: dict) -> dict:
    return _wykonaj("PUT", f"/faktury/{faktura_id}", TIMEOUT_ZAPIS, json=dane).json()


def zmien_status_faktury(faktura_id: int, status: str) -> dict:
    return _wykonaj(
        "PATCH", f"/faktury/{faktura_id}/status", TIMEOUT_ZAPIS, json={"status": status}
    ).json()


def pobierz_pdf_faktury(faktura_id: int) -> bytes:
    return _wykonaj("GET", f"/faktury/{faktura_id}/pdf", TIMEOUT_PDF).content


def pobierz_platnosci_faktury(faktura_id: int) -> list[dict]:
    return _wykonaj(
        "GET", f"/faktury/{faktura_id}/platnosci", TIMEOUT_ODCZYT
    ).json()


def dodaj_platnosc(faktura_id: int, dane: dict) -> dict:
    return _wykonaj(
        "POST", f"/faktury/{faktura_id}/platnosci", TIMEOUT_ZAPIS, json=dane
    ).json()


def pobierz_naleznosci() -> dict:
    return _wykonaj("GET", "/faktury/naleznosci", TIMEOUT_ODCZYT).json()


def pobierz_produkty(
    tylko_aktywne: bool = True, skip: int = 0, limit: int = 200
) -> list[dict]:
    parametry = {"tylko_aktywne": tylko_aktywne, "skip": skip, "limit": limit}
    return _wykonaj("GET", "/produkty", TIMEOUT_ODCZYT, params=parametry).json()


def pobierz_produkt(produkt_id: int) -> dict:
    return _wykonaj("GET", f"/produkty/{produkt_id}", TIMEOUT_ODCZYT).json()


def utworz_produkt(dane: dict) -> dict:
    return _wykonaj("POST", "/produkty", TIMEOUT_ZAPIS, json=dane).json()


def pobierz_historie_ruchow_produktu(produkt_id: int) -> list[dict]:
    return _wykonaj(
        "GET", f"/produkty/{produkt_id}/historia-ruchow", TIMEOUT_ODCZYT
    ).json()


def pobierz_magazyny(
    tylko_aktywne: bool = True, skip: int = 0, limit: int = 200
) -> list[dict]:
    parametry = {"tylko_aktywne": tylko_aktywne, "skip": skip, "limit": limit}
    return _wykonaj("GET", "/magazyny", TIMEOUT_ODCZYT, params=parametry).json()


def utworz_magazyn(dane: dict) -> dict:
    return _wykonaj("POST", "/magazyny", TIMEOUT_ZAPIS, json=dane).json()


def pobierz_dokumenty_magazynowe(
    typ: str | None = None,
    magazyn_id: int | None = None,
    data_od: str | None = None,
    data_do: str | None = None,
    skip: int = 0,
    limit: int = 200,
) -> list[dict]:
    parametry: dict = {"skip": skip, "limit": limit}
    if typ:
        parametry["typ"] = typ
    if magazyn_id is not None:
        parametry["magazyn_id"] = magazyn_id
    if data_od:
        parametry["data_od"] = data_od
    if data_do:
        parametry["data_do"] = data_do
    return _wykonaj(
        "GET", "/dokumenty-magazynowe", TIMEOUT_ODCZYT, params=parametry
    ).json()


def pobierz_dokument_magazynowy(dokument_id: int) -> dict:
    return _wykonaj(
        "GET", f"/dokumenty-magazynowe/{dokument_id}", TIMEOUT_ODCZYT
    ).json()


def utworz_dokument_magazynowy(dane: dict) -> dict:
    return _wykonaj(
        "POST", "/dokumenty-magazynowe", TIMEOUT_ZAPIS, json=dane
    ).json()


def pobierz_stany_magazynowe(magazyn_id: int | None = None) -> list[dict]:
    parametry = {}
    if magazyn_id is not None:
        parametry["magazyn_id"] = magazyn_id
    return _wykonaj(
        "GET", "/stany-magazynowe", TIMEOUT_ODCZYT, params=parametry
    ).json()


def pobierz_inwentaryzacje(
    magazyn_id: int | None = None,
    status: str | None = None,
    skip: int = 0,
    limit: int = 200,
) -> list[dict]:
    parametry: dict = {"skip": skip, "limit": limit}
    if magazyn_id is not None:
        parametry["magazyn_id"] = magazyn_id
    if status:
        parametry["status"] = status
    return _wykonaj(
        "GET", "/inwentaryzacje", TIMEOUT_ODCZYT, params=parametry
    ).json()


def pobierz_inwentaryzacje_szczegoly(inwentaryzacja_id: int) -> dict:
    return _wykonaj(
        "GET", f"/inwentaryzacje/{inwentaryzacja_id}", TIMEOUT_ODCZYT
    ).json()


def utworz_inwentaryzacje(magazyn_id: int) -> dict:
    return _wykonaj(
        "POST", "/inwentaryzacje", TIMEOUT_ZAPIS, json={"magazyn_id": magazyn_id}
    ).json()


def zapisz_pozycje_inwentaryzacji(inwentaryzacja_id: int, pozycje: list[dict]) -> dict:
    return _wykonaj(
        "PUT",
        f"/inwentaryzacje/{inwentaryzacja_id}/pozycje",
        TIMEOUT_ZAPIS,
        json={"pozycje": pozycje},
    ).json()


def zamknij_inwentaryzacje(inwentaryzacja_id: int) -> dict:
    return _wykonaj(
        "POST", f"/inwentaryzacje/{inwentaryzacja_id}/zamknij", TIMEOUT_ZAPIS
    ).json()


def pobierz_raport_historii_ruchow(
    magazyn_id: int | None = None,
    data_od: str | None = None,
    data_do: str | None = None,
) -> list[dict]:
    parametry: dict = {}
    if magazyn_id is not None:
        parametry["magazyn_id"] = magazyn_id
    if data_od:
        parametry["data_od"] = data_od
    if data_do:
        parametry["data_do"] = data_do
    return _wykonaj(
        "GET", "/raporty/historia-ruchow", TIMEOUT_ODCZYT, params=parametry
    ).json()


def pobierz_raport_ponizej_minimum(magazyn_id: int | None = None) -> list[dict]:
    parametry: dict = {}
    if magazyn_id is not None:
        parametry["magazyn_id"] = magazyn_id
    return _wykonaj(
        "GET", "/raporty/ponizej-minimum", TIMEOUT_ODCZYT, params=parametry
    ).json()


def sprawdz_gotowosc_jpk(rok: int, miesiac: int) -> dict:
    return _wykonaj(
        "GET",
        "/raporty/jpk-v7/sprawdz",
        TIMEOUT_ODCZYT,
        params={"rok": rok, "miesiac": miesiac},
    ).json()


def pobierz_jpk_v7(rok: int, miesiac: int, wariant: str) -> bytes:
    return _wykonaj(
        "GET",
        "/raporty/jpk-v7",
        TIMEOUT_PDF,
        params={"rok": rok, "miesiac": miesiac, "wariant": wariant},
    ).content


def pobierz_dashboard() -> dict:
    return _wykonaj("GET", "/dashboard", TIMEOUT_ODCZYT).json()


def pobierz_firme() -> dict:
    return _wykonaj("GET", "/firma", TIMEOUT_ODCZYT).json()


def utworz_firme(dane: dict) -> dict:
    return _wykonaj("POST", "/firma", TIMEOUT_ZAPIS, json=dane).json()


def aktualizuj_firme(dane: dict) -> dict:
    return _wykonaj("PUT", "/firma", TIMEOUT_ZAPIS, json=dane).json()


def pobierz_urzedy_skarbowe() -> list[dict]:
    return _wykonaj("GET", "/firma/urzedy-skarbowe", TIMEOUT_ODCZYT).json()


# -- integracje zewnetrzne (Faza 14: GUS, NBP, biala lista VAT) --------------
# Wywolania zewnetrznych API (przez backend) moga trwac dluzej niz lokalne
# zapytania do wlasnego serwera - stad wlasny, dluzszy timeout.
TIMEOUT_INTEGRACJA = 15.0


def pobierz_ustawienia_gus() -> dict:
    return _wykonaj("GET", "/integracje/gus/ustawienia", TIMEOUT_ODCZYT).json()


def zapisz_ustawienia_gus(dane: dict) -> dict:
    return _wykonaj(
        "PUT", "/integracje/gus/ustawienia", TIMEOUT_ZAPIS, json=dane
    ).json()


def szukaj_w_gus(nip: str) -> dict:
    return _wykonaj(
        "GET", "/integracje/gus/szukaj", TIMEOUT_INTEGRACJA, params={"nip": nip}
    ).json()


def pobierz_kurs_nbp(waluta: str, data_wystawienia: str) -> dict:
    return _wykonaj(
        "GET",
        "/integracje/nbp/kurs",
        TIMEOUT_INTEGRACJA,
        params={"waluta": waluta, "data_wystawienia": data_wystawienia},
    ).json()


def sprawdz_biala_liste(
    nip: str,
    numer_konta: str | None = None,
    klient_id: int | None = None,
    faktura_id: int | None = None,
) -> dict:
    dane = {"nip": nip}
    if numer_konta:
        dane["numer_konta"] = numer_konta
    if klient_id is not None:
        dane["klient_id"] = klient_id
    if faktura_id is not None:
        dane["faktura_id"] = faktura_id
    return _wykonaj(
        "POST", "/integracje/biala-lista/sprawdz", TIMEOUT_INTEGRACJA, json=dane
    ).json()


def historia_bialej_listy_klienta(klient_id: int) -> list[dict]:
    return _wykonaj(
        "GET", f"/integracje/biala-lista/klient/{klient_id}", TIMEOUT_ODCZYT
    ).json()


def historia_bialej_listy_faktury(faktura_id: int) -> list[dict]:
    return _wykonaj(
        "GET", f"/integracje/biala-lista/faktura/{faktura_id}", TIMEOUT_ODCZYT
    ).json()


# -- faktury cykliczne (Faza 15) ---------------------------------------------


def pobierz_szablony_cykliczne(tylko_aktywne: bool = False) -> list[dict]:
    return _wykonaj(
        "GET",
        "/faktury-cykliczne",
        TIMEOUT_ODCZYT,
        params={"tylko_aktywne": tylko_aktywne},
    ).json()


def pobierz_szablon_cykliczny(szablon_id: int) -> dict:
    return _wykonaj("GET", f"/faktury-cykliczne/{szablon_id}", TIMEOUT_ODCZYT).json()


def utworz_szablon_cykliczny(dane: dict) -> dict:
    return _wykonaj("POST", "/faktury-cykliczne", TIMEOUT_ZAPIS, json=dane).json()


def aktualizuj_szablon_cykliczny(szablon_id: int, dane: dict) -> dict:
    return _wykonaj(
        "PUT", f"/faktury-cykliczne/{szablon_id}", TIMEOUT_ZAPIS, json=dane
    ).json()


def zmien_status_szablonu_cyklicznego(szablon_id: int, status: str) -> dict:
    return _wykonaj(
        "PATCH",
        f"/faktury-cykliczne/{szablon_id}/status",
        TIMEOUT_ZAPIS,
        json={"status": status},
    ).json()


def historia_faktur_szablonu(szablon_id: int) -> list[dict]:
    return _wykonaj(
        "GET", f"/faktury-cykliczne/{szablon_id}/faktury", TIMEOUT_ODCZYT
    ).json()


def pobierz_zalegle_faktury_cykliczne() -> list[dict]:
    return _wykonaj("GET", "/faktury-cykliczne/zalegle", TIMEOUT_ODCZYT).json()


def generuj_faktury_cykliczne(pozycje: list[dict] | None = None) -> list[dict]:
    """`pozycje`: lista {"szablon_id": int, "okres": "RRRR-MM-DD"} do
    wygenerowania, albo None - wtedy generowane sa WSZYSTKIE aktualnie
    zalegle terminy wszystkich aktywnych szablonow."""
    dane = {"pozycje": pozycje} if pozycje is not None else {}
    return _wykonaj(
        "POST", "/faktury-cykliczne/generuj", TIMEOUT_ZAPIS, json=dane
    ).json()


# -- integracja KSeF (Faza 12A) -----------------------------------------------
# Pelny cykl uwierzytelnienia (challenge -> szyfrowanie -> ksef-token ->
# odpytywanie statusu -> redeem) moze potrwac dluzej niz zwykle wywolanie -
# stad wlasny, dluzszy timeout.
TIMEOUT_KSEF = 45.0


def pobierz_ustawienia_ksef() -> dict:
    return _wykonaj("GET", "/ksef/ustawienia", TIMEOUT_ODCZYT).json()


def zapisz_ustawienia_ksef(dane: dict) -> dict:
    return _wykonaj("PUT", "/ksef/ustawienia", TIMEOUT_ZAPIS, json=dane).json()


def testuj_polaczenie_ksef() -> dict:
    return _wykonaj("POST", "/ksef/testuj-polaczenie", TIMEOUT_KSEF).json()
