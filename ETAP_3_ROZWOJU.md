# Faktury Pro — Etap 3 rozwoju aplikacji

Wersja: 1.0
Data: lipiec 2026
Status: planowanie — do rozpoczęcia po ukończeniu Etapu 2

---

## Wprowadzenie i cel Etapu 3

Etap 1 dał kompletną aplikację desktopową do fakturowania i magazynu. Etap 2 dodał zgodność
prawną (KSeF, JPK) i unowocześnił interfejs. **Etap 3 ma dwa równoległe cele:**

1. **Produktyzacja** — przekształcenie aplikacji z "projektu uruchamianego przez programistę
   w terminalu" w **gotowy produkt**: jeden instalator, brak wymogu znajomości Pythona,
   terminala, Gita czy baz danych. Znajomy (i każdy przyszły użytkownik) ma móc pobrać jeden
   plik, kliknąć dwa razy, i korzystać z aplikacji tak jak z każdego innego programu na Windows.

2. **Dokończenie backlogu funkcjonalnego** — pozycje świadomie odłożone w Etapie 1
   (automatyzacja WZ z faktury) oraz zidentyfikowane w analizie rynkowej przed Etapem 2
   (linki płatnicze, split payment).

### Dlaczego produktyzacja idzie PIERWSZA

Pakowanie aplikacji w gotowy instalator dotyka fundamentów: jak appka startuje swój serwer,
gdzie fizycznie żyje baza danych, jak wygląda pierwsze uruchomienie. Lepiej ustabilizować to
teraz, budując na sprawdzonym procesie pakowania każdą kolejną funkcję, niż dokładać funkcje
i odkryć problemy architektoniczne dopiero na samym końcu.

### Kluczowe ustalenie techniczne — jak NIE pakować PostgreSQL

Z doświadczeń społeczności PostgreSQL: nigdy nie należy dołączać standardowego instalatora
PostgreSQL jako cichej instalacji wewnątrz instalatora własnej aplikacji — koliduje to
z istniejącymi instalacjami PostgreSQL na komputerze użytkownika, pojawia się osobno na
liście "Dodaj/Usuń programy", i myli użytkownika, który nie wie skąd się wzięło. Zalecane
podejście: dystrybucja **przenośnych binariów PostgreSQL** (bez instalatora), z prywatnym
folderem danych aplikacji, uruchamiana na niestandardowym porcie i zarządzana bezpośrednio
przez samą aplikację (analogicznie do tego, jak aplikacja już zarządza serwerem FastAPI
od Fazy 4 Etapu 1).

Do pakowania samej aplikacji Python w plik wykonywalny standardowym, sprawdzonym narzędziem
jest PyInstaller — bundluje interpreter Pythona i wszystkie zależności w jeden pakiet,
użytkownik nie potrzebuje mieć zainstalowanego Pythona. Zwykle łączy się to z osobnym
narzędziem do tworzenia właściwego instalatora Windows (Inno Setup lub NSIS), bo sam
PyInstaller tworzy plik wykonywalny, a nie instalator.

---

## Przegląd faz Etapu 3

| Faza | Nazwa | Priorytet | Szacowany czas | Sesje CC |
|---|---|---|---|---|
| 18 | Produktyzacja: pakowanie aplikacji + prywatny PostgreSQL + instalator + kreator pierwszego uruchomienia | KRYTYCZNY | 15-25h | 6-9 |
| 19 | Automatyczne generowanie WZ z faktury (Model A jako opcja) | Niski | 3-5h | 1-2 |
| 20 | Linki płatnicze przy fakturach | Średni | 5-8h | 2-3 |
| 21 | Split payment (mechanizm podzielonej płatności) | Niski | 3-5h | 1-2 |

**Suma Etapu 3: ~26-43h, 10-16 sesji.** Przy 3-4 sesjach/tydzień: **4-6 tygodni.**

**Pominięte z pierwotnego backlogu (patrz uzasadnienie w sekcji na końcu):**
wielu użytkowników / kilka stanowisk, aplikacja mobilna, OCR faktur kosztowych.

---

## FAZA 18 — Produktyzacja aplikacji

