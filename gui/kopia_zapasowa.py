"""Kopia zapasowa i przywracanie danych (Faza 22, Etap 4) - KRYTYCZNY priorytet:
appka przechowuje od Fazy 18B WSZYSTKIE dane firmy wylacznie lokalnie (prywatny
Postgres), bez zadnej kopii bezpieczenstwa. Awaria dysku = utrata dostepu do
danych, ktore polskie przepisy wymagaja przechowywac przez 5 lat.

Co obejmuje kopia (zweryfikowane w kodzie, nie zgadywane): appka NIE trzyma
wygenerowanych PDF-ow ani eksportow JPK jako plikow na dysku - sa generowane
na zadanie wprost z bazy (app/services/pdf.py, app/services/jpk_service.py) i
oddawane uzytkownikowi przez systemowe okno "Zapisz jako", nigdy zapisywane
przez appke samodzielnie. Podobnie UPO z KSeF (Faktura.upo_xml) i tresc
dokumentow kosztowych (DokumentKosztowy.xml_oryginalny) sa kolumnami w bazie,
nie osobnymi plikami. Jedynym plikiem powiazanym poza baza jest logo firmy
(gui/logo.py, %LOCALAPPDATA%/FakturyPro/logo/) - pelny dump bazy + ten
katalog razem daja komplet danych potrzebnych do identycznego odtworzenia appki.

Format pliku kopii (.fpbk):
  [4B] magic b"FPBK"
  [1B] wersja formatu (1)
  [16B] sol PBKDF2
  [reszta] token Fernet (AES-128-CBC + HMAC-SHA256) opakowujacy ZIP zawierajacy:
    - manifest.json (wersja, czas utworzenia, nazwa bazy)
    - baza.dump (pg_dump w formacie custom, -Fc)
    - logo/<plik> (jesli logo firmy istnieje)

Haslo szyfrowania jest CELOWO niezalezne od hasla appki (gui/auth.py) i
NIGDY nigdzie nie zapisywane (w odroznieniu od tokena KSeF, ktorego Faza 12A
zaszyfrowala DPAPI do lokalnego uzycia na TYM koncie/komputerze) - kopia
zapasowa musi byc mozliwa do odszyfrowania takze po awarii TEGO komputera
(nowy sprzet, nowe konto Windows), gdzie DPAPI-zaszyfrowany sekret zapisany
lokalnie i tak bylby bezuzyteczny. Uzytkownik jest odpowiedzialny za
zapamietanie/zapisanie hasla osobno - appka wyraznie to komunikuje w UI
(gui/windows/widok_ustawien.py).

Binaria klienckie Postgresa (pg_dump/pg_restore/psql) sa CZESCIA appki -
te same bundlowane pliki co postgres.exe/initdb.exe z Fazy 18B (patrz
gui/postgres_serwer.py), rozwiazywane przez app.sciezki.katalog_bazowy().
Uzywane niezaleznie od tego, czy appka dziala w trybie deweloperskim (baza
zarzadzana recznie) czy produktowym (prywatny Postgres) - w obu przypadkach
to zwykle narzedzia klienckie laczace sie po DATABASE_URL, ktore appka i tak
juz ma pod reka.
"""
import base64
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from app.sciezki import katalog_bazowy
from gui import logo, nastawienia

MAGIC = b"FPBK"
WERSJA_FORMATU = 1
DLUGOSC_SOLI = 16
ITERACJE_PBKDF2 = 600_000  # zalecenie OWASP (2023+) dla PBKDF2-HMAC-SHA256

KLUCZ_KATALOG_DOCELOWY = "backup_katalog_docelowy"
KLUCZ_OSTATNI_BACKUP = "backup_ostatni_udany"
PROG_DNI_PRZETERMINOWANIA = 7

