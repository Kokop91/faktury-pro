# CLAUDE.md — Kontekst projektu dla Claude Code

Ten plik jest czytany automatycznie na starcie każdej sesji Claude Code w tym repozytorium.
Zawiera kontekst, którego NIE trzeba powtarzać w każdym prompt.

## Nazwa projektu
Faktury Pro (roboczo) — aplikacja webowa do fakturowania i gospodarki magazynowej dla małej firmy.

## Stack technologiczny

**WAŻNE — zmiana architektury (decyzja podjęta po Fazie 2):** aplikacja jest DESKTOPOWA,
nie webowa. Poniższy backend to nie jest "serwer do przeglądarki" — to lokalny serwer API,
z którym gada wyłącznie aplikacja desktopowa tego samego użytkownika, na tym samym komputerze.

- **Backend (lokalny serwer API):** Python, FastAPI — bez zmian względem Faz 1-2, ten kod zostaje
- **Baza danych:** PostgreSQL. **Tryb deweloperski** (bez zmian względem Etapu 1/2):
  `DATABASE_URL` w `.env` wskazuje na Postgresa, którym opiekuje się deweloper ręcznie
  (Docker / instalacja systemowa na porcie 5432). **Tryb produktowy (Faza 18B, Etap 3):**
  gdy `DATABASE_URL` NIE jest podane jawnie (żaden `.env`, żadna zmienna środowiskowa —
  dokładnie tak wygląda appka u użytkownika końcowego), appka sama zarządza WŁASNĄ,
  prywatną, przenośną instancją PostgreSQL — użytkownik nigdy nie ma świadomości, że
  PostgreSQL w ogóle istnieje, nie instaluje go, nie konfiguruje. Zobacz sekcję
  "Prywatny PostgreSQL" niżej po szczegóły.
- **ORM/migracje:** SQLAlchemy + Alembic
- **PDF:** WeasyPrint (HTML → PDF)
- **Frontend/UI:** **customtkinter** — aplikacja desktopowa komunikująca się z FastAPI przez
  bibliotekę `requests` (ten sam wzorzec co w projekcie SecureChat autora: FastAPI backend +
  customtkinter GUI)
- **Uruchamianie serwera (zmienione w Fazie 18A):** FastAPI/uvicorn NIE jest już uruchamiany
  jako osobny podproces (`python -m uvicorn ...`) — po spakowaniu PyInstallerem nie ma
  dostępnego `python.exe` do wywołania w ten sposób. Zamiast tego `gui/main.py:WatekSerwera`
  uruchamia `uvicorn.Server` programowo, w osobnym wątku WEWNĄTRZ tego samego procesu co GUI
  (pętla Tk w wątku głównym, pętla asyncio uvicorn we własnym wątku — nie kolidują). Wybrane
  świadomie zamiast alternatywy "drugi osobny plik .exe dla backendu", bo eliminuje całą
  kategorię problemów ze względnymi ścieżkami między dwoma spakowanymi plikami. Użytkownik
  końcowy nadal nie widzi ani nie obsługuje serwera bezpośrednio.
- **Auth (Faza 6, zrobione):** appka jest jednostanowiskowa, więc zamiast JWT/sesji jest ekran
  logowania hasłem przy starcie (`gui/windows/ekran_logowania.py`). Hash hasła (bcrypt) leży
  lokalnie w `%APPDATA%/FakturyPro/auth.json` — poza bazą PostgreSQL i poza repozytorium.
  Endpointy FastAPI NIE mają JWT ani żadnej autoryzacji — serwer nasłuchuje tylko na
  127.0.0.1, więc dostęp do niego już wymaga dostępu do tego samego komputera/konta.
  Zmiana hasła: widok Ustawienia (`gui/windows/widok_ustawien.py`).