Najbardziej rozbudowana faza całego projektu pod względem liczby ruchomych części. Podzielona
na pięć podfaz, każda to osobna sesja Claude Code.

### 18A — Pakowanie aplikacji przez PyInstaller

```
Rozpoczynamy Etap 3: Fazę 18 — produktyzację aplikacji Faktury Pro. Celem całej Fazy 18 jest
dostarczenie JEDNEGO instalatora Windows, po którego uruchomieniu użytkownik NIE musi znać
Pythona, terminala, Gita ani administracji bazami danych — appka ma działać jak każdy inny
zwykły program.

Zaimplementuj część 18A: pakowanie samej aplikacji (GUI customtkinter + logika FastAPI)
przez PyInstaller.

WAŻNA PUŁAPKA DO ROZWIĄZANIA NA START: obecnie gui/main.py uruchamia serwer FastAPI jako
osobny podproces przez wywołanie "python -m uvicorn ...". Po spakowaniu przez PyInstaller
NIE będzie dostępnego pliku python.exe do wywołania w ten sposób. Zmień architekturę startu
serwera na jedną z dwóch metod (wybierz sensowniejszą, uzasadnij mi decyzję):
a) uruchamianie serwera uvicorn programowo, w osobnym wątku (threading) WEWNĄTRZ tego samego
   procesu co GUI, zamiast jako podproces — prostsze po spakowaniu, ale sprawdź czy nie
   koliduje z event loopem FastAPI/customtkinter
b) spakowanie backendu jako osobny plik .exe, wywoływany przez GUI z poprawną, względną
   ścieżką działającą zarówno w trybie deweloperskim jak i spakowanym (sys.frozen check)

DRUGA PUŁAPKA: WeasyPrint (z Fazy 3) wymaga natywnych bibliotek Pango/MSYS2 na Windows —
sprawdź, czy PyInstaller poprawnie wykrywa i dołącza te zależności natywne (DLL), czy trzeba
je dodać ręcznie jako "binaries" w pliku .spec. Przetestuj generowanie PDF w SPAKOWANEJ wersji,
nie tylko w trybie deweloperskim — to częste miejsce, gdzie pakowanie się psuje po cichu.

TRZECIA PUŁAPKA: matplotlib (z Fazy 16B) też bywa problematyczny z PyInstalerem (backendy
renderowania) — zweryfikuj że wykres na dashboardzie działa w spakowanej wersji.

Zakres:
1. Skonfiguruj PyInstaller (plik .spec) dla całej aplikacji: GUI + logika backendu + wszystkie
   zależności (customtkinter, FastAPI, SQLAlchemy, WeasyPrint + jego natywne biblioteki,
   matplotlib, psycopg2, bcrypt, wszystko co zostało dodane przez Etap 1 i 2)
2. Użyj trybu --windowed (bez okna konsoli w tle) i strukturę --onedir (nie --onefile) —
   onedir jest zalecany do dystrybucji, mimo że onefile wygląda "czyściej", bo jest bardziej
   niezawodny i szybszy przy starcie
3. Zweryfikuj, że wszystkie ścieżki do plików (szablony PDF, ikony z Fazy 16A, zasoby) używają
   poprawnego mechanizmu resolwowania ścieżek działającego zarówno w trybie deweloperskim jak
   i spakowanym (sys._MEIPASS lub odpowiednik)
4. Zbuduj i przetestuj: appka ma się uruchomić z folderu dist/ na czystym Windows (bez
   zainstalowanego Pythona, bez aktywowanego venv) i przejść przez logowanie, wystawienie
   faktury, wygenerowanie PDF, dashboard z wykresem

NIE zajmuj się jeszcze PostgreSQL (to 18B) ani właściwym instalatorem (to 18C) — na razie
tylko sam plik wykonywalny aplikacji, testowany przy istniejącej, ręcznie uruchomionej
bazie danych (tak jak dotychczas w rozwoju).

Na koniec: dokładna instrukcja jak zbudować (komenda PyInstaller) i jak przetestować że
spakowana wersja działa identycznie jak wersja deweloperska, ze szczególnym naciskiem na
PDF i wykres.
```

### 18B — Prywatny, przenośny PostgreSQL