# Bez tego pg_dump/pg_restore/psql moglyby "zawiesic sie" bez konca (np.
# katalog docelowy wskazuje na zerwany dysk sieciowy, zablokowana tabela) -
# watek w tle (uruchom_w_tle) nigdy by sie nie zakonczyl, przycisk zostalby
# na stale "Wykonywanie kopii zapasowej.../Przywracanie danych..." bez zadnego
# komunikatu. Hojny limit (dump/restore faktycznie przenosi dane, moze byc
# duzy) kontra krotki limit dla samych DROP/CREATE DATABASE (czyste DDL,
# powinno byc niemal natychmiastowe - dlugie oczekiwanie tam oznacza realny
# problem, np. nieoczekiwanie zablokowana baza).
TIMEOUT_DUMP_RESTORE_S = 600.0
TIMEOUT_DDL_S = 30.0

NAZWA_BAZY_W_ARCHIWUM = "baza.dump"
NAZWA_MANIFESTU = "manifest.json"


class BladKopiiZapasowej(Exception):
    pass


class NieprawidloweHaslo(BladKopiiZapasowej):
    pass


def _flagi_bez_okna() -> int:
    return getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _katalog_binariow() -> Path:
    return katalog_bazowy() / "vendor" / "postgresql" / "pgsql" / "bin"


def _binarka(nazwa: str) -> Path:
    return _katalog_binariow() / f"{nazwa}.exe"


def _adres_bazy() -> str:
    from app.config import DATABASE_URL

    return DATABASE_URL


def _adres_administracyjny() -> str:
    """Adres polaczenia do bazy `postgres` (nie docelowej `faktury_pro`) -
    potrzebny do DROP/CREATE DATABASE, ktorych nie da sie wykonac na bazie,
    z ktora jest sie akurat polaczonym. UWAGA: `str(url)`/`repr(url)` w
    SQLAlchemy maskuja haslo gwiazdkami (bezpieczne do logow) - tu trzeba
    jawnie `render_as_string(hide_password=False)`, inaczej pg_dump/psql
    probowalyby polaczyc sie z literalnym haslem "***"."""
    from sqlalchemy.engine import make_url

    url = make_url(_adres_bazy()).set(database="postgres")
    return url.render_as_string(hide_password=False)


def _nazwa_bazy() -> str:
    from sqlalchemy.engine import make_url

    return make_url(_adres_bazy()).database


def _wyprowadz_klucz(haslo: str, sol: bytes) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(), length=32, salt=sol, iterations=ITERACJE_PBKDF2
    )
    return base64.urlsafe_b64encode(kdf.derive(haslo.encode("utf-8")))


# -- ustawienia lokalne (folder docelowy, data ostatniego backupu) ----------
# Trzymane w tym samym pliku co reszta lokalnych ustawien appki (gui/nastawienia.py,
# %APPDATA%/FakturyPro/ustawienia.json) - to sciezka folderu i znacznik czasu,
# nie sekrety, wiec nie potrzebuja DPAPI (w odroznieniu od hasla szyfrowania,
# ktore w ogole nigdzie nie jest zapisywane - patrz docstring modulu).


def stan_backupu() -> dict:
    katalog = nastawienia.wczytaj(KLUCZ_KATALOG_DOCELOWY)
    ostatni_tekst = nastawienia.wczytaj(KLUCZ_OSTATNI_BACKUP)
    ostatni = datetime.fromisoformat(ostatni_tekst) if ostatni_tekst else None
    dni_od_ostatniego = (datetime.now(timezone.utc) - ostatni).days if ostatni else None
    return {
        "katalog_docelowy": katalog,
        "ostatni_backup": ostatni_tekst,
        "dni_od_ostatniego": dni_od_ostatniego,
        "przeterminowany": (
            dni_od_ostatniego is None or dni_od_ostatniego >= PROG_DNI_PRZETERMINOWANIA
        ),
    }


def ustaw_katalog_docelowy(sciezka: str) -> None:
    nastawienia.zapisz(KLUCZ_KATALOG_DOCELOWY, sciezka)


def _oznacz_wykonany_backup() -> None:
    nastawienia.zapisz(KLUCZ_OSTATNI_BACKUP, datetime.now(timezone.utc).isoformat())


# -- tworzenie kopii ----------------------------------------------------


