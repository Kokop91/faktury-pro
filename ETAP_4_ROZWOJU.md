# Faktury Pro — Etap 4 rozwoju aplikacji

Wersja: 1.0
Data: lipiec 2026
Status: planowanie — do rozpoczęcia po ukończeniu Etapu 3

---

## Wprowadzenie i cel Etapu 4

Etapy 1-3 dały: kompletną aplikację fakturowo-magazynową (Etap 1), zgodność prawną i
nowoczesny interfejs (Etap 2), oraz pełną produktyzację — gotowy instalator, brak wymogu
umiejętności programistycznych (Etap 3).

**Etap 4 adresuje lukę, która stała się pilna dopiero po produktyzacji:** aplikacja
przechowuje teraz wszystkie dane firmy wyłącznie lokalnie, na jednym komputerze, bez żadnej
kopii zapasowej. To już nie jest drobiazg — to realne ryzyko utraty całej historii finansowej
firmy przy awarii dysku, przy czym polskie przepisy wymagają przechowywania dokumentacji
księgowej przez 5 lat.

### Ważne odkrycie kontekstowe

Faktury wysyłane przez KSeF (Faza 12) są automatycznie archiwizowane przez państwo przez
10 lat w centralnym repozytorium — to daje pewną "siatkę bezpieczeństwa" dla samych faktur
sprzedażowych wysłanych tą drogą. NIE obejmuje to jednak: dokumentów magazynowych, danych
klientów, historii płatności, faktur kosztowych, ani jakichkolwiek faktur niewysłanych przez
KSeF (np. w okresie testowym) — te dane istnieją wyłącznie lokalnie i odpowiedzialność za
ich zachowanie spoczywa w całości na użytkowniku aplikacji.

---

## Przegląd faz Etapu 4

| Faza | Nazwa | Priorytet | Szacowany czas | Sesje CC |
|---|---|---|---|---|
| 22 | Backup i odzyskiwanie danych | KRYTYCZNY | 6-10h | 2-3 |
| 23 | Przypomnienia o płatnościach | Średni | 4-6h | 2 |
| 24 | Oferty i zamówienia przed fakturą | Średni | 6-9h | 2-3 |
| 25 | Analiza rentowności i prognoza cash-flow | Średni | 6-9h | 2-3 |
| 26 | Import danych z innych systemów | Niski | 4-6h | 1-2 |

**Suma Etapu 4: ~26-40h, 9-13 sesji.** Przy 3-4 sesjach/tydzień: **3-5 tygodni.**

**Rekomendowana kolejność:** 22 → 23 → 24 → 25 → 26. Faza 22 jest jedyną, która ma
uzasadnienie do bycia zrobioną poza kolejnością pierwszą — pozostałe można swobodnie
przestawiać zależnie od tego, co akurat przynosi realną wartość znajomemu.

---

## FAZA 22 — Backup i odzyskiwanie danych

```
Rozpoczynamy Etap 4: Fazę 22 — backup i odzyskiwanie danych. To priorytet, ponieważ po
produktyzacji z Etapu 3 (prywatny PostgreSQL, Faza 18B) aplikacja przechowuje WSZYSTKIE
dane firmy lokalnie, bez żadnej kopii zapasowej. Awaria dysku = utrata dostępu do danych,
których polskie przepisy wymagają przechowywać przez 5 lat.

Zakres:
1. Automatyczny, zaplanowany backup bazy danych (pg_dump z prywatnej instancji PostgreSQL
   z Fazy 18B) do lokalizacji WSKAZANEJ przez użytkownika — np. zewnętrzny dysk USB, folder
   sieciowy, lub folder synchronizowany z chmurą (Google Drive/OneDrive/Dropbox jako CEL
   backupu, NIE jako główne miejsce przechowywania danych — appka zostaje offline-first,
   backup to tylko kopia bezpieczeństwa)
2. Harmonogram: przy starcie appki sprawdź kiedy był ostatni backup; jeśli minął ustawiony
   próg (np. 7 dni) — zaproponuj wykonanie backupu, nie wymuszaj
3. Backup obejmuje: bazę danych w całości ORAZ pliki powiązane (logo firmy, wygenerowane
   PDF-y, pliki UPO z KSeF, eksporty JPK) — całościowy folder danych, nie tylko sama baza
4. Szyfrowanie kopii zapasowej (dane finansowe firmy) — hasłem ustawionym przez użytkownika,
   osobnym od hasła logowania do appki
5. Funkcja przywracania z backupu: ekran w Ustawieniach, wybór pliku kopii, podanie hasła
   szyfrowania, przywrócenie z jasnym ostrzeżeniem że nadpisze bieżące dane
6. Widoczny wskaźnik w appce (np. na dashboardzie z Fazy 16B): data ostatniego backupu,
   z wyraźnym ostrzeżeniem kolorem, jeśli backup jest przeterminowany

Zastosuj się do CLAUDE.md, tokeny motywu z 16A. To dotyka bezpieczeństwa danych finansowych
firmy — priorytetem jest niezawodność, nie wygoda. Przetestuj pełny cykl: backup → celowe
uszkodzenie/usunięcie lokalnej bazy → przywrócenie z kopii → weryfikacja że wszystkie dane
(faktury, magazyn, klienci) wróciły identyczne.

Na koniec: dokładny scenariusz testowy odzyskiwania po awarii, i co doradzić użytkownikowi
(np. trzymanie kopii NA INNYM nośniku niż komputer, na którym pracuje appka).
```