```
Kontynuujemy Fazę 18 (produktyzacja). Część 18A (pakowanie aplikacji przez PyInstaller)
jest ukończona i zmergowana.

Zaimplementuj część 18B: prywatna, przenośna instancja PostgreSQL zarządzana przez samą
aplikację — użytkownik końcowy NIGDY nie ma świadomości, że PostgreSQL w ogóle istnieje,
nie instaluje go osobno, nie konfiguruje.

ZASADA NADRZĘDNA (z doświadczeń społeczności PostgreSQL): NIE używaj standardowego
instalatora PostgreSQL uruchamianego po cichu — koliduje z ewentualnymi innymi instalacjami
PostgreSQL na komputerze użytkownika. Zamiast tego użyj przenośnej dystrybucji binariów
PostgreSQL (wersja .zip, bez instalatora) dołączonej do plików aplikacji.

Zakres:
1. Sprawdź aktualnie dostępne źródło przenośnych binariów PostgreSQL dla Windows (np.
   oficjalne archiwum binarne z postgresql.org lub EnterpriseDB, bez instalatora .exe) —
   jeśli nie masz pewności co do aktualnego źródła/wersji, zapytaj mnie zamiast zgadywać
2. Struktura folderów prywatnych dla aplikacji: dane binarne PostgreSQL i folder danych
   (data directory) mają żyć w folderze danych użytkownika (odpowiednik %LOCALAPPDATA%\
   FaktuyPro\ na Windows) — NIE w Program Files (unikamy wymogu uprawnień administratora
   przy pierwszym uruchomieniu)
3. Logika w gui/ (rozszerzenie zarządzania procesami z Fazy 4):
   - Przy pierwszym uruchomieniu: jeśli folder danych PostgreSQL nie istnieje, wykonaj
     initdb żeby go utworzyć
   - Uruchomienie PostgreSQL na niestandardowym, dedykowanym porcie (żeby nie kolidować
     z ewentualnym innym PostgreSQL na tym komputerze) przez pg_ctl, zarządzane jako
     podproces analogicznie do serwera FastAPI
   - Zatrzymanie PostgreSQL przy zamknięciu aplikacji (pg_ctl stop), analogicznie do
     istniejącej logiki zamykania serwera FastAPI
   - Health-check przed uruchomieniem GUI, tak jak już jest zaimplementowane dla FastAPI
4. Zaktualizuj CLAUDE.md o nową architekturę: gdzie żyje baza, jak jest zarządzana,
   że to NIE jest system-wide instalacja PostgreSQL

Zastosuj się do CLAUDE.md. To zmiana fundamentalna dla dystrybucji — testuj dokładnie
scenariusz: czysty komputer bez ŻADNEGO PostgreSQL zainstalowanego wcześniej, uruchomienie
appki po raz pierwszy, i scenariusz gdzie na komputerze JEST już inny PostgreSQL (upewnij
się że się nie gryzą, różne porty, różne dane).

Na koniec: jak przetestować oba scenariusze (czysty komputer / komputer z istniejącym
PostgreSQL), i co zrobić, żeby zweryfikować że dane nie giną między uruchomieniami appki.
```

### 18C — Właściwy instalator Windows

```
Kontynuujemy Fazę 18 (produktyzacja). Części 18A (PyInstaller) i 18B (prywatny PostgreSQL)
są ukończone i zmergowane.

Zaimplementuj część 18C: instalator Windows łączący wszystko w jeden plik do dystrybucji.

Zakres:
1. Skonfiguruj Inno Setup (lub uzasadnij, jeśli proponujesz NSIS zamiast tego) — skrypt
   instalatora obejmujący: pliki z PyInstaller (18A), przenośne binaria PostgreSQL (18B)
2. Instalacja per-użytkownik (NIE wymagająca uprawnień administratora) — instaluj do
   folderu w profilu użytkownika, nie do Program Files, żeby uniknąć okna UAC utrudniającego
   życie osobie bez uprawnień administratora na swoim komputerze firmowym
3. Skrót na pulpicie i w Menu Start, z ikoną aplikacji
4. Deinstalator: usuwa pliki aplikacji; ZAPYTAJ użytkownika czy usunąć też dane (bazę,
   wystawione faktury) czy je zachować — domyślnie ZACHOWAJ (nieodwracalne usunięcie danych
   firmowych bez wyraźnej zgody byłoby zbyt ryzykowne)
5. Nazwa i wersja instalatora zgodne z projektem (np. FakturyPro-Setup-1.0.0.exe)

Zastosuj się do CLAUDE.md. Zbuduj kompletny instalator i przetestuj na czystej maszynie
(lub czystym koncie użytkownika Windows) pełen cykl: instalacja → pierwsze uruchomienie →
deinstalacja z zachowaniem danych → ponowna instalacja → dane nadal na miejscu.

Na koniec: dokładna instrukcja budowania instalatora i pełny scenariusz testowy instalacja/
deinstalacja.
```

