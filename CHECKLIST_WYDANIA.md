# Checklist wydania nowej wersji Faktury Pro

Krok po kroku, w tej dokładnej kolejności, przy każdym wydaniu nowej wersji
aplikacji dla użytkownika końcowego (np. znajomego). Każdy krok odwołuje się
do konkretnego, istniejącego w repozytorium mechanizmu — nic tu nie jest
wymyślone na potrzeby tego dokumentu.

## 1. Podnieś numer wersji (trzy miejsca, w tej kolejności)

Pełny opis mechanizmu: `CLAUDE.md`, sekcja "Wersjonowanie i aktualizacje".

1. **`app/wersja.py`** — stała `WERSJA`. To jedyne miejsce, z którego appka
   sama zna swój numer (widoczny w Ustawieniach: "Faktury Pro w wersji X.Y.Z").
2. **`installer.iss`** — `#define AppWersja "X.Y.Z"` (linia 28). MUSI być
   identyczna z `app/wersja.py`, inaczej appka po instalacji pokazywałaby
   inny numer niż widniał w nazwie pobranego instalatora.
3. **`wersja_aktualna.txt` i `wersja_aktualna.json`** (korzeń repozytorium) —
   **JESZCZE NIE TERAZ**. Te pliki zmieniasz dopiero w kroku 6, PO
   opublikowaniu instalatora jako GitHub Release — appka porównuje się z
   nimi przez internet (`app/services/aktualizacje_service.py`), więc zmiana
   za wcześnie poinformowałaby już istniejących użytkowników o wersji,
   której jeszcze nie da się pobrać (`.json` zawiera bezpośredni link do
   assetu wydania, który w ogóle jeszcze nie istnieje przed krokiem 6).

Numeracja: proste semver (`MAJOR.MINOR.PATCH`). Podnieś **MINOR** przy
zamknięciu większej fazy/funkcjonalności, **PATCH** przy drobnej poprawce.
Appka porównuje wersje numerycznie, nie tekstowo (`1.10.0` poprawnie uznane
za nowsze niż `1.9.0`).

## 2. Upewnij się, że w wysyłanym instalatorze nie ma Twoich danych testowych

Architektura appki czyni to ryzyko strukturalnie bardzo małym, ale warto
świadomie zweryfikować, nie zakładać:

- **Instalator (`Output/FakturyPro-Setup-X.Y.Z.exe`) fizycznie nie może
  zawierać Twoich danych.** `installer.iss` (`[Files]`) pakuje wyłącznie
  `dist\Faktury Pro\*` — pliki programu z PyInstallera. Katalog z danymi
  użytkownika (`%LOCALAPPDATA%\FakturyPro` — prywatna baza, hasła, profile
  firm, patrz `CLAUDE.md` sekcja "Wiele profili firm") nigdy nie jest
  częścią `[Files]`.
- **Prywatna baza danych appki u KAŻDEGO użytkownika (w tym Ciebie, gdy
  testujesz zbudowany `.exe`) powstaje od zera przy pierwszym uruchomieniu**
  (`initdb`, `gui/postgres_serwer.py`) w `%LOCALAPPDATA%\FakturyPro\pgsql-data`
  — zawsze pusta, niezależnie od tego, czym testujesz appkę w trybie
  deweloperskim (`.env` z `DATABASE_URL` wskazującym na Twoją własną, ręcznie
  zarządzaną bazę — ta baza NIGDY nie jest dotykana przez appkę w trybie
  spakowanym, `.env` w ogóle nie jest częścią builda, patrz niżej).
- Dla pewności, przed budowaniem sprawdź, że `vendor/postgresql/pgsql/`
  (pobrane jednorazowo przez `scripts/pobierz_postgres_portable.py`) zawiera
  WYŁĄCZNIE binaria (`bin/`, `lib/`, `share/`) — żadnego podkatalogu z danymi.
  `scripts/dolacz_postgres_do_buildu.py` kopiuje tę zawartość do gotowego
  builda bez wyjątków, więc coś ręcznie dorzuconego tam trafiłoby dalej.
- `.env` (dev-owy `DATABASE_URL`) nie jest nigdzie wymieniony w `datas`
  w `faktury_pro.spec` — nie ma ryzyka, że PyInstaller przypadkiem go
  spakuje.

## 3. Uruchom weryfikację

W repozytorium **nie ma obecnie zautomatyzowanego zestawu testów** — brak
katalogu `tests/`, brak konfiguracji pytest, brak workflow CI (sprawdzone
wprost w repo, nie zakładane). Weryfikacja przed wydaniem jest więc ręczna:

- Uruchom appkę w trybie deweloperskim (`python -m gui.main`, z `.env`) i
  przejdź główne ścieżki dotyczące tego wydania — nową funkcjonalność oraz
  najbliższe okolice kodu, który zmieniałeś.
