"""Pobiera i przygotowuje przenosna dystrybucje PostgreSQL do zbudowania
prywatnej, wbudowanej instancji bazy danych appki (Faza 18B, Etap 3).

Krok jednorazowy, wykonywany PRZED zbudowaniem appki przez PyInstaller (patrz
faktury_pro.spec, ktory dolacza vendor/postgresql/pgsql/ jako `datas`) - NIE
jest czescia samej appki i nie jest wywolywany przy jej dzialaniu.

ZRODLO (oficjalne, zweryfikowane wprost - NIE zgadywane): EnterpriseDB
udostepnia na https://www.postgresql.org/download/windows/ (link "Binaries")
archiwa zip zawierajace pliki instalowane przez oficjalny instalator Windows,
"przeznaczone dla uzytkownikow, ktorzy chca dolaczyc Postgresa jako czesc
instalatora wlasnej aplikacji" - dokladnie nasz przypadek. Adres ponizej
zweryfikowany przez sprawdzenie przekierowania linku "Windows x86-64" dla
najnowszej wersji 18.x na stronie https://www.enterprisedb.com/download-postgresql-binaries
(2026-07-18).

Z pelnego archiwum (ok. 320 MB - zawiera tez pgAdmin 4, StackBuilder,
dokumentacje i naglowki C) appka potrzebuje TYLKO trzech podkatalogow
(razem ok. 146 MB): bin/ (postgres.exe, initdb.exe, pg_ctl.exe, pg_isready.exe
+ ich wlasne DLL - zweryfikowane przez ldd, ze postgres.exe NIE zalezy od
zadnych bibliotek spoza wlasnego bin/, w odroznieniu od WeasyPrint w Fazie 18A),
lib/ (rozszerzenia .dll) i share/ (dane strefy czasowej, szablony konfiguracji,
schemat information_schema itd. - initdb bez tego nie dziala).

Uzycie:
    python scripts/pobierz_postgres_portable.py

Wynik: vendor/postgresql/pgsql/{bin,lib,share}/ - katalog `vendor/` jest
celowo w .gitignore (ok. 146 MB binariow nie powinno trafiac do repozytorium
git), wiec ten skrypt trzeba uruchomic raz na kazdej maszynie budujacej appke,
przed pyinstaller faktury_pro.spec.
"""

import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

URL = "https://get.enterprisedb.com/postgresql/postgresql-18.4-2-windows-x64-binaries.zip"
PODKATALOGI_POTRZEBNE = ("pgsql/bin/", "pgsql/lib/", "pgsql/share/")

ROOT = Path(__file__).resolve().parent.parent
VENDOR_DIR = ROOT / "vendor" / "postgresql"
ZIP_SCIEZKA = VENDOR_DIR / "postgresql-18.4-2-windows-x64-binaries.zip"


def _pokaz_postep(przeczytane: int, calkowite: int) -> None:
    if calkowite <= 0:
        return
    procent = przeczytane * 100 // calkowite
    print(f"\rPobieranie... {procent}% ({przeczytane / 1_048_576:.0f} MB / {calkowite / 1_048_576:.0f} MB)", end="", flush=True)


def pobierz() -> None:
    VENDOR_DIR.mkdir(parents=True, exist_ok=True)
    if ZIP_SCIEZKA.exists():
        print(f"Archiwum juz pobrane: {ZIP_SCIEZKA}")
        return

    print(f"Pobieram {URL}")
    request = urllib.request.Request(URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(request) as odpowiedz:
        calkowite = int(odpowiedz.headers.get("Content-Length", 0))
        przeczytane = 0
        tmp_sciezka = ZIP_SCIEZKA.with_suffix(".zip.tmp")
        with open(tmp_sciezka, "wb") as plik:
            while True:
                fragment = odpowiedz.read(1024 * 1024)
                if not fragment:
                    break
                plik.write(fragment)
                przeczytane += len(fragment)
                _pokaz_postep(przeczytane, calkowite)
    print()
    tmp_sciezka.rename(ZIP_SCIEZKA)


def wypakuj() -> None:
    docelowy = VENDOR_DIR / "pgsql"
    if (docelowy / "bin" / "postgres.exe").exists():
        print(f"Binaria juz wypakowane: {docelowy}")
        return

    print(f"Wypakowuje bin/, lib/, share/ do {docelowy} ...")
    with zipfile.ZipFile(ZIP_SCIEZKA) as archiwum:
        for wpis in archiwum.infolist():
            if wpis.is_dir():
                continue
            if not wpis.filename.startswith(PODKATALOGI_POTRZEBNE):
                continue
            archiwum.extract(wpis, VENDOR_DIR)
    print("Gotowe.")


def posprzataj_zip() -> None:
    if ZIP_SCIEZKA.exists():
        ZIP_SCIEZKA.unlink()
        print(f"Usunieto archiwum zip (juz wypakowane): {ZIP_SCIEZKA}")


def main() -> None:
    pobierz()
    wypakuj()
    posprzataj_zip()

    postgres_exe = VENDOR_DIR / "pgsql" / "bin" / "postgres.exe"
    if not postgres_exe.exists():
        print(f"BLAD: nie znaleziono {postgres_exe} po wypakowaniu.", file=sys.stderr)
        sys.exit(1)
    print(f"\nGotowe: {VENDOR_DIR / 'pgsql'}")


if __name__ == "__main__":
    main()
