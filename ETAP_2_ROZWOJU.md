# Faktury Pro — Etap 2 rozwoju aplikacji

Wersja: 1.0
Data: lipiec 2026
Status: planowanie — do rozpoczęcia po ukończeniu Fazy 11 (testy Etapu 1)

---

## Wprowadzenie i kontekst rynkowy

Etap 1 (Fazy 0-11) dostarczył kompletną, testowalną aplikację desktopową do fakturowania
i gospodarki magazynowej. Etap 2 przekształca ją z "działającego narzędzia" w produkt
konkurencyjny wobec rozwiązań rynkowych, w oparciu o analizę rynku polskich programów
do fakturowania (stan: lipiec 2026).

### Kluczowe wnioski z analizy rynku

1. **KSeF przestał być opcją — to wymóg prawny.** Krajowy System e-Faktur jest obowiązkowy
   dla firm od 1 lutego 2026 (duże, >200 mln zł obrotu) i od 1 kwietnia 2026 (wszystkie
   pozostałe: mikro, małe, średnie, JDG). Odbieranie faktur z KSeF jest obowiązkowe dla
   wszystkich od 1 lutego 2026. Najmniejsi przedsiębiorcy ("wykluczeni cyfrowo", do 10 tys.
   zł sprzedaży/mies.) dołączają od 1 stycznia 2027.
   - **KONSEKWENCJA:** bez integracji z KSeF aplikacja nie może być głównym systemem
     fakturowania firmy. To priorytet #1 Etapu 2.
   - **DO WERYFIKACJI z księgową klienta:** czy firma już podlega obowiązkowi, czy mieści
     się w progu odroczenia do 2027.

2. **Pozycjonowanie rynkowe.** Rynek (2,8 mln firm objętych KSeF) jest zdominowany przez
   rozwiązania chmurowe w abonamencie (Fakturownia, Faktura.pl, wFirma, iFirma, Comarch,
   Symfonia), ceny 15-30 zł/mies. w najczęstszych planach. Aplikacja NIE konkuruje z nimi
   na szerokości funkcji ani cenie chmury — jej przewagą jest:
   - dane lokalnie, bez chmury, bez abonamentu (nisza dla firm ceniących prywatność/kontrolę)
   - pełny moduł magazynowy w standardzie (u konkurencji często dopiero w wyższych planach)
   - możliwość dopasowania pod konkretny biznes (nie do skopiowania przez SaaS)

3. **Funkcje oczekiwane jako standard rynkowy**, których jeszcze brak lub są niepełne:
   integracja z GUS po NIP, biała lista podatników VAT, kursy NBP, faktury cykliczne,
   JPK_V7, prosta analityka finansowa.

---

## Przegląd faz Etapu 2

| Faza | Nazwa | Priorytet | Szacowany czas | Sesje CC |
|---|---|---|---|---|
| 12 | Integracja z KSeF (wysyłka, odbiór, UPO) | KRYTYCZNY | 15-25h | 5-8 |
| 13 | Eksport JPK_V7 | Wysoki | 6-10h | 2-3 |
| 14 | Integracje MF/GUS/NBP (biała lista, dane po NIP, kursy) | Średni | 5-8h | 2-3 |
| 15 | Faktury cykliczne | Średni | 4-6h | 2 |
| 16 | Modernizacja GUI + dashboard analityczny | Średni | 8-12h | 3-4 |

**Suma Etapu 2: ~38-61h pracy, 14-20 sesji Claude Code.**
Kalendarzowo przy 3-4 sesjach/tydzień: **5-8 tygodni.**

**Rekomendowana kolejność:** 12 → 14 → 13 → 15 → 16.
Uzasadnienie: KSeF pierwszy (wymóg prawny). Potem integracje MF/GUS/NBP (Faza 14), bo są
tanie i część z nich (biała lista, walidacja NIP) przyda się przy KSeF. JPK (13) po tym.
Faktury cykliczne i modernizacja GUI na końcu — to komfort, nie konieczność.

---

## FAZA 12 — Integracja z KSeF

> **UWAGA — to najbardziej wymagający moduł całego projektu.** Integracja z systemem
> rządowym, wymaga certyfikatów/tokenów autoryzacyjnych, obsługi struktury logicznej FA(3),
> i BEZWZGLĘDNIE testowania w środowisku testowym Ministerstwa Finansów (KSeF 2.0) przed
> dotknięciem prawdziwych faktur. Błąd tutaj = odrzucona faktura lub problem prawny.

### Zakres