- Jeśli zmiana dotyka startu appki, bazy danych, migracji Alembic,
  backupu/przywracania albo profili firm — te ścieżki są szczególnie
  kosztowne w razie błędu (realne dane finansowe użytkownika). Przetestuj je
  "na żywo", nie tylko przez czytanie kodu: uruchom appkę w trybie
  produktowym z `LOCALAPPDATA`/`APPDATA` przekierowanymi na pusty katalog
  tymczasowy (izolacja od Twoich prawdziwych danych deweloperskich), tak jak
  w sesjach weryfikujących migrację profili i backup w Fazie 25.

## 4. Zbuduj appkę i instalator

Dokładne komendy (z `faktury_pro.spec` i `installer.iss`), w tej kolejności:

```powershell
pip install -r requirements.txt -r requirements-build.txt
python scripts/pobierz_postgres_portable.py      # tylko JEDNORAZOWO na danej maszynie budującej, jeśli vendor/ jeszcze nie istnieje
pyinstaller faktury_pro.spec --noconfirm
python scripts/dolacz_postgres_do_buildu.py
"C:\Tools\InnoSetup6\ISCC.exe" installer.iss     # albo dowolna inna instalacja Inno Setup 6
```

Kolejność jest sztywna: `dolacz_postgres_do_buildu.py` wymaga już istniejącego
`dist\Faktury Pro\`, a `installer.iss` pakuje `dist\Faktury Pro\*` razem z
dołączonymi binariami Postgresa — musi być ostatni.

Wynik pośredni: `dist\Faktury Pro\Faktury Pro.exe` (folder `--onedir`).
Wynik końcowy do wysłania: `Output\FakturyPro-Setup-X.Y.Z.exe`.

## 5. Przetestuj na czystym środowisku, zanim wyślesz dalej

1. Zainstaluj świeżo zbudowany `Output\FakturyPro-Setup-X.Y.Z.exe` na czystym
   koncie/maszynie (albo tymczasowo przekieruj `LOCALAPPDATA`/`APPDATA` na
   pusty katalog na własnej maszynie), żeby appka faktycznie uruchomiła się
   bez żadnych wcześniej istniejących danych.
2. Potwierdź pełną ścieżkę pierwszego uruchomienia: ekran wyboru profilu
   (Faza 25) → "Dodaj nową firmę" → 3 kroki kreatora pierwszego uruchomienia
   (Faza 18D) → dashboard.
3. **Jeśli to wydanie wprowadza mechanizm migracji istniejących danych po raz
   pierwszy dla danego odbiorcy** — w szczególności NAJBLIŻSZE wydanie
   zawierające Fazę 25 (wiele profili firm) dla każdego, kto ma już starszą,
   jednofirmową wersję zainstalowaną — dodatkowo przetestuj ścieżkę
   aktualizacji z zachowaniem danych, nie tylko czystą instalację: zainstaluj
   nową wersję NAD już działającą starą (z jakimiś realnymi/testowymi
   danymi), potwierdź że appka automatycznie wykrywa i migruje istniejące
   dane bez utraty dostępu (`gui/migracja_profili.py`, opisane w `CLAUDE.md`
   sekcja "Wiele profili firm"). Dla kolejnych wydań PO tym momencie (odbiorca
   ma już profile) ten krok się nie powtarza — zwykłe `alembic upgrade head`
   obsługuje dalsze zmiany schematu automatycznie i bezpiecznie.
4. Wystaw testową fakturę, sprawdź generowanie PDF, zamknij appkę i sprawdź w
   Menedżerze zadań, że nie zostaje żaden osierocony proces `postgres.exe`
   (patrz `CLAUDE.md`, "Faza 18C" — historyczny błąd, który już raz trzeba
   było naprawiać).
5. Jeśli wydanie dotyka Ustawień/backupu — sprawdź też przycisk "Zgłoś
   problem" (Faza 26): czy tworzy plik ZIP na Pulpicie i czy jego zawartość
   nie zawiera niczego wrażliwego (patrz `gui/diagnostyka.py`).

## 6. Opublikuj instalator i DOPIERO TERAZ zaktualizuj pliki wersji

Od Fazy 28 (pobieranie aktualizacji w appce) appka NIE czyta już samego
numeru wersji — potrzebuje też bezpośredniego linku do pliku instalatora i
opisu zmian. Kolejność jest sztywna, bo krok 2 wymaga linku, który powstaje
dopiero w kroku 1:

1. **Udostępnij instalator na GitHubie jako Release** (nie samo wgranie pliku
   gdziekolwiek — appka pobiera go bezpośrednio z assetu wydania):
   - `github.com/Kokop91/faktury-pro` → "Releases" → "Draft a new release".
   - Tag np. `vX.Y.Z`, dołącz `Output\FakturyPro-Setup-X.Y.Z.exe` jako asset.
   - Opublikuj wydanie. Skopiuj bezpośredni URL assetu — link pod prawym
     klawiszem myszy na nazwie pliku na stronie wydania, w formacie
     `https://github.com/Kokop91/faktury-pro/releases/download/vX.Y.Z/FakturyPro-Setup-X.Y.Z.exe`.
