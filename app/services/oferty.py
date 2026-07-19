from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Faktura, Klient, Oferta, PozycjaOferty
from app.models.enums import StatusOferty
from app.schemas.faktura import FakturaCreate, PozycjaFakturyCreate
from app.schemas.oferta import OfertaCreate, OfertaOut, OfertaUpdate, PozycjaOfertyCreate
from app.services import faktury as faktury_service
from app.services.numeracja_ofert import nastepny_numer_oferty

# Dozwolone przejscia statusu oferty. WYGASLA nigdy nie jest kluczem ani
# wartoscia tutaj - jest wylacznie statusem efektywnym (patrz
# oblicz_status_efektywny), nigdy trwale zapisywanym.
DOZWOLONE_PRZEJSCIA_STATUSU: dict[StatusOferty, set[StatusOferty]] = {
    StatusOferty.ROBOCZA: {
        StatusOferty.WYSLANA,
        StatusOferty.ZAAKCEPTOWANA,
        StatusOferty.ODRZUCONA,
    },
    StatusOferty.WYSLANA: {StatusOferty.ZAAKCEPTOWANA, StatusOferty.ODRZUCONA},
    StatusOferty.ZAAKCEPTOWANA: set(),
    StatusOferty.ODRZUCONA: set(),
}


def _zaokraglij_do_grosza(wartosc: Decimal) -> int:
    return int(wartosc.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _przelicz_pozycje(pozycje_in: list[PozycjaOfertyCreate]) -> list[PozycjaOferty]:
    """Przelicza netto/VAT/brutto pozycji po stronie serwera - mirror
    app/services/faktury.py:_przelicz_pozycje, reuzywajac ten sam slownik
    udzialu stawki VAT (UDZIAL_STAWKI_VAT), zeby nie trzymac go w dwoch
    miejscach."""
    pozycje = []
    for pozycja_in in pozycje_in:
        wartosc_netto_grosze = _zaokraglij_do_grosza(
            Decimal(pozycja_in.cena_netto_grosze) * pozycja_in.ilosc
        )
        udzial_vat = faktury_service.UDZIAL_STAWKI_VAT[pozycja_in.stawka_vat]
        wartosc_vat_grosze = _zaokraglij_do_grosza(
            Decimal(wartosc_netto_grosze) * udzial_vat
        )
        wartosc_brutto_grosze = wartosc_netto_grosze + wartosc_vat_grosze

        pozycje.append(
            PozycjaOferty(
                nazwa=pozycja_in.nazwa,
                ilosc=pozycja_in.ilosc,
                jednostka_miary=pozycja_in.jednostka_miary,
                cena_netto_grosze=pozycja_in.cena_netto_grosze,
                stawka_vat=pozycja_in.stawka_vat,
                wartosc_netto_grosze=wartosc_netto_grosze,
                wartosc_vat_grosze=wartosc_vat_grosze,
                wartosc_brutto_grosze=wartosc_brutto_grosze,
            )
        )
    return pozycje


def _pobierz_klienta_lub_404(db: Session, klient_id: int) -> Klient:
    klient = db.get(Klient, klient_id)
    if klient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nie znaleziono klienta o podanym id.",
        )
    return klient


def pobierz_oferte(db: Session, oferta_id: int) -> Oferta:
    zapytanie = (
        select(Oferta)
        .options(
            selectinload(Oferta.pozycje), selectinload(Oferta.faktury_wygenerowane)
        )
        .where(Oferta.id == oferta_id)
    )
    oferta = db.execute(zapytanie).scalar_one_or_none()
    if oferta is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nie znaleziono oferty o podanym id.",
        )
    return oferta


def lista_ofert(
    db: Session,
    skip: int,
    limit: int,
    status_filtr: StatusOferty | None,
    klient_id_filtr: int | None,
) -> list[Oferta]:
    zapytanie = select(Oferta).options(
        selectinload(Oferta.pozycje), selectinload(Oferta.faktury_wygenerowane)
    )
    if status_filtr is not None:
        zapytanie = zapytanie.where(Oferta.status == status_filtr)
    if klient_id_filtr is not None:
        zapytanie = zapytanie.where(Oferta.klient_id == klient_id_filtr)
    zapytanie = zapytanie.order_by(Oferta.id.desc()).offset(skip).limit(limit)
    return list(db.execute(zapytanie).scalars().unique().all())