**12A — Fundament i uwierzytelnianie (środowisko testowe):**
- Konfiguracja połączenia z API KSeF (osobne środowiska: testowe i produkcyjne — przełączane
  w ustawieniach, domyślnie TESTOWE)
- Uwierzytelnianie: obsługa tokena KSeF / podpisu (do ustalenia dokładny mechanizm na
  podstawie aktualnej dokumentacji MF — Claude Code musi to najpierw sprawdzić)
- Przechowywanie danych autoryzacyjnych lokalnie i bezpiecznie (jak hasło z Fazy 6 — poza repo)

**12B — Generowanie i wysyłka faktury (FA(3)):**
- Mapowanie modelu Faktura z Etapu 1 na strukturę logiczną FA(3) (XML)
- Walidacja XML względem schematu przed wysyłką
- Wysyłka faktury do KSeF, obsługa odpowiedzi (numer KSeF, status)
- Pobieranie i przechowywanie UPO (Urzędowe Poświadczenie Odbioru)
- Widok statusu KSeF na fakturze (wysłana/przyjęta/odrzucona + numer KSeF + UPO)

**12C — Odbiór faktur kosztowych:**
- Pobieranie faktur zakupowych wystawionych na NIP firmy z KSeF
- Zapisywanie ich jako dokumenty kosztowe (nowy prosty rejestr zakupów)

**12D — UI KSeF:**
- Panel statusu KSeF w widoku faktury
- Ustawienia KSeF (środowisko test/prod, dane autoryzacyjne)
- Widok rejestru faktur kosztowych pobranych z KSeF

### Prompt startowy dla Claude Code (Faza 12A)

```
Zaczynamy Etap 2 rozwoju aplikacji — Fazę 12: integracja z KSeF. To duży, wieloczęściowy
moduł, zaczynamy od części 12A (fundament + uwierzytelnianie).

ZANIM zaczniesz implementację: sprawdź aktualną dokumentację API KSeF Ministerstwa Finansów
(struktura logiczna FA(3), mechanizm uwierzytelniania, endpointy środowiska testowego KSeF 2.0).
Jeśli nie masz dostępu do aktualnej dokumentacji online, powiedz mi wprost i poproś mnie
o wklejenie kluczowych fragmentów — NIE zgaduj struktury API systemu rządowego.

Zakres 12A:
1. Moduł konfiguracji KSeF: przełącznik środowiska (TESTOWE / PRODUKCYJNE), domyślnie TESTOWE,
   w ustawieniach aplikacji
2. Mechanizm uwierzytelniania zgodny z aktualnym API KSeF, dane autoryzacyjne przechowywane
   lokalnie i bezpiecznie (analogicznie do hasła z Fazy 6 — hash/szyfrowanie, poza repozytorium,
   poza bazą główną)
3. Warstwa serwisowa (app/services/ksef_service.py) — na razie tylko połączenie i test
   uwierzytelnienia (health-check / sesja), bez wysyłki faktur
4. Prosty test: przycisk "Testuj połączenie z KSeF" w ustawieniach, który potwierdza że
   uwierzytelnienie w środowisku testowym działa

Zastosuj się do CLAUDE.md. Zaktualizuj CLAUDE.md o sekcję KSeF (środowiska, gdzie trzymane
są dane autoryzacyjne, że domyślne środowisko to TESTOWE).

To jest integracja z systemem rządowym — priorytetem jest poprawność i bezpieczeństwo, nie
szybkość. Pytaj o każdą niejednoznaczność zamiast zakładać.

Na koniec powiedz mi dokładnie: co udało się połączyć, czego potrzebujesz ode mnie (np.
dane testowe, certyfikaty), i co przetestować.
```

> Kolejne prompty (12B, 12C, 12D) przygotować po ukończeniu i przetestowaniu 12A — ze
> względu na złożoność nie warto planować ich w szczegółach zanim nie wiadomo, jak zachowa
> się środowisko testowe KSeF.

---

## FAZA 13 — Eksport JPK_V7

### Zakres
- Generowanie pliku JPK_V7 (część ewidencyjna + deklaracyjna) zgodnego z aktualnym schematem
  XML Ministerstwa Finansów
- Wybór okresu (miesiąc/kwartał)
- Walidacja wygenerowanego pliku względem schematu
- Zapis pliku XML do wskazanej lokalizacji (dla przekazania księgowej / wgrania na portal MF)
- Widok w zakładce Raporty

### Prompt startowy dla Claude Code