def wykonaj_backup(katalog_docelowy: Path, haslo: str) -> Path:
    """Tworzy zaszyfrowany plik kopii zapasowej w `katalog_docelowy`. Zwraca
    sciezke utworzonego pliku. Rzuca BladKopiiZapasowej z czytelnym
    komunikatem, jesli pg_dump sie nie powiedzie. Dziala na ZYWEJ bazie (MVCC
    - pg_dump nie wymaga wylacznego dostepu ani zatrzymania appki)."""
    katalog_docelowy = Path(katalog_docelowy)
    katalog_docelowy.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="fpro-backup-") as tmp_tekst:
        tmp = Path(tmp_tekst)
        plik_dumpu = tmp / NAZWA_BAZY_W_ARCHIWUM
        _uruchom_pg_dump(plik_dumpu)

        plik_zip = tmp / "archiwum.zip"
        _zbuduj_archiwum(plik_zip, plik_dumpu)

        sol = os.urandom(DLUGOSC_SOLI)
        klucz = _wyprowadz_klucz(haslo, sol)
        token = Fernet(klucz).encrypt(plik_zip.read_bytes())

        znacznik_czasu = datetime.now().strftime("%Y-%m-%d_%H%M%S")
        docelowy = katalog_docelowy / f"faktury-pro-backup-{znacznik_czasu}.fpbk"
        with open(docelowy, "wb") as f:
            f.write(MAGIC)
            f.write(WERSJA_FORMATU.to_bytes(1, "big"))
            f.write(sol)
            f.write(token)

    _oznacz_wykonany_backup()
    return docelowy


