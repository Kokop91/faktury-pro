"""Przeliczenie StanMagazynowy od zera na podstawie zapisanych dokumentow
magazynowych - narzedzie naprawcze/diagnostyczne, NIE czesc appki.

KONTEKST: zgloszenie uzytkownika koncowego "po zapisaniu PZ stan magazynowy
sie nie zmienil". Zdiagnozowane: app/services/magazyn_service.py zawsze
aplikowal zmiane stanu NATYCHMIAST przy zapisaniu/edycji dokumentu (nie
dopiero przy zatwierdzeniu) - kod byl poprawny od Fazy 27 w gore, zweryfikowane
bezposrednio na bazie deweloperskiej (PZ/WZ/PW/RW/MM, wszystkie 5 typow).
Rzeczywista przyczyna zgloszenia byla gdzie indziej: zakladki "Produkty" i
"Stany magazynowe" (gui/windows/panel_produktow.py, panel_stanow_magazynowych.py)
nie odswiezaly sie automatycznie po zapisaniu dokumentu w sasiedniej zakladce
"Dokumenty" w tym samym widoku Magazynu (naprawione w
gui/windows/panel_dokumentow_magazynowych.py i panel_inwentaryzacji.py -
patrz `on_zmiana_stanu` w gui/windows/widok_magazynu.py).

Ten skrypt to mimo to przydatna siatka bezpieczenstwa - jesli z jakiegokolwiek
INNEGO powodu (recznie edytowana baza, przerwana transakcja, import danych)
StanMagazynowy przestal zgadzac sie z suma ruchow z PozycjaDokumentuMagazynowego,
przelicza go od zera i pokazuje/naprawia roznice.

Zasada przeliczania - mirror app/services/magazyn_service.py (TYPY_ZWIEKSZAJACE_DOCELOWY/
TYPY_ZMNIEJSZAJACE_ZRODLOWY) - LICZY WSZYSTKIE dokumenty, niezaleznie od statusu
(roboczy/zatwierdzony), bo appka NIGDY nie odracza wplywu dokumentu na stan do
momentu zatwierdzenia - to jest wlasnie zachowanie, ktore ten skrypt odtwarza.

Uzycie:
    python scripts/przelicz_stany_magazynowe.py --database-url postgresql://postgres@127.0.0.1:55432/faktury_pro
    (bez --database-url domyslnie uzywa app.config.DATABASE_URL / prywatnego
    Postgresa z .env - wygodne w srodowisku deweloperskim)

Domyslnie DRY-RUN - pokazuje tylko roznice, NIC nie zapisuje. Dopiero
--zastosuj faktycznie nadpisuje StanMagazynowy.ilosc obliczona wartoscia.
"""
import argparse
import sys
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

# Pozwala uruchamiac skrypt z dowolnego katalogu roboczego (nie tylko z korzenia
# repo) - potrzebne dla `import app.*` ponizej, ktory zaklada, ze korzen repo
# jest na sys.path (tak jak dziala przy normalnym starcie appki przez gui/main.py).
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _typy_ruchu():
    # Import odroczony - pozwala uruchomic skrypt z jawnym --database-url bez
    # koniecznosci posiadania poprawnie skonfigurowanego .env/profilu appki
    # (app.config wymaga tego kontekstu przy imporcie, patrz CLAUDE.md Faza 25).
    from app.models.enums import TypDokumentuMagazynowego

    zwiekszajace_docelowy = frozenset(
        {
            TypDokumentuMagazynowego.PZ,
            TypDokumentuMagazynowego.PW,
            TypDokumentuMagazynowego.MM,
        }
    )
    zmniejszajace_zrodlowy = frozenset(
        {
            TypDokumentuMagazynowego.WZ,
            TypDokumentuMagazynowego.RW,
            TypDokumentuMagazynowego.MM,
        }
    )
    return zwiekszajace_docelowy, zmniejszajace_zrodlowy