```
Zaimplementuj Fazę 13 z ETAP_2_ROZWOJU.md: eksport JPK_V7.

ZANIM zaczniesz: sprawdź aktualny schemat XML JPK_V7 (JPK_V7M / JPK_V7K) Ministerstwa
Finansów. Jeśli nie masz dostępu do aktualnej specyfikacji, powiedz mi i poproś o wklejenie
— NIE zgaduj struktury pliku podatkowego.

Zakres:
1. Serwis app/services/jpk_service.py — generowanie pliku JPK_V7 na podstawie faktur
   z wybranego okresu (część ewidencyjna: rejestr sprzedaży VAT; deklaracyjna: podsumowanie)
2. Endpoint GET /raporty/jpk-v7?okres=... zwracający wygenerowany plik XML
3. Walidacja wygenerowanego XML względem schematu przed zapisem
4. UI w zakładce Raporty: wybór okresu, przycisk "Generuj JPK_V7", zapis do pliku
5. Jasny komunikat, jeśli w okresie są faktury robocze / niekompletne dane, które
   zaburzyłyby JPK

Zastosuj się do CLAUDE.md (kwoty w groszach, spójny UI). To dokument podatkowy — poprawność
przed wygodą, pytaj o niejednoznaczności.

Na koniec: jak wygenerować testowy JPK i jak go zweryfikować (np. walidatorem MF).
```

---

## FAZA 14 — Integracje Ministerstwa Finansów / GUS / NBP

### Zakres
- **Biała lista podatników VAT (API MF):** weryfikacja czy NIP kontrahenta jest czynnym
  podatnikiem VAT i czy numer konta bankowego zgadza się z białą listą (istotne dla
  bezpieczeństwa płatności i kosztów podatkowych)
- **Dane firmy po NIP (API GUS/REGON):** sprawdzić, czy zostało zaimplementowane w Etapie 1
  (było w specyfikacji kartoteki klientów) — jeśli nie, dokończyć; jeśli tak, zweryfikować
- **Kursy walut (API NBP):** automatyczne pobieranie kursu przy fakturach w walucie obcej
  (odłożone w Etapie 1 — teraz dokończyć), z podstawieniem kursu z dnia poprzedzającego
  datę wystawienia zgodnie z przepisami

### Prompt startowy dla Claude Code

```
Zaimplementuj Fazę 14 z ETAP_2_ROZWOJU.md: integracje z publicznymi API (MF, GUS, NBP).

Zakres:
1. NAJPIERW sprawdź, czy pobieranie danych po NIP z GUS/REGON zostało już zaimplementowane
   w Etapie 1 (miało być w kartotece klientów). Jeśli działa — zostaw, potwierdź. Jeśli nie —
   zaimplementuj: przycisk "Pobierz z GUS" przy polu NIP w formularzu klienta, wypełniający
   nazwę i adres.

2. Kursy NBP: automatyczne pobieranie kursu z API NBP (tabela A) przy wyborze waluty obcej
   w formularzu faktury — kurs z dnia poprzedzającego datę wystawienia. Ręczne nadpisanie
   nadal możliwe. Obsłuż brak połączenia (fallback na ręczne wpisanie z komunikatem).

3. Biała lista VAT (API MF): przycisk "Sprawdź w białej liście" przy kliencie / przy fakturze,
   weryfikujący status VAT kontrahenta i zgodność numeru konta. Wynik jasno pokazany
   (zielony/czerwony). Wynik weryfikacji zapisywany z datą sprawdzenia (istotne dowodowo).

Wszystkie trzy API są publiczne i darmowe. Obsłuż brak internetu gracefully — appka jest
desktopowa i offline-first, te funkcje są dodatkiem, nie mogą blokować pracy gdy nie ma sieci.

Zastosuj się do CLAUDE.md, kontynuuj wątkowanie dla wywołań sieciowych.

Na koniec: co przetestować dla każdej z trzech integracji, w tym zachowanie przy braku sieci.
```

---

## FAZA 15 — Faktury cykliczne

### Zakres
- Definiowanie szablonu faktury cyklicznej (klient, pozycje, częstotliwość: miesięczna/
  kwartalna/roczna, dzień wystawienia)
- Automatyczne generowanie faktur roboczych z szablonu w odpowiednich terminach
- Ponieważ appka jest desktopowa (nie działa 24/7): przy każdym uruchomieniu appka sprawdza,
  czy są zaległe faktury cykliczne do wygenerowania, i proponuje ich utworzenie (nie generuje
  po cichu — użytkownik zatwierdza)
- Widok listy szablonów cyklicznych + historia wygenerowanych z każdego

### Prompt startowy dla Claude Code

