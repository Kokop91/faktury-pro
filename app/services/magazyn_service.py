from datetime import date
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models import (
    DokumentMagazynowy,
    Firma,
    Magazyn,
    PozycjaDokumentuMagazynowego,
    Produkt,
    StanMagazynowy,
)
from app.models.enums import TrybBlokadyStanu, TypDokumentuMagazynowego
from app.schemas.magazyn import (
    DokumentMagazynowyCreate,
    MagazynCreate,
    ProduktCreate,
    RuchMagazynowyOut,
    StanMagazynowyOut,
)
from app.services.numeracja_magazynowa import nastepny_numer_dokumentu_magazynowego

# Typy dokumentow zwiekszajace stan w magazynie docelowym vs zmniejszajace stan
# w magazynie zrodlowym - MM robi obie rzeczy naraz. Patrz PLAN_PROJEKTU.md 3.3.
TYPY_ZWIEKSZAJACE_DOCELOWY: frozenset[TypDokumentuMagazynowego] = frozenset(
    {
        TypDokumentuMagazynowego.PZ,
        TypDokumentuMagazynowego.PW,
        TypDokumentuMagazynowego.MM,
    }
)
TYPY_ZMNIEJSZAJACE_ZRODLOWY: frozenset[TypDokumentuMagazynowego] = frozenset(
    {
        TypDokumentuMagazynowego.WZ,
        TypDokumentuMagazynowego.RW,
        TypDokumentuMagazynowego.MM,
    }
)

# Ktory z (magazyn_zrodlowy, magazyn_docelowy) jest wymagany dla danego typu.
WYMAGANE_MAGAZYNY: dict[TypDokumentuMagazynowego, tuple[bool, bool]] = {
    TypDokumentuMagazynowego.PZ: (False, True),
    TypDokumentuMagazynowego.WZ: (True, False),
    TypDokumentuMagazynowego.PW: (False, True),
    TypDokumentuMagazynowego.RW: (True, False),
    TypDokumentuMagazynowego.MM: (True, True),
}


def _pobierz_jedyna_firme(db: Session) -> Firma:
    """Mirror app/services/klienci.py - zduplikowane celowo, osobny modul
    biznesowy (magazyn) nie powinien zalezec od modulu klientow/faktur."""
    firmy = db.execute(select(Firma)).scalars().all()
    if len(firmy) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Brak skonfigurowanej firmy (lub jest ich wiecej niz jedna) - "
                "dodaj dokladnie jeden rekord Firma przed uzyciem modulu magazynowego."
            ),
        )
    return firmy[0]


# --- Produkty ---


def utworz_produkt(db: Session, dane: ProduktCreate) -> Produkt:
    firma = _pobierz_jedyna_firme(db)
    produkt = Produkt(firma_id=firma.id, **dane.model_dump())
    db.add(produkt)
    db.commit()
    db.refresh(produkt)
    return produkt


def pobierz_produkt(db: Session, produkt_id: int) -> Produkt:
    produkt = db.get(Produkt, produkt_id)
    if produkt is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nie znaleziono produktu o podanym id.",
        )
    return produkt


def lista_produktow(
    db: Session, skip: int, limit: int, tylko_aktywne: bool
) -> list[Produkt]:
    zapytanie = select(Produkt)
    if tylko_aktywne:
        zapytanie = zapytanie.where(Produkt.aktywny.is_(True))
    zapytanie = zapytanie.order_by(Produkt.nazwa).offset(skip).limit(limit)
    return list(db.execute(zapytanie).scalars().all())


# --- Magazyny ---


def utworz_magazyn(db: Session, dane: MagazynCreate) -> Magazyn:
    firma = _pobierz_jedyna_firme(db)
    magazyn = Magazyn(firma_id=firma.id, **dane.model_dump())
    db.add(magazyn)
    db.commit()
    db.refresh(magazyn)
    return magazyn


