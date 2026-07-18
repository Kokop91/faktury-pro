# -*- mode: python ; coding: utf-8 -*-
"""
Plik PyInstaller do budowania spakowanej wersji Faktury Pro (Faza 18A+18B -
patrz ETAP_3_ROZWOJU.md). Buduje JEDEN plik wykonywalny zawierajacy GUI
(customtkinter), logike backendu (FastAPI/uvicorn, uruchamianym w watku
wewnatrz tego samego procesu - patrz gui/main.py:WatekSerwera) i prywatna,
przenosna instancje PostgreSQL (Faza 18B - patrz gui/postgres_serwer.py),
ktora appka sama uruchamia/zatrzymuje, gdy DATABASE_URL nie jest podane
jawnie (tryb deweloperski, .env, bez zmian wzgledem Etapu 1/2). Nie zajmuje
sie jeszcze wlasciwym instalatorem Windows (Faza 18C).

BUDOWANIE:
    pip install -r requirements.txt -r requirements-build.txt
    python scripts/pobierz_postgres_portable.py   # jednorazowo, przed pierwszym budowaniem
    pyinstaller faktury_pro.spec --noconfirm
    python scripts/dolacz_postgres_do_buildu.py   # PO pyinstallerze, patrz uzasadnienie nizej

Wynik: dist/Faktury Pro/Faktury Pro.exe (tryb --onedir - CELOWY wybor,
nie --onefile, patrz uzasadnienie w raporcie Fazy 18A: onedir jest bardziej
niezawodny i szybszy przy starcie, --onefile w praktyce tylko rozpakowuje
identyczna zawartosc do folderu tymczasowego przy KAZDYM starcie appki).

Tryb --windowed: EXE(console=False) ponizej - appka nie pokazuje okna konsoli
w tle. Do debugowania bledow startu (np. brakujacy hidden import) mozna
tymczasowo ustawic console=True, zeby zobaczyc pelny traceback.

NATYWNE ZALEZNOSCI (WeasyPrint/Pango/fontconfig, customtkinter/assets,
psycopg2, uvicorn/sqlalchemy dialekty, matplotlib/mpl-data, tkinter/Tcl-Tk)
sa dolaczane AUTOMATYCZNIE przez oficjalne hooki PyInstallera i pakiet
pyinstaller-hooks-contrib (wymagany w requirements-build.txt) - zweryfikowane
czytajac ich kod przed napisaniem tego pliku (hook-weasyprint.py rozwiazuje
i dolacza cala domkniete zestawy DLL przez PyInstaller.depend.utils, oraz
kopiuje katalog etc/fonts z konfiguracja fontconfig). Appka SAMA musi jedynie
wskazac fontconfigowi na te dolaczone pliki w czasie dzialania (zamiast na
wkompilowana sciezke z maszyny budujacej) - patrz poczatek gui/main.py.

WLASNE zasoby appki (szablony PDF z Fazy 3, schematy XSD JPK_V7 z Fazy 13,
schemat XSD FA(3) z Fazy 12B, migracje Alembic i konfiguracja Alembic
potrzebna Fazie 18B do przygotowania schematu prywatnej bazy) NIE sa czescia
zadnego hooka - to pliki specyficzne dla tego projektu, wiec sa dolaczane
recznie ponizej jako `datas`, pod dokladnie takimi samymi sciezkami
wzglednymi jak w repozytorium (app/..., alembic/...), zeby
app/sciezki.py:katalog_bazowy() dzialalo identycznie w obu trybach.

PRYWATNY POSTGRESQL (Faza 18B): binaria (~146 MB, tylko bin/lib/share -
BEZ pgAdmin/StackBuilder/dokumentacji/naglowkow C, ktorych appka nie
potrzebuje w runtime) NIE sa czescia repozytorium git (zbyt duze - vendor/
jest w .gitignore) - trzeba je najpierw pobrac uruchamiajac
scripts/pobierz_postgres_portable.py (jednorazowo na kazdej maszynie
budujacej).

WAZNE - binaria PostgreSQL CELOWO NIE sa dolaczane przez `datas` w tym
Analysis() (w odroznieniu od reszty zasobow powyzej)! PyInstaller podczas
budowania wykonuje krok "binary vs. data reclassification", ktory
rozpoznaje pliki .dll w `datas` jako biblioteki natywne i poddaje je
WLASNEJ logice deduplikacji wg samej nazwy pliku - zweryfikowane empirycznie
(zbudowano dwie wersje i porownano), ze powoduje to podmiane DLL WeasyPrint
(Pango/GLib) na inaczej zbudowane pliki o tej samej nazwie z bin/ Postgresa
(m.in. zlib1.dll, libiconv-2.dll, libwinpthread-1.dll - PostgreSQL i MSYS2
buduja je oddzielnie, wiec mimo identycznej nazwy nie sa binarnie zgodne) -
efekt: WeasyPrint przestaje sie ladowac (`OSError: cannot load library
libpango-1.0-0.dll: error 0x7f`, czyli ERROR_PROC_NOT_FOUND). Binaria
Postgresa sa wiec dolaczane PO zbudowaniu, zwyklym kopiowaniem plikow
(scripts/dolacz_postgres_do_buildu.py) do dist/Faktury Pro/_internal/ -
PyInstaller nigdy ich nie widzi ani nie analizuje, wiec nie ma szans na
konflikt z DLL WeasyPrint. Ten sam mechanizm bedzie tez pasowal do
przyszlego instalatora Windows (Faza 18C), ktory i tak ma "laczyc" pliki
z PyInstallera (18A) z przenosnymi binariami Postgresa (18B) jako dwa
oddzielne skladniki.
"""