```
Zaimplementuj Fazę 15 z ETAP_2_ROZWOJU.md: faktury cykliczne.

Zakres:
1. Model SzablonCykliczny: klient, lista pozycji (jak w fakturze), częstotliwość (miesięczna/
   kwartalna/roczna), dzień generowania, data początku, opcjonalna data końca, aktywny/wstrzymany.
   Migracja Alembic.
2. Logika w services/: funkcja wykrywająca, które szablony mają zaległe/nadchodzące terminy
   generowania (na podstawie historii już wygenerowanych faktur z danego szablonu)
3. WAŻNE — appka jest desktopowa, nie działa w tle 24/7: przy starcie aplikacji sprawdź
   zaległe faktury cykliczne i pokaż użytkownikowi okno "Do wygenerowania: X faktur
   cyklicznych" z listą i przyciskiem zatwierdzenia. NIE generuj automatycznie bez zgody
   użytkownika — tworzą się jako faktury robocze do przejrzenia.
4. UI: nowa zakładka/sekcja "Faktury cykliczne" — lista szablonów, formularz tworzenia,
   historia wygenerowanych faktur per szablon, możliwość wstrzymania/wznowienia szablonu.

Zastosuj się do CLAUDE.md. Nie dodawaj żadnego schedulera/crona systemowego — mechanizm
"sprawdź przy starcie" jest właściwy dla aplikacji jednostanowiskowej.

Na koniec: jak przetestować (utworzenie szablonu, symulacja zaległego terminu, weryfikacja
że przy starcie proponuje wygenerowanie).
```

---

## FAZA 16 — Modernizacja GUI + dashboard analityczny

Ta faza podnosi warstwę wizualną z "działa i jest czytelne" do "wygląda jak nowoczesny,
profesjonalny produkt" — oraz dodaje pierwszy ekran wartości analitycznej.

### Zasady modernizacji (oparte na dobrych praktykach customtkinter)

CustomTkinter wspiera tryby jasny/ciemny, skalowanie HighDPI i spójny wygląd na Windows/
macOS/Linux. Dobre praktyki UI: spójne odstępy, grupowanie powiązanych elementów, projektowanie
responsywne, informacja zwrotna dla użytkownika, oddzielenie logiki od UI, ograniczanie
dynamicznego tworzenia widgetów, użycie after() do zadań okresowych.

### Zakres

**16A — System designu i odświeżenie wyglądu:**
- Przełącznik trybu jasny/ciemny (CustomTkinter obsługuje to natywnie: `set_appearance_mode`)
  — zapisywany w ustawieniach, plus opcja "zgodnie z systemem"
- Spójny motyw kolorystyczny zdefiniowany centralnie (jeden plik motywu/tokenów) zamiast
  kolorów rozsianych po kodzie — łatwiejsze przyszłe zmiany
- HighDPI scaling włączony (ostre renderowanie na ekranach 4K/skalowanych)
- Ujednolicone odstępy, marginesy, zaokrąglenia, typografia w całej appce
- Ikony przy pozycjach menu i przyciskach (biblioteka ikon, np. zestaw dołączony jako
  zasoby — bez zależności wymagającej internetu)

**16B — Dashboard (ekran startowy po zalogowaniu):**
- Kafelki z kluczowymi wskaźnikami: przychód w bieżącym miesiącu, należności (do zapłaty),
  faktury po terminie, liczba faktur w miesiącu
- Wykres przychodów miesiąc po miesiącu (ostatnie 12 miesięcy) — użyj matplotlib
  osadzonego w customtkinter (FigureCanvasTkAgg) albo lekkiego rysowania na Canvas
- Lista "wymagają uwagi": faktury po terminie, towary poniżej stanu minimalnego
- Kafelek statusu KSeF (ile faktur czeka na wysyłkę / zostało odrzuconych) — jeśli Faza 12
  ukończona

**16C — Dopracowanie UX (drobiazgi, które robią różnicę):**
- Wskaźniki ładowania podczas operacji sieciowych (zamiast "zamrożonego" okna — mimo
  wątkowania warto pokazać spinner)
- Potwierdzenia i komunikaty sukcesu spójne wizualnie (toasty/bannery zamiast surowych
  okien dialogowych gdzie to pasuje)
- Skróty klawiszowe dla najczęstszych akcji (np. Ctrl+N = nowa faktura)
- Zapamiętywanie ostatnio używanych ustawień widoków (filtry, sortowanie)

### Prompt startowy dla Claude Code (Faza 16A)