- **Integracja z KSeF (Faza 12A+12B, zrobione — fundament, uwierzytelnianie i wysyłka
  faktur w strukturze FA(3)):** obsługa API KSeF 2.0 (Krajowy System e-Faktur,
  Ministerstwo Finansów), metoda uwierzytelniania "token KSeF" (nie certyfikat/XAdES —
  appka nigdy nie podpisuje dokumentów, tylko wysyła zaszyfrowany token).
  - **Środowiska:** TESTOWE (`https://api-test.ksef.mf.gov.pl/v2`) i PRODUKCYJNE
    (`https://api.ksef.mf.gov.pl/v2`), przełączane w Ustawieniach
    (`gui/windows/widok_ustawien.py`). **Domyślne i bezpieczne środowisko startowe to
    zawsze TESTOWE.** Aktywne środowisko ma wyraźne wizualne oznaczenie (kolorowa
    "banda" — zielona dla testowego, czerwona dla produkcyjnego). Przełączenie na
    PRODUKCYJNE wymaga świadomej akcji użytkownika — potwierdzenia w oknie dialogowym
    ostrzegającym o realnych skutkach prawnych/finansowych — appka NIGDY nie przełącza
    się na produkcję cicho/automatycznie.
  - **Token KSeF appka NIE generuje** — token zdobywa użytkownik samodzielnie poza
    aplikacją (portal KSeF, Profil Zaufany, sekcja "Zarządzanie tokenami") i wkleja go
    w Ustawieniach. Backend jedynie go przechowuje i używa do uwierzytelnienia.
  - **Przechowywanie tokena:** lokalnie w `%APPDATA%/FakturyPro/ksef.json`, poza bazą
    PostgreSQL i poza repozytorium (ten sam katalog co `auth.json` z Fazy 6). W
    odróżnieniu od hasła appki (bcrypt — hash jednokierunkowy, tylko do weryfikacji),
    token KSeF musi być odwracalny (appka wysyła go do KSeF przy każdym
    uwierzytelnieniu), więc jest zaszyfrowany, nie zahaszowany — Windows DPAPI
    (`win32crypt.CryptProtectData`/`CryptUnprotectData`), związany z kontem Windows na
    tym komputerze. Zob. `app/services/ksef_ustawienia.py`.
  - **Warstwa serwisowa:** `app/services/ksef_service.py` — cykl uwierzytelnienia
    (challenge → szyfrowanie RSA-OAEP/SHA-256 tokenu → `/auth/ksef-token` → odpytywanie
    statusu → `/auth/token/redeem`), wywoływany przyciskiem "Testuj połączenie z KSeF"
    w Ustawieniach (12A) oraz przy każdej wysyłce faktury (12B) — accessToken jest
    zawsze świeży i jednorazowy, appka NIE zarządza długożyciowymi sesjami/refresh
    tokenami.
  - **Faza 12B — generowanie i wysyłka faktury FA(3):** `app/services/ksef_fa3_builder.py`
    mapuje `Faktura`+`PozycjaFaktury`+`Firma`+`Klient` na XML zgodny ze strukturą
    logiczną FA(3) (schemat XSD Ministerstwa Finansów, kopia w `app/xsd/fa3/`) i
    waliduje go wzgledem tego schematu PRZED wysyłką — błąd walidacji nigdy nie
    trafia do KSeF, tylko wraca jako czytelny komunikat (pole + przyczyna).
    Wysyłka: `app/services/ksef_service.py:wyslij_fakture_do_ksef` — sesja
    interaktywna (szyfrowanie AES-256-CBC faktury kluczem symetrycznym, sam klucz
    szyfrowany RSA-OAEP kluczem publicznym MF), odpytywanie statusu faktury i pobranie
    UPO po przyjęciu. Wynik zapisywany na `Faktura`: `status_ksef` (nie_wyslana /
    wysylanie_w_toku / przyjeta / odrzucona), `numer_ksef`, `upo_xml`,
    `przyczyna_odrzucenia_ksef`. UI: przycisk "Wyślij do KSeF" i "Pobierz UPO" w
    szczegółach faktury (`gui/windows/szczegoly_faktury.py`), kolumna statusu KSeF na
    liście faktur.
    **Typy dokumentu wysyłane do KSeF:** faktura VAT, zaliczkowa, końcowa (rozliczeniowa),
    korygująca (`RodzajFaktury` = VAT/ZAL/ROZ/KOR/KOR_ZAL/KOR_ROZ dobierany automatycznie).
    **Faktura pro forma i nota korygująca NIGDY nie są wysyłane** — zweryfikowane wprost
    w schemacie FA(3) (typ `TRodzajFaktury` nie ma dla nich żadnej wartości), to nie
    jest "faktura" w rozumieniu ustawy o VAT. **Pozycje ze stawką VAT "zw" (w tym cały
    typ RACHUNEK) są tymczasowo zablokowane** — FA(3) wymaga wtedy wskazania podstawy
    prawnej zwolnienia (pole P_19A/B/C), a model danych appki jeszcze tego nie zbiera;
    appka zgłasza to jako czytelny błąd zamiast zgadywać podstawę prawną.
  - **Faza 12C — odbiór faktur kosztowych (zakupowych):** nowy model `DokumentKosztowy`
    (`app/models/dokument_kosztowy.py`) — rejestr/podgląd faktur wystawionych na NIP
    naszej firmy, BEZ integracji księgowej (to potencjalny temat na przyszłość).
    Sprawdzanie: `app/services/ksef_koszty_service.py:pobierz_nowe_faktury_kosztowe` —
    `POST /invoices/query/metadata` (SubjectType=Subject2/nabywca) + pobranie treści
    XML każdej nowej faktury (`GET /invoices/ksef/{ksefNumber}`); punkt startowy
    kolejnego sprawdzenia to `MAX(data_trwalego_zapisu)` z już pobranych dokumentów
    (typ daty `PermanentStorage`, zalecany przez MF do przyrostowego pobierania -
    świadomie NIE używamy mechanizmu eksportu paczek z HWM, bo jest zaprojektowany
    dla systemów działających 24/7, a ta appka sprawdza tylko na żądanie).
    Wywoływane WYŁĄCZNIE: (a) ręcznie przyciskiem "Sprawdź nowe faktury kosztowe"
    (`gui/windows/widok_dokumentow_kosztowych.py`), (b) opcjonalnie przy starcie appki,
    jeśli użytkownik włączył to w Ustawieniach (`sprawdzaj_koszty_przy_starcie`,
    domyślnie WYŁĄCZONE — w odróżnieniu od zaległych faktur cyklicznych z Fazy 15,
    to prawdziwe połączenie sieciowe z KSeF, nie tylko lokalne zapytanie do bazy).
    Liczba nierozpatrzonych ("nowa") dokumentów pokazywana jako odznaka w pasku
    bocznym — TA odznaka odświeża się zawsze (czysto lokalne zapytanie), niezależnie
    od ustawienia auto-sprawdzania.
  - Mechanizm i adresy zweryfikowane wprost z oficjalnej dokumentacji Ministerstwa
    Finansów (`github.com/CIRFMF/ksef-api`) i z żywego środowiska testowego, nie
    zgadywane.
  - **Faza 12D — domknięcie (dashboard + wysyłka zbiorcza), Faza 12 KOMPLETNA:**
    dashboard ma sekcję "KSeF" (faktury oczekujące na wysyłkę, nowe dokumenty
    kosztowe) i faktury odrzucone przez KSeF w "Wymagają uwagi". Ustawienia
    pokazują zamaskowany podgląd zapisanego tokena (ostatnie 4 znaki) i datę
    ostatniego sprawdzenia faktur kosztowych. Lista faktur (`gui/windows/widok_faktur.py`)
    ma zaznaczanie wierszy (`Tabela(zaznaczalne=True)`, opt-in, nie wpływa na inne
    tabele) i przycisk "Wyślij zaznaczone do KSeF"
    (`ksef_service.wyslij_faktury_zbiorczo` — jedno wspólne uwierzytelnienie dla
    całej paczki, nie N uwierzytelnień dla N faktur).
    **Bezpieczeństwo środowiska (testowe/produkcyjne):** oznaczenie aktywnego
    środowiska (`gui/widgets_pomocnicze.py:etykieta_srodowiska_ksef`, jedno
    źródło tekstu/kolorów) widoczne w KAŻDYM miejscu, z którego appka wysyła/
    pobiera coś z KSeF — Ustawienia, szczegóły faktury, lista faktur (wysyłka
    zbiorcza), dokumenty kosztowe. Przed każdą wysyłką do KSeF (pojedynczą i
    zbiorczą) appka odczytuje środowisko NA NOWO tuż przed akcją (nie ufa
    wartości sprzed otwarcia okna) i wymaga świadomego potwierdzenia w oknie
    dialogowym, jeśli aktywne jest PRODUKCYJNE.