### 18D — Kreator pierwszego uruchomienia

```
Kontynuujemy Fazę 18 (produktyzacja). Części 18A-18C są ukończone i zmergowane.

Zaimplementuj część 18D: kreator pierwszego uruchomienia (First-Run Setup Wizard),
zastępujący WSZYSTKIE ręczne kroki, które dotychczas wykonywał programista przez terminal
podczas developmentu (ręczne "python -c" wstawiające dane testowej firmy, ręczne
"alembic upgrade head", ręczne tworzenie bazy).

Zakres:
1. Wykrywanie pierwszego uruchomienia: brak zainicjowanej bazy danych LUB brak rekordu
   Firma → uruchom kreator zamiast głównego okna aplikacji
2. Automatyczne wykonanie migracji Alembic przy starcie, jeśli baza nie jest na najnowszej
   wersji — użytkownik nie wykonuje tego ręcznie nigdy, appka robi to sama i pokazuje
   prosty pasek postępu / komunikat "Przygotowywanie aplikacji..."
3. Ekran 1 kreatora: dane firmy (nazwa, NIP, adres, dane bankowe, logo — pola z modelu
   Firma z Fazy 1), z opcjonalnym przyciskiem "Pobierz z GUS" (z Fazy 14, jeśli już
   zaimplementowane)
4. Ekran 2 kreatora: ustawienie hasła do aplikacji (integracja z mechanizmem z Fazy 6 —
   to samo okno "Ustaw hasło", tylko teraz jako część spójnego kreatora, nie osobny ekran)
5. Ekran 3 (opcjonalny, z możliwością pominięcia i skonfigurowania później): podstawowe
   ustawienia — domyślna stawka VAT, format numeracji faktur, środowisko KSeF (domyślnie
   TESTOWE, z wyraźnym wyjaśnieniem czym się różni od PRODUKCYJNEGO dla osoby nietechnicznej)
6. Po zakończeniu kreatora: normalne uruchomienie głównego okna aplikacji

Zastosuj się do CLAUDE.md, użyj tokenów motywu z 16A. To pierwszy kontakt użytkownika
z aplikacją — priorytetem jest prostota języka (zero żargonu technicznego) i niemożność
utknięcia w martwym punkcie (zawsze jasne, co robić dalej, możliwość cofnięcia się).

Na koniec: pełny scenariusz testowy kreatora od zera (usunięcie/przeniesienie folderu danych,
żeby zasymulować zupełnie nowego użytkownika), oraz test że przy KOLEJNYM uruchomieniu
kreator się już nie pojawia.
```

### 18E — Ostatnia weryfikacja produktyzacji (opcjonalna, zalecana)

Po 18A-18D warto przeprowadzić jeden pełny test na komputerze, który **nigdy wcześniej nie
miał nic związanego z projektem** (żaden Python, żaden PostgreSQL, żadne repozytorium) —
najlepiej fizycznie inny komputer albo czysta maszyna wirtualna. To jedyny sposób, żeby
mieć pewność, że znajomy faktycznie uruchomi to jednym kliknięciem. Prompt do tego testu
przygotować po ukończeniu 18D, w zależności od tego, co się wtedy okaże.

---

## FAZA 19 — Automatyczne generowanie WZ z faktury

Odłożone w Etapie 1 jako "Model A jako opcja" — teraz, gdy oba moduły (faktury, magazyn)
są dojrzałe i przetestowane, można to dodać jako świadomą, opcjonalną automatyzację.

