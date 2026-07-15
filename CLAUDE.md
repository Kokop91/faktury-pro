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
- **Integracja z KSeF (Faza 12A, zrobione — fundament + uwierzytelnianie, BEZ wysyłki
  faktur):** obsługa API KSeF 2.0 (Krajowy System e-Faktur, Ministerstwo Finansów),
  metoda uwierzytelniania "token KSeF" (nie certyfikat/XAdES — to poza zakresem 12A).
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
  - **Warstwa serwisowa:** `app/services/ksef_service.py` — pełny cykl uwierzytelnienia
    (challenge → szyfrowanie RSA-OAEP/SHA-256 tokenu → `/auth/ksef-token` → odpytywanie
    statusu → `/auth/token/redeem`), wywoływany przyciskiem "Testuj połączenie z KSeF"
    w Ustawieniach. accessToken/refreshToken z redeem NIE są nigdzie zapisywane — to
    tylko test działania, wysyłka faktur to kolejna faza (12B, patrz
    `ETAP_2_ROZWOJU.md`).
  - Mechanizm i adresy zweryfikowane wprost z oficjalnej dokumentacji Ministerstwa
    Finansów (`github.com/CIRFMF/ksef-api`) i z żywego środowiska testowego, nie
    zgadywane.
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
