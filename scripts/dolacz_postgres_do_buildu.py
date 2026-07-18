"""Dolacza przenosne binaria PostgreSQL do juz zbudowanej paczki PyInstallera
(Faza 18B) - uruchamiane PO `pyinstaller faktury_pro.spec`, nie w jego trakcie.

DLACZEGO OSOBNY KROK, NIE `datas` W .SPEC: PyInstaller podczas budowania
rozpoznaje pliki .dll przekazane przez `datas` jako biblioteki natywne
("binary vs. data reclassification") i poddaje je wlasnej logice
deduplikacji wg samej nazwy pliku - zweryfikowane empirycznie, ze to
podmienia DLL WeasyPrint (Pango/GLib) na inaczej zbudowane pliki o tej samej
nazwie z bin/ Postgresa (m.in. zlib1.dll, libiconv-2.dll,
libwinpthread-1.dll), psujac generowanie PDF w spakowanej wersji. Zwykle
kopiowanie plikow PO zbudowaniu appki omija ten mechanizm calkowicie -
PyInstaller nigdy nie widzi tych plikow.

Uzycie (po `pyinstaller faktury_pro.spec --noconfirm`):
    python scripts/dolacz_postgres_do_buildu.py
"""

import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ZRODLO = ROOT / "vendor" / "postgresql" / "pgsql"
DOCELOWY = ROOT / "dist" / "Faktury Pro" / "_internal" / "vendor" / "postgresql" / "pgsql"


def main() -> None:
    if not (ZRODLO / "bin" / "postgres.exe").exists():
        print(
            f"BLAD: brak {ZRODLO} - uruchom najpierw scripts/pobierz_postgres_portable.py",
            file=sys.stderr,
        )
        sys.exit(1)

    katalog_internal = ROOT / "dist" / "Faktury Pro" / "_internal"
    if not katalog_internal.exists():
        print(
            f"BLAD: brak {katalog_internal} - najpierw zbuduj appke "
            "(pyinstaller faktury_pro.spec --noconfirm)",
            file=sys.stderr,
        )
        sys.exit(1)

    if DOCELOWY.exists():
        shutil.rmtree(DOCELOWY)

    print(f"Kopiuje {ZRODLO} -> {DOCELOWY} ...")
    shutil.copytree(ZRODLO, DOCELOWY)
    print("Gotowe.")


if __name__ == "__main__":
    main()
