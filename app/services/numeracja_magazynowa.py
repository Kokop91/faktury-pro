from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.enums import TypDokumentuMagazynowego
from app.models.licznik_numeracji_magazynowej import LicznikNumeracjiMagazynowej

PREFIKSY_TYPU_DOKUMENTU: dict[TypDokumentuMagazynowego, str] = {
    TypDokumentuMagazynowego.PZ: "PZ",
    TypDokumentuMagazynowego.WZ: "WZ",
    TypDokumentuMagazynowego.PW: "PW",
    TypDokumentuMagazynowego.RW: "RW",
    TypDokumentuMagazynowego.MM: "MM",
}


def nastepny_numer_dokumentu_magazynowego(
    db: Session, typ: TypDokumentuMagazynowego, rok: int
) -> str:
    """Zwraca kolejny, ciagly numer dokumentu magazynowego dla danego typu i roku
    (np. PZ/2026/0001, WZ/2026/0001 - osobna numeracja dla kazdego typu).

    Blokuje wiersz licznika (SELECT ... FOR UPDATE), zeby rownolegle requesty
    nie dostaly tego samego numeru - mirror app/services/numeracja.py.
    """
    licznik = db.execute(
        select(LicznikNumeracjiMagazynowej)
        .where(
            LicznikNumeracjiMagazynowej.typ == typ,
            LicznikNumeracjiMagazynowej.rok == rok,
        )
        .with_for_update()
    ).scalar_one_or_none()

    if licznik is None:
        licznik = LicznikNumeracjiMagazynowej(typ=typ, rok=rok, ostatni_numer=0)
        db.add(licznik)
        db.flush()

    licznik.ostatni_numer += 1
    db.flush()

    prefiks = PREFIKSY_TYPU_DOKUMENTU[typ]
    return f"{prefiks}/{rok}/{licznik.ostatni_numer:04d}"
