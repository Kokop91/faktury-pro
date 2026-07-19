"""Rejestr uruchomionych procesow appki (watek serwera FastAPI, prywatny
Postgres z Fazy 18B) - udostepniony globalnie, zeby ekrany GLEBOKO w GUI
(przywracanie kopii zapasowej w Ustawieniach, Faza 22) mogly bezpiecznie
zatrzymac serwer FastAPI przed operacja na bazie danych, bez koniecznosci
przekazywania referencji `watek`/`postgres_prywatny` z gui/main.py:main()
przez cale drzewo widgetow.

Bez tego przywracanie backupu ryzykowaloby dokladnie ten sam problem, ktory
installer.iss musial juz raz naprawiac w Fazie 18C: osierocony proces
postgres.exe dzialajacy dalej w tle po tym, jak appka "zniknela" z ekranu.
"""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from gui.main import WatekSerwera
    from gui.postgres_serwer import PostgresPrywatny

_watek_serwera: "WatekSerwera | None" = None
_postgres_prywatny: "PostgresPrywatny | None" = None


def zarejestruj(watek: "WatekSerwera | None", postgres: "PostgresPrywatny | None") -> None:
    global _watek_serwera, _postgres_prywatny
    _watek_serwera = watek
    _postgres_prywatny = postgres


def postgres_prywatny() -> "PostgresPrywatny | None":
    return _postgres_prywatny


def zatrzymaj_serwer_fastapi() -> None:
    """Zatrzymuje WYLACZNIE watek FastAPI (i zamyka pule polaczen SQLAlchemy) -
    prywatny Postgres (jesli dotyczy) zostaje uruchomiony, bo operacje
    pg_dump/pg_restore/dropdb/createdb potrzebuja dzialajacego serwera bazy,
    do ktorego moga sie polaczyc wlasnymi, niezaleznymi polaczeniami klienckimi."""
    from app.database import engine
    from gui.main import zatrzymaj_serwer

    zatrzymaj_serwer(_watek_serwera)
    engine.dispose()


def zatrzymaj_wszystko() -> None:
    """Pelne, czyste zamkniecie - ten sam efekt koncowy co normalne zamkniecie
    okna aplikacji (gui/main.py:_przy_zamknieciu). Wolane PO udanym
    przywroceniu kopii zapasowej, tuz przed wymuszeniem ponownego uruchomienia
    calej appki (patrz gui/kopia_zapasowa.py)."""
    zatrzymaj_serwer_fastapi()
    if _postgres_prywatny is not None:
        _postgres_prywatny.zatrzymaj()