### Zarys (pełny prompt przygotować po ukończeniu Fazy 18)
- Przycisk "Wygeneruj WZ z tej faktury" w widoku szczegółów faktury — świadoma, jednorazowa
  akcja użytkownika, NIE automatyczna reguła w tle
- Działa tylko dla pozycji faktury odpowiadających towarom magazynowym (usługi pomijane)
- Wybór magazynu źródłowego przy generowaniu
- Zachowuje Model B jako domyślny — to jest dodatkowa wygoda, nie zmiana fundamentalnej
  zasady rozłączności modułów

---

## FAZA 20 — Linki płatnicze przy fakturach

Z analizy rynkowej: linki płatnicze przy fakturach realnie podnoszą odsetek terminowych
płatności w porównaniu do tradycyjnego przelewu.

### Zarys (pełny prompt przygotować po ukończeniu Fazy 19)
- Integracja z bramką płatności (do wyboru razem z Tobą — np. Przelewy24 lub podobna
  popularna w Polsce, w zależności od tego, z którą znajomy ma już założone konto firmowe)
- Generowanie linku płatniczego przy wystawieniu faktury, umieszczenie go na PDF (kod
  QR lub URL)
- Webhook/sprawdzanie statusu płatności, automatyczne oznaczanie faktury jako opłaconej
  po potwierdzeniu z bramki
- WYMAGA: konta firmowego znajomego w wybranej bramce płatności i danych API — do ustalenia
  zanim zaczniecie tę fazę

---

## FAZA 21 — Split payment (mechanizm podzielonej płatności)

### Zarys (pełny prompt przygotować po ukończeniu Fazy 20)
- Oznaczenie na fakturze, czy dotyczy jej obowiązkowy split payment (zależnie od kategorii
  towarów/usług objętych mechanizmem oraz progu kwotowego zgodnie z przepisami — do
  zweryfikowania w aktualnych przepisach przed implementacją, podobnie jak przy KSeF/JPK)
- Odpowiednia adnotacja na PDF faktury
- Osobne pole rachunku VAT w danych bankowych firmy

---

## Funkcje pominięte z pierwotnego backlogu — uzasadnienie

| Funkcja | Dlaczego pominięta na razie |
|---|---|
| Wielu użytkowników / kilka stanowisk | Sprzeczne z fundamentalną decyzją architektoniczną podjętą po Fazie 2 (aplikacja desktopowa, jednostanowiskowa, bez JWT/sesji wieloużytkownikowych). Dodanie tego wymagałoby powrotu do pełnego auth i prawdopodobnie zmiany modelu wdrożenia (serwer współdzielony zamiast lokalnego). Warte rozważenia jako odrębny, duży projekt — nie "dopisanie funkcji" |
| Aplikacja mobilna / dostęp zdalny | Wymaga innej architektury (appka lokalna nie jest dostępna spoza komputera, na którym działa) — podobnie duża zmiana jak wyżej |
| OCR faktur kosztowych | Trudne do zrobienia dobrze bez usługi chmurowej OCR — kłóci się z filozofią "dane lokalnie, offline-first", która jest przewagą konkurencyjną aplikacji (patrz analiza rynkowa z Etapu 2) |

Jeśli w przyszłości pojawi się realna potrzeba któregokolwiek z powyższych, warto potraktować
to jako osobny etap planistyczny, a nie kolejną fazę — to zmiany na poziomie architektury,
nie funkcjonalności.

---

## Zasady pracy z Claude Code w Etapie 3 (przypomnienie)

1. Jedna (pod)faza = jedna sesja, `/clear` między nimi
2. **Faza 18 (produktyzacja) wymaga testowania na możliwie "czystym" środowisku** —
   w miarę możliwości na innym komputerze lub koncie Windows niż to, na którym rozwijana
   jest appka, żeby faktycznie zweryfikować doświadczenie nowego użytkownika
3. Przy split payment (Faza 21): sprawdzić aktualne przepisy przed implementacją, tak jak
   przy KSeF/JPK w Etapie 2 — nie zgadywać progów kwotowych ani kategorii towarów
4. `commit` + **od razu `merge` do main** + `push` po każdej ukończonej i przetestowanej
   fazie + `git branch -a` dla potwierdzenia
