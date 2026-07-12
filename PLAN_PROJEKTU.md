# Faktury Pro — Dokumentacja projektowa

Wersja: 1.0
Status: planowanie / gotowe do rozpoczęcia Fazy 1

---

## 1. Cel projektu

Aplikacja webowa do fakturowania i gospodarki magazynowej dla małej firmy, wzorowana zakresem
funkcjonalnym na programie Faktura Small Business Pro, zbudowana od podstaw pod konkretne
potrzeby klienta docelowego, z możliwością elastycznej rozbudowy.

Cel MVP: wersja **testowalna** — znajomy może wystawiać realne faktury i prowadzić magazyn na
własnych danych, jeszcze przed dodaniem funkcji zaawansowanych (KSeF, JPK, cykliczne faktury).

---

## 2. Zakres funkcjonalny (CORE)

### 2.1 Dokumenty sprzedażowe
- Faktura VAT
- Faktura Proforma
- Faktura Zaliczkowa + Końcowa
- Faktura Korygująca
- Nota korygująca
- Rachunek (firmy zwolnione z VAT)

### 2.2 Kartoteka klientów
- Dane: nazwa, NIP, adres, e-mail, telefon, domyślna waluta, domyślny termin płatności
- Pobieranie danych po NIP z bazy GUS/REGON (API)
- Indywidualne rabaty/ceny per klient (opcjonalnie)
- Historia faktur danego klienta

### 2.3 Kartoteka produktów/usług
- Nazwa, jednostka miary, cena netto, domyślna stawka VAT
- Rozróżnienie: towar magazynowy (ma stan) vs usługa (bez stanu)
- Autouzupełnianie przy dodawaniu do faktury

### 2.4 Tworzenie i zarządzanie fakturami
- Konfigurowalna numeracja (format, reset miesięczny/roczny), ciągła, bez dziur
- Wielopozycyjne faktury, automatyczne przeliczanie netto/VAT/brutto per stawka
- Wielowalutowość z automatycznym kursem z API NBP
- Daty: wystawienia, sprzedaży, termin płatności
- Statusy: robocza / wystawiona / wysłana / opłacona (częściowo/całość) / po terminie / anulowana

### 2.5 PDF i szablony
- Dane sprzedawcy/nabywcy, tabela pozycji, podsumowanie VAT wg stawek, logo firmy
- 2-3 warianty wizualne szablonu do wyboru

### 2.6 Wysyłka i komunikacja
- Wysyłka faktury e-mailem (SMTP) z historią wysyłek

### 2.7 Płatności i należności
- Ręczne oznaczanie płatności (data, kwota, obsługa płatności częściowych)
- Widok należności: faktury nieopłacone/po terminie z sumą

### 2.8 Raporty i eksporty
- Rejestr sprzedaży VAT (zestawienie wg stawek, okres)
- Eksport JPK_V7 (osobna, dokładnie zaplanowana faza — wymaga weryfikacji aktualnego schematu XML)
- Raport przychodów (miesiąc/kwartał/rok), ranking klientów

### 2.9 Ustawienia firmy
- Dane sprzedawcy, logo, domyślna stawka VAT, format numeracji, dane bankowe, konfiguracja SMTP

### 2.10 Autoryzacja
- Login jednej firmy (JWT/sesja), architektura otwarta na rozszerzenie do wielu użytkowników

---

## 3. Zakres funkcjonalny — MODUŁ MAGAZYNOWY

### 3.1 Kartoteka towarów (rozszerzenie 2.3)
- Stan magazynowy (ilość), jednostka magazynowa, minimalny stan (alert), lokalizacja (opcjonalnie)

### 3.2 Magazyny
- Obsługa wielu magazynów, stan towaru liczony osobno per magazyn

### 3.3 Dokumenty magazynowe

| Dokument | Opis | Wpływ na stan |
|---|---|---|
| PZ — Przyjęcie Zewnętrzne | Przyjęcie towaru od dostawcy | + |
| WZ — Wydanie Zewnętrzne | Wydanie towaru do klienta | − |
| PW — Przyjęcie Wewnętrzne | Korekta/inwentaryzacyjna nadwyżka | + |
| RW — Rozchód Wewnętrzny | Zużycie własne, ubytek, reklamacja | − |
| MM — Przesunięcie Międzymagazynowe | Między magazynami | − źródłowy / + docelowy |

### 3.4 Relacja faktura ↔ magazyn — DECYZJA PROJEKTOWA

**Wybrano Model B (rozłączny).**

- Stan magazynowy zmienia się WYŁĄCZNIE przez dokumenty magazynowe
- WZ może mieć opcjonalne pole referencyjne do numeru faktury (informacyjne, nie transakcyjne)
- Uzasadnienie: mniej logiki transakcyjnej i przypadków brzegowych (anulowanie faktury, korekty,
  faktury zaliczkowe z odroczonym wydaniem towaru), łatwiejsze niezależne testowanie obu modułów,
  prostsze wdrożenie dla użytkownika końcowego
- **Ścieżka rozwoju:** po ustabilizowaniu obu modułów — Faza 12 (poza MVP): przycisk
  "Wygeneruj WZ z tej faktury" jako świadoma, jednorazowa akcja użytkownika, nie automatyzacja w tle