- **Kursy walut:** publiczne API NBP
- **Dane firm po NIP:** API GUS/REGON
- **Pakowanie do dystrybucji (Faza 18A+18B+18C+18D, Etap 3 KOMPLETNY: sam
  plik wykonywalny + prywatny PostgreSQL + instalator Windows + kreator
  pierwszego uruchomienia):** appka pakowana przez **PyInstaller**
  (`faktury_pro.spec` w katalogu głównym repo — celowo WYJĄTEK od reguły
  `*.spec` w `.gitignore`, to ręcznie utrzymywany plik, nie auto-wygenerowane
  rusztowanie). Tryb `--onedir` + `--windowed` (nie `--onefile` — onedir jest
  bardziej niezawodny i szybszy przy starcie). Zależności potrzebne WYŁĄCZNIE
  do budowania (PyInstaller + `pyinstaller-hooks-contrib`, ten drugi pakiet
  dostarcza gotowe reguły pakowania dla WeasyPrint/customtkinter/psycopg2/
  uvicorn/sqlalchemy — bez niego PyInstaller sam nie wie, które natywne .dll
  dołączyć) żyją w osobnym `requirements-build.txt`, nie w głównym
  `requirements.txt`.
  - **Budowanie:** `pip install -r requirements.txt -r requirements-build.txt`,
    potem `pyinstaller faktury_pro.spec --noconfirm`. Wynik:
    `dist/Faktury Pro/Faktury Pro.exe`.
  - **Rozwiązywanie ścieżek do zasobów** (szablony PDF z Fazy 3, schematy XSD
    JPK_V7 z Fazy 13, schemat XSD FA(3) z Fazy 12B): `app/sciezki.py:katalog_bazowy()`
    sprawdza `sys.frozen`/`sys._MEIPASS` (zalecany przez PyInstaller wzorzec) —
    w trybie deweloperskim to katalog główny repo, w wersji spakowanej katalog
    rozpakowanych danych. Wszystkie miejsca ładujące pliki z dysku (nie przez
    `importlib.resources`) muszą przez to przechodzić, nie liczyć na goły
    `__file__`.
  - **WeasyPrint w wersji spakowanej:** natywne biblioteki (Pango/GLib/HarfBuzz/
    fontconfig, ok. 20 plików .dll) i katalog konfiguracyjny fontconfig
    (`etc/fonts/`) są dołączane AUTOMATYCZNIE przez `hook-weasyprint.py`
    z `pyinstaller-hooks-contrib` (zweryfikowane czytając ten hook i licząc
    zamknięte drzewo zależności `ldd` niezależnie — obie metody dały ten sam
    zestaw plików). Appka SAMA musi jednak wskazać fontconfigowi na te
    dołączone pliki w czasie działania (inaczej próbowałby wkompilowanej
    ścieżki z maszyny budującej) — `os.environ["FONTCONFIG_PATH"]` ustawiane
    na samej górze `gui/main.py`, TYLKO gdy `sys.frozen`, PRZED jakimkolwiek
    importem `weasyprint` (ten dlopen'uje biblioteki natywne już przy
    imporcie modułu). Przetestowane na żywo w spakowanej wersji (nie tylko
    deweloperskiej) — polskie znaki diakrytyczne renderują się poprawnie.
  - **matplotlib w wersji spakowanej:** działa bez dodatkowej konfiguracji —
    kod dashboardu importuje `matplotlib.backends.backend_tkagg` bezpośrednio
    (nie przez automatyczne wykrywanie backendu), więc PyInstaller widzi ten
    import statycznie; dane `mpl-data` dołącza wbudowany hook PyInstallera.
    Przetestowane na żywo w spakowanej wersji.
  - **customtkinter/psycopg2/uvicorn/sqlalchemy/bcrypt/pywin32:** obsługiwane
    automatycznie przez hooki PyInstallera / `pyinstaller-hooks-contrib`, bez
    ręcznej konfiguracji w `.spec`.
  - **Prywatny, przenośny PostgreSQL (Faza 18B):** appka zarządza WŁASNĄ
    instancją PostgreSQL — użytkownik końcowy nigdy nie instaluje ani nie
    konfiguruje bazy danych. Aktywne TYLKO gdy `DATABASE_URL` nie jest podane
    jawnie (`app.config.UZYWA_PRYWATNEGO_POSTGRESA`) — tryb deweloperski z
    `.env` (jak w Etapie 1/2) pozostaje całkowicie bez zmian, appka wtedy w
    ogóle nie dotyka prywatnej instancji.
    - **Źródło binariów:** oficjalne archiwum EDB "binaries" (zip, bez
      instalatora — przeznaczone wprost do embedowania w innych aplikacjach),
      zweryfikowane bezpośrednio przez sprawdzenie przekierowania pobierania,
      NIE zgadywane. Wersja 18.4, zgodna z wersją zainstalowaną na maszynie
      deweloperskiej. Pobierane i przycinane (tylko `bin/`+`lib/`+`share/`,
      ~146 MB z ~320 MB — bez pgAdmin/StackBuilder/dokumentacji/nagłówków C)
      przez `scripts/pobierz_postgres_portable.py`, jednorazowo na maszynie
      budującej. Ląduje w `vendor/postgresql/pgsql/` (`.gitignore` — zbyt
      duże na repozytorium git).
    - **KLUCZOWA PUŁAPKA (zweryfikowana empirycznie, kosztowała najwięcej
      czasu w tej fazie):** binaria PostgreSQL NIE mogą być dołączone przez
      `datas` w `faktury_pro.spec` — PyInstaller podczas budowania wykonuje
      krok "binary vs. data reclassification", który rozpoznaje pliki .dll
      w `datas` jako biblioteki natywne i poddaje je własnej logice
      deduplikacji wg samej nazwy pliku. Postgres i WeasyPrint mają kilka
      bibliotek o IDENTYCZNEJ nazwie, ale zbudowanych przez różne łańcuchy
      narzędzi (`zlib1.dll`, `libiconv-2.dll`, `libwinpthread-1.dll`) — efekt:
      PDF przestawał się generować (`OSError: cannot load library
      libpango-1.0-0.dll: error 0x7f`). Naprawione przez pominięcie binariów
      Postgresa w `Analysis(datas=...)` i dołączenie ich PO zbudowaniu, zwykłym
      kopiowaniem plików (`scripts/dolacz_postgres_do_buildu.py`) do
      `dist/Faktury Pro/_internal/vendor/postgresql/pgsql/` — PyInstaller
      nigdy ich wtedy nie widzi ani nie analizuje.
    - **Katalog binariów** (`vendor/postgresql/pgsql/`) rozwiązywany przez
      `app.sciezki.katalog_bazowy()` (jak reszta zasobów) — to pliki appki,
      tylko do odczytu. **Katalog DANYCH** (żywa, mutowalna baza) leży
      NATOMIAST w `%LOCALAPPDATA%/FakturyPro/pgsql-data/` — musi przetrwać
      aktualizacje/reinstalacje samej appki, więc nie może siedzieć w tym
      samym miejscu co jej pliki programu (analogicznie do `auth.json`/
      `ksef.json` z wcześniejszych faz, tylko `%LOCALAPPDATA%`, nie
      `%APPDATA%` — to duże pliki binarne, nie powinny "wędrować" w profilu
      sieciowym/domenowym tak jak małe ustawienia).
    - **Zarządzanie procesem** (`gui/postgres_serwer.py:PostgresPrywatny`,
      rozszerzenie wzorca z Fazy 4/18A): `initdb` przy pierwszym uruchomieniu
      (`--auth=trust`, `--locale=C`, `--encoding=UTF8` — trust auth bezpieczny
      tu, bo instancja nasłuchuje WYŁĄCZNIE na 127.0.0.1 na niestandardowym
      porcie **55432** — celowo inny niż domyślne 5432, żeby nie kolidować z
      ewentualnym innym Postgresem na komputerze użytkownika — i katalog
      danych ma uprawnienia NTFS ograniczone do konta Windows użytkownika).
      Start/stop jako podproces `postgres.exe`/`pg_ctl.exe stop -m fast`,
      health-check przez `pg_isready.exe`, uruchamiane w `gui/main.py:main()`
      PRZED serwerem FastAPI (i zatrzymywane PO nim, w odwrotnej kolejności).
      `gui/postgres_serwer.py:upewnij_baze_i_migracje()` tworzy bazę
      `faktury_pro`, jeśli jeszcze nie istnieje, i dociąga schemat do
      najnowszej migracji Alembic (bezpieczne wywoływać przy każdym starcie —
      no-op, gdy już aktualne) — Alembic (`alembic.ini` + `alembic/`) musi
      być dołączony jako `datas` w `.spec`, bo `env.py` jest wczytywany przez
      Alembic ręcznie z pliku, nie zwykłym `import` (i wymagał jawnego
      `hiddenimports=["logging.config"]` — ten sam powód: dynamicznie
      wczytany plik nie jest widoczny dla statycznej analizy PyInstallera).
  - **Instalator Windows (Faza 18C):** `installer.iss` (Inno Setup 6 — wybrany
    zamiast NSIS, bo Pascal Script czytelniej wyraża potrzebną tu logikę
    "zapytaj o zachowanie danych, ale tylko przy deinstalacji interaktywnej"
    niż język skryptowy NSIS, a deklaratywne wsparcie dla instalacji
    per-użytkownika bez uprawnień administratora jest wbudowane).
    - **Budowanie:** `"C:\Tools\InnoSetup6\ISCC.exe" installer.iss` (albo
      dowolna inna instalacja Inno Setup 6) — PO `pyinstaller faktury_pro.spec`
      i PO `scripts/dolacz_postgres_do_buildu.py` (pakuje cały gotowy folder
      `dist/Faktury Pro/`, więc musi już zawierać binaria Postgresa). Wynik:
      `Output/FakturyPro-Setup-1.0.0.exe`.
    - **Per-użytkownik, bez uprawnień administratora:**
      `PrivilegesRequired=lowest` — instalator NIGDY nie prosi o podniesienie
      uprawnień (UAC), nawet uruchomiony przez administratora. Katalog
      instalacji domyślnie `%LOCALAPPDATA%\Programs\FakturyPro` (NIE Program
      Files) — ten sam wzorzec co inne nowoczesne instalatory per-użytkownik
      na Windows (np. VS Code).
    - **Skróty:** Menu Start zawsze, Pulpit opcjonalnie (zaznaczone domyślnie,
      task `desktopicon`) — obie wskazują wprost na `Faktury Pro.exe`
      (ikona `assets/icon.ico` wbudowana w plik .exe przez
      `EXE(icon=...)` w `faktury_pro.spec`, więc skróty i sam plik mają tę
      samą ikonę bez dodatkowego kopiowania).
    - **Deinstalacja i dane:** katalog instalacji i katalog DANYCH
      (`%LOCALAPPDATA%\FakturyPro`, z prywatnym Postgresem z Fazy 18B) są
      CELOWO rozdzielone (patrz wyżej) — zwykła deinstalacja usuwa tylko
      pliki programu. Przy deinstalacji **interaktywnej** `installer.iss`
      pyta osobnym oknem, czy usunąć też dane — domyślny fokus na "Nie"
      (`MB_DEFBUTTON2`), bo nieodwracalne usunięcie faktur bez wyraźnej
      zgody byłoby zbyt ryzykowne. Deinstalacja **cicha/automatyczna**
      (`UninstallSilent()`, np. wdrożenie firmowe) NIGDY nie usuwa danych
      bez pytania — pomija to okno całkowicie i zawsze zachowuje dane.
    - **Odporność na osierocone procesy (zweryfikowana na żywo, prawdziwy
      znaleziony błąd):** jeśli appka zakończyła się awaryjnie (np. Menedżer
      zadań, awaria) zamiast przez normalne zamknięcie okna, prywatny
      PostgreSQL mógł zostać osierocony i nadal działać, blokując pliki
      `.dll`/`.exe` — deinstalacja/reinstalacja wtedy nie mogła usunąć
      katalogu instalacji. Naprawione: `installer.iss` przed usuwaniem
      plików (i przed reinstalacją) zamyka wszelkie procesy uruchomione
      DOKŁADNIE z katalogu instalacji (filtrowanie po ścieżce pliku
      wykonywalnego, NIE po samej nazwie `postgres.exe` — żeby nigdy nie
      tknąć innego, niezwiązanego Postgresa na komputerze użytkownika).
    - **Zweryfikowane na żywo, pełny cykl (powtórzone po naprawie crasha
      uvicorn z commita `851f536` — poprzedni zbudowany `Output/FakturyPro-
      Setup-1.0.0.exe` był starszy niż ta naprawa i pakował appkę, która
      wywalała się od razu po starcie w trybie `--windowed`; przebudowany od
      zera: `pyinstaller faktury_pro.spec` → `dolacz_postgres_do_buildu.py`
      → `ISCC.exe installer.iss`):** cicha instalacja (pliki, skróty Pulpit +
      Menu Start, wpis w rejestrze odinstalowywania) → uruchomienie appki ze
      spakowanej lokalizacji (potwierdzone: dochodzi do ekranu logowania bez
      crasha) → cicha deinstalacja z domyślnym zachowaniem danych → ponowna
      cicha instalacja → dane nadal na miejscu → **interaktywna deinstalacja
      z oknem "czy usunąć dane?" (UI Automation, oba warianty)**: wariant A —
      sam Enter (domyślny fokus, `MB_DEFBUTTON2` = "Nie") zachował katalog
      danych, usunął tylko pliki programu; wariant B — jawne kliknięcie "Tak"
      usunęło katalog danych (`%LOCALAPPDATA%\FakturyPro`) całkowicie. Tekst
      okna, oba przyciski i oba efekty zgodne z kodem w `installer.iss`.
      Symulacja osieroconego Postgresa (zweryfikowana we wcześniejszej
      sesji, nie powtarzana tu) opisana wyżej w sekcji o odporności na
      osierocone procesy.
  - **Kreator pierwszego uruchomienia (Faza 18D, Etap 3 KOMPLETNY):**
    zastępuje wszystkie ręczne kroki, które dotychczas wykonywał deweloper
    przez terminal (ręczny `python -c` wstawiający testową `Firmę`, ręczny
    `alembic upgrade head`) czymś, co realny użytkownik końcowy może sam
    przejść.
    - **Kolejność startu appki (`gui/main.py`) zmieniona:** hasło appki
      (Faza 6) jest wymagane PRZED startem bazy/serwera TYLKO wtedy, gdy już
      istnieje (`auth.czy_haslo_ustawione()` — plik lokalny, sprawdzenie
      natychmiastowe). Gdy hasła jeszcze nie ma (pierwsze uruchomienie),
      stary ekran logowania (`gui/windows/ekran_logowania.py`) jest pomijany
      w ogóle — ten ekran obsługuje teraz WYŁĄCZNIE logowanie istniejącym
      hasłem, martwy tryb "ustaw hasło przy pierwszym starcie" został z niego
      usunięty. Ustawienie hasła przeszło do Kroku 2 kreatora, który rusza
      PO starcie backendu, bo Krok 1 (dane firmy) potrzebuje działającego API.
    - **Pasek postępu startu backendu** (`gui/windows/ekran_startu.py`,
      `pokaz_podczas()`) — bez niego odstęp między zamknięciem ekranu
      logowania a pojawieniem się głównego okna (kilka sekund, dłużej przy
      pierwszym `initdb` + pierwszych migracjach Alembic) był całkowicie
      niemy, appka sprawiała wrażenie zawieszonej. Owija ISTNIEJĄCE, NIE
      zmienione `_uruchom_prywatny_postgres_jesli_trzeba()` +
      `_uruchom_serwer()` + `_czekaj_na_serwer()` w małe okno z
      `ctk.CTkProgressBar(mode="indeterminate")` i tekstem statusu
      ("Przygotowywanie bazy danych..." → "Uruchamianie serwera aplikacji...").
    - **Wykrywanie pierwszego uruchomienia i sam kreator**
      (`gui/windows/kreator_pierwszego_uruchomienia.py`,
      `uruchom_kreator_jesli_potrzebny()`): brak rekordu `Firma` (`GET /firma`
      → 404) LUB brak hasła appki → kreator zamiast głównego okna. Lista
      kroków jest budowana DYNAMICZNIE wg tego, czego jeszcze brakuje —
      dzięki temu kreator jest wznawialny: jeśli appka zamknie się (albo
      użytkownik świadomie przerwie, po potwierdzeniu w oknie dialogowym)
      między krokami, kolejne uruchomienie zaczyna od pierwszego wciąż
      brakującego kroku, nie od początku, i nigdy nie próbuje ponownie
      utworzyć już zapisanej `Firmy` (śledzone lokalnie w kroku, przełącza
      się na `PUT` zamiast `POST` po pierwszym udanym zapisie). Instancje
      kroków są tworzone leniwie i trzymane w pamięci (nie niszczone przy
      "Wstecz"), żeby cofnięcie się nie gubiło wpisanych wartości.
      - **Krok 1 — Dane firmy:** nazwa, NIP (+ przycisk "Pobierz z GUS",
        Faza 14 — reużywa `gui/integracje_gui.py:pobierz_z_gus`, identycznie
        jak Ustawienia), adres, dane bankowe, logo (opcjonalnie). Świadomie
        POMIJA typ_podatnika/JDG/urząd skarbowy/tryb blokady ujemnego stanu
        (zaawansowane pola JPK/magazynowe) — zostają wartościami domyślnymi
        z modelu, konfigurowalne później w Ustawieniach.
      - **Krok 2 — Hasło:** taka sama walidacja (min. 4 znaki, zgodność
        powtórzenia) i to samo `auth.ustaw_haslo()` co dawny tryb ustawiania
        w ekranie logowania, teraz jako krok kreatora zamiast osobnego okna.
      - **Krok 3 — Ustawienia (jedyny pomijalny, przycisk "Pomiń"):**
        domyślna stawka VAT (dropdown), informacja o formacie numeracji
        faktur (`FV/RRRR/NNNN`) jako zwykły TEKST, nie ustawienie — appka
        NIE MA dziś żadnego mechanizmu konfiguracji formatu/resetu numeracji
        (`app/services/numeracja.py` ma to zakodowane na sztywno), więc
        kreator nie obiecuje ustawienia, którego appka nie ma; oraz środowisko
        KSeF (Testowe/Produkcyjne, domyślnie Testowe) z nietechnicznym
        wyjaśnieniem różnicy i TYM SAMYM oknem potwierdzenia przy wyborze
        Produkcyjne co w Ustawieniach (`widok_ustawien.py:_na_zmiane_srodowiska_ksef`)
        — kreator NIGDY nie przełącza się cicho na produkcję.
    - **Logo firmy — nowy, minimalny mechanizm** (`gui/logo.py:wybierz_i_skopiuj_logo()`):
      `Firma.logo_path` istniał w modelu od Fazy 1 (i `app/services/pdf.py`
      już go odczytywał do PDF), ale nie było żadnego sposobu go ustawić —
      brakowało pola w schemacie Pydantic i przycisku w GUI. Naprawione:
      `logo_path` (+ przy okazji `domyslna_stawka_vat`, też nieużywane od
      Fazy 13) dodane do `FirmaBase`/`FirmaUpdate` w `app/schemas/firma.py`
      (kolumny w bazie już istniały — ŻADNA nowa migracja Alembic nie była
      potrzebna). Wybrany plik obrazu jest kopiowany do
      `%LOCALAPPDATA%/FakturyPro/logo/logo.<rozszerzenie>` (stała nazwa —
      jedna firma = jedno logo, nowy wybór nadpisuje poprzedni). Reużyte
      też w Ustawieniach (`widok_ustawien.py` — karta "Dane firmy" dostała
      te same dwa pola, logo i domyślna stawka VAT), żeby nie zostawić
      użytkownika bez możliwości zmiany po zakończeniu kreatora.
    - **Zweryfikowane na żywo:** pełna nowa sekwencja startu (uruchomienie
      appki bez `auth.json` i bez rekordu `Firma` w bazie - symulacja
      prawdziwego pierwszego użytkownika, przez prywatny Postgres 18B
      izolowany od bazy deweloperskiej) - ekran logowania poprawnie POMINIĘTY,
      pasek postępu pokazany, kreator wystartował na Kroku 1 z poprawnym
      tekstem/polami (zrzut ekranu przez `PrintWindow`, bo widgety
      customtkinter są rysowane na Canvas i nie mają drzewa dostępności UI
      Automation). Wszystkie 3 kroki zweryfikowane wizualnie (zrzuty ekranu
      Krok 1/2/3 - poprawny tytuł, podtytuł, pola, przyciski
      Wstecz/Pomiń/Dalej-lub-Zakończ, banda środowiska KSeF). Cały łańcuch
      zapisu zweryfikowany na żywo przez warstwę serwisową (bez HTTP, ten sam
      kod co endpointy): `pobierz_firme` 404 na pustej bazie →
      `utworz_firme` z `logo_path`+domyślnym `domyslna_stawka_vat=23%` →
      `aktualizuj_firme` z samym `domyslna_stawka_vat` (Krok 3) → odczyt po
      ponownym połączeniu z bazą potwierdza trwały zapis obu nowych pól.
      **NIE zweryfikowane przez rzeczywiste kliknięcia myszą** (symulowane
      kliknięcia/klawiatura konsekwentnie trafiały w tło, bo na tej maszynie
      działająca w tle gra pełnoekranowa - Farming Simulator 22 - odbierała
      fokus systemowy z powrotem po każdej próbie ustawienia go
      programowo - potwierdzone przez `GetForegroundWindow` wracające do
      okna gry; to ograniczenie środowiska testowego, nie appki) -
      przejście Krok 1 → Krok 2 przyciskiem "Dalej" (walidacja + zapis przez
      `uruchom_w_tle`), przycisk "Pobierz z GUS" w kreatorze, oraz wybór
      pliku logo (`tkinter.filedialog`) wymagają jednego ręcznego przejścia
      przez człowieka przed uznaniem fazy za w pełni potwierdzoną.

