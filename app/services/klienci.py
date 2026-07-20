from fastapi import HTTPException, status
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Firma, Klient
from app.schemas.klient import (
    KlientCreate,
    KlientImportWiersz,
    KlientImportWynik,
    KlientUpdate,
)


def _sformatuj_blad_walidacji(e: ValidationError) -> str:
    """Pierwszy blad z ValidationError, w czytelnej formie 'pole: powod' -
    reuzywane w importuj_klientow, zeby GUI nie musialo znac ksztaltu bledow
    pydantic (te same, ktore normalnie widzialoby jako odpowiedz HTTP 422)."""
    pierwszy = e.errors()[0]
    komunikat = str(pierwszy.get("msg", ""))
    if komunikat.startswith("Value error, "):
        komunikat = komunikat[len("Value error, ") :]
    pole = ".".join(str(czesc) for czesc in pierwszy.get("loc", ()) if czesc != "body")
    return f"{pole}: {komunikat}" if pole else komunikat


def _pobierz_jedyna_firme(db: Session) -> Firma:
    firmy = db.execute(select(Firma)).scalars().all()
    if len(firmy) != 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "Brak skonfigurowanej firmy (lub jest ich wiecej niz jedna) - "
                "dodaj dokladnie jeden rekord Firma przed utworzeniem klienta."
            ),
        )
    return firmy[0]


def pobierz_klienta(db: Session, klient_id: int) -> Klient:
    klient = db.get(Klient, klient_id)
    if klient is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Nie znaleziono klienta o podanym id.",
        )
    return klient


def lista_klientow(
    db: Session, skip: int, limit: int, tylko_aktywni: bool
) -> list[Klient]:
    zapytanie = select(Klient)
    if tylko_aktywni:
        zapytanie = zapytanie.where(Klient.aktywny.is_(True))
    zapytanie = zapytanie.order_by(Klient.id).offset(skip).limit(limit)
    return list(db.execute(zapytanie).scalars().all())


def utworz_klienta(db: Session, dane: KlientCreate) -> Klient:
    firma = _pobierz_jedyna_firme(db)
    klient = Klient(firma_id=firma.id, **dane.model_dump())
    db.add(klient)
    db.commit()
    db.refresh(klient)
    return klient


def aktualizuj_klienta(db: Session, klient_id: int, dane: KlientUpdate) -> Klient:
    klient = pobierz_klienta(db, klient_id)
    zmiany = dane.model_dump(exclude_unset=True)
    for pole, wartosc in zmiany.items():
        setattr(klient, pole, wartosc)
    db.commit()
    db.refresh(klient)
    return klient


def importuj_klientow(
    db: Session, wiersze: list[KlientImportWiersz], zapisz: bool
) -> list[KlientImportWynik]:
    """Import zbiorczy z pliku CSV (Faza 26). Kazdy wiersz jest walidowany
    NIEZALEZNIE - bledny wiersz nie przerywa importu pozostalych, uzytkownik
    dostaje pelne podsumowanie zaimportowane/pominiete z przyczynami zamiast
    cichej czesciowej porazki.

    `zapisz=False` to tryb "suchej" walidacji (wywolywany z kroku podgladu w
    GUI, PRZED faktycznym importem) - wykonuje DOKLADNIE ta sama walidacje,
    w tym wykrywanie duplikatow NIP wzgledem calej bazy i wewnatrz samego
    pliku, ale nigdy nie zapisuje do bazy. Jedno zrodlo prawdy dla obu trybow,
    zeby podglad w GUI nigdy nie obiecywal czegos innego niz to, co faktycznie
    zaimportuje sie po kliknieciu "Importuj"."""
    nipy_w_bazie = {nip for nip in db.execute(select(Klient.nip)).scalars().all() if nip}
    nipy_w_tym_imporcie: set[str] = set()

    wyniki: list[KlientImportWynik] = []
    for wiersz in wiersze:
        surowe = wiersz.model_dump(exclude={"numer_wiersza"}, exclude_none=True)
        nip = surowe.get("nip")

        if nip and (nip in nipy_w_bazie or nip in nipy_w_tym_imporcie):
            wyniki.append(
                KlientImportWynik(
                    numer_wiersza=wiersz.numer_wiersza,
                    sukces=False,
                    komunikat=f"NIP {nip} już istnieje (w bazie albo powtarza się w pliku).",
                )
            )
            continue

        try:
            dane = KlientCreate(**surowe)
        except ValidationError as e:
            wyniki.append(
                KlientImportWynik(
                    numer_wiersza=wiersz.numer_wiersza,
                    sukces=False,
                    komunikat=_sformatuj_blad_walidacji(e),
                )
            )
            continue

        if nip:
            nipy_w_tym_imporcie.add(nip)

        if not zapisz:
            wyniki.append(KlientImportWynik(numer_wiersza=wiersz.numer_wiersza, sukces=True))
            continue

        klient = utworz_klienta(db, dane)
        wyniki.append(
            KlientImportWynik(
                numer_wiersza=wiersz.numer_wiersza,
                sukces=True,
                klient=klient,
            )
        )
    return wyniki


def usun_klienta(db: Session, klient_id: int) -> None:
    """Soft-delete: klient moze miec powiazane faktury (historia sprzedazy),
    wiec fizyczne usuniecie zerwaloby integralnosc danych. Ustawiamy aktywny=False
    i domyslnie ukrywamy go z listy, ale rekord i jego faktury pozostaja nietkniete.
    """
    klient = pobierz_klienta(db, klient_id)
    klient.aktywny = False
    db.commit()
