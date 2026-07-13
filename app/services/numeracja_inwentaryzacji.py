from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.licznik_numeracji_inwentaryzacji import LicznikNumeracjiInwentaryzacji

PREFIKS_NUMERU_INWENTARYZACJI = "INW"


def nastepny_numer_inwentaryzacji(db: Session, rok: int) -> str:
    """Zwraca kolejny, ciagly numer spisu inwentaryzacyjnego dla danego roku
    (np. INW/2026/0001). Mirror app/services/numeracja.py (faktury) - jeden
    wspolny rejestr na rok, bez rozroznienia typu."""
    licznik = db.execute(
        select(LicznikNumeracjiInwentaryzacji)
        .where(LicznikNumeracjiInwentaryzacji.rok == rok)
        .with_for_update()
    ).scalar_one_or_none()

    if licznik is None:
        licznik = LicznikNumeracjiInwentaryzacji(rok=rok, ostatni_numer=0)
        db.add(licznik)
        db.flush()

    licznik.ostatni_numer += 1
    db.flush()

    return f"{PREFIKS_NUMERU_INWENTARYZACJI}/{rok}/{licznik.ostatni_numer:04d}"