## Wiele profili firm (Faza 25, zrobione)

**ZASADA NADRZĘDNA: profile firm są w PEŁNI NIEZALEŻNE — zero współdzielenia
danych biznesowych.** To NIE jest wielofirmowość w sensie jednej wspólnej bazy
z filtrowaniem po `firma_id` — modele biznesowe (`Faktura`, `Klient`,
`Produkt`, `Magazyn`, `Oferta` itd.) są **całkowicie nietknięte** przez tę
fazę. Każdy profil dostaje własną, osobną bazę danych i własny podkatalog
plików; jedyne, co jest współdzielone między profilami, to sam proces
prywatnego PostgreSQL (Faza 18B) i garstka globalnych ustawień UI (tryb
wyglądu, geometria okna — patrz niżej).

- **Mechanizm:** jedna instancja prywatnego Postgresa (bez zmian względem
  Fazy 18B — ten sam port 55432, ten sam katalog danych
  `%LOCALAPPDATA%/FakturyPro/pgsql-data/`), ale KAŻDY profil ma wewnątrz niej
  własną bazę (`faktury_pro_<id_profilu>`, gdzie `id_profilu` to
  `uuid.uuid4().hex`). Który profil jest aktywny w danym procesie appki
  ustala `app/profil.py:ustaw_aktywny_profil(profil_id, nazwa_bazy)` przez
  **zmienną środowiskową procesu** `FAKTURY_PRO_PROFIL_BAZA` — `app/config.py`
  odczytuje ją przy obliczaniu `POSTGRES_PRYWATNY_BAZA`
  (`os.environ.get(ZMIENNA_BAZA_PROFILU, "faktury_pro")`).
  **KRYTYCZNE: `app.config` (i wszystko co go importuje, w tym
  `app.database` z jego globalnym `engine`/`SessionLocal` tworzonym raz przy
  imporcie) NIE MOŻE być zaimportowane nigdzie w procesie, zanim profil
  zostanie wybrany** — moduł oblicza swoje stałe raz, przy pierwszym
  imporcie, więc wcześniejszy import zamroziłby appkę na złej bazie (albo na
  domyślnej `faktury_pro`) do końca życia procesu. `gui/main.py` pilnuje tego
  porządku: ekran wyboru profilu (i `ustaw_aktywny_profil`) działa jeszcze
  PRZED jakimkolwiek importem `app.config`/`gui.postgres_serwer` (te są i tak
  importowane leniwie, dopiero wewnątrz `_uruchom_prywatny_postgres_jesli_trzeba`).
  Dzięki temu `app/database.py`, `alembic/env.py` i
  `gui/postgres_serwer.py:upewnij_baze_i_migracje()` (tworzenie
  bazy + `alembic upgrade head`) działają dla profili **bez żadnej zmiany
  własnej logiki** — po prostu zawsze widzą już poprawnie rozwiązaną nazwę
  bazy.
