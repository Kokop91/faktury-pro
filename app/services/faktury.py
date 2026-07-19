from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models import Faktura, Klient, PozycjaFaktury
from app.models.enums import (
    DOZWOLONE_TYPY_DOKUMENTU_KORYGOWANEGO,
    StatusFaktury,
    StawkaVat,
    TypDokumentu,
)
from app.schemas.faktura import (
    FakturaCreate,
    FakturaUpdate,
    PozycjaFakturyCreate,
    znajdz_blad_zgodnosci_typu_dokumentu,
)
from app.services import mpp_service
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


def podsumowanie_wg_stawek(pozycje: list[PozycjaFaktury]) -> list[dict]:
    """Grupuje pozycje faktury wg stawki VAT, sumujac netto/vat/brutto w groszach.
    Uzywane przez PDF (Faza 3) i docelowo przez rejestr sprzedazy VAT (Faza 8).
    """
    podsumowanie: dict[StawkaVat, dict[str, int]] = {}
    for pozycja in pozycje:
        wpis = podsumowanie.setdefault(
            pozycja.stawka_vat, {"netto_grosze": 0, "vat_grosze": 0, "brutto_grosze": 0}
        )
        wpis["netto_grosze"] += pozycja.wartosc_netto_grosze
        wpis["vat_grosze"] += pozycja.wartosc_vat_grosze
        wpis["brutto_grosze"] += pozycja.wartosc_brutto_grosze

    return [
        {"stawka_vat": stawka, **wartosci}
        for stawka, wartosci in sorted(podsumowanie.items(), key=lambda kv: kv[0].value)
    ]


def _pobierz_dokument_powiazany_lub_404(db: Session, dokument_powiazany_id: int) -> Faktura:
    dokument = db.get(Faktura, dokument_powiazany_id)
    if dokument is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nie znaleziono dokumentu powiązanego o podanym id.",
        )
    return dokument


def _waliduj_dokument_powiazany(
    db: Session,
    typ_dokumentu: TypDokumentu,
    dokument_powiazany_id: int | None,
    faktura_id: int | None,
) -> None:
    if dokument_powiazany_id is None:
        return
    if dokument_powiazany_id == faktura_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Dokument nie może wskazywać samego siebie jako dokument powiązany.",
        )

    dokument_powiazany = _pobierz_dokument_powiazany_lub_404(db, dokument_powiazany_id)

    if typ_dokumentu == TypDokumentu.FAKTURA_KONCOWA:
        if dokument_powiazany.typ_dokumentu != TypDokumentu.FAKTURA_ZALICZKOWA:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Faktura końcowa musi wskazywać fakturę zaliczkową "
                    "jako dokument powiązany."
                ),
            )
    elif dokument_powiazany.typ_dokumentu not in DOZWOLONE_TYPY_DOKUMENTU_KORYGOWANEGO:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Nie można korygować dokumentu typu "
                f"'{dokument_powiazany.typ_dokumentu.value}'."
            ),
        )


def _waliduj_zgodnosc_dokumentu(
    db: Session,
    typ_dokumentu: TypDokumentu,
    pozycje: list,
    dokument_powiazany_id: int | None,
    przyczyna_korekty: str | None,
    faktura_id: int | None = None,
) -> None:
    """Zrodlo prawdy dla regul biznesowych zwiazanych z typ_dokumentu - wolane zarowno
    przy tworzeniu jak i edycji (na efektywnym stanie, patrz aktualizuj_fakture).
    """
    blad = znajdz_blad_zgodnosci_typu_dokumentu(
        typ_dokumentu, pozycje, dokument_powiazany_id, przyczyna_korekty
    )
    if blad is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=blad)

    _waliduj_dokument_powiazany(db, typ_dokumentu, dokument_powiazany_id, faktura_id)