def _uruchom(polecenie: list[str], timeout: float, opis_narzedzia: str) -> subprocess.CompletedProcess:
    """Wspolny wrapper na subprocess.run dla wszystkich wywolan narzedzi
    Postgresa w tym module - jedno miejsce pilnujace, zeby ZADNE z nich nie
    moglo wisiec bez konca (patrz TIMEOUT_DUMP_RESTORE_S/TIMEOUT_DDL_S wyzej)."""
    try:
        return subprocess.run(
            polecenie,
            capture_output=True,
            text=True,
            creationflags=_flagi_bez_okna(),
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as e:
        raise BladKopiiZapasowej(
            f"{opis_narzedzia} nie zakończył działania w wyznaczonym czasie "
            f"({int(timeout)}s). Sprawdź, czy katalog docelowy jest dostępny "
            "(np. czy dysk sieciowy/chmurowy nie jest odłączony) i spróbuj ponownie."
        ) from e


def _uruchom_pg_dump(plik_docelowy: Path) -> None:
    wynik = _uruchom(
        [str(_binarka("pg_dump")), "-Fc", "-f", str(plik_docelowy), _adres_bazy()],
        TIMEOUT_DUMP_RESTORE_S,
        "Tworzenie kopii bazy danych (pg_dump)",
    )
    if wynik.returncode != 0:
        raise BladKopiiZapasowej(
            f"Nie udało się wykonać kopii bazy danych (pg_dump, kod {wynik.returncode}):\n{wynik.stderr}"
        )


def _zbuduj_archiwum(plik_zip: Path, plik_dumpu: Path) -> None:
    manifest = {
        "wersja_formatu": WERSJA_FORMATU,
        "utworzono": datetime.now(timezone.utc).isoformat(),
        "nazwa_bazy": _nazwa_bazy(),
    }
    with zipfile.ZipFile(plik_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(NAZWA_MANIFESTU, json.dumps(manifest, indent=2))
        zf.write(plik_dumpu, NAZWA_BAZY_W_ARCHIWUM)
        katalog_logo = logo.katalog_logo()
        if katalog_logo.is_dir():
            for plik in katalog_logo.iterdir():
                if plik.is_file():
                    zf.write(plik, f"logo/{plik.name}")


# -- przywracanie ----------------------------------------------------


def przywroc_z_backupu(plik_kopii: Path, haslo: str) -> None:
    """Przywraca dane z pliku kopii zapasowej, NADPISUJAC calkowicie biezaca
    baze danych. Zatrzymuje watek serwera FastAPI (dla polaczen SQLAlchemy),
    ale zostawia prywatny Postgres dzialajacy, bo pg_restore/psql musza sie z
    nim polaczyc. Wywolujacy (gui/windows/widok_ustawien.py) jest
    odpowiedzialny za PELNE zamkniecie i wymuszenie ponownego uruchomienia
    appki PO powodzeniu tej funkcji - stan appki w pamieci (otwarte okna,
    zaladowane dane) jest niespojny z nowa zawartoscia bazy."""
    plik_kopii = Path(plik_kopii)
    surowe = plik_kopii.read_bytes()
    if surowe[:4] != MAGIC:
        raise BladKopiiZapasowej("To nie jest plik kopii zapasowej Faktury Pro (.fpbk).")
    wersja = surowe[4]
    if wersja != WERSJA_FORMATU:
        raise BladKopiiZapasowej(
            f"Nieobsługiwana wersja formatu kopii zapasowej ({wersja}) - "
            "ten plik wymaga nowszej wersji aplikacji."
        )

    sol = surowe[5 : 5 + DLUGOSC_SOLI]
    token = surowe[5 + DLUGOSC_SOLI :]
    klucz = _wyprowadz_klucz(haslo, sol)
    try:
        zip_bajty = Fernet(klucz).decrypt(token)
    except InvalidToken as e:
        raise NieprawidloweHaslo(
            "Nieprawidłowe hasło szyfrowania kopii zapasowej (albo plik jest uszkodzony)."
        ) from e

    with tempfile.TemporaryDirectory(prefix="fpro-restore-") as tmp_tekst:
        tmp = Path(tmp_tekst)
        plik_zip = tmp / "archiwum.zip"
        plik_zip.write_bytes(zip_bajty)

        with zipfile.ZipFile(plik_zip) as zf:
            zf.extractall(tmp)

        if not (tmp / NAZWA_MANIFESTU).exists() or not (tmp / NAZWA_BAZY_W_ARCHIWUM).exists():
            raise BladKopiiZapasowej("Archiwum kopii zapasowej jest niekompletne.")

        from gui import proces_aplikacji

        proces_aplikacji.zatrzymaj_serwer_fastapi()

        _odtworz_baze(tmp / NAZWA_BAZY_W_ARCHIWUM)
        _odtworz_logo(tmp / "logo")


def _uruchom_psql(polecenie: str) -> None:
    wynik = _uruchom(
        [str(_binarka("psql")), _adres_administracyjny(), "-c", polecenie],
        TIMEOUT_DDL_S,
        "Przygotowanie bazy danych (psql)",
    )
    if wynik.returncode != 0:
        raise BladKopiiZapasowej(
            f"Nie udało się przygotować bazy danych do przywrócenia:\n{wynik.stderr}"
        )


def _odtworz_baze(plik_dumpu: Path) -> None:
    nazwa = _nazwa_bazy()
    # WITH (FORCE) (PostgreSQL 13+) rozlacza wszelkie pozostale sesje przed
    # usunieciem - dodatkowa gwarancja przeciwko jakiemukolwiek przeoczonemu
    # polaczeniu, mimo ze wlasny watek FastAPI zostal juz zatrzymany wyzej.
    _uruchom_psql(f'DROP DATABASE IF EXISTS "{nazwa}" WITH (FORCE)')
    _uruchom_psql(f'CREATE DATABASE "{nazwa}"')

    wynik = _uruchom(
        [str(_binarka("pg_restore")), "-d", _adres_bazy(), str(plik_dumpu)],
        TIMEOUT_DUMP_RESTORE_S,
        "Przywracanie bazy danych (pg_restore)",
    )
    if wynik.returncode != 0:
        raise BladKopiiZapasowej(
            f"Nie udało się przywrócić bazy danych (pg_restore, kod {wynik.returncode}):\n{wynik.stderr}"
        )


def _odtworz_logo(katalog_logo_z_archiwum: Path) -> None:
    if not katalog_logo_z_archiwum.is_dir():
        return
    docelowy = logo.katalog_logo()
    if docelowy.exists():
        shutil.rmtree(docelowy)
    shutil.copytree(katalog_logo_z_archiwum, docelowy)