def utworz_oferte(db: Session, dane: OfertaCreate) -> Oferta:
    klient = _pobierz_klienta_lub_404(db, dane.klient_id)

    waluta = dane.waluta or klient.domyslna_waluta
    numer = nastepny_numer_oferty(db, dane.data_wystawienia.year)
    pozycje = _przelicz_pozycje(dane.pozycje)

    oferta = Oferta(
        numer=numer,
        klient_id=klient.id,
        data_wystawienia=dane.data_wystawienia,
        data_waznosci=dane.data_waznosci,
        waluta=waluta,
        kurs_waluty=dane.kurs_waluty,
        status=StatusOferty.ROBOCZA,
        pozycje=pozycje,
    )

    db.add(oferta)
    db.commit()
    db.refresh(oferta)
    return oferta


def aktualizuj_oferte(db: Session, oferta_id: int, dane: OfertaUpdate) -> Oferta:
    oferta = pobierz_oferte(db, oferta_id)
    if oferta.status != StatusOferty.ROBOCZA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Nie mozna edytowac oferty w statusie '{oferta.status.value}' - "
                "edycja jest mozliwa tylko dla ofert w statusie 'robocza'."
            ),
        )

    zmiany = dane.model_dump(exclude_unset=True, exclude={"pozycje"})
    if "klient_id" in zmiany:
        _pobierz_klienta_lub_404(db, zmiany["klient_id"])

    if dane.pozycje is not None and not dane.pozycje:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Oferta musi mieć co najmniej jedną pozycję.",
        )

    for pole, wartosc in zmiany.items():
        setattr(oferta, pole, wartosc)

    if dane.pozycje is not None:
        oferta.pozycje.clear()
        db.flush()
        oferta.pozycje.extend(_przelicz_pozycje(dane.pozycje))

    db.commit()
    db.refresh(oferta)
    return oferta


def zmien_status_oferty(
    db: Session, oferta_id: int, nowy_status: StatusOferty
) -> Oferta:
    oferta = pobierz_oferte(db, oferta_id)
    if nowy_status == oferta.status:
        return oferta

    dozwolone = DOZWOLONE_PRZEJSCIA_STATUSU.get(oferta.status, set())
    if nowy_status not in dozwolone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Nie mozna zmienic statusu z '{oferta.status.value}' "
                f"na '{nowy_status.value}'."
            ),
        )

    oferta.status = nowy_status
    db.commit()
    db.refresh(oferta)
    return oferta


def oblicz_status_efektywny(oferta: Oferta, dzisiaj: date) -> StatusOferty:
    """Wylicza status oferty na podstawie daty waznosci, bez zapisu do bazy -
    mirror app/services/platnosci.py:oblicz_status_efektywny. Robocza jeszcze
    nie zostala wyslana klientowi, wiec nie "wygasa"; zaakceptowana/odrzucona
    to decyzje juz podjete, tez nie wygasaja."""
    if oferta.status in (
        StatusOferty.ROBOCZA,
        StatusOferty.ZAAKCEPTOWANA,
        StatusOferty.ODRZUCONA,
    ):
        return oferta.status
    if oferta.data_waznosci < dzisiaj:
        return StatusOferty.WYGASLA
    return oferta.status


def zbuduj_oferte_out(oferta: Oferta, dzisiaj: date | None = None) -> OfertaOut:
    # Atrybuty przejsciowe (nie mapowane kolumny) - bezpieczne do ustawienia
    # na instancji ORM, mirror platnosci.zbuduj_fakture_out.
    oferta.status_efektywny = oblicz_status_efektywny(oferta, dzisiaj or date.today())
    oferta.faktura_wygenerowana_id = (
        oferta.faktury_wygenerowane[0].id if oferta.faktury_wygenerowane else None
    )
    return OfertaOut.model_validate(oferta)


def wystaw_fakture_z_oferty(db: Session, oferta_id: int) -> Faktura:
    oferta = pobierz_oferte(db, oferta_id)

    if oferta.status != StatusOferty.ZAAKCEPTOWANA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Fakturę można wystawić tylko z zaakceptowanej oferty.",
        )
    if oferta.faktury_wygenerowane:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Z tej oferty faktura została już wystawiona "
                f"(numer {oferta.faktury_wygenerowane[0].numer})."
            ),
        )

    dzisiaj = date.today()
    dane = FakturaCreate(
        klient_id=oferta.klient_id,
        data_wystawienia=dzisiaj,
        data_sprzedazy=dzisiaj,
        waluta=oferta.waluta,
        kurs_waluty=oferta.kurs_waluty,
        pozycje=[
            PozycjaFakturyCreate(
                nazwa=p.nazwa,
                ilosc=p.ilosc,
                jednostka_miary=p.jednostka_miary,
                cena_netto_grosze=p.cena_netto_grosze,
                stawka_vat=p.stawka_vat,
            )
            for p in oferta.pozycje
        ],
    )
    faktura = faktury_service.utworz_fakture(db, dane)
    faktura.oferta_zrodlowa_id = oferta.id
    db.commit()
    db.refresh(faktura)
    return faktura