- **Tryb deweloperski bez zmian:** appka z jawnym `DATABASE_URL` w `.env`
  (`app.profil.czy_tryb_deweloperski()`) w ogóle pomija ekran wyboru profilu
  i całą resztę tej fazy — łączy się z bazą administrowaną ręcznie przez
  dewelopera, dokładnie jak przed Fazą 25.
- **Układ katalogów** (`app/profil.py` — jedno, wspólne źródło prawdy,
  zastępuje 8 wcześniej niezależnie zduplikowanych helperów
  `_katalog_appdata()`/`_katalog_konfiguracji()` w `gui/postgres_serwer.py`,
  `gui/logo.py`, `gui/auth.py`, `gui/nastawienia.py`,
  `app/services/ksef_ustawienia.py`, `app/services/email_ustawienia.py`,
  `app/services/integracje_ustawienia.py`):
  - `%LOCALAPPDATA%\FakturyPro\profiles.json` — rejestr profili
    (`gui/profile_rejestr.py`): id, nazwa bazy, nazwa wyświetlana, daty
    utworzenia/ostatniego użycia. Czysto lokalny plik, zero połączenia z bazą
    — musi być czytelny, zanim jakikolwiek backend wystartuje.
  - `%LOCALAPPDATA%\FakturyPro\profiles\<id>\` — dane PER-PROFILU: `auth.json`
    (hasło appki, Faza 6), `ksef.json` (Faza 12A), `email.json` (SMTP, Faza
    23), `integracje.json` (środowisko/klucz GUS, Faza 14), `logo/` (Faza
    18D), `ustawienia_profilu.json` (katalog docelowy i data ostatniego
    backupu, Faza 22 — `gui/nastawienia_profilu.py`). Każdy z tych plików
    żył wcześniej płasko pod `%APPDATA%\FakturyPro` (małe, roamingowe) albo
    `%LOCALAPPDATA%\FakturyPro` (logo) — od tej fazy wszystko per-profilowe
    konsoliduje się pod jeden, wspólny korzeń w `%LOCALAPPDATA%`, niezależnie
    od dawnego podziału roaming/local.
  - `%LOCALAPPDATA%\FakturyPro\ustawienia.json` — zostaje GLOBALNE
    (`gui/nastawienia.py`, bez zmian poza przeniesieniem katalogu z `%APPDATA%`
    tutaj): tryb wyglądu, geometria głównego okna, zapamiętane
    filtry/sortowania list. To preferencje UI/monitora, nie dane firmy — ekran
    wyboru profilu też potrzebuje trybu wyglądu, zanim jakikolwiek profil
    zostanie wybrany, więc nie może być per-profilowy. Świadomy,
    zaakceptowany kompromis: otwarcie listy faktur w Firmie B może pokazać
    filtr ostatnio używany w Firmie A — to nieszkodliwy stan UI, nie dane
    biznesowe.
  - `%LOCALAPPDATA%\FakturyPro\pgsql-data\` — bez zmian, współdzielone przez
    wszystkie profile (jeden serwer, wiele baz).
- **Kolejność startu** (`gui/main.py:main()`): blokada pojedynczej instancji →
  tryb wyglądu (globalny) → *(tylko tryb produktowy)* migracja starej
  instalacji (`gui/migracja_profili.py`) → ekran wyboru profilu
  (`gui/windows/ekran_wyboru_profilu.py`) → `ustaw_aktywny_profil()` → *od
  tego miejsca cały dotychczasowy ciąg startu (ekran hasła Fazy 6 → prywatny
  Postgres + backend z paskiem postępu Fazy 18D → kreator pierwszego
  uruchomienia → główne okno) działa bez ŻADNEJ zmiany wewnętrznej logiki*,
  bo operuje na już rozwiązanym profilu.
- **Tworzenie nowego profilu:** `gui/profile_rejestr.py:utworz_nowy_profil()`
  generuje id i nazwę bazy (`faktury_pro_<id>` — jedyne miejsce z tą
  konwencją zakodowaną) i dodaje wpis do rejestru; sama baza/migracje/katalog
  danych powstają naturalnie w dalszym, niezmienionym cyklu startu (kreator
  pierwszego uruchomienia z Fazy 18D uruchamia się dla tego profilu tak samo,
  jak dla jedynej firmy przed Fazą 25).
- **Blokada pojedynczej instancji (`gui/blokada_instancji.py`) zostaje
  GLOBALNA — jeden proces Faktury Pro na raz, NIE per-profil.** Świadoma
  decyzja: FastAPI nasłuchuje na sztywno zakodowanym porcie 8000
  (`gui/main.py:PORT`, `gui/api_client.py:BASE_URL`) i istniejąca logika
  `_serwer_odpowiada()` ("jeśli serwer już odpowiada na 8000, to poprzednia
  sesja — przejmij ją zamiast startować własną") sprawiłaby, że drugi
  równoległy proces dla innej firmy **cicho podłączyłby się do backendu
  pierwszego procesu**, pokazując dane złej firmy pod etykietą dobrej — realne
  złamanie zasady nadrzędnej. Obsługa prawdziwie równoległych okien
  wymagałaby dynamicznego przydziału portów i przebudowy
  `api_client.py`/`_serwer_odpowiada()` — poza zakresem tej fazy. **Żeby
  zmienić firmę, użytkownik zamyka appkę i uruchamia ją ponownie** — trafia z
  powrotem na ekran wyboru profilu. Appka NIE obsługuje przełączania profilu
  w trakcie działania procesu — to celowe uproszczenie (patrz też
  `app/database.py`: jeden globalny `engine`/`SessionLocal` tworzony raz przy
  imporcie, więc przełączenie bazy w locie i tak byłoby bardzo kruche).
- **Migracja instalacji sprzed Fazy 25** (`gui/migracja_profili.py:migruj_jesli_trzeba()`,
  wołane raz na starcie, przed ekranem wyboru profilu): jeśli `profiles.json`
  jeszcze nie istnieje, a stary, płaski `%APPDATA%\FakturyPro\auth.json`
  istnieje — appka PRZENOSI (nie kopiuje) `auth.json`/`ksef.json`/
  `email.json`/`integracje.json`/`logo/`/`ustawienia.json` (z wydzieleniem
  kluczy backupu) do nowej struktury i rejestruje profil `"legacy"`
  wskazujący na **niezmienioną** bazę `faktury_pro` (rename żywej bazy jest
  niepotrzebnym ryzykiem — nazwa bazy jest zapisywana jawnie per-profil w
  rejestrze, nie zawsze wyprowadzana z konwencji `faktury_pro_<id>`).
  Idempotentne — każdy krok sam sprawdza, czy jest jeszcze co robić, więc
  przerwana w połowie migracja bezpiecznie wznawia się przy kolejnym starcie.
- **Backup/przywracanie (Faza 22) są per-profil "za darmo":**
  `gui/kopia_zapasowa.py` już wcześniej derywowało nazwę/adres bazy z
  `app.config.DATABASE_URL` i katalog logo z `gui/logo.py` — oba są teraz
  poprawnie profilowo-świadome bez zmiany logiki, jedyna zmiana to
  przeniesienie katalogu docelowego backupu/daty ostatniego backupu z
  globalnego `nastawienia.py` do per-profilowego `nastawienia_profilu.py`.
  Dodatkowo manifest kopii (`manifest.json` w archiwum `.fpbk`) zyskał pole
  `nazwa_firmy` — przed przywróceniem appka podgląda je
  (`kopia_zapasowa.py:podejrzyj_manifest()`, bez dotykania bazy/serwera) i
  jeśli nie zgadza się z aktywnym profilem, pokazuje dodatkowe ostrzeżenie w
  `gui/windows/dialog_kopii_zapasowej.py:DialogPrzywrocBackup` — chroni przed
  przypadkowym przywróceniem backupu jednej firmy do profilu drugiej.
- **Usuwanie profilu** (Ustawienia → karta "Usuń tę firmę", ukryta w trybie
  deweloperskim): wymaga wpisania dokładnej nazwy firmy (przycisk nieaktywny,
  dopóki tekst się nie zgadza) + drugiego potwierdzenia
  (`messagebox.askyesno`). Po potwierdzeniu: zatrzymanie wątku FastAPI
  (`gui/proces_aplikacji.py:zatrzymaj_serwer_fastapi`, żeby `DROP DATABASE`
  miał się do czego podłączyć bez konfliktu połączeń) → `DROP DATABASE ...
  WITH (FORCE)` (`gui/postgres_serwer.py:usun_baze()`) → skasowanie katalogu
  profilu → usunięcie wpisu z rejestru → **zatrzymanie też prywatnego
  Postgresa** (`proces_aplikacji.zatrzymaj_wszystko()`, dopiero w tym
  momencie — patrz błąd niżej) → wymuszone zamknięcie CAŁEJ appki
  (`os._exit(0)`, appka NIE wraca do ekranu wyboru profilu w tym samym
  procesie — spójnie z brakiem przełączania profilu w locie). Usuwa
  WYŁĄCZNIE dane tego jednego profilu — inne bazy/katalogi profili są
  całkowicie nienaruszone.
- **Znalezione i naprawione na żywo w trakcie weryfikacji tej fazy** (dwa
  osobne przeglądy z realnym klikaniem w izolowanym sandboxie —
  `%LOCALAPPDATA%`/`%APPDATA%` przekierowane na katalog tymczasowy, prawdziwy
  prywatny Postgres, `.env` chwilowo ukryte, żeby appka faktycznie weszła w
  tryb produktowy z profilami):
  - **Osierocony prywatny Postgres po usunięciu profilu.** Pierwsza wersja
    `_usun_profil()` w `widok_ustawien.py` po udanym usunięciu wołała od razu
    `os._exit(0)`, wołając PRZEDTEM tylko `zatrzymaj_serwer_fastapi()` (co
    zostawia proces `postgres.exe` żywy celowo — `DROP DATABASE` potrzebuje
    działającego serwera). Wykryte przez wymuszone zabicie procesu appki w
    trakcie testu (symulacja awarii) — `Get-CimInstance Win32_Process`
    pokazał osierocone `postgres.exe` wskazujące na katalog danych
    właśnie skasowanego profilu, dokładnie ten sam rodzaj problemu, jaki
    `installer.iss` musiał już raz naprawiać w Fazie 18C. Naprawione dodaniem
    `proces_aplikacji.zatrzymaj_wszystko()` (ten sam wzorzec co
    `DialogPrzywrocBackup` po udanym przywróceniu backupu) tuż przed
    `os._exit(0)` — powtórzony na żywo test usunięcia profilu (zamknięcie
    appki normalną ścieżką, nie zabite) potwierdził zero osieroconych
    procesów.
  - **Przypomnienie o backupie: "wykonana None dni temu"** — błąd sprzed tej
    fazy (Faza 22), niezwiązany z profilami, ale trafiony po raz pierwszy
    właśnie w tym sandboxie (katalog docelowy backupu ustawiony, ale jeszcze
    żaden backup nie wykonany — kombinacja stanów, która wcześniej nie miała
    okazji wystąpić w żadnym live-teście). `gui/windows/dialog_przypomnienia_backupu.py`
    zakładał, że skoro `nigdy_skonfigurowano` jest `False`, to
    `dni_od_ostatniego` jest zawsze liczbą — nieprawda, gdy katalog JEST
    ustawiony, ale backup jeszcze nigdy nie powstał. Naprawione trzecim,
    odrębnym wariantem tekstu ("Nie wykonano jeszcze kopii zapasowej") dla
    tego dokładnie stanu.

## Faza 19 — automatyczne generowanie WZ z faktury (Etap 3, zrobione)

Świadomy, jednorazowy skrót dla użytkownika — przycisk "Wygeneruj WZ z tej
faktury" w szczegółach faktury (`gui/windows/szczegoly_faktury.py`), NIE
automatyczna reguła w tle. **Model B (rozłączność faktur i magazynu) pozostaje
domyślnym zachowaniem appki** — ten przycisk tylko wstępnie wypełnia zwykły,
w pełni edytowalny formularz WZ danymi z faktury; użytkownik wciąż świadomie
przegląda/koryguje i zatwierdza, zanim cokolwiek się zapisze. Wystawienie
faktury samo z siebie nadal nigdy nie zmienia stanu magazynowego.

- **Dopasowanie pozycji faktury do towarów magazynowych — po nazwie, nie po
  FK.** `PozycjaFaktury` (Faza 1) nie ma powiązania z `Produkt` — to wolny
  tekst (nazwa/ilość/cena wpisywane ręcznie przy wystawianiu faktury), nawet
  gdy fakturę wystawiono na podstawie towaru z katalogu. Dopasowanie
  (`gui/windows/formularz_wz_z_faktury.py:dopasuj_pozycje_do_produktow`) jest
  więc dokładnym dopasowaniem tekstu nazwy (bez rozróżniania wielkości liter)
  względem aktywnych, magazynowych (`jest_magazynowy=True`) produktów z
  katalogu — świadomie zaakceptowane jako wystarczające, bo formularz i tak
  otwiera się do wglądu/edycji przed zapisem. Pozycje bez dopasowania (usługi
  albo literówka/inna nazwa niż w katalogu) są pomijane z czytelną informacją
  w formularzu, nie blokują generowania reszty.
- **Zero zmian w logice Fazy 8.** Zapis idzie dokładnie tym samym kodem co
  ręczne tworzenie dokumentu magazynowego —
  `app/services/magazyn_service.py:utworz_dokument_magazynowy` przez ten sam
  endpoint `POST /dokumenty-magazynowe` (`gui/api_client.py:utworz_dokument_magazynowy`)
  — więc numeracja, walidacja `jest_magazynowy`, i tryb
  ostrzegaj/blokuj (`Firma.tryb_blokady_ujemnego_stanu`) działają identycznie
  jak zawsze. `DokumentMagazynowy.faktura_powiazana_id` (prawdziwy FK do
  `Faktura.id`, istniejący od migracji Fazy 7) jest po prostu ustawiany wprost
  na id faktury — żadna nowa migracja Alembic nie była potrzebna.
- **Zabezpieczenie przed duplikacją** — `GET /dokumenty-magazynowe` dostał
  nowy, opcjonalny filtr `faktura_powiazana_id` (dokładne dopasowanie po FK,
  nie zgadywanie po numerze jak w wolno-tekstowym polu formularza ręcznego
  tworzenia dokumentu). Gdy dla faktury istnieje już powiązane WZ, przycisk
  zamienia się w link "WZ już wygenerowane: {numer}" otwierający istniejący
  dokument (`gui/windows/szczegoly_dokumentu_magazynowego.py`) zamiast
  pozwalać wygenerować drugie bez ostrzeżenia.
- **Trzy stany przycisku** w `szczegoly_faktury.py`, zależnie od faktury:
  ukryty dla `robocza`/`anulowana`; nieaktywny + wyjaśnienie tekstowe obok
  (mirror istniejącego wzorca "Sprawdź w białej liście" w tym samym ekranie),
  gdy zero pozycji dopasowanych do towaru magazynowego; aktywny w pozostałych
  przypadkach.
- `gui/windows/wiersz_pozycji_magazynowej.py` — wydzielony z
  `formularz_dokumentu_magazynowego.py` (był tam prywatną klasą) do
  współdzielonego pliku, bo Faza 19 też go potrzebuje (ten sam wzorzec co
  `gui/windows/wiersz_pozycji.py` dla pozycji faktur), z dwoma nowymi
  opcjonalnymi parametrami do wstępnego wypełnienia (`produkt_wybrany`,
  `ilosc_poczatkowa`).
- Przy okazji naprawiony drobny, wcześniej istniejący błąd w
  `formularz_dokumentu_magazynowego.py:_zapisz` — `wynik['numer']` zamiast
  `wynik['dokument']['numer']` (odpowiedź `POST /dokumenty-magazynowe` jest
  zagnieżdżona, `UtworzenieDokumentuMagazynowegoOut.dokument`) — powodował
  ciche `KeyError` w callbacku sukcesu PO już udanym zapisie dokumentu (efekt:
  brakujący toast potwierdzenia, dokument i tak zapisany poprawnie).
- **Zweryfikowane:** logika dopasowania (jednostkowo), pełny cykl
  backendu przez warstwę serwisową w transakcji z rollbackiem na bazie
  deweloperskiej (filtr `faktura_powiazana_id` przed/po utworzeniu, oba tryby
  ostrzegaj/blokuj z Fazy 8 przez dokładnie ten sam kod), oraz stan
  skonstruowanych widgetów GUI (wartości pól, liczba i zawartość wstępnie
  wypełnionych wierszy, wszystkie etykiety) przez bezpośrednią introspekcję
  drzewa widgetów — zrzuty ekranu z tej samej sesji były momentami mylące
  (`CTkScrollableFrame` bywa wyrenderowany w przewiniętej pozycji, ten sam
  znany kaprys co przy Fazie 18D), ale introspekcja na żywym obiekcie
  potwierdziła, że wszystkie dane są poprawne niezależnie od tego, co akurat
  pokazał zrzut ekranu.

## Struktura katalogów (docelowa)
```
app/
  models/         # modele SQLAlchemy
  schemas/        # Pydantic schemas
  api/            # routery FastAPI (lokalny serwer, nie publiczny)
  services/       # logika biznesowa (osobno od routerów!)
  templates/      # szablony PDF (WeasyPrint)
