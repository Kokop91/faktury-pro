from datetime import date

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app.models import DokumentMagazynowy, PozycjaDokumentuMagazynowego
from app.schemas.magazyn import RuchMagazynowyOut, StanMagazynowyOut
from app.services.magazyn_service import (
    TYPY_ZMNIEJSZAJACE_ZRODLOWY,
    TYPY_ZWIEKSZAJACE_DOCELOWY,
    lista_stanow_magazynowych,
)

# GET /raporty/stany-aktualne swiadomie NIE istnieje jako osobny endpoint -
# GET /stany-magazynowe z Fazy 8 juz zwraca dokladnie to samo (produkt, magazyn,
# ilosc, prog minimalny, oznaczenie ponizej minimum); dublowanie go tutaj byloby
# martwym kodem. GUI zakladki "Raporty" uzywa tego istniejacego endpointu wprost.


def historia_ruchow_magazynu(
    db: Session,
    magazyn_id: int | None,
    data_od: date | None,
    data_do: date | None,
) -> list[RuchMagazynowyOut]:
    """Jak magazyn_service.historia_ruchow_produktu, ale dla calego magazynu
    (albo wszystkich magazynow, gdy magazyn_id=None) i wszystkich produktow
    naraz, z opcjonalnym zakresem dat. Jedna pozycja dokumentu MM daje ruch w
    obu magazynach, gdy magazyn_id nie jest podany - albo tylko w tym, ktory
    pasuje do filtra, gdy jest.
    """
    zapytanie = (
        select(PozycjaDokumentuMagazynowego)
        .join(DokumentMagazynowy)
        .options(
            joinedload(PozycjaDokumentuMagazynowego.produkt),
            joinedload(PozycjaDokumentuMagazynowego.dokument).joinedload(
                DokumentMagazynowy.magazyn_zrodlowy
            ),
            joinedload(PozycjaDokumentuMagazynowego.dokument).joinedload(
                DokumentMagazynowy.magazyn_docelowy
            ),
        )
    )
    if magazyn_id is not None:
        zapytanie = zapytanie.where(
            or_(
                DokumentMagazynowy.magazyn_zrodlowy_id == magazyn_id,
                DokumentMagazynowy.magazyn_docelowy_id == magazyn_id,
            )
        )
    if data_od is not None:
        zapytanie = zapytanie.where(DokumentMagazynowy.data_dokumentu >= data_od)
    if data_do is not None:
        zapytanie = zapytanie.where(DokumentMagazynowy.data_dokumentu <= data_do)
    zapytanie = zapytanie.order_by(
        DokumentMagazynowy.data_dokumentu.desc(), DokumentMagazynowy.id.desc()
    )

    pozycje = db.execute(zapytanie).scalars().unique().all()

    ruchy: list[RuchMagazynowyOut] = []
    for pozycja in pozycje:
        dokument = pozycja.dokument
        wspolne = {
            "dokument_id": dokument.id,
            "typ_dokumentu": dokument.typ,
            "numer_dokumentu": dokument.numer,
            "data_dokumentu": dokument.data_dokumentu,
            "produkt_id": pozycja.produkt_id,
            "produkt_nazwa": pozycja.produkt.nazwa,
            "notatka": pozycja.notatka,
            "utworzono": dokument.utworzono,
        }

        if dokument.typ in TYPY_ZMNIEJSZAJACE_ZRODLOWY and (
            magazyn_id is None or dokument.magazyn_zrodlowy_id == magazyn_id
        ):
            ruchy.append(
                RuchMagazynowyOut(
                    magazyn_id=dokument.magazyn_zrodlowy_id,
                    magazyn_nazwa=dokument.magazyn_zrodlowy.nazwa,
                    zmiana_ilosci=-pozycja.ilosc,
                    **wspolne,
                )
            )

        if dokument.typ in TYPY_ZWIEKSZAJACE_DOCELOWY and (
            magazyn_id is None or dokument.magazyn_docelowy_id == magazyn_id
        ):
            ruchy.append(
                RuchMagazynowyOut(
                    magazyn_id=dokument.magazyn_docelowy_id,
                    magazyn_nazwa=dokument.magazyn_docelowy.nazwa,
                    zmiana_ilosci=pozycja.ilosc,
                    **wspolne,
                )
            )

    return ruchy


def lista_ponizej_minimum(
    db: Session, magazyn_id: int | None
) -> list[StanMagazynowyOut]:
    wszystkie = lista_stanow_magazynowych(db, magazyn_id)
    return [stan for stan in wszystkie if stan.ponizej_minimum]