```
Zaimplementuj Fazę 16 z ETAP_2_ROZWOJU.md, część 16A: modernizacja warstwy wizualnej GUI
(customtkinter). Nie zmieniaj logiki biznesowej ani API — tylko warstwa prezentacji.

Zakres 16A:
1. Centralny plik motywu (gui/motyw.py lub rozszerz istniejący gui/styl.py): wszystkie kolory,
   odstępy, promienie zaokrągleń, rozmiary czcionek zdefiniowane w JEDNYM miejscu jako stałe/
   tokeny. Zrefaktoruj istniejące widoki, żeby korzystały z tych tokenów zamiast wartości
   wpisanych na sztywno.
2. Przełącznik trybu jasny/ciemny/systemowy w ustawieniach, zapisywany lokalnie, stosowany
   przez set_appearance_mode. Sprawdź, czy wszystkie widoki wyglądają poprawnie w obu trybach.
3. Włącz HighDPI scaling dla ostrego renderowania na ekranach skalowanych.
4. Ujednolić odstępy, marginesy i typografię w całej aplikacji zgodnie z tokenami z pkt 1.
5. Dodaj ikony do pozycji panelu bocznego i głównych przycisków akcji — użyj zestawu ikon
   dołączonego jako lokalne zasoby (bez zależności wymagającej internetu w runtime).

Zastosuj się do CLAUDE.md. To refaktor wizualny — po zmianach WSZYSTKIE dotychczasowe
funkcje muszą działać identycznie jak przed, zmienia się tylko wygląd. Przetestuj klikając
przez główne widoki w obu trybach kolorystycznych.

Na koniec: co sprawdzić wizualnie w obu trybach (jasny/ciemny).
```

> Prompty 16B (dashboard) i 16C (dopracowanie UX) przygotować po ukończeniu 16A.

---

## Backlog Etapu 3 (poza zakresem Etapu 2)

Funkcje rozważane w dalszej przyszłości, jeśli projekt będzie się rozwijał:
- Linki płatnicze przy fakturach (integracja z bramką płatności, np. Przelewy24) —
  według danych rynkowych podnosi konwersję płatności, ale wymaga umowy z operatorem
- Split payment (mechanizm podzielonej płatności) — dla wybranych towarów/usług
- Wielu użytkowników / kilka stanowisk (wymagałoby powrotu do pełnego auth JWT)
- Aplikacja mobilna / dostęp zdalny (istotna zmiana architektury — z desktopowej na hybrydową)
- OCR faktur kosztowych (trudne bez chmury, prawdopodobnie poza zasięgiem architektury desktop)
- Automatyczne generowanie WZ z faktury (Model A jako opcja — pierwotnie odłożone w Etapie 1)

---

## Zasady pracy z Claude Code w Etapie 2 (przypomnienie)

Te same reguły co w Etapie 1, ze szczególnym naciskiem przy integracjach zewnętrznych:

1. Jedna faza/podfaza = jedna sesja (rzadziej dwie), `/clear` między nimi
2. **Przy integracjach z API rządowymi (KSeF, JPK, biała lista): Claude Code MA sprawdzić
   aktualną dokumentację i pytać przy niejednoznacznościach — nigdy nie zgadywać struktury
   dokumentów podatkowych ani API rządowego**
3. Testowanie po każdej fazie na środowisku TESTOWYM zanim cokolwiek dotknie produkcji /
   prawdziwych faktur
4. `commit` + **od razu `merge` do main** + `push` po każdej ukończonej i przetestowanej fazie
   (nie odkładać merge — to lekcja z Fazy 6 w Etapie 1)
5. Po każdym merge: `git branch -a` dla potwierdzenia że został tylko main

---

## Historia decyzji (uzupełnienie)

| Data | Decyzja | Uzasadnienie |
|---|---|---|
| Lipiec 2026 | KSeF przeniesiony z backlogu na priorytet #1 Etapu 2 (Faza 12) | Wymóg prawny obowiązujący firmy od lutego/kwietnia 2026; bez tego appka nie może być głównym systemem fakturowania |
| Lipiec 2026 | Kolejność 12→14→13→15→16 | KSeF pierwszy (prawo), integracje MF/GUS/NBP wcześnie (tanie, część wspiera KSeF), komfort (cykliczne, GUI) na końcu |
| Lipiec 2026 | Pozostanie przy architekturze desktop + customtkinter, modernizacja wizualna zamiast przepisywania | Przewaga rynkowa aplikacji to właśnie lokalność/brak abonamentu; customtkinter wspiera tryby jasny/ciemny, HighDPI i nowoczesny wygląd bez zmiany technologii |