### 3.5 Blokada sprzedaży poniżej zera
Konfigurowalna: ostrzeżenie lub twarda blokada przy próbie wydania większej ilości niż stan.

### 3.6 Inwentaryzacja
Tryb spisu z natury: lista towarów z polem "stan faktyczny" → automatyczne wygenerowanie PW/RW
na różnice po zapisaniu.

### 3.7 Raporty magazynowe
- Aktualny stan wszystkich towarów
- Historia ruchów danego towaru (kto, kiedy, jaki dokument, ile)
- Towary poniżej stanu minimalnego

---

## 4. Architektura techniczna

- **Backend:** FastAPI (Python)
- **Baza danych:** PostgreSQL
- **ORM / migracje:** SQLAlchemy + Alembic
- **Generowanie PDF:** WeasyPrint (szablony HTML)
- **Frontend:** Jinja2 + HTMX (server-rendered)
- **Auth:** JWT
- **Integracje zewnętrzne:** API NBP (kursy walut), API GUS/REGON (dane firm po NIP), SMTP (e-mail)

### Kluczowe reguły implementacyjne
- Kwoty pieniężne: `integer` w groszach, nigdy `float`
- Logika biznesowa w warstwie `services/`, routery `api/` mają być cienkie
- Stawki VAT jako konfigurowalny słownik, nie hardkodowane wartości

---

## 5. Harmonogram faz

| Faza | Zakres | Szacowany czas | Sesje Claude Code |
|---|---|---|---|
| 0 | Przygotowanie: wymagania szczegółowe, wybór stacku | 0.5-1h | — |
| 1 | Modele danych + baza (faktury: Firma, Klient, Faktura, PozycjaFaktury) | 2-3h | 1 |
| 2 | CRUD API faktur | 4-6h | 1-2 |
| 3 | Generowanie PDF faktur | 3-5h | 1 |
| 4 | Interfejs użytkownika (faktury) | 5-7h | 2 |
| 5 | Statusy i płatności | 2-3h | 1 |
| 6 | Autoryzacja (auth) | 1-2h | częściowo |
| 7 | Modele magazynowe (towary ze stanem, magazyny, dokumenty PZ/WZ/PW/RW/MM) | 3-4h | 1 |
| 8 | Logika stanów magazynowych (przyjęcia/wydania, walidacja, blokady) | 4-5h | 1-2 |
| 9 | UI dokumentów magazynowych + pole referencyjne do faktury | 4-5h | 2 |
| 10 | Inwentaryzacja + raporty magazynowe | 3-4h | 1 |
| 11 | Testowanie całości i poprawki | 3-4h | 1-2 |

**Suma: ~33-47h pracy, 12-17 sesji Claude Code.**
Przy 3-4 sesjach tygodniowo: realnie **4-6 tygodni kalendarzowych** do wersji testowej.

> Uwaga o limitach Claude Code: 5-godzinne okno sesji i osobny limit tygodniowy są dzielone
> między Claude Code i Claude.ai. Jedna faza = jedna sesja (rzadziej dwie). Nie łączyć wielu faz
> w jednym oknie — to najszybszy sposób na wyczerpanie limitu bez postępu proporcjonalnego do
> zużytych tokenów.

---

## 6. Backlog — poza MVP (świadomie odłożone)

- **KSeF** (Krajowy System e-Faktur) — integracja API, certyfikaty, obowiązkowe etapowo w Polsce;
  osobny, duży temat wymagający dedykowanego planowania
- **JPK_V7** — pełna zgodność ze schematem XML wymaga starannej weryfikacji aktualnych przepisów
- Faktury cykliczne / subskrypcyjne
- Automatyzacja WZ z faktury (Model A jako opcja, po ustabilizowaniu Modelu B)
- Wielu użytkowników / multi-firma
- WDT, faktury eksportowe, faktury marża (nisza, do dodania na żądanie)
- Split payment (mechanizm podzielonej płatności)
- Integracje ze sklepami internetowymi (np. Shoper)

---

## 7. Sposób pracy z Claude Code

1. Repo zawiera plik `CLAUDE.md` z pełnym kontekstem technicznym i regułami biznesowymi —
   czytany automatycznie na starcie każdej sesji
2. Jedna faza z harmonogramu = jedna (rzadziej dwie) sesja Claude Code, z `/clear` między fazami
3. Przed większymi zmianami strukturalnymi: Plan Mode (Claude Code proponuje plan, deweloper
   akceptuje przed implementacją)
4. Git commit po każdej zakończonej, działającej funkcjonalności
5. Ręczny test (Swagger UI / curl) po zakończeniu każdej fazy, przed przejściem do kolejnej
6. Niejednoznaczności w regułach biznesowych (VAT, numeracja, stany magazynowe) — pytać, nie
   zgadywać

---

## 8. Historia decyzji

| Data | Decyzja | Uzasadnienie |
|---|---|---|
| Etap planowania | Model B (faktura i magazyn rozłączne) | Mniej logiki transakcyjnej, łatwiejsze testowanie, prostsze wdrożenie na start |
| Etap planowania | Kwoty jako integer w groszach | Unikanie błędów zaokrągleń typowych dla float w kontekście finansowym |
| Etap planowania | KSeF i JPK poza MVP | Duża złożoność prawna/integracyjna, nie blokuje testów wewnętrznych |