def pobierz_fakture(db: Session, faktura_id: int) -> Faktura:
    zapytanie = (
        select(Faktura)
        .options(selectinload(Faktura.pozycje), selectinload(Faktura.platnosci))
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
    zapytanie = select(Faktura).options(
        selectinload(Faktura.pozycje), selectinload(Faktura.platnosci)
    )
    if status_filtr is not None:
        zapytanie = zapytanie.where(Faktura.status == status_filtr)
    if klient_id_filtr is not None:
        zapytanie = zapytanie.where(Faktura.klient_id == klient_id_filtr)
    zapytanie = zapytanie.order_by(Faktura.id.desc()).offset(skip).limit(limit)
    return list(db.execute(zapytanie).scalars().unique().all())


def utworz_fakture(db: Session, dane: FakturaCreate) -> Faktura:
    klient = _pobierz_klienta_lub_404(db, dane.klient_id)
    _waliduj_zgodnosc_dokumentu(
        db,
        dane.typ_dokumentu,
        dane.pozycje,
        dane.dokument_powiazany_id,
        dane.przyczyna_korekty,
    )

    termin_platnosci = dane.termin_platnosci or (
        dane.data_wystawienia + timedelta(days=klient.domyslny_termin_platnosci_dni)
    )
    waluta = dane.waluta or klient.domyslna_waluta
    numer = nastepny_numer_faktury(db, dane.data_wystawienia.year)
    pozycje = _przelicz_pozycje(dane.pozycje)

    if dane.wymaga_mpp is None:
        suma_brutto_grosze = sum(p.wartosc_brutto_grosze for p in pozycje)
        wymaga_mpp = mpp_service.sugeruj_wymaga_mpp(
            db, klient, suma_brutto_grosze, [p.nazwa for p in pozycje]
        )
    else:
        wymaga_mpp = dane.wymaga_mpp

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
        dokument_powiazany_id=dane.dokument_powiazany_id,
        przyczyna_korekty=dane.przyczyna_korekty,
        pozycje=pozycje,
        wymaga_mpp=wymaga_mpp,
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

    zmiany = dane.model_dump(exclude_unset=True, exclude={"pozycje", "wymaga_mpp"})
    if "klient_id" in zmiany:
        _pobierz_klienta_lub_404(db, zmiany["klient_id"])

    typ_docelowy = zmiany.get("typ_dokumentu", faktura.typ_dokumentu)
    pozycje_docelowe = dane.pozycje if dane.pozycje is not None else faktura.pozycje
    dokument_powiazany_docelowy = zmiany.get(
        "dokument_powiazany_id", faktura.dokument_powiazany_id
    )
    przyczyna_docelowa = zmiany.get("przyczyna_korekty", faktura.przyczyna_korekty)
    _waliduj_zgodnosc_dokumentu(
        db,
        typ_docelowy,
        pozycje_docelowe,
        dokument_powiazany_docelowy,
        przyczyna_docelowa,
        faktura_id=faktura.id,
    )

    for pole, wartosc in zmiany.items():
        setattr(faktura, pole, wartosc)

    if dane.pozycje is not None:
        faktura.pozycje.clear()
        db.flush()
        faktura.pozycje.extend(_przelicz_pozycje(dane.pozycje))

    # wymaga_mpp: reczna wartosc (nawet False) zawsze wygrywa jako swiadome
    # nadpisanie; w przeciwnym razie, jesli pozycje albo klient mogly wplynac
    # na sugestie, przeliczamy ja na nowo - nigdy nie zostawiamy przestarzalej
    # wartosci po zmianie danych, od ktorych zalezy (patrz mpp_service).
    pola_podane = dane.model_fields_set
    if "wymaga_mpp" in pola_podane and dane.wymaga_mpp is not None:
        faktura.wymaga_mpp = dane.wymaga_mpp
    elif dane.pozycje is not None or "klient_id" in zmiany:
        klient_aktualny = db.get(Klient, faktura.klient_id)
        suma_brutto_grosze = sum(p.wartosc_brutto_grosze for p in faktura.pozycje)
        faktura.wymaga_mpp = mpp_service.sugeruj_wymaga_mpp(
            db,
            klient_aktualny,
            suma_brutto_grosze,
            [p.nazwa for p in faktura.pozycje],
        )

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