def pobierz_magazyn(db: Session, magazyn_id: int) -> Magazyn:
    magazyn = db.get(Magazyn, magazyn_id)
    if magazyn is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nie znaleziono magazynu o podanym id.",
        )
    return magazyn


def lista_magazynow(
    db: Session, skip: int, limit: int, tylko_aktywne: bool
) -> list[Magazyn]:
    zapytanie = select(Magazyn)
    if tylko_aktywne:
        zapytanie = zapytanie.where(Magazyn.aktywny.is_(True))
    zapytanie = zapytanie.order_by(Magazyn.nazwa).offset(skip).limit(limit)
    return list(db.execute(zapytanie).scalars().all())


# --- Stany magazynowe ---


def _pobierz_lub_utworz_stan(
    db: Session, produkt_id: int, magazyn_id: int
) -> StanMagazynowy:
    stan = db.execute(
        select(StanMagazynowy)
        .where(
            StanMagazynowy.produkt_id == produkt_id,
            StanMagazynowy.magazyn_id == magazyn_id,
        )
        .with_for_update()
    ).scalar_one_or_none()

    if stan is None:
        stan = StanMagazynowy(
            produkt_id=produkt_id, magazyn_id=magazyn_id, ilosc=Decimal("0")
        )
        db.add(stan)
        db.flush()

    return stan


def _zmien_ilosc(
    db: Session, produkt_id: int, magazyn_id: int, delta: Decimal
) -> StanMagazynowy:
    stan = _pobierz_lub_utworz_stan(db, produkt_id, magazyn_id)
    stan.ilosc = stan.ilosc + delta
    db.flush()
    return stan


def _sprawdz_ujemny_stan(
    firma: Firma, stan: StanMagazynowy, produkt: Produkt, magazyn: Magazyn
) -> str | None:
    if stan.ilosc >= 0:
        return None

    komunikat = (
        f"Stan produktu '{produkt.nazwa}' w magazynie '{magazyn.nazwa}' spadl "
        f"ponizej zera (aktualnie {stan.ilosc} {produkt.jednostka_miary})."
    )
    if firma.tryb_blokady_ujemnego_stanu == TrybBlokadyStanu.BLOKUJ:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=komunikat)
    return komunikat


def _zbuduj_stan_out(stan: StanMagazynowy) -> StanMagazynowyOut:
    return StanMagazynowyOut(
        id=stan.id,
        produkt_id=stan.produkt_id,
        magazyn_id=stan.magazyn_id,
        produkt_nazwa=stan.produkt.nazwa,
        jednostka_miary=stan.produkt.jednostka_miary,
        magazyn_nazwa=stan.magazyn.nazwa,
        ilosc=stan.ilosc,
        stan_minimalny=stan.stan_minimalny,
        ponizej_minimum=(
            stan.stan_minimalny is not None and stan.ilosc < stan.stan_minimalny
        ),
    )


def lista_stanow_magazynowych(
    db: Session, magazyn_id: int | None
) -> list[StanMagazynowyOut]:
    zapytanie = (
        select(StanMagazynowy)
        .join(Produkt)
        .options(
            joinedload(StanMagazynowy.produkt), joinedload(StanMagazynowy.magazyn)
        )
        .order_by(Produkt.nazwa)
    )
    if magazyn_id is not None:
        zapytanie = zapytanie.where(StanMagazynowy.magazyn_id == magazyn_id)
    stany = db.execute(zapytanie).scalars().all()
    return [_zbuduj_stan_out(stan) for stan in stany]


# --- Dokumenty magazynowe ---


