from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.licznik_numeracji import LicznikNumeracji

PREFIKS_NUMERU_FAKTURY = "FV"


def nastepny_numer_faktury(db: Session, rok: int) -> str:
    """Zwraca kolejny, ciagly numer faktury dla danego roku (np. FV/2026/0001).

    Blokuje wiersz licznika (SELECT ... FOR UPDATE), zeby rownolegle requesty
    nie dostaly tego samego numeru.
    """
    licznik = db.execute(
        select(LicznikNumeracji).where(LicznikNumeracji.rok == rok).with_for_update()
    ).scalar_one_or_none()

    if licznik is None:
        licznik = LicznikNumeracji(rok=rok, ostatni_numer=0)
        db.add(licznik)
        db.flush()

    licznik.ostatni_numer += 1
    db.flush()

    return f"{PREFIKS_NUMERU_FAKTURY}/{rok}/{licznik.ostatni_numer:04d}"
