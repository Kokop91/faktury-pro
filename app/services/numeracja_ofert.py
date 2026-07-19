from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.licznik_numeracji_ofert import LicznikNumeracjiOfert

PREFIKS_NUMERU_OFERTY = "OF"


def nastepny_numer_oferty(db: Session, rok: int) -> str:
    """Zwraca kolejny, ciagly numer oferty dla danego roku (np. OF/2026/0001).

    Blokuje wiersz licznika (SELECT ... FOR UPDATE), zeby rownolegle requesty
    nie dostaly tego samego numeru - mirror app/services/numeracja.py.
    """
    licznik = db.execute(
        select(LicznikNumeracjiOfert).where(LicznikNumeracjiOfert.rok == rok).with_for_update()
    ).scalar_one_or_none()

    if licznik is None:
        licznik = LicznikNumeracjiOfert(rok=rok, ostatni_numer=0)
        db.add(licznik)
        db.flush()

    licznik.ostatni_numer += 1
    db.flush()

    return f"{PREFIKS_NUMERU_OFERTY}/{rok}/{licznik.ostatni_numer:04d}"
