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
- **Baza danych:** PostgreSQL
- **ORM/migracje:** SQLAlchemy + Alembic
- **PDF:** WeasyPrint (HTML → PDF)
- **Frontend/UI:** **customtkinter** — aplikacja desktopowa komunikująca się z FastAPI przez
  bibliotekę `requests` (ten sam wzorzec co w projekcie SecureChat autora: FastAPI backend +
  customtkinter GUI)
- **Uruchamianie serwera:** aplikacja customtkinter odpala FastAPI/uvicorn jako subprocess
  przy starcie i zatrzymuje go przy zamknięciu okna — użytkownik końcowy nie widzi ani nie
  obsługuje serwera bezpośrednio, dla niego ma to wyglądać jak zwykły, pojedynczy program
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

## Zasady pracy w tej sesji
- Nie implementuj więcej niż jedną fazę na raz (patrz `PLAN_PROJEKTU.md` za zakresem faz)
- Przed dużymi zmianami strukturalnymi zaproponuj plan (Plan Mode), poczekaj na akceptację
- Po zakończeniu fazy: podsumuj co zostało zrobione i co należy ręcznie przetestować przed przejściem dalej
- Jeśli napotkasz niejednoznaczność w regułach biznesowych, zapytaj — nie zgaduj (szczególnie przy VAT, numeracji, stanach magazynowych)

## Pełny plan projektu
Zobacz `PLAN_PROJEKTU.md` w tym repozytorium — zawiera pełny zakres funkcjonalny, model danych i harmonogram faz.