2. **Zaktualizuj `wersja_aktualna.json`** (korzeń repozytorium) — TRZY pola:
   ```json
   {
     "wersja": "X.Y.Z",
     "url_instalatora": "<dokładny URL assetu skopiowany w kroku 1>",
     "zmiany": "- Punkt pierwszy zmiany\n- Punkt drugi zmiany\n- ..."
   }
   ```
   `zmiany` to changelog pokazywany w banerze aktualizacji w appce (patrz
   `gui/windows/widok_ustawien.py`) — pisz po polsku, bez żargonu, z
   perspektywy użytkownika ("Naprawiono błąd logowania po zmianie firmy", nie
   "Naprawiono race condition w app/profil.py"). Nowe linie w polu `zmiany`
   to dosłowne `\n` wewnątrz stringa JSON (jedna linia = jeden punkt).
3. **Zaktualizuj TEŻ `wersja_aktualna.txt`** (JEDNA linia, sam numer wersji,
   bez zmian od Fazy 6) — appki sprzed Fazy 28 (≤1.1.1) nadal czytają
   WYŁĄCZNIE ten plik i nigdy nie zobaczą `.json`; musi zostać zsynchronizowany
   z `wersja_aktualna.json`, żeby te starsze instalacje też wiedziały o
   nowej wersji (bez changelogu/linku bezpośredniego — dostają tylko numer i
   link do ogólnej strony wydań, tak jak przed Fazą 28).
4. `git commit` + `git push` OBU plików razem na `main`. Appka użytkownika
   (w wersji ≥ zawierającej Fazę 28) pokaże baner z changelogiem i przyciskiem
   "Pobierz aktualizację" dopiero po tym kroku, przy najbliższym ręcznym
   kliknięciu "Sprawdź aktualizacje" w Ustawieniach — appka nigdy nie
   sprawdza tego sama w tle.

## 7. Co wysłać odbiorcy

- **Jeśli odbiorca ma już zainstalowaną wersję z Fazy 28 lub nowszą**: NIC
  wysyłać nie trzeba — sam kliknie "Sprawdź aktualizacje" → "Pobierz
  aktualizację" → "Zainstaluj aktualizację" w Ustawieniach, appka pobierze
  instalator z Release i sama go uruchomi (patrz `gui/aktualizacje.py`).
  Warto tylko dać znać, że nowa wersja jest dostępna (appka NIGDY nie
  sprawdza automatycznie w tle).
- **W przeciwnym razie (pierwsza instalacja, albo bardzo stara wersja
  sprzed Fazy 28)**: wyślij sam plik `Output\FakturyPro-Setup-X.Y.Z.exe`. To
  jedyny plik, jaki trzeba pobrać i uruchomić — instalacja jest
  per-użytkownik, bez uprawnień administratora (`installer.iss`,
  `PrivilegesRequired=lowest`).
- **Krótka informacja co robić** (dla ręcznej instalacji): jeśli odbiorca ma
  już starszą wersję zainstalowaną, wystarczy uruchomić nowy instalator NAD
  istniejącą instalacją — dane zostają zachowane, instalator sam poprosi o
  zamknięcie appki, jeśli akurat działa (`CloseApplications=yes`). Nie trzeba
  nic odinstalowywać ręcznie.
- **Nowa instrukcja obsługi — TYLKO jeśli coś zmieniło się w sposobie
  korzystania z appki** (nowy ekran, nowy krok w istniejącym procesie, nowa
  ważna funkcja — np. ekran wyboru profilu z Fazy 25 albo przycisk "Zgłoś
  problem" z Fazy 26): kilka zdań po polsku, bez żargonu, co jest nowe i jak
  z tego skorzystać. Jeśli wydanie to same poprawki błędów bez zmian
  widocznych dla użytkownika, taka instrukcja nie jest potrzebna.
- Warto przypomnieć odbiorcy o przycisku **"Zgłoś problem"** w Ustawieniach
  (Faza 26) — jeśli appka będzie się kiedyś zachowywać niepoprawnie, sam
  przygotuje plik diagnostyczny do wysłania Tobie mailem, bez potrzeby
  opisywania czegokolwiek technicznego.