gui/
  main.py         # punkt startowy aplikacji desktopowej, odpala/zatrzymuje serwer FastAPI
  windows/        # okna customtkinter (lista faktur, formularz faktury, klienci, magazyn)
  api_client.py   # cienka warstwa `requests` do komunikacji z lokalnym FastAPI
alembic/          # migracje
tests/
```

## KRYTYCZNE reguły biznesowe — nie łam ich

1. **Kwoty pieniężne zawsze jako integer w groszach**, nigdy `float`. Konwersja na złotówki tylko w warstwie prezentacji.
2. **Faktury i magazyn są modelami ROZŁĄCZNYMI (Model B).** Stan magazynowy zmienia się WYŁĄCZNIE przez dokumenty magazynowe (PZ/WZ/PW/RW/MM). Wystawienie faktury NIE zmienia stanu magazynowego automatycznie. WZ może mieć opcjonalne pole referencyjne do numeru faktury, ale to tylko informacja, nie transakcja.
3. **Numeracja dokumentów** (faktur, WZ, PZ itd.) musi być konfigurowalna co do formatu i resetu (miesięczny/roczny), ale zawsze ciągła i bez dziur w ramach jednego roku/rejestru.
4. **Stawki VAT** to zamknięty, konfigurowalny słownik (23%, 8%, 5%, 0%, zw.) — nie hardkoduj wartości w logice, trzymaj w tabeli/enumie.
5. **Towar magazynowy vs usługa** — usługi NIGDY nie przechodzą przez dokumenty magazynowe i nie mają stanu.
6. Każda faza implementowana jest w **izolacji** — nie dotykaj kodu z późniejszych faz, dopóki nie dojdziemy do nich w planie (patrz `PLAN_PROJEKTU.md`).

## Konwencje kodu
- Logika biznesowa w `services/`, routery w `api/` mają być cienkie (walidacja + wywołanie serwisu)
- Nazwy zmiennych/funkcji w kodzie: angielski. Komunikaty dla użytkownika (UI, błędy walidacji): polski.
- Każda migracja Alembic ma opisową nazwę (`add_invoice_status_field`, nie `update1`)
- Commit po każdej zakończonej, działającej funkcjonalności — commit message opisowy po polsku lub angielsku, konsekwentnie

## Wersjonowanie i aktualizacje

Appka ma świadomość własnej wersji i RĘCZNY (nie w pełni automatyczny)
mechanizm dostarczania aktualizacji — CELOWO bez auto-update Poziomu 3
(appka nigdy sama nie podmienia własnych plików w locie, świadomie odłożone
na przyszłość). Appka SAMA, na żądanie użytkownika (przycisk "Sprawdź
aktualizacje" w Ustawieniach), sprawdza dostępność nowszej wersji, pokazuje
changelog, POBIERA gotowy instalator i go URUCHAMIA — ale sama podmiana
plików programu nadal należy WYŁĄCZNIE do istniejącego, sprawdzonego
instalatora Inno Setup (`installer.iss`), dokładnie tego samego, którego
użytkownik uruchomiłby ręcznie po pobraniu ze strony wydań. Zobacz
`app/services/aktualizacje_service.py` (sprawdzanie) i `gui/aktualizacje.py`
(pobieranie + uruchomienie instalatora, Faza 28).

**Trzy miejsca z numerem wersji — przy KAŻDYM wydaniu nowej wersji trzeba
zaktualizować WSZYSTKIE TRZY, ręcznie, w tej kolejności:**

1. **`app/wersja.py`** — stała `WERSJA` — to jest numer wersji, który appka
   o SOBIE wie i pokazuje w Ustawieniach ("Faktury Pro w wersji X.Y.Z") oraz
   z którym porównuje się przy sprawdzaniu aktualizacji. Zmień na nowy numer
   PRZED zbudowaniem instalatora dla tego wydania.
2. **`installer.iss`** — `#define AppWersja "X.Y.Z"` (linia z definicją na
   górze pliku) — numer wersji zbudowanego instalatora (widoczny w nazwie
   pliku wynikowego `FakturyPro-Setup-X.Y.Z.exe`, we właściwościach Windows
   "Aplikacje i funkcje", w tytule kreatora instalacji). MUSI być identyczny
   z `app/wersja.py`, inaczej appka po instalacji pokazywałaby inny numer w
   Ustawieniach niż widniał w nazwie pobranego instalatora — myląco dla
   użytkownika.