---

## FAZA 23 — Przypomnienia o płatnościach

### Zarys (pełny prompt przygotować po ukończeniu Fazy 22)
- Automatyczne (lub półautomatyczne, z akceptacją użytkownika — zgodnie z filozofią appki
  niedziałającej 24/7) e-maile przypominające o zbliżającym się/minionym terminie płatności
- Wykorzystanie istniejącego mechanizmu SMTP z Etapu 1 (wysyłka faktur mailem)
- Konfigurowalny harmonogram przypomnień (np. 3 dni przed terminem, w dniu terminu, 7 dni po)
- Naturalnie łączy się z linkami płatniczymi z Fazy 20 (jeśli/gdy zostanie odblokowana) —
  przypomnienie z linkiem do szybkiej płatności byłoby najskuteczniejsze
- Przy starcie appki: propozycja wysłania zaległych przypomnień (podobnie jak faktury
  cykliczne z Fazy 15 — appka nie działa 24/7, więc sprawdzanie dzieje się przy starcie)

---

## FAZA 24 — Oferty i zamówienia przed fakturą

### Zarys (pełny prompt przygotować po ukończeniu Fazy 23)
- Nowy typ dokumentu: Oferta (wycena dla klienta przed zobowiązaniem) → status zaakceptowana/
  odrzucona → Zamówienie (potwierdzone zlecenie) → Faktura (na końcu procesu)
- Przydatne dla firm usługowych, które najpierw wyceniają pracę, a dopiero po akceptacji
  klienta wystawiają fakturę
- Możliwość wygenerowania faktury bezpośrednio z zaakceptowanej oferty/zamówienia (pozycje
  przenoszą się automatycznie, tak jak przy fakturach cyklicznych z Fazy 15)
- PDF oferty w podobnym stylu co faktura, ale wyraźnie oznaczony jako "Oferta — nie jest
  dokumentem księgowym"

---

## FAZA 25 — Analiza rentowności i prognoza cash-flow

### Zarys (pełny prompt przygotować po ukończeniu Fazy 24)
- Rozszerzenie dashboardu (Faza 16B) o marże: przychody minus koszty, wykorzystując dane
  z dokumentów kosztowych odbieranych przez KSeF (Faza 12C) oraz ręcznie wprowadzone koszty
  spoza KSeF
- Prosta prognoza przepływów pieniężnych: na podstawie terminów płatności nieopłaconych
  faktur oraz historycznego zachowania płatniczego klientów (średni czas płacenia per klient)
- Wskaźnik rentowności per produkt/usługa (jeśli koszt jednostkowy jest znany)

---

## FAZA 26 — Import danych z innych systemów

### Zarys (pełny prompt przygotować po ukończeniu Fazy 25)
- Import CSV klientów i produktów — dla kogoś migrującego z innego programu do fakturowania
- Mapowanie kolumn CSV na pola aplikacji (elastyczny import, nie sztywny format)
- Walidacja i podgląd przed ostatecznym zapisem (żeby uniknąć zaimportowania błędnych danych
  masowo)
- Rozważyć eksport w drugą stronę (żeby dane z tej appki dało się też wynieść, gdyby
  użytkownik chciał zmienić system w przyszłości) — dobra praktyka niezależnie od tego,
  czy akurat teraz jest potrzebna

---

## Rzecz strategiczna, nie techniczna — do przemyślenia, nie do zakodowania

Aplikacja osiągnęła poziom dojrzałości (KSeF, JPK, magazyn, gotowy instalator, kreator
pierwszego uruchomienia), który wykracza poza "narzędzie dla jednego znajomego". To dobry
moment na pytanie biznesowe: **czy to zostaje produktem na własny użytek, czy widoczny jest
potencjał, żeby zaoferować to innym małym firmom?**

Gdyby odpowiedź brzmiała "tak" w przyszłości, warto mieć na uwadze, że wymagałoby to:
- Rozważenia modelu dystrybucji/licencjonowania (jednorazowa sprzedaż instalatora? wsparcie
  techniczne dla wielu niezależnych instalacji?)
- Faza 26 (import danych) nabrałaby dużo większego znaczenia — ułatwiałaby migrację nowym
  klientom
- Prawdopodobnie osobnego rozważenia kwestii wsparcia i aktualizacji dla wielu niezależnych
  instalacji u różnych klientów (mechanizm powiadamiania o nowej wersji, dystrybucja poprawek)

To nie jest coś do zaplanowania jako "faza" — to decyzja biznesowa, którą warto podjąć
świadomie, gdy/jeśli nadejdzie odpowiedni moment, a nie wplatać po cichu w bieżący rozwój.

---

## Zasady pracy z Claude Code w Etapie 4 (przypomnienie)

1. Jedna faza = jedna sesja (rzadziej dwie), `/clear` między nimi
2. Faza 22 (backup) wymaga przetestowania scenariusza faktycznej awarii/utraty danych —
   nie poprzestawać na "backup się wykonał", tylko faktycznie zweryfikować przywracanie
3. Przy Fazie 24 (oferty): rozważyć, czy warto to zintegrować z KSeF (oferty NIE są
   dokumentami podlegającymi KSeF, tylko faktury na końcu procesu — upewnić się, że to
   rozróżnienie jest jasne w kodzie i UI)
4. `commit` + **od razu `merge` do main** + `push` po każdej ukończonej i przetestowanej
   fazie + `git branch -a` dla potwierdzenia