def _waliduj_magazyny_dokumentu(
    typ: TypDokumentuMagazynowego,
    magazyn_zrodlowy_id: int | None,
    magazyn_docelowy_id: int | None,
) -> None:
    wymaga_zrodlowy, wymaga_docelowy = WYMAGANE_MAGAZYNY[typ]

    if wymaga_zrodlowy and magazyn_zrodlowy_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dokument typu '{typ.value}' wymaga wskazania magazynu zrodlowego.",
        )
    if not wymaga_zrodlowy and magazyn_zrodlowy_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Dokument typu '{typ.value}' nie moze miec wskazanego "
                "magazynu zrodlowego."
            ),
        )
    if wymaga_docelowy and magazyn_docelowy_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Dokument typu '{typ.value}' wymaga wskazania magazynu docelowego.",
        )
    if not wymaga_docelowy and magazyn_docelowy_id is not None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Dokument typu '{typ.value}' nie moze miec wskazanego "
                "magazynu docelowego."
            ),
        )
    if (
        typ == TypDokumentuMagazynowego.MM
        and magazyn_zrodlowy_id == magazyn_docelowy_id
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Magazyn zrodlowy i docelowy musza byc rozne dla przesuniecia MM.",
        )


def utworz_dokument_magazynowy(
    db: Session, dane: DokumentMagazynowyCreate
) -> tuple[DokumentMagazynowy, list[str]]:
    """Tworzy dokument magazynowy z pozycjami i aplikuje zmiany StanMagazynowy.
    Cala operacja to jedna transakcja (jeden db.commit() na koncu) - kazdy
    HTTPException podniesiony w trakcie (nieprawidlowy produkt, usluga w
    dokumencie, tryb "blokuj" ponizej zera) powoduje, ze sesja zamyka sie bez
    commitu i wszystkie czastkowe zmiany znikaja (patrz app/database.py get_db).
    """
    _waliduj_magazyny_dokumentu(
        dane.typ, dane.magazyn_zrodlowy_id, dane.magazyn_docelowy_id
    )

    magazyn_zrodlowy = (
        pobierz_magazyn(db, dane.magazyn_zrodlowy_id)
        if dane.magazyn_zrodlowy_id is not None
        else None
    )
    magazyn_docelowy = (
        pobierz_magazyn(db, dane.magazyn_docelowy_id)
        if dane.magazyn_docelowy_id is not None
        else None
    )

    produkty_wg_id: dict[int, Produkt] = {}
    for pozycja_in in dane.pozycje:
        if pozycja_in.produkt_id in produkty_wg_id:
            continue
        produkt = db.get(Produkt, pozycja_in.produkt_id)
        if produkt is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Nie znaleziono produktu o id {pozycja_in.produkt_id}.",
            )
        if not produkt.jest_magazynowy:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Produkt '{produkt.nazwa}' jest usluga (jest_magazynowy=False) "
                    "i nie moze wystepowac w dokumencie magazynowym."
                ),
            )
        produkty_wg_id[pozycja_in.produkt_id] = produkt

    firma = _pobierz_jedyna_firme(db)
    numer = nastepny_numer_dokumentu_magazynowego(
        db, dane.typ, dane.data_dokumentu.year
    )

    dokument = DokumentMagazynowy(
        typ=dane.typ,
        numer=numer,
        data_dokumentu=dane.data_dokumentu,
        magazyn_zrodlowy_id=dane.magazyn_zrodlowy_id,
        magazyn_docelowy_id=dane.magazyn_docelowy_id,
        faktura_powiazana_id=dane.faktura_powiazana_id,
    )
    db.add(dokument)
    db.flush()

    ostrzezenia: list[str] = []
    for pozycja_in in dane.pozycje:
        produkt = produkty_wg_id[pozycja_in.produkt_id]
        db.add(
            PozycjaDokumentuMagazynowego(
                dokument_id=dokument.id,
                produkt_id=produkt.id,
                ilosc=pozycja_in.ilosc,
                notatka=pozycja_in.notatka,
            )
        )

        if dane.typ in TYPY_ZMNIEJSZAJACE_ZRODLOWY:
            stan = _zmien_ilosc(
                db, produkt.id, dane.magazyn_zrodlowy_id, -pozycja_in.ilosc
            )
            ostrzezenie = _sprawdz_ujemny_stan(firma, stan, produkt, magazyn_zrodlowy)
            if ostrzezenie:
                ostrzezenia.append(ostrzezenie)

        if dane.typ in TYPY_ZWIEKSZAJACE_DOCELOWY:
            _zmien_ilosc(db, produkt.id, dane.magazyn_docelowy_id, pozycja_in.ilosc)

    db.commit()
    db.refresh(dokument)
    return dokument, ostrzezenia


