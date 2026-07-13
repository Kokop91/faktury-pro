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
