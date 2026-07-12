from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Faktura, Klient, PozycjaFaktury
from app.models.enums import StatusFaktury, StawkaVat
from app.schemas.faktura import FakturaCreate, FakturaUpdate, PozycjaFakturyCreate
from app.services.numeracja import nastepny_numer_faktury

UDZIAL_STAWKI_VAT: dict[StawkaVat, Decimal] = {
    StawkaVat.STAWKA_23: Decimal("0.23"),
    StawkaVat.STAWKA_8: Decimal("0.08"),
    StawkaVat.STAWKA_5: Decimal("0.05"),
    StawkaVat.STAWKA_0: Decimal("0.00"),
    StawkaVat.ZW: Decimal("0.00"),
}

# Dozwolone przejscia statusu faktury. ROBOCZA->ANULOWANA i dalsze przejscia
# do ANULOWANA sa mozliwe (np. blad wystawienia); ANULOWANA i OPLACONA sa stanami
# koncowymi. Powrot do ROBOCZA po wystawieniu nie jest dozwolony.
DOZWOLONE_PRZEJSCIA_STATUSU: dict[StatusFaktury, set[StatusFaktury]] = {
    StatusFaktury.ROBOCZA: {StatusFaktury.WYSTAWIONA, StatusFaktury.ANULOWANA},
    StatusFaktury.WYSTAWIONA: {
        StatusFaktury.WYSLANA,
        StatusFaktury.OPLACONA_CZESCIOWO,
        StatusFaktury.OPLACONA,
        StatusFaktury.PO_TERMINIE,
        StatusFaktury.ANULOWANA,
    },
    StatusFaktury.WYSLANA: {
        StatusFaktury.OPLACONA_CZESCIOWO,
        StatusFaktury.OPLACONA,
        StatusFaktury.PO_TERMINIE,
        StatusFaktury.ANULOWANA,
    },
    StatusFaktury.OPLACONA_CZESCIOWO: {
        StatusFaktury.OPLACONA,
        StatusFaktury.PO_TERMINIE,
        StatusFaktury.ANULOWANA,
    },
    StatusFaktury.PO_TERMINIE: {
        StatusFaktury.OPLACONA_CZESCIOWO,
        StatusFaktury.OPLACONA,
        StatusFaktury.ANULOWANA,
    },
    StatusFaktury.OPLACONA: set(),
    StatusFaktury.ANULOWANA: set(),
}


def _zaokraglij_do_grosza(wartosc: Decimal) -> int:
    return int(wartosc.quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _przelicz_pozycje(
    pozycje_in: list[PozycjaFakturyCreate],
) -> list[PozycjaFaktury]:
    """Przelicza netto/VAT/brutto pozycji po stronie serwera. Nigdy nie ufamy
    przeliczeniom z frontendu - liczymy wylacznie na podstawie ceny, ilosci
    i stawki VAT, zaokraglajac kazda pozycje do pelnego grosza.
    """
    pozycje = []
    for pozycja_in in pozycje_in:
        wartosc_netto_grosze = _zaokraglij_do_grosza(
            Decimal(pozycja_in.cena_netto_grosze) * pozycja_in.ilosc
        )
        udzial_vat = UDZIAL_STAWKI_VAT[pozycja_in.stawka_vat]
        wartosc_vat_grosze = _zaokraglij_do_grosza(
            Decimal(wartosc_netto_grosze) * udzial_vat
        )
        wartosc_brutto_grosze = wartosc_netto_grosze + wartosc_vat_grosze

        pozycje.append(
            PozycjaFaktury(
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


def pobierz_fakture(db: Session, faktura_id: int) -> Faktura:
    zapytanie = (
        select(Faktura)
        .options(selectinload(Faktura.pozycje))
        .where(Faktura.id == faktura_id)
    )
    faktura = db.execute(zapytanie).scalar_one_or_none()
    if faktura is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nie znaleziono faktury o podanym id.",
        )
    return faktura


def lista_faktur(
    db: Session,
    skip: int,
    limit: int,
    status_filtr: StatusFaktury | None,
    klient_id_filtr: int | None,
) -> list[Faktura]:
    zapytanie = select(Faktura).options(selectinload(Faktura.pozycje))
    if status_filtr is not None:
        zapytanie = zapytanie.where(Faktura.status == status_filtr)
    if klient_id_filtr is not None:
        zapytanie = zapytanie.where(Faktura.klient_id == klient_id_filtr)
    zapytanie = zapytanie.order_by(Faktura.id.desc()).offset(skip).limit(limit)
    return list(db.execute(zapytanie).scalars().unique().all())


def utworz_fakture(db: Session, dane: FakturaCreate) -> Faktura:
    klient = _pobierz_klienta_lub_404(db, dane.klient_id)

    termin_platnosci = dane.termin_platnosci or (
        dane.data_wystawienia + timedelta(days=klient.domyslny_termin_platnosci_dni)
    )
    waluta = dane.waluta or klient.domyslna_waluta
    numer = nastepny_numer_faktury(db, dane.data_wystawienia.year)

    faktura = Faktura(
        numer=numer,
        typ_dokumentu=dane.typ_dokumentu,
        klient_id=klient.id,
        data_wystawienia=dane.data_wystawienia,
        data_sprzedazy=dane.data_sprzedazy,
        termin_platnosci=termin_platnosci,
        waluta=waluta,
        kurs_waluty=dane.kurs_waluty,
        status=StatusFaktury.ROBOCZA,
        pozycje=_przelicz_pozycje(dane.pozycje),
    )

    db.add(faktura)
    db.commit()
    db.refresh(faktura)
    return faktura


def aktualizuj_fakture(db: Session, faktura_id: int, dane: FakturaUpdate) -> Faktura:
    faktura = pobierz_fakture(db, faktura_id)
    if faktura.status != StatusFaktury.ROBOCZA:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Nie mozna edytowac faktury w statusie '{faktura.status.value}' - "
                "edycja jest mozliwa tylko dla faktur w statusie 'robocza'."
            ),
        )

    zmiany = dane.model_dump(exclude_unset=True, exclude={"pozycje"})
    if "klient_id" in zmiany:
        _pobierz_klienta_lub_404(db, zmiany["klient_id"])
    for pole, wartosc in zmiany.items():
        setattr(faktura, pole, wartosc)

    if dane.pozycje is not None:
        faktura.pozycje.clear()
        db.flush()
        faktura.pozycje.extend(_przelicz_pozycje(dane.pozycje))

    db.commit()
    db.refresh(faktura)
    return faktura


def zmien_status_faktury(
    db: Session, faktura_id: int, nowy_status: StatusFaktury
) -> Faktura:
    faktura = pobierz_fakture(db, faktura_id)
    if nowy_status == faktura.status:
        return faktura

    dozwolone = DOZWOLONE_PRZEJSCIA_STATUSU.get(faktura.status, set())
    if nowy_status not in dozwolone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Nie mozna zmienic statusu z '{faktura.status.value}' "
                f"na '{nowy_status.value}'."
            ),
        )

    faktura.status = nowy_status
    db.commit()
    db.refresh(faktura)
    return faktura
