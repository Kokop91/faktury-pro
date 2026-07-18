# -*- mode: python ; coding: utf-8 -*-
"""
Plik PyInstaller do budowania spakowanej wersji Faktury Pro (Faza 18A - patrz
ETAP_3_ROZWOJU.md). Buduje JEDEN plik wykonywalny zawierajacy GUI
(customtkinter) razem z logika backendu (FastAPI/uvicorn, uruchamianym w
watku wewnatrz tego samego procesu - patrz gui/main.py:WatekSerwera). Nie
zajmuje sie jeszcze PostgreSQL (Faza 18B) ani wlasciwym instalatorem
Windows (Faza 18C) - appka nadal laczy sie z reczne uruchomiona baza danych
tak jak w trybie deweloperskim.

BUDOWANIE:
    pip install -r requirements.txt -r requirements-build.txt
    pyinstaller faktury_pro.spec --noconfirm

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
schemat XSD FA(3) z Fazy 12B) NIE sa czescia zadnego hooka - to pliki
specyficzne dla tego projektu, wiec sa dolaczane rezcznie ponizej jako `datas`,
pod dokladnie takimi samymi sciezkami wzglednymi jak w repozytorium (app/...),
zeby app/sciezki.py:katalog_bazowy() dzialalo identycznie w obu trybach.
"""

from pathlib import Path

ROOT = Path(SPECPATH)  # noqa: F821 - SPECPATH jest wstrzykiwane przez PyInstaller

a = Analysis(  # noqa: F821
    [str(ROOT / "gui" / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=[
        (str(ROOT / "app" / "templates"), "app/templates"),
        (str(ROOT / "app" / "jpk_schemas"), "app/jpk_schemas"),
        (str(ROOT / "app" / "xsd"), "app/xsd"),
    ],
    hiddenimports=[],
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