def przelicz(db: Session, zastosuj: bool) -> int:
    from app.models import DokumentMagazynowy, PozycjaDokumentuMagazynowego, StanMagazynowy

    zwiekszajace_docelowy, zmniejszajace_zrodlowy = _typy_ruchu()

    dokumenty = {
        d.id: d for d in db.execute(select(DokumentMagazynowy)).scalars().all()
    }
    pozycje = db.execute(select(PozycjaDokumentuMagazynowego)).scalars().all()

    obliczone: dict[tuple[int, int], Decimal] = defaultdict(lambda: Decimal("0"))
    for pozycja in pozycje:
        dokument = dokumenty.get(pozycja.dokument_id)
        if dokument is None:
            continue
        if dokument.typ in zmniejszajace_zrodlowy and dokument.magazyn_zrodlowy_id:
            klucz = (pozycja.produkt_id, dokument.magazyn_zrodlowy_id)
            obliczone[klucz] -= pozycja.ilosc
        if dokument.typ in zwiekszajace_docelowy and dokument.magazyn_docelowy_id:
            klucz = (pozycja.produkt_id, dokument.magazyn_docelowy_id)
            obliczone[klucz] += pozycja.ilosc

    istniejace = {
        (s.produkt_id, s.magazyn_id): s
        for s in db.execute(select(StanMagazynowy)).scalars().all()
    }

    wszystkie_klucze = set(obliczone) | set(istniejace)
    liczba_roznic = 0

    for klucz in sorted(wszystkie_klucze):
        produkt_id, magazyn_id = klucz
        docelowa_ilosc = obliczone.get(klucz, Decimal("0"))
        stan = istniejace.get(klucz)
        biezaca_ilosc = stan.ilosc if stan is not None else None

        if biezaca_ilosc == docelowa_ilosc:
            continue

        liczba_roznic += 1
        print(
            f"produkt_id={produkt_id:>5}  magazyn_id={magazyn_id:>3}  "
            f"w bazie={'brak wiersza' if biezaca_ilosc is None else biezaca_ilosc:>12}  "
            f"obliczone={docelowa_ilosc:>12}"
        )

        if zastosuj:
            if stan is None:
                stan = StanMagazynowy(
                    produkt_id=produkt_id, magazyn_id=magazyn_id, ilosc=docelowa_ilosc
                )
                db.add(stan)
            else:
                stan.ilosc = docelowa_ilosc

    if zastosuj and liczba_roznic:
        db.commit()

    return liczba_roznic


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database-url",
        default=None,
        help=(
            "Connection string do bazy Postgres (np. "
            "postgresql://postgres@127.0.0.1:55432/faktury_pro dla prywatnej "
            "instancji appki). Bez tej opcji uzywa app.config.DATABASE_URL "
            "(wymaga poprawnie skonfigurowanego .env/profilu - wygodne tylko "
            "w srodowisku deweloperskim)."
        ),
    )
    parser.add_argument(
        "--zastosuj",
        action="store_true",
        help="Faktycznie zapisz obliczone wartosci. Bez tej flagi: tylko pokaz roznice (dry-run).",
    )
    argumenty = parser.parse_args()

    if argumenty.database_url:
        silnik = create_engine(argumenty.database_url)
        Sesja = sessionmaker(bind=silnik)
        db = Sesja()
    else:
        from app.database import SessionLocal

        db = SessionLocal()

    try:
        tryb = "ZASTOSUJ (zapisuje zmiany)" if argumenty.zastosuj else "DRY-RUN (tylko podglad)"
        print(f"Tryb: {tryb}\n")
        liczba_roznic = przelicz(db, argumenty.zastosuj)
        print(f"\nZnaleziono roznic: {liczba_roznic}")
        if liczba_roznic and not argumenty.zastosuj:
            print("Uruchom ponownie z --zastosuj, zeby faktycznie zapisac powyzsze wartosci.")
    finally:
        db.close()


if __name__ == "__main__":
    main()