3. **`wersja_aktualna.json`** (korzeń repozytorium, od Fazy 28) — plik JSON
   z TRZEMA polami (`wersja`, `url_instalatora` — bezpośredni link do assetu
   GitHub Release, `zmiany` — changelog po polsku pokazywany w appce) — TO
   JEST plik, który appka faktycznie odpytuje przez internet (surowy URL
   GitHub, `https://raw.githubusercontent.com/Kokop91/faktury-pro/main/wersja_aktualna.json`,
   patrz `app/services/aktualizacje_service.py`), żeby wiedzieć, czy istnieje
   coś nowszego niż wersja zainstalowana u użytkownika, i skąd to pobrać.
   **To jedyny krok z tej trójki, który trzeba zrobić PO zbudowaniu I
   opublikowaniu instalatora jako GitHub Release (nie przed)** — `url_instalatora`
   wymaga już istniejącego assetu wydania, więc kolejność jest sztywna.
   Dokładna procedura (w tym JEDNOCZESNA aktualizacja `wersja_aktualna.txt`
   dla wstecznej zgodności) opisana krok po kroku w `CHECKLIST_WYDANIA.md`.

**Wsteczna zgodność (Faza 28):** stary, płaski `wersja_aktualna.txt` (SAMA
linia z numerem wersji, format sprzed Fazy 28) zostaje NIETKNIĘTY i nadal
aktualizowany przy KAŻDYM wydaniu razem z `.json` — appki w wersji ≤1.1.1
(sprzed pobierania w appce) nadal czytają wyłącznie ten plik i muszą go
móc znaleźć aktualny, inaczej nigdy nie dowiedzą się o żadnej kolejnej
wersji. Appka od Fazy 28 w górę czyta WYŁĄCZNIE `.json` (bez logiki
"spróbuj JSON, spadnij na txt") — nie ma ryzyka rozjazdu, bo oba pliki są
publikowane w tym samym kroku checklisty.

