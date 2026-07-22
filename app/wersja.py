"""Numer wersji aplikacji Faktury Pro - JEDYNE, centralne miejsce w kodzie
Pythona (backend i GUI dzialaja w tym samym procesie od Fazy 18A, wiec obie
strony po prostu importuja ta sama stala zamiast miec wlasna kopie).

WAZNE - ten numer NIE jest automatycznie zsynchronizowany z:
- installer.iss (#define AppWersja) - Inno Setup nie czyta plikow .py
  podczas budowania instalatora,
- wersja_aktualna.txt (plik w korzeniu repo, odczytywany PRZEZ DZIALAJACA
  appke przez proste zapytanie HTTP do GitHub, do sprawdzania dostepnosci
  aktualizacji - patrz app/services/aktualizacje_service.py).

Przy podnoszeniu wersji trzeba wiec recznie zaktualizowac WSZYSTKIE TRZY
miejsca - pelna checklist w CLAUDE.md, sekcja "Wersjonowanie i aktualizacje".
"""

WERSJA = "1.1.1"