from pathlib import Path

ROOT = Path(SPECPATH)  # noqa: F821 - SPECPATH jest wstrzykiwane przez PyInstaller

POSTGRES_PORTABLE_DIR = ROOT / "vendor" / "postgresql" / "pgsql"
if not (POSTGRES_PORTABLE_DIR / "bin" / "postgres.exe").exists():
    raise SystemExit(
        "Brak przenosnych binariow PostgreSQL (Faza 18B) w "
        f"{POSTGRES_PORTABLE_DIR} - uruchom najpierw:\n"
        "    python scripts/pobierz_postgres_portable.py\n"
        "a dopiero potem pyinstaller faktury_pro.spec."
    )

a = Analysis(  # noqa: F821
    [str(ROOT / "gui" / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "app" / "templates"), "app/templates"),
        (str(ROOT / "app" / "jpk_schemas"), "app/jpk_schemas"),
        (str(ROOT / "app" / "xsd"), "app/xsd"),
        (str(ROOT / "alembic.ini"), "."),
        (str(ROOT / "alembic"), "alembic"),
        # Binaria PostgreSQL (Faza 18B) CELOWO nie sa tutaj - patrz duzy
        # komentarz na gorze tego pliku. Dolaczane PO zbudowaniu przez
        # scripts/dolacz_postgres_do_buildu.py.
    ],
    # alembic/env.py jest wczytywany przez alembic recznie z pliku (importlib.util
    # spec_from_file_location + exec_module), NIE przez zwykly "import" - PyInstaller
    # nie widzi tej sciezki w statycznej analizie, wiec "from logging.config import
    # fileConfig" w env.py nie znajduje modulu w spakowanej wersji (zweryfikowane -
    # ModuleNotFoundError: No module named 'logging.config'), mimo ze logging.config
    # jest standardowym modulem biblioteki. Wymuszamy jego dolaczenie jawnie.
    hiddenimports=["logging.config"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)  # noqa: F821

exe = EXE(  # noqa: F821
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Faktury Pro",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,  # UPX bywa niekompatybilny z niektorymi natywnymi .dll (Pango/fontconfig) i podnosi ryzyko falszywych alarmow antywirusow - dla pierwszej dzialajacej wersji lepiej wylaczony
    console=False,  # --windowed: bez okna konsoli w tle
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(ROOT / "assets" / "icon.ico"),  # Faza 18C - tez uzywana przez skroty instalatora
)

coll = COLLECT(  # noqa: F821
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Faktury Pro",
)