**Pobieranie i instalacja w appce (Faza 28, `gui/aktualizacje.py`):** po
wykryciu nowszej wersji appka pokazuje baner z changelogiem i przyciskiem,
który przechodzi przez stany Pobierz → Pobieranie (pasek postępu, wznawialne
przez `Range`, plik zapisywany w `%LOCALAPPDATA%/FakturyPro/aktualizacje/`
jako `<nazwa>.exe.czesciowy` aż do ukończenia, potem atomowy `rename` na
`<nazwa>.exe` — sama obecność pliku bez przyrostka jest dowodem ukończonego
pobrania, appka pomija ponowne pobieranie przy kolejnym otwarciu Ustawień)
→ Zainstaluj (potwierdzenie → `subprocess.Popen` uruchamia pobrany
instalator jako niezależny proces → appka zamyka się przez ten sam wzorzec
co po przywróceniu kopii zapasowej/usunięciu profilu:
`proces_aplikacji.zatrzymaj_wszystko()` + `os._exit(0)`). Błędy sieciowe
(brak internetu, przerwane połączenie, brak miejsca na dysku) pokazywane
nieblokującym Bannerem z osobnym, rozróżnialnym komunikatem dla każdego
przypadku, przycisk wraca do stanu "Spróbuj ponownie" (klik ponawia
DOKŁADNIE to samo pobieranie, wznawiając od miejsca przerwania).

**Numeracja**: proste semver (`MAJOR.MINOR.PATCH`, np. `1.0.0` → `1.1.0`) —
podnoś MINOR przy zamknięciu większej fazy/funkcjonalności, PATCH przy
drobnej poprawce/naprawie błędu. Appka porównuje wersje NUMERYCZNIE (nie
tekstowo), więc `1.10.0` jest poprawnie rozpoznawane jako nowsze niż `1.9.0`.

Pełna procedura publikowania wydania (budowanie, testowanie, publikacja
Release, aktualizacja obu plików wersji): `CHECKLIST_WYDANIA.md`.

## Zasady pracy w tej sesji
- Nie implementuj więcej niż jedną fazę na raz (patrz `PLAN_PROJEKTU.md` za zakresem faz)
- Przed dużymi zmianami strukturalnymi zaproponuj plan (Plan Mode), poczekaj na akceptację
- Po zakończeniu fazy: podsumuj co zostało zrobione i co należy ręcznie przetestować przed przejściem dalej
- Jeśli napotkasz niejednoznaczność w regułach biznesowych, zapytaj — nie zgaduj (szczególnie przy VAT, numeracji, stanach magazynowych)

## Pełny plan projektu
Zobacz `PLAN_PROJEKTU.md` w tym repozytorium — zawiera pełny zakres funkcjonalny, model danych i harmonogram faz.