def pobierz_dokument_magazynowy(db: Session, dokument_id: int) -> DokumentMagazynowy:
    zapytanie = (
        select(DokumentMagazynowy)
        .options(selectinload(DokumentMagazynowy.pozycje))
        .where(DokumentMagazynowy.id == dokument_id)
    )
    dokument = db.execute(zapytanie).scalar_one_or_none()
    if dokument is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nie znaleziono dokumentu magazynowego o podanym id.",
        )
    return dokument


def lista_dokumentow_magazynowych(
    db: Session,
    skip: int,
    limit: int,
    typ: TypDokumentuMagazynowego | None,
    magazyn_id: int | None,
    data_od: date | None,
    data_do: date | None,
) -> list[DokumentMagazynowy]:
    zapytanie = select(DokumentMagazynowy).options(
        selectinload(DokumentMagazynowy.pozycje)
    )
    if typ is not None:
        zapytanie = zapytanie.where(DokumentMagazynowy.typ == typ)
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

    zapytanie = (
        zapytanie.order_by(DokumentMagazynowy.id.desc()).offset(skip).limit(limit)
    )
    return list(db.execute(zapytanie).scalars().unique().all())


# --- Historia ruchow produktu ---


def historia_ruchow_produktu(db: Session, produkt_id: int) -> list[RuchMagazynowyOut]:
    """Historia wszystkich ruchow magazynowych danego produktu. Jedna pozycja
    dokumentu MM daje DWA ruchy (ujemny w zrodlowym, dodatni w docelowym) -
    pozostale typy daja jeden ruch w swoim jedynym magazynie. Nie ma pojecia
    "kto" - appka jest jednostanowiskowa i auth nie jest jeszcze zaimplementowane
    (Faza 6), wiec ta kolumna z sekcji 3.7 planu jest tu celowo pominieta.
    """
    pobierz_produkt(db, produkt_id)  # 404, jesli produkt nie istnieje

    zapytanie = (
        select(PozycjaDokumentuMagazynowego)
        .join(DokumentMagazynowy)
        .options(
            joinedload(PozycjaDokumentuMagazynowego.dokument).joinedload(
                DokumentMagazynowy.magazyn_zrodlowy
            ),
            joinedload(PozycjaDokumentuMagazynowego.dokument).joinedload(
                DokumentMagazynowy.magazyn_docelowy
            ),
        )
        .where(PozycjaDokumentuMagazynowego.produkt_id == produkt_id)
        .order_by(DokumentMagazynowy.data_dokumentu.desc(), DokumentMagazynowy.id.desc())
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
            "notatka": pozycja.notatka,
            "utworzono": dokument.utworzono,
        }
        if dokument.typ in TYPY_ZMNIEJSZAJACE_ZRODLOWY:
            ruchy.append(
                RuchMagazynowyOut(
                    magazyn_id=dokument.magazyn_zrodlowy_id,
                    magazyn_nazwa=dokument.magazyn_zrodlowy.nazwa,
                    zmiana_ilosci=-pozycja.ilosc,
                    **wspolne,
                )
            )
        if dokument.typ in TYPY_ZWIEKSZAJACE_DOCELOWY:
            ruchy.append(
                RuchMagazynowyOut(
                    magazyn_id=dokument.magazyn_docelowy_id,
                    magazyn_nazwa=dokument.magazyn_docelowy.nazwa,
                    zmiana_ilosci=pozycja.ilosc,
                    **wspolne,
                )
            )

    return ruchy
